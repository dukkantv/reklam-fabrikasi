# GTA 6 özel bölümü (19 Kasım 2026): Levent'in gönderdiği 3 sessiz klibi (kanca, mizah, kapanış) birleştirir,
# altyazılara denk gelecek şekilde Levent & Cemo seslerini (ücretsiz edge-tts) ve telifsiz müziği ekler.
# Kullanım: python gta6/birlestir.py  ->  gta6/cikti.mp4
import os, subprocess, sys, wave

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "arena"))
import carsi_ses  # noqa: E402
import muzik      # noqa: E402

SR = carsi_ses.SR
BURA = os.path.join(KOK, "gta6")
KLIP = 10.0  # her klip 10 sn

# Haber spikeri (kanca başlığı): normal hızda, net
carsi_ses.SESLER["N"] = {"voice": "tr-TR-AhmetNeural", "rate": "+10%", "pitch": "+0Hz"}

# (başlangıç sn, bitiş sn, kim, metin) — süreler videodaki altyazı değişimlerinden ölçüldü
SATIRLAR = [
    # Bölüm 1 — kanca
    (0.05, 3.15, "N", "GTA 6 yüzünden dükkân kapandı, ama asıl olay bu değil!"),
    (3.30, 6.55, "L", "Abi, esnaf bile kepenk indirmiş. Bugün herkes izinli!"),
    (6.70, 9.90, "C", "On üç yıl bekledik evlat, dükkân mı kalır ortada!"),
    # Bölüm 2 — mizah
    (10.15, 13.35, "L", "Leonida sahilleri efsane, grafikler şahane..."),
    (13.50, 16.95, "C", "İyi güzel de... Menüde yine Türkçe dil desteği yok!"),
    (17.10, 19.90, "C", "İngilizceyi yine GTA'dan sökeceğiz galiba!"),
    # Bölüm 3 — kapanış
    (20.15, 23.55, "L", "Peki sen bugün GTA 6 için işten izin alır mıydın?"),
    (23.70, 26.95, "C", "Yoksa Türkçe olmadan oynanmaz mı diyorsun?"),
    (27.10, 29.80, "L", "Yorumlara yaz, orada buluşalım!"),
]


MOTOR = os.environ.get("GTA_SES", "ucretsiz")   # ucretsiz (edge-tts) / eleven (ElevenLabs v3)
ELEVEN_KEY = "".join(os.environ.get("ELEVENLABS_API_KEY", "").split())


def _eleven_ses(kim):
    """L: Levent (Fatih Yıldırım), C: Cemo (Doga), N: anlatıcı = Levent'in kendi ses klonu."""
    import json
    if kim == "N":
        return json.load(open(os.path.join(KOK, "sesler", "levent_klon.json")))["voice_id"], \
            {"stability": 0.5, "similarity_boost": 0.85}
    ad = {"L": "levent", "C": "cemo"}[kim]
    vid = json.load(open(os.path.join(KOK, "karakterler", "sesler.json")))[ad]["voice_id"]
    a = json.load(open(os.path.join(KOK, "karakterler", "karakterler.json")))["karakterler"][ad].get("eleven", {})
    return vid, {"stability": a.get("stability", 0.5), "similarity_boost": a.get("similarity_boost", 0.85)}


def eleven_kalan():
    import requests
    try:
        j = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": ELEVEN_KEY}, timeout=60).json()
        return j["character_limit"] - j["character_count"]
    except Exception as e:
        print("ElevenLabs kredi okunamadı:", str(e)[:120])
        return None


def _kirp(d):
    """Baştaki/sondaki sessizliği atar."""
    w = int(0.02 * SR)
    rms = np.array([np.sqrt(np.mean(d[i:i + w] ** 2)) for i in range(0, len(d), w)])
    yuksek = np.where(rms > 0.01)[0]
    if not len(yuksek):
        return d
    return d[max(0, yuksek[0] * w - int(0.03 * SR)):min(len(d), (yuksek[-1] + 1) * w + int(0.08 * SR))]


