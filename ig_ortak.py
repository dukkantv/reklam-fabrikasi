"""Instagram (Meta Graph API, Facebook Login) yardımcıları: kurulum ve Reels yükleme.

Sayfa (Page) erişim anahtarları süresizdir; tokens/ig_<kanal>.enc olarak şifreli saklanır
(şifre: YT_CLIENT_SECRET — YouTube izinleriyle aynı yöntem).
"""
import json
import os
import subprocess
import sys
import time

from yt_ortak import CSEC, KOK, istek, telegram

API = "https://graph.facebook.com/v25.0"
KULLANICI_KANAL = {"dukkan.tv": "dukkantv", "dramabitetr": "dramabite", "kasakurgu.tr": "kasakurgu", "81ilturnuvasi": "ilturnuva"}


def _sifrele(metin, yol):
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:YT_SIFRE", "-out", yol],
                   input=metin.encode(), check=True, env={**os.environ, "YT_SIFRE": CSEC})


def _coz(yol):
    return subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:YT_SIFRE", "-in", yol],
                          capture_output=True, check=True, env={**os.environ, "YT_SIFRE": CSEC}).stdout.decode().strip()


def ig_hesap(kanal):
    yol = os.path.join(KOK, "tokens", f"ig_{kanal}.json")
    if not os.path.exists(yol):
        return None
    bilgi = json.load(open(yol, encoding="utf-8"))
    bilgi["token"] = _coz(os.path.join(KOK, "tokens", f"ig_{kanal}.enc"))
    return bilgi


def kurulum():
    """IG_USER_TOKEN (60 günlük kullanıcı anahtarı) ile sayfa anahtarlarını alır ve şifreli kaydeder."""
    tok = "".join(os.environ.get("IG_USER_TOKEN", "").split())
    if not tok:
        sys.exit("IG_USER_TOKEN gizli anahtarı yok")
    # Graph API Explorer'ın verdiği anahtar 1-2 saatliktir; ondan alınan sayfa anahtarları da çabuk biter.
    # Uygulama kimliği + gizli anahtarıyla önce 60 günlük anahtara çevrilir; ondan alınan sayfa anahtarları SÜRESİZDİR.
    app_id = os.environ.get("IG_APP_ID", "").strip()
    app_sec = os.environ.get("IG_APP_SECRET", "").strip()
    if not (app_id and app_sec):
        telegram("❌ Instagram kurulumu: IG_APP_ID ve IG_APP_SECRET gizli anahtarları eksik (anahtar birkaç saatte biterdi).")
        sys.exit("IG_APP_ID / IG_APP_SECRET yok")
    kod, _, uzun = istek(f"{API}/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}"
                         f"&client_secret={app_sec}&fb_exchange_token={tok}")
    if kod != 200 or "access_token" not in (uzun or {}):
        telegram(f"❌ Instagram: uzun süreli anahtar alınamadı: {str(uzun)[:300]}")
        sys.exit(f"hata: {uzun}")
    tok = uzun["access_token"]
    # Facebook sayfasına Reels paylaşma izni var mı? (pages_manage_posts) — sayfa anahtarları bu izni miras alır
    _, _, dbg = istek(f"{API}/debug_token?input_token={tok}&access_token={app_id}|{app_sec}")
    izinler = set(((dbg or {}).get("data") or {}).get("scopes", []))
    fb_izin = "pages_manage_posts" in izinler
    print("Anahtar izinleri:", sorted(izinler))
    kod, _, veri = istek(f"{API}/me/accounts?fields=name,access_token,instagram_business_account%7Busername%7D"
                         f"&limit=50&access_token={tok}")
    if kod != 200:
        telegram(f"❌ Instagram kurulumu başarısız: {str(veri)[:300]}")
        sys.exit(f"hata: {veri}")
    bagli, eksik = [], []
    for s in veri.get("data", []):
        ig = s.get("instagram_business_account")
        if not ig:
            eksik.append(s["name"])
            continue
        kanal = KULLANICI_KANAL.get(ig["username"], ig["username"].replace(".", "_"))
        if "gizli" in ig["username"].lower() and "tarih" in ig["username"].lower():
            kanal = "gizlitarih"   # Gizli Tarih hangi kullanıcı adıyla açılırsa açılsın YouTube kanalıyla eşleşsin
        _sifrele(s["access_token"], os.path.join(KOK, "tokens", f"ig_{kanal}.enc"))
        json.dump({"kanal": kanal, "kullanici": ig["username"], "ig_id": ig["id"], "sayfa": s["name"],
                   "sayfa_id": s["id"], "fb_izin": fb_izin}, open(os.path.join(KOK, "tokens", f"ig_{kanal}.json"), "w",
                                            encoding="utf-8"), ensure_ascii=False, indent=1)
        bagli.append(f"@{ig['username']}")
    mesaj = "📸 Instagram bağlandı: " + (", ".join(bagli) or "hiçbiri")
    mesaj += ("\n📘 Facebook sayfalarına Reels paylaşımı: AÇIK" if fb_izin else
              "\n📘 Facebook sayfalarına Reels paylaşımı kapalı (anahtarda pages_manage_posts izni yok)")
    if eksik:
        mesaj += "\n⚠️ Instagram hesabı bağlı olmayan Facebook sayfaları: " + ", ".join(eksik)
    telegram(mesaj)
    print(mesaj)


