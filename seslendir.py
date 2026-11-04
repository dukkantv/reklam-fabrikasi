# Kullanım: python seslendir.py eserim
# bilgi.json'daki "seslendirme" cümlelerini edge-tts (ücretsiz Microsoft sesleri) ile okutur,
# her cümleyi kendi sahnesinin üstüne yerleştirir ve sesli videoyu cikti/ klasörüne yazar.
import asyncio, json, os, subprocess, sys

import edge_tts

KOK = os.path.dirname(os.path.abspath(__file__))
FPS = 30


async def main(klasor):
    veri = json.load(open(os.path.join(KOK, "reklamlar", klasor, "bilgi.json"), encoding="utf-8"))
    ad = veri.get("dosya_adi", klasor)
    cikti = os.path.join(KOK, "cikti")
    sessiz = os.path.join(cikti, ad + "_sessiz.mp4")
    sahneler = json.load(open(os.path.join(cikti, "sahneler.json")))
    ses_adi = veri.get("ses", "tr-TR-AhmetNeural")
    satirlar = veri.get("seslendirme", [])

    if not satirlar:
        os.replace(sessiz, os.path.join(cikti, ad + ".mp4"))
        print("Seslendirme yok, sessiz video bırakıldı.")
        return

    girdiler, filtreler = [], []
    for i, s in enumerate(satirlar):
        dosya = os.path.join(cikti, f"ses_{i}.mp3")
        await edge_tts.Communicate(s["metin"], s.get("ses", ses_adi), rate=s.get("hiz", "+8%")).save(dosya)
        baslangic_karesi = sahneler[s["sahne"] - 1][1]
        ms = int((baslangic_karesi / FPS + s.get("saniye", 0)) * 1000)
        girdiler += ["-i", dosya]
        filtreler.append(f"[{i + 1}:a]aresample=44100,aformat=channel_layouts=stereo,adelay=delays={ms}:all=1[a{i}]")
        print(f"Ses {i + 1}: sahne {s['sahne']}, {ms / 1000:.1f}. saniye -> {s['metin']}")

    karisim = "".join(f"[a{i}]" for i in range(len(satirlar)))
    filtre = ";".join(filtreler) + f";{karisim}amix=inputs={len(satirlar)}:normalize=0,apad[ses]"
    gecici = os.path.join(cikti, ad + "_yaziliyor.mp4")
    subprocess.run(["ffmpeg", "-v", "warning", "-y", "-i", sessiz, *girdiler, "-filter_complex", filtre,
                    "-map", "0:v", "-map", "[ses]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", gecici], check=True)
    os.replace(gecici, os.path.join(cikti, ad + ".mp4"))
    print("Sesli video hazır: " + ad + ".mp4")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
