"""Drama Bite — Hikâye Atölyesi (dramabitetr-crypto/hikaye-atolyesi deposundan kopyalandı;
farkı: video bitince YouTube onay kuyruğuna eklenir)."""
import os
import re
import io
import json
import glob
import time
import random
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ====================== AYARLAR ======================
KONU = (os.environ.get("KONU") or "rastgele").strip()
DIL = (os.environ.get("DIL") or "tr").strip().lower()
SERI = (os.environ.get("SERI") or "tek").strip().lower()   # tek | bolum1 | devam | son
OZET = (os.environ.get("OZET") or "").strip()              # onceki bolumun ozeti (devam/son icin)
GEMINI_KEY = os.environ["GEMINI_API_KEY"].strip()
TG_TOKEN = os.environ["TELEGRAM_TOKEN"].strip()

DIL_ADI = {"tr": "Turkce", "en": "Ingilizce (English)", "es": "Ispanyolca (Espanol)"}.get(DIL, "Turkce")

# Slaytlarin ustundeki imza ve son slayttaki hesap adi (hesap adini kendine gore degistir)
HESAPLAR = {
    "tr": ("DRAMA BITE", "@dramabitetr"),
    "en": ("DRAMA BITE STORIES", ""),
    "es": ("DRAMA BITE HISTORIAS", ""),
}
MARKA, HESAP = HESAPLAR.get(DIL, HESAPLAR["tr"])

KAPANIS = {
    "tr": ["Beğendiysen kaydet.", "Sevdiklerinle paylaş.", "Yarın yeni bir hikaye."],
    "en": ["Save this story.", "Share it with someone you love.", "A new story tomorrow."],
    "es": ["Guarda esta historia.", "Compártela con alguien que quieras.", "Mañana, una nueva historia."],
}.get(DIL)

# Seri hikayelerde kapanis slaytinin son satiri ve baslik etiketi
KAPANIS_SERI = {
    "tr": "Devamı için takip et.",
    "en": "Follow for the next part.",
    "es": "Sígueme para la siguiente parte.",
}.get(DIL)
SERI_ETIKET = {
    "tr": {"bolum1": "Bölüm 1", "devam": "Devam", "son": "Final"},
    "en": {"bolum1": "Part 1", "devam": "Continued", "son": "Finale"},
    "es": {"bolum1": "Parte 1", "devam": "Continuación", "son": "Final"},
}.get(DIL)

# "rastgele" yazilirsa bu listeden biri secilir
# 23 Kas 2026 (Levent): soyut kelimeler ("umut", "aile") yerine dikkat çekici, gizemli ve hayatın içinden
# somut durumlar. İzleyici "bu bana da olabilir" desin ve sonunu merak etsin.
KONULAR = [
    "kasadan her gece biraz para eksiliyor ve kamera kaydında görülen kişi hiç beklenmedik biri",
    "yanlış numaradan gelen mesaj, 20 yıl önce olan bir şeyi biliyor",
    "kiralık evin duvar kâğıdının altından eski bir mektup çıkıyor",
    "taksiye unutulan çantadan bir fotoğraf ve bir adres çıkıyor",
    "mahalle bakkalının veresiye defterinde birinin borçları her ay gizlice siliniyor",
    "esnafın kepengine her sabah isimsiz biri sıcak ekmek bırakıyor",
    "otobüste her sabah aynı koltuğa küçük bir not bırakılıyor",
    "apartmanda yıllardır kimsenin girmediği bir daireden gece ışık geliyor",
    "dedenin sandığından kimsenin bilmediği bir tapu ve bir isim çıkıyor",
    "annenin eski defterinde hiç bahsetmediği bir isim yazıyor",
    "çocukken kaybolan köpek 10 yıl sonra kapının önünde beliriyor",
    "ikinci el alınan telefonda önceki sahibinin bıraktığı tek bir sesli not var",
    "düğünde masaya bırakılan isimsiz zarftan çıkan şey herkesi susturuyor",
    "emekli öğretmene 30 yıl önceki bir öğrencisinden paket geliyor",
    "15 yıl önce ödünç verilen para hiç beklenmedik bir şekilde geri dönüyor",
    "yolda bulunan cüzdanın sahibi, bulan kişinin geçmişinden biri çıkıyor",
    "tamirciye bırakılan eski radyonun içinden bir kaset çıkıyor",
    "asansörde mahsur kalan iki eski arkadaş yıllar önceki kavgayı konuşmak zorunda kalıyor",
    "kardeşler baba evini satmak üzereyken bodrumda bir şey buluyor",
    "gece vardiyasındaki bekçi her gece aynı saatte aynı kişiyi görüyor",
    "pazarda her hafta yaşlı bir adama bedava domates veren manavın sebebi",
    "bayram harçlığını biriktiren çocuğun parayı aslında kim için biriktirdiği",
    "düğün masrafı yüzünden ertelenen nikâh ve gelinin sakladığı karar",
    "gece kuryelik yapan beyaz yakalının kapısına geldiği müşteri tanıdık çıkıyor",
    "kira artışı isteyen ev sahibiyle yaşlı kiracı arasında ortaya çıkan eski bağ",
    "hastane bekleme salonunda tanışan iki yabancının aynı kişiyi beklediği ortaya çıkıyor",
    "mezuniyet töreninde boş kalan sandalyenin hikâyesi",
    "yıllardır konuşmayan iki komşudan birinin kapısına diğerinin adına mektup geliyor",
    "hesabına yanlışlıkla yüklü para yatan esnafın verdiği karar",
    "kayınvalidenin kimseye vermediği tarifin içindeki sır",
    "askerden dönen oğlun evde fark ettiği tek değişiklik",
    "eski bir fotoğraftaki yabancı kişinin aslında ailenin bir parçası çıkması",
    "babanın 30 yıl çalıştığı fabrikadaki son gününde dolabında bulunan not",
    "her yıl aynı gün kapıya bırakılan çiçeği kimin bıraktığı",
]

