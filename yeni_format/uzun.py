# Dükkan TV — UZUN eğitim videoları (16:9, 8–12 dk). 26 Kas 2026.
# Neon tarz (Doğru Bilinen Yanlışlar ile aynı kimlik), bölüm kartları, cümle cümle Levent'in klon sesi + altyazı,
# kapak resmi. Senaryolar: yeni_format/uzun_senaryolar/*.json, sıra yeni_format/durum.json → "uzun".
# Hız: sahnelerin durağan kısımlarında kare yeniden çizilmez (önbellek), bu yüzden 10 dk'lık video birkaç dakikada çizilir.
#
# Kullanım (yeni_format klasöründen):
#   python uzun.py                 -> sıradaki senaryo: video + kapak + yayin.json (+ tanıtım Shorts'u)
#   python uzun.py kare 5 40 90    -> test kareleri (SESSIZ_TEST=1 ile sessiz zamanlama)
#   SENARYO=uzun_senaryolar/x.json python uzun.py ...
import glob, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw
import kit
kit.W, kit.H, kit.FPS = 1920, 1080, 24
from kit import (font, wrap, glow_text, stamp, paste_alpha, fast_blur, vignette, grain, prog, clamp, ease_out,
                 back_out, ease_in_out, Mix, note, hz, sfx_whoosh, sfx_thud, sfx_pop, sfx_ding, sfx_tick, seslendir,
                 tg_video, SR, tr_upper)

W, H, FPS = 1920, 1080, 24
BURA = os.path.dirname(os.path.abspath(__file__))
RED = (255, 48, 72)
WHITE = (245, 245, 250)
GREY = (150, 150, 165)
GREEN = (60, 230, 140)
YELLOW = (255, 205, 70)
BG = (9, 8, 12)
RENK = {"kirmizi": RED, "yesil": GREEN, "beyaz": WHITE, "sari": YELLOW}
TARZ = "samimi"
BOSLUK = 0.32          # cümleler arası
SAHNE_SON = 0.55       # sahne sonunda nefes
SERI = "DÜKKAN TV  ·  ÖĞREN"

