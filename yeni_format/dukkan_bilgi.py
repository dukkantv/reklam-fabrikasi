# Dükkan TV — "Doğru Bilinen Yanlışlar" serisi (26 Kas 2026, Kürşat/Youtube Kampı videosunun tarzından).
# Koyu zemin + neon kırmızı, damga yazılar, bölüm etiketleri, vurgulu altyazı. Levent'in klon sesi ("samimi").
# Konular: yeni_format/dukkan_konular.json (sırayla). Kullanım:
#   python dukkan_bilgi.py            -> sıradaki konu, video + yayin.json
#   python dukkan_bilgi.py kare 3 9   -> test kareleri (out/)
import json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw
from kit import *

BURA = os.path.dirname(os.path.abspath(__file__))
RED = (255, 48, 72)
WHITE = (245, 245, 250)
GREY = (150, 150, 165)
GREEN = (60, 230, 140)
YELLOW = (255, 205, 70)
BG = (9, 8, 12)
RENK = {"kirmizi": RED, "yesil": GREEN, "beyaz": WHITE, "sari": YELLOW}
TARZ = "samimi"
MIN = {"kanca": 3.6, "efsane": 4.2, "gercek": 4.5, "uyari": 4.5, "liste": 5.5, "son": 4.0}

_vig = vignette(W, H, 0.8)


def background(t):
    y, x = np.ogrid[:H // 4, :W // 4]
    cx = W / 8 + 60 * np.sin(t * 0.35)
    cy = H / 8 * 0.8 + 50 * np.cos(t * 0.27)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    glow = np.exp(-(r / 170) ** 2)[..., None] * np.array([70, 10, 18])
    small = np.clip(np.array(BG)[None, None] + glow, 0, 255).astype(np.uint8)
    big = np.asarray(Image.fromarray(small).resize((W, H), Image.BILINEAR)).astype(np.float32)
    big *= _vig[..., None]
    return Image.fromarray(grain(big.astype(np.uint8), 4, seed=int(t * FPS))).convert("RGBA")


def kelimeler(txt):
    words, cur, hi, i = [], [], False, 0
    while i < len(txt):
        if txt.startswith("**", i):
            hi = not hi; i += 2; continue
        ch = txt[i]
        if ch == " ":
            if cur:
                words.append(cur); cur = []
        elif cur and cur[-1][1] == hi:
            cur[-1] = (cur[-1][0] + ch, hi)
        else:
            cur.append((ch, hi))
        i += 1
    if cur:
        words.append(cur)
    return words


def caption(img, txt, lt, dur, y_mid=1440):
    f = font("black", 74)
    space = f.getlength(" ")
    lines, cur, cw = [], [], 0
    for w in kelimeler(txt):
        wl = sum(f.getlength(p) for p, _ in w)
        if cur and cw + space + wl > 920:
            lines.append(cur); cur, cw = [], 0
        cw += (space if cur else 0) + wl
        cur.append((w, wl))
    if cur:
        lines.append(cur)
    lh = 92
    y0 = y_mid - (len(lines) - 1) * lh / 2
    a_in = ease_out(prog(lt, 0, 0.35))
    alpha = a_in * (1 - prog(lt, dur - 0.25, 0.25))
    if alpha <= 0:
        return
    dy = (1 - a_in) * 40
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    k = 0
    for i, line in enumerate(lines):
        x = (W - (sum(wl for _, wl in line) + space * (len(line) - 1))) / 2
        for w, wl in line:
            wa = clamp((lt - 0.06 * k) / 0.2)
            xx = x
            for p, hi in w:
                d.text((xx, y0 + i * lh + dy), p, font=f, fill=(RED if hi else WHITE) + (int(255 * wa),), anchor="lm",
                       stroke_width=3, stroke_fill=(0, 0, 0, int(200 * wa)))
                xx += f.getlength(p)
            x += wl + space
            k += 1
    paste_alpha(img, fast_blur(L, 10), alpha * 0.5)
    paste_alpha(img, L, alpha)


def top_brand(img):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 90, 86, 116), radius=6, fill=RED)
    d.text((104, 103), "DÜKKAN TV  ·  DOĞRU BİLİNEN YANLIŞLAR", font=font("bold", 30), fill=GREY + (255,), anchor="lm")


