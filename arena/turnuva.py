# 81 İl Turnuvası — sezon yönetimi. Her çalıştırmada sıradaki maçı oynatır.
#   1. tur: 9 grup × 9 il (Çemberden Kaçış), son 3 kalan tur atlar → 27 il
#   2. tur: 3 grup × 9 il (Çift Kapı), son 3 kalan tur atlar → 9 il
#   Final:  9 il (Ters Dünya), son kalan ŞAMPİYON. Sonra yeni sezon.
# Kullanım: python turnuva.py oyna   |   python turnuva.py durum
import json, os, random, sys, time

import requests

from iller import AD, ILLER
from motor import mac_oyna

KOK = os.path.dirname(os.path.abspath(__file__))
DURUM = os.path.join(KOK, "sezon.json")
CIKTI = os.path.join(KOK, "..", "cikti", "arena")
HARF = "ABCDEFGHI"
TOKEN, CHAT = os.environ.get("TOKEN", "").strip(), os.environ.get("CHAT", "").strip()


def yeni_sezon(no, tohum):
    rnd = random.Random(tohum)
    p = [x for x, _ in ILLER]; rnd.shuffle(p)
    maclar = [{"id": f"1{HARF[g]}", "tur": 1, "baslik": f"1. TUR · {HARF[g]} GRUBU", "mod": "kacis",
               "plakalar": p[g * 9:(g + 1) * 9], "tur_atlar": 3} for g in range(9)]
    import datetime as dt
    bugun = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    return {"sezon": no, "tohum": tohum, "maclar": maclar, "sampiyon": None, "baslangic": bugun}


def tur_kur(s, tur):
    """Önceki turun kazananlarından yeni turun maçlarını oluşturur."""
    rnd = random.Random(s["tohum"] + tur)
    gecen = [p for m in s["maclar"] if m["tur"] == tur - 1 for p in m.get("atlayan", [])]
    rnd.shuffle(gecen)
    if tur == 2:
        s["maclar"] += [{"id": f"2{g + 1}", "tur": 2, "baslik": f"2. TUR · {g + 1}. GRUP", "mod": "cift_kapi",
                         "plakalar": gecen[g * 9:(g + 1) * 9], "tur_atlar": 3} for g in range(3)]
    else:
        s["maclar"].append({"id": "F", "tur": 3, "baslik": "BÜYÜK FİNAL", "mod": "ters_dunya",
                            "plakalar": gecen, "tur_atlar": 1})


def sonraki_mac(s):
    for m in s["maclar"]:
        if not m.get("atlayan"):
            return m
    return None


def yukle():
    if os.path.exists(DURUM):
        return json.load(open(DURUM, encoding="utf-8"))
    return yeni_sezon(1, int(time.time()) % 100000)


def kaydet(s):
    json.dump(s, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def oyna():
    s = yukle()
    if s.get("sampiyon"):
        s = yeni_sezon(s["sezon"] + 1, s["tohum"] + 7)
    m = sonraki_mac(s)
    if m is None:  # tur bitti, yeni turu kur
        tur = max(x["tur"] for x in s["maclar"]) + 1
        tur_kur(s, tur); m = sonraki_mac(s)
    # bir sonraki maçın tanıtımı (aynı turda varsa)
    i = s["maclar"].index(m)
    if i + 1 < len(s["maclar"]):
        sn = s["maclar"][i + 1]; sonraki = (sn["baslik"], sn["plakalar"])
    elif m["tur"] == 1:
        sonraki = ("2. TUR KURASI · 27 İL", [])
    elif m["tur"] == 2:
        sonraki = ("BÜYÜK FİNAL · 9 İL", [])
    else:
        sonraki = None
    os.makedirs(CIKTI, exist_ok=True)
    cikti = os.path.join(CIKTI, f"S{s['sezon']}_{m['id']}.mp4")
    atlayan, elenen, sure = mac_oyna(m["plakalar"], m["mod"], m["baslik"], m["tur_atlar"], sonraki,
                                     tohum=s["tohum"] * 31 + i, cikti=cikti, final=m["tur"] == 3)
    m["atlayan"], m["elenen"] = atlayan, elenen
    if m["tur"] == 3:
        s["sampiyon"] = atlayan[0]
    kaydet(s)
    adlar = ", ".join(AD[p] for p in atlayan)
    kim = " ".join("#" + AD[p].lower().replace("İ", "i").replace("I", "ı") for p in m["plakalar"])
    if m["tur"] == 3:
        baslik = f"81 İl Turnuvası BÜYÜK FİNAL 🏆 Şampiyon kim oldu? #shorts"
    else:
        baslik = f"81 İl Turnuvası · {m['baslik'].title()} 🏆 Senin şehrin tur atlar mı? #shorts"
    aciklama = (f"Sezon {s['sezon']} · {m['baslik']}\n"
                f"Katılan iller: {', '.join(p + ' ' + AD[p] for p in m['plakalar'])}\n\n"
                f"Şehrini yorumlara yaz! Her gün yeni maç 🏆\n\n#81ilturnuvası #türkiye {kim}")
    meta = {"video": cikti, "baslik": baslik[:100], "aciklama": aciklama,
            "etiketler": ["81 il turnuvası", "türkiye", "şehirler", "simülasyon", "top yarışı", "il il"],
            "atlayan": atlayan, "sure": round(sure, 1), "mac": m["id"], "sezon": s["sezon"]}
    json.dump(meta, open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{m['baslik']}: tur atlayan {adlar} · {sure:.0f} sn")
    # fikstür görselini güncelle; sezonun ilk maçında ve her tur bitince Telegram'a da yolla
    from fikstur import ciz
    import datetime as dt
    fk = ciz(s, os.path.join(KOK, "fikstur.jpg"), dt.date.fromisoformat(s["baslangic"]) if s.get("baslangic") else None)
    tur_bitti = all(x.get("atlayan") for x in s["maclar"] if x["tur"] == m["tur"])
    if TOKEN and (i == 0 or tur_bitti):
        with open(fk, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", timeout=120,
                          data={"chat_id": CHAT, "caption": "🗓 81 İl Turnuvası · güncel fikstür (sabitlenmiş gönderi için)"},
                          files={"photo": f})
    if TOKEN:
        with open(cikti, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", timeout=300,
                          data={"chat_id": CHAT, "supports_streaming": "true",
                                "caption": f"🏆 81 İl Turnuvası · {m['baslik']}\nTur atlayan: {adlar}"},
                          files={"video": f})


def durum():
    s = yukle()
    print("Sezon", s["sezon"], "· şampiyon:", AD.get(s.get("sampiyon") or "", "-"))
    for m in s["maclar"]:
        print(m["id"], m["baslik"], "→", ", ".join(AD[p] for p in m.get("atlayan", [])) or "oynanmadı")


if __name__ == "__main__":
    {"oyna": oyna, "durum": durum}[sys.argv[1] if len(sys.argv) > 1 else "durum"]()