# ---------- arka plan (sabit, bir kez) ----------
def _bg():
    y, x = np.ogrid[:H // 4, :W // 4]
    g1 = np.exp(-(((x - W / 8 * 0.7) / 160) ** 2 + ((y - H / 8 * 0.6) / 120) ** 2))[..., None] * np.array([70, 10, 18])
    g2 = np.exp(-(((x - W / 8 * 1.5) / 140) ** 2 + ((y - H / 8 * 1.4) / 110) ** 2))[..., None] * np.array([40, 6, 12])
    small = np.clip(np.array(BG)[None, None] + g1 + g2, 0, 255).astype(np.uint8)
    big = np.asarray(Image.fromarray(small).resize((W, H), Image.BILINEAR)).astype(np.float32)
    big *= vignette(W, H, 0.7)[..., None]
    return Image.fromarray(grain(big.astype(np.uint8), 4, seed=7)).convert("RGBA")


BGI = _bg()


def temiz(s):
    """Ses için: ** işaretlerini ve emoji benzeri karakterleri kaldır."""
    return re.sub(r"\*\*", "", s).strip()


def cumleler(metin):
    parca = [c.strip() for c in re.split(r"(?<=[.!?…])\s+", metin.strip()) if c.strip()]
    out = []
    for c in parca:   # çok uzun cümleyi virgülden böl (altyazı 2 satırı geçmesin)
        if len(c) > 150 and "," in c:
            ks = c.split(", ")
            cur = ""
            for k in ks:
                if cur and len(cur) + len(k) > 120:
                    out.append(cur + ","); cur = k
                else:
                    cur = (cur + ", " + k) if cur else k
            out.append(cur)
        else:
            out.append(c)
    return out


# ---------- altyazı (vurgulu) ----------
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


def altyazi(img, txt, a):
    if a <= 0 or not txt:
        return
    f = font("bold", 46)
    space = f.getlength(" ")
    lines, cur, cw = [], [], 0
    for w in kelimeler(txt):
        wl = sum(f.getlength(p) for p, _ in w)
        if cur and cw + space + wl > 1560:
            lines.append(cur); cur, cw = [], 0
        cw += (space if cur else 0) + wl
        cur.append((w, wl))
    if cur:
        lines.append(cur)
    if len(lines) > 2:   # çok uzunsa küçült
        f = font("bold", 38); return altyazi_kucuk(img, txt, a)
    lh = 60
    y0 = 975 - (len(lines) - 1) * lh / 2
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    maxw = max(sum(wl for _, wl in ln) + space * (len(ln) - 1) for ln in lines)
    d.rounded_rectangle((W / 2 - maxw / 2 - 36, y0 - 46, W / 2 + maxw / 2 + 36, y0 + (len(lines) - 1) * lh + 46),
                        radius=24, fill=(0, 0, 0, 165))
    for i, ln in enumerate(lines):
        x = (W - (sum(wl for _, wl in ln) + space * (len(ln) - 1))) / 2
        for w, wl in ln:
            xx = x
            for p, hi in w:
                d.text((xx, y0 + i * lh), p, font=f, fill=(RED if hi else WHITE) + (255,), anchor="lm")
                xx += f.getlength(p)
            x += wl + space
    paste_alpha(img, L, a)


def altyazi_kucuk(img, txt, a):
    f = font("bold", 38)
    lines = wrap(temiz(txt), f, 1600)[:3]
    lh = 50
    y0 = 975 - (len(lines) - 1) * lh / 2
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    maxw = max(f.getlength(l) for l in lines)
    d.rounded_rectangle((W / 2 - maxw / 2 - 36, y0 - 40, W / 2 + maxw / 2 + 36, y0 + (len(lines) - 1) * lh + 40),
                        radius=24, fill=(0, 0, 0, 165))
    for i, l in enumerate(lines):
        d.text((W / 2, y0 + i * lh), l, font=f, fill=WHITE + (255,), anchor="mm")
    paste_alpha(img, L, a)


# ---------- sahne çizimleri (yatay) ----------
def baslik_metni(img, txt, y, size, col, a, glow=14, maxw=1700):
    f = font("black", size)
    while f.getlength(txt) > maxw and size > 40:
        size -= 6; f = font("black", size)
    glow_text(img, (W / 2, y), txt, f, col, glow=glow, strength=1, alpha=a)


def s_kanca(img, sc, lt, olaylar):
    a = ease_out(prog(lt, 0.1, 0.5))
    f = font("black", 104)
    lines = wrap(sc.get("baslik", ""), f, 1600)[:3]
    y0 = 430 - (len(lines) - 1) * 62
    for i, ln in enumerate(lines):
        glow_text(img, (W / 2, y0 + i * 124), ln, f, WHITE if i < len(lines) - 1 or len(lines) == 1 else RED,
                  glow=16, strength=1, alpha=clamp(a * 1.3 - i * 0.25))
    if sc.get("alt"):
        b = ease_out(prog(lt, 0.8, 0.5))
        glow_text(img, (W / 2, y0 + len(lines) * 124 + 20), sc["alt"], font("bold", 50), GREY, glow=4, strength=0, alpha=b)


def s_bolum(img, sc, lt, olaylar):
    k = ease_out(prog(lt, 0.05, 0.5))
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    x = 220 - (1 - k) * 120
    d.rounded_rectangle((x, 330, x + 190, 520), radius=34, fill=RED + (255,))
    d.text((x + 95, 425), str(sc["_no"]), font=font("black", 130), fill=(255, 255, 255, 255), anchor="mm")
    d.text((x + 250, 360), f"BÖLÜM {sc['_no']}", font=font("bold", 44), fill=RED + (255,), anchor="lm")
    f = font("black", 92)
    lines = wrap(sc["ad"], f, 1300)[:2]
    for i, ln in enumerate(lines):
        d.text((x + 250, 445 + i * 104), ln, font=f, fill=WHITE + (255,), anchor="lm")
    paste_alpha(img, fast_blur(L, 18), k * 0.6)
    paste_alpha(img, L, k)


def _kart(d, x0, y0, x1, y1, col=(28, 26, 34), kenar=(60, 58, 70)):
    d.rounded_rectangle((x0, y0, x1, y1), radius=30, fill=col + (255,), outline=kenar + (255,), width=3)


def s_madde(img, sc, lt, olaylar):
    """Başlık + sırayla gelen maddeler (tik işaretli)."""
    baslik_metni(img, sc.get("baslik", ""), 190, 74, WHITE, ease_out(prog(lt, 0.05, 0.4)))
    items = sc["maddeler"][:5]
    n = len(items)
    top = 300
    h = min(118, (860 - top) / n - 14) if n else 110
    for i, txt in enumerate(items):
        t0 = olaylar[i] if i < len(olaylar) else 0.4 + i * 0.6
        k = back_out(prog(lt, t0, 0.45))
        if k <= 0:
            continue
        y = top + i * (h + 16)
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        x = 260 - (1 - clamp(k)) * 160
        _kart(d, x, y, x + 1400, y + h)
        cy = y + h / 2
        tk = prog(lt, t0 + 0.3, 0.3)
        r = h * 0.3
        olumsuz = sc.get("olumsuz")   # "yapma / verme" listeleri: yeşil tik yerine kırmızı çarpı
        d.ellipse((x + 40, cy - r, x + 40 + 2 * r, cy + r),
                  fill=((RED if olumsuz else GREEN) if tk > 0 else (60, 58, 70)) + (255,))
        if tk > 0 and olumsuz:
            a = r * 0.42; cx = x + 40 + r; w = max(6, int(r * 0.22))
            d.line((cx - a, cy - a, cx + a, cy + a), fill=WHITE + (255,), width=w)
            d.line((cx - a, cy + a, cx + a, cy - a), fill=WHITE + (255,), width=w)
        elif tk > 0:
            d.line((x + 40 + r * 0.55, cy + 2, x + 40 + r * 0.9, cy + r * 0.4, x + 40 + r * 1.5, cy - r * 0.45),
                   fill=(10, 30, 20, 255), width=max(6, int(r * 0.22)), joint="curve")
        f = font("xbold", int(min(56, h * 0.46)))
        while f.getlength(txt) > 1200:
            f = font("xbold", f.size - 3)
        d.text((x + 40 + 2 * r + 40, cy), txt, font=f, fill=WHITE + (255,), anchor="lm")
        paste_alpha(img, L, clamp(k * 2))


def s_adimlar(img, sc, lt, olaylar):
    """Numaralı adımlar (1, 2, 3...)."""
    baslik_metni(img, sc.get("baslik", ""), 190, 74, WHITE, ease_out(prog(lt, 0.05, 0.4)))
    items = sc["adimlar"][:5]
    n = len(items)
    top = 300
    h = min(118, (860 - top) / n - 14) if n else 110
    for i, txt in enumerate(items):
        t0 = olaylar[i] if i < len(olaylar) else 0.4 + i * 0.6
        k = back_out(prog(lt, t0, 0.45))
        if k <= 0:
            continue
        y = top + i * (h + 16)
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        x = 260 - (1 - clamp(k)) * 160
        _kart(d, x, y, x + 1400, y + h)
        d.rounded_rectangle((x + 24, y + 14, x + 24 + h - 28, y + h - 14), radius=20, fill=RED + (255,))
        d.text((x + 24 + (h - 28) / 2, y + h / 2), str(i + 1), font=font("black", int(h * 0.5)), fill=(255, 255, 255, 255), anchor="mm")
        f = font("xbold", int(min(54, h * 0.45)))
        while f.getlength(txt) > 1220:
            f = font("xbold", f.size - 3)
        d.text((x + h + 30, y + h / 2), txt, font=f, fill=WHITE + (255,), anchor="lm")
        paste_alpha(img, L, clamp(k * 2))


def s_buyuk(img, sc, lt, olaylar):
    col = RENK.get(sc.get("renk", "kirmizi"), RED)
    if sc.get("ust"):
        glow_text(img, (W / 2, 260), sc["ust"], font("bold", 50), GREY, glow=4, strength=0, alpha=ease_out(prog(lt, 0.05, 0.4)))
    baslik_metni(img, sc["buyuk"], 480, 230, col, ease_out(prog(lt, 0.15, 0.5)), glow=24)
    if sc.get("alt"):
        b = ease_out(prog(lt, 0.7, 0.5))
        f = font("bold", 56)
        for i, ln in enumerate(wrap(sc["alt"], f, 1500)[:2]):
            glow_text(img, (W / 2, 690 + i * 72), ln, f, WHITE, glow=4, strength=0, alpha=b)


def s_efsane(img, sc, lt, olaylar):
    k = back_out(prog(lt, 0.1, 0.5))
    ts = olaylar[1] if len(olaylar) > 1 else 1.6
    L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    if k > 0:
        cx, cy = W / 2, 430
        f = font("xbold", 70)
        lines = wrap("“" + sc["balon"] + "”", f, 1200)[:3]
        w, h = 1400 * k, (130 + 90 * len(lines)) * k
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(70 * k), fill=(38, 36, 46, 255))
        d.polygon([(cx - 380 * k, cy + h / 2 - 4), (cx - 470 * k, cy + h / 2 + 100 * k), (cx - 250 * k, cy + h / 2 - 4)],
                  fill=(38, 36, 46, 255))
        if k > 0.8:
            for i, ln in enumerate(lines):
                d.text((cx, cy - (len(lines) - 1) * 45 + i * 90), ln, font=f, fill=WHITE + (255,), anchor="mm")
    paste_alpha(img, L, 1 - 0.35 * prog(lt, ts, 0.3))
    stamp(img, W / 2, 760, sc.get("damga", "EFSANE!"), font("black", 120), RED, t=prog(lt, ts, 0.35), angle=-6)


