# Günün haberi (23 Kas 2026, Levent: "güncel haber olursa ve kanallara fayda sağlayacağından emin olunca
# Claude videoyu habere göre ayarlayıp onay almadan 11:00'de yayına alsın").
#
# Her sabah Claude (zamanlanmış görev) gündemi tarar. Güvenli ve kanallara uygun bir konu bulursa
# haber/bugun.json dosyasını yazıp depoya gönderir; bu dosya "Günün Haberi" işini tetikler.
# Bu betik: bölümü "Ne Olur?" görsel motoruyla (neolur/render.py) ve aynı ses klonuyla üretir,
# seçilen her kanalın yayın kuyruğuna sabit saatle (varsayılan 11:00) ekler.
#
# GÖRSEL (24 Kas 2026, Levent: "güncel haberlerde habere göre ücretsiz görsel koyalım"):
# bolum["gorsel_ara"] = ["İngilizce kısa sorgu", ...] (2-4 adet) yazılırsa iş önce SADECE aday fotoğrafları bulur
# (Wikimedia Commons + Openverse, yalnız özgür lisans), haber/gorsel_onizleme.jpg + haber/gorsel_aday.json yazar ve durur.
# Claude önizlemeye bakar, uygun adayları sahnelere "gorsel": {url, ad, yazar, lisans} olarak yazar (uygun yoksa
# bolum["gorselsiz"] = true) ve tekrar gönderir; o zaman video üretilir. Haber sitesi fotoğrafı ASLA kullanılmaz.
#
# haber/bugun.json biçimi:
# {"tarih": "2026-11-24", "saat": "11:00",
#  "kaynaklar": ["https://..."],
#  "kanallar": {"dukkantv": {"baslik": "... #shorts", "etiketler": ["..."]}, "kasakurgu": {...}},
#  "bolum": {neolur/bolumler.json'daki bir bölümle aynı yapı: id, efekt, baslik, ozet, etiketler, adimlar (5),
#            sahneler: kanca, 5 asama, vurgu, son}}
import datetime as dt
import json
import os
import sys

KLASOR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(KLASOR)
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "neolur"))
TR = dt.timezone(dt.timedelta(hours=3))
GECMIS = os.path.join(KLASOR, "gecmis.json")
KANALLAR = {"dukkantv", "kasakurgu", "dramabite", "gizlitarih", "ilturnuva"}


def dogrula(h):
    b = h["bolum"]
    assert set(h["kanallar"]) <= KANALLAR and h["kanallar"], "kanallar hatalı"
    assert len(b["adimlar"]) == 5, "5 adım olmalı"
    tipler = [s["tip"] for s in b["sahneler"]]
    assert tipler[0] == "kanca" and tipler[-1] == "son" and tipler.count("asama") == 5, f"sahne düzeni hatalı: {tipler}"
    for s in b["sahneler"]:
        assert s["satir"] and s["ses"], s
        if s["tip"] == "asama" and "grup" not in s:   # her satırın hangi ses parçasıyla görüneceği
            n, m = len(s["ses"]), len(s["satir"])
            s["grup"] = [min(i, n - 1) if n >= m else (0 if i == 0 or n == 1 else 1) for i in range(m)]
        if "grup" in s:
            assert len(s["grup"]) == len(s["satir"]) and max(s["grup"]) < len(s["ses"]), f"grup hatalı: {s}"
    return h


def aciklama(b, kaynaklar, gorsel_kaynak=()):
    return (f"{b['ozet']}\n\nGörseller temsilidir, seslendirme yapay zekâ ile üretilmiştir."
            + ("\nKaynak: " + " · ".join(kaynaklar[:2]) if kaynaklar else "")
            + ("\nFotoğraflar: " + " · ".join(gorsel_kaynak) if gorsel_kaynak else ""))


def asama(h):
    """aday: önce görsel adayları bulunmalı · uret: video üretilebilir"""
    b = h["bolum"]
    if b.get("gorsel_ara") and not b.get("gorselsiz") and not any(s.get("gorsel") for s in b["sahneler"]):
        return "aday"
    return "uret"


def main():
    yol = os.path.join(KLASOR, "bugun.json")
    if not os.path.exists(yol):
        print("Bugün haber yok.")
        return
    h = dogrula(json.load(open(yol, encoding="utf-8")))
    if len(sys.argv) > 1 and sys.argv[1] == "asama":
        print(asama(h))
        return
    import gorsel
    if asama(h) == "aday":
        liste = gorsel.adaylar(h["bolum"])
        if not liste:
            print("Uygun özgür lisanslı görsel bulunamadı; Claude 'gorselsiz': true yazıp yeniden göndermeli.")
        return
    gecmis = json.load(open(GECMIS, encoding="utf-8")) if os.path.exists(GECMIS) else []
    if any(g["id"] == h["bolum"]["id"] and g["tarih"] == h["tarih"] for g in gecmis):
        print("Bu haber zaten üretildi:", h["bolum"]["id"])
        return
    hh, mm = map(int, h.get("saat", "11:00").split(":"))
    t = dt.date.fromisoformat(h["tarih"])
    zaman = dt.datetime(t.year, t.month, t.day, hh, mm, tzinfo=TR)
    if zaman < dt.datetime.now(TR) + dt.timedelta(minutes=40):
        # Üretim geç kaldıysa haber bayatlamasın: ilk boş yarım saate kaydır, akşamı geçtiyse vazgeç
        zaman = (dt.datetime.now(TR) + dt.timedelta(minutes=50)).replace(second=0, microsecond=0)
        zaman = zaman.replace(minute=0 if zaman.minute < 30 else 30) + dt.timedelta(minutes=30)
        if zaman.hour >= 21:
            print("Haber için çok geç, iptal.")
            return

    import uret as neolur
    import yt_kuyruk
    from yt_ortak import telegram
    b = dict(h["bolum"], tarz=h["bolum"].get("tarz", "belgesel"))
    gorsel_kaynak = gorsel.indir(b)
    if gorsel_kaynak:
        print("Fotoğraflı sahne:", sum(1 for s in b["sahneler"] if s.get("arka")), "· kaynak:", gorsel_kaynak)
    mp4, sorunlar = neolur.uret(b, t)
    satirlar = []
    for kanal, k in h["kanallar"].items():
        os.environ["SABIT_YAYIN"] = zaman.isoformat()
        yt_kuyruk.ekle(kanal, mp4, k["baslik"], aciklama(b, h.get("kaynaklar", []), gorsel_kaynak),
                       ",".join(k.get("etiketler") or b["etiketler"]))
        satirlar.append(f"• {kanal}: {k['baslik']}")
    gecmis.append({"id": h["bolum"]["id"], "tarih": h["tarih"], "saat": f"{zaman:%H:%M}",
                   "kanallar": list(h["kanallar"])})
    json.dump(gecmis, open(GECMIS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.remove(yol)
    for f in (gorsel.ADAY_JSON, gorsel.ONIZLEME):   # bir sonraki haberle karışmasın
        if os.path.exists(f):
            os.remove(f)
    telegram(f"📰 Günün haberi hazır, {zaman:%d.%m %H:%M}'de yayında:\n" + "\n".join(satirlar)
             + ("\n\n🔎 Ses kontrolü: " + "; ".join(sorunlar)[:1500] if sorunlar else ""))


if __name__ == "__main__":
    main()
