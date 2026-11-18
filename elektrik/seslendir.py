# Elektriksiz Dünya Shorts: her sahnenin anlatımını Levent'in ücretsiz klon sesiyle (Chatterbox) okur.
import json, os, subprocess, sys
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import ucretsiz_ses

veri = json.load(open(os.path.join(KOK, "elektrik", "metin.json"), encoding="utf-8"))
cikti = os.path.join(KOK, "elektrik", "ses")
os.makedirs(cikti, exist_ok=True)
for ad, metin in veri["sahneler"].items():
    wav = f"/tmp/{ad}.wav"
    ucretsiz_ses.oku(veri["tarz"], metin, wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-ac", "1", "-ar", "44100", "-b:a", "160k",
                    os.path.join(cikti, f"{ad}.mp3")], check=True)
    print("okundu:", ad, flush=True)