def s_uyari(img, sc, lt, olaylar):
    baslik_metni(img, sc["buyuk"], 380, 170, RED, ease_out(prog(lt, 0.1, 0.5)), glow=22)
    if sc.get("alt"):
        f = font("bold", 54)
        for i, ln in enumerate(wrap(sc["alt"], f, 1500)[:2]):
            glow_text(img, (W / 2, 560 + i * 70), ln, f, WHITE, glow=4, strength=0, alpha=ease_out(prog(lt, 0.6, 0.4)))
    if sc.get("damga"):
        ts = olaylar[1] if len(olaylar) > 1 else 1.4
        stamp(img, W / 2, 760, sc["damga"], font("black", 76), RED, t=prog(lt, ts, 0.35), angle=-4)


def s_karsilastir(img, sc, lt, olaylar):
    baslik_metni(img, sc.get("baslik", ""), 170, 70, WHITE, ease_out(prog(lt, 0.05, 0.4)))
    sutun = [sc["sol"], sc["sag"]]
    renk = [RENK.get(sc.get("sol_renk", "kirmizi"), RED), RENK.get(sc.get("sag_renk", "yesil"), GREEN)]
    for j in range(2):
        t0 = olaylar[j] if j < len(olaylar) else 0.4 + j * 0.8
        k = back_out(prog(lt, t0, 0.45))
        if k <= 0:
            continue
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        x0 = 170 + j * 820 + (1 - clamp(k)) * (-120 if j == 0 else 120)
        _kart(d, x0, 260, x0 + 760, 830, kenar=renk[j])
        d.rounded_rectangle((x0, 260, x0 + 760, 360), radius=30, fill=renk[j] + (255,))
        d.rectangle((x0, 330, x0 + 760, 360), fill=renk[j] + (255,))
        d.text((x0 + 380, 310), sutun[j]["baslik"], font=font("black", 54), fill=(15, 12, 16, 255), anchor="mm")
        f = font("bold", 44)
        y = 420
        for it in sutun[j]["maddeler"][:5]:
            for li, ln in enumerate(wrap(it, f, 640)[:2]):
                d.text((x0 + 50, y), ("•  " if li == 0 else "    ") + ln, font=f, fill=WHITE + (255,), anchor="lm")
                y += 54
            y += 30
        paste_alpha(img, L, clamp(k * 2))


