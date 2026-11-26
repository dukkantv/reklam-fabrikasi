# Drama Bite: "Mesajlaşma hikâyesi" formatı (26 Kas 2026). Hikâyeler mesaj_hikayeleri.json, sırayla.
# Klasik slayt hikâyesiyle gün aşırı dönüşümlü yayınlanır (drama-bite.yml).
# — WhatsApp benzeri sohbet akışıyla duygusal hikaye.
import sys
import numpy as np
from PIL import Image, ImageDraw
from kit import *

GOLD = (222, 184, 92)
CHAT_BG = (11, 20, 26)
OUT_B = (0, 92, 75)
IN_B = (32, 44, 51)
TXT = (233, 237, 239)
SUB = (134, 150, 160)
BLUE = (83, 189, 235)

import json, os
BURA = os.path.dirname(os.path.abspath(__file__))
HIKAYELER = json.load(open(os.path.join(BURA, "mesaj_hikayeleri.json"), encoding="utf-8"))
DURUM_YOL = os.path.join(BURA, "durum.json")
DURUM = json.load(open(DURUM_YOL, encoding="utf-8")) if os.path.exists(DURUM_YOL) else {}
_sec = os.environ.get("HIKAYE_NO", "").strip()
IDX = (int(_sec) - 1) if _sec.isdigit() else DURUM.get("mesaj", 0)
STOK_BITTI = IDX >= len(HIKAYELER)
HK = HIKAYELER[IDX % len(HIKAYELER)]
CONTACT = HK["kisi"]
# (kim, metin, ekstra bekleme)  kim: "ben" / "o"
MSGS = [(m[0], m[1], m[2] if len(m) > 2 else 0) for m in HK["mesajlar"]]
HOOK = 3.0
F_MSG = font("reg", 54)
F_TIME = font("reg", 28)
MAXW = 740
TOP, BOTTOM = 250, 1760

# ---------- zamanlama ----------
timeline = []  # (görünme zamanı, msg idx, yazıyor_başlangıcı veya None)
t = HOOK + 0.4
for i, (who, txt, extra) in enumerate(MSGS):
    if who == "o":
        typing = 0.9 + len(txt) / 32 + extra
        if extra >= 1.0:
            typing += 0.0
        timeline.append((t + typing, i, t))
        t += typing
    else:
        timeline.append((t + 0.35, i, None))
        t += 0.35
    t += 0.7 + len(txt) / 21  # okuma süresi
END_CHAT = t + 1.5
DUR = END_CHAT + 5.0


# ---------- balon ölçüleri ----------
def bubble_lines(txt):
    return wrap(txt, F_MSG, MAXW)


LAYOUT = []
y = TOP + 40
prev = None
for i, (who, txt, _) in enumerate(MSGS):
    lines = bubble_lines(txt)
    tw = max(F_MSG.getlength(l) for l in lines)
    bw = max(tw + 60, 0) + 120  # saat için yer
    bh = 32 + len(lines) * 66 + 26
    gap = 10 if prev == who else 26
    y += gap
    LAYOUT.append((y, bw, bh, lines))
    y += bh
    prev = who


def msg_time(i):
    hh, mm = map(int, HK.get("saat", "23:14").split(":"))
    mm += i // 3
    return f"{(hh + mm // 60) % 24:02d}:{mm % 60:02d}"


def draw_bubble(d, i, ytop, alpha, scale=1.0):
    who = MSGS[i][0]
    _, bw, bh, lines = LAYOUT[i]
    if who == "ben":
        x1 = W - 36; x0 = x1 - bw
        col = OUT_B
    else:
        x0 = 36; x1 = x0 + bw
        col = IN_B
    a = int(255 * alpha)
    if scale != 1.0:
        cx = x1 if who == "ben" else x0
        x0 = cx + (x0 - cx) * scale; x1 = cx + (x1 - cx) * scale
        bh2 = bh * scale
    else:
        bh2 = bh
    d.rounded_rectangle((x0, ytop, x1, ytop + bh2), radius=28, fill=col + (a,))
    # kuyruk
    if who == "ben":
        d.polygon([(x1 - 30, ytop), (x1 + 18, ytop), (x1 - 4, ytop + 26)], fill=col + (a,))
    else:
        d.polygon([(x0 + 30, ytop), (x0 - 18, ytop), (x0 + 4, ytop + 26)], fill=col + (a,))
    if scale < 0.85:
        return
    for k, ln in enumerate(lines):
        d.text((x0 + 30, ytop + 30 + k * 66), ln, font=F_MSG, fill=TXT + (a,), anchor="lt")
    tx = x1 - 26
    if who == "ben":
        # çift tik (mavi = okundu)
        d.line((tx - 30, ytop + bh - 30, tx - 22, ytop + bh - 22, tx - 8, ytop + bh - 40), fill=BLUE + (a,), width=4)
        d.line((tx - 18, ytop + bh - 26, tx - 14, ytop + bh - 22, tx, ytop + bh - 40), fill=BLUE + (a,), width=4)
        tx -= 42
    d.text((tx, ytop + bh - 30), msg_time(i), font=F_TIME, fill=(SUB if who == "o" else (170, 210, 200)) + (a,), anchor="rm")


