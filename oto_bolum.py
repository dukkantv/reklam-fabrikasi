# Dükkan TV · Tam otomatik çizgi film bölümü ("Levent'in Maceraları") — dudak senkronlu sürüm
#
# Aşamalar (GitHub Actions > "Otomatik Bölüm" düğmesi bunları çağırır):
#   python oto_bolum.py karakter [yenile]          -> karakter kartları (Nano Banana Pro) — bir kez
#   python oto_bolum.py ses ["cemo,levent"]        -> ElevenLabs Türkçe ses kütüphanesinden her karaktere sabit ses — bir kez
#   python oto_bolum.py taslak eserim "konu" ["3,7"] -> senaryo (Gemini) + plan resimleri + yüz tutarlılık kontrolü
#   python oto_bolum.py video eserim               -> konuşan planlar: ses + dudak senkronu (Kling AI Avatar),
#                                                     aksiyon planları: Seedance; altyazı + KASA + kartlar
#
# Gizli anahtarlar: FAL_KEY, GEMINI_API_KEY, ELEVENLABS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import asyncio, base64, hashlib, json, math, os, re, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
KARAKTER_KLASOR = os.path.join(KOK, "karakterler")
SESLER_YOL = os.path.join(KARAKTER_KLASOR, "sesler.json")
CIKTI = os.path.join(KOK, "cikti")
FAL_KEY = "".join(os.environ.get("FAL_KEY", "").split())
GEMINI_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
ELEVEN_KEY = "".join(os.environ.get("ELEVENLABS_API_KEY", "").split())
TOKEN = os.environ.get("TOKEN", "").strip()
CHAT = os.environ.get("CHAT", "").strip()

# ---- Kalite ayarı: standart | pro ----
KALITE = os.environ.get("KALITE", "standart")
RESIM_MODEL = "fal-ai/nano-banana-pro/edit"
RESIM_MODEL_YAZIDAN = "fal-ai/nano-banana-pro"
AVATAR_MODEL = {"standart": "fal-ai/kling-video/ai-avatar/v2/standard",
                "pro": "fal-ai/kling-video/ai-avatar/v2/pro"}[KALITE]
AKSIYON_COZUNURLUK = {"standart": "720p", "pro": "1080p"}[KALITE]
UCRET = {"resim": 0.15, "avatar": {"standart": 0.0562, "pro": 0.115}[KALITE],
         "aksiyon": {"720p": 0.0216, "1080p": 0.049}[AKSIYON_COZUNURLUK]}
DOLAR_TL = float(os.environ.get("DOLAR_TL", "50"))
AYNI_ANDA = 6
KONTROL_ESIGI = 7          # yüz tutarlılık puanı (10 üzerinden) bunun altındaysa resim yeniden çizilir
EN_FAZLA_YENIDEN = 2

KARAKTERLER = json.load(open(os.path.join(KARAKTER_KLASOR, "karakterler.json"), encoding="utf-8"))
KAR = KARAKTERLER["karakterler"]
harcama = {"resim": 0, "avatar_sn": 0.0, "aksiyon_sn": 0.0, "karakter_harf": 0}


# ------------------------------------------------------------------ genel yardımcılar
def tg(metod, dosyalar=None, **veri):
    if not TOKEN:
        return None
    try:
        return requests.post(f"https://api.telegram.org/bot{TOKEN}/{metod}", data={"chat_id": CHAT, **veri},
                             files=dosyalar, timeout=300).json()
    except Exception as e:
        print("Telegram hatası:", e)


def tg_mesaj(metin):
    print(metin)
    for i in range(0, len(metin), 3900):
        tg("sendMessage", text=metin[i:i + 3900])


def tg_albumler(resimler, basliklar=None):
    for bas in range(0, len(resimler), 10):
        grup = resimler[bas:bas + 10]
        medya, dosyalar = [], {}
        for j, yol in enumerate(grup):
            dosyalar[f"r{j}"] = open(yol, "rb")
            m = {"type": "photo", "media": f"attach://r{j}"}
            if basliklar:
                m["caption"] = basliklar[bas + j][:1000]
            medya.append(m)
        tg("sendMediaGroup", dosyalar=dosyalar, media=json.dumps(medya))


def calistir(*komut):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *komut], check=True)


def sure(dosya):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", dosya]).strip())


def kucult(yol, en=1024):
    gecici = os.path.join(CIKTI, "ref_" + re.sub(r"\W", "_", yol[-60:]) + ".jpg")
    calistir("-i", yol, "-vf", f"scale='min({en},iw)':-2", "-q:v", "3", gecici)
    return gecici


def veri_uri(yol, tur="image/jpeg"):
    return f"data:{tur};base64," + base64.b64encode(open(yol, "rb").read()).decode()


def resim_uri(yol, en=1024):
    return veri_uri(kucult(yol, en))


def fal(model, girdi, deneme=2):
    """fal.ai kuyruğuna iş gönderir, bitene kadar bekler, sonucu döndürür."""
    if not FAL_KEY:
        sys.exit("FAL_KEY gizli anahtarı yok. GitHub > Settings > Secrets > Actions kısmına ekle.")
    bas = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
    for d in range(deneme + 1):
        try:
            r = requests.post(f"https://queue.fal.run/{model}", headers=bas, json=girdi, timeout=180)
            if r.status_code >= 400:
                raise RuntimeError(f"{r.status_code} {r.text[:300]}")
            is_ = r.json()
            bitis = time.time() + 1200
            while time.time() < bitis:
                durum = requests.get(is_["status_url"], headers=bas, timeout=60).json()
                if durum.get("status") == "COMPLETED":
                    sonuc = requests.get(is_["response_url"], headers=bas, timeout=180)
                    if sonuc.status_code >= 400:
                        raise RuntimeError(f"{sonuc.status_code} {sonuc.text[:300]}")
                    return sonuc.json()
                if durum.get("status") in ("FAILED", "ERROR"):
                    raise RuntimeError(str(durum)[:300])
                time.sleep(4)
            raise TimeoutError("fal.ai 20 dakikada bitirmedi")
        except Exception as e:
            print(f"fal.ai hatası ({model}, deneme {d + 1}): {str(e)[:300]}")
            if d == deneme:
                raise
            time.sleep(10)