def s_soru(img, sc, lt, olaylar):
    a = ease_out(prog(lt, 0.05, 0.5))
    glow_text(img, (W / 2, 330), "?", font("black", 300), RED, glow=26, strength=1, alpha=a)
    f = font("black", 76)
    for i, ln in enumerate(wrap(sc["soru"], f, 1500)[:2]):
        glow_text(img, (W / 2, 590 + i * 96), ln, f, WHITE, glow=10, strength=0, alpha=ease_out(prog(lt, 0.4, 0.5)))


def s_son(img, sc, lt, olaylar):
    a = ease_out(prog(lt, 0.1, 0.5))
    glow_text(img, (W / 2, 250), "SIRADAKİ VİDEO", font("black", 56), RED, glow=12, strength=1, alpha=a)
    f = font("black", 84)
    for i, ln in enumerate(wrap(sc.get("sonraki", ""), f, 1500)[:2]):
        glow_text(img, (W / 2, 380 + i * 104), ln, f, WHITE, glow=10, strength=0, alpha=clamp(a * 1.2 - i * 0.2))
    b = back_out(prog(lt, 0.9, 0.5))
    if b > 0:
        L = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        w = 640 * b
        d.rounded_rectangle((W / 2 - w / 2, 640, W / 2 + w / 2, 770), radius=65, fill=RED + (255,))
        if b > 0.7:
            d.text((W / 2, 705), "ABONE OL", font=font("black", 66), fill=(255, 255, 255, 255), anchor="mm")
        paste_alpha(img, fast_blur(L, 22), 1.0)
        paste_alpha(img, L, 1.0)


TIPLER = {"kanca": s_kanca, "bolum": s_bolum, "madde": s_madde, "adimlar": s_adimlar, "buyuk": s_buyuk,
          "efsane": s_efsane, "uyari": s_uyari, "karsilastir": s_karsilastir, "soru": s_soru, "son": s_son}
OGE = {"madde": "maddeler", "adimlar": "adimlar"}


# ---------- sohbet tarzı anlatım: her cümleye ayrı ton (26 Kas 2026) ----------
# Levent: "bazı yerlerde yavaş, bazı yerlerde hızlı, bazı yerlerde heyecanlı; sohbet eder gibi".
# (tarz, hız, cümleden sonraki duraklama sn). Cümle başına "[sakin]" gibi etiket yazılırsa o ton zorlanır.
TONLAR = {
    "normal":  ("samimi", 1.00, 0.30),
    "sakin":   ("sohbet_sakin", 0.94, 0.55),
    "merak":   ("sohbet_merak", 0.97, 0.65),
    "hizli":   ("sohbet_hizli", 1.07, 0.18),
    "heyecan": ("sohbet_heyecan", 1.03, 0.40),
}
ANLATIM = os.environ.get("ANLATIM", "duz")   # "sohbet" -> tonlu anlatım
_SIRA = ("birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci", "önce ", "sonra ", "ardından", "son olarak")
_HEYECAN = ("dikkat", "asla", "sakın", "tuzak", "hemen", "bir dakika", "çöker", "kilitlen", "ikiye katl", "inanılmaz")
_SAKIN = ("altın kural", "unutma", "en önemlisi", "aklında tek", "dürüst ol")


