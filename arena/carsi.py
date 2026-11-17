# Çarşı Ligi (Dükkan TV) — esnaf karakterler müşteri kapışıyor. Fizik + çizim + ses tamamen kodla, ücretsiz.
# Yukarıdan müşteriler yağar, çivilere ve hareketli tamponlara çarpıp alttaki 5 dükkândan birine düşer.
# Altın müşteri 5 puan. En çok müşteri toplayan esnaf günü kazanır. Levent & Cemo maçı anlatır.
#
# Kullanım: python3 carsi.py <gün_no> <tohum> <çıktı.mp4> [karakter1 karakter2 ... karakter5]
import json, math, os, random, subprocess, sys, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GORSEL = os.path.join(KOK, "gorseller", "brainrot")
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
W, H, FPS, ALT = 1080, 1920, 30, 4          # ALT: kare başına fizik adımı
SR = 44100

ESNAF = {  # dosya: (ekranda ad, renk)
    "simitci-kedi": ("SİMİTÇİ KEDİ", (240, 140, 50)),
    "borekci-baykus": ("BÖREKÇİ BAYKUŞ", (205, 150, 70)),
    "dondurmaci-keci": ("DONDURMACI KEÇİ", (120, 190, 240)),
    "kokorec-ejderha": ("KOKOREÇ EJDERHA", (230, 80, 60)),
    "lahmacun-kaplumbaga": ("LAHMACUN KAPLUMBAĞA", (110, 190, 90)),
    "pide-timsah": ("PİDE TİMSAH", (80, 170, 90)),
    "ayran-penguen": ("AYRAN PENGUEN", (90, 120, 200)),
    "cay-bardagi-tavsan": ("ÇAY BARDAĞI TAVŞAN", (200, 60, 50)),
    "caydanlik-pasa": ("ÇAYDANLIK PAŞA", (150, 160, 175)),
    "dolmus-kopek": ("DOLMUŞ KÖPEK", (240, 190, 40)),
    "kumpir-ayi": ("KUMPİR AYI", (160, 110, 70)),
    "lokum-fil": ("LOKUM FİL", (240, 120, 170)),
    "nazar-baligi": ("NAZAR BALIĞI", (40, 90, 220)),
    "simit-kapan-marti": ("SİMİT KAPAN MARTI", (170, 180, 190)),
    "tavla-kurbaga": ("TAVLA KURBAĞA", (70, 160, 70)),
}

# Yerleşim
CARSI = os.path.join(KOK, "gorseller", "carsi")
MASA_Y = 120              # spiker masasının üst kenarı
BALON_Y = 500             # konuşma balonunun üst kenarı
DOGUM_Y = 640             # müşterilerin doğduğu yükseklik
CIVI_Y0, CIVI_DY, CIVI_SIRA = 705, 78, 9
KUTU_Y = 1395             # müşteri bu çizgiyi geçince dükkâna sayılır
DUKKAN_Y = 1420           # dükkân resimlerinin üst kenarı


def sinirlar(n):
    """n dükkânın kenar çizgileri. Kenar dükkânlar biraz dar (duvardan sekenleri de topluyorlar);
    5'li testlerde 280 maçla ölçüldü. Konumlar her maçta rastgele dağıtıldığı için kalan şans payı dengelenir."""
    g = [0.95 if i in (0, n - 1) and n > 2 else 1.0 for i in range(n)]
    return np.cumsum([0] + [W * x / sum(g) for x in g])
TOP_R, CIVI_R = 18, 9
G = 1500.0


def tr_ad(s):
    """Türkçe kurallarla 'Baş Harfler Büyük' (Python .title() 'I'yı 'i' yapıyor: ÇAYDANLIK → Çaydanlik)."""
    def kucuk(c):
        return {"I": "ı", "İ": "i"}.get(c, c.lower())
    return " ".join(w[:1] + "".join(kucuk(c) for c in w[1:]) for w in s.split(" "))


def _son_unlu(s):
    for c in reversed(s.lower()):
        if c in "aıoueiöü":
            return c
    return "e"


def soru(s):
    """Soru eki: 'Simitçi Kedi mi', 'Kumpir Ayı mı', 'Lokum Fil mi', 'Pide Timsah mı'."""
    return {"a": "mı", "ı": "mı", "o": "mu", "u": "mu", "e": "mi", "i": "mi", "ö": "mü", "ü": "mü"}[_son_unlu(s)]


def de(s):
    """Bulunma eki kesme işaretiyle: Kedi'de, Ayı'da, Martı'da, Balığı'nda, Tente'de, Kurbağa'da."""
    kalin = _son_unlu(s) in "aıou"
    if s.endswith(("Balığı", "Bardağı")):
        return s + ("'nda" if kalin else "'nde")
    sert = s[-1].lower() in "çfhkpsşt"
    return s + "'" + ("t" if sert else "d") + ("a" if kalin else "e")


def font(s, k="Black"):
    return ImageFont.truetype(FONT_DIR + f"InterDisplay-{k}.otf", int(s))


def yazi(d, xy, s, f, dolgu=(255, 255, 255), kenar=6, anchor="mm", kenar_renk=(0, 0, 0)):
    d.text(xy, s, font=f, fill=dolgu, anchor=anchor, stroke_width=kenar, stroke_fill=kenar_renk)


