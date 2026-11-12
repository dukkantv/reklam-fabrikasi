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
KULLANICI_KANAL = {"dukkan.tv": "dukkantv", "dramabitetr": "dramabite", "kasakurgu.tr": "kasakurgu"}


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
        _sifrele(s["access_token"], os.path.join(KOK, "tokens", f"ig_{kanal}.enc"))
        json.dump({"kanal": kanal, "kullanici": ig["username"], "ig_id": ig["id"], "sayfa": s["name"],
                   "sayfa_id": s["id"]}, open(os.path.join(KOK, "tokens", f"ig_{kanal}.json"), "w",
                                            encoding="utf-8"), ensure_ascii=False, indent=1)
        bagli.append(f"@{ig['username']}")
    mesaj = "📸 Instagram bağlandı: " + (", ".join(bagli) or "hiçbiri")
    if eksik:
        mesaj += "\n⚠️ Instagram hesabı bağlı olmayan Facebook sayfaları: " + ", ".join(eksik)
    telegram(mesaj)
    print(mesaj)


def reels_yukle(kanal, video_yolu, aciklama):
    """Videoyu Reels olarak paylaşır. Döndürür: (medya_id, kalıcı bağlantı)."""
    h = ig_hesap(kanal)
    if not h:
        raise RuntimeError(f"{kanal} için Instagram bağlı değil")
    tok, ig = h["token"], h["ig_id"]
    kod, _, kap = istek(f"{API}/{ig}/media", veri={"media_type": "REELS", "upload_type": "resumable",
                                                   "caption": aciklama[:2200], "share_to_feed": "true",
                                                   "access_token": tok})
    if kod != 200 or "id" not in kap:
        raise RuntimeError(f"Instagram kapsayıcı açılamadı ({kod}): {kap}")
    boyut = os.path.getsize(video_yolu)
    with open(video_yolu, "rb") as f:
        kod, _, cev = istek(kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v25.0/{kap['id']}", method="POST",
                            ham=f.read(), zaman=900,
                            headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(boyut)})
    if kod != 200:
        raise RuntimeError(f"Instagram video yüklenemedi ({kod}): {str(cev)[:300]}")
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
    for sn in (59, 70, 78, 81):
        hedef = f"/tmp/t_{sn}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, "-t", str(sn), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", hedef], check=True)
        print(f"{sn} sn: {_sadece_yukle(tok, ig, hedef)}", flush=True)

if __name__ == "__main__":
    if sys.argv[1] == "kurulum":
        kurulum()
    elif sys.argv[1] == "teshis":
        teshis(sys.argv[2])
    elif sys.argv[1] == "teshis_video":
        teshis_video(sys.argv[2], sys.argv[3])