# Deneme Reels (Trial Reels): video önce yalnızca takip etmeyenlere gösterilir; iyi giderse Instagram
# otomatik olarak herkese açar (SS_PERFORMANCE). Hesap uygun değilse normal Reels'e düşülür.
SON_DENEME = False


def _reels_alanlari(veri, deneme):
    """Kapsayıcı isteğine deneme ayarını ekler (deneme Reels'te share_to_feed gönderilmez)."""
    if deneme:
        veri = dict(veri)
        veri.pop("share_to_feed", None)
        veri["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    return veri


def _kapsayici_ac(ig, veri, deneme):
    """Kapsayıcıyı açar; deneme Reels reddedilirse normal Reels ile tekrar dener. Döndürür: (kod, kap)."""
    global SON_DENEME
    kod, _, kap = istek(f"{API}/{ig}/media", veri=_reels_alanlari(veri, deneme))
    if deneme and (kod != 200 or "id" not in kap):
        print(f"Deneme Reels kabul edilmedi ({kod}): {str(kap)[:200]} → normal Reels", flush=True)
        kod, _, kap = istek(f"{API}/{ig}/media", veri=veri)
        deneme = False
    SON_DENEME = bool(deneme and kod == 200 and "id" in kap)
    return kod, kap


def _kapsayici_yukle(kanal, video_yolu, aciklama, deneme=False):
    """Kapsayıcı açar ve videoyu yükler (yayınlamaz)."""
    h = ig_hesap(kanal)
    if not h:
        raise RuntimeError(f"{kanal} için Instagram bağlı değil")
    tok, ig = h["token"], h["ig_id"]
    kod, kap = _kapsayici_ac(ig, {"media_type": "REELS", "upload_type": "resumable",
                                  "caption": aciklama[:2200], "share_to_feed": "true",
                                  "access_token": tok}, deneme)
    if kod != 200 or "id" not in kap:
        raise RuntimeError(f"Instagram kapsayıcı açılamadı ({kod}): {kap}")
    boyut = os.path.getsize(video_yolu)
    with open(video_yolu, "rb") as f:
        kod, _, cev = istek(kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v25.0/{kap['id']}", method="POST",
                            ham=f.read(), zaman=900,
                            headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(boyut)})
    if kod != 200:
        raise RuntimeError(f"Instagram video yüklenemedi ({kod}): {str(cev)[:300]}")
    return kap