def chapter_label(img, sc, lt, dur):
    if not sc.get("etiket"):
        return
    k = ease_out(prog(lt, 0.1, 0.4))
    al = k * (1 - prog(lt, dur - 0.25, 0.25))
    x = 60 - (1 - k) * 60
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle((x, 170, x + 72, 242), radius=14, fill=RED + (255,))
    d.text((x + 36, 206), sc.get("rozet", "!"), font=font("black", 46), fill=(255, 255, 255, 255), anchor="mm")
    d.text((x + 96, 190), sc["etiket"], font=font("bold", 28), fill=RED + (255,), anchor="lm")
    d.text((x + 96, 226), sc.get("baslik", ""), font=font("bold", 38), fill=WHITE + (255,), anchor="lm")
    paste_alpha(img, L, al)


def big_text(img, txt, y, col, lt, t0=0.15, size=150):
    a = ease_out(prog(lt, t0, 0.4))
    f = font("black", size)
    while f.getlength(txt) > 960 and size > 60:
        size -= 8; f = font("black", size)
    glow_text(img, (540, y), txt, f, col, glow=18, strength=1, alpha=a)


def phone(d, cx, cy, w=300, h=560, col=WHITE, width=10, alpha=255):
    d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=48, outline=col + (alpha,), width=width)
    d.rounded_rectangle((cx - 40, cy - h / 2 + 22, cx + 40, cy - h / 2 + 36), radius=7, fill=col + (alpha,))


# ---------- sahne tipleri ----------
def s_kanca(img, sc, lt, dur):
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    k = back_out(prog(lt, 0.0, 0.6))
    cy = 860 + (1 - k) * 200
    phone(d, 540, cy, alpha=int(255 * clamp(lt * 3)))
    ek = sc.get("ekran", "?")
    ea = prog(lt, 0.6, 0.4)
    if ea > 0:
        f = font("sembol", 150)
        while f.getlength(ek) > 240:
            f = font("sembol", f.size - 10)
        d.text((540, cy), ek, font=f, fill=RED + (int(255 * ea),), anchor="mm")
    paste_alpha(img, fast_blur(L, 14), 1.0)
    paste_alpha(img, L, 1.0)
    if sc.get("buyuk"):
        big_text(img, sc["buyuk"], 420, WHITE, lt, 0.9, 120)


def s_efsane(img, sc, lt, dur):
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    k = back_out(prog(lt, 0.1, 0.5))
    ts = dur * 0.45
    if k > 0:
        cx, cy = 540, 780
        f = font("xbold", 62)
        lines = wrap("“" + sc["balon"] + "”", f, 680)
        w, h = 780 * k, (110 + 80 * len(lines)) * k
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(60 * k), fill=(38, 36, 46, 255))
        d.polygon([(cx - 200 * k, cy + h / 2 - 4), (cx - 270 * k, cy + h / 2 + 90 * k), (cx - 110 * k, cy + h / 2 - 4)],
                  fill=(38, 36, 46, 255))
        if k > 0.8:
            for i, ln in enumerate(lines):
                d.text((cx, cy - (len(lines) - 1) * 40 + i * 80), ln, font=f, fill=WHITE + (255,), anchor="mm")
        for i, px in enumerate((300, 540, 780)):
            a = int(255 * clamp((lt - 0.3 - i * 0.15) * 3))
            d.ellipse((px - 38, 1080, px + 38, 1156), fill=(80, 78, 92, a))
            d.rounded_rectangle((px - 70, 1170, px + 70, 1260), radius=50, fill=(80, 78, 92, a))
    paste_alpha(img, L, 1 - 0.75 * prog(lt, ts, 0.3))
    stamp(img, 540, 800, sc.get("damga", "EFSANE!"), font("black", 120), RED, t=prog(lt, ts, 0.35), angle=-8)