def ton_sec(c, tip, j, n):
    m = re.match(r"\s*\[(\w+)\]\s*", c)
    if m and m.group(1) in TONLAR:
        return m.group(1)
    t = temiz(c).replace("İ", "i").replace("I", "ı").lower()
    if any(k in t for k in _SAKIN):
        return "sakin"
    if t.endswith("?"):
        return "merak"
    if "!" in t or any(k in t for k in _HEYECAN):
        return "heyecan"
    if tip in ("madde", "adimlar") and t.startswith(_SIRA):
        return "hizli"
    if re.search(r"\d|yüzde|bin |milyon|milyar|sekiz|dört|on iki|doksan", t) and tip in ("buyuk", "karsilastir", "uyari"):
        return "sakin"
    if tip == "kanca" and j == 0:
        return "heyecan"
    if tip == "son" or tip == "soru":
        return "normal"
    return "normal"


def ton_bilgisi(c, tip, j, n):
    """(seslendirilecek metin, tarz, hız, duraklama)"""
    metin = re.sub(r"^\s*\[\w+\]\s*", "", c)
    if ANLATIM != "sohbet":
        return temiz(metin), TARZ, 1.0, BOSLUK
    tz, hz_, gap = TONLAR[ton_sec(c, tip, j, n)]
    return temiz(metin), tz, hz_, gap


# ---------- madde <-> cümle eşleştirme (her madde, kendisinden bahseden cümleyle ekrana gelir) ----------
def _kokler(t):
    t = re.sub(r"[^\wçğıöşüâîû ]", " ", temiz(t).lower().replace("İ", "i").replace("I", "ı"))
    return {w[:5] for w in t.split() if len(w) >= 3}


def oge_metinleri(sc):
    if sc["tip"] == "karsilastir":
        return [sc["sol"]["baslik"] + " " + " ".join(sc["sol"]["maddeler"]), sc["sag"]["baslik"] + " " + " ".join(sc["sag"]["maddeler"])]
    return sc.get(OGE.get(sc["tip"], ""), [])


def eslestir(ogeler, cumle_metinleri):
    """Sırayı koruyarak her maddeye en çok ortak kelimesi olan cümleyi bulur."""
    n, m = len(ogeler), len(cumle_metinleri)
    ck = [_kokler(c) for c in cumle_metinleri]
    sonuc, bas = [], 0
    for k, o in enumerate(ogeler):
        ok = _kokler(o)
        son_izin = m - (n - k)          # kalan maddelere yer bırak
        aday = range(bas, max(bas, son_izin) + 1)
        en = max(aday, key=lambda j: (len(ok & ck[j]), -j))
        if len(ok & ck[en]) == 0:
            en = min(bas, son_izin)
        sonuc.append(en)
        bas = en + 1
    return sonuc