def draw_typing(d, ytop, t):
    x0 = 36
    d.rounded_rectangle((x0, ytop, x0 + 160, ytop + 84), radius=28, fill=IN_B + (255,))
    d.polygon([(x0 + 30, ytop), (x0 - 18, ytop), (x0 + 4, ytop + 26)], fill=IN_B + (255,))
    for k in range(3):
        ph = (t * 6 - k * 0.9)
        off = max(0, np.sin(ph)) * 10
        c = 150 + int(80 * max(0, np.sin(ph)))
        d.ellipse((x0 + 38 + k * 34 - 10, ytop + 42 - 10 - off, x0 + 38 + k * 34 + 10, ytop + 42 + 10 - off), fill=(c, c, c, 255))


# arka plan deseni (WhatsApp duvar kağıdı hissi)
_bg = Image.new("RGBA", (W, H), CHAT_BG + (255,))
_d = ImageDraw.Draw(_bg)
rng = np.random.default_rng(4)
for _ in range(260):
    x, y = rng.uniform(0, W), rng.uniform(0, H)
    r = rng.uniform(6, 16)
    kind = rng.integers(0, 3)
    c = (22, 33, 40, 255)
    if kind == 0:
        _d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=3)
    elif kind == 1:
        _d.rounded_rectangle((x - r, y - r * 0.7, x + r, y + r * 0.7), radius=4, outline=c, width=3)
    else:
        _d.line((x - r, y, x + r, y), fill=c, width=3); _d.line((x, y - r, x, y + r), fill=c, width=3)


def header(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 210), fill=(31, 44, 51, 255))
    # geri ok
    d.line((60, 140, 36, 116, 60, 92), fill=TXT + (255,), width=6)
    # avatar
    d.ellipse((90, 70, 180, 160), fill=(96, 125, 139, 255))
    d.ellipse((118, 84, 152, 118), fill=(207, 216, 220, 255))
    d.chord((102, 118, 168, 178), 180, 360, fill=(207, 216, 220, 255))
    d.text((210, 98), CONTACT, font=font("semi", 46), fill=TXT + (255,), anchor="lm")
    typing_now = any(ts is not None and ts <= t < ta for ta, i, ts in timeline)
    status = "yazıyor…" if typing_now else "çevrimiçi"
    d.text((210, 146), status, font=font("reg", 32), fill=((0, 200, 130) if typing_now else SUB) + (255,), anchor="lm")
    # sağ simgeler (kamera, telefon)
    d.rounded_rectangle((880, 100, 926, 136), radius=8, outline=TXT + (255,), width=5)
    d.polygon([(926, 112), (948, 100), (948, 136), (926, 124)], fill=TXT + (255,))
    for k in range(3):
        d.ellipse((1000, 98 + k * 18, 1010, 108 + k * 18), fill=TXT + (255,))


def input_bar(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, BOTTOM + 20, W, H), fill=CHAT_BG + (255,))
    d.rounded_rectangle((24, BOTTOM + 40, W - 150, BOTTOM + 136), radius=48, fill=(32, 44, 51, 255))
    d.text((110, BOTTOM + 88), "Mesaj", font=font("reg", 40), fill=SUB + (255,), anchor="lm")
    d.ellipse((W - 128, BOTTOM + 36, W - 24, BOTTOM + 140), fill=(0, 168, 132, 255))
    d.rounded_rectangle((W - 86, BOTTOM + 62, W - 66, BOTTOM + 100), radius=10, fill=(255, 255, 255, 255))
    d.arc((W - 98, BOTTOM + 74, W - 54, BOTTOM + 114), 0, 180, fill=(255, 255, 255, 255), width=4)