def kes(yol, boy):
    """Beyaz arka planı köşelerden doldurarak saydam yapar, karakteri kırpıp 'boy' kareye sığdırır."""
    im = (yol if isinstance(yol, Image.Image) else Image.open(yol)).convert("RGB")
    isaret = (255, 0, 255)
    for k in [(0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1)]:
        if im.getpixel(k) != isaret:
            ImageDraw.floodfill(im, k, isaret, thresh=38)
    a = np.array(im)
    alfa = np.where(np.all(a == isaret, axis=-1), 0, 255).astype(np.uint8)
    rgba = Image.fromarray(np.dstack([a, alfa]), "RGBA")
    rgba.putalpha(Image.fromarray(alfa).filter(ImageFilter.GaussianBlur(1.2)))
    rgba = rgba.crop(rgba.getbbox())
    rgba.thumbnail((boy, boy), Image.LANCZOS)
    return rgba


def yuz(yol, kutu, boy):
    """Karakter sayfasından yüz kesip yuvarlak spiker avatarı yapar."""
    im = Image.open(yol).convert("RGB").crop(kutu).resize((boy, boy), Image.LANCZOS)
    maske = Image.new("L", (boy, boy), 0)
    ImageDraw.Draw(maske).ellipse([0, 0, boy - 1, boy - 1], fill=255)
    out = Image.new("RGBA", (boy + 12, boy + 12), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse([0, 0, boy + 11, boy + 11], fill=(255, 210, 60))
    out.paste(im, (6, 6), maske)
    return out


# ───────────────────────── ses ─────────────────────────
class Ses:
    def __init__(self, sure):
        self.a = np.zeros(int(SR * (sure + 2)), np.float32)

    def ekle(self, t, dalga, kaz=1.0):
        i = int(t * SR); n = min(len(dalga), len(self.a) - i)
        if n > 0:
            self.a[i:i + n] += dalga[:n] * kaz

    @staticmethod
    def ton(f, sure, sonum=30, tip="sin"):
        t = np.arange(int(SR * sure)) / SR
        if tip == "kare":
            d = np.sign(np.sin(2 * np.pi * f * t)) * 0.5
        else:
            d = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
        return (d * np.exp(-t * sonum)).astype(np.float32)

    def kaydet(self, yol):
        a = np.tanh(self.a / max(1e-6, np.abs(self.a).max()) * 1.6) * 0.92
        with wave.open(yol, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((a * 32767).astype(np.int16).tobytes())


# ───────────────────────── maç ─────────────────────────
TAKIM_RENK = {"K": (215, 45, 45), "M": (35, 105, 225)}
TAKIM_AD = {"K": "KIRMIZI TENTE", "M": "MAVİ TENTE"}
TURLER = ("serbest", "odul", "dokunulmazlik", "duello", "bireysel", "final")


def gorsel(ad):
    yol = os.path.join(CARSI, ad)
    return yol if os.path.exists(yol) else None


def soluk(im):
    """Eleme adayı / veda eden için gri tonlu kopya."""
    g = im.convert("LA").convert("RGBA")
    g.putalpha(im.getchannel("A"))
    return g


def mac(cikti, esnaflar, tohum, tur="serbest", takimlar=None, ust="1. GÜN",
        kanca=None, arka_no=1,
        gecici="/tmp", cizme=False, konusmalar=None):
    """Bir Çarşı Ligi maçı.
    tur: serbest | odul | dokunulmazlik (takım maçı, takimlar=["K","M",...]) | duello | bireysel | final
    cizme=True: yalnızca fizik (hızlı), {"puan", "balon", ...} döner — aynı tohumla görüntülü oynatma birebir aynıdır.
    konusmalar: balon sırasına göre ses dizileri (SR, mono)."""
    assert tur in TURLER
    rnd = random.Random(tohum)
    n = len(esnaflar)
    kanca = kanca or (f"{n} ESNAF · 30 SANİYE", "SENCE KİM KAZANIR?")
    takim_modu = takimlar is not None
    SINIR = sinirlar(n)

    def kutu(x):
        return int(min(n - 1, max(0, np.searchsorted(SINIR, x, side="right") - 1)))

    adlar = [ESNAF[e][0] for e in esnaflar]
    tad = [tr_ad(a) for a in adlar]

    def dukkan(e):
        return gorsel(f"dukkan-{e}.png") or os.path.join(GORSEL, e + ".png")
    kutu_gen = int(min(min(SINIR[i + 1] - SINIR[i] for i in range(n)) - 8, 290))
    kesik = [kes(dukkan(e), kutu_gen) for e in esnaflar]
    buyuk = [kes(dukkan(e), 560) for e in esnaflar]
    veda_im = [kes(gorsel(f"veda-{e}.png"), 560) if gorsel(f"veda-{e}.png") else soluk(buyuk[i])
               for i, e in enumerate(esnaflar)]
    sevinc_im = [kes(gorsel(f"sevinc-{e}.png"), 560) if gorsel(f"sevinc-{e}.png") else buyuk[i]
                 for i, e in enumerate(esnaflar)]
    masa_im = Image.open(os.path.join(CARSI, "spiker-masasi.png")).convert("RGB")
    md = ImageDraw.Draw(masa_im)
    md.rounded_rectangle([262, 392, 762, 508], 14, fill=(150, 40, 40), outline=(255, 210, 60), width=5)
    md.text((512, 452), "ÇARŞI LİGİ", font=font(64), fill=(255, 235, 120), anchor="mm", stroke_width=3, stroke_fill=(60, 10, 10))
    masa = kes(masa_im, 680)
    MASA_X = (W - masa.width) // 2
    KONUSAN_X = {"L": MASA_X + masa.width * 0.30, "C": MASA_X + masa.width * 0.72}
    logo = kes(os.path.join(CARSI, "logo.png"), 600)
    kupa = kes(os.path.join(CARSI, "kupa.png"), 330)
    takim_logo = {}
    for t_, dosya in (("K", "takim-kirmizi.png"), ("M", "takim-mavi.png")):
        if gorsel(dosya):
            takim_logo[t_] = kes(gorsel(dosya), 300)

    OYUN, SON = 30.0, 6.5
    TOPLAM = OYUN + SON
    ses = Ses(TOPLAM)

    # çiviler (kaydırmalı ızgara)
    civi = []
    for sira in range(CIVI_SIRA):
        y = CIVI_Y0 + sira * CIVI_DY
        kay = 0 if sira % 2 == 0 else 54
        for k in range(11):
            x = 54 + kay + k * 108
            if 30 < x < W - 30:
                civi.append((x, y))
    civi = np.array(civi, float)
    tampon_y = [CIVI_Y0 + 2.5 * CIVI_DY, CIVI_Y0 + 6.5 * CIVI_DY]
    TAMPON_R = 40
    faz = [rnd.uniform(0, 2 * math.pi) for _ in range(2)]
    hiz = [rnd.uniform(0.9, 1.5) * rnd.choice([-1, 1]) for _ in range(2)]

    def tampon_x(t, i):
        return W / 2 + math.sin(t * hiz[i] + faz[i]) * (W / 2 - 160)

    dogum = []
    t = 0.3
    while t < OYUN - 4.0:
        dogum.append((t, 1))
        t += rnd.uniform(0.11, 0.24) * (1.2 - 0.5 * t / OYUN)
    for at in (9.0, 17.5, 24.0):
        dogum.append((at + rnd.uniform(-1, 1), 5))
    dogum.sort()

    pos = np.zeros((0, 2)); vel = np.zeros((0, 2)); deger = np.zeros(0, int)
    puan = [0] * n
    pop = [0.0] * n
    ucan = []
    lider_once = None
    balon = []                 # (kim, metin, bitiş, başlangıç)
    son_tik = 0.0
    sira_dogum = 0

    def takim_puan():
        tp = {"K": 0, "M": 0}
        if takim_modu:
            for i in range(n):
                tp[takimlar[i]] += puan[i]
        return tp

    def konus(kim, metin, t, sure=2.4, zorla=False):
        if not zorla and balon and balon[-1][2] > t + 0.6:
            return
        if balon and balon[-1][2] > t:
            balon[-1] = (balon[-1][0], balon[-1][1], t, balon[-1][3])
        balon.append((kim, metin, t + sure, t))

    CEMO_ESPRI = ["Abi ben de acıktım, bir simit alsam?", "Bu müşteriler nereye koşuyor böyle?",
                  "Ben olsam hepsinden birer tane alırdım!", "Abi kamerayı tutamıyorum, çok heyecanlı!",
                  "Esnafın bereketi bol olsun!"]
    ACILIS = {
        "serbest": "Çarşı Ligi başlıyor! Müşteriler geliyor!",
        "odul": "Ödül maçı başlıyor! Kırmızı mı, Mavi mi?",
        "dokunulmazlik": "Dokunulmazlık maçı! Kaybeden takımdan biri potaya gidecek!",
        "duello": "Eleme düellosu! Kaybeden çarşıya veda edecek!",
        "bireysel": "Bireysel dokunulmazlık! Herkes kendi dükkânı için!",
        "final": "Büyük final! Sezonun şampiyonu belli oluyor!",
    }
    konus("L", ACILIS[tur], 0.2, 2.8)

    # sabit arka plan
    arka = Image.open(os.path.join(CARSI, "carsi-aksam.png" if arka_no % 2 else "carsi-gunduz.png")).convert("RGB")
    arka = arka.resize((W, int(arka.height * W / arka.width)), Image.LANCZOS).crop((0, 0, W, H))
    bg = arka.copy()
    karart = Image.new("RGBA", (W, H), (10, 8, 25, 0)); kd = ImageDraw.Draw(karart)
    for y in range(H):
        kd.line([(0, y), (W, y)], fill=(10, 8, 25, 95 if y < DOGUM_Y - 40 else 150))
    bg.paste(karart, (0, 0), karart)
    bd = ImageDraw.Draw(bg)
    for (x, y) in civi:
        bd.ellipse([x - CIVI_R, y - CIVI_R, x + CIVI_R, y + CIVI_R], fill=(255, 210, 60), outline=(120, 80, 20), width=2)
    alt = Image.new("RGBA", (W, H - KUTU_Y + 10), (15, 10, 30, 175))
    bg.paste(alt, (0, KUTU_Y - 10), alt); bd = ImageDraw.Draw(bg)
    if takim_modu:
        for i in range(n):
            bd.rectangle([int(SINIR[i]) + 4, H - 200, int(SINIR[i + 1]) - 4, H - 188], fill=TAKIM_RENK[takimlar[i]])
    for i in range(1, n):
        x = int(SINIR[i])
        renk = (255, 210, 60) if takim_modu and takimlar[i] != takimlar[i - 1] else (255, 255, 255)
        bd.rectangle([x - (6 if renk != (255, 255, 255) else 4), KUTU_Y - 40, x + (6 if renk != (255, 255, 255) else 4), H - 210], fill=renk)
    yazi(bd, (W / 2, 62), f"ÇARŞI LİGİ · {ust}", font(56 if len(ust) < 22 else 46), dolgu=(255, 210, 60), kenar=7)
    bg.paste(masa, (MASA_X, MASA_Y), masa); bd = ImageDraw.Draw(bg)

    vid = os.path.join(gecici, f"carsi_v_{os.getpid()}.mp4"); wav = os.path.join(gecici, f"carsi_s_{os.getpid()}.wav")
    proc = None if cizme else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                                "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    for b in np.arange(0, OYUN, 0.5):
        ses.ekle(b, Ses.ton(60, 0.18, 18), 0.35)
        if int(b * 2) % 2:
            ses.ekle(b, (np.random.default_rng(int(b * 10)).standard_normal(int(SR * 0.05)) *
                         np.exp(-np.arange(int(SR * 0.05)) / SR * 60)).astype(np.float32), 0.08)
    notalar = [523, 587, 659, 784, 880, 988, 1046]

    def sonuc_hesapla():
        sira = sorted(range(n), key=lambda i: (-puan[i], i))
        r = {"sira": sira, "kazanan": sira[0]}
        if takim_modu:
            tp = takim_puan()
            kt = "K" if (tp["K"], 1) > (tp["M"], 0) else "M"   # eşitlikte Kırmızı (nadiren); ödül tablosunda görünür
            r["kazanan_takim"] = kt
            kaybeden = [i for i in range(n) if takimlar[i] != kt]
            r["eleme_adayi"] = min(kaybeden, key=lambda i: (puan[i], -i))
        elif tur == "bireysel":
            r["eleme_adayi"] = sira[-1]
        elif tur == "duello":
            r["veda"] = sira[-1]
        return r

    def ortala(im, resim, cy):
        im.paste(resim, (int(W / 2 - resim.width / 2), int(cy - resim.height / 2)), resim)

    def konfeti(d, kare, dt_, renkler=((255, 210, 60), (230, 60, 90), (90, 200, 240), (120, 220, 120))):
        rr = random.Random(kare)
        for _ in range(40):
            x, y = rr.uniform(0, W), (rr.uniform(0, H) + dt_ * 400) % H
            d.rectangle([x, y, x + 12, y + 22], fill=rr.choice(renkler))

    def bitis_karti(im, dt_, kare, son):
        p = min(1.0, dt_ / 0.6)
        kat = Image.new("RGBA", (W, H), (15, 10, 30, int(220 * p)))
        im.paste(kat, (0, 0), kat); d = ImageDraw.Draw(im)
        sc = 0.6 + 0.4 * p

        def olcek(r, k=1.0):
            return r.resize((max(1, int(r.width * sc * k)), max(1, int(r.height * sc * k))))
        if takim_modu:
            kt = son["kazanan_takim"]; tp = takim_puan()
            yazi(d, (W / 2, 150), "ÖDÜL MAÇI" if tur == "odul" else "DOKUNULMAZLIK", font(64), dolgu=(255, 210, 60), kenar=7)
            if kt in takim_logo:
                ortala(im, olcek(takim_logo[kt], 0.75), 330); d = ImageDraw.Draw(im)
            else:
                d.ellipse([W / 2 - 110, 230, W / 2 + 110, 450], fill=TAKIM_RENK[kt], outline=(255, 255, 255), width=6)
            yazi(d, (W / 2, 520), f"{TAKIM_AD[kt]} KAZANDI!", font(58), dolgu=TAKIM_RENK[kt], kenar=8, kenar_renk=(255, 255, 255))
            yazi(d, (W / 2, 595), f"KIRMIZI {tp['K']}  –  {tp['M']} MAVİ", font(40, "Bold"), kenar=5)
            if tur == "odul":
                kaz = [i for i in range(n) if takimlar[i] == kt]
                for j, i in enumerate(kaz):
                    r = olcek(sevinc_im[i], 0.5)
                    im.paste(r, (int(W * (j + 0.5) / len(kaz) - r.width / 2), int(900 - r.height / 2)), r)
                d = ImageDraw.Draw(im); konfeti(d, kare, dt_)
                yazi(d, (W / 2, 1640), "SIRADA DOKUNULMAZLIK VAR!", font(52), dolgu=(255, 210, 60), kenar=6)
                yazi(d, (W / 2, 1712), "TAKIMINI YORUMLARA YAZ: KIRMIZI MI MAVİ Mİ?", font(34, "Bold"), kenar=5)
            else:
                ea = son["eleme_adayi"]
                yazi(d, (W / 2, 720), "ELEME ADAYI", font(56), dolgu=(240, 70, 70), kenar=7)
                ortala(im, olcek(veda_im[ea] if gorsel(f"veda-{esnaflar[ea]}.png") else soluk(buyuk[ea]), 0.8), 1020)
                d = ImageDraw.Draw(im)
                yazi(d, (W / 2, 1300), adlar[ea], font(60), kenar=7)
                yazi(d, (W / 2, 1370), f"{puan[ea]} MÜŞTERİ · POTAYA GİDİYOR", font(38, "Bold"), dolgu=(240, 120, 120), kenar=5)
                yazi(d, (W / 2, 1640), "SENCE KİM KURTULMALI?", font(54), dolgu=(255, 210, 60), kenar=6)
                yazi(d, (W / 2, 1712), "KONSEYDE YORUMLAR KARAR VERECEK", font(38, "Bold"), kenar=5)
        elif tur == "duello":
            v = son["veda"]; k_ = son["kazanan"]
            yazi(d, (W / 2, 190), "ÇARŞIYA VEDA", font(90), dolgu=(240, 90, 90), kenar=8)
            ortala(im, olcek(veda_im[v], 1.0), 720); d = ImageDraw.Draw(im)
            yazi(d, (W / 2, 1060), adlar[v], font(62), kenar=7)
            yazi(d, (W / 2, 1130), f"{puan[v]} MÜŞTERİ", font(40, "Bold"), dolgu=(240, 120, 120), kenar=5)
            yazi(d, (W / 2, 1260), f"ÇARŞIDA KALAN: {adlar[k_]} ({puan[k_]})", font(40, "Bold"), dolgu=(255, 210, 60), kenar=5)
            yazi(d, (W / 2, 1650), "VEDA EDEN ESNAFA", font(50), dolgu=(255, 210, 60), kenar=6)
            yazi(d, (W / 2, 1720), "YORUMLARDA BİR MESAJ BIRAK", font(42, "Bold"), kenar=5)
        elif tur == "bireysel":
            k_ = son["kazanan"]; ea = son["eleme_adayi"]
            yazi(d, (W / 2, 150), "BİREYSEL DOKUNULMAZLIK", font(58), dolgu=(255, 210, 60), kenar=7)
            r = olcek(sevinc_im[k_], 0.62); im.paste(r, (int(W * 0.27 - r.width / 2), int(620 - r.height / 2)), r)
            r = olcek(soluk(buyuk[ea]), 0.62); im.paste(r, (int(W * 0.73 - r.width / 2), int(620 - r.height / 2)), r)
            d = ImageDraw.Draw(im)
            yazi(d, (W * 0.27, 920), "DOKUNULMAZ", font(44), dolgu=(120, 230, 120), kenar=5)
            yazi(d, (W * 0.27, 975), tad[k_], font(34, "Bold"), kenar=4)
            yazi(d, (W * 0.73, 920), "ELEME ADAYI", font(44), dolgu=(240, 90, 90), kenar=5)
            yazi(d, (W * 0.73, 975), tad[ea], font(34, "Bold"), kenar=4)
            sira = sorted(range(n), key=lambda i: (-puan[i], i))
            for n_, i in enumerate(sira):
                yazi(d, (W / 2, 1100 + n_ * 56), f"{n_ + 1}. {adlar[i]} · {puan[i]}", font(36, "Bold"), kenar=4)
            yazi(d, (W / 2, 1680), "SENCE KİM KURTULMALI? YORUMLARA YAZ", font(40, "Bold"), dolgu=(255, 210, 60), kenar=5)
        else:   # serbest / final
            sira = sorted(range(n), key=lambda i: (-puan[i], i))
            im.paste(kupa, ((W - kupa.width) // 2, 110), kupa)
            ortala(im, olcek(sevinc_im[sira[0]] if tur == "final" else buyuk[sira[0]], 1.0), 820)
            d = ImageDraw.Draw(im); konfeti(d, kare, dt_)
            yazi(d, (W / 2, 470), "SEZON ŞAMPİYONU" if tur == "final" else "GÜNÜN ŞAMPİYONU", font(54), dolgu=(255, 210, 60), kenar=6)
            yazi(d, (W / 2, 1170), adlar[sira[0]], font(66), kenar=7)
            yazi(d, (W / 2, 1245), f"{puan[sira[0]]} MÜŞTERİ", font(46, "Bold"), dolgu=(255, 210, 60), kenar=5)
            for n_, i in enumerate(sira[1:6]):
                yazi(d, (W / 2, 1340 + n_ * 58), f"{n_ + 2}. {adlar[i]} · {puan[i]}", font(38, "Bold"), kenar=4)
            yazi(d, (W / 2, 1700), "YENİ SEZON YAKINDA!" if tur == "final" else "FAVORİ ESNAFINI YORUMLARA YAZ",
                 font(44, "Bold"), dolgu=(255, 210, 60), kenar=5)

    kare_sayisi = int(TOPLAM * FPS)
    dt = 1 / FPS / ALT
    son = None
    for kare in range(kare_sayisi):
        t = kare / FPS
        oyunda = t < OYUN
        while sira_dogum < len(dogum) and dogum[sira_dogum][0] <= t:
            _, dg = dogum[sira_dogum]; sira_dogum += 1
            x = rnd.uniform(80, W - 80)
            pos = np.vstack([pos, [x, DOGUM_Y]]); vel = np.vstack([vel, [rnd.uniform(-60, 60), 0]])
            deger = np.append(deger, dg)
            if dg == 5:
                ses.ekle(t, Ses.ton(880, 0.5, 4, "kare"), 0.25)
                konus("C", "Altın müşteri! 5 puan değerinde!", t, 2.2)
        for _ in range(ALT):
            if not len(pos):
                break
            vel[:, 1] += G * dt
            pos += vel * dt
            sol = pos[:, 0] < TOP_R; pos[sol, 0] = TOP_R; vel[sol, 0] = np.abs(vel[sol, 0]) * 0.6
            sag = pos[:, 0] > W - TOP_R; pos[sag, 0] = W - TOP_R; vel[sag, 0] = -np.abs(vel[sag, 0]) * 0.6
            fark = pos[:, None, :] - civi[None, :, :]
            uz = np.linalg.norm(fark, axis=2)
            i_, j_ = np.nonzero(uz < TOP_R + CIVI_R)
            for i, j in zip(i_, j_):
                nrm = fark[i, j] / max(uz[i, j], 1e-6)
                pos[i] = civi[j] + nrm * (TOP_R + CIVI_R)
                vn = vel[i] @ nrm
                if vn < 0:
                    vel[i] -= 1.55 * vn * nrm
                    vel[i, 0] += rnd.uniform(-25, 25)
                    if t - son_tik > 0.045:
                        ses.ekle(t, Ses.ton(rnd.choice([1200, 1350, 1500]), 0.04, 70), 0.05); son_tik = t
            for ti, ty in enumerate(tampon_y):
                c = np.array([tampon_x(t, ti), ty])
                f = pos - c; u = np.linalg.norm(f, axis=1)
                for i in np.nonzero(u < TOP_R + TAMPON_R)[0]:
                    nrm = f[i] / max(u[i], 1e-6)
                    pos[i] = c + nrm * (TOP_R + TAMPON_R)
                    vn = vel[i] @ nrm
                    if vn < 0:
                        vel[i] -= 1.8 * vn * nrm
                        ses.ekle(t, Ses.ton(300, 0.08, 40), 0.12)
            if len(pos) > 1:
                f = pos[:, None, :] - pos[None, :, :]
                u = np.linalg.norm(f, axis=2) + np.eye(len(pos)) * 1e6
                for i, j in zip(*np.nonzero(np.triu(u < 2 * TOP_R))):
                    nrm = f[i, j] / max(u[i, j], 1e-6); ic = (2 * TOP_R - u[i, j]) / 2
                    pos[i] += nrm * ic; pos[j] -= nrm * ic
                    vr = (vel[i] - vel[j]) @ nrm
                    if vr < 0:
                        vel[i] -= vr * nrm * 0.9; vel[j] += vr * nrm * 0.9
            for b in range(1, n):
                bx = SINIR[b]
                yak = (np.abs(pos[:, 0] - bx) < TOP_R + 4) & (pos[:, 1] > KUTU_Y - 40)
                for i in np.nonzero(yak)[0]:
                    yon = 1 if pos[i, 0] > bx else -1
                    pos[i, 0] = bx + yon * (TOP_R + 4); vel[i, 0] = yon * abs(vel[i, 0]) * 0.5
            np.clip(vel, -1400, 1400, out=vel)
        if len(pos):
            giren = pos[:, 1] > KUTU_Y + 20
            for i in np.nonzero(giren)[0]:
                b = kutu(pos[i, 0])
                if oyunda:
                    puan[b] += int(deger[i]); pop[b] = 1.0
                    ucan.append([pos[i, 0], KUTU_Y - 10, f"+{deger[i]}", (255, 210, 60) if deger[i] == 5 else (255, 255, 255), 1.0])
                    ses.ekle(t, Ses.ton(notalar[b % len(notalar)] * (2 if deger[i] == 5 else 1), 0.18, 14), 0.22)
            pos, vel, deger = pos[~giren], vel[~giren], deger[~giren]

        # ── yorumlar
        if takim_modu:
            tp = takim_puan()
            lider = None if tp["K"] == tp["M"] else ("K" if tp["K"] > tp["M"] else "M")
            if oyunda and lider and lider != lider_once and abs(tp["K"] - tp["M"]) >= 3 and t < OYUN - 5.5 and sum(puan) > 6:
                konus("L" if rnd.random() < 0.5 else "C",
                      rnd.choice([f"{tr_ad(TAKIM_AD[lider])} öne geçti!", f"Liderlik {de(tr_ad(TAKIM_AD[lider]))}!"]), t, 2.2, zorla=True)
                lider_once = lider
            if oyunda and 3 < t < OYUN - 5.5 and (not balon or balon[-1][2] < t - 1.2) and sum(puan) > 3:
                secim = rnd.random()
                fark_ = abs(tp["K"] - tp["M"])
                if fark_ <= 3 and secim < 0.45:
                    konus("L", f"Takımlar arasında fark sadece {fark_}! Kıyasıya mücadele!", t)
                elif tur == "dokunulmazlik" and secim < 0.75 and lider:
                    geri = "M" if lider == "K" else "K"
                    en_az = min((i for i in range(n) if takimlar[i] == geri), key=lambda i: puan[i])
                    konus("L", f"{de(tr_ad(TAKIM_AD[geri]))} en az müşteri {de(tad[en_az])}, potaya yaklaşıyor!", t)
                else:
                    konus("C", rnd.choice(CEMO_ESPRI), t)
        else:
            lider = max(range(n), key=lambda i: puan[i]) if max(puan) > 0 else None
            sirali = sorted(puan, reverse=True)
            if (oyunda and lider is not None and lider != lider_once and sum(puan) > 6 and sirali[0] - sirali[1] >= 2
                    and t < OYUN - 5.5):
                konus("L" if rnd.random() < 0.5 else "C",
                      rnd.choice([f"{tad[lider]} öne geçti!", f"Liderlik değişti: {tad[lider]}!",
                                  f"{tad[lider]} dükkânı doldurdu!"]), t, 2.2, zorla=True)
                lider_once = lider
            if oyunda and 3 < t < OYUN - 5.5 and (not balon or balon[-1][2] < t - 1.2) and sum(puan) > 3:
                s_ = sorted(range(n), key=lambda i: -puan[i])
                fark_ = puan[s_[0]] - puan[s_[1]]
                secim = rnd.random()
                if fark_ <= 2 and secim < 0.5:
                    konus("L", f"Fark sadece {fark_}! {tad[s_[0]]} ile {tad[s_[1]]} kafa kafaya!"
                          if fark_ else f"Eşitlik! {tad[s_[0]]} ile {tad[s_[1]]} kafa kafaya!", t)
                elif secim < 0.75 and n > 2 and puan[s_[-2]] - puan[s_[-1]] >= 3:
                    tehlike = {"duello": "çarşıya veda etmek üzere", "bireysel": "potaya yaklaşıyor"}.get(tur, "geride kaldı")
                    konus("L", f"{tad[s_[-1]]} {tehlike}, toparlanabilecek mi?", t)
                elif tur == "duello" and secim < 0.75 and fark_ >= 3:
                    konus("L", f"{tad[s_[1]]} geride, çarşıya veda etmek üzere!", t)
                else:
                    konus("C", rnd.choice(CEMO_ESPRI), t)
        if abs(t - (OYUN - 5)) < 1 / FPS / 2:
            konus("L", "Son 5 saniye! Son müşteriler!", t, 2.5, zorla=True)
            ses.ekle(t, Ses.ton(660, 0.3, 6, "kare"), 0.2)
        if abs(t - OYUN) < 1 / FPS / 2:
            son = sonuc_hesapla()
            if tur == "odul":
                metin = f"Ödül {tr_ad(TAKIM_AD[son['kazanan_takim']])}'nin!"
            elif tur == "dokunulmazlik":
                metin = f"Dokunulmazlık {tr_ad(TAKIM_AD[son['kazanan_takim']])}'nin! Eleme adayı: {tad[son['eleme_adayi']]}!"
            elif tur == "duello":
                metin = f"{tad[son['veda']]} çarşıya veda ediyor!"
            elif tur == "bireysel":
                metin = f"{tad[son['kazanan']]} dokunulmaz! Eleme adayı: {tad[son['eleme_adayi']]}!"
            elif tur == "final":
                metin = f"Sezonun şampiyonu: {tad[son['kazanan']]}!"
            else:
                metin = f"Bugünün esnafı: {tad[son['kazanan']]}!"
            konus("C" if tur in ("serbest", "odul") else "L", metin, t, 5.0, zorla=True)
            for n_, f_ in enumerate([523, 659, 784, 1046] if tur != "duello" else [392, 349, 311, 262]):
                ses.ekle(t + n_ * 0.16, Ses.ton(f_, 0.5, 5, "kare"), 0.3)

        if cizme:
            continue
        # ── çizim
        im = bg.copy(); d = ImageDraw.Draw(im)
        for ti, ty in enumerate(tampon_y):
            x = tampon_x(t, ti)
            d.ellipse([x - TAMPON_R, ty - TAMPON_R, x + TAMPON_R, ty + TAMPON_R], fill=(230, 60, 90), outline=(255, 255, 255), width=5)
        for (x, y), dg in zip(pos, deger):
            if dg == 5:
                d.ellipse([x - TOP_R - 5, y - TOP_R - 5, x + TOP_R + 5, y + TOP_R + 5], fill=(255, 205, 40), outline=(255, 255, 255), width=3)
                yazi(d, (x, y + 1), "5", font(22), kenar=2)
            else:
                d.ellipse([x - TOP_R, y - TOP_R, x + TOP_R, y + TOP_R], fill=(250, 235, 215), outline=(60, 40, 30), width=2)
                d.ellipse([x - 6, y - 4, x - 2, y], fill=(30, 30, 30)); d.ellipse([x + 2, y - 4, x + 6, y], fill=(30, 30, 30))
        if takim_modu:   # takım skor tabelası
            tp = takim_puan()
            for t_, x0 in (("K", 150), ("M", W / 2 + 20)):
                d.rounded_rectangle([x0, 596, x0 + 390, 650], 27, fill=TAKIM_RENK[t_], outline=(255, 255, 255), width=3)
                yazi(d, (x0 + 195, 623), f"{TAKIM_AD[t_]}  {tp[t_]}", font(30), kenar=3)
        lider_i = max(range(n), key=lambda i: puan[i]) if max(puan) > 0 else None
        for i in range(n):
            cx = (SINIR[i] + SINIR[i + 1]) / 2
            s = 1 + 0.18 * pop[i]; pop[i] = max(0.0, pop[i] - 0.12)
            k = kesik[i]
            if s != 1:
                k = k.resize((int(k.width * s), int(k.height * s)))
            im.paste(k, (int(cx - k.width / 2), int(DUKKAN_Y + kutu_gen / 2 - k.height / 2)), k)
            if i == lider_i and not takim_modu:
                yazi(d, (cx, KUTU_Y - 58), "LİDER", font(28), dolgu=(255, 210, 60), kenar=4)
            renk = TAKIM_RENK[takimlar[i]] if takim_modu else None
            yazi(d, (cx, H - 155), str(puan[i]), font(72 if n <= 5 else 62),
                 dolgu=(255, 210, 60) if (i == lider_i and not takim_modu) else (255, 255, 255), kenar=6,
                 kenar_renk=renk or (0, 0, 0))
            for sat_no, sat in enumerate(adlar[i].split(" ", 1)):
                yazi(d, (cx, H - 88 + sat_no * 32), sat, font(26 if n <= 5 else 22, "Bold"), kenar=4)
        for u in ucan:
            yazi(d, (u[0], u[1] - (1 - u[4]) * 90), u[2], font(40), dolgu=u[3], kenar=4)
            u[4] -= 0.05
        ucan = [u for u in ucan if u[4] > 0]
        aktif = [b for b in balon if b[2] > t and b[2] - t < 6] if t < OYUN else []
        if aktif:
            kim, metin, _, _ = aktif[-1]
            x0, x1, y0, y1 = 50, W - 50, BALON_Y, BALON_Y + 84
            ux = KONUSAN_X[kim]
            d.polygon([(ux - 26, y0 + 4), (ux + 26, y0 + 4), (ux, y0 - 34)], fill=(255, 255, 255))
            d.rounded_rectangle([x0, y0, x1, y1], 26, fill=(255, 255, 255), outline=(255, 210, 60), width=4)
            tam = ("LEVENT: " if kim == "L" else "CEMO: ") + metin
            f = font(36 if len(tam) < 40 else 31 if len(tam) < 50 else 26 if len(tam) < 62 else 22, "Bold")
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), tam, font=f, fill=(20, 20, 30), anchor="mm")
        if t < 2.5:   # açılış kancası
            a = 1 - max(0, t - 2.0) / 0.5
            kat = Image.new("RGBA", (W, 900), (0, 0, 0, int(150 * a)))
            im.paste(kat, (0, 560), kat)
            lg = logo.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v * a)))
            im.paste(lg, ((W - lg.width) // 2, 600), lg); d = ImageDraw.Draw(im)
            yazi(d, (W / 2, 1270), kanca[0], font(60 if len(kanca[0]) < 24 else 48), dolgu=(255, 210, 60), kenar=7)
            yazi(d, (W / 2, 1352), kanca[1], font(60 if len(kanca[1]) < 24 else 48), kenar=7)
        if t >= OYUN:
            bitis_karti(im, t - OYUN, kare, son)
        proc.stdin.write(im.tobytes())

    if cizme:
        son = son or sonuc_hesapla()
        return _sonuc(esnaflar, puan, son, takimlar, balon)
    if konusmalar:
        for (kim, metin, bitis, bas_), dalga in zip(balon, konusmalar):
            if dalga is not None and len(dalga):
                ses.ekle(bas_ + 0.05, np.asarray(dalga, np.float32), 1.0)
    proc.stdin.close(); proc.wait()
    ses.kaydet(wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", cikti], check=True)
    for p in (vid, wav):
        if os.path.exists(p):
            os.remove(p)
    sonuc = _sonuc(esnaflar, puan, son, takimlar, balon)
    print(json.dumps({k: v for k, v in sonuc.items() if k != "balon"}, ensure_ascii=False))
    return sonuc


def _sonuc(esnaflar, puan, son, takimlar, balon):
    r = {"esnaflar": esnaflar, "puan": dict(zip(esnaflar, puan)), "kazanan": esnaflar[son["kazanan"]],
         "sira": [esnaflar[i] for i in son["sira"]], "balon": balon}
    if takimlar:
        tp = {"K": 0, "M": 0}
        for e, t_, p in zip(esnaflar, takimlar, puan):
            tp[t_] += p
        r["takim_puan"] = tp
        r["kazanan_takim"] = son["kazanan_takim"]
    if "eleme_adayi" in son:
        r["eleme_adayi"] = esnaflar[son["eleme_adayi"]]
    if "veda" in son:
        r["veda"] = esnaflar[son["veda"]]
    return r


if __name__ == "__main__":
    # deneme: python3 carsi.py <tür> <tohum> <çıktı.mp4> esnaf1 esnaf2 ... [--takim KKKMMM]
    tur, tohum, cikti = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    arg = sys.argv[4:]
    takimlar = None
    if "--takim" in arg:
        k = arg.index("--takim"); takimlar = list(arg[k + 1]); arg = arg[:k] + arg[k + 2:]
    mac(cikti, arg, tohum, tur=tur, takimlar=takimlar, ust="DENEME")
