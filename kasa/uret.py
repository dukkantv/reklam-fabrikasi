import time
import asyncio, json, sys, os, math, wave, subprocess, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1080, 1920, 24, 44100
LH = 640          # illustration layer height
LY = 540          # illustration layer y
URUN = {"ad": "domates"}

FONT_YOL = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
_F = {}
def font(s):
    s = int(s)
    if s not in _F:
        f = None
        for p in FONT_YOL:
            if os.path.exists(p):
                f = ImageFont.truetype(p, s); break
        _F[s] = f or ImageFont.load_default()
    return _F[s]

def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()

def para(v):
    return f"{int(round(v)):,}".replace(",", ".") + " TL"

def yaz(d, xy, t, size, fill=(255, 255, 255), anchor="mm", stroke=0, sf=(0, 0, 0)):
    d.text(xy, t, font=font(size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sf)

TEMA = {"gece": ((15, 20, 55), (45, 30, 95)), "sabah": ((255, 165, 90), (255, 225, 160)),
        "gun": ((60, 165, 235), (195, 238, 255)), "aksam": ((110, 45, 110), (250, 135, 80)),
        "hesap": ((18, 62, 52), (8, 24, 30)), "oylama": ((20, 20, 70), (100, 30, 120))}
_G = {}
def zemin(tema):
    if tema not in _G:
        a, b = TEMA.get(tema, TEMA["gun"])
        t = np.linspace(0, 1, H)[:, None, None]
        arr = np.array(a) * (1 - t) + np.array(b) * t
        arr = np.repeat(arr, W, axis=1).astype(np.uint8)
        _G[tema] = Image.fromarray(arr, "RGB")
    return _G[tema]

# ---------------- cizimler (layer: W x LH) ----------------
def kisi(d, cx, ifade):
    b = 620
    d.rounded_rectangle((cx - 95, b - 270, cx + 95, b), 34, fill=(225, 75, 60))
    d.ellipse((cx - 90, b - 490, cx + 90, b - 300), fill=(245, 200, 160))
    d.pieslice((cx - 98, b - 520, cx + 98, b - 330), 180, 360, fill=(40, 60, 125))
    d.rectangle((cx - 110, b - 420, cx + 115, b - 402), fill=(28, 44, 95))
    hy = b - 360
    for dx in (-36, 36):
        r = 20 if ifade == "saskin" else 15
        d.ellipse((cx + dx - r, hy - r, cx + dx + r, hy + r), fill="white")
        d.ellipse((cx + dx - 8, hy - 8, cx + dx + 8, hy + 8), fill=(30, 30, 40))
    br = (60, 40, 30)
    if ifade == "saskin":
        for dx in (-36, 36): d.line((cx + dx - 18, hy - 38, cx + dx + 18, hy - 38), fill=br, width=7)
    elif ifade == "uzgun":
        d.line((cx - 58, hy - 22, cx - 20, hy - 38), fill=br, width=7)
        d.line((cx + 20, hy - 38, cx + 58, hy - 22), fill=br, width=7)
    elif ifade == "dusunceli":
        d.line((cx - 58, hy - 30, cx - 18, hy - 30), fill=br, width=7)
        d.line((cx + 18, hy - 44, cx + 58, hy - 36), fill=br, width=7)
    my = hy + 55
    if ifade == "saskin":
        d.ellipse((cx - 20, my - 22, cx + 20, my + 22), fill=(120, 30, 30))
    elif ifade == "mutlu":
        d.pieslice((cx - 44, my - 36, cx + 44, my + 40), 0, 180, fill=(120, 30, 30))
    elif ifade == "uzgun":
        d.arc((cx - 36, my - 6, cx + 36, my + 46), 200, 340, fill=(120, 30, 30), width=7)
    elif ifade == "dusunceli":
        d.line((cx - 28, my + 6, cx + 28, my + 6), fill=(120, 30, 30), width=7)
    else:
        d.arc((cx - 40, my - 30, cx + 40, my + 24), 20, 160, fill=(120, 30, 30), width=7)

def hal(d, yazi):
    d.rectangle((560, 190, 1000, 580), fill=(205, 165, 115))
    for k in range(8):
        d.polygon([(560 + k * 55, 190), (615 + k * 55, 190), (630 + k * 55, 270), (545 + k * 55, 270)],
                  fill=(220, 50, 50) if k % 2 == 0 else (250, 250, 250))
    d.rectangle((650, 330, 790, 580), fill=(90, 60, 40))
    d.rectangle((820, 330, 950, 460), fill=(150, 210, 240))
    d.rounded_rectangle((620, 100, 940, 180), 18, fill=(30, 40, 90))
    yaz(d, (780, 140), yazi or "HAL", 56)

def etiket(d, yazi):
    d.line((620, 60, 700, 220), fill=(240, 240, 240), width=6)
    d.rounded_rectangle((560, 200, 980, 480), 40, fill=(250, 228, 110), outline=(120, 90, 20), width=8)
    d.ellipse((600, 235, 640, 275), fill=(60, 60, 60))
    t = textwrap.wrap(yazi or "FİYAT", 9)[:3]
    for i, s in enumerate(t):
        yaz(d, (790, 340 + (i - (len(t) - 1) / 2) * 90), s, 72, (60, 30, 10))

def domates(d, yazi):
    cilek = URUN.get("ad") == "cilek"
    d.rounded_rectangle((570, 420, 990, 580), 20, fill=(170, 120, 70))
    pos = [(650, 400), (770, 385), (890, 400), (710, 330), (830, 320)]
    for x, y in pos:
        if cilek:
            d.ellipse((x - 52, y - 55, x + 52, y + 55), fill=(225, 40, 70))
            for dx, dy in ((-18, -10), (14, -22), (10, 14), (-14, 26)):
                d.ellipse((x + dx - 4, y + dy - 4, x + dx + 4, y + dy + 4), fill=(255, 230, 120))
        else:
            d.ellipse((x - 55, y - 50, x + 55, y + 50), fill=(220, 40, 40))
        d.polygon([(x - 16, y - 50), (x, y - 72), (x + 16, y - 50)], fill=(50, 150, 60))

def tezgah(d, yazi):
    for k in range(6):
        d.polygon([(540 + k * 78, 200), (618 + k * 78, 200), (630 + k * 78, 280), (528 + k * 78, 280)],
                  fill=(50, 120, 220) if k % 2 == 0 else (250, 250, 250))
    d.rectangle((550, 280, 566, 580), fill=(110, 80, 50)); d.rectangle((1000, 280, 1016, 580), fill=(110, 80, 50))
    d.rectangle((530, 440, 1040, 480), fill=(150, 105, 65))
    cols = [(230, 70, 60), (250, 190, 40), (90, 170, 70), (230, 120, 40)]
    for i, c in enumerate(cols):
        d.rounded_rectangle((570 + i * 115, 370, 670 + i * 115, 440), 12, fill=c)
    d.rectangle((560, 480, 1010, 580), fill=(130, 90, 55))

def kalabalik(d, yazi):
    cols = [(230, 80, 70), (70, 140, 220), (240, 190, 50), (110, 180, 90), (170, 90, 200), (240, 130, 60)]
    for i in range(6):
        x = 560 + i * 85; y = 580 - (i % 2) * 30; s = 1.0 - (i % 2) * 0.12
        d.rounded_rectangle((x - 34 * s, y - 190 * s, x + 34 * s, y), 16, fill=cols[i])
        d.ellipse((x - 32 * s, y - 270 * s, x + 32 * s, y - 200 * s), fill=(245, 205, 165))

def parayi(d, yazi):
    for k in range(4):
        o = k * 22
        d.rounded_rectangle((570 + o, 380 - o, 970 + o, 520 - o), 14, fill=(60 + k * 12, 150 + k * 10, 90), outline=(20, 90, 50), width=5)
    d.ellipse((730, 330 - 66, 810, 410 - 66), fill=(245, 205, 60), outline=(150, 110, 10), width=6)
    yaz(d, (770, 370 - 66), "TL", 36, (120, 80, 0))
    if yazi: yaz(d, (790, 560), yazi, 64, (255, 235, 110), stroke=6)

def defter(d, yazi):
    d.rounded_rectangle((580, 120, 960, 590), 22, fill=(252, 246, 225), outline=(120, 100, 60), width=6)
    for k in range(9): d.line((610, 190 + k * 45, 940, 190 + k * 45), fill=(190, 200, 225), width=3)
    d.line((650, 120, 650, 590), fill=(220, 90, 90), width=4)
    for k in range(7): d.ellipse((565, 140 + k * 62, 595, 170 + k * 62), fill=(70, 70, 80))
    t = textwrap.wrap(yazi or "", 9)[:4]
    for i, s in enumerate(t):
        yaz(d, (800, 250 + i * 80 - (len(t) - 1) * 20), s, 64, (170, 30, 40))

GORSEL = {"hal": hal, "etiket": etiket, "domates": domates, "tezgah": tezgah,
          "kalabalik": kalabalik, "para": parayi, "defter": defter}

def oy_katman(sc):
    L = Image.new("RGBA", (W, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    sec = (sc.get("secenek") or ["A", "B"]) + ["", ""]
    for i, (x0, c) in enumerate(((50, (40, 110, 230)), (570, (240, 130, 30)))):
        d.rounded_rectangle((x0, 40, x0 + 460, 520), 40, fill=c, outline="white", width=8)
        d.ellipse((x0 + 150, 70, x0 + 310, 230), fill="white")
        yaz(d, (x0 + 230, 150), "AB"[i], 120, c)
        yaz(d, (x0 + 230, 370), tr_upper(sec[i]), 78, (255, 255, 255), stroke=6, sf=(0, 0, 0))
    yaz(d, (540, 590), "YORUMA  A  veya  B  YAZ", 54, (255, 235, 110), stroke=6)
    return L

def katman(sc):
    if sc.get("tema") == "oylama": return oy_katman(sc)
    L = Image.new("RGBA", (W, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    kisi(d, 270, sc.get("ifade", "gulen"))
    g = sc.get("gorsel"); yazi = sc.get("gorsel_yazi", "")
    if g in GORSEL: GORSEL[g](d, yazi)
    if yazi and g in ("domates", "tezgah", "kalabalik"):
        d.rounded_rectangle((540, 590, 1040, 640), 20, fill=(0, 0, 0))
        yaz(d, (790, 615), yazi, 36)
    return L

def damga_resim(t):
    t = tr_upper(t)
    im = Image.new("RGBA", (960, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, 950, 250), 30, outline=(220, 30, 40), width=14, fill=(255, 255, 255, 235))
    sz = 130
    while font(sz).getlength(t) > 860 and sz > 40: sz -= 6
    yaz(d, (480, 132), t, sz, (220, 30, 40))
    return im.rotate(10, expand=True, resample=Image.BICUBIC)

# ---------------- ses efektleri ----------------
def ton(f, s, vol=.5, ck=6):
    t = np.arange(int(SR * s)) / SR
    return np.sin(2 * np.pi * f * t) * np.exp(-ck * t) * vol
def sfx_coin():
    a = ton(988, .1, .5, 5); b = ton(1319, .45, .5, 6)
    return np.concatenate([a, b])
def sfx_buzz():
    t = np.arange(int(SR * .4)) / SR
    return np.sign(np.sin(2 * np.pi * 110 * t)) * np.exp(-4 * t) * .3
def sfx_thud():
    t = np.arange(int(SR * .4)) / SR
    n = np.random.RandomState(1).randn(len(t)) * np.exp(-30 * t) * .4
    return ton(70, .4, .8, 9) + n
def sfx_whoosh():
    n = np.random.RandomState(2).randn(int(SR * .35))
    k = np.ones(60) / 60; n = np.convolve(n, k, "same")
    e = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    return n * e * 1.8
def sfx_pop():
    return np.concatenate([ton(520, .08, .5, 25), ton(780, .1, .4, 20)])

# ---------------- plan ----------------
def kelime_gruplari(metin):
    ws = metin.split(); gr = []; cur = []
    for w in ws:
        if cur and (len("".join(cur)) + len(w) > 15 or len(cur) >= 3):
            gr.append(cur); cur = []
        cur.append(w)
        if w[-1] in ".?!,": gr.append(cur); cur = []
    if cur: gr.append(cur)
    return [" ".join(g) for g in gr]

def zamanla(metin, dur):
    gr = kelime_gruplari(metin)
    agr = [len(g) + 3 + (6 if g[-1] in ".?!" else 2 if g[-1] == "," else 0) for g in gr]
    top = sum(agr); t = 0.05; out = []
    for g, a in zip(gr, agr):
        l = (dur - 0.15) * a / top
        out.append((t, t + l, tr_upper(g))); t += l
    return out

def plan(veri, sureler):
    sah = []; bas = 0.0; onceki = veri["kasa_basi"]
    for sc, dur in zip(veri["sahneler"], sureler):
        k = sc.get("kasa", onceki)
        sah.append({"sc": sc, "bas": bas, "dur": dur, "once": onceki, "kasa": k,
                    "kat": katman(sc), "damga": damga_resim(sc["damga"]) if sc.get("damga") else None,
                    "cap": zamanla(sc.get("anlatim", ""), dur)})
        bas += dur; onceki = k
    return sah, bas

_C = {}
def chunk_resim(t):
    if t not in _C:
        sz = 108
        while font(sz).getlength(t) > 960 and sz > 40: sz -= 4
        im = Image.new("RGBA", (1040, 200), (0, 0, 0, 0))
        yaz(ImageDraw.Draw(im), (520, 100), t, sz, (255, 228, 60), stroke=11)
        _C[t] = im
    return _C[t]

def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

def kare(veri, sah, toplam, t):
    i = 0
    for k, s in enumerate(sah):
        if s["bas"] <= t: i = k
    s = sah[i]; sc = s["sc"]; lt = t - s["bas"]
    img = zemin(sc.get("tema", "gun")).copy(); d = ImageDraw.Draw(img)
    # illustrasyon: tek yonlu yavas yakinlasma
    z = 1 + 0.07 * (lt / s["dur"])
    cw, ch = W / z, LH / z
    kes = s["kat"].crop((int((W - cw) / 2), int((LH - ch) / 2), int((W + cw) / 2), int((LH + ch) / 2))).resize((W, LH), Image.BILINEAR)
    if lt < .2:  # giris: asagidan kayarak gelir
        img.paste(kes, (0, int(LY + 80 * (1 - ease(lt / .2)))), kes)
    else:
        img.paste(kes, (0, LY), kes)
    # baslik
    bs = textwrap.wrap(tr_upper(sc.get("baslik", "")), 16)[:2]
    for n, satir in enumerate(bs):
        yaz(d, (540, 395 + n * 100), satir, 88, (255, 255, 255), stroke=9)
    # damga
    if s["damga"] is not None and lt > .4:
        p = ease((lt - .4) / .18); sc2 = 1.9 - .9 * p
        st = s["damga"]; st = st.resize((int(st.width * sc2), int(st.height * sc2)), Image.BILINEAR)
        img.paste(st, (540 - st.width // 2, 930 - st.height // 2), st)
    # HUD
    fark = s["kasa"] - s["once"]
    deger = s["once"] + fark * ease(lt / .9)
    renk = (255, 255, 255)
    if fark and lt < 1.6: renk = (90, 235, 120) if fark > 0 else (255, 90, 90)
    d.rounded_rectangle((30, 40, 1050, 340), 36, fill=(12, 16, 42), outline=(245, 200, 60), width=5)
    yaz(d, (70, 85), f"GÜN {veri['gun']}/{veri.get('toplam_gun', 30)}", 40, (245, 200, 60), "lm")
    yaz(d, (1010, 85), "KASA", 40, (200, 205, 235), "rm")
    yaz(d, (540, 170), para(deger), 118, renk, stroke=0)
    oran = max(0.02, min(1, deger / veri["hedef"]))
    d.rounded_rectangle((70, 250, 1010, 285), 16, fill=(50, 55, 95))
    d.rounded_rectangle((70, 250, 70 + int(940 * oran), 285), 16, fill=(245, 200, 60))
    yaz(d, (540, 315), f"HEDEF {para(veri['hedef'])} · {tr_upper(veri.get('hedef_adi', ''))}", 30, (225, 230, 250))
    if fark and .15 < lt < 2.4:
        p = (lt - .15) / 2.25
        yaz(d, (540, 560 - 90 * p), ("+" if fark > 0 else "−") + para(abs(fark)), 96,
            (90, 235, 120) if fark > 0 else (255, 90, 90), stroke=9)
    # altyazi
    for a, b, tx in s["cap"]:
        if a <= lt < b:
            im = chunk_resim(tx); p = ease((lt - a) / .09); sc3 = .8 + .2 * p
            if sc3 < .999: im = im.resize((int(im.width * sc3), int(im.height * sc3)), Image.BILINEAR)
            img.paste(im, (540 - im.width // 2, 1370 - im.height // 2), im)
            break
    # ilerleme cubugu + alt yazi
    d.rectangle((0, 1790, int(W * t / toplam), 1802), fill=(245, 200, 60))
    yaz(d, (540, 1850), "@kasakurgu  ·  kurgusal hikâye", 32, (235, 235, 245))
    return img

# ---------------- ses ----------------
def wav_oku(yol):
    with wave.open(yol, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a

def yaz_wav(yol, a):
    a = np.clip(a, -1, 1)
    with wave.open(yol, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())

async def tts(metin, mp3):
    import edge_tts
    await edge_tts.Communicate(metin, "tr-TR-AhmetNeural", rate="+20%").save(mp3)

def ses_uret(i, metin):
    wav = f"tmp{i}.wav"
    if os.environ.get("SAHTE_SES"):
        n = max(1, len(metin.split())) * 0.34
        yaz_wav(wav, ton(220, n, .2, 0.1)); return wav_oku(wav)
    mp3 = f"tmp{i}.mp3"
    for deneme in range(4):  # edge-tts ara sıra bağlantı hatası veriyor: birkaç kez dene
        try:
            asyncio.run(tts(metin, mp3)); break
        except Exception as e:
            if deneme == 3:
                raise
            print("Ses denemesi başarısız, tekrar:", str(e)[:120]); time.sleep(10 * (deneme + 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", wav], check=True)
    return wav_oku(wav)

def karisim(sah, toplam, sesler):
    buf = np.zeros(int(SR * (toplam + 1)), dtype=np.float32)
    def ekle(x, sn, v=1.0):
        a = int(sn * SR); x = np.asarray(x, dtype=np.float32) * v
        buf[a:a + len(x)] += x[:max(0, len(buf) - a)]
    for n, (s, ses) in enumerate(zip(sah, sesler)):
        pk = np.max(np.abs(ses)) or 1
        ekle(ses / pk * .9, s["bas"] + .05)
        if n > 0: ekle(sfx_whoosh(), s["bas"], .12)
        f = s["kasa"] - s["once"]
        if f > 0: ekle(sfx_coin(), s["bas"] + .12, .45)
        elif f < 0: ekle(sfx_buzz(), s["bas"] + .12, .6)
        if s["damga"] is not None: ekle(sfx_thud(), s["bas"] + .45, .7)
        if s["sc"].get("tema") == "oylama": ekle(sfx_pop(), s["bas"] + .1, .6)
    if os.path.exists("muzik.mp3"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "muzik.mp3", "-ar", str(SR), "-ac", "1", "muzik.wav"], check=True)
        m = wav_oku("muzik.wav"); m = np.tile(m, int(len(buf) / max(1, len(m))) + 1)[:len(buf)]
        buf += m * .09
    return buf

# ---------------- ana ----------------
def tahmin(veri):
    return [max(1.6, len(sc.get("anlatim", "").split()) * 0.34 + .3) for sc in veri["sahneler"]]

def onizleme(dosya):
    veri = json.load(open(dosya, encoding="utf-8"))
    sah, top = plan(veri, tahmin(veri))
    for n, s in enumerate(sah):
        kare(veri, sah, top, s["bas"] + min(1.4, s["dur"] - .1)).save(f"onizleme_{n+1:02d}.png")
    print("hazir:", len(sah), "kare,", round(top, 1), "sn")

def main(dosya):
    veri = json.load(open(dosya, encoding="utf-8"))
    sesler = []; sureler = []
    for i, sc in enumerate(veri["sahneler"]):
        a = ses_uret(i, sc.get("anlatim", ""))
        sesler.append(a); sureler.append(len(a) / SR + (.2 if i == 0 else .32))
    sah, top = plan(veri, sureler)
    yaz_wav("ses.wav", karisim(sah, top, sesler))
    kare(veri, sah, top, 1.0).save("kapak.png")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", "ses.wav",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-t", f"{top:.2f}", "-movflags", "+faststart", "cikti.mp4"],
                         stdin=subprocess.PIPE)
    for n in range(int(top * FPS)):
        p.stdin.write(kare(veri, sah, top, n / FPS).tobytes())
    p.stdin.close(); p.wait()
    print("tamam:", round(top, 1), "sn")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "onizleme": onizleme(sys.argv[1])
    else: main(sys.argv[1])
