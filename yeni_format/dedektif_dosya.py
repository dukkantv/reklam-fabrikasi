# Kasa Kurgu — "Katil Kim?" vakaları için yeni DEDEKTİF DOSYASI şablonu (26 Kas 2026).
# Klasör + GİZLİ damgası, daktilo tutanak, mantar pano + polaroid şüpheliler, ipucu kartları, geri sayım.
# Anlatım: Levent'in klon sesi ("dedektif" tarzı). Vakalar: dedektif/vakalar_v2.json (sıra state.json → v2_index).
# Kullanım: python yeni_format/dedektif_dosya.py   (depo kökünden)   ·   ... kare 3 9 15  → test kareleri
import json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kit import *

BURA = os.path.dirname(os.path.abspath(__file__))
DED = os.path.join(os.path.dirname(BURA), "dedektif")
INK = (200, 30, 36)
PAPER = (236, 228, 210)
TYPE = (34, 30, 28)
CREAM = (245, 236, 214)
YEL = (247, 214, 92)
HARF = "ABC"
TARZ = "dedektif"
MIN = {"dosya": 4.2, "olay": 6.0, "supheli": 6.0, "ipucu": 4.5, "oy": 7.5}

rng = np.random.default_rng(11)


def make_desk():
    n = rng.standard_normal((H // 4, W // 4)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 20) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    streak = np.asarray(Image.fromarray((rng.standard_normal((H, 30)) * 40 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    base = np.array([46, 30, 20], np.float32)
    arr = base[None, None] * (0.75 + 0.002 * (n - 128) + 0.003 * (streak - 128))[..., None]
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
    arr = arr * np.clip(1.5 - 2.6 * r, 0.25, 1.4)[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")


def make_cork():
    n = rng.integers(0, 60, (H, W)).astype(np.float32)
    n = np.asarray(Image.fromarray(n.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    arr = np.array([150, 104, 62], np.float32)[None, None] * (0.55 + n[..., None] / 140)
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
    arr *= np.clip(1.35 - 1.9 * r, 0.3, 1.2)[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")


def paper_tex(w, h, col=PAPER):
    arr = np.clip(np.array(col)[None, None] + rng.normal(0, 7, (h, w, 1)), 0, 255).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


DESK, CORK, VIG = make_desk(), make_cork(), vignette(W, H, 0.55)


def ink_stamp(img, cx, cy, txt, size, t, angle=-12, col=INK):
    if t <= 0:
        return
    f = font("black", size)
    tw, th = text_size(txt, f)
    bw, bh = tw + 70, th + 60
    L = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle((20, 20, 20 + bw, 20 + bh), outline=col + (255,), width=12)
    d.text((20 + bw / 2, 20 + bh / 2 + 4), txt, font=f, fill=col + (255,), anchor="mm")
    a = np.asarray(L.getchannel("A"), np.float32)
    holes = np.random.default_rng(len(txt)).random(a.shape)
    L.putalpha(Image.fromarray((a * np.where(holes < 0.18, 0.25, 0.92)).astype(np.uint8)))
    L = L.rotate(angle, resample=Image.BICUBIC, expand=True)
    sc = 1.6 - 0.6 * min(1, t / 0.25)
    L = L.resize((max(1, int(L.width * sc)), max(1, int(L.height * sc))), Image.BICUBIC)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lay.alpha_composite(L, (int(cx - L.width / 2), int(cy - L.height / 2)))
    paste_alpha(img, lay, clamp(t * 5) * 0.92)


def shadowed(img, layer, xy, angle=0, shadow=18, alpha=1.0):
    lay = layer.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else layer
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    sh.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(shadow / 2))
    full = Image.new("RGBA", img.size, (0, 0, 0, 0))
    x, y = int(xy[0] - lay.width / 2), int(xy[1] - lay.height / 2)
    full.alpha_composite(sh, (max(0, x + 14), max(0, y + 22)))
    full.alpha_composite(lay, (max(0, x), max(0, y)))
    paste_alpha(img, full, alpha)


def top_text(img, txt, lt, dur, y=200, size=64, col=(255, 255, 255)):
    a = ease_out(prog(lt, 0.1, 0.4)) * (1 - prog(lt, dur - 0.3, 0.3))
    if a <= 0:
        return
    f = font("black", size)
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for i, ln in enumerate(wrap(txt, f, 960)):
        d.text((540, y + i * (size + 16)), ln, font=f, fill=col + (255,), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 255))
    paste_alpha(img, L, a)


class Dosya:
    def __init__(self, v, no, onceki, sesler, metinler):
        self.v, self.no, self.onceki = v, no, onceki
        self.tipler = ["dosya", "olay", "supheli", "ipucu", "ipucu", "oy"]
        self.bas, self.sure, t = [], [], 0.0
        for tip, s in zip(self.tipler, sesler):
            d = max(MIN[tip], len(s) / SR + 0.8)
            self.bas.append(t); self.sure.append(d); t += d
        self.DUR = t
        self.sup = v["supheliler"]
        self.pol = [self.polaroid(HARF[i], s["ad"], s["rol"]) for i, s in enumerate(self.sup)]
        self.clue = [self.clue_card(c, i + 1) for i, c in enumerate(v["ipuclari"][:2])]
        self.folder_base = None

    # ----- parçalar -----
    def folder_layer(self, lt):
        w, h = 820, 1000
        L = Image.new("RGBA", (w, h + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        d.rounded_rectangle((40, 0, 330, 90), radius=18, fill=(196, 160, 98, 255))
        d.text((185, 46), f"VAKA #{self.no:02d}", font=font("black", 40), fill=(80, 56, 26, 255), anchor="mm")
        tex = paper_tex(w, h, (208, 172, 108))
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), radius=22, fill=255)
        tex.putalpha(m)
        L.alpha_composite(tex, (0, 60))
        d.rectangle((90, 360, 730, 560), fill=CREAM + (255,))
        title = tr_upper(self.v["baslik"])
        f = font("mono", 70)
        lines = wrap(title, f, 600)
        if len(lines) > 2:
            f = font("mono", 52); lines = wrap(title, f, 600)[:2]
        n = int(sum(len(x) for x in lines) * clamp((lt - 1.4) / 1.2))
        for i, ln in enumerate(lines):
            part = ln[:max(0, n)]; n -= len(ln)
            d.text((410, 460 + (i - (len(lines) - 1) / 2) * (f.size + 10)), part, font=f, fill=TYPE + (255,), anchor="mm")
        d.line((150, 820, 670, 820), fill=(150, 116, 66, 255), width=3)
        d.text((410, 860), "Delil: 3 şüpheli · 2 ipucu", font=font("mono", 34), fill=(110, 80, 40, 255), anchor="mm")
        return L

    def polaroid(self, letter, name, role, w=300):
        h = int(w * 1.25)
        L = Image.new("RGBA", (w, h), (248, 246, 240, 255)); d = ImageDraw.Draw(L)
        ph = (20, 20, w - 20, int(h * 0.76))
        d.rectangle(ph, fill=(70, 84, 96, 255))
        for i in range(8):
            y = ph[1] + 20 + i * 30
            d.line((ph[0], y, ph[0] + 30, y), fill=(160, 175, 185, 255), width=2)
        cx = w / 2
        d.ellipse((cx - 52, ph[1] + 55, cx + 52, ph[1] + 165), fill=(24, 28, 34, 255))
        d.rounded_rectangle((cx - 100, ph[1] + 170, cx + 100, ph[3] + 40), radius=70, fill=(24, 28, 34, 255))
        d.rectangle((ph[0], ph[3], ph[2], ph[3] + 40), fill=(248, 246, 240, 255))
        d.text((cx, ph[1] + 120), "?", font=font("black", 70), fill=(90, 100, 110, 255), anchor="mm")
        f = font("black", 42)
        nm = tr_upper(name)
        while f.getlength(nm) > w - 30:
            f = font("black", f.size - 3)
        d.text((cx, int(h * 0.84)), nm, font=f, fill=TYPE + (255,), anchor="mm")
        f2 = font("mono", 28)
        rl = role[:1].upper() + role[1:]
        while f2.getlength(rl) > w - 20:
            f2 = font("mono", f2.size - 2)
        d.text((cx, int(h * 0.93)), rl, font=f2, fill=(90, 80, 70, 255), anchor="mm")
        d.ellipse((w - 76, 6, w - 6, 76), fill=INK + (255,))
        d.text((w - 41, 42), letter, font=font("black", 44), fill=(255, 255, 255, 255), anchor="mm")
        return L

    def clue_card(self, txt, num):
        w = 920
        f = font("bold", 50)
        lines = wrap(txt, f, w - 100)
        if len(lines) > 6:
            f = font("bold", 42); lines = wrap(txt, f, w - 100)
        h = 150 + len(lines) * (f.size + 16) + 40
        L = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        d.rounded_rectangle((0, 0, w, h), radius=26, fill=(18, 16, 15, 245), outline=YEL + (255,), width=5)
        d.rounded_rectangle((40, 36, 300, 104), radius=14, fill=YEL + (255,))
        d.text((170, 70), f"İPUCU {num}", font=font("black", 44), fill=(20, 16, 10, 255), anchor="mm")
        for i, ln in enumerate(lines):
            d.text((50, 160 + i * (f.size + 16)), ln, font=f, fill=(250, 246, 236, 255), anchor="lm")
        return L

    POS = [(220, 820, -5), (540, 700, 3), (860, 820, -2)]

    def board(self, img, lt, adim=1.1):
        img.alpha_composite(CORK)
        pins = [(x, y - 195) for x, y, _ in self.POS]
        sa = prog(lt, 0.4 + 3 * adim, 1.0)
        if sa > 0:
            L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            for (x0, y0), (x1, y1) in [(pins[0], pins[1]), (pins[1], pins[2])]:
                pts = [(x0 + (x1 - x0) * s, y0 + (y1 - y0) * s + 30 * np.sin(np.pi * s)) for s in np.linspace(0, sa, 30)]
                d.line(pts, fill=(190, 20, 30, 255), width=6)
            img.alpha_composite(L)
        for i, (x, y, a) in enumerate(self.POS):
            k = back_out(prog(lt, 0.4 + i * adim, 0.4))
            if k <= 0:
                continue
            sc = 1.5 - 0.5 * clamp(k)
            P = self.pol[i].resize((int(300 * sc), int(375 * sc)))
            shadowed(img, P, (x, y), angle=a, alpha=clamp(k * 3))
            d = ImageDraw.Draw(img)
            px, py = pins[i]
            d.ellipse((px - 18, py - 18, px + 18, py + 18), fill=(210, 30, 40, 255))
            d.ellipse((px - 8, py - 12, px + 2, py - 2), fill=(255, 150, 150, 255))

    # ----- sahneler -----
    def s_dosya(self, img, lt, dur):
        img.alpha_composite(DESK)
        k = ease_out(prog(lt, 0.0, 0.7))
        shadowed(img, self.folder_layer(lt), (540, 1020 + (1 - k) * 900), angle=-3)
        ink_stamp(img, 690, 680, "GİZLİ", 92, lt - 1.0, angle=-14)
        top_text(img, "3 şüpheli. 1 yalancı.", lt, dur, y=220, size=76)
        top_text(img, "Sen bulabilir misin?", max(0, lt - 0.9), dur - 0.9, y=320, size=64, col=YEL)

    def s_olay(self, img, lt, dur):
        img.alpha_composite(DESK)
        w, h = 900, 1180
        P = paper_tex(w, h); d = ImageDraw.Draw(P)
        d.text((70, 90), "OLAY TUTANAĞI", font=font("mono", 54), fill=INK + (255,), anchor="lm")
        d.line((70, 140, w - 70, 140), fill=TYPE + (180,), width=3)
        metin = self.v["olay"]
        f = font("mono", 46)
        lines = wrap(metin, f, w - 140)
        if len(lines) > 13:
            f = font("mono", 38); lines = wrap(metin, f, w - 140)
        lh = f.size + 28
        nchar = int(len(metin) * clamp((lt - 0.5) / max(1.0, dur * 0.78)))
        shown = 0
        saat = re.search(r"\d{1,2}[:.]\d{2}", metin)
        for i, ln in enumerate(lines):
            if shown >= nchar:
                break
            part = ln[: max(0, nchar - shown)]
            d.text((70, 220 + i * lh), part, font=f, fill=TYPE + (255,), anchor="lm")
            if saat and saat.group() in part:
                x0 = 70 + f.getlength(part[: part.index(saat.group())])
                d.line((x0, 220 + i * lh + 30, x0 + f.getlength(saat.group()), 220 + i * lh + 30), fill=INK + (255,), width=7)
            shown += len(ln) + 1
        k = ease_out(prog(lt, 0.0, 0.5))
        shadowed(img, P, (540, 1040 + (1 - k) * 300), angle=1.5, alpha=k)
        top_text(img, tr_upper(self.v["baslik"]), lt, dur, y=230, size=62, col=YEL)

    def s_supheli(self, img, lt, dur):
        adim = max(0.9, (dur - 2.0) / 3)
        self.board(img, lt, adim)
        top_text(img, "ŞÜPHELİLER", lt, dur, y=230, size=80, col=YEL)

    def s_ipucu(self, img, lt, dur, i):
        self.board(img, 99)
        k = back_out(prog(lt, 0.25, 0.45))
        g = Image.new("RGBA", img.size, (0, 0, 0, int(130 * clamp(k))))
        img.alpha_composite(g)
        L = self.clue[i]
        sc = 0.7 + 0.3 * k
        L2 = L.resize((max(1, int(L.width * sc)), max(1, int(L.height * sc))))
        shadowed(img, L2, (540, 1480), alpha=clamp(k))
        top_text(img, "ŞÜPHELİLER", 1, 99, y=230, size=80, col=YEL)

    def s_oy(self, img, lt, dur):
        self.board(img, 99)
        img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, 180)))
        a = ease_out(prog(lt, 0.1, 0.5))
        glow_text(img, (540, 430), "KATİL KİM?",
                  font("black", 130), (255, 255, 255), glow=14, strength=1, alpha=a)
        for i, s in enumerate(self.sup):
            k = back_out(prog(lt, 0.5 + i * 0.25, 0.4))
            if k <= 0:
                continue
            L = Image.new("RGBA", (860, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            d.rounded_rectangle((0, 0, 860, 150), radius=75, fill=(24, 22, 20, 255), outline=YEL + (255,), width=5)
            d.ellipse((20, 15, 140, 135), fill=INK + (255,))
            d.text((80, 75), HARF[i], font=font("black", 64), fill=(255, 255, 255, 255), anchor="mm")
            t = f"{tr_upper(s['ad'])} · {s['rol'][:1].upper() + s['rol'][1:]}"
            f = font("black", 56)
            while f.getlength(t) > 640:
                f = font("black", f.size - 3)
            d.text((180, 75), t, font=f, fill=(255, 255, 255, 255), anchor="lm")
            shadowed(img, L, (540, 640 + i * 190), alpha=clamp(k))
        cd0 = 1.6
        if cd0 <= lt < cd0 + 5:
            cd = 5 - int(lt - cd0)
            r, fr = 110, (lt - cd0) % 1.0
            L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            d.ellipse((540 - r, 1330 - r, 540 + r, 1330 + r), outline=(80, 80, 80, 255), width=14)
            d.arc((540 - r, 1330 - r, 540 + r, 1330 + r), -90, -90 + 360 * (1 - fr), fill=INK + (255,), width=14)
            d.text((540, 1330), str(cd), font=font("black", 120), fill=(255, 255, 255, 255), anchor="mm")
            img.alpha_composite(L)
        b = ease_out(prog(lt, cd0 + 5, 0.4))
        if b > 0:
            glow_text(img, (540, 1300), "Harfini yorumlara yaz", font("black", 62), YEL, glow=12, strength=1, alpha=b)
            glow_text(img, (540, 1390), "Cevap yarınki dosyada.", font("bold", 50), (255, 255, 255), glow=4, strength=0, alpha=b)
        if self.onceki:
            c = ease_out(prog(lt, 0.8, 0.4))
            L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            t = f"Dünkü vaka: {self.onceki} çıktı"
            f = font("bold", 40)
            wv = f.getlength(t) / 2 + 40
            d.rounded_rectangle((540 - wv, 1560, 540 + wv, 1640), radius=40, fill=(40, 34, 28, 255), outline=(120, 100, 70, 255), width=3)
            d.text((540, 1600), t, font=f, fill=(230, 220, 200, 255), anchor="mm")
            paste_alpha(img, L, c)

    def frame(self, t):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        for i, tip in enumerate(self.tipler):
            a, dur = self.bas[i], self.sure[i]
            if not (a <= t < a + dur):
                continue
            lt = t - a
            if tip == "ipucu":
                self.s_ipucu(img, lt, dur, i - 3)
            else:
                getattr(self, "s_" + tip)(img, lt, dur)
            son = i == len(self.tipler) - 1
            fade = prog(lt, 0, 0.25) if son else min(prog(lt, 0, 0.25), 1 - prog(lt, dur - 0.2, 0.2))
            if tip == "ipucu" and i == 4:   # iki ipucu arası pano sabit kalsın
                fade = 1.0 if lt > 0.01 else fade
            if fade < 1:
                img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, int(255 * (1 - fade)))))
        arr = np.asarray(img.convert("RGB"), np.float32) * VIG[..., None]
        out = Image.fromarray(grain(arr.astype(np.uint8), 6, seed=int(t * FPS))).convert("RGBA")
        ImageDraw.Draw(out).text((540, 1850), "KASA KURGU · DEDEKTİF DOSYASI", font=font("bold", 30), fill=(210, 190, 160, 200), anchor="mm")
        return out

    def audio(self, sesler, path):
        m = Mix(self.DUR)
        for tt in np.arange(0, self.DUR, 4.0):
            for n in (38, 45, 50):
                m.add(note(hz(n), 4.6, "pad", 0.05, a=0.8, r=1.0), tt)
        for tt in np.arange(0.5, self.DUR - 0.5, 1.0):
            m.add(sfx_tick() * 0.2, tt)
        for i, tip in enumerate(self.tipler):
            a, dur = self.bas[i], self.sure[i]
            m.add(sesler[i], a + 0.3, 1.6)
            if tip == "dosya":
                m.add(sfx_whoosh(0.6), 0.0, 0.7); m.add(sfx_thud(), a + 1.0, 0.8)
            elif tip == "olay":
                n = len(self.v["olay"])
                m.add(sfx_type(int(n * 0.6), gap=dur * 0.78 / (n * 0.6), seed=3) * 0.3, a + 0.5)
            elif tip == "supheli":
                adim = max(0.9, (dur - 2.0) / 3)
                for k in range(3):
                    m.add(sfx_shutter(), a + 0.4 + k * adim, 0.8)
            elif tip == "ipucu":
                m.add(sfx_pop(500, 0.2), a + 0.25, 0.9)
            elif tip == "oy":
                m.add(sfx_thud(), a + 0.1, 0.6)
                for k in range(5):
                    m.add(sfx_tick() * 2.0, a + 1.6 + k)
                m.add(sfx_ding(), a + 6.6, 0.7)
        m.save(path)