# ---------- zamanlama ----------
class Uzun:
    def __init__(self, sen, sesler_fn):
        """sen: senaryo; sesler_fn(i_sahne, j_cumle, metin) -> float32 dizi"""
        self.sen = sen
        self.sahneler = []
        no = 0
        for sc in sen["sahneler"]:
            if sc.get("bolum"):
                no += 1
                self.sahneler.append({"tip": "bolum", "ad": sc["bolum"], "_no": no, "metin": sc.get("bolum_metin", "")})
            self.sahneler.append(sc)
        self.plan = []     # her sahne: dict(bas, sure, cumleler[(t0,t1,metin)], olaylar[], sesler[])
        t = 0.0
        for i, sc in enumerate(self.sahneler):
            cs = cumleler(sc.get("metin", "")) if sc.get("metin") else []
            seg, ses, tt = [], [], 0.35
            for j, c in enumerate(cs):
                metin, tz, hz_, gap = ton_bilgisi(c, sc["tip"], j, len(cs))
                s = sesler_fn(i, j, metin, tz, hz_)
                d = len(s) / SR
                yazi = re.sub(r"^\s*\[\w+\]\s*", "", c)
                seg.append((tt, tt + d, yazi)); ses.append((tt, s))
                tt += d + gap
            sure = max(tt + SAHNE_SON, 2.4 if sc["tip"] == "bolum" else 3.0)
            n_oge = len(sc.get(OGE.get(sc["tip"], ""), [])) if sc["tip"] in OGE else (2 if sc["tip"] == "karsilastir" else 0)
            if n_oge:
                if len(seg) >= n_oge:
                    olay = [seg[k][0] for k in eslestir(oge_metinleri(sc), [c[2] for c in seg])]
                else:
                    olay = [0.5 + k * (sure - 1.2) / n_oge for k in range(n_oge)]
            else:
                olay = [s[0] for s in seg]
            self.plan.append({"bas": t, "sure": sure, "cumleler": seg, "olaylar": olay, "sesler": ses})
            t += sure
        self.DUR = t

    def anahtar(self, t):
        """Aynı anahtar -> aynı kare (durağan kısımlar yeniden çizilmez)."""
        for i, p in enumerate(self.plan):
            if p["bas"] <= t < p["bas"] + p["sure"]:
                lt = t - p["bas"]
                olaylar = [0.0] + list(p["olaylar"]) + [c[0] for c in p["cumleler"]] + [c[1] for c in p["cumleler"]]
                son = max([o for o in olaylar if o <= lt], default=0.0)
                if lt - son < 0.85 or lt > p["sure"] - 0.3:
                    return None          # animasyon var: çiz
                ci = sum(1 for c in p["cumleler"] if c[0] <= lt)
                ca = any(c[0] <= lt < c[1] + BOSLUK * 0.6 for c in p["cumleler"])
                return (i, ci, ca, sum(1 for o in p["olaylar"] if o <= lt))
        return ("son",)

    def frame(self, t):
        img = BGI.copy()
        for i, p in enumerate(self.plan):
            if not (p["bas"] <= t < p["bas"] + p["sure"]):
                continue
            sc, lt = self.sahneler[i], t - p["bas"]
            L = Image.new("RGBA", img.size, (0, 0, 0, 0))
            TIPLER[sc["tip"]](L, sc, lt, p["olaylar"])
            fin = ease_out(prog(lt, 0, 0.3))
            fout = 1 - prog(lt, p["sure"] - 0.25, 0.25)
            paste_alpha(img, L, fin * fout)
            # altyazı: o an okunan cümle
            for (c0, c1, c) in p["cumleler"]:
                if c0 - 0.05 <= lt < c1 + BOSLUK * 0.6:
                    a = clamp((lt - c0 + 0.05) / 0.15) * (1 - prog(lt, c1 + BOSLUK * 0.6 - 0.12, 0.12))
                    altyazi(img, c, a)
            # bölüm göstergesi (sağ üst)
            no = max([s["_no"] for s in self.sahneler[: i + 1] if s["tip"] == "bolum"], default=0)
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((60, 52, 86, 78), radius=6, fill=RED)
            d.text((104, 65), SERI, font=font("bold", 30), fill=GREY + (255,), anchor="lm")
            if no and sc["tip"] != "bolum":
                ad = [s["ad"] for s in self.sahneler[: i + 1] if s["tip"] == "bolum"][-1]
                f = font("bold", 30)
                txt = f"BÖLÜM {no} · {ad}"
                while f.getlength(txt) > 900:
                    txt = txt[:-2]
                d.text((W - 60, 65), txt, font=f, fill=GREY + (255,), anchor="rm")
        return img

    def render(self, yol):
        w = kit.Writer(yol, self.DUR)
        onceki_k, onceki_b, cizilen = None, None, 0
        for n in range(w.n):
            t = n / FPS
            k = self.anahtar(t)
            if k is not None and k == onceki_k and onceki_b is not None:
                w.p.stdin.write(onceki_b)
                continue
            b = self.frame(t).convert("RGB").tobytes()
            cizilen += 1
            w.p.stdin.write(b)
            onceki_k, onceki_b = k, b
        w.close()
        print(f"Kare: {w.n}, çizilen: {cizilen}")

    def audio(self, yol):
        m = Mix(self.DUR)
        # hafif, dikkat dağıtmayan müzik yatağı (Am–F–C–G pad)
        chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
        bar, t, i = 4.0, 0.0, 0
        while t < self.DUR:
            for n in chords[i % 4]:
                m.add(note(hz(n), bar + 0.6, "pad", 0.018, a=0.8, r=1.0), t)
            m.add(note(hz(chords[i % 4][0] - 24), bar, "sine", 0.035, a=0.4, r=0.8), t)
            t += bar; i += 1
        for k, (sc, p) in enumerate(zip(self.sahneler, self.plan)):
            m.add(sfx_whoosh(0.45), max(0, p["bas"] - 0.1), 0.25 if sc["tip"] != "bolum" else 0.5)
            for (t0, s) in p["sesler"]:
                m.add(s, p["bas"] + t0, 1.7)
            if sc["tip"] == "efsane":
                ts = p["olaylar"][1] if len(p["olaylar"]) > 1 else 1.6
                m.add(sfx_thud(), p["bas"] + ts, 0.5)
            if sc["tip"] == "uyari" and sc.get("damga"):
                ts = p["olaylar"][1] if len(p["olaylar"]) > 1 else 1.4
                m.add(sfx_thud(), p["bas"] + ts, 0.5)
            if sc["tip"] in OGE:
                for o in p["olaylar"]:
                    m.add(sfx_pop(1180, 0.08), p["bas"] + o, 0.35)
            if sc["tip"] == "bolum":
                m.add(sfx_ding(), p["bas"] + 0.2, 0.25)
        m.save(yol)