BICIMLER = {
    "anlatim": "Birinci agizdan, samimi klasik bir anlatim.",
    "mektup": "Hikaye bir mektup olarak yazilsin ('Sevgili ...' diye baslasin, imzayla bitsin).",
    "gunluk": "Hikaye bir gunluk olarak yazilsin (kisa, tarihli veya gunlu notlar).",
    "telefon": "Hikaye bir telefon veya mesajlasma konusmasi uzerinden, kisa diyaloglarla anlatilsin.",
    "diyalog": "Hikaye iki kisinin tek sahnelik diyalogu olarak anlatilsin.",
    "tanik": "Hikaye olaya taniklik eden bir gozlemcinin (komsu, garson, sofor gibi) agzindan anlatilsin.",
}
FINALLER = {
    "ters_kose": "Final beklenmedik bir ters kose olsun.",
    "ders": "Final sade ve vurucu bir hayat dersi cumlesiyle bitsin.",
    "acik_uc": "Final huzunlu ama acik uclu, okuyani dusunduren bir cumle olsun.",
    "umut": "Final umut veren, sicak bir sonla bitsin.",
}
# Ilk slayt (kanca) turleri: her calismada biri secilir, boylece acilislar birbirine benzemez
KANCALAR = {
    "itiraf": "1. slayt bir itirafla acilsin (kimseye soylenmemis bir sey). Hazir kalip cumle kullanma, kendi cumleni kur.",
    "yarim": "1. slayt yarim birakilmis bir cumleyle bitsin; cevap sonraki slaytlarda gelsin.",
    "celiski": "1. slayt bir celiskiyle acilsin: iki zit seyi yan yana koy ya da sasirtici bir gercegi soyle.",
    "somut": "1. slayt cok somut bir ayrintiyla acilsin (bir saat, bir sayi, bir esya) ve hemen bir sorun hissettirsin.",
    "replik": "1. slayt, birinin soyledigi tek bir carpici repliklle acilsin.",
}

