# Gizli Tarih "Ne Olur?" Shorts serisi – 2 günde bir yeni bölüm (uzun belgesellerle aynı güne denk gelmez).
# Akış: sıradaki bölüm → Levent'in ücretsiz klon sesi (Chatterbox) → yazıya döküp kontrol (faster-whisper)
#       → kodla çizilen video → müzik → Gizli Tarih YouTube kuyruğu (sabit saat) → TikTok için Telegram'a video.
# Kullanım:
#   python neolur/uret.py otomatik            # bugün üretilmesi gerekiyorsa üretir (her gün çalışır)
#   python neolur/uret.py zorla                # sıradaki bölümü hemen üretir
#   python neolur/uret.py hazir <mp4> <id>     # hazır videoyu (elektrik) sıraya koyar
#   python neolur/uret.py dene <bolum_id> <klasor>   # sessiz yerel deneme (tahmini süreler)
import datetime as dt, difflib, glob, json, os, re, subprocess, sys

KLASOR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(KLASOR)
sys.path.insert(0, KOK)
sys.path.insert(0, KLASOR)
TR = dt.timezone(dt.timedelta(hours=3))
ARALIK_GUN = 2
# Shorts saati: belgeseller 17:30–18:30 arası çıkıyor; kısa videolar akşam en yoğun saatte, diğer kanallardan 30 dk uzak
SAAT_TERCIH = ["20:45", "21:15", "19:45", "21:45", "20:15", "22:00"]
VO, ARA = 0.3, 0.18
TIKTOK_ETIKET = "#neolur #bilgi #merak #senaryo #keşfet #fyp"


def sh(*a, **k):
    return subprocess.run(list(a), check=True, **k)


def sure_olc(yol):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                                capture_output=True, text=True).stdout)


# ---------------- zamanlama ----------------
def zamanla(bolum, sureler):
    """sureler: {sahne_ad: [parça süreleri]} → render.py'nin istediği zaman tablosu + seslerin konumları."""
    z, konum, t = {}, [], 0.0
    for i, s in enumerate(bolum["sahneler"]):
        ad = f"{i:02d}_{s['tip']}"
        d = sureler[ad]
        vo = 0.1 if s["tip"] == "kanca" else VO
        bas, c = [], vo
        for x in d:
            bas.append(c)
            c += x + ARA
        konum += [(ad, j, t + b) for j, b in enumerate(bas)]
        if s["tip"] == "kanca":
            gorun = [bas[0] + f * d[0] for f in (0.0, 0.22, 0.5, 0.68)]
            z["an"] = t + bas[0] + 0.5 * d[0]
        elif s["tip"] == "son":
            gorun = [bas[0], bas[0] + 0.4 * d[0]]
        else:
            grup = s.get("grup") or list(range(len(s["satir"])))
            gorun = [max(0.05, bas[g] - 0.1) for g in grup]
        kuyruk = 1.6 if s["tip"] == "son" else 0.5
        sure = round(c - ARA + kuyruk, 3)
        z[ad] = {"sure": sure, "gorun": [round(x, 3) for x in gorun]}
        t += sure
    z["toplam"] = t
    return z, konum


# ---------------- ses ----------------
def normal(m):
    m = m.lower().replace("â", "a").replace("î", "i").replace("û", "u")
    return re.sub(r"[^a-zçğıöşü0-9 ]", "", m.replace("'", "")).split()


def benzerlik(a, b):
    return difflib.SequenceMatcher(None, " ".join(normal(a)), " ".join(normal(b))).ratio()


def kirp(src, hedef):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "s16le", "-ac", "1", "-ar", "44100", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(float) / 32768
    w = int(0.05 * 44100)
    rms = np.array([20 * np.log10(np.sqrt(np.mean(a[i:i + w] ** 2)) + 1e-9) for i in range(0, len(a), w)])
    yuksek = np.where(rms > -30)[0]
    bas = max(0.0, yuksek[0] * 0.05 - 0.05)
    son = min(len(a) / 44100, (yuksek[-1] + 1) * 0.05 + 0.12)
    sh("ffmpeg", "-v", "error", "-y", "-i", src, "-af",
       f"atrim={bas}:{son},asetpts=N/SR/TB,afade=t=out:st={son - bas - 0.08:.3f}:d=0.08,loudnorm=I=-16:TP=-1.5",
       "-ar", "44100", "-ac", "1", hedef)
    return sure_olc(hedef)