def metinler_yap(v, no, onceki):
    sup = v["supheliler"]
    oy = "Sence kim yaptı? Harfini yorumlara yaz."
    oy += f" Dünkü vakada cevap {onceki} çıktı." if onceki else " Cevabı yarın açıklıyorum."
    return [f"Dosya {no}. {v['baslik']}. Üç şüpheli var. Biri yalan söylüyor.",
            v["olay"],
            "Şüpheliler. " + " ".join(f"{HARF[i]}, {s['ad']}, {s['rol']}." for i, s in enumerate(sup)),
            "Birinci ipucu. " + v["ipuclari"][0],
            "İkinci ipucu. " + v["ipuclari"][1],
            oy]


def hazirla(idx=None):
    vakalar = json.load(open(os.path.join(DED, "vakalar_v2.json"), encoding="utf-8"))
    durum = json.load(open(os.path.join(DED, "state.json"), encoding="utf-8")) if os.path.exists(os.path.join(DED, "state.json")) else {}
    secili = (os.environ.get("VAKA_NO") or "").strip()
    if idx is None:
        idx = (int(secili) - 1) if secili.isdigit() else durum.get("v2_index", 0)
    idx %= len(vakalar)
    v = vakalar[idx]; no = idx + 1
    onceki = vakalar[idx - 1]["supheliler"][vakalar[idx - 1]["dogru"]]["ad"] if idx > 0 else None
    metinler = metinler_yap(v, no, onceki)
    os.makedirs("/tmp/ks", exist_ok=True)
    sesler, kaynak = [], set()
    for i, mt in enumerate(metinler):
        s, k = seslendir(TARZ, mt, f"/tmp/ks/s{i}.wav")
        sesler.append(s); kaynak.add(k)
    print("Vaka:", no, v["baslik"], "· ses:", kaynak)
    return Dosya(v, no, onceki, sesler, metinler), sesler, v, no, idx, durum, secili


