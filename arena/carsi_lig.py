# Çarşı Ligi — günlük lig yöneticisi (Dükkan TV).
# Her gün 15 esnaftan en az oynamış 5'i seçilir (konumlar rastgele: konum şansı hafta içinde dengelenir),
# maç oynatılır, Levent & Cemo yorumları ücretsiz edge-tts ile seslendirilir. Günlük sıralama puanı
# (5-4-3-2-1) haftalık tabloya eklenir; her 7. gün haftanın en iyi 5 esnafı HAFTA FİNALİ'nde kapışır.
#
# Kullanım: python3 carsi_lig.py [--deneme]     (--deneme: lig durumunu kaydetmez)
# Çıktı: cikti/carsi/yayin.json  (video, baslik, aciklama, etiketler)
import asyncio, json, os, random, subprocess, sys, tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carsi  # noqa: E402

KOK = carsi.KOK
DURUM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carsi_lig.json")
CIKTI = os.path.join(KOK, "cikti", "carsi")
SES = {  # edge-tts: Türkçe tek erkek ses var; Levent hızlı ve tiz, Cemo yavaş ve kalın
    "L": {"voice": "tr-TR-AhmetNeural", "rate": "+12%", "pitch": "+8Hz"},
    "C": {"voice": "tr-TR-AhmetNeural", "rate": "-4%", "pitch": "-14Hz"},
}


def yukle():
    if os.path.exists(DURUM):
        return json.load(open(DURUM, encoding="utf-8"))
    return {"gun": 0, "hafta": 1, "hafta_puan": {}, "oynama": {}, "kazanma": {}, "gecmis": []}


def kaydet(d):
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def ad(e):
    return carsi.tr_ad(carsi.ESNAF[e][0])


async def _tts(metin, kim, yol):
    import edge_tts
    s = SES[kim]
    await edge_tts.Communicate(metin, s["voice"], rate=s["rate"], pitch=s["pitch"]).save(yol)


def seslendir(balon):
    """Her balon için ses dizisi. Ses, bir sonraki balon başlayana kadar sığacak şekilde hızlandırılır/kırpılır."""
    sonuc = []
    with tempfile.TemporaryDirectory() as td:
        for n, (kim, metin, bitis, bas) in enumerate(balon):
            sonraki = balon[n + 1][3] if n + 1 < len(balon) else bas + 4.5
            pay = max(1.0, min(sonraki - bas, 4.5) - 0.1)
            mp3, wav = os.path.join(td, f"{n}.mp3"), os.path.join(td, f"{n}.wav")
            try:
                for deneme in range(3):
                    try:
                        asyncio.run(_tts(metin, kim, mp3)); break
                    except Exception:
                        if deneme == 2:
                            raise
                sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                             "csv=p=0", mp3], capture_output=True, text=True).stdout.strip() or 0)
                hiz = min(1.45, max(1.0, sure / pay)) if sure else 1.0
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"atempo={hiz:.3f}", "-ac", "1",
                                "-ar", str(carsi.SR), "-f", "f32le", wav], check=True)
                d = np.fromfile(wav, np.float32)
                n_ = int(pay * carsi.SR)
                if len(d) > n_:   # hâlâ uzunsa sonunu yumuşakça kes
                    d = d[:n_].copy(); f = min(len(d), int(0.15 * carsi.SR)); d[-f:] *= np.linspace(1, 0, f)
                sonuc.append(d / max(1e-6, np.abs(d).max()) * 0.9)
            except Exception as ex:
                print("seslendirme atlandı:", metin, ex)
                sonuc.append(None)
    return sonuc


