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
    (0.15, 3.15, "N", "Son dakika! GTA 6 yüzünden dükkânlar kapandı... ama asıl olay bu değil!"),
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


def wav_yaz(yol, x):
    x = np.clip(x, -1, 1)
    with wave.open(yol, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    sure = KLIP * 3
    ses = np.zeros(int(SR * sure), np.float32)
    eksik = []
    for bas, bit, kim, metin in SATIRLAR:
        d = carsi_ses.tek(metin, kim, pay=bit - bas)
        if d is None:
            eksik.append(metin)
            continue
        s = int(bas * SR)
        ses[s:s + len(d)] += d[:len(ses) - s] * 0.95
    if eksik:
        sys.exit(f"Seslendirilemeyen satırlar var, video yarım kalmasın diye durduruldu: {eksik}")

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
    cikti = os.path.join(BURA, "cikti.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", liste, "-i", swav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-t", f"{sure}", "-movflags", "+faststart", cikti], check=True)
    print("Hazır:", cikti, os.path.getsize(cikti) // 1024, "KB")


if __name__ == "__main__":
    main()
