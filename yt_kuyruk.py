"""YouTube yayın kuyruğu: ekle → Telegram'da onay → otomatik yükleme (19:00'da yayında).

Kullanım:
  python3 yt_kuyruk.py ekle <kanal> <video.mp4> "<başlık>" "<açıklama>" "<etiket1,etiket2>"
  python3 yt_kuyruk.py kontrol      # onayları okur, onaylananları YouTube'a yükler

Kurallar:
- Levent onay vermeden HİÇBİR video yayınlanmaz. İptal ya da 3 gün cevapsız kalırsa silinir.
- Onaylanan video YouTube'a "planlı" yüklenir: saat 18:30'dan önce onaylanırsa aynı gün 19:00,
  sonra onaylanırsa ertesi gün 19:00 (Türkiye saati) yayına girer.
- Telegram güncellemeleri ONAYLANMAZ (offset kullanılmaz), böylece aynı botu kullanan
  'Bölüm Üret' işinin klip kuyruğu bozulmaz.
"""
import datetime as dt
import glob
import json
import os
import subprocess
import sys

from yt_ortak import KOK, erisim_anahtari, istek, kanal_bilgi, telegram

KUYRUK = os.path.join(KOK, "kuyruk")
TR = dt.timezone(dt.timedelta(hours=3))
TG = f"https://api.telegram.org/bot{os.environ.get('TELEGRAM_BOT_TOKEN', '')}"


def gh(*arg):
    return subprocess.run(["gh", *arg], check=True, capture_output=True, text=True).stdout


def kaydet(kayit):
    json.dump(kayit, open(os.path.join(KUYRUK, f"{kayit['id']}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def ekle(kanal, video, baslik, aciklama="", etiketler=""):
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
    ad = kanal_bilgi(kanal)["ad"]
    klavye = {"inline_keyboard": [[{"text": "✅ Onayla", "callback_data": f"yt:onay:{kid}"},
                                   {"text": "❌ Yayınlama", "callback_data": f"yt:iptal:{kid}"}]]}
    cevap = telegram(f"📺 YouTube'a yüklensin mi? → {ad}\n\n🎬 {kayit['baslik']}\n\n"
                     f"Onaylarsan 19:00'da yayına girer (18:30'dan sonra onaylarsan yarın 19:00).\n"
                     f"Video yukarıda Telegram'a gelen son video.",
                     reply_markup=json.dumps(klavye))
    kayit["mesaj_id"] = (cevap.get("result") or {}).get("message_id")
    kaydet(kayit)
    print("Kuyruğa eklendi:", kid)


def yayin_zamani():
    simdi = dt.datetime.now(TR)
    hedef = simdi.replace(hour=19, minute=0, second=0, microsecond=0)
    if simdi > hedef - dt.timedelta(minutes=30):
        hedef += dt.timedelta(days=1)
    return hedef


def youtube_yukle(kayit):
    token = erisim_anahtari(kayit["kanal"])
    yerel = os.path.join("/tmp", kayit["dosya"])
    gh("release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber")
    boyut = os.path.getsize(yerel)
    zaman = yayin_zamani()
    ust = {"snippet": {"title": kayit["baslik"], "description": kayit["aciklama"], "tags": kayit["etiketler"],
                       "categoryId": "24", "defaultLanguage": "tr", "defaultAudioLanguage": "tr"},
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
    return veri["id"], zaman


def mesaj_guncelle(kayit, metin):
    if kayit.get("mesaj_id"):
        istek(f"{TG}/editMessageText", veri={"chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
                                              "message_id": kayit["mesaj_id"], "text": metin})


def kontrol():
    kayitlar = {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8"))
                for p in glob.glob(os.path.join(KUYRUK, "*.json"))}
    if not kayitlar:
        print("Kuyruk boş.")
        return
    _, _, guncel = istek(f"{TG}/getUpdates?timeout=0")
    for u in (guncel or {}).get("result", []):
        cq = u.get("callback_query") or {}
        parca = (cq.get("data") or "").split(":")
        if len(parca) != 3 or parca[0] != "yt" or parca[2] not in kayitlar:
            continue
        kayit = kayitlar[parca[2]]
        istek(f"{TG}/answerCallbackQuery", veri={"callback_query_id": cq["id"], "text": "Alındı 👍"})
        if kayit["durum"] == "bekliyor":
            kayit["durum"] = "onaylandi" if parca[1] == "onay" else "iptal"
            kaydet(kayit)

    simdi = dt.datetime.now(TR)
    for kayit in kayitlar.values():
        ad = kanal_bilgi(kayit["kanal"])["ad"]
        if kayit["durum"] == "onaylandi":
            try:
                vid, zaman = youtube_yukle(kayit)
                kayit.update(durum="yuklendi", video_id=vid, yayin=zaman.isoformat())
                kaydet(kayit)
                metin = (f"✅ {ad}: \"{kayit['baslik']}\" yüklendi.\n"
                         f"🕖 {zaman:%d.%m %H:%M}'da yayına girecek.\nhttps://youtube.com/shorts/{vid}")
                mesaj_guncelle(kayit, metin)
                telegram(metin)
            except Exception as e:
                kayit["hata"] = str(e)[:300]
                kaydet(kayit)
                telegram(f"⚠️ {ad}: \"{kayit['baslik']}\" yüklenemedi: {str(e)[:200]}\nBir sonraki kontrolde tekrar denenecek.")
        elif kayit["durum"] == "iptal" or (kayit["durum"] == "bekliyor" and
                                            simdi - dt.datetime.fromisoformat(kayit["eklendi"]) > dt.timedelta(days=3)):
            mesaj_guncelle(kayit, f"🗑️ {ad}: \"{kayit['baslik']}\" yayınlanmadı.")
            try:
                gh("release", "delete-asset", "kuyruk", kayit["dosya"], "-y")
            except subprocess.CalledProcessError:
                pass
            os.remove(os.path.join(KUYRUK, f"{kayit['id']}.json"))
        elif kayit["durum"] == "yuklendi":
            try:
                gh("release", "delete-asset", "kuyruk", kayit["dosya"], "-y")
            except subprocess.CalledProcessError:
                pass
            os.makedirs(os.path.join(KUYRUK, "arsiv"), exist_ok=True)
            os.replace(os.path.join(KUYRUK, f"{kayit['id']}.json"),
                       os.path.join(KUYRUK, "arsiv", f"{kayit['id']}.json"))


if __name__ == "__main__":
    if sys.argv[1] == "ekle":
        ekle(*sys.argv[2:7])
    elif sys.argv[1] == "kontrol":
        kontrol()