def secim(d, rnd):
    """Bugünün 5 esnafı ve maç türü."""
    gun = d["gun"] + 1
    if gun % 7 == 0 and d["hafta_puan"]:
        sira = sorted(carsi.ESNAF, key=lambda e: (-d["hafta_puan"].get(e, 0), rnd.random()))[:5]
        rnd.shuffle(sira)
        return gun, sira, True
    # en az oynayanlar önce (herkes eşit sahneye çıksın), eşitlikte rastgele
    sira = sorted(carsi.ESNAF, key=lambda e: (d["oynama"].get(e, 0), rnd.random()))[:5]
    rnd.shuffle(sira)   # konum rastgele
    return gun, sira, False


def yayin_bilgisi(gun, esnaflar, final, hafta, sonuc):
    a, b = ad(esnaflar[0]), ad(esnaflar[1])
    if final:
        baslik = f"Çarşı Ligi {hafta}. Hafta FİNALİ: Haftanın Esnafı Kim? 🏆 #shorts"
        ilk = f"{hafta}. haftanın en iyi 5 esnafı finalde! Kupayı kim kaldıracak? 🏆"
    else:
        baslik = f"Çarşı Ligi {gun}. Gün: {a} mı, {b} mı? 🏆 #shorts"
        ilk = f"{', '.join(ad(e) for e in esnaflar)} müşteri kapışıyor! Sence kim kazanır? 🏆"
    aciklama = (f"{ilk}\n\nHer gün yeni maç, her hafta final! Favori esnafını yorumlara yaz 👇\n"
                f"Maçları Levent & Cemo anlatıyor 🎙️\n\n"
                "#çarşıligi #dükkantv #brainrot #esnaf #simitçikedi #oyun #shorts")
    etiket = "çarşı ligi,dükkan tv,brainrot,türk brainrot,esnaf,simülasyon,levent ve cemo"
    return {"baslik": baslik[:100], "aciklama": aciklama, "etiketler": etiket}


def main():
    deneme = "--deneme" in sys.argv
    d = yukle()
    rnd = random.Random()
    gun, esnaflar, final = secim(d, rnd)
    tohum = rnd.randrange(1, 10 ** 9)
    hafta = d["hafta"]
    etiket = f"{hafta}. HAFTA FİNALİ" if final else None
    unvan = "HAFTANIN ESNAFI" if final else None
    # 1) sessiz oynatma: yorumların zamanlarını çıkar  2) seslendir  3) aynı tohumla görüntülü oynat
    taslak = carsi.mac(gun, tohum, "x", esnaflar, cizme=True)
    sesler = seslendir(taslak["balon"])
    os.makedirs(CIKTI, exist_ok=True)
    video = os.path.join(CIKTI, f"carsi_{gun:03d}.mp4")
    sonuc = carsi.mac(gun, tohum, video, esnaflar, konusmalar=sesler, etiket=etiket, sampiyon_yazi=unvan)
    if sonuc["puan"] != dict(zip(esnaflar, taslak["puan"])):
        sys.exit("HATA: sessiz ve görüntülü oynatma farklı sonuç verdi (sesler kayar)")
    # lig tablosu
    sira = sorted(esnaflar, key=lambda e: -sonuc["puan"][e])
    for puan_, e in zip([5, 4, 3, 2, 1], sira):
        d["hafta_puan"][e] = d["hafta_puan"].get(e, 0) + (0 if final else puan_)
        d["oynama"][e] = d["oynama"].get(e, 0) + 1
    d["kazanma"][sira[0]] = d["kazanma"].get(sira[0], 0) + 1
    d["gecmis"].append({"gun": gun, "esnaflar": esnaflar, "puan": sonuc["puan"], "kazanan": sira[0],
                        "final": final, "tohum": tohum})
    d["gun"] = gun
    if final:
        d["hafta"] += 1; d["hafta_puan"] = {}
    bilgi = yayin_bilgisi(gun, esnaflar, final, hafta, sonuc)
    bilgi["video"] = video
    json.dump(bilgi, open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not deneme:
        kaydet(d)
    print(json.dumps({"gun": gun, "final": final, "kazanan": sira[0], "baslik": bilgi["baslik"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
