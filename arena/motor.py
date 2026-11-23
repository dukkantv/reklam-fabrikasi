# 81 İl Turnuvası — oyun motoru. Fizik + çizim + ses tamamen kodla, ücretsiz (numpy, Pillow, ffmpeg).
# mac_oyna(...) bir maçı oynatır, 9:16 video üretir, tur atlayan plakaları döndürür.
import colorsys, math, os, random, subprocess, wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from iller import AD, ILLER

W, H, FPS, SUB = 1080, 1920, 30, 6
CX, CY, R = 540, 1010, 465
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
SR = 44100
SARI, KIRMIZI = (255, 210, 60), (255, 85, 85)

# Oyun türleri: boşluklar (açı, dönüş hızı rad/sn), yerçekimi dönüşü, kurallar
MODLAR = {
    "kacis": {"ad": "ÇEMBERDEN KAÇIŞ", "kural": "Çemberden kaçan elenir!",
              "bosluklar": [(0.0, 0.9)], "g_donus": 0.0, "bosluk0": 17, "buyume": 0.55},
    "cift_kapi": {"ad": "ÇİFT KAPI", "kural": "İki kapı ters dönüyor. Kaçan elenir!",
                  "bosluklar": [(0.0, 0.8), (math.pi, -1.1)], "g_donus": 0.0, "bosluk0": 12, "buyume": 0.35},
    "ters_dunya": {"ad": "TERS DÜNYA", "kural": "Yerçekimi dönüyor. Alttaki kapıdan düşen elenir!",
                   "bosluklar": [(math.pi / 2, 0.0)], "g_donus": 0.55, "bosluk0": 22, "buyume": 0.6},
}


def font(s, k="Black"):
    return ImageFont.truetype(FONT_DIR + f"InterDisplay-{k}.otf", s)


def renk(plaka):
    i = int(plaka)
    h = (i * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.70 if i % 2 else 0.85, 0.98)
    return int(r * 255), int(g * 255), int(b * 255)


def yazi(d, xy, s, f, dolgu=(255, 255, 255), kenar=6, anchor="mm"):
    d.text(xy, s, font=f, fill=dolgu, anchor=anchor, stroke_width=kenar, stroke_fill=(0, 0, 0))


class Ses:
    def __init__(self, sure):
        self.a = np.zeros(int(SR * (sure + 3)), np.float32)

    def ekle(self, t, dalga, kaz=1.0):
        i = int(t * SR); n = min(len(dalga), len(self.a) - i)
        if n > 0:
            self.a[i:i + n] += dalga[:n] * kaz

    @staticmethod
    def blip(f, sure=0.07):
        t = np.arange(int(SR * sure)) / SR
        return (np.sin(2 * np.pi * f * t) * np.exp(-t * 40)).astype(np.float32)

    @staticmethod
    def pop():
        t = np.arange(int(SR * 0.35)) / SR
        f = 520 * np.exp(-t * 6)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)).astype(np.float32)

    @staticmethod
    def kick():
        t = np.arange(int(SR * 0.18)) / SR
        f = 120 * np.exp(-t * 18) + 45
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14)).astype(np.float32)

    @staticmethod
    def akor(notalar, sure=1.6):
        t = np.arange(int(SR * sure)) / SR
        d = sum(np.sin(2 * np.pi * n * t) + 0.4 * np.sin(4 * np.pi * n * t) for n in notalar)
        return (d / len(notalar) * np.minimum(1, t * 30) * np.exp(-t * 1.6)).astype(np.float32)

    def kaydet(self, yol, sure):
        a = self.a[:int(sure * SR)]
        m = np.max(np.abs(a)) or 1
        with wave.open(yol, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((a / m * 0.85 * 32767).astype(np.int16).tobytes())


def _arka_plan(rnd):
    bg = Image.new("RGB", (W, H)); bd = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        bd.line([(0, y), (W, y)], fill=(int(14 + 20 * k), int(16 + 6 * k), int(40 + 30 * k)))
    for _ in range(60):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        bd.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(60, 70, 110))
    return bg