# ---------- kapak (1280x720) ----------
def kapak(sen, yol):
    w, h = 1280, 720
    y, x = np.ogrid[:h, :w]
    g = np.exp(-(((x - w * 0.72) / 420) ** 2 + ((y - h * 0.45) / 300) ** 2))[..., None] * np.array([120, 14, 30])
    arr = np.clip(np.array(BG)[None, None] + g, 0, 255) * vignette(w, h, 0.6)[..., None]
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    yazi = sen.get("kapak_yazi", sen["baslik"])
    satirlar = yazi.split("|") if "|" in yazi else wrap(yazi, font("black", 120), 1120)
    f = font("black", 128)
    while max(f.getlength(s) for s in satirlar) > 1150 and f.size > 70:
        f = font("black", f.size - 6)
    y0 = h / 2 - (len(satirlar) - 1) * (f.size + 6) / 2 + 20
    for i, s in enumerate(satirlar[:3]):
        col = RED if i == len(satirlar) - 1 else WHITE
        L = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(L).text((70, y0 + i * (f.size + 6)), s, font=f, fill=col + (255,), anchor="lm",
                               stroke_width=6, stroke_fill=(0, 0, 0, 255))
        paste_alpha(img, fast_blur(L, 16), 0.9)
        paste_alpha(img, L, 1.0)
    if sen.get("kapak_rozet"):
        stamp(img, 1040, 120, sen["kapak_rozet"], font("black", 58), RED, t=1.0, angle=-8)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 40, 96, 66), radius=6, fill=RED)
    d.text((112, 53), "DÜKKAN TV", font=font("black", 34), fill=WHITE + (255,), anchor="lm")
    img.convert("RGB").save(yol, quality=92)


# ---------- tanıtım Shorts'u (dikey, mevcut Doğru Bilinen Yanlışlar motoru) ----------
def tanitim_kisa(sen, cikti):
    if not sen.get("tanitim"):
        return None
    import importlib
    kit.W, kit.H, kit.FPS = 1080, 1920, 30
    import dukkan_bilgi as db
    importlib.reload(db)
    konu = {"baslik": sen["tanitim"]["baslik"], "aciklama": sen["tanitim"].get("aciklama", ""), "sahneler": sen["tanitim"]["sahneler"]}
    v, sesler = db.hazirla(konu, "/tmp/uz_tan")
    kit.render("out/_tn_v.mp4", v.DUR, v.frame)
    v.audio(sesler, "out/_tn_a.wav")
    kit.sikistir("out/_tn_v.mp4", cikti, "out/_tn_a.wav")
    kit.W, kit.H, kit.FPS = 1920, 1080, 24
    return cikti


def senaryo_sec():
    if os.environ.get("SENARYO"):
        yol = os.path.join(BURA, os.environ["SENARYO"]) if not os.path.isabs(os.environ["SENARYO"]) else os.environ["SENARYO"]
        return yol, None
    liste = json.load(open(os.path.join(BURA, "uzun_sira.json"), encoding="utf-8"))
    durum = json.load(open(os.path.join(BURA, "durum.json"), encoding="utf-8")) if os.path.exists(os.path.join(BURA, "durum.json")) else {}
    idx = durum.get("uzun", 0)
    if idx >= len(liste):
        print("Uzun senaryo stoğu bitti"); sys.exit(3)
    return os.path.join(BURA, "uzun_senaryolar", liste[idx]), idx


