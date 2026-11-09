"""Kasa Kurgu — "500 TL ile 50.000 TL Hedefi" dizisinin sıradaki gününü yazar.

1) Bir önceki günün YouTube videosundaki yorumlarda A/B oylarını sayar (eşitlik ya da oy yoksa A).
2) Gemini, seçilen kararla hikâyeyi devam ettiren yeni günün sahnelerini aynı biçimde yazar.
3) Biçim kontrolünden geçerse bolumler/gunNN_X.json olarak kaydeder ve yayın bilgisi bırakır.
Bu dosya bir sonraki adımda uret.py ile videoya çevrilir.
"""
import glob
import json
import os
import re
import sys
import time

import requests

KLASOR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(KLASOR))
from yt_ortak import erisim_anahtari, kanal_bilgi, yt  # noqa: E402

ANAHTAR = "".join(os.environ.get("GEMINI_API_KEY", "").split())
MODELLER = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]
GORSEL = ["defter", "domates", "etiket", "hal", "kalabalik", "para", "tezgah"]
IFADE = ["dusunceli", "gulen", "mutlu", "saskin", "uzgun"]
TEMA = ["gece", "sabah", "gun", "aksam", "hesap"]


def gemini(istem):
    for model in MODELLER:
        for _ in range(4):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={ANAHTAR}",
                    json={"contents": [{"parts": [{"text": istem}]}],
                          "generationConfig": {"temperature": 0.85, "responseMimeType": "application/json"}},
                    timeout=120)
                if r.status_code == 404:
                    break
                if r.status_code == 429:
                    print("Gemini kota sınırı, bekleniyor...", flush=True)
                    time.sleep(20)
                    continue
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print("Gemini hata:", str(e)[:150], flush=True)
                time.sleep(5)
    raise RuntimeError("Gemini cevap vermedi")


def bolumler():
    liste = []
    for p in glob.glob(os.path.join(KLASOR, "bolumler", "gun*.json")):
        v = json.load(open(p, encoding="utf-8"))
        liste.append((v["gun"], p, v))
    return sorted(liste)


def son_kasa(v):
    deger = v["kasa_basi"]
    for s in v["sahneler"]:
        if isinstance(s.get("kasa"), (int, float)):
            deger = s["kasa"]
    return deger


def oy_say(gun):
    """Gün N videosundaki yorumlardan A/B oylarını sayar."""
    try:
        tok = erisim_anahtari("kasakurgu")
        kanal = yt(tok, "channels", part="contentDetails", mine="true")["items"][0]
        yukleme = kanal["contentDetails"]["relatedPlaylists"]["uploads"]
        videolar = yt(tok, "playlistItems", part="snippet", playlistId=yukleme, maxResults=50)["items"]
        hedef = [v for v in videolar if re.search(rf"Gün\s*{gun}\s*/", v["snippet"]["title"])]
        if not hedef:
            print(f"Gün {gun} videosu bulunamadı, varsayılan A.")
            return "A", 0, 0
        vid = hedef[0]["snippet"]["resourceId"]["videoId"]
        a = b = 0
        sayfa = None
        while True:
            ek = {"pageToken": sayfa} if sayfa else {}
            c = yt(tok, "commentThreads", part="snippet", videoId=vid, maxResults=100, textFormat="plainText", **ek)
            for t in c.get("items", []):
                metin = t["snippet"]["topLevelComment"]["snippet"]["textDisplay"].strip().upper()
                if re.match(r"^\W*A\b", metin):
                    a += 1
                elif re.match(r"^\W*B\b", metin):
                    b += 1
            sayfa = c.get("nextPageToken")
            if not sayfa:
                break
        print(f"Gün {gun} oyları: A={a} B={b}")
        return ("A" if a >= b else "B"), a, b
    except Exception as e:
        print("Oylar okunamadı, varsayılan A:", str(e)[:200])
        return "A", 0, 0


def gecerli(v, gun, kasa_basi):
    try:
        assert v["gun"] == gun and v["kasa_basi"] == kasa_basi and v["hedef"] == 50000
        sah = v["sahneler"]
        assert 5 <= len(sah) <= 8
        for s in sah[:-1]:
            assert s["tema"] in TEMA and s["gorsel"] in GORSEL and s["ifade"] in IFADE
            assert 1 <= len(s["baslik"]) <= 28 and len(s["anlatim"].split()) <= 30
            if "kasa" in s and s["kasa"] is not None:
                assert isinstance(s["kasa"], int) and 0 <= s["kasa"] <= 60000
            if s.get("gorsel_yazi"):
                assert len(s["gorsel_yazi"]) <= 16
            if s.get("damga"):
                assert len(s["damga"]) <= 12
        son = sah[-1]
        if gun < 30:
            assert son["tema"] == "oylama" and len(son["secenek"]) == 2 and son["ifade"] in IFADE
            assert all(len(x) <= 18 for x in son["secenek"])
        return True
    except Exception as e:
        print("Biçim hatası:", repr(e)[:200])
        return False


