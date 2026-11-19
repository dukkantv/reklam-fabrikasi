"""YouTube yayın kuyruğu: ekle → Telegram'da onay → otomatik yükleme (19:00'da yayında).

Kullanım:
  python3 yt_kuyruk.py ekle <kanal> <video.mp4> "<başlık>" "<açıklama>" "<etiket1,etiket2>"
  python3 yt_kuyruk.py kontrol      # onayları okur, onaylananları YouTube'a yükler

Kurallar:
- Dükkan TV: Levent onay vermeden HİÇBİR video yayınlanmaz. İptal ya da 3 gün cevapsız kalırsa silinir.
- Dükkan TV, Drama Bite, Kasa Kurgu, Gizli Tarih (YAYIN_KANALLARI): onay beklemeden sıraya girer; "Durdur" ile yüklenmeden önce iptal edilebilir.
- Onaylanan video YouTube'a "planlı" yüklenir: saat 18:30'dan önce onaylanırsa aynı gün 19:00,
  sonra onaylanırsa ertesi gün 19:00 (Türkiye saati) yayına girer.
- Günlük stok ("gunluk": kısa mizah serisi): onaylanan videolar hemen değil, HER GÜN BİR TANE sırayla
  yüklenir (en eskisi önce). Onay için 14 gün beklenir.
- Telegram güncellemeleri ONAYLANMAZ (offset kullanılmaz), böylece aynı botu kullanan
  'Bölüm Üret' işinin klip kuyruğu bozulmaz.
"""
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys

from yt_ortak import KOK, erisim_anahtari, istek, kanal_bilgi, telegram
import ig_ortak
from ig_ortak import fb_bekliyor_mu, fb_reels_yukle, ig_hesap, reels_yukle, reels_yukle_fb_kaynak
from tt_ortak import taslak_yukle, tt_hesap


def deneme_reels_mi(kayit):
    """Deneme Reels (yalnızca takip etmeyenlere önce gösterim) uygulanacak videolar.
    16 Kasım 2026 denemesi: Kasa Kurgu'nun Katil Kim serisi."""
    # 18 Kasım 2026: Meta uygulamaya bu izni vermiyor (kod 10, alt kod 2207081: "Application does not have
    # permission"). İzin açılana kadar kapalı; videolar normal Reels olarak paylaşılır.
    return False and (kayit.get("kanal") == "kasakurgu" and "Katil Kim" in kayit.get("baslik", "")
            and not kayit.get("ig_deneme"))


def ig_paylasildi_mesaji(ad, kayit, link):
    ek = " (Deneme Reels: önce takip etmeyenlere gösteriliyor, tutarsa Instagram herkese açar)" if kayit.get("ig_deneme_reels") else ""
    return f"📸 {ad}: \"{kayit['baslik']}\" Instagram'da Reels olarak paylaşıldı{ek}.\n{link}"


def tt_bekliyor(kayit):
    """Bu kanal için TikTok bağlıysa ve video henüz gönderilmediyse True."""
    if kayit.get("tt") in ("taslak", "hata") or kayit.get("uzun"):
        return False
    try:
        return tt_hesap(kayit["kanal"]) is not None
    except Exception:
        return False


def urun_bilgisi():
    try:
        return json.load(open(os.path.join(KOK, "urunler.json"), encoding="utf-8"))
    except Exception:
        return {}


def urunlu_aciklama(aciklama):
    """YouTube açıklamasının sonuna dijital ürün linklerini ekler (zaten varsa tekrar eklemez)."""
    u = urun_bilgisi()
    if not u.get("urunler") or u["urunler"][0]["link"] in aciklama:
        return aciklama
    blok = u.get("youtube_baslik", "🛒 Ürünlerimiz:") + "\n" + "\n".join(
        f"▶ {x['ad']}: {x['link']}" for x in u["urunler"])
    return (aciklama.rstrip() + "\n\n" + blok)[:4900]


def kisa_urun_satiri():
    return urun_bilgisi().get("kisa_satir", "")


def tt_aciklama(kayit):
    return kayit["baslik"].replace("#shorts", "").replace("#Shorts", "").strip(" |") + "\n\n" + \
        (kisa_urun_satiri() + "\n\n" if kisa_urun_satiri() else "") + \
        " ".join("#" + e.replace(" ", "") for e in kayit.get("etiketler", [])[:6]) + " #fyp #keşfet"


def ig_bekliyor(kayit):
    """Bu kanal için Instagram bağlıysa ve henüz paylaşılmadıysa True."""
    if kayit.get("ig") in ("paylasildi", "hata") or kayit.get("uzun"):
        return False
    # Instagram reddettiyse araları açarak dene: 1., 2., 3. denemeden sonra 2 / 4 / 8 saat bekle.
    # (Sık deneme Instagram'ın yükleme kısıtlamasını uzatıyordu; 19 Kas 2026'da 19 deneme görüldü.)
    son = kayit.get("ig_son_deneme")
    if son:
        ara = dt.timedelta(hours=2 ** min(kayit.get("ig_deneme", 1), 3))
        if dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(son) < ara:
            return False
    try:
        return ig_hesap(kayit["kanal"]) is not None
    except Exception:
        return False


def fb_bekliyor(kayit):
    """Kanalın Facebook sayfasına Reels izni varsa ve henüz paylaşılmadıysa True."""
    if kayit.get("fb") in ("paylasildi", "hata") or kayit.get("uzun"):
        return False
    try:
        return fb_bekliyor_mu(kayit["kanal"])
    except Exception:
        return False


def ig_aciklama(kayit):
    baslik = kayit["baslik"].replace("#shorts", "").replace("#Shorts", "").strip(" |")
    etiket = " ".join("#" + e.replace(" ", "") for e in kayit.get("etiketler", [])[:8])
    urun = kisa_urun_satiri()
    return f"{baslik}\n\n" + (f"{urun}\n\n" if urun else "") + etiket

