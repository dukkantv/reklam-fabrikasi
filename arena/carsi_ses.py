# Çarşı Ligi seslendirme: ücretsiz edge-tts (Microsoft). Türkçede tek erkek ses var; karakterler hız ve
# perdeyle ayrılır. Ses alınamazsa (ağ yok vb.) None döner, video sessiz anlatımla yine üretilir.
import asyncio, os, subprocess, tempfile

import numpy as np

SR = 44100
SESLER = {
    "L": {"voice": "tr-TR-AhmetNeural", "rate": "+12%", "pitch": "+8Hz"},    # Levent: hızlı, heyecanlı
    "C": {"voice": "tr-TR-AhmetNeural", "rate": "-4%", "pitch": "-14Hz"},    # Cemo: kalın, ağır
    "B": {"voice": "tr-TR-AhmetNeural", "rate": "-10%", "pitch": "-4Hz"},    # Çarşı Muhtarı: ağırbaşlı
}


async def _tts(metin, kim, yol):
    import edge_tts
    s = SESLER[kim]
    await edge_tts.Communicate(metin, s["voice"], rate=s["rate"], pitch=s["pitch"]).save(yol)


def tek(metin, kim, pay=None):
    """Bir satırı seslendirir. pay (sn) verilirse en çok 1,45 kat hızlanır, hâlâ uzunsa sonu yumuşakça kesilir."""
    with tempfile.TemporaryDirectory() as td:
        mp3, ham = os.path.join(td, "s.mp3"), os.path.join(td, "s.f32")
        try:
            for deneme in range(3):
                try:
                    asyncio.run(_tts(metin, kim, mp3)); break
                except Exception:
                    if deneme == 2:
                        raise
            sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                                        capture_output=True, text=True).stdout.strip() or 0)
            hiz = min(1.45, max(1.0, sure / pay)) if (pay and sure) else 1.0
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"atempo={hiz:.3f}", "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", ham], check=True)
            d = np.fromfile(ham, np.float32)
            if pay and len(d) > int(pay * SR):
                d = d[:int(pay * SR)].copy(); f = min(len(d), int(0.15 * SR)); d[-f:] *= np.linspace(1, 0, f)
            return d / max(1e-6, np.abs(d).max()) * 0.9
        except Exception as ex:
            print("seslendirme atlandı:", metin[:50], ex)
            return None


def balonlar(balon):
    """Maç yorumları: her balon bir sonraki balon başlayana kadar sığacak şekilde."""
    out = []
    for n, (kim, metin, bitis, bas) in enumerate(balon):
        sonraki = balon[n + 1][3] if n + 1 < len(balon) else bas + 5.5
        out.append(tek(metin, kim, max(1.0, min(sonraki - bas, 5.5) - 0.1)))
    return out


def tahmini_sure(metin):
    """TTS yokken (yerel deneme) satır süresi tahmini."""
    return 0.4 + len(metin) * 0.065