def main():
    D, sesler, v, no, idx, durum, secili = hazirla()
    os.makedirs("out", exist_ok=True)
    render("out/_ks_v.mp4", D.DUR, D.frame)
    D.audio(sesler, "out/_ks_a.wav")
    hedef = os.path.join(DED, "gunun_vakasi.mp4")
    sikistir("out/_ks_v.mp4", hedef, "out/_ks_a.wav")
    print("Video hazır:", round(D.DUR, 1), "sn")
    tg_video(hedef, f"🕵️ Kasa Kurgu · Dosya #{no:02d}: {v['baslik']}\n\nYarınki videoda söyleyeceğin cevap:\n{v['cozum']}")
    json.dump({"video": hedef,
               "baslik": f"{v['baslik']}: Katil Kim? Sadece %1 Çözer! 🕵️ #shorts"[:100],
               "aciklama": (f"Dosya #{no:02d}: {v['baslik']}\n\nİpuçlarını izle, şüphelini seç ve yorumlara A, B ya da C yaz! "
                            "Cevap bir sonraki dosyada açıklanacak. 🕵️\n\n#katilkim #dedektif #gizem #vaka #shorts"),
               "etiketler": "katil kim,dedektif,gizem,vaka,bilmece,kurgusal hikaye"},
              open(os.path.join(DED, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if not secili.isdigit():
        durum["v2_index"] = idx + 1
        json.dump(durum, open(os.path.join(DED, "state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=4)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kare":
        os.environ["SESSIZ_TEST"] = "1"
        D, *_ = hazirla()
        os.makedirs("out", exist_ok=True)
        print("süre", round(D.DUR, 1), [round(b, 1) for b in D.bas])
        for t in map(float, sys.argv[2:]):
            D.frame(t).convert("RGB").save(f"out/ks_{t:05.1f}.jpg", quality=85)
    else:
        main()