def s_gercek(img, sc, lt, dur):
    col = RENK.get(sc.get("renk", "yesil"), GREEN)
    if sc.get("bar") is not None:
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        a = ease_out(prog(lt, 0.2, 0.4)); al = int(255 * a)
        x0, x1, y = 130, 950, 900
        d.rounded_rectangle((x0, y - 50, x1, y + 50), radius=50, fill=(34, 32, 42, al))
        p = float(sc["bar"]) * ease_in_out(prog(lt, 0.5, min(2.5, dur * 0.5)))
        if p > 0.01:
            d.rounded_rectangle((x0 + 10, y - 40, x0 + 10 + (x1 - x0 - 20) * p, y + 40), radius=40, fill=col + (al,))
        if sc.get("bar_sol"):
            d.text((x0, y + 110), sc["bar_sol"], font=font("bold", 42), fill=GREY + (al,), anchor="lm")
        if sc.get("bar_sag"):
            d.text((x1, y + 110), sc["bar_sag"], font=font("bold", 42), fill=GREY + (al,), anchor="rm")
        paste_alpha(img, fast_blur(L, 16), 0.8)
        paste_alpha(img, L, 1.0)
        big_text(img, sc.get("buyuk", ""), 620, col, lt)
    else:
        big_text(img, sc.get("buyuk", ""), 800, col, lt, size=170)
    if sc.get("cip"):
        ca = back_out(prog(lt, dur * 0.5, 0.45))
        if ca > 0:
            L2 = Image.new("RGBA", img.size, (0, 0, 0, 0)); d2 = ImageDraw.Draw(L2)
            f = font("black", 52)
            w2 = (f.getlength(sc["cip"]) + 110) * ca
            d2.rounded_rectangle((540 - w2 / 2, 1100, 540 + w2 / 2, 1210), radius=55, fill=(20, 40, 34, 255) if col == GREEN else (50, 16, 22, 255),
                                 outline=col + (255,), width=5)
            if ca > 0.7:
                d2.text((540, 1155), sc["cip"], font=f, fill=col + (255,), anchor="mm")
            paste_alpha(img, L2, clamp(ca))


def s_uyari(img, sc, lt, dur):
    big_text(img, sc.get("buyuk", "!"), 780, RED, lt, size=190)
    if sc.get("alt"):
        a = ease_out(prog(lt, 0.6, 0.4))
        glow_text(img, (540, 960), sc["alt"], font("bold", 56), WHITE, glow=6, strength=0, alpha=a)
    if sc.get("damga"):
        stamp(img, 540, 1190, sc["damga"], font("black", 70), RED, t=prog(lt, dur * 0.5, 0.35), angle=-5)


def s_liste(img, sc, lt, dur):
    items = sc["maddeler"][:3]
    adim = max(1.2, (dur - 1.5) / len(items))
    for i, txt in enumerate(items):
        t0 = 0.5 + i * adim
        k = back_out(prog(lt, t0, 0.45))
        if k <= 0:
            continue
        y = 560 + i * 210
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        x = 120 - (1 - clamp(k)) * 120
        d.rounded_rectangle((x, y - 80, x + 840, y + 80), radius=34, fill=(28, 26, 34, 255), outline=(60, 58, 70, 255), width=3)
        tk = prog(lt, t0 + 0.35, 0.3)
        d.ellipse((x + 40, y - 46, x + 132, y + 46), fill=(GREEN if tk > 0 else (60, 58, 70)) + (255,))
        if tk > 0:
            p1, p2, p3 = (x + 62, y + 2), (x + 80, y + 22), (x + 112, y - 20)
            m = min(1, tk * 2)
            d.line((p1, (p1[0] + (p2[0] - p1[0]) * m, p1[1] + (p2[1] - p1[1]) * m)), fill=(10, 30, 20, 255), width=11)
            if tk > 0.5:
                m2 = (tk - 0.5) * 2
                d.line((p2, (p2[0] + (p3[0] - p2[0]) * m2, p2[1] + (p3[1] - p2[1]) * m2)), fill=(10, 30, 20, 255), width=11)
        f = font("xbold", 58)
        while f.getlength(txt) > 640:
            f = font("xbold", f.size - 4)
        d.text((x + 170, y), txt, font=f, fill=WHITE + (255,), anchor="lm")
        paste_alpha(img, L, clamp(k * 2))