def reels_yukle(kanal, video_yolu, aciklama, deneme=False):
    """Videoyu Reels olarak paylaşır. Döndürür: (medya_id, kalıcı bağlantı).
    Instagram aynı dosyayı bazen rastgele 'ProcessingFailedError' ile reddediyor; yeni kapsayıcıyla 5 kez dener."""
    h = ig_hesap(kanal)
    if not h:
        raise RuntimeError(f"{kanal} için Instagram bağlı değil")
    tok, ig = h["token"], h["ig_id"]
    for deneme in range(5):
        try:
            kap = _kapsayici_yukle(kanal, video_yolu, aciklama, deneme)
            break
        except RuntimeError as e:
            if "ProcessingFailedError" not in str(e) or deneme == 4:
                raise
            print(f"Instagram yükleme {deneme + 1}. deneme reddedildi, tekrar deneniyor", flush=True)
            time.sleep(20)
    for _ in range(60):  # işleme bitene kadar bekle (en çok ~10 dk)
        _, _, d = istek(f"{API}/{kap['id']}?fields=status_code,status&access_token={tok}")
        durum = (d or {}).get("status_code")
        if durum == "FINISHED":
            break
        if durum in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram videoyu işleyemedi: {d}")
        time.sleep(10)
    kod, _, yay = istek(f"{API}/{ig}/media_publish", veri={"creation_id": kap["id"], "access_token": tok})
    if kod != 200 or "id" not in yay:
        raise RuntimeError(f"Instagram paylaşım başarısız ({kod}): {yay}")
    _, _, p = istek(f"{API}/{yay['id']}?fields=permalink&access_token={tok}")
    return yay["id"], (p or {}).get("permalink", "")


def reels_yukle_fb_kaynak(kanal, fb_video_id, aciklama, deneme=False):
    """Yedek yol: Facebook'a yüklenmiş aynı videonun CDN adresini Instagram'a video_url olarak verir
    (doğrudan yükleme 'ProcessingFailedError' ile reddedildiğinde)."""
    h = ig_hesap(kanal)
    tok, ig = h["token"], h["ig_id"]
    _, _, v = istek(f"{API}/{fb_video_id}?fields=source&access_token={tok}")
    url = (v or {}).get("source")
    if not url:
        raise RuntimeError(f"Facebook video adresi alınamadı: {v}")
    kod, kap = _kapsayici_ac(ig, {"media_type": "REELS", "video_url": url, "caption": aciklama[:2200],
                                  "share_to_feed": "true", "access_token": tok}, deneme)
    if kod != 200 or "id" not in kap:
        raise RuntimeError(f"Instagram kapsayıcı açılamadı ({kod}): {kap}")
    for _ in range(60):
        _, _, d = istek(f"{API}/{kap['id']}?fields=status_code,status&access_token={tok}")
        durum = (d or {}).get("status_code")
        if durum == "FINISHED":
            break
        if durum in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram videoyu işleyemedi: {d}")
        time.sleep(10)
    kod, _, yay = istek(f"{API}/{ig}/media_publish", veri={"creation_id": kap["id"], "access_token": tok})
    if kod != 200 or "id" not in yay:
        raise RuntimeError(f"Instagram paylaşım başarısız ({kod}): {yay}")
    _, _, p = istek(f"{API}/{yay['id']}?fields=permalink&access_token={tok}")
    return yay["id"], (p or {}).get("permalink", "")


def fb_bekliyor_mu(kanal):
    h = ig_hesap(kanal)
    return bool(h and h.get("fb_izin") and h.get("sayfa_id"))


def fb_reels_yukle(kanal, video_yolu, aciklama):
    """Videoyu kanalın Facebook SAYFASINA Reels olarak paylaşır. Döndürür: video_id."""
    h = ig_hesap(kanal)
    tok, sayfa = h["token"], h["sayfa_id"]
    kod, _, bas = istek(f"{API}/{sayfa}/video_reels", veri={"upload_phase": "start", "access_token": tok})
    if kod != 200 or "video_id" not in (bas or {}):
        raise RuntimeError(f"Facebook Reels başlatılamadı ({kod}): {str(bas)[:300]}")
    vid = bas["video_id"]
    adres = bas.get("upload_url") or f"https://rupload.facebook.com/video-upload/v25.0/{vid}"
    with open(video_yolu, "rb") as f:
        veri = f.read()
    kod, _, yuk = istek(adres, method="POST", ham=veri, zaman=900,
                        headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(veri))})
    if kod != 200:
        raise RuntimeError(f"Facebook video yüklenemedi ({kod}): {str(yuk)[:300]}")
    kod, _, bit = istek(f"{API}/{sayfa}/video_reels", veri={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": aciklama[:2200], "access_token": tok})
    if kod != 200 or not (bit or {}).get("success"):
        raise RuntimeError(f"Facebook Reels yayınlanamadı ({kod}): {str(bit)[:300]}")
    return vid


def teshis(kanal):
    """Instagram hesabının paylaşım durumunu ve küçük bir deneme yüklemesini (yayınlamadan) kontrol eder."""
    h = ig_hesap(kanal)
    tok, ig = h["token"], h["ig_id"]
    print("Hesap:", istek(f"{API}/{ig}?fields=username,name,media_count,followers_count&access_token={tok}")[2])
    print("Paylaşım sınırı:", istek(f"{API}/{ig}/content_publishing_limit?fields=config,quota_usage&access_token={tok}")[2])
    print("Anahtar:", istek(f"{API}/debug_token?input_token={tok}&access_token={tok}")[2])
    deneme = "/tmp/ig_deneme.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=5",
                    "-f", "lavfi", "-i", "sine=f=440:d=5", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart", deneme], check=True)
    kod, _, kap = istek(f"{API}/{ig}/media", veri={"media_type": "REELS", "upload_type": "resumable",
                                                   "caption": "deneme", "access_token": tok})
    print("Kapsayıcı:", kod, kap)
    if "id" not in (kap or {}):
        return
    with open(deneme, "rb") as f:
        veri = f.read()
    kod, _, cev = istek(kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v25.0/{kap['id']}", method="POST", ham=veri,
                        headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(veri))})
    print("Deneme yükleme (yayınlanmaz):", kod, cev)
    time.sleep(20)
    print("Durum:", istek(f"{API}/{kap['id']}?fields=status_code,status&access_token={tok}")[2])