MODELLER = [
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


def prompt_olustur(konu, bicim, final, kanca, seri, ozet):
    if seri == "bolum1":
        seri_kural = ("- Bu, bir serinin 1. BOLUMU. Bolumun kendi kucuk bir sonucu olsun ama son slayt cozulmemis, "
                      "merak uyandiran bir anla bitsin (acilmayan bir kapi, yarim kalan bir mesaj gibi). "
                      "Karakterlere gercekci, dile uygun isimler ver; sonraki bolumlerde kullanilacak.")
    elif seri in ("devam", "son") and ozet:
        bitis = ("Bu bolum hikayeyi tatmin edici sekilde BITIRSIN."
                 if seri == "son" else
                 "Bolumun kendi sonucu olsun ama son slayt yeni bir merak aniyla bitsin.")
        seri_kural = ("- Bu, bir serinin sonraki bolumu. Simdiye kadarki ozet:\n" + ozet + "\n"
                      "Ayni karakter isimlerini ve olaylari koru, ozetin bittigi yerden devam et. "
                      "Ilk slayt hatirlatma yapmasin, dogrudan yeni gelismeyle acilsin. " + bitis)
    else:
        seri_kural = "- Hikaye tek parcada tamamlansin. " + final
    return f"""Sen duygusal, kisa hikayeler yazan usta bir yazarsin.
Konu: {konu}
Dil: {DIL_ADI}

TikTok, Instagram ve YouTube Shorts'ta kaydirmali slayt ve kisa video olarak paylasilacak KURGU bir hikaye yaz.
Kurallar:
- 8 slayt olsun (en fazla 9). Video 75-100 saniye olsun: hikaye nefes alsin, ortada bir donum noktasi, sonda ters kose ya da duygusal bir kapanis olsun.
- {kanca}
- Hikaye hayatin icinden ve gizemli olsun: gunluk bir ortamda (bakkal, otobus, apartman, pazar, is yeri) gecsin, izleyici "bu bana da olabilir" desin ve ilk slayttan itibaren "sonra ne oldu?" diye merak etsin. Gizem dogaustu olmasin; sonunda mantikli bir cevabi olsun.
- 1. slayt EN FAZLA 18 kelime olsun. "Merhaba" gibi giris, mekan tasvirleriyle yavas acilis yok: dogrudan catismayla ac.
- "kanca_adaylari" alanina 3 farkli 1. slayt metni yaz; en guclusunu 1. slayt yap.
- Anlatim bicimi: {bicim}
{seri_kural}
- Sade, samimi, gunluk dil kullan. Klise cumlelerden kacin, somut ayrintilar ver (bir esya, bir koku, bir saat gibi). Karakterlere gercekci, dile uygun isimler ver.
- Her slaytta 15 ile 25 kelime olsun, 25'i ASLA gecme. Cumleler kisa olsun.
- Her slaytta 1 ile 2 paragraf olsun. Vurucu cumleler "k": true (kalin) olsun.
- Her slaytta EN FAZLA BIR cumle icin "v": true (vurgu rengi) kullan, en onemli cumle olsun.
- Gercek kisi, marka veya siyaset kullanma. Siddet, cinsellik, nefret yok.
- Hikaye tamamen kurgu olsun.
- Butun metinleri (slayt metinleri, baslik, aciklama, hashtagler, soru, ozet) su dilde yaz: {DIL_ADI}. Konu Turkce verilmis olabilir, hikayeyi yine de bu dilde yaz.
- "duygu" alani icin hikayeye en uygun olani sec: "huzun" (kayip, pismanlik, ayrilik), "nostalji" (aile, cocukluk, anilar), "umut" (dostluk, af, yeni baslangic) veya "gizem" (yalnizlik, supheli, ters kose).
- "baslik" alani: 30-55 karakter, hikayenin EN merak uyandiran catismasini one koyan bir cumle olsun (or. "Babam 20 Yil Sonra Kapiyi Caldi", "Kasadaki Eksik Parayi Kim Aldi?"). Tek kelimelik ya da siirsel baslik ("Kutsal Yalan", "Yarim Kalan Piyon") YAZMA; hikayede olmayan bir seyi vaat etme.
- "soru" alanina izleyiciyi yorum yazmaya iten, hikayedeki ikilemi soran tek bir kisa soru yaz (en fazla 12 kelime). "Sen olsan ne yapardin?" gibi hazir kalip olmasin.
- "ozet" alanina, simdiye kadarki tum hikayenin 4-6 cumlelik ozetini yaz (karakter isimleri ve son durum dahil).
- "aciklama" alaninin sonuna "Kurgu hikayedir." cumlesinin bu dildeki karsiligini yaz.

SADECE su JSON bicimini dondur, baska hicbir sey yazma:
{{
  "baslik": "kisa baslik",
  "duygu": "huzun",
  "kanca_adaylari": ["aday 1", "aday 2", "aday 3"],
  "slaytlar": [
    {{"paragraflar": [{{"m": "metin", "k": false, "v": false}}]}}
  ],
  "soru": "yorum sorusu",
  "ozet": "hikaye ozeti",
  "aciklama": "paylasim icin 1-2 cumlelik aciklama",
  "hashtagler": ["#hikaye", "#duygusal"]
}}"""


# ====================== GEMINI ======================
def kullanilabilir_modeller():
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
            headers={"x-goog-api-key": GEMINI_KEY},
            timeout=60,
        )
        r.raise_for_status()
        adlar = []
        for m in r.json().get("models", []):
            ad = m.get("name", "").replace("models/", "")
            if "flash" not in ad:
                continue
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if any(x in ad for x in ("image", "tts", "live", "audio", "embedding", "thinking", "robotics")):
                continue
            adlar.append(ad)
        adlar.sort(reverse=True)
        return adlar
    except Exception as e:
        print("Model listesi alinamadi:", e)
        return []


def gemini_hikaye(prompt):
    bulunan = kullanilabilir_modeller()
    print("Bulunan modeller:", bulunan)
    if bulunan:
        sirali = [m for m in MODELLER if m in bulunan] + [m for m in bulunan if m not in MODELLER]
    else:
        sirali = list(MODELLER)

    son_hata = None
    for model in sirali:
        for deneme in range(3):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
                    },
                    timeout=180,
                )
                if r.status_code in (429, 500, 503):
                    raise RuntimeError(f"gecici hata {r.status_code}")
                r.raise_for_status()
                parts = r.json()["candidates"][0]["content"]["parts"]
                metin = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                metin = re.sub(r"^```(?:json)?|```$", "", metin.strip(), flags=re.M).strip()
                veri = json.loads(metin)
                if veri.get("slaytlar"):
                    print("Kullanilan model:", model)
                    return veri
                break
            except Exception as e:
                son_hata = e
                print(f"{model} deneme {deneme + 1} calismadi: {e}")
                if "404" in str(e):
                    break
                time.sleep(5 * (deneme + 1))
    raise RuntimeError(f"Hicbir model calismadi. Son hata: {son_hata}")


# ====================== GORSEL ======================
W, H = 1080, 1920
ALTIN = (240, 196, 110)

STILLER = {
    "huzun": {"tip": "gradyan", "ust": (38, 8, 18), "alt": (96, 28, 44),
              "renk": (252, 244, 238), "vurgu": ALTIN, "soluk": (205, 160, 170), "dekor": "halka"},
    "umut": {"tip": "gradyan", "ust": (10, 18, 38), "alt": (32, 46, 82),
             "renk": (240, 238, 230), "vurgu": ALTIN, "soluk": (160, 165, 185), "dekor": "cizgi"},
    "nostalji": {"tip": "kagit", "renk": (50, 36, 28), "vurgu": (140, 70, 30),
                 "soluk": (150, 118, 70), "dekor": "tirnak"},
    "gizem": {"tip": "siyah", "renk": (245, 245, 245), "vurgu": ALTIN,
              "soluk": (170, 140, 80), "dekor": "cerceve"},
}

_kagit_onbellek = {}