def main(sadece_kare=None):
    yol, idx = senaryo_sec()
    sen = json.load(open(yol, encoding="utf-8"))
    os.makedirs("out", exist_ok=True); os.makedirs("/tmp/uz", exist_ok=True)
    kaynak = set()

    def sesler_fn(i, j, metin, tz=TARZ, hz_=1.0):
        s, k = seslendir(tz, metin, f"/tmp/uz/s{i:03d}_{j:02d}.wav", hz_)
        kaynak.add(k)
        return s
    v = Uzun(sen, sesler_fn)
    print("Senaryo:", sen["baslik"], "· süre", round(v.DUR / 60, 1), "dk · ses:", kaynak)
    if sadece_kare is not None:
        for t in sadece_kare:
            v.frame(t).convert("RGB").save(f"out/uz_{t:06.1f}.jpg", quality=85)
        kapak(sen, "out/kapak.jpg")
        return v
    v.render("out/_uz_v.mp4")
    v.audio("out/_uz_a.wav")
    kit.sikistir("out/_uz_v.mp4", "out/uzun.mp4", "out/_uz_a.wav")
    kapak(sen, "out/kapak.jpg")
    bolum_satiri = []
    for p, sc in zip(v.plan, v.sahneler):
        if sc["tip"] == "bolum":
            s = int(p["bas"])
            bolum_satiri.append(f"{s // 60:02d}:{s % 60:02d} {sc['ad']}")
    aciklama = sen["aciklama"] + "\n\n⏱️ Bölümler\n00:00 Giriş\n" + "\n".join(bolum_satiri)
    if sen.get("kaynaklar"):
        aciklama += "\n\n📚 Kaynaklar\n" + "\n".join("• " + k for k in sen["kaynaklar"])
    aciklama += "\n\nBu video genel bilgilendirme amaçlıdır; finansal, hukuki ya da tıbbi tavsiye değildir.\n\n#dükkantv #nasılyapılır #öğren"
    y = {"video": os.path.abspath("out/uzun.mp4"), "kapak": os.path.abspath("out/kapak.jpg"), "baslik": sen["baslik"][:100],
         "aciklama": aciklama, "etiketler": sen.get("etiketler", "")}
    try:
        if tanitim_kisa(sen, "out/tanitim.mp4"):
            y["kisa"] = {"video": os.path.abspath("out/tanitim.mp4"), "baslik": sen["tanitim"]["baslik"][:100],
                         "aciklama": sen["tanitim"].get("aciklama", "") + "\n\nTamamı kanalda: " + sen["baslik"] + "\n#shorts",
                         "etiketler": sen.get("etiketler", "")}
    except Exception as e:
        print("Tanıtım Shorts'u üretilemedi:", str(e)[:300])
    json.dump(y, open("out/yayin_uzun.json", "w", encoding="utf-8"), ensure_ascii=False)
    tg_video("out/uzun.mp4", f"🎬 Dükkan TV uzun video · {round(v.DUR / 60, 1)} dk\n{sen['baslik']}") if os.path.getsize("out/uzun.mp4") < 48e6 else \
        tg_video("out/tanitim.mp4", f"🎬 Dükkan TV uzun video hazır ({round(v.DUR / 60, 1)} dk, Telegram sınırı için tanıtımı gönderildi)\n{sen['baslik']}") if os.path.exists("out/tanitim.mp4") else None
    if idx is not None:
        d = json.load(open(os.path.join(BURA, "durum.json"), encoding="utf-8")) if os.path.exists(os.path.join(BURA, "durum.json")) else {}
        d["uzun"] = idx + 1
        json.dump(d, open(os.path.join(BURA, "durum.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def tum_metinler(sen):
    """Videoda seslendirilecek bütün (tarz, metin) çiftleri — paralel ses işleri için."""
    out = []
    for sc in sen["sahneler"]:
        if sc.get("bolum") and sc.get("bolum_metin"):
            cs = cumleler(sc["bolum_metin"])
            for j, c in enumerate(cs):
                m, tz, hz_, _ = ton_bilgisi(c, "bolum", j, len(cs)); out.append((tz, m, hz_))
        if sc.get("metin"):
            cs = cumleler(sc["metin"])
            for j, c in enumerate(cs):
                m, tz, hz_, _ = ton_bilgisi(c, sc["tip"], j, len(cs)); out.append((tz, m, hz_))
    for sc in (sen.get("tanitim") or {}).get("sahneler", []):
        out.append(("samimi", sc["seslendirme"], 1.0))
    return out


def ses_parcasi(parca, toplam):
    """Önbelleğe (SES_ONBELLEK) bu işe düşen cümleleri seslendirir: python uzun.py ses 0 4"""
    yol, _ = senaryo_sec()
    sen = json.load(open(yol, encoding="utf-8"))
    os.makedirs("/tmp/uzp", exist_ok=True)
    liste = tum_metinler(sen)
    benim = [x for i, x in enumerate(liste) if i % toplam == parca]
    print(f"Parça {parca}/{toplam}: {len(benim)}/{len(liste)} cümle")
    for i, (tz, m, hz_) in enumerate(benim):
        seslendir(tz, m, f"/tmp/uzp/{i}.wav", hz_)
    print("bitti")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ses":
        ses_parcasi(int(sys.argv[2]), int(sys.argv[3]))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "kare":
        os.environ["SESSIZ_TEST"] = "1"
        main([float(x) for x in sys.argv[2:]])
    else:
        main()
