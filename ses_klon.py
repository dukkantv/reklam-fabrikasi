# Levent'in sesini ElevenLabs'te klonlar (Instant Voice Cloning, Starter pakete dahil) ve
# karşılaştırma için aynı metni hem klonla hem ücretsiz Ahmet sesiyle seslendirip Telegram'a yollar.
# Kullanım: python ses_klon.py          (klon yoksa oluşturur, varsa yeniden kullanır)
import asyncio, json, os, sys

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
KEY = "".join(os.environ.get("ELEVENLABS_API_KEY", "").split())
TOKEN, CHAT = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
KAYIT = os.path.join(KOK, "sesler", "levent_klon.json")
ORNEK = os.path.join(KOK, "sesler", "levent_ornek.mp3")
CIKTI = os.path.join(KOK, "sesler", "deneme")
H = {"xi-api-key": KEY}

METIN = ("Mayıs 1481. Dünyanın en korkulan hükümdarı, ordusunun başında sefere çıkıyor. Hedefini kimse bilmiyor. "
         "Ve birkaç gün sonra, Gebze yakınlarında bir çadırda, sessizce ölüyor. Hastalık mı onu aldı, yoksa bir "
         "hekimin elindeki küçük bir şişe mi? Beş yüz yılı aşkın süredir bu soru tartışılıyor.")


def klon_id():
    if os.path.exists(KAYIT):
        vid = json.load(open(KAYIT))["voice_id"]
        if requests.get(f"https://api.elevenlabs.io/v1/voices/{vid}", headers=H, timeout=60).ok:
            print("Mevcut klon kullanılıyor:", vid)
            return vid
    with open(ORNEK, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/voices/add", headers=H, timeout=180,
                          data={"name": "Levent (Gizli Tarih anlatıcı)", "remove_background_noise": "true",
                                "description": "Levent'in kendi sesi — Gizli Tarih belgesel anlatımı",
                                "labels": json.dumps({"language": "tr", "use_case": "narration"})},
                          files={"files": ("levent_ornek.mp3", f, "audio/mpeg")})
    if not r.ok:
        sys.exit(f"Klon oluşturulamadı: {r.status_code} {r.text[:400]}")
    vid = r.json()["voice_id"]
    os.makedirs(os.path.dirname(KAYIT), exist_ok=True)
    json.dump({"voice_id": vid, "ad": "Levent (Gizli Tarih anlatıcı)", "kaynak": "sesler/levent_ornek.mp3"},
              open(KAYIT, "w"), ensure_ascii=False, indent=1)
    print("Yeni klon:", vid)
    return vid


def klon_seslendir(vid, model, hedef):
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", headers=H, timeout=300,
                      params={"output_format": "mp3_44100_128"},
                      json={"text": METIN, "model_id": model, "language_code": "tr",
                            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.0,
                                               "use_speaker_boost": True}})
    if not r.ok:
        print(f"{model} hata: {r.status_code} {r.text[:300]}")
        return False
    open(hedef, "wb").write(r.content)
    return True


def telegram_ses(yol, baslik):
    if TOKEN and os.path.exists(yol):
        with open(yol, "rb") as f:
            print(baslik, requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio", timeout=120,
                                        data={"chat_id": CHAT, "title": baslik, "caption": baslik},
                                        files={"audio": f}).json().get("ok"))


def main():
    if not KEY:
        sys.exit("ELEVENLABS_API_KEY yok")
    os.makedirs(CIKTI, exist_ok=True)
    vid = klon_id()
    sonuc = []
    for model, ad in [("eleven_v3", "v3"), ("eleven_multilingual_v2", "v2")]:
        hedef = os.path.join(CIKTI, f"levent_klon_{ad}.mp3")
        if klon_seslendir(vid, model, hedef):
            sonuc.append((hedef, f"🎙 Senin sesin (klon, {ad})"))
    import edge_tts
    ahmet = os.path.join(CIKTI, "ahmet.mp3")
    asyncio.run(edge_tts.Communicate(METIN, "tr-TR-AhmetNeural", rate="-4%").save(ahmet))
    sonuc.append((ahmet, "🤖 Şu anki ses (Ahmet, ücretsiz)"))
    if TOKEN:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", timeout=60,
                      data={"chat_id": CHAT, "text": "🔊 Ses karşılaştırması — Fatih videosunun girişi. "
                                                     "Hangisi daha iyi? Claude'a yaz."})
    for yol, ad in sonuc:
        telegram_ses(yol, ad)
    print("Bitti:", [s[1] for s in sonuc])


if __name__ == "__main__":
    main()