def indir(url, hedef):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(hedef, "wb") as f:
            for parca in r.iter_content(1 << 16):
                f.write(parca)
    return hedef


_MODELLER = []


def gemini_modelleri():
    """Google'a hangi modellerin açık olduğunu sorar; en yeni 'flash' modelleri öne alır (ad sabit yazılmaz)."""
    if _MODELLER:
        return _MODELLER
    try:
        r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}&pageSize=200", timeout=60)
        r.raise_for_status()
        adlar = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception as e:
        print("Model listesi alınamadı:", e)
        adlar = []
    yasak = ("image", "tts", "audio", "live", "embedding", "vision", "learnlm", "gemma", "robotics", "computer")

    def surum(ad):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", ad)
        return float(m.group(1)) if m else 0.0

    uygun = [a for a in adlar if a.startswith("gemini") and not any(y in a for y in yasak)]
    flash = [a for a in uygun if "flash" in a]
    # sıralama: önce kararlı (preview/exp değil) ve lite olmayan, sonra en yeni sürüm
    flash.sort(key=lambda a: (("preview" in a or "exp" in a), "lite" in a, -surum(a), a.endswith("latest")))
    secim = flash[:3] or uygun[:3]
    for yedek in ["gemini-flash-latest", "gemini-flash-lite-latest"]:
        if yedek not in secim:
            secim.append(yedek)
    print("Kullanılacak Gemini modelleri:", secim)
    _MODELLER.extend(secim)
    return _MODELLER


_GEMINI_KILIT = threading.Lock()
_GEMINI_SON = [0.0]
GEMINI_ARALIK = float(os.environ.get("GEMINI_ARALIK", "7"))  # ücretsiz kota: istekler arası en az bu kadar saniye
KOTA_DOLDU = [False]


def gemini(parcalar, json_mu=True, sicaklik=1.0, hizli_vazgec=False):
    """hizli_vazgec=True: kota doluysa uzun uzun deneme, hemen vazgeç (yüz kontrolü için)."""
    if hizli_vazgec and KOTA_DOLDU[0]:
        raise RuntimeError("Gemini kotası dolu, kontrol atlandı")
    with _GEMINI_KILIT:  # istekleri sıraya koy ve aralarına bekleme koy
        bekle = _GEMINI_SON[0] + GEMINI_ARALIK - time.time()
        if bekle > 0:
            time.sleep(bekle)
        _GEMINI_SON[0] = time.time()
        return _gemini_istek(parcalar, json_mu, sicaklik, hizli_vazgec)


def _gemini_istek(parcalar, json_mu=True, sicaklik=1.0, hizli_vazgec=False):
    if not GEMINI_KEY:
        sys.exit("GEMINI_API_KEY gizli anahtarı yok.")
    if isinstance(parcalar, str):
        parcalar = [{"text": parcalar}]
    ayar = {"temperature": sicaklik}
    if json_mu:
        ayar["responseMimeType"] = "application/json"
    for model in gemini_modelleri():
        for d in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                    json={"contents": [{"parts": parcalar}], "generationConfig": ayar}, timeout=180)
                if r.status_code == 404:
                    print(f"Gemini modeli yok: {model}")
                    break
                if r.status_code == 429 and hizli_vazgec:
                    if "PerDay" in r.text or "per day" in r.text.lower():
                        KOTA_DOLDU[0] = True
                    break
                if r.status_code in (429, 500, 503):
                    raise RuntimeError(f"{r.status_code} {r.text[:200]}")
                r.raise_for_status()
                metin = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                metin = re.sub(r"^```(json)?|```$", "", metin.strip()).strip()
                return json.loads(metin) if json_mu else metin
            except Exception as e:
                print(f"Gemini ({model}) deneme {d + 1}: {str(e)[:200]}")
                time.sleep(5 * (d + 1))
    if hizli_vazgec:
        KOTA_DOLDU[0] = True
    raise RuntimeError("Gemini cevap vermedi")


def maliyet_ozeti():
    r = harcama["resim"] * UCRET["resim"]
    a = harcama["avatar_sn"] * UCRET["avatar"]
    k = harcama["aksiyon_sn"] * UCRET["aksiyon"]
    t = r + a + k
    return (f"💰 Bu çalışma: {t:.2f} $ ≈ {t * DOLAR_TL:.0f} TL (kalite: {KALITE})\n"
            f"   • {harcama['resim']} resim: {r:.2f} $\n"
            f"   • {harcama['avatar_sn']:.0f} sn konuşan plan (dudak senkronu): {a:.2f} $\n"
            f"   • {harcama['aksiyon_sn']:.0f} sn aksiyon planı: {k:.2f} $\n"
            f"   • ElevenLabs: {harcama['karakter_harf']} karakter (aylık paketten düşer)")


def etiketsiz(metin):
    """[laughs] gibi ses etiketlerini altyazıdan siler."""
    return re.sub(r"\s*\[[^\]]+\]\s*", " ", metin).strip()


# ------------------------------------------------------------------ 1) karakter kartları
def karakter_karti(kid):
    return os.path.join(KARAKTER_KLASOR, kid + ".jpg")