def font_bul(kalin):
    adaylar = (
        [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ]
        if kalin
        else [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    )
    for yol in adaylar:
        if os.path.exists(yol):
            return yol
    raise RuntimeError("Yazi tipi bulunamadi")


def sar(metin, font, genislik):
    kelimeler = metin.split()
    satirlar, satir = [], ""
    for k in kelimeler:
        deneme = (satir + " " + k).strip()
        if font.getlength(deneme) <= genislik:
            satir = deneme
        else:
            if satir:
                satirlar.append(satir)
            satir = k
    if satir:
        satirlar.append(satir)
    return satirlar


def zemin_olustur(st):
    if st["tip"] == "gradyan":
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            renk = tuple(int(st["ust"][i] + (st["alt"][i] - st["ust"][i]) * t) for i in range(3))
            d.line([(0, y), (W, y)], fill=renk)
        return img
    if st["tip"] == "kagit":
        if "k" not in _kagit_onbellek:
            img = Image.new("RGB", (W, H), (243, 234, 216))
            rnd = random.Random(3)
            px = img.load()
            for _ in range(60000):
                x, y = rnd.randrange(W), rnd.randrange(H)
                r, g, b = px[x, y]
                v = rnd.randint(-9, 9)
                px[x, y] = (r + v, g + v, b + v)
            _kagit_onbellek["k"] = img.filter(ImageFilter.GaussianBlur(0.8))
        return _kagit_onbellek["k"].copy()
    return Image.new("RGB", (W, H), (6, 6, 6))


def dekor_ciz(d, st):
    dk = st["dekor"]
    if dk == "halka":
        d.ellipse([W - 360, -240, W + 240, 360], outline=(160, 70, 85), width=3)
        d.ellipse([W - 300, -180, W + 180, 300], outline=(130, 50, 65), width=2)
    elif dk == "tirnak":
        d.rectangle([56, 56, W - 56, H - 56], outline=(150, 118, 70), width=3)
        d.rectangle([76, 76, W - 76, H - 76], outline=(190, 160, 110), width=2)
        f = ImageFont.truetype(font_bul(True), 380)
        d.text((104, 150), "\u201C", font=f, fill=(210, 178, 120))
    elif dk == "cerceve":
        d.rectangle([60, 60, W - 60, H - 60], outline=ALTIN, width=3)
        d.rectangle([84, 84, W - 84, H - 84], outline=(120, 96, 52), width=2)
        for cx, cy in [(60, 60), (W - 60, 60), (60, H - 60), (W - 60, H - 60)]:
            d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=ALTIN)


def ust_bilgi(d, st, no=None, toplam=None):
    # Alt kisim platform yazilariyla kapandigi icin imza ve sayac ustte
    f = ImageFont.truetype(font_bul(True), 28)
    ayrik = " ".join(MARKA.replace(" ", "\u00A0\u00A0"))
    if f.getlength(ayrik) > W - 360:
        ayrik = MARKA
    d.text((110, 170), ayrik, font=f, fill=st["soluk"])
    if no and toplam:
        fs = ImageFont.truetype(font_bul(False), 34)
        t = f"{no}/{toplam}"
        d.text((W - 110 - fs.getlength(t), 168), t, font=fs, fill=st["vurgu"])


def metin_ciz(img, paragraflar, st, sol, sag, ortala=False, kalin_boyut=72, normal_boyut=66, min_y=260):
    d = ImageDraw.Draw(img)
    genislik = W - sol - sag
    blok = []
    for p in paragraflar:
        kalin = bool(p.get("k"))
        boyut = kalin_boyut if kalin else normal_boyut
        font = ImageFont.truetype(font_bul(kalin), boyut)
        satirlar = sar(str(p.get("m", "")), font, genislik)
        renk = st["vurgu"] if p.get("v") else st["renk"]
        blok.append((satirlar, font, boyut, renk))

    satir_aralik = 1.25
    para_aralik = 56
    toplam = sum(int(len(s) * b * satir_aralik) + para_aralik for s, _, b, _ in blok) - para_aralik
    # Biraz yukari: alttaki platform yazilari metni kapatmasin
    y = max(min_y, (H - toplam) // 2 - 70)
    ilk_y = y
    for satirlar, font, boyut, renk in blok:
        for s in satirlar:
            x = sol + (genislik - font.getlength(s)) / 2 if ortala else sol
            d.text((x, y), s, font=font, fill=renk)
            y += int(boyut * satir_aralik)
        y += para_aralik
    return ilk_y


def slayt_ciz(slayt, stil_adi, no=None, toplam=None):
    st = STILLER[stil_adi]
    img = zemin_olustur(st)
    d = ImageDraw.Draw(img)
    dekor_ciz(d, st)
    ust_bilgi(d, st, no, toplam)
    cerceve = st["dekor"] in ("cerceve", "tirnak")
    sol, sag = (140, 180) if cerceve else (100, 140)
    ilk_y = metin_ciz(img, slayt["paragraflar"], st, sol, sag, min_y=(380 if st["dekor"] == "tirnak" else 260))
    if st["dekor"] == "cizgi":
        d.line([(sol, ilk_y - 50), (sol + 110, ilk_y - 50)], fill=st["vurgu"], width=5)
    return png_yap(img)


def kapanis_ciz():
    st = STILLER["gizem"]
    img = zemin_olustur(st)
    d = ImageDraw.Draw(img)
    dekor_ciz(d, st)
    ust_bilgi(d, st)
    paragraflar = [{"m": KAPANIS[0], "k": True, "v": True},
                   {"m": KAPANIS[1], "k": False, "v": False},
                   {"m": KAPANIS[2], "k": False, "v": False}]
    if HESAP:
        paragraflar.append({"m": HESAP, "k": True, "v": True})
    metin_ciz(img, paragraflar, st, 140, 180, ortala=True)
    return png_yap(img)


def png_yap(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ====================== TELEGRAM ======================
def chat_id_bul():
    sabit = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    if sabit:
        return sabit
    token = TG_TOKEN.strip()
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=60).json()
    cid = None
    for u in r.get("result", []):
        for anahtar in ("message", "edited_message", "my_chat_member", "channel_post"):
            m = u.get(anahtar) or {}
            if "chat" in m and m["chat"].get("type") == "private":
                cid = m["chat"]["id"]
    if cid is None:
        raise RuntimeError("Telegram chat id bulunamadi (TELEGRAM_CHAT_ID secret'ini kontrol et).")
    return cid


def telegrama_gonder(cid, resimler, aciklama):
    media, files = [], {}
    for i, buf in enumerate(resimler[:10]):
        ad = f"s{i}"
        media.append({"type": "photo", "media": f"attach://{ad}"})
        files[ad] = (f"{ad}.png", buf, "image/png")
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup",
        data={"chat_id": cid, "media": json.dumps(media)},
        files=files,
        timeout=180,
    )
    r.raise_for_status()
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": cid, "text": aciklama},
        timeout=60,
    ).raise_for_status()


