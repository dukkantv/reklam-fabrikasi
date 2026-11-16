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
UST = 380                 # oyun alanının üstü
KUTU_Y = 1395             # müşteri bu çizgiyi geçince dükkâna sayılır
DUKKAN_Y = 1450           # karakterlerin üst kenarı
N = 5
# Kenar dükkânlar duvardan sekenleri, orta dükkân çivilerden ortaya toplananları fazla alıyordu.
# 40 maçlık testlerle ölçülen ortalamalara göre ayarlanmış dükkân genişlikleri (soldan sağa, simetrik)
GENISLIK = [0.856, 1.035, 0.975, 1.035, 0.856]
SINIR = np.cumsum([0] + [W * g / sum(GENISLIK) for g in GENISLIK])


def kutu(x):
    return int(min(N - 1, max(0, np.searchsorted(SINIR, x, side="right") - 1)))
TOP_R, CIVI_R = 18, 9
G = 1500.0


def font(s, k="Black"):
    return ImageFont.truetype(FONT_DIR + f"InterDisplay-{k}.otf", int(s))


def yazi(d, xy, s, f, dolgu=(255, 255, 255), kenar=6, anchor="mm", kenar_renk=(0, 0, 0)):
    d.text(xy, s, font=f, fill=dolgu, anchor=anchor, stroke_width=kenar, stroke_fill=kenar_renk)