def karakter(yenile=False):
    os.makedirs(CIKTI, exist_ok=True)
    stil = KARAKTERLER["stil"].replace(", vertical 9:16 frame", "")
    cizilen = []
    for kid, k in KAR.items():
        hedef = karakter_karti(kid)
        if os.path.exists(hedef) and not yenile:
            continue
        refs = [os.path.join(KARAKTER_KLASOR, r) for r in k["kaynak"]]
        prompt = (f"{stil}. Professional animation CHARACTER MODEL SHEET on a plain light grey background. Top row: "
                  f"full body front view, 3/4 view, side view, back view. Bottom row: five head close-ups with "
                  f"expressions: neutral, big smile talking, surprised, worried, laughing. Same character in every "
                  f"drawing, identical face, hair and outfit. {k['kostum']} No text labels.")
        if refs:
            sonuc = fal(RESIM_MODEL, {"prompt": prompt, "image_urls": [resim_uri(r) for r in refs],
                                      "aspect_ratio": "16:9", "resolution": "2K", "output_format": "jpeg"})
        else:
            sonuc = fal(RESIM_MODEL_YAZIDAN, {"prompt": prompt, "aspect_ratio": "16:9", "resolution": "2K",
                                              "output_format": "jpeg"})
        harcama["resim"] += 1
        indir(sonuc["images"][0]["url"], hedef)
        cizilen.append(hedef)
        print(f"{k['ad']} karakter kartı çizildi")
    if cizilen:
        tg_albumler(cizilen, [f"Karakter kartı: {os.path.basename(c)}" for c in cizilen])
        tg_mesaj("🎨 Karakter kartları hazır. Bundan sonra her sahne bu kartlara bakılarak çizilecek.\n"
                 "Beğenmezsen aşama: karakter-yenile.\n" + maliyet_ozeti())
    else:
        print("Karakter kartları zaten hazır.")


# ------------------------------------------------------------------ 2) sesler (ElevenLabs)
_ELEVEN_SINIR = threading.Semaphore(2)  # Starter paket: aynı anda en fazla 3 istek; 2 ile güvenli kalıyoruz