def main():
    liste = bolumler()
    gun_n, _, son = liste[-1]
    if gun_n >= 30:
        print("Dizi tamamlandı (30. gün).")
        return
    secim, a, b = oy_say(gun_n)
    oylama = son["sahneler"][-1]
    secilen = oylama.get("secenek", ["Evet", "Hayır"])[0 if secim == "A" else 1]
    kasa_basi = son_kasa(son)
    yeni_gun = gun_n + 1
    gecmis = "\n".join(f"Gün {g}: " + " ".join(s.get("anlatim", "") for s in v["sahneler"]) for g, _, v in liste[-4:])
    ornek = json.dumps(son, ensure_ascii=False)
    istem = f"""Sen Türkçe kısa dikey video dizisi yazan bir senaristsin. Dizi: "500 TL ile 50.000 TL Hedefi".
Anlatıcı (birinci tekil kişi), 30 günde 50.000 TL biriktirip dükkân kirasını ödemeye çalışan genç bir girişimci.
Her gün izleyiciler yorumlarla A/B kararı veriyor.

Son günler:
{gecmis}

Gün {gun_n} sonunda soru: "{oylama.get('baslik', '')}" — İzleyiciler {secim} ("{secilen}") seçti (A={a}, B={b}).
Şimdi GÜN {yeni_gun}'i yaz. Kasa {kasa_basi} TL ile başlıyor.

Kurallar:
- İlk sahne güçlü kanca: kararın sonucunu hemen göster (ilk 2 saniyede merak/şok).
- 6 sahne + en sonda 1 oylama sahnesi (toplam 7). {"30. gün dizinin finali: oylama sahnesi YOK, hikâye tatmin edici biter." if yeni_gun == 30 else ""}
- Her "anlatim" en fazla 22 kelime, kısa cümleler, konuşma dili. "baslik" BÜYÜK HARF, en fazla 24 karakter.
- Para değişince o sahneye "kasa": yeni_toplam (tam sayı) ekle; gerçekçi küçük kazanç/kayıplar (bir günde en fazla ±6.000 TL).
  Hedefe ulaşmak {30 - yeni_gun} gün sonra mümkün olmalı ama kolay olmasın.
- "tema" şunlardan: {", ".join(TEMA)}; son sahne "oylama". "gorsel" şunlardan: {", ".join(GORSEL)}.
  "ifade" şunlardan: {", ".join(IFADE)}. İsteğe bağlı "gorsel_yazi" (en fazla 14 karakter) ve "damga" (en fazla 10 karakter).
- Oylama sahnesi: "secenek": ["...", "..."] (her biri en fazla 16 karakter), anlatım "Yoruma A veya B yaz. Yarın gün {yeni_gun + 1}!" ile bitsin.
- Temiz, herkese uygun; kumar, bahis, yasa dışı iş, şiddet, gerçek marka ve gerçek kişi YOK. Ticaret, pazarlık, esnaflık, emek olsun.
- Aynı JSON biçimi: "gun": {yeni_gun}, "toplam_gun": 30, "kasa_basi": {kasa_basi}, "hedef": 50000, "hedef_adi": "{son.get('hedef_adi', 'Dükkan Kirası')}".

Örnek biçim (önceki gün): {ornek}

SADECE yeni günün JSON nesnesini döndür."""
    for deneme in range(3):
        v = json.loads(gemini(istem))
        if isinstance(v, list):
            v = v[0]
        v["gun"], v["toplam_gun"], v["kasa_basi"], v["hedef"] = yeni_gun, 30, kasa_basi, 50000
        v.setdefault("hedef_adi", son.get("hedef_adi", "Dükkan Kirası"))
        if gecerli(v, yeni_gun, kasa_basi):
            break
        print(f"Deneme {deneme + 1} geçersiz, yeniden yazılıyor.")
    else:
        sys.exit("Geçerli bölüm yazılamadı")
    yol = os.path.join(KLASOR, "bolumler", f"gun{yeni_gun:02d}_{secim}.json")
    json.dump(v, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    bitis = son_kasa(v)
    json.dump({"bolum": yol,
               "baslik": f"500 TL ile 50.000 TL Hedefi | Gün {yeni_gun}/30 | Kararı Siz Verin! 💸",
               "aciklama": (f"Gün {yeni_gun}/30 — Kasa: {bitis:,} TL / Hedef: 50.000 TL\n"
                            f"Dün sizin kararınız: {secilen} ({secim}).\n\n"
                            "Bugünün kararını yorumlara A ya da B yazarak siz verin! Kurgusal hikâyedir.\n\n"
                            "#para #girişimci #kurgu #hikaye #shorts").replace(",", "."),
               "etiketler": "girişimcilik,para biriktirme,kurgu hikaye,kasa,esnaf,karar"},
              open(os.path.join(KLASOR, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"Gün {yeni_gun} yazıldı: {yol} (kasa {kasa_basi} → {bitis})")


if __name__ == "__main__":
    main()