def kes(yol, boy):
    """Beyaz arka planı köşelerden doldurarak saydam yapar, karakteri kırpıp 'boy' kareye sığdırır."""
    im = Image.open(yol).convert("RGB")
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
def mac(gun, tohum, cikti, esnaflar=None, gecici="/tmp", cizme=False):
    rnd = random.Random(tohum)
    esnaflar = esnaflar or rnd.sample(sorted(ESNAF), N)
    adlar = [ESNAF[e][0] for e in esnaflar]
    renkler = [ESNAF[e][1] for e in esnaflar]
    kesik = [kes(os.path.join(GORSEL, e + ".png"), 190) for e in esnaflar]
    buyuk = [kes(os.path.join(GORSEL, e + ".png"), 620) for e in esnaflar]
    lev = yuz(os.path.join(KOK, "karakterler", "levent.jpg"), (560, 960, 1060, 1460), 120)
    cem = yuz(os.path.join(KOK, "karakterler", "cemo.jpg"), (580, 880, 1080, 1380), 120)

    OYUN, SON = 30.0, 6.0
    TOPLAM = OYUN + SON
    ses = Ses(TOPLAM)

    # çiviler (kaydırmalı ızgara)
    civi = []
    for sira in range(10):
        y = UST + 150 + sira * 86
        kay = 0 if sira % 2 == 0 else 54
        for k in range(11):
            x = 54 + kay + k * 108
            if 30 < x < W - 30:
                civi.append((x, y))
    civi = np.array(civi, float)
    tampon_y = [UST + 150 + 3.5 * 86, UST + 150 + 7.5 * 86]
    TAMPON_R = 40

    # her maçta farklı faz ve hız: tamponlar hep aynı tarafa itmesin (adillik)
    faz = [rnd.uniform(0, 2 * math.pi) for _ in range(2)]
    hiz = [rnd.uniform(0.9, 1.5) * rnd.choice([-1, 1]) for _ in range(2)]

    def tampon_x(t, i):
        return W / 2 + math.sin(t * hiz[i] + faz[i]) * (W / 2 - 160)

    # müşteri programı: zamanla hızlanan yağmur + altın müşteriler
    dogum = []
    t = 0.3
    while t < OYUN - 4.0:
        dogum.append((t, 1))
        t += rnd.uniform(0.11, 0.24) * (1.2 - 0.5 * t / OYUN)
    for at in (9.0, 17.5, 24.0):
        dogum.append((at + rnd.uniform(-1, 1), 5))
    dogum.sort()

    pos = np.zeros((0, 2)); vel = np.zeros((0, 2)); deger = np.zeros(0, int)
    puan = [0] * N
    pop = [0.0] * N            # dükkân zıplama animasyonu
    ucan = []                  # (x, y, metin, renk, kalan)
    lider_once = None
    balon = []                 # (kim, metin, bitiş)
    son_tik = 0.0
    sira_dogum = 0

    def konus(kim, metin, t, sure=2.4, zorla=False):
        if not zorla and balon and balon[-1][2] > t + 0.6:
            return
        if balon and balon[-1][2] > t:
            balon[-1] = (balon[-1][0], balon[-1][1], t)   # eski balonu kapat
        balon.append((kim, metin, t + sure))

    CEMO_ESPRI = ["Abi ben de acıktım, bir simit alsam?", "Bu müşteriler nereye koşuyor böyle?",
                  "Ben olsam hepsinden birer tane alırdım!", "Abi kamerayı tutamıyorum, çok heyecanlı!",
                  "Esnafın bereketi bol olsun!"]

    konus("L", "Çarşı Ligi başlıyor! Müşteriler geliyor!", 0.2, 2.6)

    # sabit arka plan
    bg = Image.new("RGB", (W, H)); bd = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        bd.line([(0, y), (W, y)], fill=(int(40 + 30 * k), int(24 + 10 * k), int(54 + 20 * k)))
    # tente şeritleri (çarşı havası)
    for i in range(0, W, 90):
        bd.polygon([(i, 0), (i + 90, 0), (i + 90, 50), (i + 45, 70), (i, 50)],
                   fill=(220, 60, 60) if (i // 90) % 2 == 0 else (245, 240, 230))
    for (x, y) in civi:
        bd.ellipse([x - CIVI_R, y - CIVI_R, x + CIVI_R, y + CIVI_R], fill=(255, 210, 60), outline=(120, 80, 20), width=2)
    for i in range(1, N):
        x = int(SINIR[i])
        bd.rectangle([x - 4, KUTU_Y - 40, x + 4, H - 260], fill=(255, 255, 255))
    for i in range(N):
        x0, x1 = int(SINIR[i]) + 6, int(SINIR[i + 1]) - 6
        bd.rounded_rectangle([x0, DUKKAN_Y - 10, x1, H - 270], 18, fill=tuple(int(c * 0.45) for c in renkler[i]))
    yazi(bd, (W / 2, 130), "ÇARŞI LİGİ", font(92), dolgu=(255, 210, 60), kenar=8)
    yazi(bd, (W / 2, 215), f"{gun}. GÜN · KİM DAHA ÇOK MÜŞTERİ KAPAR?", font(38, "Bold"), kenar=4)

    vid = os.path.join(gecici, "carsi_v.mp4"); wav = os.path.join(gecici, "carsi_s.wav")
    proc = None if cizme else subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)

    # davul altlığı (enerji)
    for b in np.arange(0, OYUN, 0.5):
        ses.ekle(b, Ses.ton(60, 0.18, 18), 0.35)
        if int(b * 2) % 2:
            ses.ekle(b, (np.random.default_rng(int(b * 10)).standard_normal(int(SR * 0.05)) *
                         np.exp(-np.arange(int(SR * 0.05)) / SR * 60)).astype(np.float32), 0.08)

    kare_sayisi = int(TOPLAM * FPS)
    dt = 1 / FPS / ALT
    for kare in range(kare_sayisi):
        t = kare / FPS
        oyunda = t < OYUN
        # ── doğum
        while sira_dogum < len(dogum) and dogum[sira_dogum][0] <= t:
            _, dg = dogum[sira_dogum]; sira_dogum += 1
            x = rnd.uniform(80, W - 80)
            pos = np.vstack([pos, [x, UST + 20]]); vel = np.vstack([vel, [rnd.uniform(-60, 60), 0]])
            deger = np.append(deger, dg)
            if dg == 5:
                ses.ekle(t, Ses.ton(880, 0.5, 4, "kare"), 0.25)
                konus("C", "Altın müşteri! 5 puan değerinde!", t, 2.2)
        # ── fizik
        for _ in range(ALT):
            if not len(pos):
                break
            vel[:, 1] += G * dt
            pos += vel * dt
            # duvarlar
            sol = pos[:, 0] < TOP_R; pos[sol, 0] = TOP_R; vel[sol, 0] = np.abs(vel[sol, 0]) * 0.6
            sag = pos[:, 0] > W - TOP_R; pos[sag, 0] = W - TOP_R; vel[sag, 0] = -np.abs(vel[sag, 0]) * 0.6
            # çiviler
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
            # hareketli tamponlar
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
            # müşteriler birbirine çarpar
            if len(pos) > 1:
                f = pos[:, None, :] - pos[None, :, :]
                u = np.linalg.norm(f, axis=2) + np.eye(len(pos)) * 1e6
                for i, j in zip(*np.nonzero(np.triu(u < 2 * TOP_R))):
                    nrm = f[i, j] / max(u[i, j], 1e-6); ic = (2 * TOP_R - u[i, j]) / 2
                    pos[i] += nrm * ic; pos[j] -= nrm * ic
                    vr = (vel[i] - vel[j]) @ nrm
                    if vr < 0:
                        vel[i] -= vr * nrm * 0.9; vel[j] += vr * nrm * 0.9
            # bölme duvarları (kutuların arası)
            for b in range(1, N):
                bx = SINIR[b]
                yak = (np.abs(pos[:, 0] - bx) < TOP_R + 4) & (pos[:, 1] > KUTU_Y - 40)
                for i in np.nonzero(yak)[0]:
                    yon = 1 if pos[i, 0] > bx else -1
                    pos[i, 0] = bx + yon * (TOP_R + 4); vel[i, 0] = yon * abs(vel[i, 0]) * 0.5
            np.clip(vel, -1400, 1400, out=vel)
        # ── sayma
        if len(pos):
            giren = pos[:, 1] > KUTU_Y + 20
            for i in np.nonzero(giren)[0]:
                b = kutu(pos[i, 0])
                if oyunda:
                    puan[b] += int(deger[i]); pop[b] = 1.0
                    ucan.append([pos[i, 0], KUTU_Y - 10, f"+{deger[i]}", (255, 210, 60) if deger[i] == 5 else (255, 255, 255), 1.0])
                    ses.ekle(t, Ses.ton([523, 587, 659, 784, 880][b] * (2 if deger[i] == 5 else 1), 0.18, 14), 0.22)
            pos, vel, deger = pos[~giren], vel[~giren], deger[~giren]
        # ── yorumlar: liderlik değişimi, son saniyeler
        lider = max(range(N), key=lambda i: puan[i]) if max(puan) > 0 else None
        sirali = sorted(puan, reverse=True)
        if (oyunda and lider is not None and lider != lider_once and sum(puan) > 6 and sirali[0] - sirali[1] >= 2
                and t < OYUN - 5.5):
            kim = "L" if rnd.random() < 0.5 else "C"
            konus(kim, rnd.choice([f"{adlar[lider].title()} öne geçti!", f"Liderlik değişti: {adlar[lider].title()}!",
                                   f"{adlar[lider].title()} dükkânı doldurdu!"]), t, 2.2, zorla=True)
            lider_once = lider
        # sessiz kalınmasın: 3 sn boşlukta yarış yorumu ya da Cemo esprisi
        if oyunda and 3 < t < OYUN - 5.5 and (not balon or balon[-1][2] < t - 1.2) and sum(puan) > 3:
            s_ = sorted(range(N), key=lambda i: -puan[i])
            fark_ = puan[s_[0]] - puan[s_[1]]
            secim = rnd.random()
            if fark_ <= 2 and secim < 0.5:
                konus("L", f"Fark sadece {fark_}! {adlar[s_[0]].title()} ile {adlar[s_[1]].title()} kafa kafaya!"
                      if fark_ else f"Eşitlik! {adlar[s_[0]].title()} ile {adlar[s_[1]].title()} kafa kafaya!", t)
            elif secim < 0.75 and puan[s_[-2]] - puan[s_[-1]] >= 3:
                konus("L", f"{adlar[s_[-1]].title()} geride kaldı, toparlanabilecek mi?", t)
            else:
                konus("C", rnd.choice(CEMO_ESPRI), t)
        if abs(t - (OYUN - 5)) < 1 / FPS / 2:
            konus("L", "Son 5 saniye! Son müşteriler!", t, 2.5, zorla=True)
            ses.ekle(t, Ses.ton(660, 0.3, 6, "kare"), 0.2)
        if abs(t - OYUN) < 1 / FPS / 2:
            k = max(range(N), key=lambda i: puan[i])
            konus("C", f"Bugünün esnafı: {adlar[k].title()}!", t, 4.0)
            for n_, f_ in enumerate([523, 659, 784, 1046]):
                ses.ekle(t + n_ * 0.14, Ses.ton(f_, 0.5, 5, "kare"), 0.3)

        # ── çizim
        if cizme:
            continue
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
        # dükkânlar
        lider = max(range(N), key=lambda i: puan[i]) if max(puan) > 0 else None
        for i in range(N):
            cx = (SINIR[i] + SINIR[i + 1]) / 2
            s = 1 + 0.18 * pop[i]; pop[i] = max(0.0, pop[i] - 0.12)
            k = kesik[i]
            if s != 1:
                k = k.resize((int(k.width * s), int(k.height * s)))
            im.paste(k, (int(cx - k.width / 2), int(DUKKAN_Y + 105 - k.height / 2)), k)
            if i == lider:
                yazi(d, (cx, DUKKAN_Y - 20), "LİDER", font(26), dolgu=(255, 210, 60), kenar=4)
            yazi(d, (cx, H - 228), str(puan[i]), font(70), dolgu=(255, 210, 60) if i == lider else (255, 255, 255), kenar=6)
            for sat_no, sat in enumerate(adlar[i].split(" ", 1)):
                yazi(d, (cx, H - 160 + sat_no * 34), sat, font(28, "Bold"), kenar=4)
        for u in ucan:
            yazi(d, (u[0], u[1] - (1 - u[4]) * 90), u[2], font(40), dolgu=u[3], kenar=4)
            u[4] -= 0.05
        ucan = [u for u in ucan if u[4] > 0]
        # spikerler ve konuşma balonu
        im.paste(lev, (18, 250), lev); im.paste(cem, (W - 18 - cem.width, 250), cem)
        yazi(d, (18 + lev.width / 2, 250 + lev.height + 8), "LEVENT", font(22, "Bold"), kenar=3)
        yazi(d, (W - 18 - cem.width / 2, 250 + cem.height + 8), "CEMO", font(22, "Bold"), kenar=3)
        aktif = [b for b in balon if b[2] > t and b[2] - t < 6]
        if aktif:
            kim, metin, _ = aktif[-1]
            x0, x1 = 170, W - 170
            d.rounded_rectangle([x0, 262, x1, 362], 24, fill=(255, 255, 255))
            uc = (x0 - 22, 300) if kim == "L" else (x1 + 22, 300)
            kok = (x0 + 6, 290, x0 + 6, 330) if kim == "L" else (x1 - 6, 290, x1 - 6, 330)
            d.polygon([uc, (kok[0], kok[1]), (kok[2], kok[3])], fill=(255, 255, 255))
            f = font(34 if len(metin) < 32 else 29 if len(metin) < 40 else 25, "Bold")
            d.text(((x0 + x1) / 2, 312), metin, font=f, fill=(20, 20, 30), anchor="mm")
        # açılış kancası: ilk 2.5 sn büyük soru
        if t < 2.5:
            a = 1 - max(0, t - 2.0) / 0.5
            kat = Image.new("RGBA", (W, 300), (0, 0, 0, int(170 * a)))
            im.paste(kat, (0, 800), kat)
            yazi(d, (W / 2, 900), "5 ESNAF · 30 SANİYE", font(64), dolgu=(255, 210, 60), kenar=7)
            yazi(d, (W / 2, 990), "SENCE KİM KAZANIR?", font(64), kenar=7)
        # bitiş kartı
        if t >= OYUN:
            p = min(1.0, (t - OYUN) / 0.6)
            kat = Image.new("RGBA", (W, H), (15, 10, 30, int(215 * p)))
            im.paste(kat, (0, 0), kat); d = ImageDraw.Draw(im)
            sira = sorted(range(N), key=lambda i: -puan[i])
            k = buyuk[sira[0]]
            sc = 0.6 + 0.4 * p
            kk = k.resize((int(k.width * sc), int(k.height * sc)))
            im.paste(kk, (int(W / 2 - kk.width / 2), int(820 - kk.height / 2)), kk)
            rr = random.Random(kare)
            for _ in range(40):
                x, y = rr.uniform(0, W), (rr.uniform(0, H) + (t - OYUN) * 400) % H
                d.rectangle([x, y, x + 12, y + 22], fill=rr.choice([(255, 210, 60), (230, 60, 90), (90, 200, 240), (120, 220, 120)]))
            yazi(d, (W / 2, 330), "ÇARŞININ ESNAFI", font(80), dolgu=(255, 210, 60), kenar=8)
            yazi(d, (W / 2, 420), f"{gun}. GÜN", font(46, "Bold"), kenar=5)
            yazi(d, (W / 2, 1170), adlar[sira[0]], font(66), kenar=7)
            yazi(d, (W / 2, 1245), f"{puan[sira[0]]} MÜŞTERİ", font(46, "Bold"), dolgu=(255, 210, 60), kenar=5)
            for n_, i in enumerate(sira[1:]):
                yazi(d, (W / 2, 1340 + n_ * 58), f"{n_ + 2}. {adlar[i]} · {puan[i]}", font(38, "Bold"), kenar=4)
            yazi(d, (W / 2, 1640), "YARIN KİM KAZANIR?", font(54), dolgu=(255, 210, 60), kenar=6)
            yazi(d, (W / 2, 1710), "FAVORİ ESNAFINI YORUMLARA YAZ", font(40, "Bold"), kenar=5)
        proc.stdin.write(im.tobytes())
    if cizme:
        return puan
    proc.stdin.close(); proc.wait()
    ses.kaydet(wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", cikti], check=True)
    sonuc = {"gun": gun, "esnaflar": esnaflar, "puan": dict(zip(esnaflar, puan)),
             "kazanan": esnaflar[max(range(N), key=lambda i: puan[i])]}
    print(json.dumps(sonuc, ensure_ascii=False))
    return sonuc


if __name__ == "__main__":
    gun, tohum, cikti = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    mac(gun, tohum, cikti, sys.argv[4:9] or None)