# ====================== SES (SESLI ANLATIM) ======================
import base64
import wave
import asyncio

# (edge-tts sesi, Gemini sesi) - dil kodu ile eslesir
SESLER = {
    "tr": ("tr-TR-EmelNeural", "Kore"),
    "en": ("en-US-AriaNeural", "Kore"),
    "es": ("es-MX-DaliaNeural", "Kore"),
}
EDGE_SES, GEMINI_SES = SESLER.get(DIL, SESLER["tr"])
EDGE_HIZ = "+8%"   # biraz daha akıcı (Shorts)
SES_SEVIYE = 1.0          # anlatici ses seviyesi
MUZIK_SEVIYE_SESLI = 0.15  # anlatim varken fon muzigi seviyesi


def anlatim_metni(slayt):
    parcalar = [str(p.get("m", "")).strip() for p in slayt["paragraflar"]]
    return " ".join(p for p in parcalar if p)


def ses_edge(metin, yol):
    import edge_tts  # kurulu degilse hata verir, Gemini sesine gecilir

    async def _kaydet():
        await edge_tts.Communicate(metin, EDGE_SES, rate=EDGE_HIZ).save(yol)

    asyncio.run(_kaydet())
    if not os.path.exists(yol) or os.path.getsize(yol) < 1000:
        raise RuntimeError("edge-tts bos ses dondurdu")


def tts_modelleri_bul():
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
            headers={"x-goog-api-key": GEMINI_KEY},
            timeout=60,
        )
        r.raise_for_status()
        adlar = []
        for m in r.json().get("models", []):
            ad = m.get("name", "").replace("models/", "")
            if "tts" in ad and "generateContent" in m.get("supportedGenerationMethods", []):
                adlar.append(ad)
        adlar.sort(key=lambda a: ("flash" not in a, a))
        if adlar:
            return adlar
    except Exception as e:
        print("TTS model listesi alinamadi:", e)
    return ["gemini-2.5-flash-preview-tts"]


def ses_gemini(metin, yol, modeller):
    son_hata = None
    for model in modeller:
        for deneme in range(3):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "Say in a warm, emotional storytelling voice at a natural, slightly brisk pace: " + metin}]}],
                        "generationConfig": {
                            "responseModalities": ["AUDIO"],
                            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_SES}}},
                        },
                    },
                    timeout=180,
                )
                if r.status_code in (429, 500, 503):
                    raise RuntimeError(f"gecici hata {r.status_code}")
                r.raise_for_status()
                parca = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                pcm = base64.b64decode(parca["data"])
                hz = 24000
                eslesme = re.search(r"rate=(\d+)", parca.get("mimeType", ""))
                if eslesme:
                    hz = int(eslesme.group(1))
                with wave.open(yol, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(hz)
                    w.writeframes(pcm)
                return
            except Exception as e:
                son_hata = e
                print(f"Gemini ses {model} deneme {deneme + 1} calismadi: {e}")
                if "404" in str(e):
                    break
                time.sleep(8 * (deneme + 1))
    raise RuntimeError(f"Gemini ses uretimi basarisiz: {son_hata}")


def sure_olc(yol):
    c = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", yol],
        capture_output=True, text=True, check=True,
    )
    return float(c.stdout.strip())


def ses_uret(slaytlar):
    """Her slayt icin anlatim sesi uretir: [(dosya, sure), ...]. Hicbiri olmazsa None doner."""
    klasor = "sesler"
    os.makedirs(klasor, exist_ok=True)
    for saglayici in ("edge", "gemini"):
        try:
            modeller = tts_modelleri_bul() if saglayici == "gemini" else None
            sonuc = []
            for i, s in enumerate(slaytlar):
                metin = anlatim_metni(s)
                if saglayici == "edge":
                    yol = f"{klasor}/a{i:02d}.mp3"
                    ses_edge(metin, yol)
                else:
                    yol = f"{klasor}/a{i:02d}.wav"
                    ses_gemini(metin, yol, modeller)
                    time.sleep(3)
                sonuc.append((yol, sure_olc(yol)))
            print("Sesli anlatim hazir:", saglayici)
            return sonuc
        except Exception as e:
            print(f"{saglayici} ses uretimi calismadi: {e}")
    print("Sesli anlatim uretilemedi, video anlatimsiz olacak.")
    return None