def _sadece_yukle(tok, ig, yol, aciklama="deneme", akis=None):
    v = {"media_type": "REELS", "upload_type": "resumable", "caption": aciklama, "access_token": tok}
    if akis:
        v["share_to_feed"] = akis
    kod, _, kap = istek(f"{API}/{ig}/media", veri=v)
    with open(yol, "rb") as f:
        veri = f.read()
    kod, _, cev = istek(kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v25.0/{kap['id']}", method="POST", ham=veri,
                        zaman=900, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(veri))})
    if kod != 200:
        return f"YÜKLEME {kod} {str(cev)[:150]}"
    for _ in range(18):
        time.sleep(10)
        d = istek(f"{API}/{kap['id']}?fields=status_code,status&access_token={tok}")[2]
        if d.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
            return f"{d.get('status_code')} {d.get('status')}"
    return "zaman aşımı"


def teshis_video(kanal, yol):
    """Gerçek videonun farklı kodlamalarını yayınlamadan yükleyip hangisinin kabul edildiğini gösterir."""
    h = ig_hesap(kanal)
    tok, ig = h["token"], h["ig_id"]
    print(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,profile,level,pix_fmt,width,height,"
                          "r_frame_rate,sample_rate,channels,duration,start_time:format=duration",
                          "-of", "compact", yol], capture_output=True, text=True).stdout)
    import glob as _g
    from yt_kuyruk import ig_aciklama
    kid = os.path.basename(yol)[:-4]
    yollar = _g.glob(os.path.join(KOK, "kuyruk", f"{kid}.json")) + _g.glob(os.path.join(KOK, "kuyruk", "arsiv", f"{kid}.json"))
    gercek = ig_aciklama(json.load(open(yollar[0], encoding="utf-8"))) if yollar else "deneme"
    print("Gerçek açıklama:", repr(gercek))
    for sn in [int(x) for x in os.environ.get("TESHIS_SN", "10 25 40 56").split()]:
        hedef = f"/tmp/t_{sn}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, "-t", str(sn), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", hedef], check=True)
        print(f"{sn} sn ({os.path.getsize(hedef) / 1048576:.1f} MB): {_sadece_yukle(tok, ig, hedef)}", flush=True)
        cbr = f"/tmp/c_{sn}.mp4"  # sabit yüksek bit hızı (durağan slaytlarda bile ~3,5 Mbps)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, "-t", str(sn), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-b:v", "3500k", "-minrate", "3500k", "-maxrate", "3500k",
                        "-bufsize", "7000k", "-x264-params", "nal-hrd=cbr:force-cfr=1", "-r", "30",
                        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", cbr], check=True)
        print(f"{sn} sn CBR ({os.path.getsize(cbr) / 1048576:.1f} MB): {_sadece_yukle(tok, ig, cbr)}", flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "kurulum":
        kurulum()
    elif sys.argv[1] == "teshis":
        teshis(sys.argv[2])
    elif sys.argv[1] == "teshis_video":
        teshis_video(sys.argv[2], sys.argv[3])