def s_son(img, sc, lt, dur):
    a = ease_out(prog(lt, 0.1, 0.5))
    glow_text(img, (540, 520), sc.get("ust", "YARIN"), font("black", 64), RED, glow=12, strength=1, alpha=a)
    f = font("black", 86)
    for i, ln in enumerate(wrap(sc["yarin"], f, 920)[:3]):
        glow_text(img, (540, 660 + i * 105), ln, f, WHITE, glow=10, strength=0, alpha=clamp(a * 1.2 - i * 0.2))
    b = back_out(prog(lt, 1.0, 0.5))
    if b > 0:
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        w = 520 * b
        d.rounded_rectangle((540 - w / 2, 1050, 540 + w / 2, 1170), radius=60, fill=RED + (255,))
        if b > 0.7:
            d.text((540, 1110), sc.get("buton", "TAKİP ET"), font=font("black", 60), fill=(255, 255, 255, 255), anchor="mm")
        paste_alpha(img, fast_blur(L, 20), 1.0)
        paste_alpha(img, L, 1.0)
    c = prog(lt, 1.6, 0.5)
    if c > 0:
        glow_text(img, (540, 1400), "DÜKKAN TV", font("black", 70), WHITE, glow=8, strength=0, alpha=c)


TIPLER = {"kanca": s_kanca, "efsane": s_efsane, "gercek": s_gercek, "uyari": s_uyari, "liste": s_liste, "son": s_son}


class Video:
    def __init__(self, konu, sesler):
        self.k = konu
        self.sahneler = konu["sahneler"]
        self.bas, t = [], 0.0
        self.sure = []
        for sc, s in zip(self.sahneler, sesler):
            d = max(MIN[sc["tip"]], len(s) / SR + 0.7)
            self.bas.append(t); self.sure.append(d); t += d
        self.DUR = t

    def frame(self, t):
        img = background(t)
        for i, sc in enumerate(self.sahneler):
            a, dur = self.bas[i], self.sure[i]
            if not (a <= t < a + dur):
                continue
            lt = t - a
            L = Image.new("RGBA", img.size, (0, 0, 0, 0))
            TIPLER[sc["tip"]](L, sc, lt, dur)
            fin = ease_out(prog(lt, 0, 0.3))
            son = i == len(self.sahneler) - 1
            fout = 1 if son else 1 - prog(lt, dur - 0.22, 0.22)
            dy = int((1 - fin) * 80 - (1 - fout) * 80)
            if dy:
                L2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
                if dy > 0:
                    L2.alpha_composite(L.crop((0, 0, W, H - dy)), (0, dy))
                else:
                    L2.alpha_composite(L.crop((0, -dy, W, H)), (0, 0))
                L = L2
            paste_alpha(img, L, fin * fout)
            if sc.get("altyazi"):
                caption(img, sc["altyazi"], lt, dur)
            chapter_label(img, sc, lt, dur)
        top_brand(img)
        ImageDraw.Draw(img).rectangle((0, H - 10, W * t / self.DUR, H), fill=RED + (255,))
        return img

    def audio(self, sesler, path):
        m = Mix(self.DUR)
        chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
        bar, t, i = 2.4, 0.0, 0
        while t < self.DUR:
            ch = chords[i % 4]
            for n in ch:
                m.add(note(hz(n), bar + 0.4, "pad", 0.03, a=0.3, r=0.6), t)
            for b in range(4):
                m.add(note(hz(ch[0] - 24), 0.35, "sine", 0.12, a=0.005, r=0.25), t + b * bar / 4)
                m.add(sfx_tick() * 0.12, t + b * bar / 4 + bar / 8)
            t += bar; i += 1
        for k, sc in enumerate(self.sahneler):
            a, dur = self.bas[k], self.sure[k]
            m.add(sfx_whoosh(0.5), max(0, a - 0.15), 0.5)
            m.add(sesler[k], a + 0.25, 1.6)   # anlatım (müzikten belirgin yüksek)
            if sc["tip"] in ("efsane",):
                m.add(sfx_thud(), a + dur * 0.45, 0.8)
            if sc["tip"] == "uyari" and sc.get("damga"):
                m.add(sfx_thud(), a + dur * 0.5, 0.8)
            if sc["tip"] == "gercek" and sc.get("cip"):
                m.add(sfx_ding(), a + dur * 0.5, 0.5)
            if sc["tip"] == "liste":
                adim = max(1.2, (dur - 1.5) / len(sc["maddeler"][:3]))
                for j in range(len(sc["maddeler"][:3])):
                    m.add(sfx_pop(1320, 0.1), a + 0.85 + j * adim, 0.7)
        m.save(path)