# ====================== MUZIK ======================
from array import array

MUZIK_SEVIYE_URETILEN_SESLI = 0.22   # uretilen muzik, anlatim varken
MUZIK_SEVIYE_URETILEN = 0.6          # uretilen muzik, anlatim yokken

# Duyguya gore otomatik uretilen (telifsiz, tamamen ozgun) ortam muzigi.
# akorlar: MIDI nota numaralari, desen: akor icindeki nota sirasi (None = sessizlik)
MUZIK_STILLERI = {
    "huzun": {"bpm": 60, "sonum": 0.9975, "desen": [0, 2, 3, 4, 3, 2, 3, 1],
              "akorlar": [(45, 52, 57, 60, 64), (41, 48, 53, 57, 60), (48, 55, 60, 64, 67), (43, 50, 55, 59, 62)]},
    "nostalji": {"bpm": 72, "sonum": 0.9945, "desen": [1, 2, 3, 4, 3, 2, 3, 1],
                 "akorlar": [(48, 60, 64, 67, 72), (45, 57, 60, 64, 69), (41, 57, 60, 65, 69), (43, 55, 59, 62, 67)]},
    "umut": {"bpm": 76, "sonum": 0.996, "desen": [0, 2, 3, 4, 3, 2, 4, 3],
             "akorlar": [(50, 57, 62, 66, 69), (45, 57, 61, 64, 69), (47, 59, 62, 66, 71), (43, 55, 59, 62, 67)]},
    "gizem": {"bpm": 56, "sonum": 0.9975, "desen": [0, None, 3, None, 4, None, 2, None],
              "akorlar": [(38, 50, 57, 62, 65), (46, 53, 58, 62, 65), (43, 50, 55, 58, 62), (45, 52, 57, 61, 64)]},
}
MUZIK_HZ = 22050


def _nota_ekle(cikis, bas, f, sure_n, sonum, guc, rnd):
    # Karplus-Strong: telli calgi (arp/gitar) benzeri nota
    n = max(2, int(MUZIK_HZ / f))
    halka = [rnd.uniform(-1, 1) for _ in range(n)]
    uzunluk = min(int(sure_n * MUZIK_HZ), len(cikis) - bas)
    idx = 0
    for i in range(uzunluk):
        cur = halka[idx]
        nxt = halka[(idx + 1) % n]
        cikis[bas + i] += cur * guc
        halka[idx] = sonum * 0.5 * (cur + nxt)
        idx = (idx + 1) % n


