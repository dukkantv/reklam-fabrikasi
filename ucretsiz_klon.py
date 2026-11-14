# ÜCRETSİZ ses klonu: Chatterbox Multilingual (Resemble AI, MIT lisans — ticari kullanım serbest, Türkçe destekli).
# Levent'in kaydını (sesler/levent_ornek.mp3) referans alır, GitHub'ın kendi işlemcisinde çalışır: kredi/ücret yok.
# Karşılaştırma için 2 ayar üretir ve ElevenLabs v3 denemesiyle birlikte Telegram'a yollar.
import os, re, subprocess, sys, time

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
TOKEN, CHAT = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
CIKTI = os.path.join(KOK, "sesler", "deneme")
REF = os.path.join(CIKTI, "ref.wav")

METIN = ("Mayıs 1481. Dünyanın en korkulan hükümdarı, ordusunun başında sefere çıkıyor. Hedefini kimse bilmiyor. "
         "Ve birkaç gün sonra, Gebze yakınlarında bir çadırda, sessizce ölüyor. Hastalık mı onu aldı, yoksa bir "
         "hekimin elindeki küçük bir şişe mi? Beş yüz yılı aşkın süredir bu soru tartışılıyor.")

AYARLAR = [("A_dengeli", 0.5, 0.5), ("B_yavas_sakin", 0.4, 0.3)]  # (ad, exaggeration, cfg_weight) — hızlı konuşan referansta düşük cfg yavaşlatır


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def main():
    os.makedirs(CIKTI, exist_ok=True)
    ffmpeg("-i", os.path.join(KOK, "sesler", "levent_ornek.mp3"), "-ar", "24000", "-ac", "1", REF)
    import torch, torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    torch.set_num_threads(os.cpu_count() or 4)
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    print(f"Model yüklendi ({time.time() - t0:.0f} sn)")
    cumleler = [c.strip() for c in re.split(r"(?<=[.?!])\s+", METIN) if c.strip()]
    sonuc = []
    for ad, exa, cfg in AYARLAR:
        t0, parcalar = time.time(), []
        for j, c in enumerate(cumleler):
            wav = model.generate(c, language_id="tr", audio_prompt_path=REF, exaggeration=exa, cfg_weight=cfg)
            p = os.path.join(CIKTI, f"_p_{ad}_{j}.wav")
            ta.save(p, wav, model.sr)
            parcalar.append(p)
        liste = os.path.join(CIKTI, f"_liste_{ad}.txt")
        # cümleler arasına 0.35 sn sessizlik
        sus = os.path.join(CIKTI, "_sus.wav")
        ffmpeg("-f", "lavfi", "-i", f"anullsrc=r={model.sr}:cl=mono", "-t", "0.35", sus)
        open(liste, "w").writelines(f"file '{x}'\nfile '{sus}'\n" for x in parcalar)
        hedef = os.path.join(CIKTI, f"levent_ucretsiz_{ad}.mp3")
        ffmpeg("-f", "concat", "-safe", "0", "-i", liste, "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "160k", hedef)
        print(f"{ad}: {time.time() - t0:.0f} sn sürdü")
        sonuc.append((hedef, f"🆓 Ücretsiz klon ({ad.replace('_', ' ')})"))
        for x in parcalar:
            os.remove(x)
    v3 = os.path.join(CIKTI, "levent_klon_v3.mp3")
    if os.path.exists(v3):
        sonuc.append((v3, "💳 ElevenLabs klon (v3) — karşılaştırma için"))
    if TOKEN:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", timeout=60,
                      data={"chat_id": CHAT, "text": "🔊 Ücretsiz klon denemesi (Chatterbox, sınırsız ve bedava) — "
                                                     "ElevenLabs v3 ile karşılaştır. Robot gibi mi? Claude'a yaz."})
        for yol, baslik in sonuc:
            with open(yol, "rb") as f:
                print(baslik, requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio", timeout=120,
                                            data={"chat_id": CHAT, "title": baslik, "caption": baslik},
                                            files={"audio": f}).json().get("ok"))


if __name__ == "__main__":
    main()
