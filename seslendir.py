# Kullanım: python seslendir.py eserim
# bilgi.json'daki "seslendirme" cümlelerini edge-tts (ücretsiz Microsoft sesleri) ile okutur,
# "efektler" listesindeki sesleri (örn. telefon zili) ekler, her şeyi kendi sahnesine yerleştirir
# ve sesli videoyu cikti/ klasörüne yazar. Cümleler asla üst üste binmez.
import asyncio, json, os, subprocess, sys

import edge_tts

KOK = os.path.dirname(os.path.abspath(__file__))
FPS = 30
BOSLUK = 0.15  # iki cümle arasında en az bu kadar saniye sessizlik

# Hazır ses efektleri (ffmpeg ile üretilir, dışarıdan dosya gerekmez)
EFEKTLER = {
    # Klasik telefon zili: 440+480 Hz, 0.4 sn çal / 0.2 sn dur + hafif titreşim vızıltısı
    "zil": "0.22*(sin(2*PI*440*t)+sin(2*PI*480*t))*lt(mod(t,0.6),0.4)"
           "+0.12*sin(2*PI*150*t)*lt(mod(t,0.6),0.4)*gt(sin(2*PI*25*t),0)",
}


def sure(dosya):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dosya]).strip())


async def main(klasor):
    veri = json.load(open(os.path.join(KOK, "reklamlar", klasor, "bilgi.json"), encoding="utf-8"))
    ad = veri.get("dosya_adi", klasor)
    cikti = os.path.join(KOK, "cikti")
    sessiz = os.path.join(cikti, ad + "_sessiz.mp4")
    sahneler = json.load(open(os.path.join(cikti, "sahneler.json")))
    ses_adi = veri.get("ses", "tr-TR-AhmetNeural")
    bas = lambda s: sahneler[s["sahne"] - 1][1] / FPS + s.get("saniye", 0)

    parcalar = []  # (dosya, başlangıç saniyesi, ses seviyesi)
    son_bitis = 0.0
    for i, s in enumerate(veri.get("seslendirme", [])):
        dosya = os.path.join(cikti, f"ses_{i}.mp3")
        await edge_tts.Communicate(s["metin"], s.get("ses", ses_adi), rate=s.get("hiz", "+8%")).save(dosya)
        t = max(bas(s), son_bitis + BOSLUK)
        son_bitis = t + sure(dosya)
        parcalar.append((dosya, t, 1.0))
        print(f"Ses {i + 1}: {t:.1f}–{son_bitis:.1f} sn -> {s['metin']}")

    for i, e in enumerate(veri.get("efektler", [])):
        dosya = os.path.join(cikti, f"efekt_{i}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "aevalsrc=" + EFEKTLER[e["efekt"]].replace(",", "\\,") + f":s=44100:d={e.get('sure', 1.5)}", dosya], check=True)
        parcalar.append((dosya, bas(e), e.get("seviye", 0.8)))
        print(f"Efekt '{e['efekt']}': {bas(e):.1f}. saniye")

    if not parcalar:
        os.replace(sessiz, os.path.join(cikti, ad + ".mp4"))
        print("Ses yok, sessiz video bırakıldı.")
        return

    girdiler, filtreler = [], []
    for i, (dosya, t, seviye) in enumerate(parcalar):
        ms = int(t * 1000)
        girdiler += ["-i", dosya]
        filtreler.append(f"[{i + 1}:a]aresample=44100,aformat=channel_layouts=stereo,"
                         f"volume={seviye},adelay=delays={ms}:all=1[a{i}]")
    karisim = "".join(f"[a{i}]" for i in range(len(parcalar)))
    filtre = ";".join(filtreler) + f";{karisim}amix=inputs={len(parcalar)}:normalize=0,apad[ses]"
    gecici = os.path.join(cikti, ad + "_yaziliyor.mp4")
    subprocess.run(["ffmpeg", "-v", "warning", "-y", "-i", sessiz, *girdiler, "-filter_complex", filtre,
                    "-map", "0:v", "-map", "[ses]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", gecici], check=True)
    os.replace(gecici, os.path.join(cikti, ad + ".mp4"))
    print("Sesli video hazır: " + ad + ".mp4")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
