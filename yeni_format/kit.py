# Ortak görsel + ses kiti: üç pilot (Dükkan TV neon, Drama Bite mesaj, Kasa Kurgu dedektif) bunu kullanır.
import math, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, SR = 1080, 1920, 30, 44100

_FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fontlar")   # Inter (OFL), FreeMono, DejaVu
FONTS = {
    "black": os.path.join(_FD, "InterDisplay-Black.otf"),
    "xbold": os.path.join(_FD, "InterDisplay-ExtraBold.otf"),
    "bold": os.path.join(_FD, "Inter-Bold.otf"),
    "semi": os.path.join(_FD, "Inter-SemiBold.otf"),
    "reg": os.path.join(_FD, "Inter-Regular.otf"),
    "med": os.path.join(_FD, "Inter-Medium.otf"),
    "mono": os.path.join(_FD, "FreeMonoBold.ttf"),
    "sembol": os.path.join(_FD, "DejaVuSans-Bold.ttf"),
}
_F = {}


def font(kind, size):
    k = (kind, int(size))
    if k not in _F:
        _F[k] = ImageFont.truetype(FONTS[kind], int(size))
    return _F[k]


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


# ---------- zaman yardımcıları ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def back_out(x, s=1.7):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


# ---------- çizim yardımcıları ----------
def text_size(txt, f):
    b = f.getbbox(txt)
    return b[2] - b[0], b[3] - b[1]


def wrap(txt, f, maxw):
    lines, cur = [], ""
    for w in txt.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def glow_text(img, xy, txt, f, color, glow=18, strength=2, anchor="mm", alpha=1.0):
    """Neon yazı: bulanık kopya + net yazı."""
    if alpha <= 0:
        return
    L = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.text(xy, txt, font=f, fill=color + (255,), anchor=anchor)
    g = fast_blur(L, glow)
    for _ in range(strength):
        paste_alpha(img, g, alpha)
    paste_alpha(img, L, alpha)