def frame(t):
    img = _bg.copy()
    # içerik kaydırma: son görünen eleman alt sınırı geçmesin
    visible = [(ta, i, ts) for ta, i, ts in timeline if ta <= t]
    typing = [(ta, i, ts) for ta, i, ts in timeline if ts is not None and ts <= t < ta]
    bottom_needed = TOP
    if visible:
        i = visible[-1][1]
        bottom_needed = LAYOUT[i][0] + LAYOUT[i][2]
    if typing:
        i = typing[0][1]
        bottom_needed = LAYOUT[i][0] + 84
    target = max(0, bottom_needed - (BOTTOM - 30))
    # yumuşak kaydırma: hedefin geçmişini takip et
    def target_at(tt):
        v = [(ta, i, ts) for ta, i, ts in timeline if ta <= tt]
        ty = [(ta, i, ts) for ta, i, ts in timeline if ts is not None and ts <= tt < ta]
        bn = TOP
        if v:
            bn = LAYOUT[v[-1][1]][0] + LAYOUT[v[-1][1]][2]
        if ty:
            bn = LAYOUT[ty[0][1]][0] + 84
        return max(0, bn - (BOTTOM - 30))
    scroll = sum(target_at(t - k * 0.02) for k in range(10)) / 10
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    # tarih rozeti
    d.rounded_rectangle((W / 2 - 90, TOP - 20 - scroll, W / 2 + 90, TOP + 30 - scroll), radius=14, fill=(24, 34, 41, 255))
    d.text((W / 2, TOP + 5 - scroll), "BUGÜN", font=font("semi", 28), fill=SUB + (255,), anchor="mm")
    for ta, i, ts in visible:
        k = prog(t, ta, 0.22)
        sc = 0.6 + 0.4 * back_out(k)
        draw_bubble(d, i, LAYOUT[i][0] - scroll, clamp(k * 2), sc if k < 1 else 1.0)
    for ta, i, ts in typing:
        draw_typing(d, LAYOUT[i][0] - scroll, t)
    img.alpha_composite(L)
    header(img, t)
    input_bar(img)
    # giriş kancası
    if t < HOOK + 0.5:
        a = 1 - prog(t, HOOK, 0.5)
        S_ = Image.new("RGBA", (W, H), (0, 0, 0, int(200 * a)))
        img.alpha_composite(S_)
        k = ease_out(prog(t, 0.1, 0.6))
        f1 = font("black", 78)
        l1 = wrap(HK["kanca"][0], f1, 940)
        y = 900 - len(l1) * 50
        for j, ln in enumerate(l1):
            glow_text(img, (540, y + j * 100), ln, f1, (255, 255, 255), glow=8, strength=0, alpha=a * k)
        k2 = ease_out(prog(t, 1.2, 0.5))
        f2 = font("black", 84)
        for j, ln in enumerate(wrap(HK["kanca"][1], f2, 940)):
            glow_text(img, (540, y + len(l1) * 100 + 50 + j * 100), ln, f2, GOLD, glow=16, strength=1, alpha=a * k2)
        glow_text(img, (540, 1420), "DRAMA BITE", font("bold", 34), GOLD, glow=6, strength=0, alpha=a * k * 0.8)
    # kapanış kartı
    if t >= END_CHAT:
        lt = t - END_CHAT
        a = ease_out(prog(lt, 0, 0.6))
        img.alpha_composite(Image.new("RGBA", (W, H), (5, 5, 6, int(248 * a))))
        k1 = ease_out(prog(lt, 0.4, 0.7))
        f1 = font("black", 76)
        l1 = wrap(HK["son"][0], f1, 940)
        for j, ln in enumerate(l1):
            glow_text(img, (540, 720 + j * 95), ln, f1, (255, 255, 255), glow=6, strength=0, alpha=k1)
        k2 = ease_out(prog(lt, 1.6, 0.7))
        f2 = font("black", 84)
        for j, ln in enumerate(wrap(HK["son"][1], f2, 940)):
            glow_text(img, (540, 720 + len(l1) * 95 + 50 + j * 100), ln, f2, GOLD, glow=18, strength=1, alpha=k2)
        k3 = ease_out(prog(lt, 2.6, 0.6))
        if k3 > 0:
            Lc = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dc = ImageDraw.Draw(Lc)
            cw_ = font("bold", 48).getlength(HK["cagri"]) / 2 + 60
            dc.rounded_rectangle((540 - cw_, 1180, 540 + cw_, 1290), radius=55, outline=GOLD + (255,), width=4)
            fc = font("bold", 48)
            dc.text((540, 1235), HK["cagri"], font=fc, fill=GOLD + (255,), anchor="mm")
            paste_alpha(img, Lc, k3)
            glow_text(img, (540, 1420), "DRAMA BITE · takip et", font("bold", 36), (200, 200, 205), glow=4, strength=0, alpha=k3)
    return img


