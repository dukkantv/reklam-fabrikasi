# Telifsiz arka plan müziği: kodla üretilir (dışarıdan dosya yok), bölüm sonunda konuşmanın altına kısık olarak eklenir.
# Kullanım (tek başına): python muzik.py 60 cikti/muzik.wav
import sys, wave
import numpy as np

SR = 44100


def uret(sure, hedef, bpm=104, tohum=7):
    rng = np.random.default_rng(tohum)
    x = np.zeros(int(SR * (sure + 2)))
    beat = 60 / bpm

    def nota(f, bas, uzun, ses, tur):
        n = int(uzun * SR); t = np.arange(n) / SR
        if tur == "pluck":
            w = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)) * np.exp(-t * 5)
        elif tur == "bas":
            w = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.5)
        else:  # zil
            w = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t)) * np.exp(-t * 3)
        w *= np.minimum(1, t * 200)
        s = int(bas * SR); e = min(len(x), s + n)
        if s < len(x): x[s:e] += ses * w[:e - s]

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    akorlar = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    baslar = [36, 31, 33, 29]
    melodi = [76, 79, 76, 74, 74, 71, 74, 79, 72, 76, 72, 71, 69, 72, 74, 76]
    t, i = 0.0, 0
    while t < sure:
        for b in range(4):
            bt = t + b * beat
            nota(hz(baslar[i % 4]), bt, beat * 0.9, 0.35, "bas")
            for k, m in enumerate(akorlar[i % 4]):
                nota(hz(m), bt + k * beat / 6, beat * 0.8, 0.10, "pluck")
            nota(hz(melodi[(i % 4) * 4 + b]), bt, beat * 0.9, 0.14, "zil")
            n = int(0.12 * SR); tt = np.arange(n) / SR; s = int(bt * SR)
            if s + n < len(x): x[s:s + n] += 0.35 * np.sin(2 * np.pi * (90 - 40 * tt / 0.12) * tt) * np.exp(-tt * 30)
            s2 = int((bt + beat / 2) * SR); n2 = int(0.04 * SR)
            if s2 + n2 < len(x): x[s2:s2 + n2] += 0.05 * rng.standard_normal(n2) * np.exp(-np.arange(n2) / SR * 120)
        t += 4 * beat; i += 1
    x = x[:int(SR * sure)]
    f = min(len(x), int(1.7 * SR)); x[-f:] *= np.linspace(1, 0, f)
    x = x / max(1e-9, np.max(np.abs(x))) * 0.85
    with wave.open(hedef, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return hedef


if __name__ == "__main__":
    uret(float(sys.argv[1]), sys.argv[2])