# Yayın yetkisi: tüm kanallar onaysız otomatik yayın (Levent, 14 Kasım 2026: reklam/satış olmadığı için Dükkan TV dahil).
# Her video Telegram'a "Durdur" düğmesiyle gelir; Levent istemezse yüklenmeden önce durdurur.
YAYIN_KANALLARI = {"dukkantv", "dramabite", "kasakurgu", "gizlitarih", "ilturnuva"}

KUYRUK = os.path.join(KOK, "kuyruk")
TR = dt.timezone(dt.timedelta(hours=3))
TG = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', '')}"
# Cloudflare onay dinleyicisi (cloudflare/onay-worker.js). Boşsa sadece Telegram getUpdates kullanılır.
ONAY_URL = os.environ.get("ONAY_URL", "").rstrip("/")
# Dinleyiciyle paylaşılan gizli değer, bot anahtarından türetilir (kodda şifre tutulmaz)
ONAY_GIZLI = hashlib.sha256(os.environ.get("TELEGRAM_BOT_TOKEN", "").encode()).hexdigest()[:48]


def gh(*arg):
    return subprocess.run(["gh", *arg], check=True, capture_output=True, text=True).stdout


def kaydet(kayit):
    json.dump(kayit, open(os.path.join(KUYRUK, f"{kayit['id']}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def ekle(kanal, video, baslik, aciklama="", etiketler="", gunluk="", kapak="", kategori=""):
    os.makedirs(KUYRUK, exist_ok=True)
    simdi = dt.datetime.now(TR)
    kid = f"{simdi:%Y%m%d-%H%M%S}-{kanal}"
    dosya = f"{kid}.mp4"
    # Video, depoyu şişirmesin diye "kuyruk" sürümüne (release) ek dosya olarak konur
    try:
        gh("release", "view", "kuyruk")
    except subprocess.CalledProcessError:
        gh("release", "create", "kuyruk", "--title", "Yayın kuyruğu", "--notes", "Onay bekleyen videolar")
    kopya = os.path.join("/tmp", dosya)
    subprocess.run(["cp", video, kopya], check=True)
    gh("release", "upload", "kuyruk", kopya, "--clobber")
    kayit = {"id": kid, "kanal": kanal, "baslik": baslik[:100], "aciklama": aciklama[:4900],
             "etiketler": [e.strip() for e in etiketler.split(",") if e.strip()][:15],
             "dosya": dosya, "durum": "bekliyor", "eklendi": simdi.isoformat()}
    if gunluk:
        kayit["gunluk"] = True
    if kapak and os.path.exists(kapak):  # uzun video: kapak resmi + Reels/TikTok'a gitmez
        kad = f"{kid}-kapak.jpg"
        subprocess.run(["cp", kapak, os.path.join("/tmp", kad)], check=True)
        gh("release", "upload", "kuyruk", os.path.join("/tmp", kad), "--clobber")
        kayit.update(kapak=kad, uzun=True)
    if kategori:
        kayit["kategori"] = kategori
    if os.environ.get("DERLEME"):
        kayit.update(derleme=True, sira="0" + kid)
    if os.environ.get("SABIT_YAYIN"):   # ör. lansman videoları: "2026-11-21T13:00:00+03:00"
        kayit["sabit_yayin"] = os.environ["SABIT_YAYIN"]
    ad = kanal_bilgi(kanal)["ad"]
    if kanal in YAYIN_KANALLARI:
        # Yayın yetkisi Claude'da: onay beklemeden sıraya girer; Levent isterse yüklenmeden önce durdurabilir
        kayit["durum"] = "onaylandi"
        kayit["otomatik"] = True
        klavye = {"inline_keyboard": [[{"text": "⛔ Durdur (yayınlama)", "callback_data": f"yt:iptal:{kid}"}]]}
        cevap = telegram(f"🚀 Otomatik yayın sırasına girdi → {ad}\n\n🎬 {kayit['baslik']}\n\n"
                         f"Onay gerekmez (Yayın hesabı). İlk boş akşam saatinde YouTube'da, aynı saatte "
                         f"Instagram'da yayına girer. İstemezsen yüklenmeden önce \"Durdur\"a bas.",
                         reply_markup=json.dumps(klavye))
    elif gunluk:
        klavye = {"inline_keyboard": [[{"text": "✅ Onayla (stoğa al)", "callback_data": f"yt:onay:{kid}"},
                                       {"text": "❌ Yayınlama", "callback_data": f"yt:iptal:{kid}"}]]}
        metin = (f"📦 Günlük mizah stoğu → {ad}\n\n🎬 {kayit['baslik']}\n\n"
                 f"Onaylarsan stoğa girer; stoktaki videolar her gün BİR tane, 19:00 civarında sırayla "
                 f"(YouTube + Instagram) yayına girer. 14 gün içinde onaylamazsan silinir.")
        cevap = {}
        try:  # video ve butonlar tek mesajda gelsin
            import requests
            with open(video, "rb") as f:
                cevap = requests.post(f"{TG}/sendVideo", data={
                    "chat_id": os.environ.get("TELEGRAM_CHAT_ID"), "caption": metin, "supports_streaming": "true",
                    "reply_markup": json.dumps(klavye)}, files={"video": f}, timeout=300).json()
        except Exception as e:
            print("Video Telegram'a gönderilemedi:", str(e)[:200])
        if not cevap.get("ok"):
            cevap = telegram(metin + "\n(Video GitHub'daki çalışmanın Artifacts kısmında.)", reply_markup=json.dumps(klavye))
    else:
        klavye = {"inline_keyboard": [[{"text": "✅ Onayla", "callback_data": f"yt:onay:{kid}"},
                                       {"text": "❌ Yayınlama", "callback_data": f"yt:iptal:{kid}"}]]}
        cevap = telegram(f"📺 YouTube'a yüklensin mi? → {ad}\n\n🎬 {kayit['baslik']}\n\n"
                         f"Onaylarsan ilk boş akşam saatinde (18:00–21:30 arası, diğer videolarla çakışmadan) yayına girer.\n"
                         f"Video yukarıda Telegram'a gelen son video.",
                         reply_markup=json.dumps(klavye))
    kayit["mesaj_id"] = (cevap.get("result") or {}).get("message_id")
    if (cevap.get("result") or {}).get("video"):
        kayit["videolu"] = True
    kaydet(kayit)
    print("Kuyruğa eklendi:", kid)


# Yayın saatleri: videolar aynı anda çıkmasın, izleyici birinde takılı kalmasın diye aralıklı.
# Her kanalın tercih ettiği saatler; boş olan ilk saat seçilir. Kanallar arası en az 30 dk,
# aynı kanalın iki videosu arası en az 60 dk.
SAATLER = ["17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30"]
TERCIH = {"dukkantv": ["19:00", "18:00", "20:00", "21:00"],
          # Kasa Kurgu'nun günde 2 videosu (500 TL + Katil Kim?) arasında 2,5–3,5 saat olsun (Levent, 15.11.2026)
          "kasakurgu": ["18:00", "21:00", "17:30", "20:30", "21:30"],
          "dramabite": ["20:00", "21:00", "18:00", "19:00"],
          # 81 İl Turnuvası: genç kitle, okul/iş çıkışı (Kasım 2026)
          "ilturnuva": ["17:30", "18:30", "19:30", "20:30"]}
AYNI_KANAL_ARALIK = {"kasakurgu": 2.5 * 3600}
GUNDE_BIR = {"ilturnuva", "gizlitarih"}   # turnuva fikstürü günde 1 maç; belgesel günde en fazla 1   # sn; diğer kanallarda aynı kanalın iki videosu arası 1 saat


def dolu_zamanlar():
    zamanlar = []
    for p in glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
            if k.get("yayin"):
                zamanlar.append((k["kanal"], dt.datetime.fromisoformat(k["yayin"])))
        except Exception:
            pass
    return zamanlar


def gunluk_gunler():
    """Günlük stoktan yayına planlanmış videoların tarihleri."""
    gunler = set()
    for p in glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
            if k.get("gunluk") and k.get("yayin"):
                gunler.add(dt.datetime.fromisoformat(k["yayin"]).astimezone(TR).date())
        except Exception:
            pass
    return gunler


def ayni_tur_gunler(kanal, uzun):
    """Kanalın aynı türden (uzun belgesel / kısa video) yayın planlanmış günleri."""
    gunler = set()
    for p in glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
            if k.get("kanal") == kanal and k.get("yayin") and bool(k.get("uzun")) == bool(uzun):
                gunler.add(dt.datetime.fromisoformat(k["yayin"]).astimezone(TR).date())
        except Exception:
            pass
    return gunler


def yayin_zamani(kanal="dukkantv", gunluk=False, uzun=False):
    simdi = dt.datetime.now(TR)
    dolu = dolu_zamanlar()
    yasak_gunler = gunluk_gunler() if gunluk else set()
    sira = TERCIH.get(kanal, []) + [x for x in SAATLER if x not in TERCIH.get(kanal, [])]
    for gun in range(0, 14):
        tarih = (simdi + dt.timedelta(days=gun)).date()
        if tarih in yasak_gunler:
            continue
        if kanal in GUNDE_BIR and tarih in ayni_tur_gunler(kanal, uzun):
            continue  # bu kanala günde en fazla 1 video (turnuva/belgesel takvimi kaymasın; Shorts ayrı sayılır)
        for saat in sira:
            hh, mm = map(int, saat.split(":"))
            aday = dt.datetime(tarih.year, tarih.month, tarih.day, hh, mm, tzinfo=TR)
            if aday < simdi + dt.timedelta(minutes=30):
                continue
            cakisma = any(abs((aday - z).total_seconds()) < (AYNI_KANAL_ARALIK.get(kanal, 3600) if k == kanal else 1800)
                          for k, z in dolu)
            if not cakisma:
                return aday
    return simdi.replace(hour=19, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)


def zaman_sec(kayit):
    """Kayıtta sabit yayın saati varsa (ve en az 30 dk sonraysa) onu, yoksa ilk boş akşam saatini kullan."""
    if kayit.get("sabit_yayin"):
        z = dt.datetime.fromisoformat(kayit["sabit_yayin"])
        if z > dt.datetime.now(TR) + dt.timedelta(minutes=30):
            return z
    return yayin_zamani(kayit["kanal"], kayit.get("gunluk", False), kayit.get("uzun", False))


def youtube_yukle(kayit):
    token = erisim_anahtari(kayit["kanal"])
    yerel = os.path.join("/tmp", kayit["dosya"])
    gh("release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber")
    boyut = os.path.getsize(yerel)
    zaman = zaman_sec(kayit)
    ust = {"snippet": {"title": kayit["baslik"], "description": urunlu_aciklama(kayit["aciklama"]), "tags": kayit["etiketler"],
                       "categoryId": kayit.get("kategori") or "24", "defaultLanguage": "tr", "defaultAudioLanguage": "tr"},
           "status": {"privacyStatus": "private", "publishAt": zaman.astimezone(dt.timezone.utc).isoformat()
                      .replace("+00:00", "Z"), "selfDeclaredMadeForKids": False}}
    kod, bas, veri = istek(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        method="POST", json_govde=ust,
        headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(boyut)})
    yer = bas.get("Location") or bas.get("location")
    if kod != 200 or not yer:
        raise RuntimeError(f"Yükleme başlatılamadı ({kod}): {veri}")
    with open(yerel, "rb") as f:
        kod, _, veri = istek(yer, method="PUT", ham=f.read(), zaman=900,
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"})
    if kod not in (200, 201) or "id" not in veri:
        raise RuntimeError(f"Yükleme bitmedi ({kod}): {str(veri)[:300]}")
    if kayit.get("kapak"):
        try:
            gh("release", "download", "kuyruk", "-p", kayit["kapak"], "-D", "/tmp", "--clobber")
            k, _, v = istek(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={veri['id']}",
                            method="POST", ham=open(os.path.join("/tmp", kayit["kapak"]), "rb").read(),
                            headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
            print("Kapak:", k, str(v)[:150])
            if k == 200:
                kayit["kapak_tamam"] = True
            if k != 200:
                telegram(f"⚠️ Kapak resmi yüklenemedi ({k}). Kanalda telefon doğrulaması gerekebilir: "
                         "youtube.com/verify")
        except Exception as e:
            print("Kapak hatası:", str(e)[:150])
    return veri["id"], zaman


def mesaj_guncelle(kayit, metin):
    if kayit.get("mesaj_id"):
        veri = {"chat_id": os.environ.get("TELEGRAM_CHAT_ID"), "message_id": kayit["mesaj_id"]}
        if kayit.get("videolu"):  # video mesajında metin "caption" olarak durur
            istek(f"{TG}/editMessageCaption", veri={**veri, "caption": metin})
        else:
            istek(f"{TG}/editMessageText", veri={**veri, "text": metin})


def kontrol():
    kayitlar = {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8"))
                for p in glob.glob(os.path.join(KUYRUK, "*.json"))}
    if not kayitlar:
        print("Kuyruk boş.")
        return
    kod, _, guncel = istek(f"{TG}/getUpdates?timeout=0&allowed_updates=%5B%22message%22%2C%22callback_query%22%5D")
    sonuc = (guncel or {}).get("result", []) if isinstance(guncel, dict) else []
    print(f"Telegram getUpdates: kod={kod}, {len(sonuc)} güncelleme,",
          "butonlar:", [(u.get("callback_query") or {}).get("data") for u in sonuc if u.get("callback_query")],
          "" if sonuc or kod == 200 else str(guncel)[:200])
    if kod == 409:
        _, _, wh = istek(f"{TG}/getWebhookInfo")
        print("Webhook:", str(wh)[:200])
    for u in sonuc:
        cq = u.get("callback_query") or {}
        parca = (cq.get("data") or "").split(":")
        if len(parca) != 3 or parca[0] != "yt" or parca[2] not in kayitlar:
            continue
        kayit = kayitlar[parca[2]]
        istek(f"{TG}/answerCallbackQuery", veri={"callback_query_id": cq["id"], "text": "Alındı 👍"})
        if kayit["durum"] == "bekliyor":
            kayit["durum"] = "onaylandi" if parca[1] == "onay" else "iptal"
            kaydet(kayit)
        elif kayit["durum"] == "onaylandi" and kayit.get("otomatik") and parca[1] == "iptal":
            kayit["durum"] = "iptal"   # otomatik yayın, yüklenmeden önce durduruldu
            kaydet(kayit)

    # Cloudflare onay dinleyicisinden (anında onay) gelen kararlar
    if ONAY_URL:
        kod, _, kararlar = istek(f"{ONAY_URL}/onaylar?k={ONAY_GIZLI}", headers={"User-Agent": "dukkantv-bot"})
        if kod == 200 and isinstance(kararlar, dict):
            print("Dinleyiciden gelen kararlar:", {k: v.get("karar") for k, v in kararlar.items()})
            for kid, k in kararlar.items():
                kayit = kayitlar.get(kid)
                if kayit and kayit["durum"] == "bekliyor":
                    kayit["durum"] = "onaylandi" if k.get("karar") == "onay" else "iptal"
                    kaydet(kayit)
                elif kayit and kayit["durum"] == "onaylandi" and kayit.get("otomatik") and k.get("karar") != "onay":
                    kayit["durum"] = "iptal"
                    kaydet(kayit)
                # Karar ancak iş kesinleşince (yüklendi / silindi) dinleyiciden silinir; arada iş
                # yarıda kalırsa bir sonraki kontrolde karar yeniden okunur.
                if kayit is None or kayit["durum"] not in ("bekliyor", "onaylandi"):
                    istek(f"{ONAY_URL}/onaylar?k={ONAY_GIZLI}&id={kid}", method="DELETE",
                          headers={"User-Agent": "dukkantv-bot"})
        else:
            print(f"Onay dinleyicisine ulaşılamadı ({kod}): {str(kararlar)[:200]}")

    simdi = dt.datetime.now(TR)
    # Günlük stok: bugün ya da ileri bir güne planlanmış stok videosu yoksa, en eski onaylı olan yüklenir; diğerleri bekler.
    # "sira" varsa onu kullan (derlemeler sıranın başına girer: Pazar günü yayınlansın diye)
    stok = sorted((k for k in kayitlar.values() if k.get("gunluk") and k["durum"] == "onaylandi"),
                  key=lambda k: k.get("sira", k["id"]))
    sradaki = None
    if stok and not any(g >= simdi.date() for g in gunluk_gunler()):
        sradaki = stok[0]["id"]
    for sira_no, k in enumerate(stok, 1):
        if not k.get("stok_bildirildi"):
            k["stok_bildirildi"] = True
            mesaj_guncelle(k, f"📦 Stoğa alındı: \"{k['baslik']}\" — stokta {len(stok)} video var, "
                              f"her gün bir tanesi sırayla yayına girer.")
            kaydet(k)
    for kayit in kayitlar.values():
        ad = kanal_bilgi(kayit["kanal"])["ad"]
        if kayit["durum"] == "onaylandi" and kayit.get("gunluk") and kayit["id"] != sradaki:
            continue  # sırası gelmedi
        if kayit["durum"] == "onaylandi":
            try:
                vid, zaman = youtube_yukle(kayit)
                kayit.update(durum="yuklendi", video_id=vid, yayin=zaman.isoformat())
                kaydet(kayit)
                try:  # kanal oynatma listesine ekle (kanal_ayarlari.json kuralları)
                    from kanal_ayar import listeye_ekle
                    listeye_ekle(kayit["kanal"], vid, kayit["baslik"])
                except Exception as e:
                    print("Oynatma listesine eklenemedi:", str(e)[:200])
                metin = (f"✅ {ad}: \"{kayit['baslik']}\" yüklendi.\n"
                         f"🕖 {zaman:%d.%m %H:%M}'da yayına girecek.\nhttps://youtube.com/{'watch?v=' if kayit.get('uzun') else 'shorts/'}{vid}")
                mesaj_guncelle(kayit, metin)
                telegram(metin)
            except Exception as e:
                kayit["hata"] = str(e)[:300]
                kaydet(kayit)
                telegram(f"⚠️ {ad}: \"{kayit['baslik']}\" yüklenemedi: {str(e)[:200]}\nBir sonraki kontrolde tekrar denenecek.")
        elif kayit["durum"] == "iptal" or (kayit["durum"] == "bekliyor" and
                                            simdi - dt.datetime.fromisoformat(kayit["eklendi"])
                                            > dt.timedelta(days=14 if kayit.get("gunluk") else 3)):
            mesaj_guncelle(kayit, f"🗑️ {ad}: \"{kayit['baslik']}\" yayınlanmadı.")
            try:
                gh("release", "delete-asset", "kuyruk", kayit["dosya"], "-y")
            except subprocess.CalledProcessError:
                pass
            os.remove(os.path.join(KUYRUK, f"{kayit['id']}.json"))
        elif kayit["durum"] == "yuklendi" and (ig_bekliyor(kayit) or tt_bekliyor(kayit) or fb_bekliyor(kayit)):
            # YouTube'a planlı yüklendi; yayın saatinde Instagram'a Reels, TikTok'a taslak olarak gider
            if simdi < dt.datetime.fromisoformat(kayit["yayin"]):
                continue
            if ig_bekliyor(kayit) and kayit.get("fb_id"):
                # Doğrudan yükleme daha önce reddedildiyse Facebook'taki kopyanın adresiyle dene
                try:
                    mid, link = reels_yukle_fb_kaynak(kayit["kanal"], kayit["fb_id"], ig_aciklama(kayit), deneme_reels_mi(kayit))
                    kayit.update(ig="paylasildi", ig_id=mid, ig_link=link, ig_yol="fb_kaynak", ig_deneme_reels=ig_ortak.SON_DENEME)
                    kaydet(kayit)
                    telegram(ig_paylasildi_mesaji(ad, kayit, link))
                except Exception as e:
                    print(f"Instagram (Facebook kaynağı) hatası ({kayit['id']}):", str(e)[:300])
                    if "2207076" in str(e) or "2207001" in str(e):
                        # Meta tarafında geçici arıza: doğrudan yüklemeyi de boşuna deneme, bir saat sonra tekrar
                        kayit["ig_deneme"] = kayit.get("ig_deneme", 0) + 1
                        kayit["ig_son_deneme"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                        kaydet(kayit)
            if ig_bekliyor(kayit):
                try:
                    gh("release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber")
                    yol = os.path.join("/tmp", kayit["dosya"])
                    try:
                        mid, link = reels_yukle(kayit["kanal"], yol, ig_aciklama(kayit), deneme_reels_mi(kayit))
                    except RuntimeError as e1:
                        if "Request processing failed" in str(e1):
                            raise  # yükleme kısıtlaması: yeniden kodlamak işe yaramaz, saatler sonra tekrar denenir
                        # Instagram bazı videoları "ProcessingFailedError" ile reddediyor (ör. çok düşük bit hızı).
                        # Instagram'ın önerdiği ayarlarla yeniden kodlayıp bir kez daha dene.
                        print(f"Instagram ilk deneme ({kayit['id']}):", str(e1)[:300], "→ yeniden kodlanıyor")
                        yeni = yol[:-4] + "_ig.mp4"
                        if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
                            subprocess.run("sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg",
                                           shell=True, check=True)
                        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, "-c:v", "libx264",
                                        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
                                        "-b:v", "3500k", "-maxrate", "5000k", "-bufsize", "7000k",
                                        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k",
                                        "-movflags", "+faststart", yeni], check=True)
                        mid, link = reels_yukle(kayit["kanal"], yeni, ig_aciklama(kayit), deneme_reels_mi(kayit))
                    kayit.update(ig="paylasildi", ig_id=mid, ig_link=link, ig_deneme_reels=ig_ortak.SON_DENEME)
                    kaydet(kayit)
                    telegram(ig_paylasildi_mesaji(ad, kayit, link))
                except Exception as e:
                    print(f"Instagram hatası ({kayit['id']}):", str(e)[:400])
                    kayit["ig_deneme"] = kayit.get("ig_deneme", 0) + 1
                    kayit["ig_son_deneme"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                    if kayit["ig_deneme"] >= 4:  # 2+4+8 saat aralıklı 4 deneme; sonra bırak (kota yememesi için)
                        kayit["ig"] = "hata"
                        telegram(f"⚠️ {ad}: Instagram paylaşımı 4 kez başarısız: {str(e)[:200]}")
                    kaydet(kayit)
            if fb_bekliyor(kayit):
                try:
                    gh("release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber")
                    fid = fb_reels_yukle(kayit["kanal"], os.path.join("/tmp", kayit["dosya"]), ig_aciklama(kayit))
                    kayit.update(fb="paylasildi", fb_id=fid)
                    kaydet(kayit)
                    telegram(f"📘 {ad}: \"{kayit['baslik']}\" Facebook sayfasında Reels olarak paylaşıldı.")
                except Exception as e:
                    print(f"Facebook hatası ({kayit['id']}):", str(e)[:400])
                    kayit["fb_deneme"] = kayit.get("fb_deneme", 0) + 1
                    if kayit["fb_deneme"] >= 4:
                        kayit["fb"] = "hata"
                        telegram(f"⚠️ {ad}: Facebook Reels paylaşımı 4 kez başarısız: {str(e)[:200]}")
                    kaydet(kayit)
            if tt_bekliyor(kayit):
                try:
                    gh("release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber")
                    pid = taslak_yukle(kayit["kanal"], os.path.join("/tmp", kayit["dosya"]))
                    kayit.update(tt="taslak", tt_id=pid)
                    kaydet(kayit)
                    telegram(f"🎵 {ad}: \"{kayit['baslik']}\" TikTok'a taslak olarak gönderildi.\n"
                             f"TikTok'ta taslağı aç → alttaki mesajdaki açıklamaya bir kez dokun (kopyalanır) → yapıştır → Paylaş.")
                    import html
                    telegram(f"<code>{html.escape(tt_aciklama(kayit))}</code>", parse_mode="HTML")
                except Exception as e:
                    print(f"TikTok hatası ({kayit['id']}):", str(e)[:400])
                    kayit["tt_deneme"] = kayit.get("tt_deneme", 0) + 1
                    if kayit["tt_deneme"] >= 3:
                        kayit["tt"] = "hata"
                        telegram(f"⚠️ {ad}: TikTok gönderimi 3 kez başarısız: {str(e)[:200]}")
                    kaydet(kayit)
        elif kayit["durum"] == "yuklendi":
            # Yayın saatinden önce arşivleme: o arada kanala Instagram/TikTok/Facebook bağlanabilir
            if simdi < dt.datetime.fromisoformat(kayit["yayin"]) + dt.timedelta(hours=1):
                continue
            # Instagram denemesi bekleme süresindeyse (saatte bir dener) arşivleme: yoksa paylaşılmadan kalır.
            # 16 Kasım 2026: Drama Bite "Gece Gelen Mesaj" bu yüzden Instagram'a gitmeden arşivlendi.
            if (kayit.get("ig") not in ("paylasildi", "hata") and not kayit.get("uzun") and kayit.get("ig_son_deneme")
                    and simdi < dt.datetime.fromisoformat(kayit["yayin"]) + dt.timedelta(hours=30)):
                continue
            try:
                gh("release", "delete-asset", "kuyruk", kayit["dosya"], "-y")
            except subprocess.CalledProcessError:
                pass
            os.makedirs(os.path.join(KUYRUK, "arsiv"), exist_ok=True)
            os.replace(os.path.join(KUYRUK, f"{kayit['id']}.json"),
                       os.path.join(KUYRUK, "arsiv", f"{kayit['id']}.json"))


YORUM_SABLON = {
    "ilturnuva": "🏆 Bütün maçlar sırayla burada 👉 {link}\nŞehrin hangi grupta? Yorumlara yaz, takip et, maçını kaçırma!",
    "kasakurgu": "🕵️ Serinin bütün videoları burada 👉 {link}\nSen ne düşünüyorsun? Cevabını yorumlara yaz 👇",
    "dramabite": "💔 Bütün hikâyeler burada 👉 {link}\nSen olsan ne yapardın? Yorumlara yaz 👇",
    "dukkantv": "😂 Levent & Cemo'nun bütün skeçleri burada 👉 {link}\nEn çok hangisine güldün? Yaz bakalım 👇",
    "gizlitarih": "📜 Bütün bölümler burada 👉 {link}\nSıradaki bölümde hangi sırrı anlatalım? Yorumlara yaz 👇",
}


def seri_satiri(baslik, liste_adi):
    """Yorumun ilk satırı: serideki yer + listenin adı (Shorts yorumlarında bağlantı tıklanmadığı için
    izleyici listeyi kanal sayfasındaki 'Oynatma listeleri' sekmesinde adından bulabilsin)."""
    import re
    yer = f"📺 Kanal sayfasında 'Oynatma listeleri' → \"{liste_adi}\""
    m = re.search(r"Gün\s*(\d+)\s*/", baslik)
    if m and int(m.group(1)) > 1:
        return f"⏪ Önceki bölüm: Gün {int(m.group(1)) - 1} · Tüm günler sırayla: {yer}"
    m = re.search(r"Dosya\s*#\s*(\d+)", baslik)
    if m and int(m.group(1)) > 1:
        return f"🔎 Önceki vaka: Dosya #{int(m.group(1)) - 1:02d} · Bütün vakalar: {yer}"
    m = re.search(r"(\d+)\.\s*Tur\s*·\s*(\w+)\s*Grubu", baslik)
    if m:
        return f"🏆 {m.group(1)}. Tur, {m.group(2)} Grubu · Bütün maçlar sırayla: {yer}"
    return f"▶️ Hepsi tek listede: {yer}"


def yorumlar(gun=14):
    """Yayına girmiş videoların altına kanal adına 'serinin bütün videoları' yorumu bırakır (bir kez)."""
    from kanal_ayar import kanal_listeleri, kural_uyar
    simdi = dt.datetime.now(TR)
    listeler = {}
    for p in sorted(glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json"))):
        k = json.load(open(p, encoding="utf-8"))
        if not k.get("video_id") or not k.get("yayin") or k.get("yorum") or k["kanal"] not in YORUM_SABLON:
            continue
        zaman = dt.datetime.fromisoformat(k["yayin"])
        if zaman > simdi or simdi - zaman > dt.timedelta(days=gun) or k.get("yorum_deneme", 0) >= 3:
            continue
        try:
            if k["kanal"] not in listeler:
                listeler[k["kanal"]] = kanal_listeleri(k["kanal"])
            eslesen = next(((pid, l) for pid, l in listeler[k["kanal"]] if kural_uyar(l["kural"], k["baslik"])), None)
            if not eslesen:
                continue
            pid, liste = eslesen
            metin = YORUM_SABLON[k["kanal"]].format(link=f"https://www.youtube.com/playlist?list={pid}")
            metin = seri_satiri(k["baslik"], liste["ad"]) + "\n" + metin
            tok = erisim_anahtari(k["kanal"])
            kod, _, v = istek("https://www.googleapis.com/youtube/v3/commentThreads?part=snippet", method="POST",
                              headers={"Authorization": f"Bearer {tok}"},
                              json_govde={"snippet": {"videoId": k["video_id"],
                                                      "topLevelComment": {"snippet": {"textOriginal": metin}}}})
            if kod not in (200, 201):
                raise RuntimeError(f"{kod} {str(v)[:200]}")
            k["yorum"] = v["id"]
            print("yorum bırakıldı:", k["kanal"], k["baslik"][:40])
        except Exception as e:
            k["yorum_deneme"] = k.get("yorum_deneme", 0) + 1
            print("yorum hatası:", k["id"], str(e)[:250])
        json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def geri_al(kid):
    """Arşive erken kaldırılmış bir videoyu Telegram'daki onay mesajından geri indirip kuyruğa döndürür."""
    import requests
    ap = os.path.join(KUYRUK, "arsiv", f"{kid}.json")
    kayit = json.load(open(ap, encoding="utf-8"))
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    anahtar = os.environ.get("GERI_AL_ANAHTAR", "")
    fid = None
    for mid in range(kayit["mesaj_id"] + 2, kayit["mesaj_id"] - 12, -1):
        r = requests.post(f"{TG}/forwardMessage", data={"chat_id": chat, "from_chat_id": chat,
                                                         "message_id": mid, "disable_notification": "true"}, timeout=60).json()
        if not r.get("ok"):
            continue
        msg = r["result"]
        requests.post(f"{TG}/deleteMessage", data={"chat_id": chat, "message_id": msg["message_id"]}, timeout=60)
        v = msg.get("video") or msg.get("document")
        yazi = msg.get("caption", "")
        print(mid, "video" if v else "metin", v and v.get("duration"), yazi[:80].replace("\n", " "))
        if v and (not anahtar or anahtar in yazi):
            fid = v["file_id"]
            break
    if not fid:
        raise SystemExit("video bulunamadı")
    yol = requests.get(f"{TG}/getFile", params={"file_id": fid}, timeout=60).json()["result"]["file_path"]
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    veri = requests.get(f"https://api.telegram.org/file/bot{tok}/{yol}", timeout=300).content
    hedef = os.path.join("/tmp", kayit["dosya"])
    open(hedef, "wb").write(veri)
    print("indirildi", len(veri), "bayt")
    gh("release", "upload", "kuyruk", hedef, "--clobber")
    os.replace(ap, os.path.join(KUYRUK, f"{kid}.json"))


def yeniden_planla():
    """Planlanmış (henüz yayınlanmamış) videoları aralıklı saatlere yeniden dağıtır."""
    simdi = dt.datetime.now(TR)
    yollar = sorted(glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json")))
    bekleyen = []
    for p in yollar:
        k = json.load(open(p, encoding="utf-8"))
        if k.get("video_id") and k.get("yayin") and dt.datetime.fromisoformat(k["yayin"]) > simdi + dt.timedelta(minutes=20):
            bekleyen.append((p, k))
    # önce hepsinin saatini boşalt, sonra sırayla (Dükkan TV önce) yeni saat ver
    for p, k in bekleyen:
        k["yayin"] = None
        json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    oncelik = {"dukkantv": 0, "kasakurgu": 1, "dramabite": 2}
    satirlar = []
    for p, k in sorted(bekleyen, key=lambda x: (oncelik.get(x[1]["kanal"], 9), x[1]["id"])):
        zaman = zaman_sec(k)
        token = erisim_anahtari(k["kanal"])
        kod, _, veri = istek("https://www.googleapis.com/youtube/v3/videos?part=status", method="PUT",
                             headers={"Authorization": f"Bearer {token}"},
                             json_govde={"id": k["video_id"], "status": {
                                 "privacyStatus": "private", "selfDeclaredMadeForKids": False,
                                 "publishAt": zaman.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")}})
        if kod != 200:
            satirlar.append(f"⚠️ {k['baslik'][:40]}: saat değiştirilemedi ({kod})")
            k["yayin"] = dt.datetime.fromisoformat(k.get("eski_yayin") or zaman.isoformat()).isoformat()
            continue
        k["yayin"] = zaman.isoformat()
        json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        satirlar.append(f"🕖 {zaman:%d.%m %H:%M} — {kanal_bilgi(k['kanal'])['ad']}: {k['baslik'][:45]}")
    if satirlar:
        telegram("📅 Yayın saatleri aralıklı olacak şekilde güncellendi:\n" + "\n".join(satirlar))
    print("\n".join(satirlar) or "Planlı video yok.")


def urunleri_ekle():
    """Yüklenmiş ama henüz yayına girmemiş (planlı) videoların açıklamasına ürün linklerini ekler."""
    simdi = dt.datetime.now(TR)
    for p in sorted(glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json"))):
        k = json.load(open(p, encoding="utf-8"))
        if not k.get("video_id") or k.get("urun_eklendi"):
            continue
        token = erisim_anahtari(k["kanal"])
        kod, _, veri = istek(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={k['video_id']}",
                             headers={"Authorization": f"Bearer {token}"})
        if kod != 200 or not veri.get("items"):
            print("Bulunamadı:", k["id"], kod)
            continue
        sn = veri["items"][0]["snippet"]
        yeni = urunlu_aciklama(sn.get("description", ""))
        if yeni != sn.get("description", ""):
            govde = {"id": k["video_id"], "snippet": {"title": sn["title"], "description": yeni,
                                                       "categoryId": sn.get("categoryId", "24"),
                                                       "tags": sn.get("tags", []),
                                                       "defaultLanguage": sn.get("defaultLanguage", "tr")}}
            kod, _, veri = istek("https://www.googleapis.com/youtube/v3/videos?part=snippet", method="PUT",
                                 headers={"Authorization": f"Bearer {token}"}, json_govde=govde)
            print("Güncellendi" if kod == 200 else f"Hata {kod} {str(veri)[:150]}", k["id"], sn["title"][:40])
        if kod == 200:
            k["urun_eklendi"] = True
            json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


URUN_ISARETLERI = ("shopier.com", "gumroad.com", "dukkantv.github.io/urunler", "Dijital ürünlerimiz")


def urunsuz_aciklama(aciklama):
    """Açıklamadan satış/ürün satırlarını (🛒 başlık + ▶ ürün linkleri) çıkarır."""
    satirlar = [s for s in aciklama.split("\n") if not any(i in s for i in URUN_ISARETLERI)]
    metin = "\n".join(satirlar)
    while "\n\n\n" in metin:
        metin = metin.replace("\n\n\n", "\n\n")
    return metin.strip()


def urunleri_kaldir():
    """Bütün kanallardaki BÜTÜN videoların (yayındaki + planlı) açıklamasından ürün linklerini siler."""
    from yt_ortak import kanallar, yt
    toplam = 0
    for kanal in kanallar():
        try:
            token = erisim_anahtari(kanal)
            yukleme = yt(token, "channels", part="contentDetails", mine="true")["items"][0][
                "contentDetails"]["relatedPlaylists"]["uploads"]
        except Exception as e:
            print(kanal, "atlandı:", str(e)[:150])
            continue
        idler, sayfa = [], None
        while True:
            ek = {"pageToken": sayfa} if sayfa else {}
            v = yt(token, "playlistItems", part="contentDetails", playlistId=yukleme, maxResults=50, **ek)
            idler += [i["contentDetails"]["videoId"] for i in v.get("items", [])]
            sayfa = v.get("nextPageToken")
            if not sayfa:
                break
        degisen = 0
        for i in range(0, len(idler), 50):
            for it in yt(token, "videos", part="snippet", id=",".join(idler[i:i + 50])).get("items", []):
                sn = it["snippet"]
                eski = sn.get("description", "")
                yeni = urunsuz_aciklama(eski)
                if yeni == eski.strip():
                    continue
                govde = {"id": it["id"], "snippet": {"title": sn["title"], "description": yeni,
                                                     "categoryId": sn.get("categoryId", "24"),
                                                     "tags": sn.get("tags", []),
                                                     "defaultLanguage": sn.get("defaultLanguage", "tr")}}
                kod, _, veri = istek("https://www.googleapis.com/youtube/v3/videos?part=snippet", method="PUT",
                                     headers={"Authorization": f"Bearer {token}"}, json_govde=govde)
                print(kanal, "temizlendi" if kod == 200 else f"HATA {kod} {str(veri)[:150]}", sn["title"][:50])
                degisen += kod == 200
        print(f"{kanal}: {len(idler)} video tarandı, {degisen} açıklama temizlendi")
        toplam += degisen
    telegram(f"🧹 Satış linkleri kaldırıldı: {toplam} video açıklaması temizlendi.")


def kapaklari_tamamla():
    """Yüklenmiş ama kapak resmi henüz konamamış uzun videolara kapağı yeniden dener (kanal doğrulandıktan sonra)."""
    for p in glob.glob(os.path.join(KUYRUK, "*.json")) + glob.glob(os.path.join(KUYRUK, "arsiv", "*.json")):
        k = json.load(open(p, encoding="utf-8"))
        if not k.get("kapak") or not k.get("video_id") or k.get("kapak_tamam"):
            continue
        try:
            token = erisim_anahtari(k["kanal"])
            gh("release", "download", "kuyruk", "-p", k["kapak"], "-D", "/tmp", "--clobber")
            kod, _, v = istek(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={k['video_id']}",
                              method="POST", ham=open(os.path.join("/tmp", k["kapak"]), "rb").read(),
                              headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"})
            print("Kapak", k["id"], kod, str(v)[:120])
            if kod == 200:
                k["kapak_tamam"] = True
                json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                telegram(f"🖼 Kapak resmi yüklendi: {k['baslik']}")
        except Exception as e:
            print("Kapak hatası:", str(e)[:150])


if __name__ == "__main__":
    if sys.argv[1] == "ekle":
        ekle(*sys.argv[2:10])
    elif sys.argv[1] == "kontrol":
        kontrol()
    elif sys.argv[1] == "yorumlar":
        yorumlar()
    elif sys.argv[1] == "geri_al":
        geri_al(sys.argv[2])
    elif sys.argv[1] == "planla":
        yeniden_planla()
    elif sys.argv[1] == "urunler":
        urunleri_ekle()
    elif sys.argv[1] == "urun_kaldir":
        urunleri_kaldir()
    elif sys.argv[1] == "kapaklar":
        kapaklari_tamamla()