def muzik_uret(duygu, sure, yol="muzik_uretilen.wav"):
    st = MUZIK_STILLERI.get(duygu, MUZIK_STILLERI["huzun"])
    rnd = random.Random(7)
    toplam = int(sure * MUZIK_HZ)
    cikis = array("f", [0.0]) * toplam
    sekizlik = 60.0 / st["bpm"] / 2
    adim = 0
    while True:
        t = adim * sekizlik
        bas = int(t * MUZIK_HZ)
        if bas >= toplam:
            break
        akor = st["akorlar"][(adim // 8) % len(st["akorlar"])]
        nota = st["desen"][adim % len(st["desen"])]
        if nota is not None:
            midi = akor[nota]
            f = 440.0 * 2 ** ((midi - 69) / 12)
            guc = 0.9 if adim % 8 == 0 else 0.6 + rnd.uniform(0, 0.15)
            _nota_ekle(cikis, bas, f, 2.6, st["sonum"], guc, rnd)
        adim += 1

    tepe = max(max(cikis), -min(cikis)) or 1.0
    olcek = 0.7 * 32767 / tepe
    ham = yol + ".ham.wav"
    with wave.open(ham, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(MUZIK_HZ)
        w.writeframes(array("h", [int(x * olcek) for x in cikis]).tobytes())
    # Yumusat, yankı ekle, sesi sinirla
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", ham,
         "-af", "lowpass=f=4500,aecho=0.7:0.9:70|140|280:0.35|0.25|0.18,alimiter=limit=0.9",
         yol],
        check=True,
    )
    return yol


def muzik_sec(duygu, sure):
    """Once muzik/<duygu>/ klasorune, sonra muzik/ klasorune bakar; yoksa otomatik uretir.
    Doner: (dosya, uretilen_mi) ya da (None, False)"""
    for desen in (f"muzik/{duygu}/*", "muzik/*"):
        dosyalar = [f for f in glob.glob(desen) if f.lower().endswith((".mp3", ".m4a", ".wav"))]
        if dosyalar:
            return random.choice(dosyalar), False
    try:
        return muzik_uret(duygu, sure + 3), True
    except Exception as e:
        print("Otomatik muzik uretilemedi:", e)
        return None, False


# ====================== VIDEO ======================
GECIS = 0.6  # slaytlar arasi yumusak gecis (saniye)


def slayt_suresi(slayt):
    kelime = sum(len(str(p.get("m", "")).split()) for p in slayt["paragraflar"])
    return min(12.0, max(5.0, 3.0 + kelime / 2.5))


def sureleri_hesapla(slaytlar, sesler):
    # Anlatim varsa slayt, anlatim bitene kadar ekranda kalir
    if sesler:
        sureler = [max(3.0, sure + 0.7) for _, sure in sesler]  # Shorts: bekleme kısa, izleyici kaydırmasın
    else:
        sureler = [slayt_suresi(s) for s in slaytlar]
    return sureler + [3.0]  # kapanis slayti


def video_yap(resimler, sureler, sesler=None, duygu="huzun", cikis="hikaye.mp4"):
    klasor = "kareler"
    os.makedirs(klasor, exist_ok=True)
    yollar = []
    for i, buf in enumerate(resimler):
        yol = f"{klasor}/s{i:02d}.png"
        with open(yol, "wb") as f:
            f.write(buf.getvalue())
        yollar.append(yol)

    n = len(yollar)
    toplam = sum(sureler) - (n - 1) * GECIS

    komut = ["ffmpeg", "-y"]
    for yol, sure in zip(yollar, sureler):
        komut += ["-loop", "1", "-framerate", "30", "-t", f"{sure:.2f}", "-i", yol]
    sira = n  # sonraki girdinin numarasi

    # Anlatim dosyalari
    ses_girdileri = []
    if sesler:
        for yol, _ in sesler:
            komut += ["-i", yol]
            ses_girdileri.append(sira)
            sira += 1

    # Fon muzigi (duyguya uygun)
    muzik_girdisi = None
    muzik, uretilen = muzik_sec(duygu, toplam)
    if muzik:
        print("Fon muzigi:", muzik, "(otomatik uretildi)" if uretilen else "")
        komut += ["-stream_loop", "-1", "-i", muzik]
        muzik_girdisi = sira
        sira += 1
    else:
        print("Fon muzigi olmayacak.")

    # Goruntu: slaytlari yumusak gecisle (xfade) birlestir
    filtre = []
    onceki = "0:v"
    gecen = 0.0
    for k in range(1, n):
        gecen += sureler[k - 1]
        offset = gecen - k * GECIS
        cikti = f"v{k}"
        filtre.append(
            f"[{onceki}][{k}:v]xfade=transition=fade:duration={GECIS}:offset={offset:.2f}[{cikti}]"
        )
        onceki = cikti
    filtre.append(f"[{onceki}]format=yuv420p,fps=30[vson]")

    # Ses: her slaytin anlatimi, slayt tam gorunur olunca baslar
    ses_etiket = None
    if ses_girdileri:
        etiketler = []
        for j, girdi in enumerate(ses_girdileri):
            gorunur = 0.0 if j == 0 else sum(sureler[:j]) - (j - 1) * GECIS
            ms = int((gorunur + (0.5 if j == 0 else 0.3)) * 1000)
            filtre.append(
                f"[{girdi}:a]aresample=44100,aformat=channel_layouts=stereo,"
                f"volume={SES_SEVIYE},adelay={ms}|{ms}[a{j}]"
            )
            etiketler.append(f"[a{j}]")
        filtre.append(f"{''.join(etiketler)}amix=inputs={len(etiketler)}:duration=longest:normalize=0[ses]")
        ses_etiket = "ses"

    muzik_etiket = None
    if muzik_girdisi is not None:
        if uretilen:
            seviye = MUZIK_SEVIYE_URETILEN_SESLI if ses_etiket else MUZIK_SEVIYE_URETILEN
        else:
            seviye = MUZIK_SEVIYE_SESLI if ses_etiket else 1.0
        filtre.append(
            f"[{muzik_girdisi}:a]aresample=44100,aformat=channel_layouts=stereo,volume={seviye},"
            f"afade=t=in:d=2,afade=t=out:st={max(0, toplam - 3):.2f}:d=3[muz]"
        )
        muzik_etiket = "muz"

    if ses_etiket and muzik_etiket:
        filtre.append("[ses][muz]amix=inputs=2:duration=longest:normalize=0[sson]")
        son_ses = "sson"
    else:
        son_ses = ses_etiket or muzik_etiket

    komut += ["-filter_complex", ";".join(filtre), "-map", "[vson]"]
    if son_ses:
        komut += ["-map", f"[{son_ses}]", "-c:a", "aac", "-b:a", "192k"]
    komut += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-movflags", "+faststart",
        "-t", f"{toplam:.2f}",
        cikis,
    ]
    subprocess.run(komut, check=True)
    print(f"Video hazir: {cikis} ({toplam:.0f} sn)")
    return cikis


def video_gonder(cid, yol, aciklama):
    with open(yol, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
            data={
                "chat_id": cid,
                "caption": aciklama[:1000],
                "supports_streaming": "true",
                "width": W,
                "height": H,
            },
            files={"video": (yol, f, "video/mp4")},
            timeout=300,
        ).raise_for_status()


# ====================== KAPANIS, SURE, SERI (YENI) ======================
# Bu bolumdeki ayni adli fonksiyonlar, yukaridakilerin yerine gecer (sonra tanimlandigi icin).

def kapanis_ciz(soru="", seri="tek"):
    """Son slayt: hikayeye ozgu yorum sorusu + kaydet/paylas cagrisi + hesap adi."""
    st = STILLER["gizem"]
    img = zemin_olustur(st)
    d = ImageDraw.Draw(img)
    dekor_ciz(d, st)
    ust_bilgi(d, st)
    paragraflar = []
    if soru:
        paragraflar.append({"m": soru, "k": True, "v": True})
    paragraflar.append({"m": KAPANIS[0], "k": False, "v": False})
    paragraflar.append({"m": KAPANIS[1], "k": False, "v": False})
    if seri in ("bolum1", "devam"):
        paragraflar.append({"m": KAPANIS_SERI, "k": True, "v": False})
    else:
        paragraflar.append({"m": KAPANIS[2], "k": False, "v": False})
    if HESAP:
        paragraflar.append({"m": HESAP, "k": True, "v": True})
    metin_ciz(img, paragraflar, st, 140, 180, ortala=True)
    return png_yap(img)