def fast_blur(layer, radius):
    """Bulanıklaştırmayı küçültülmüş kopyada yapar (çok daha hızlı)."""
    k = 4
    sm = layer.resize((max(1, layer.width // k), max(1, layer.height // k)), Image.BILINEAR)
    sm = sm.filter(ImageFilter.GaussianBlur(max(1, radius / k)))
    return sm.resize(layer.size, Image.BILINEAR)


def paste_alpha(img, layer, alpha=1.0):
    if alpha < 1:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer = layer.copy()
        layer.putalpha(a)
    img.alpha_composite(layer)


def stamp(img, cx, cy, txt, f, color=(255, 45, 70), t=1.0, angle=-6, pad=(46, 26), glow=True):
    """Ekrana çarpan damga yazı: büyükten küçüğe iner, hafif sallanır."""
    if t <= 0:
        return
    k = ease_out(t)
    scale = 1.9 - 0.9 * k
    alpha = clamp(t * 3)
    tw, th = text_size(txt, f)
    bw, bh = tw + pad[0] * 2, th + pad[1] * 2 + 10
    L = Image.new("RGBA", (bw + 80, bh + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((40, 40, 40 + bw, 40 + bh), radius=18, outline=color + (255,), width=10)
    d.text((40 + bw / 2, 40 + bh / 2), txt, font=f, fill=color + (255,), anchor="mm")
    L = L.rotate(angle, resample=Image.BICUBIC, expand=True)
    L = L.resize((max(1, int(L.width * scale)), max(1, int(L.height * scale))), Image.BICUBIC)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lay.alpha_composite(L, (int(cx - L.width / 2), int(cy - L.height / 2)))
    if glow:
        g = fast_blur(lay, 16)
        paste_alpha(img, g, alpha)
    paste_alpha(img, lay, alpha)


def vignette(w, h, strength=0.75):
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    r = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2) / 1.42
    v = 1 - strength * np.clip(r, 0, 1) ** 1.8
    return v.astype(np.float32)


def grain(arr, amount=6, seed=None):
    rng = np.random.default_rng(seed)
    n = rng.integers(-amount, amount + 1, size=arr.shape[:2], dtype=np.int16)[..., None]
    return np.clip(arr.astype(np.int16) + n, 0, 255).astype(np.uint8)


# ---------- video yazıcı ----------
class Writer:
    def __init__(self, path, dur):
        self.path, self.n = path, int(round(dur * FPS))
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", path],
            stdin=subprocess.PIPE)

    def write(self, img):
        if img.mode != "RGB":
            img = img.convert("RGB")
        self.p.stdin.write(img.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def render(path, dur, frame_fn):
    w = Writer(path, dur)
    for i in range(w.n):
        w.write(frame_fn(i / FPS))
    w.close()


# ---------- ses sentezi (ücretsiz, harici dosya yok) ----------
def silence(dur):
    return np.zeros(int(dur * SR), np.float32)


def env(n, a=0.005, r=0.1):
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    # tek kutuplu basit alçak geçiren
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # kısa sesler için yeterince hızlı
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lp_fast(x, cutoff):
    # uzun sinyaller için FFT ile alçak geçiren
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def sfx_whoosh(dur=0.45, up=True):
    n = int(dur * SR)
    noise = np.random.default_rng(1).standard_normal(n).astype(np.float32)
    t = np.linspace(0, 1, n)
    shape = np.sin(np.pi * t) ** 2
    out = lp_fast(noise, 2500) * shape
    return 0.35 * out / (np.abs(out).max() + 1e-6)


def sfx_thud(dur=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 9) + 45
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    click = np.random.default_rng(2).standard_normal(n) * np.exp(-t * 60) * 0.5
    out = (body + lp_fast(click.astype(np.float32), 3000)).astype(np.float32)
    return 0.9 * out / np.abs(out).max()


def sfx_pop(freq=880, dur=0.09):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.6 * np.exp(-t * 60))
    out = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35)
    return (0.35 * out).astype(np.float32)


def sfx_ding():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    out = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318.5, 0.5), (1975.5, 0.25), (2637, 0.1)])
    return (0.3 * out * np.exp(-t * 5)).astype(np.float32)


def sfx_type(n_keys=1, gap=0.07, seed=0):
    rng = np.random.default_rng(seed)
    out = silence(n_keys * gap + 0.08)
    for k in range(n_keys):
        m = int(0.03 * SR)
        click = rng.standard_normal(m).astype(np.float32) * np.exp(-np.arange(m) / SR * 220)
        click = lp_fast(click, 4000 + rng.uniform(-800, 800)) * rng.uniform(0.6, 1.0)
        s = int(k * gap * SR * rng.uniform(0.8, 1.2))
        if s >= len(out):
            continue
        e = min(len(out), s + m)
        out[s:e] += click[: e - s]
    return 0.5 * out / (np.abs(out).max() + 1e-6)


def sfx_shutter():
    a = sfx_type(1, seed=5) * 1.2
    b = sfx_type(1, seed=7)
    out = silence(0.2)
    out[: len(a)] += a
    s = int(0.06 * SR)
    out[s:s + len(b)] += b[: len(out) - s]
    return out


def sfx_tick():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return (0.4 * np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 120)).astype(np.float32)