def seslendir(bolum, cikti):
    import ucretsiz_ses
    from faster_whisper import WhisperModel
    kulak = WhisperModel("medium", device="cpu", compute_type="int8")
    sureler, sorunlar = {}, []
    for i, s in enumerate(bolum["sahneler"]):
        ad = f"{i:02d}_{s['tip']}"
        sureler[ad] = []
        for j, metin in enumerate(s["ses"]):
            hedef = os.path.join(cikti, f"{ad}_{j}.wav")
            en_iyi = (-1, None, "")
            for deneme in range(3):
                ham = f"/tmp/ham_{ad}_{j}_{deneme}.wav"
                ucretsiz_ses.oku(bolum.get("tarz", "belgesel"), metin, ham)
                segs, _ = kulak.transcribe(ham, language="tr")
                duyulan = " ".join(x.text.strip() for x in segs)
                oran = benzerlik(metin, duyulan)
                print(f"{ad}/{j} deneme {deneme + 1}: %{oran * 100:.0f} | {duyulan}", flush=True)
                if oran > en_iyi[0]:
                    en_iyi = (oran, ham, duyulan)
                if oran >= 0.86:
                    break
            if en_iyi[0] < 0.86:
                sorunlar.append(f"{ad}/{j}: \"{metin}\" → duyulan: \"{en_iyi[2]}\" (%{en_iyi[0] * 100:.0f})")
            sureler[ad].append(kirp(en_iyi[1], hedef))
    return sureler, sorunlar