def hazirla(konu, gecici="/tmp/dk"):
    os.makedirs(gecici, exist_ok=True)
    sesler, kaynak = [], set()
    for i, sc in enumerate(konu["sahneler"]):
        s, k = seslendir(TARZ, sc["seslendirme"], f"{gecici}/s{i}.wav")
        sesler.append(s); kaynak.add(k)
    print("Ses kaynağı:", kaynak)
    return Video(konu, sesler), sesler


def main():
    konular = json.load(open(os.path.join(BURA, "dukkan_konular.json"), encoding="utf-8"))
    durum_yol = os.path.join(BURA, "durum.json")
    durum = json.load(open(durum_yol, encoding="utf-8")) if os.path.exists(durum_yol) else {}
    secili = os.environ.get("KONU_NO", "").strip()
    idx = (int(secili) - 1) if secili.isdigit() else durum.get("dukkan", 0)
    if idx >= len(konular):
        print("Dükkan TV konu stoğu bitti — yeni konular yazılmalı"); sys.exit(3)
    konu = konular[idx]
    v, sesler = hazirla(konu)
    os.makedirs("out", exist_ok=True)
    render("out/_dk_v.mp4", v.DUR, v.frame)
    v.audio(sesler, "out/_dk_a.wav")
    sikistir("out/_dk_v.mp4", "out/dukkan_bilgi.mp4", "out/_dk_a.wav")
    print("Video:", round(v.DUR, 1), "sn")
    tg_video("out/dukkan_bilgi.mp4", f"🔴 Dükkan TV · Doğru Bilinen Yanlışlar #{idx + 1}\n{konu['baslik']}")
    json.dump({"video": os.path.abspath("out/dukkan_bilgi.mp4"), "baslik": konu["baslik"][:100],
               "aciklama": konu["aciklama"] + "\n\n#doğrubilinenyanlışlar #telefon #bilgi #shorts",
               "etiketler": konu.get("etiketler", "doğru bilinen yanlışlar,telefon,bilgi,teknoloji,ipucu")},
              open("out/yayin.json", "w", encoding="utf-8"), ensure_ascii=False)
    if not secili.isdigit():
        durum["dukkan"] = idx + 1
        json.dump(durum, open(durum_yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kare":
        os.environ["SESSIZ_TEST"] = "1"
        konular = json.load(open(os.path.join(BURA, "dukkan_konular.json"), encoding="utf-8"))
        konu = konular[int(os.environ.get("KONU_NO", "1")) - 1]
        v, _ = hazirla(konu)
        os.makedirs("out", exist_ok=True)
        print("süre", round(v.DUR, 1), [round(b, 1) for b in v.bas])
        for t in map(float, sys.argv[2:]):
            v.frame(t).convert("RGB").save(f"out/dk_{t:05.1f}.jpg", quality=85)
    else:
        main()