def sfx_riser(dur=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 200 + 900 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = lp_fast(np.random.default_rng(3).standard_normal(n).astype(np.float32), 3000) * 0.3
    return ((tone + noise) * (t / dur) ** 2).astype(np.float32) * 0.5


def note(freq, dur, kind="sine", vol=0.2, a=0.01, r=0.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "piano":
        w = sum(np.sin(2 * np.pi * freq * h * t) / h ** 1.4 for h in (1, 2, 3, 4)) * np.exp(-t * 2.2)
    elif kind == "pad":
        w = sum(np.sin(2 * np.pi * freq * d * t + d) for d in (1, 1.003, 0.997, 2.001)) / 4
    elif kind == "saw":
        w = 2 * ((freq * t) % 1) - 1
    else:
        w = np.sin(2 * np.pi * freq * t)
    return (vol * w * env(n, a, r)).astype(np.float32)


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


class Mix:
    def __init__(self, dur):
        self.buf = silence(dur + 1)
        self.dur = dur

    def add(self, sig, at, vol=1.0):
        s = int(at * SR)
        if s >= len(self.buf):
            return
        e = min(len(self.buf), s + len(sig))
        self.buf[s:e] += vol * sig[: e - s]

    def save(self, path):
        x = self.buf[: int(self.dur * SR)]
        x = x / (np.abs(x).max() + 1e-6) * 0.89
        pcm = (x * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-c:v", "copy", "-af",
                    "loudnorm=I=-15:TP=-1.5", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    out], check=True)


# ---------- seslendirme: Levent'in ücretsiz klon sesi (Chatterbox), olmazsa edge-tts ----------
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wav_oku(yol):
    """Herhangi bir ses dosyasını 44.1 kHz mono float32 diziye çevirir."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def _edge(metin, yol, ses="tr-TR-AhmetNeural", hiz="+8%"):
    import asyncio
    import edge_tts
    mp3 = yol.rsplit(".", 1)[0] + ".mp3"
    asyncio.run(edge_tts.Communicate(metin, ses, rate=hiz).save(mp3))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, yol], check=True)
    return yol


def _onbellek_yolu(tarz, metin):
    import hashlib
    d = os.environ.get("SES_ONBELLEK")
    if not d:
        return None
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, hashlib.md5(f"{tarz}|{metin}".encode()).hexdigest() + ".wav")


def seslendir(tarz, metin, yol):
    """Önbellekte varsa onu kullanır (paralel ses işleri doldurur); yoksa üretir ve önbelleğe de koyar."""
    ob = _onbellek_yolu(tarz, metin)
    if ob and os.path.exists(ob) and not os.environ.get("SESSIZ_TEST"):
        subprocess.run(["cp", ob, yol], check=True)
        return wav_oku(yol), "klon"
    s, k = _seslendir(tarz, metin, yol)
    if ob and k != "test":
        subprocess.run(["cp", yol, ob], check=True)
    return s, k


def _seslendir(tarz, metin, yol):
    """Önce klon ses; o çalışmazsa edge-tts; test modunda (SESSIZ_TEST=1) metin uzunluğunda sessizlik."""
    if os.environ.get("SESSIZ_TEST"):
        n = int(SR * (0.6 + len(metin) / 15))
        x = np.zeros(n, np.float32)
        Mix_tmp = (x * 32767).astype(np.int16)
        with wave.open(yol, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(Mix_tmp.tobytes())
        return wav_oku(yol), "test"
    if not os.environ.get("KLON_YOK"):
        try:
            import sys
            sys.path.insert(0, KOK)
            import ucretsiz_ses
            ucretsiz_ses.oku(tarz, metin, yol)
            return wav_oku(yol), "klon"
        except Exception as e:  # model yüklenemezse video yine çıksın
            print("Klon ses çalışmadı, edge-tts'e geçiliyor:", str(e)[:200])
    _edge(metin, yol)
    return wav_oku(yol), "edge"


def tg_video(yol, yazi):
    import requests
    t, c = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not t:
        print("Telegram yok, gönderilmedi")
        return
    with open(yol, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{t}/sendVideo", timeout=300, files={"video": f},
                          data={"chat_id": c, "caption": yazi[:1000], "supports_streaming": "true"})
    print("Telegram:", r.status_code)


def sikistir(girdi, cikti, ses=None):
    """Kumlanma (grain) dosyayı şişirmesin diye hafif gürültü temizleme + makul kalite."""
    a = ["ffmpeg", "-v", "error", "-y", "-i", girdi]
    if ses:
        a += ["-i", ses]
    a += ["-vf", "hqdn3d=6:5:8:8", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p"]
    if ses:
        a += ["-af", "loudnorm=I=-15:TP=-1.5", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    a += ["-movflags", "+faststart", cikti]
    subprocess.run(a, check=True)