# ---------------- müzik ----------------
def muzik(v, yol):
    import numpy as np, wave
    SR = 44100
    n = int(v.toplam * SR) + SR
    t = np.arange(n) / SR
    L, R = np.zeros(n), np.zeros(n)
    rng = np.random.default_rng(1)

    def ekle(sig, bas, k=1.0):
        i = int(bas * SR); j = min(n, i + len(sig))
        if i < n:
            L[i:j] += sig[:j - i] * k; R[i:j] += sig[:j - i] * k

    def zarf(a, b, ta=0.5, tb=0.8):
        return np.clip((t - a) / ta, 0, 1) * np.clip((b - t) / tb, 0, 1)

    an = v.an
    hum = (0.05 * np.sin(2 * np.pi * 100 * t) + 0.02 * np.sin(2 * np.pi * 200 * t) + 0.012 * rng.standard_normal(n))
    hum *= np.clip((an - t) / 0.08, 0, 1)
    L += hum; R += hum
    tt = np.arange(int(1.4 * SR)) / SR
    if v.efekt in ("karartma", "soguk", "ay", "uydu", "normal"):
        f = 240 * np.exp(-tt * 2.6) + 28
        faz = 2 * np.pi * np.cumsum(f) / SR
        ekle((np.sin(faz) + 0.4 * np.sin(2 * faz)) * np.exp(-tt * 2.2) * 0.35, an)
    ekle(np.sin(2 * np.pi * 42 * tt * np.exp(-tt * 0.6)) * np.exp(-tt * 2.5) * 0.7, an)
    dr = np.zeros(n)
    for fr, a in [(55, 0.16), (82.4, 0.09), (110.3, 0.05), (164.8, 0.025)]:
        dr += a * np.sin(2 * np.pi * fr * t + 0.6 * np.sin(2 * np.pi * 0.11 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.23 * t + fr))
    dr *= zarf(an + 0.3, v.vurgu_bas + 0.6, 1.5, 1.2)
    L += dr; R += dr * 0.95
    A = v.asama_bas
    kalp = np.sin(2 * np.pi * 50 * np.arange(int(0.18 * SR)) / SR) * np.exp(-np.arange(int(0.18 * SR)) / SR * 28) * 0.55
    z = A[2] if len(A) > 3 else v.vurgu_bas
    while z < v.vurgu_bas - 0.3:
        ekle(kalp, z); ekle(kalp * 0.7, z + 0.24)
        z += 1.0 - 0.35 * (z - A[2]) / max(1, v.vurgu_bas - A[2])
    for s in v.sahneler[1:]:
        hit = np.sin(2 * np.pi * 60 * tt * np.exp(-tt * 1.2)) * np.exp(-tt * 4) * 0.55
        ekle(hit[:int(0.9 * SR)] + rng.standard_normal(int(0.9 * SR)) * np.exp(-tt[:int(0.9 * SR)] * 30) * 0.12, s["bas"])
    pad = np.zeros(n)
    for fr, a in [(130.8, 0.06), (196.0, 0.05), (261.6, 0.04), (329.6, 0.03), (392.0, 0.02)]:
        pad += a * np.sin(2 * np.pi * fr * t) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.3 * t + fr))
    pad *= zarf(v.vurgu_bas, v.toplam, 1.2, 1.6)
    L += pad; R += pad
    fade = np.clip((v.toplam - t) / 1.2, 0, 1)
    L *= fade; R *= fade
    st = np.stack([L, R], 1)[: int(v.toplam * SR)]
    st = st / np.abs(st).max() * 0.89
    with wave.open(yol, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


def birlestir(v, konum, ses_klasor, klasor, cikti):
    from render import Video  # noqa
    dosyalar = v.render(klasor)
    liste = os.path.join(klasor, "liste.txt")
    open(liste, "w").writelines(f"file '{d}'\n" for d in dosyalar)
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", os.path.join(klasor, "sessiz.mp4"))
    muzik(v, os.path.join(klasor, "muzik.wav"))
    girdi, flt = ["-i", os.path.join(klasor, "muzik.wav")], []
    for k, (ad, j, bas) in enumerate(konum):
        girdi += ["-i", os.path.join(ses_klasor, f"{ad}_{j}.wav")]
        ms = int(bas * 1000)
        flt.append(f"[{k + 1}:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{k}]")
    flt.append("".join(f"[v{k}]" for k in range(len(konum))) + f"amix=inputs={len(konum)}:normalize=0[ses]")
    flt.append("[0:a]volume=0.30[muz]")
    flt.append("[muz][ses]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    sh("ffmpeg", "-v", "error", "-y", *girdi, "-filter_complex", ";".join(flt), "-map", "[out]", "-ar", "44100",
       "-t", f"{v.toplam:.3f}", os.path.join(klasor, "karisim.wav"))
    sh("ffmpeg", "-v", "error", "-y", "-i", os.path.join(klasor, "sessiz.mp4"), "-i", os.path.join(klasor, "karisim.wav"),
       "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", cikti)


# ---------------- yayın ----------------
def yayin_saati(tarih):
    from yt_kuyruk import dolu_zamanlar
    dolu = dolu_zamanlar()
    simdi = dt.datetime.now(TR)
    for saat in SAAT_TERCIH:
        hh, mm = map(int, saat.split(":"))
        aday = dt.datetime(tarih.year, tarih.month, tarih.day, hh, mm, tzinfo=TR)
        if aday < simdi + dt.timedelta(minutes=45):
            continue
        if not any(abs((aday - z).total_seconds()) < (3600 if k == "gizlitarih" else 1800) for k, z in dolu):
            return aday
    return dt.datetime(tarih.year, tarih.month, tarih.day, 22, 15, tzinfo=TR)


def aciklama(b):
    return (f"{b['ozet']}\n\nBu video bir senaryodur; bilgiler genel bilimsel tahminlere dayanır, kesin tahmin değildir. "
            f"Görseller temsilidir, seslendirme yapay zekâ ile üretilmiştir.\n\n"
            f"🌍 \"Ne Olur?\" serisi: her iki günde bir yeni senaryo. Sıradaki için abone ol!\n\n#shorts #neolur #gizlitarih")


def kuyruga_koy(b, mp4, zaman):
    import yt_kuyruk
    from yt_ortak import telegram
    os.environ["SABIT_YAYIN"] = zaman.isoformat()
    yt_kuyruk.ekle("gizlitarih", mp4, b["baslik"], aciklama(b), ",".join(b["etiketler"]))
    # TikTok: Gizli Tarih'in TikTok bağlantısı yok → Levent elle yükler, video + hazır açıklama Telegram'a
    tt_baslik = b["baslik"].replace(" #shorts", "")
    metin = (f"📱 TikTok'a yüklenecek · Gizli Tarih \"Ne Olur?\"\n🕘 Önerilen saat: {zaman:%d.%m %H:%M} "
             f"(YouTube ile aynı)\n\nAçıklama (kopyala):\n{tt_baslik} Sen olsan ne yapardın? 👇 {TIKTOK_ETIKET}")
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok:
        import requests
        with open(mp4, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{tok}/sendVideo", timeout=300, files={"video": f},
                              data={"chat_id": chat, "caption": metin[:1024], "supports_streaming": "true"}).json()
        if not r.get("ok"):
            telegram(metin + "\n\n(Video Telegram'a gönderilemedi: " + str(r)[:200] + ")")


def durum_yaz(d):
    json.dump(d, open(os.path.join(KLASOR, "durum.json"), "w"), indent=1, ensure_ascii=False)


def uret(b, tarih):
    from render import Video
    klasor = f"/tmp/neolur_{b['id']}"
    os.makedirs(klasor, exist_ok=True)
    sureler, sorunlar = seslendir(b, klasor)
    zaman, konum = zamanla(b, sureler)
    if zaman["toplam"] > 58.8 and any(s["tip"] == "liste" for s in b["sahneler"]):
        # 60 sn sınırı: "liste" sahnesini çıkar (sesleri de), yeniden zamanla
        i = next(i for i, s in enumerate(b["sahneler"]) if s["tip"] == "liste")
        eski = f"{i:02d}_liste"
        b = dict(b, sahneler=[s for s in b["sahneler"] if s["tip"] != "liste"])
        yeni = {}
        for k, x in enumerate(b["sahneler"]):
            ad = f"{k:02d}_{x['tip']}"
            eski_ad = ad if k < i else f"{k + 1:02d}_{x['tip']}"
            yeni[ad] = sureler[eski_ad]
            if eski_ad != ad:
                for j in range(len(x["ses"])):
                    os.replace(os.path.join(klasor, f"{eski_ad}_{j}.wav"), os.path.join(klasor, f"{ad}_{j}.wav"))
        sureler = yeni
        zaman, konum = zamanla(b, sureler)
        print("Süre sınırı için liste sahnesi çıkarıldı:", eski)
    v = Video(b, zaman)
    mp4 = os.path.join(klasor, f"neolur_{b['id']}.mp4")
    birlestir(v, konum, klasor, klasor, mp4)
    print("Video:", mp4, f"{sure_olc(mp4):.1f} sn")
    if sure_olc(mp4) > 59.5:
        raise RuntimeError("Video 60 saniyeyi geçti; Shorts sayılmaz. Metni kısalt.")
    return mp4, sorunlar


def main():
    komut = sys.argv[1]
    d = json.load(open(os.path.join(KLASOR, "durum.json")))
    banka = json.load(open(os.path.join(KLASOR, "bolumler.json"), encoding="utf-8"))["bolumler"]
    if komut == "dene":
        from render import Video
        b = next(x for x in banka if x["id"] == sys.argv[2])
        sureler = {f"{i:02d}_{s['tip']}": [len(m) / 14.5 for m in s["ses"]] for i, s in enumerate(b["sahneler"])}
        zaman, _ = zamanla(b, sureler)
        print("toplam", round(zaman["toplam"], 1))
        json.dump(zaman, open(os.path.join(sys.argv[3], f"zaman_{b['id']}.json"), "w"))
        return
    from yt_ortak import telegram
    if komut == "hazir":
        tarih = dt.date.fromisoformat(d["son_tarih"])
        b = {"id": sys.argv[3], "baslik": "Dünyada Elektrikler Tamamen Kesilirse Ne Olur? ⚡ #shorts",
             "ozet": "Dünyada elektrikler bir anda tamamen kesilseydi ilk saatlerden haftalar sonrasına kadar neler olurdu? "
                     "Su, gıda ve hazırlık için en önemli adımlar.",
             "etiketler": ["ne olur", "elektrik kesilirse", "elektriksiz dünya", "hayatta kalma", "senaryo", "merak",
                           "Gizli Tarih", "shorts"]}
        kuyruga_koy(b, sys.argv[2], yayin_saati(tarih))
        return
    bugun = dt.datetime.now(TR).date()
    hedef = dt.date.fromisoformat(d["son_tarih"]) + dt.timedelta(days=ARALIK_GUN)
    if komut == "gerek":
        print("evet" if (hedef - bugun).days <= 1 and d["sira"] < len(banka) else "hayir")
        return
    if komut == "otomatik" and (hedef - bugun).days > 1:
        print(f"Bugün üretim yok. Sıradaki yayın günü: {hedef}")
        return
    if hedef < bugun:
        hedef = bugun + dt.timedelta(days=1) if dt.datetime.now(TR).hour >= 19 else bugun
    if d["sira"] >= len(banka):
        telegram("⚠️ Gizli Tarih \"Ne Olur?\" serisinde yeni bölüm kalmadı. Claude'a yeni senaryolar yazdır.")
        return
    b = banka[d["sira"]]
    mp4, sorunlar = uret(b, hedef)
    zaman = yayin_saati(hedef)
    kuyruga_koy(b, mp4, zaman)
    d["sira"] += 1
    d["son_tarih"] = hedef.isoformat()
    d["gecmis"].append({"id": b["id"], "tarih": hedef.isoformat(), "saat": f"{zaman:%H:%M}"})
    durum_yaz(d)
    kalan = len(banka) - d["sira"]
    if sorunlar:
        telegram("🔎 Ne Olur? ses kontrolü: bazı cümleler tam anlaşılmadı, videoyu bir dinle:\n" + "\n".join(sorunlar)[:3500])
    if kalan <= 2:
        telegram(f"ℹ️ Gizli Tarih \"Ne Olur?\" serisinde {kalan} bölüm kaldı. Claude'a yeni senaryolar yazdır.")


if __name__ == "__main__":
    main()