def eleven(yol, metod="GET", **kw):
    for d in range(8):
        with _ELEVEN_SINIR:
            r = requests.request(metod, "https://api.elevenlabs.io" + yol, headers={"xi-api-key": ELEVEN_KEY},
                                 timeout=180, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            print(f"ElevenLabs meşgul ({r.status_code}), {5 * (d + 1)} sn bekleniyor")
            time.sleep(5 * (d + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")
        return r
    raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:300]}")


def sesler_oku():
    return json.load(open(SESLER_YOL, encoding="utf-8")) if os.path.exists(SESLER_YOL) else {}


def ses_rolleri():
    roller = {kid: k["ses_arama"] for kid, k in KAR.items()}
    roller.update({rol: a["ses_arama"] for rol, a in KARAKTERLER["diger_sesler"].items()})
    return roller


def ses_adaylari(rol, mevcut):
    """Rol için puana göre sıralı aday sesler (seçili ve önceden denenmiş olanlar hariç)."""
    arama = ses_rolleri()[rol]
    kullanilan = {v["voice_id"] for r, v in mevcut.items()}
    denenen = set(mevcut.get(rol, {}).get("denenen", [])) | {a["voice_id"] for a in mevcut.get(rol, {}).get("adaylar", [])}
    params = {"language": "tr", "page_size": 100, "sort": "cloned_by_count", **arama.get("filtre", {})}
    adaylar = eleven("/v1/shared-voices", params=params).json().get("voices", [])
    adaylar = [a for a in adaylar if a["voice_id"] not in kullanilan | denenen and a.get("category") != "famous"]
    adaylar.sort(key=lambda a: (-ses_puani(a, arama), -(a.get("cloned_by_count") or 0)))
    return adaylar


def ses_hesaba_ekle(rol, a):
    try:
        eleven(f"/v1/voices/add/{a['public_owner_id']}/{a['voice_id']}", "POST",
               json={"new_name": f"DTV {rol} {a['name']}"[:40]})
    except RuntimeError as e:
        if "already" not in str(e).lower():
            print("Ses eklenemedi:", e)


def ses_aday_dinlet(rol, adet):
    """Seçili sesi değiştirmeden 'adet' kadar yeni aday sesi Telegram'a örnek olarak gönderir."""
    mevcut = sesler_oku()
    adaylar = ses_adaylari(rol, mevcut)[:adet]
    ornek = ses_roller_ornek(rol)
    kayit = []
    for i, a in enumerate(adaylar, 1):
        ses_hesaba_ekle(rol, a)
        yol = os.path.join(CIKTI, f"aday_{rol}_{i}.mp3")
        seslendir(ornek, rol, yol, voice_id=a["voice_id"])
        tg("sendAudio", dosyalar={"audio": open(yol, "rb")},
           caption=f"🎙 {rol} — ADAY {i}: {a.get('name')}\n{(a.get('description') or '')[:150]}")
        kayit.append({"voice_id": a["voice_id"], "ad": a.get("name"), "aciklama": (a.get("description") or "")[:120]})
    mevcut.setdefault(rol, {})["adaylar"] = kayit
    json.dump(mevcut, open(SESLER_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    simdiki = mevcut[rol].get("ad", "-")
    tg_mesaj(f"🎧 {rol} için {len(kayit)} aday gönderildi. Şu anki ses: {simdiki}.\n"
             f"Seçmek için: aşama ses, yeniden kutusuna {rol}:1 ya da {rol}:2 yaz.")


def ses_aday_sec(rol, no):
    mevcut = sesler_oku()
    adaylar = mevcut.get(rol, {}).get("adaylar", [])
    if not 1 <= no <= len(adaylar):
        sys.exit(f"{rol} için {no}. aday yok. Önce {rol}:aday2 ile aday dinlet.")
    eski = mevcut[rol]
    sec = adaylar[no - 1]
    mevcut[rol] = {**sec, "denenen": [d for d in eski.get("denenen", []) + [eski.get("voice_id")] if d]}
    json.dump(mevcut, open(SESLER_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    tg_mesaj(f"✅ {rol} sesi artık: {sec['ad']}. Bundan sonraki bütün bölümlerde bu ses kullanılacak.")


def ses(degistir=""):
    if not ELEVEN_KEY:
        tg_mesaj("ELEVENLABS_API_KEY yok; ücretsiz edge-tts sesleri kullanılacak (dudak senkronu yine çalışır).")
        return
    os.makedirs(CIKTI, exist_ok=True)
    m = re.fullmatch(r"\s*(\w+)\s*:\s*(aday)?\s*(\d+)\s*", degistir or "")
    if m:
        rol, aday, sayi = m.group(1), m.group(2), int(m.group(3))
        return ses_aday_dinlet(rol, sayi) if aday else ses_aday_sec(rol, sayi)
    os.makedirs(CIKTI, exist_ok=True)
    mevcut = sesler_oku()
    degisecek = {x.strip() for x in degistir.split(",") if x.strip()}
    kullanilan = {v["voice_id"] for r, v in mevcut.items() if r not in degisecek}
    yeni = []
    for rol, arama in ses_rolleri().items():
        if rol in mevcut and rol not in degisecek:
            continue
        denenen = (mevcut.get(rol, {}).get("denenen", []) + [mevcut.get(rol, {}).get("voice_id")]) if rol in degisecek else []
        sira = 0
        params = {"language": "tr", "page_size": 100, "sort": "cloned_by_count", **arama.get("filtre", {})}
        adaylar = eleven("/v1/shared-voices", params=params).json().get("voices", [])
        if not adaylar:  # filtre çok darsa sadece dil + cinsiyetle ara
            params = {"language": "tr", "page_size": 100, "gender": arama.get("filtre", {}).get("gender", "male")}
            adaylar = eleven("/v1/shared-voices", params=params).json().get("voices", [])
        adaylar = [a for a in adaylar if a["voice_id"] not in kullanilan and a["voice_id"] not in denenen
                   and a.get("category") != "famous"]
        if not adaylar:
            print(f"{rol} için ses bulunamadı")
            continue
        adaylar.sort(key=lambda a: (-ses_puani(a, arama), -(a.get("cloned_by_count") or 0)))
        for a in adaylar[:5]:
            print(f"  aday {rol}: {a.get('name')} | puan {ses_puani(a, arama)}")
        sec = adaylar[sira % len(adaylar)]
        try:
            eleven(f"/v1/voices/add/{sec['public_owner_id']}/{sec['voice_id']}", "POST",
                   json={"new_name": f"DTV {rol} {sec['name']}"[:40]})
        except RuntimeError as e:
            if "already" not in str(e).lower():
                print("Ses eklenemedi:", e)
        mevcut[rol] = {"voice_id": sec["voice_id"], "ad": sec.get("name"), "denenen": [d for d in denenen if d],
                       "aciklama": sec.get("description", "")[:120]}
        kullanilan.add(sec["voice_id"])
        yeni.append(rol)
    json.dump(mevcut, open(SESLER_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for rol in yeni:
        ornek = ses_roller_ornek(rol)
        yol = os.path.join(CIKTI, f"ornek_{rol}.mp3")
        seslendir(ornek, rol, yol)
        tg("sendAudio", dosyalar={"audio": open(yol, "rb")},
           caption=f"🎙 {rol}: {mevcut[rol]['ad']} — \"{etiketsiz(ornek)}\"")
    if yeni:
        tg_mesaj("🎙 Sesler seçildi. Bir sesi beğenmezsen aşama: ses, 'yeniden' kutusuna rolü yaz (ör. cemo). "
                 "Seçilen sesler kaydedildi, her bölümde aynı ses kullanılacak.")


def ses_puani(a, arama):
    """Ses açıklamasındaki kelimelere göre puan: Türkçe anadil + istenen özellikler artı, istenmeyenler eksi."""
    metin = " ".join(str(a.get(k) or "") for k in ("name", "description", "descriptive", "accent", "use_case")).lower()
    puan = 0
    if any(k in metin for k in ("türk", "turk", "istanbul", "anadolu")):
        puan += 4
    puan += 3 * sum(1 for k in arama.get("tercih", []) if k in metin)
    puan -= 6 * sum(1 for k in arama.get("kacin", []) if k in metin)
    return puan


def ses_roller_ornek(rol):
    if rol in KAR:
        return KAR[rol].get("ornek_cumle", "Merhaba, ben " + KAR[rol]["ad"] + "!")
    return KARAKTERLER["diger_sesler"][rol].get("ornek_cumle", "Hoş geldiniz, buyurun!")


def ses_ayari(kim):
    if kim in KAR:
        return KAR[kim]
    return KARAKTERLER["diger_sesler"].get(kim, KARAKTERLER["diger_sesler"]["erkek"])


def seslendir(metin, kim, hedef, voice_id=None):
    """Repliği karakterin sabit sesiyle mp3'e çevirir."""
    secili = {"voice_id": voice_id} if voice_id else (sesler_oku().get(kim) or sesler_oku().get("erkek"))
    if ELEVEN_KEY and secili:
        a = ses_ayari(kim).get("eleven", {})
        r = eleven(f"/v1/text-to-speech/{secili['voice_id']}", "POST", params={"output_format": "mp3_44100_128"},
                   json={"text": metin, "model_id": "eleven_v3", "language_code": "tr",
                         "voice_settings": {"stability": a.get("stability", 0.5),
                                            "similarity_boost": a.get("similarity_boost", 0.8),
                                            "speed": a.get("speed", 1.0)}})
        open(hedef, "wb").write(r.content)
        harcama["karakter_harf"] += len(metin)
        return hedef
    import edge_tts
    a = ses_ayari(kim)
    asyncio.run(edge_tts.Communicate(etiketsiz(metin), a["ses"], rate=a.get("hiz", "+0%"),
                                     pitch=a.get("perde", "+0Hz")).save(hedef))
    return hedef


# ------------------------------------------------------------------ 3) senaryo + plan resimleri
def esnaf_bilgisi(klasor):
    kok = os.path.join(KOK, "reklamlar", klasor)
    b = json.load(open(os.path.join(kok, "bilgi.json"), encoding="utf-8"))
    oto, kart = b.get("oto", {}), b.get("kart", {})
    temiz = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()
    return kok, b, {
        "firma": oto.get("firma", klasor), "sektor": oto.get("sektor", ""),
        "esnaf_adi": oto.get("esnaf_adi", "Esnaf"), "esnaf_cinsiyet": oto.get("esnaf_cinsiyet", "erkek"),
        "esnaf_tarif": oto.get("esnaf_tarif", ""), "esnaf_foto": oto.get("esnaf_foto"),
        "dukkan_fotolari": oto.get("dukkan_fotolari", []), "logo": oto.get("logo", kart.get("logo")),
        "urunler": oto.get("urunler", ""), "adres": temiz(kart.get("adres", "")),
        "telefon": kart.get("telefon", ""), "slogan": temiz(kart.get("slogan2", "")), "notlar": oto.get("notlar", ""),
    }


SENARYO_ISTEMI = """Sen Türkiye'de çok izlenen, Pixar tarzı 3D çizgi film skeçleri yazan komik bir senaristsin.
Dizi: "Levent'in Maceraları". Dikey (9:16) TikTok/Instagram bölümü, toplam 90-105 saniye.
Film dili: plan / karşı plan. Her KONUŞMA planında kamerada SADECE konuşan karakterin yüzü net görünür
(diğerleri arkadan, omuz üstünden ya da kadraj dışında). Böylece dudak senkronu kusursuz olur.

KARAKTERLER (konuşma tarzlarına sadık kal)
- levent: {levent_rol} Konuşma tarzı: {levent_tarz}
- cemo: {cemo_rol} Konuşma tarzı: {cemo_tarz}
- esnaf: {esnaf_adi} — {firma} sahibi ({esnaf_cinsiyet}). {esnaf_tarif} Konuşma tarzı: sıcak, esnaf ağzı, misafirperver.
- erkek / kadin: gerekirse kısa görünen yan karakterler.

SPONSOR ESNAF (hikâyenin doğal parçası; reklam kokmasın ama ürün ve dükkân net görünsün)
İşletme: {firma} | Sektör: {sektor} | Ürünler: {urunler} | Adres: {adres} | Telefon: {telefon}
Slogan: {slogan} | Notlar: {notlar}

BÖLÜM KONUSU: {konu}

KURALLAR
- 22-28 plan. Plan türleri:
  * "konusma": tek karakter, tek replik (en fazla 18 kelime, ~2-6 sn). Replikte duyguyu ElevenLabs ses etiketleriyle
    verebilirsin: [laughs], [sighs], [excited], [whispers], [surprised] (en fazla bir etiket, cümle başında).
  * "aksiyon": konuşmasız 3-4 saniyelik geçiş/aksiyon (yürüme, dükkânın dışı, ürün yakın çekimi, komik tepki).
- Planların en az %70'i konuşma olsun. İlk plan güçlü bir kanca (merak/komedi).
- 3 perde: dert/macera -> yol esnafa düşer (en az 7 plan dükkânda; ürünler ve esnaf konuşur) -> komik çözüm + başa dönen espri.
- KASA: Levent ile Cemo'nun bütçesi (TL). İlk planda başlangıç değeri; para harcanınca/kazanılınca yeni değer; diğerlerinde null.
- Temiz, herkesin güleceği mizah. Siyaset, din alayı, +18, kumar, şiddet, sağlık iddiası, rakip kötüleme, uydurma fiyat YOK.
- Son konuşmada Levent esnafın adını/sloganını doğal biçimde söylesin.
- "gorsel": İngilizce tek kare tarifi: mekân, kamera açısı (konuşmada "medium close-up of <speaker> facing the camera,
  mouth clearly visible"), ifade, arka plan. Karakterleri sadece "Levent", "Cemo", "the shop owner" diye an; kıyafet tarif etme.
- "hareket": sadece aksiyon planlarında, İngilizce kısa hareket tarifi.
- "karakterler": karede görünen herkes (konuşan ilk sırada).

SADECE şu JSON:
{{"baslik": "kısa bölüm adı",
  "planlar": [
    {{"tip": "konusma", "kim": "levent", "metin": "[excited] ...", "duygu": "excited",
      "karakterler": ["levent", "cemo"], "dukkan": false, "gorsel": "...", "kasa": 3000}},
    {{"tip": "aksiyon", "karakterler": ["levent", "cemo"], "dukkan": true, "gorsel": "...", "hareket": "...",
      "sure": 3, "kasa": null}}
  ]}}"""


KONTROLSUZ = [0]


def tutarlilik_kontrolu(resim, kimler):
    """Gemini'ye karakter kartlarıyla üretilen kareyi karşılaştırtır. Döndürür: (puan, sorun)."""
    if not kimler:
        return 10, ""
    parcalar = [{"text": "Reference character sheets:"}]
    for kid in kimler:
        parcalar += [{"text": f"{KAR[kid]['ad']}:"},
                     {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(
                         open(kucult(karakter_karti(kid), 768), "rb").read()).decode()}}]
    parcalar += [{"text": "Generated frame:"},
                 {"inline_data": {"mime_type": "image/jpeg",
                                  "data": base64.b64encode(open(kucult(resim, 768), "rb").read()).decode()}},
                 {"text": "Compare each named character in the generated frame with their reference sheet: face shape, "
                          "eyes, nose, hair, mustache/glasses, outfit and colors, body proportions. Also fail if a "
                          "character appears twice, if a face is deformed, or if there is any written text/caption "
                          "except a shop sign. Return JSON {\"puan\": 1-10, \"sorun\": \"short English description\"}."}]
    try:
        c = gemini(parcalar, sicaklik=0.1, hizli_vazgec=True)
        return int(c.get("puan", 10)), c.get("sorun", "")
    except Exception as e:
        print("Kontrol yapılamadı:", str(e)[:120])
        KONTROLSUZ[0] += 1
        return 10, ""


def taslak(klasor, konu, yeniden=""):
    os.makedirs(CIKTI, exist_ok=True)
    if any(not os.path.exists(karakter_karti(k)) for k in KAR):
        karakter()
    if ELEVEN_KEY and not all(r in sesler_oku() for r in ses_rolleri()):
        ses()
    kok, bilgi, e = esnaf_bilgisi(klasor)
    oto = os.path.join(kok, "oto")
    os.makedirs(oto, exist_ok=True)
    senaryo_yol = os.path.join(oto, "senaryo.json")

    if yeniden.strip() and os.path.exists(senaryo_yol):
        senaryo = json.load(open(senaryo_yol, encoding="utf-8"))
        cizilecek = [int(x) for x in re.findall(r"\d+", yeniden)]
    else:
        senaryo = gemini(SENARYO_ISTEMI.format(
            levent_rol=KAR["levent"]["rol"], levent_tarz=KAR["levent"]["konusma_tarzi"],
            cemo_rol=KAR["cemo"]["rol"], cemo_tarz=KAR["cemo"]["konusma_tarzi"],
            konu=konu or "Levent ile Cemo'nun başı derde girer, çözüm bu esnafta çıkar.", **e))
        json.dump(senaryo, open(senaryo_yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        for eski in os.listdir(oto):
            if eski.startswith("plan_"):
                os.remove(os.path.join(oto, eski))
        cizilecek = list(range(1, len(senaryo["planlar"]) + 1))

    stil = KARAKTERLER["stil"]
    uyarilar = []

    def ciz(no):
        p = senaryo["planlar"][no - 1]
        gorunen = [k for k in p.get("karakterler", []) if k in KAR]
        refs, tarif = [], []
        for kid in gorunen:
            refs.append(karakter_karti(kid))
            tarif.append(f"{KAR[kid]['ad']} = the character on reference sheet {len(refs)} ({KAR[kid]['tarif']})")
        if "esnaf" in p.get("karakterler", []):
            if e["esnaf_foto"]:
                refs.append(os.path.join(kok, e["esnaf_foto"]))
                tarif.append(f"the shop owner = the person in reference image {len(refs)}, as a Pixar-style 3D cartoon")
            elif e["esnaf_tarif"]:
                tarif.append(f"the shop owner is {e['esnaf_tarif']}")
        if p.get("dukkan"):
            for f in e["dukkan_fotolari"][:2] + ([e["logo"]] if e["logo"] else []):
                refs.append(os.path.join(kok, f))
            tarif.append(f"the place is the shop '{e['firma']}': match the real shop/products/logo from the photo "
                         f"references, redrawn in the same 3D animated style")
        konusan = ""
        if p["tip"] == "konusma":
            konusan = (f" The speaker {KAR.get(p['kim'], {}).get('ad', 'the shop owner')} faces the camera in medium "
                       f"close-up with the mouth clearly visible and closed in a neutral position, expression: "
                       f"{p.get('duygu', 'neutral')}. Any other character is seen only from behind or out of focus.")
        temel = (f"{stil}. {p['gorsel']}{konusan} Characters: {'; '.join(tarif)}. Every character must look EXACTLY "
                 f"like their reference sheet (same face, hair, outfit, colors, proportions). Each character appears "
                 f"only once. No subtitles, captions, speech bubbles or watermark. The story takes place in Bursa, Turkey: any signs, "
                 f"banners or labels in the background must be in TURKISH (never English), or left blank.")
        hedef = os.path.join(oto, f"plan_{no:02d}.jpg")
        istem, en_iyi = temel, (-1, None)
        for d in range(EN_FAZLA_YENIDEN + 1):
            sonuc = fal(RESIM_MODEL, {"prompt": istem, "image_urls": [resim_uri(r) for r in refs[:12]],
                                      "aspect_ratio": "9:16", "resolution": "1K", "output_format": "jpeg"})
            harcama["resim"] += 1
            aday = os.path.join(CIKTI, f"aday_{no:02d}_{d}.jpg")
            indir(sonuc["images"][0]["url"], aday)
            puan, sorun = tutarlilik_kontrolu(aday, gorunen)
            print(f"Plan {no} deneme {d + 1}: tutarlılık {puan}/10 {sorun}")
            if puan > en_iyi[0]:
                en_iyi = (puan, aday)
            if puan >= KONTROL_ESIGI:
                break
            istem = temel + f" Fix this problem from the previous attempt: {sorun}"
        os.replace(en_iyi[1], hedef)
        if en_iyi[0] < KONTROL_ESIGI:
            uyarilar.append(f"{no}. plan ({en_iyi[0]}/10)")
        return hedef

    with ThreadPoolExecutor(AYNI_ANDA) as h:
        list(h.map(ciz, cizilecek))

    basliklar = []
    for i, p in enumerate(senaryo["planlar"], 1):
        kasa = f" [KASA {p['kasa']:,} TL]".replace(",", ".") if p.get("kasa") is not None else ""
        if p["tip"] == "konusma":
            basliklar.append(f"{i}. {p['kim'].capitalize()}: {etiketsiz(p['metin'])}{kasa}")
        else:
            basliklar.append(f"{i}. (aksiyon) {p.get('hareket', '')}{kasa}")
    tg_mesaj(f"📝 {senaryo.get('baslik', '')} — {len(senaryo['planlar'])} plan\n" + "\n".join(basliklar))
    tg_albumler([os.path.join(oto, f"plan_{n:02d}.jpg") for n in cizilecek], [basliklar[n - 1] for n in cizilecek])
    tahmin = tahmini_video_maliyeti(senaryo)
    tg_mesaj(maliyet_ozeti()
             + (f"\n⚠️ Yüzü tam tutmayan planlar: {', '.join(uyarilar)} — 'yeniden' kutusuyla tekrar çizdirebilirsin."
                if uyarilar else "\n✅ Kontrol edilen planlar karakter kartlarıyla uyumlu.")
             + (f"\n👀 {KONTROLSUZ[0]} plan Google kotası yüzünden otomatik kontrol edilemedi, gözle bak."
                if KONTROLSUZ[0] else "")
             + f"\n\n▶️ Beğendiysen aşama: video. Tahmini video maliyeti ≈ {tahmin:.2f} $ (≈ {tahmin * DOLAR_TL:.0f} TL).")


def tahmini_video_maliyeti(senaryo):
    t = 0.0
    for p in senaryo["planlar"]:
        if p["tip"] == "konusma":
            t += (len(etiketsiz(p["metin"]).split()) / 2.6 + 0.6) * UCRET["avatar"]
        else:
            t += p.get("sure", 3) * UCRET["aksiyon"]
    return t


# ------------------------------------------------------------------ 4) video
_ONBELLEK_KILIT = threading.Lock()


def onbellek_anahtari(p, resim):
    ses_id = (sesler_oku().get(p.get("kim")) or {}).get("voice_id", "") if p["tip"] == "konusma" else ""
    model = AVATAR_MODEL if p["tip"] == "konusma" else f"seedance-{AKSIYON_COZUNURLUK}"
    h = hashlib.sha1(open(resim, "rb").read())
    h.update(json.dumps([p["tip"], p.get("metin"), p.get("kim"), p.get("hareket"), p.get("sure"), ses_id, model],
                        ensure_ascii=False).encode())
    return h.hexdigest()[:16]


def onbellekten(klasor_klip, no, anahtar):
    try:
        dizin = json.load(open(os.path.join(klasor_klip, "dizin.json"), encoding="utf-8"))
    except Exception:
        return None
    k = dizin.get(str(no))
    if not k or k.get("anahtar") != anahtar or not os.path.exists(os.path.join(klasor_klip, k["klip"])):
        return None
    klip = os.path.join(klasor_klip, k["klip"])
    ses = os.path.join(klasor_klip, k["ses"]) if k.get("ses") else None
    return klip, ses, tuple(k["aralik"]) if k.get("aralik") else None


def onbellege_yaz(klasor_klip, no, anahtar, sonuc):
    klip, ses, aralik = sonuc
    os.makedirs(klasor_klip, exist_ok=True)
    shutil.copy(klip, os.path.join(klasor_klip, f"klip_{no:02d}.mp4"))
    kayit = {"anahtar": anahtar, "klip": f"klip_{no:02d}.mp4", "aralik": list(aralik) if aralik else None}
    if ses:
        shutil.copy(ses, os.path.join(klasor_klip, f"ses_{no:02d}.mp3"))
        kayit["ses"] = f"ses_{no:02d}.mp3"
    with _ONBELLEK_KILIT:
        yol = os.path.join(klasor_klip, "dizin.json")
        dizin = json.load(open(yol, encoding="utf-8")) if os.path.exists(yol) else {}
        dizin[str(no)] = kayit
        json.dump(dizin, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def konusma_klibi(no, p, resim, klasor_cikti):
    ham = os.path.join(klasor_cikti, f"ses_{no:02d}.mp3")
    seslendir(p["metin"], p["kim"], ham)
    # Başa 0.25 sn, sona 0.4 sn sessizlik: karakter konuşmaya doğal girip çıksın
    pay = os.path.join(klasor_cikti, f"ses_{no:02d}_pay.mp3")
    calistir("-i", ham, "-af", "adelay=250:all=1,apad=pad_dur=0.4,aresample=44100", "-ac", "2", "-b:a", "192k", pay)
    konusan = KAR.get(p["kim"], {}).get("ad", "the shop owner")
    prompt = (f"{konusan} speaks with precise lip sync, {p.get('duygu', 'natural')} expression, natural head and "
              f"hand movement, blinking. Only {konusan} talks; everyone else keeps their mouth closed. "
              f"Pixar-style 3D animation, stable face and outfit.")
    sonuc = fal(AVATAR_MODEL, {"image_url": resim_uri(resim, 1280), "audio_url": veri_uri(pay, "audio/mpeg"),
                               "prompt": prompt})
    hedef = os.path.join(klasor_cikti, f"klip_{no:02d}.mp4")
    indir(sonuc["video"]["url"], hedef)
    harcama["avatar_sn"] += sure(pay)
    return hedef, pay, (0.25, 0.25 + sure(ham))


def aksiyon_klibi(no, p, resim, klasor_cikti):
    saniye = max(2, min(6, int(p.get("sure", 3))))
    sonuc = fal("fal-ai/bytedance/seedance/v1/pro/fast/image-to-video",
                {"prompt": (p.get("hareket") or "subtle natural motion") + ". Pixar-style 3D animation, characters keep "
                           "their exact faces and outfits, nobody talks, no text.",
                 "image_url": resim_uri(resim, 1280), "duration": str(saniye),
                 "resolution": AKSIYON_COZUNURLUK, "aspect_ratio": "9:16"})
    hedef = os.path.join(klasor_cikti, f"klip_{no:02d}.mp4")
    indir(sonuc["video"]["url"], hedef)
    harcama["aksiyon_sn"] += saniye
    return hedef, None, None


def ass_zaman(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def video(klasor):
    sys.path.insert(0, KOK)
    from bolum import resimden_video, VIDEO_AYAR, SES_AYAR

    os.makedirs(CIKTI, exist_ok=True)
    kok, bilgi, e = esnaf_bilgisi(klasor)
    oto = os.path.join(kok, "oto")
    senaryo = json.load(open(os.path.join(oto, "senaryo.json"), encoding="utf-8"))
    planlar = senaryo["planlar"]

    klasor_klip = os.path.join(oto, "klipler")
    hatalar = []

    def uret(no):
        p = planlar[no - 1]
        resim = os.path.join(oto, f"plan_{no:02d}.jpg")
        anahtar = onbellek_anahtari(p, resim)
        hazir = onbellekten(klasor_klip, no, anahtar)
        if hazir:
            print(f"Plan {no} klibi önbellekten alındı (ücret yok)")
            return hazir
        fn = konusma_klibi if p["tip"] == "konusma" else aksiyon_klibi
        try:
            sonuc = fn(no, p, resim, CIKTI)
        except Exception as e:
            print(f"Plan {no} üretilemedi: {str(e)[:200]}")
            hatalar.append(no)
            return None
        onbellege_yaz(klasor_klip, no, anahtar, sonuc)
        print(f"Plan {no} klibi hazır ({p['tip']})")
        return sonuc

    with ThreadPoolExecutor(AYNI_ANDA) as h:
        klipler = list(h.map(uret, range(1, len(planlar) + 1)))
    if hatalar:
        tg_mesaj(f"⚠️ {sorted(hatalar)} numaralı planlar üretilemedi. Hazır olanlar kaydedildi; 'video' aşamasını "
                 f"tekrar çalıştırınca SADECE eksikler üretilir (hazırlar için tekrar ödeme yok).\n" + maliyet_ozeti())
        sys.exit(1)

    parcalar, ass, zaman, son_kasa = [], [], 0.0, None
    for no, (p, (klip, ses_dosya, konusma_araligi)) in enumerate(zip(planlar, klipler), 1):
        d = sure(ses_dosya) if ses_dosya else min(sure(klip), max(2, p.get("sure", 3)))
        cikis = os.path.join(CIKTI, f"parca_{no:02d}.mp4")
        vf = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
              f"tpad=stop_mode=clone:stop_duration=3,trim=duration={d:.3f},setpts=PTS-STARTPTS[v]")
        if ses_dosya:  # temiz ElevenLabs sesi; video zaten bu sese göre konuşuyor
            calistir("-i", klip, "-i", ses_dosya, "-filter_complex",
                     vf + f";[1:a]aresample=44100,aformat=channel_layouts=stereo,apad,atrim=duration={d:.3f}[a]",
                     "-map", "[v]", "-map", "[a]", *VIDEO_AYAR, *SES_AYAR, cikis)
            b, s = konusma_araligi
            ass.append(f"Dialogue: 0,{ass_zaman(zaman + b)},{ass_zaman(zaman + s)},Alt,,0,0,0,,{etiketsiz(p['metin'])}")
        else:
            calistir("-i", klip, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", vf,
                     "-map", "[v]", "-map", "1:a", "-t", f"{d:.3f}", *VIDEO_AYAR, *SES_AYAR, cikis)
        if p.get("kasa") is not None:
            son_kasa = p["kasa"]
        if son_kasa is not None:
            ass.append(f"Dialogue: 1,{ass_zaman(zaman)},{ass_zaman(zaman + d)},Kasa,,0,0,0,,"
                       + f"KASA: {son_kasa:,} TL".replace(",", "."))
        zaman += d
        parcalar.append(cikis)

    liste = os.path.join(CIKTI, "govde.txt")
    open(liste, "w").writelines(f"file '{x}'\n" for x in parcalar)
    govde = os.path.join(CIKTI, "govde.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", govde)
    ass_yol = os.path.join(CIKTI, "altyazi.ass")
    open(ass_yol, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Alt,Inter,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,360,1\n"
        "Style: Kasa,Inter,54,&H00FFFFFF,&H00FFFFFF,&H003130D6,&H003130D6,-1,0,0,0,100,100,0,0,3,14,0,9,40,50,170,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(ass) + "\n")
    govde_yazili = os.path.join(CIKTI, "govde_yazili.mp4")
    calistir("-i", govde, "-vf", f"ass={ass_yol}", *VIDEO_AYAR, "-c:a", "copy", govde_yazili)

    renk = bilgi.get("renk", "#e3121b")
    baslik_png = os.path.join(CIKTI, "baslik.png")
    subprocess.run(["node", os.path.join(KOK, "kart.js"),
                    f"<span>LEVENT'İN MACERALARI</span>{senaryo.get('baslik', '')}", baslik_png, "baslik", renk], check=True)
    baslik = os.path.join(CIKTI, "baslik.mp4")
    resimden_video(baslik_png, 1.8, baslik)
    sira = [baslik, govde_yazili]
    if bilgi.get("kart"):
        sessiz = os.path.join(CIKTI, "bilgi_sessiz.mp4")
        subprocess.run(["node", os.path.join(KOK, "uret.js"), klasor], check=True,
                       env={**os.environ, "KARE_BAS": "480", "KARE_BIT": "690", "CIKTI": sessiz})
        bilgi_mp4 = os.path.join(CIKTI, "bilgi.mp4")
        calistir("-i", sessiz, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                 "-shortest", *VIDEO_AYAR, *SES_AYAR, bilgi_mp4)
        sira.append(bilgi_mp4)
    liste2 = os.path.join(CIKTI, "son.txt")
    open(liste2, "w").writelines(f"file '{x}'\n" for x in sira)
    ad = re.sub(r"[^A-Za-z0-9_]+", "_", f"Levent_{klasor}_{senaryo.get('baslik', 'bolum')}".translate(
        str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")))[:60]
    son = os.path.join(CIKTI, ad + ".mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste2, "-c", "copy", "-movflags", "+faststart", son)
    print(f"Bölüm hazır: {son} ({sure(son):.0f} sn)")
    if TOKEN:
        with open(son, "rb") as f:
            tg("sendVideo", dosyalar={"video": f}, supports_streaming="true",
               caption=f"🎬 Levent'in Maceraları: {senaryo.get('baslik', '')} ({sure(son):.0f} sn)")
    tg_mesaj(maliyet_ozeti())


if __name__ == "__main__":
    komut = sys.argv[1]
    arg = sys.argv[2:] + ["", "", ""]
    if komut == "karakter":
        karakter(yenile=arg[0] == "yenile")
    elif komut == "ses":
        ses(arg[0])
    elif komut == "taslak":
        taslak(arg[0], arg[1], arg[2])
    elif komut == "video":
        video(arg[0])
    else:
        sys.exit("Komut: karakter | ses | taslak | video")