def audio(path):
    m = Mix(DUR)
    # hüzünlü piyano arpej: Am F C G
    prog_ = [(57, 60, 64, 69), (53, 57, 60, 65), (48, 52, 55, 60), (55, 59, 62, 67)]
    beat = 0.5
    tt = 0.0; c = 0
    while tt < DUR - 0.5:
        ch = prog_[c % 4]
        m.add(note(hz(ch[0] - 12), 4 * beat * 2, "piano", 0.10, r=1.0), tt)
        for k in range(8):
            n = ch[[0, 1, 2, 3, 2, 1, 2, 3][k]] + 12
            m.add(note(hz(n), 1.4, "piano", 0.045, r=0.9), tt + k * beat)
        tt += 8 * beat; c += 1
    for ta, i, ts in timeline:
        if MSGS[i][0] == "ben":
            m.add(sfx_pop(1250, 0.08), ta, 0.9)
            m.add(sfx_type(max(3, len(MSGS[i][1]) // 3), gap=0.05, seed=i) * 0.25, max(0, ta - 0.9))
        else:
            m.add(sfx_pop(760, 0.12), ta, 1.0)
    # isteğe bağlı efekt: hikâyede "zil": mesaj metni varsa o mesajdan sonra kapı zili
    if HK.get("zil"):
        hedef = [k for k, x in enumerate(MSGS) if x[1] == HK["zil"]]
        if hedef:
            ta = [x[0] for x in timeline if x[1] == hedef[0]][0]
            for k, f in enumerate((659.3, 523.3)):
                n = int(1.2 * SR); tq = np.arange(n) / SR
                m.add((0.35 * np.sin(2 * np.pi * f * tq) * np.exp(-tq * 3)).astype(np.float32), ta + 0.9 + k * 0.45)
    m.add(sfx_riser(1.0), END_CHAT - 0.6, 0.5)
    m.add(sfx_thud(), END_CHAT + 1.6, 0.6)
    m.save(path)


def main():
    if STOK_BITTI:
        print("Mesaj hikâyesi stoğu bitti — yeni hikâyeler yazılmalı"); sys.exit(3)
    os.makedirs("out", exist_ok=True)
    render("out/_dr_v.mp4", DUR, frame)
    audio("out/_dr_a.wav")
    sikistir("out/_dr_v.mp4", "out/drama_mesaj.mp4", "out/_dr_a.wav")
    print("Video:", round(DUR, 1), "sn ·", HK["baslik"])
    tg_video("out/drama_mesaj.mp4", f"💬 Drama Bite · Mesaj hikâyesi #{IDX + 1}\n{HK['baslik']}")
    json.dump({"video": os.path.abspath("out/drama_mesaj.mp4"), "baslik": HK["baslik"][:100],
               "aciklama": HK["aciklama"] + "\n\nBu hikâye kurgudur. 💬 Sen olsan ne yazardın? Yorumlara yaz.\n\n#hikaye #duygusal #mesaj #shorts",
               "etiketler": "duygusal hikaye,mesajlaşma,aile,hikaye,drama,kısa hikaye"},
              open("out/yayin.json", "w", encoding="utf-8"), ensure_ascii=False)
    if not _sec.isdigit():
        d = json.load(open(DURUM_YOL, encoding="utf-8")) if os.path.exists(DURUM_YOL) else {}
        d["mesaj"] = IDX + 1
        json.dump(d, open(DURUM_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kare":
        os.makedirs("out", exist_ok=True)
        print("süre", round(DUR, 1))
        for tt in map(float, sys.argv[2:]):
            frame(tt).convert("RGB").save(f"out/dr_{tt:05.1f}.jpg", quality=85)
    else:
        main()