def sureleri_hesapla(slaytlar, sesler):
    # Anlatim varsa slayt, anlatim bitince biraz bekleyip degisir (daha kisa video)
    if sesler:
        sureler = [max(4.5, sure + 1.3) for _, sure in sesler]
    else:
        sureler = [slayt_suresi(s) for s in slaytlar]
    return sureler + [6.0]  # kapanis slayti (soruyu okumaya zaman)


def mesaj_gonder(cid, metin):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": cid, "text": metin[:4000]},
        timeout=60,
    ).raise_for_status()


# ====================== ANA AKIS ======================
def main():
    seri = SERI if SERI in ("tek", "bolum1", "devam", "son") else "tek"
    if seri in ("devam", "son") and not OZET:
        print("UYARI: 'ozet' bos, seri modu 'tek' olarak calisacak.")
        seri = "tek"

    if KONU.lower() in ("", "rastgele", "random", "rastgele konu"):
        konu = random.choice(KONULAR)
    else:
        konu = KONU
    bicim_ad = random.choice(list(BICIMLER))
    final_ad = random.choice(list(FINALLER))
    kanca_ad = random.choice(list(KANCALAR))
    print(f"Konu: {konu} | Bicim: {bicim_ad} | Final: {final_ad} | Kanca: {kanca_ad} | Seri: {seri} | Dil: {DIL}")

    prompt = prompt_olustur(konu, BICIMLER[bicim_ad], FINALLER[final_ad], KANCALAR[kanca_ad], seri, OZET)
    veri = gemini_hikaye(prompt)
    slaytlar = veri["slaytlar"][:7]
    duygu = str(veri.get("duygu", "huzun")).strip().lower()
    if duygu not in STILLER:
        duygu = "huzun"
    print("Duygu / stil:", duygu)
    print("Kanca adaylari:", veri.get("kanca_adaylari"))
    for i, s in enumerate(slaytlar):
        kelime = sum(len(str(p.get("m", "")).split()) for p in s["paragraflar"])
        print(f"Slayt {i + 1}: {kelime} kelime" + ("  (UZUN!)" if kelime > 30 else ""))

    soru = str(veri.get("soru", "")).strip()
    n = len(slaytlar)
    resimler = [
        slayt_ciz(s, "gizem" if i == 0 else duygu, no=i + 1, toplam=n)
        for i, s in enumerate(slaytlar)
    ]
    resimler.append(kapanis_ciz(soru, seri))

    baslik = str(veri.get("baslik", "")).strip()
    if seri != "tek" and SERI_ETIKET:
        baslik = f"{baslik} ({SERI_ETIKET[seri]})"
    etiketler = " ".join(veri.get("hashtagler", []))
    aciklama = f"{baslik}\n\n{veri.get('aciklama', '')}\n\n{soru}\n\n{etiketler}".strip()
    cid = chat_id_bul()
    telegrama_gonder(cid, resimler, aciklama)
    print("Slaytlar Telegram'a gonderildi.")

    # Seri icin ozet: sonraki bolumde workflow'daki 'ozet' kutusuna yapistirilacak
    if seri in ("bolum1", "devam") and veri.get("ozet"):
        mesaj_gonder(cid, "SERI OZETI - sonraki bolum icin 'ozet' kutusuna yapistir (seri: devam):\n\n" + str(veri["ozet"]))

    # Video adimi: hata verirse slaytlar zaten gonderildigi icin akis bozulmaz
    try:
        sesler = ses_uret(slaytlar)
        sureler = sureleri_hesapla(slaytlar, sesler)
        yol = video_yap(resimler, sureler, sesler, duygu)
        video_gonder(cid, yol, aciklama)
        print("Video Telegram'a gonderildi.")
        # YouTube yayın kuyruğu (Drama Bite) için bilgi bırak — onaysız yayın olmaz
        import json as _json
        # Başlığa yorum sorusu eklenir (Kasa Kurgu'da yorum isteyen başlıklar daha çok izlendi); sığmazsa eski hâli
        # 15 Kasım 2026 analizi: en çok izlenen Drama Bite videoları (1-3,7 bin) 75-150 sn sürüyordu ve başlıkları
        # kısa, merak uyandıran tek ifadeydi ("Sekiz Yıllık Sır", "Gece 03:20 Borcu"); 9 Kasım'dan sonra 45-55 sn,
        # "| soru #shorts" başlıklı videolar 30-300'de kaldı. Eski kazanan biçime dönüldü.
        yt_baslik = baslik[:90] if baslik else "Drama Bite"
        os.makedirs("cikti", exist_ok=True)
        _json.dump({"video": os.path.abspath(yol), "baslik": yt_baslik, "aciklama": aciklama,
                    "etiketler": ",".join(h.lstrip("#") for h in veri.get("hashtagler", []))},
                   open("cikti/yayin.json", "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e:
        print("Video adimi calismadi:", e)


if __name__ == "__main__":
    main()