def mac_oyna(plakalar, mod="kacis", baslik="1. TUR · A GRUBU", tur_atlar=3, sonraki=None, tohum=1,
             cikti="mac.mp4", gecici="/tmp", final=False):
    """plakalar: ['16','34',...]  ·  sonraki: (başlık, [plakalar]) bir sonraki maçın tanıtımı
    Dönüş: (tur atlayan plakalar, elenme sırası, süre sn)"""
    m = MODLAR[mod]
    rnd = random.Random(tohum)
    n = len(plakalar)
    TOP_R = 62 if n <= 9 else 56 if n <= 12 else 48
    pos = np.zeros((n, 2)); vel = np.zeros((n, 2))
    for i in range(n):
        while True:
            a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, R - TOP_R - 20)
            p = np.array([CX + r * math.cos(a), CY + r * math.sin(a)])
            if all(np.linalg.norm(p - pos[j]) > 2 * TOP_R + 6 for j in range(i)):
                pos[i] = p; break
        ang = rnd.uniform(0, 2 * math.pi); vel[i] = [math.cos(ang) * 520, math.sin(ang) * 520]
    canli = [True] * n
    renkler = [renk(p) for p in plakalar]
    elenen = []                       # (index, kare)
    bosluklar = [list(b) for b in m["bosluklar"]]
    G, g_aci = 700.0, math.pi / 2     # aşağı
    INTRO, OUTRO, MAXOYUN = int(2.8 * FPS), int(5.0 * FPS), 80 * FPS
    ses = Ses(INTRO / FPS + MAXOYUN / FPS + OUTRO / FPS)
    son_ses = [0.0] * n
    bg = _arka_plan(rnd)
    vid_yol = os.path.join(gecici, "arena_v.mp4"); ses_yol = os.path.join(gecici, "arena_s.wav")
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", vid_yol], stdin=subprocess.PIPE)
    oyun_kare = [0]

    def bosluk_gen():
        return math.radians(m["bosluk0"] + min(40, oyun_kare[0] / FPS * m["buyume"]))

    def top_ciz(d, i, x, y, rr):
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=renkler[i], outline=(255, 255, 255), width=4)
        ad = AD[plakalar[i]]
        fa = font(max(13, int(min(19, 170 / max(5, len(ad))) * rr / 62)), "Black")
        yazi(d, (x, y - rr * 0.13), plakalar[i], font(int(44 * rr / 56)), kenar=3)
        yazi(d, (x, y + rr * 0.45), ad, fa, kenar=2)

    def ciz(durum, kare_no, olcek=1.0):
        im = bg.copy(); d = ImageDraw.Draw(im)
        bg_ = bosluk_gen()
        d.ellipse([CX - R, CY - R, CX + R, CY + R], fill=(22, 26, 46))
        # halka: boşlukları atlayarak çiz
        acilar = sorted(((b[0] % (2 * math.pi)) for b in bosluklar))
        for k, a in enumerate(acilar):
            bas = math.degrees(a + bg_ / 2)
            son = math.degrees(acilar[(k + 1) % len(acilar)] - bg_ / 2)
            if son <= bas:
                son += 360
            d.arc([CX - R - 6, CY - R - 6, CX + R + 6, CY + R + 6], bas, son, fill=SARI, width=14)
        if m["g_donus"]:  # yerçekimi oku
            ux, uy = math.cos(g_aci), math.sin(g_aci)
            d.line([CX, CY, CX + ux * 120, CY + uy * 120], fill=(255, 255, 255, 80), width=6)
            d.ellipse([CX + ux * 120 - 12, CY + uy * 120 - 12, CX + ux * 120 + 12, CY + uy * 120 + 12], fill=(255, 255, 255))
        if durum == "outro":
            atl = [i for i in range(n) if canli[i]]
            for k, i in enumerate(atl):
                x = CX + (k - (len(atl) - 1) / 2) * (2 * TOP_R * olcek + 40)
                top_ciz(d, i, x, CY, TOP_R * olcek)
        else:
            son_elenen = elenen[-1] if elenen else None
            for i in range(n):
                gorunur = canli[i] or (son_elenen and son_elenen[0] == i and kare_no - son_elenen[1] < 10)
                if gorunur:
                    top_ciz(d, i, pos[i][0], pos[i][1], TOP_R)
        yazi(d, (W / 2, 145), "81 İL TURNUVASI", font(78), SARI, 8)
        yazi(d, (W / 2, 228), f"{baslik} · {m['ad']}", font(42, "Bold"), kenar=5)
        kalan = sum(canli)
        yazi(d, (W / 2, 318), f"KALAN: {kalan}/{n}  ·  İLK {tur_atlar} TUR ATLAR", font(46), kenar=6)
        if durum == "oyun" and kalan == tur_atlar + 1:
            yazi(d, (W / 2, 420), "SON ELEME!", font(66), KIRMIZI, 7)
        for k, (e, _) in enumerate(reversed(elenen[-4:])):
            c = KIRMIZI if k == 0 else (190 - k * 30,) * 3
            yazi(d, (W / 2, 1530 + k * 62), f"× {plakalar[e]} {AD[plakalar[e]]} ELENDİ", font(40, "Bold"), c, 5)
        if durum == "intro":
            d.rectangle([0, 760, W, 1260], fill=(0, 0, 0))
            yazi(d, (W / 2, 880), "ŞEHRİN", font(96), SARI, 8)
            yazi(d, (W / 2, 990), "TUR ATLAYABİLECEK Mİ?", font(84), kenar=8)
            yazi(d, (W / 2, 1120), m["kural"], font(42, "Bold"), kenar=4)
            yazi(d, (W / 2, 1185), f"Son {tur_atlar} kalan tur atlar.", font(42, "Bold"), kenar=4)
        if durum == "outro":
            d.rectangle([0, 1380, W, 1900], fill=(0, 0, 0))
            yazi(d, (W / 2, 1450), "ŞAMPİYON!" if final else "TUR ATLADI!", font(84), SARI, 8)
            if sonraki:
                yazi(d, (W / 2, 1555), f"YARIN: {sonraki[0]}", font(48), kenar=5)
                adlar = [AD[p] for p in sonraki[1]]
                satirlar = [" · ".join(adlar[i:i + 3]) for i in range(0, len(adlar), 3)]
                for k, s in enumerate(satirlar[:3]):
                    yazi(d, (W / 2, 1630 + k * 55), s, font(38, "Bold"), (200, 210, 255), 4)
                yazi(d, (W / 2, 1790), "Şehrin tur atladıysa BEĞEN, yorumlara yaz!", font(48), SARI, 5)
            else:
                yazi(d, (W / 2, 1580), "Yeni sezon yarın başlıyor!", font(50), kenar=5)
                yazi(d, (W / 2, 1670), "Şampiyon senin şehrin mi? BEĞEN, yorumlara yaz!", font(42, "Bold"), SARI, 4)
        proc.stdin.write(im.tobytes())

    for k in range(INTRO):
        ciz("intro", k)
    ses.ekle(0.05, Ses.akor([392, 494, 587], 1.2), 0.5)
    ses.ekle(INTRO / FPS - 0.2, Ses.kick(), 1.0)

    dt = 1 / FPS / SUB
    kare = INTRO
    while sum(canli) > tur_atlar and oyun_kare[0] < MAXOYUN:
        t_s = kare / FPS
        if oyun_kare[0] % 15 == 0:
            ses.ekle(t_s, Ses.kick(), 0.5)
        for _ in range(SUB):
            bg_ = bosluk_gen()
            g = np.array([math.cos(g_aci), math.sin(g_aci)]) * G
            idx = [i for i in range(n) if canli[i]]
            for i in idx:
                vel[i] += g * dt; pos[i] += vel[i] * dt
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    i, j = idx[a], idx[b]
                    dv = pos[j] - pos[i]; dist = np.linalg.norm(dv)
                    if 0 < dist < 2 * TOP_R:
                        nr = dv / dist; rel = np.dot(vel[i] - vel[j], nr)
                        if rel > 0:
                            vel[i] -= rel * nr; vel[j] += rel * nr
                        u = (2 * TOP_R - dist) / 2; pos[i] -= nr * u; pos[j] += nr * u
            for i in idx:
                dv = pos[i] - [CX, CY]; dist = np.linalg.norm(dv)
                if dist + TOP_R < R:
                    continue
                ang = math.atan2(dv[1], dv[0])
                kapida = any(abs((ang - b[0] + math.pi) % (2 * math.pi) - math.pi) < bg_ / 2 for b in bosluklar)
                if kapida:
                    if dist > R + TOP_R * 1.2 and canli[i] and sum(canli) > tur_atlar:
                        canli[i] = False; elenen.append((i, kare)); ses.ekle(t_s, Ses.pop(), 0.9)
                    continue
                nr = dv / dist; vn = np.dot(vel[i], nr)
                if vn > 0:
                    vel[i] -= 2 * vn * nr
                    hiz = np.linalg.norm(vel[i]); hedef = min(1150, max(650, hiz))
                    vel[i] = vel[i] / (hiz or 1) * hedef + [rnd.uniform(-40, 40), rnd.uniform(-40, 40)]
                    if t_s - son_ses[i] > 0.12:
                        ses.ekle(t_s, Ses.blip(440 + 55 * (i % 8)), 0.25); son_ses[i] = t_s
                pos[i] = [CX, CY] + nr * (R - TOP_R)
            if elenen:
                e = elenen[-1][0]; vel[e] += g * dt; pos[e] += vel[e] * dt
            for b in bosluklar:
                b[0] += b[1] * dt
            g_aci += m["g_donus"] * dt
        ciz("oyun", kare)
        kare += 1; oyun_kare[0] += 1
    # süre dolduysa: merkeze en uzak olanlar elenir
    while sum(canli) > tur_atlar:
        i = max((i for i in range(n) if canli[i]), key=lambda i: np.linalg.norm(pos[i] - [CX, CY]))
        canli[i] = False; elenen.append((i, kare))
    ses.ekle(kare / FPS, Ses.akor([523, 659, 784, 1047], 2.5), 1.0)
    for k in range(OUTRO):
        ciz("outro", kare + k, olcek=1 + 0.5 * min(1, k / 15))
    toplam = (kare + OUTRO) / FPS
    proc.stdin.close(); proc.wait()
    ses.kaydet(ses_yol, toplam)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid_yol, "-i", ses_yol, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", cikti], check=True)
    atlayan = [plakalar[i] for i in range(n) if canli[i]]
    return atlayan, [plakalar[e] for e, _ in elenen], toplam