def eleven_tek(metin, kim, pay):
    """ElevenLabs v3 ile seslendirir; yuvaya sığmazsa 3 kez dener, en kısasını en çok 1,3 kat hızlandırır.
    Kelime kesmez: yine sığmazsa hata verir."""
    import requests, tempfile
    vid, ayar = _eleven_ses(kim)
    en_iyi = None
    for deneme in range(3):
        for bekle in range(5):
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers={"xi-api-key": ELEVEN_KEY},
                              params={"output_format": "mp3_44100_128"}, timeout=180,
                              json={"text": metin, "model_id": "eleven_v3", "language_code": "tr", "voice_settings": ayar})
            if r.status_code == 429 or r.status_code >= 500:
                import time; time.sleep(5 * (bekle + 1)); continue
            break
        if not r.ok:
            raise SystemExit(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        with tempfile.TemporaryDirectory() as td:
            mp3, ham = os.path.join(td, "s.mp3"), os.path.join(td, "s.f32")
            open(mp3, "wb").write(r.content)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", str(SR), "-f", "f32le", ham], check=True)
            d = _kirp(np.fromfile(ham, np.float32))
        sure = len(d) / SR
        print(f"  {kim} deneme {deneme + 1}: {sure:.2f} sn (yuva {pay:.2f} sn)", flush=True)
        if en_iyi is None or sure < len(en_iyi) / SR:
            en_iyi = d
        if sure <= pay:
            break
    hiz = len(en_iyi) / SR / pay
    if hiz > 1.3:
        print(f"SIĞMADI ({hiz:.2f} kat hızlanması gerekirdi): {metin}", flush=True)
        return None
    d = en_iyi
    if hiz > 1.0:
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a.f32"), os.path.join(td, "b.f32")
            d.astype(np.float32).tofile(a)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", a,
                            "-af", f"atempo={hiz:.3f}", "-f", "f32le", b], check=True)
            d = np.fromfile(b, np.float32)
    return d / max(1e-6, np.abs(d).max()) * 0.9


def kontrol_et(parcalar):
    """Her satırı yazıya döküp metinle karşılaştırır (faster-whisper kuruluysa)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("faster-whisper yok, ses kontrolü atlandı"); return
    import difflib, re, tempfile
    kulak = WhisperModel("small", device="cpu", compute_type="int8")
    norm = lambda m: " ".join(re.sub(r"[^a-zçğıöşü0-9 ]", "", m.lower().replace("'", "").replace("â", "a")).split())
    kotu = []
    for metin, d in parcalar:
        with tempfile.NamedTemporaryFile(suffix=".wav") as t:
            wav_yaz(t.name, d)
            duyulan = " ".join(s.text.strip() for s in kulak.transcribe(t.name, language="tr")[0])
        oran = difflib.SequenceMatcher(None, norm(metin), norm(duyulan)).ratio()
        print(f"  %{oran * 100:.0f} | {metin} → {duyulan}", flush=True)
        if oran < 0.8:
            kotu.append(metin)
    if kotu:
        raise SystemExit(f"Anlaşılmayan satırlar: {kotu}")


def wav_yaz(yol, x):
    x = np.clip(x, -1, 1)
    with wave.open(yol, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    sure = KLIP * 3
    ses = np.zeros(int(SR * sure), np.float32)
    eksik, parcalar = [], []
    if MOTOR == "eleven":
        gerek = sum(len(s[3]) for s in SATIRLAR) * 3
        kalan = eleven_kalan()
        print(f"ElevenLabs kalan kredi: {kalan} (en çok ≈{gerek} gerekir)")
        if not ELEVEN_KEY or (kalan is not None and kalan < gerek):
            sys.exit("ElevenLabs kredisi yetmiyor — ücretsiz sürüm yerinde kalıyor")
    for bas, bit, kim, metin in SATIRLAR:
        d = eleven_tek(metin, kim, bit - bas) if MOTOR == "eleven" else carsi_ses.tek(metin, kim, pay=bit - bas)
        if d is not None:
            parcalar.append((metin, d))
        if d is None:
            eksik.append(metin)
            continue
        s = int(bas * SR)
        ses[s:s + len(d)] += d[:len(ses) - s] * 0.95
    if eksik:
        sys.exit(f"Seslendirilemeyen satırlar var, video yarım kalmasın diye durduruldu: {eksik}")
    kontrol_et(parcalar)
    if MOTOR == "eleven":
        print("ElevenLabs kalan kredi (sonra):", eleven_kalan())

    # Telifsiz müzik: konuşmanın altında kısık (yaklaşık -22 dB)
    mwav = "/tmp/gta6_muzik.wav"
    muzik.uret(sure, mwav, bpm=112, tohum=19)
    with wave.open(mwav) as w:
        m = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32767
    m = np.pad(m, (0, max(0, len(ses) - len(m))))[:len(ses)]
    karisim = ses + m * 0.08
    karisim = karisim / max(1e-6, np.abs(karisim).max()) * 0.89
    swav = "/tmp/gta6_ses.wav"
    wav_yaz(swav, karisim)

    liste = "/tmp/gta6_liste.txt"
    with open(liste, "w") as f:
        for n in (1, 2, 3):
            f.write(f"file '{os.path.join(BURA, f'b{n}.mp4')}'\n")
    cikti = os.path.join(BURA, "cikti_eleven.mp4" if MOTOR == "eleven" else "cikti.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", liste, "-i", swav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-t", f"{sure}", "-movflags", "+faststart", cikti], check=True)
    print("Hazır:", cikti, os.path.getsize(cikti) // 1024, "KB")


if __name__ == "__main__":
    main()
