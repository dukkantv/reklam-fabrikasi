# ÜCRETSİZ seslendirme: Chatterbox Multilingual (MIT lisans, Türkçe) ile Levent'in klon sesi.
# sesler/istek/<ad>.txt içindeki HER SATIR ayrı bir cümle olarak okunur ve
# sesler/cikti/<ad>/01.mp3, 02.mp3 ... olarak kaydedilir (videoda her cümle kendi sahnesine konur).
# Bitmiş istekler (klasöründe tamam.txt olanlar) tekrar üretilmez. Kredi/ücret yok.
import glob, os, subprocess, time

KOK = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(KOK, "sesler", "_ref.wav")
EXA, CFG = 0.55, 0.5   # canlılık (exaggeration) ve hız/sadakat (cfg_weight)


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def main():
    istekler = []
    for yol in sorted(glob.glob(os.path.join(KOK, "sesler", "istek", "*.txt"))):
        ad = os.path.splitext(os.path.basename(yol))[0]
        hedef = os.path.join(KOK, "sesler", "cikti", ad)
        if not os.path.exists(os.path.join(hedef, "tamam.txt")):
            istekler.append((ad, yol, hedef))
    if not istekler:
        print("Yeni istek yok."); return

    ffmpeg("-i", os.path.join(KOK, "sesler", "levent_ornek.mp3"), "-ar", "24000", "-ac", "1", REF)
    import torch, torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(os.cpu_count() or 4)
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    print(f"Model yüklendi ({time.time() - t0:.0f} sn)")

    for ad, yol, hedef in istekler:
        os.makedirs(hedef, exist_ok=True)
        satirlar = [s.strip() for s in open(yol, encoding="utf-8") if s.strip()]
        for i, cumle in enumerate(satirlar, 1):
            t0 = time.time()
            wav = model.generate(cumle, language_id="tr", audio_prompt_path=REF, exaggeration=EXA, cfg_weight=CFG)
            gecici = os.path.join(hedef, f"_{i:02d}.wav")
            ta.save(gecici, wav, model.sr)
            ffmpeg("-i", gecici, "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "160k", os.path.join(hedef, f"{i:02d}.mp3"))
            os.remove(gecici)
            print(f"{ad} {i:02d} ({time.time() - t0:.0f} sn): {cumle}")
        open(os.path.join(hedef, "tamam.txt"), "w", encoding="utf-8").write("\n".join(satirlar) + "\n")
    os.remove(REF)


if __name__ == "__main__":
    main()
