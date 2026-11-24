# Ücretsiz ses klonu: Chatterbox Multilingual (Resemble AI, MIT lisans, Türkçe destekli, ticari kullanım serbest).
# Levent'in kayıtlarından (sesler/klon/<tarz>.wav|mp3) sıfır-örnekli klonla seslendirir. GitHub'ın ücretsiz
# sunucusunda CPU ile çalışır; ElevenLabs gerekmez.
# Kullanım:
#   python ucretsiz_ses.py deneme                 -> her tarz için örnek cümleleri okur, Telegram'a yollar
#   python ucretsiz_ses.py oku <tarz> "<metin>" cikti.wav
import os, re, sys, time, glob, subprocess

import torch

_yukle = torch.load
torch.load = lambda *a, **k: _yukle(*a, **{**k, "map_location": torch.device("cpu")})  # GPU'da kaydedilmiş ağırlıklar

KOK = os.path.dirname(os.path.abspath(__file__))
KLASOR = os.path.join(KOK, "sesler", "klon")

# Tarz -> (referans dosya adı, exaggeration, cfg_weight, temperature). exaggeration: duygu/enerji; cfg: tempo-ritim bağlılığı
# 24 Kas 2026: Levent 4 tarzda ayrı kayıt yaptı (sesler/klon/belgesel|neseli|gizemli|spiker.flac). Ayarlar test edildi,
# Levent beğendi ("daha önceki klondan güzel"). ElevenLabs kredisi bitince bütün anlatımlar bu seslerle yapılır.
TARZLAR = {
    "belgesel": ("belgesel", 0.40, 0.50, 0.7),   # Gizli Tarih: sakin, ağır belgesel anlatıcı
    "neseli":   ("neseli", 0.65, 0.35, 0.8),     # Çarşı Ligi / skeç / liste videoları: hızlı, neşeli
    "gizemli":  ("gizemli", 0.45, 0.50, 0.7),    # gizem, gerilim, "Ne Olur?" karanlık senaryolar
    "spiker":   ("spiker", 0.80, 0.30, 0.8),     # 81 İl Turnuvası: coşkulu maç spikeri
    "hikaye":   ("belgesel", 0.55, 0.45, 0.75),  # Drama Bite: sıcak, duygulu (belgesel kaydından)
    "dedektif": ("gizemli", 0.50, 0.45, 0.7),    # Kasa Kurgu: gergin, merak uyandıran
    "samimi":   ("neseli", 0.50, 0.40, 0.75),    # Kasa Kurgu günlük seri: arkadaşla konuşur gibi
}

ORNEK = {
    "belgesel": "Mayıs 1481. Dünyanın en korkulan hükümdarı, ordusunun başında sefere çıkıyor. Hedefini kimse bilmiyor. Ve birkaç gün sonra, bir çadırda, sessizce ölüyor.",
    "neseli": "Ve top bırakıldı! Simitçi Kedi önde, Kokoreç Ejderha hemen arkasında! Bu nasıl bir maç böyle, inanılır gibi değil!",
    "hikaye": "Annesi kapıyı açtığında karşısında yıllardır görmediği oğlunu buldu. Bir an konuşamadı. Sonra gözleri doldu ve sadece sarıldı.",
    "samimi": "Bugün kasada beş yüz lira var. Hedef elli bin. Biliyorum, çılgınca görünüyor ama dur, sana bugün ne yaptığımı anlatayım.",
    "gizemli": "Kimse o kuleye yıllardır girmemişti. Peki ışığı kim yakmıştı? Ve neden tam o gece?",
    "spiker": "Ve karşınızda büyük final! Bursa ile Trabzon sahaya çıkıyor! Toplar hazır, tribünler dolu, başlıyoruz!",
    "dedektif": "Kapı içeriden kilitliydi. Anahtar kilitte duruyordu. Peki katil bu odadan nasıl çıktı? Cevap, gözünüzün önündeydi.",
}

_model = None


def model():
    global _model
    if _model is None:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        torch.set_num_threads(os.cpu_count() or 4)
        _model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return _model


def referans(tarz):
    tarz = tarz if tarz in TARZLAR else "belgesel"
    """Tarzın kendi kaydı yoksa genel örneğe (sesler/levent_ornek.mp3) düşer. 16 sn'lik temiz wav'a çevirir."""
    ad = TARZLAR[tarz][0]
    adaylar = glob.glob(os.path.join(KLASOR, ad + ".*")) or [os.path.join(KOK, "sesler", "levent_ornek.mp3")]
    hedef = f"/tmp/ref_{tarz}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", adaylar[0], "-t", "16", "-ac", "1", "-ar", "24000",
                    "-af", "highpass=f=70,loudnorm=I=-18:TP=-2", hedef], check=True)
    return hedef, os.path.basename(adaylar[0])


def cumleler(metin, sinir=220):
    parca, son = [], ""
    for c in re.split(r"(?<=[.!?…])\s+", metin.strip()):
        if son and len(son) + len(c) > sinir:
            parca.append(son); son = c
        else:
            son = (son + " " + c).strip()
    return parca + ([son] if son else [])


def oku(tarz, metin, cikti):
    import torchaudio as ta
    tarz = tarz if tarz in TARZLAR else "belgesel"
    m = model()
    ref, _ = referans(tarz)
    _, ex, cfg, sic = TARZLAR[tarz]
    parcalar = []
    for c in cumleler(metin):
        w = m.generate(c, language_id="tr", audio_prompt_path=ref, exaggeration=ex, cfg_weight=cfg, temperature=sic)
        parcalar += [w, torch.zeros(1, int(m.sr * 0.25))]
    ta.save(cikti, torch.cat(parcalar[:-1], dim=1), m.sr)
    return cikti


def telegram(dosya, yazi):
    import requests
    t, c = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not t:
        return
    mp3 = dosya.rsplit(".", 1)[0] + ".mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", dosya, "-b:a", "128k", mp3], check=True)
    with open(mp3, "rb") as f:
        requests.post(f"https://api.telegram.org/bot{t}/sendAudio", data={"chat_id": c, "caption": yazi},
                      files={"audio": f}, timeout=120)


if __name__ == "__main__":
    if sys.argv[1] == "deneme":
        os.makedirs("/tmp/klon", exist_ok=True)
        t0 = time.time(); model(); print(f"Model yüklendi: {time.time() - t0:.0f} sn")
        for tarz, metin in ORNEK.items():
            t0 = time.time()
            f = oku(tarz, metin, f"/tmp/klon/{tarz}.wav")
            sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                        capture_output=True, text=True).stdout)
            gecen = time.time() - t0
            _, kaynak = referans(tarz)
            print(f"{tarz}: {sure:.1f} sn ses, {gecen:.0f} sn sürdü (x{gecen / sure:.1f}) · referans: {kaynak}")
            telegram(f, f"🎙 Ücretsiz klon · {tarz} (referans: {kaynak}) · {sure:.0f} sn ses {gecen:.0f} sn'de")
    elif sys.argv[1] == "oku":
        oku(sys.argv[2], sys.argv[3], sys.argv[4])
