"""TikTok (Content Posting API) yardımcıları: izin, anahtar yenileme ve taslak (inbox) yükleme.

Kullanım:
  python3 tt_ortak.py link <kanal>          # izin bağlantısını Telegram'a gönderir
  python3 tt_ortak.py kurulum <kanal> <kod> # tiktok.html sayfasındaki kodla bağlantıyı kurar

Notlar:
- Uygulama TikTok denetiminden geçmeden herkese açık doğrudan paylaşım yapılamaz. Bu yüzden video
  TikTok uygulamasına TASLAK olarak gönderilir (video.upload); Levent bildirimden açıp "Paylaş"a basar.
- Yenileme anahtarı her kullanımda değişir; tokens/tt_<kanal>.enc olarak şifreli saklanır
  (şifre: YT_CLIENT_SECRET — YouTube/Instagram ile aynı yöntem). Bu yüzden iş sonunda tokens/ kaydedilmelidir.
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse

from yt_ortak import CSEC, KOK, istek, telegram

API = "https://open.tiktokapis.com/v2"
YONLENDIRME = "https://dukkantv.github.io/tiktok.html"
KAPSAM = "user.info.basic,video.upload"
CK = os.environ.get("TT_CLIENT_KEY", "").strip()
CS = os.environ.get("TT_CLIENT_SECRET", "").strip()


def _sifrele(metin, yol):
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:YT_SIFRE", "-out", yol],
                   input=metin.encode(), check=True, env={**os.environ, "YT_SIFRE": CSEC})


def _coz(yol):
    return subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:YT_SIFRE", "-in", yol],
                          capture_output=True, check=True, env={**os.environ, "YT_SIFRE": CSEC}).stdout.decode().strip()


def _yol(kanal, uzanti):
    return os.path.join(KOK, "tokens", f"tt_{kanal}.{uzanti}")


def tt_hesap(kanal):
    """Bu kanal için TikTok bağlıysa bilgi sözlüğü, değilse None."""
    if not (CK and CS) or not os.path.exists(_yol(kanal, "json")):
        return None
    return json.load(open(_yol(kanal, "json"), encoding="utf-8"))


def _kaydet(kanal, cevap, bilgi=None):
    _sifrele(cevap["refresh_token"], _yol(kanal, "enc"))
    bilgi = bilgi or tt_hesap(kanal) or {}
    bilgi.update(kanal=kanal, open_id=cevap.get("open_id", bilgi.get("open_id")),
                 yenileme_bitis=int(time.time()) + int(cevap.get("refresh_expires_in", 0)))
    json.dump(bilgi, open(_yol(kanal, "json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def link(kanal):
    if not CK:
        sys.exit("TT_CLIENT_KEY gizli anahtarı yok")
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
        "client_key": CK, "scope": KAPSAM, "response_type": "code",
        "redirect_uri": YONLENDIRME, "state": kanal})
    import base64
    print("IZIN_LINKI_B64", base64.b64encode(url.encode()).decode())  # client_key herkese açık; günlükte maskelenmesin diye
    telegram(f"🎵 TikTok izni ({kanal}):\n1) Bu bağlantıyı aç, TikTok hesabınla gir ve izin ver.\n"
             f"2) Açılan sayfadaki kodu kopyala.\n3) GitHub → Actions → TikTok İzin → kanal: {kanal}, kod: yapıştır.\n\n{url}")
    print(url)


def kurulum(kanal, kod):
    kod = urllib.parse.unquote(kod.strip())
    c, _, cev = istek(f"{API}/oauth/token/", veri={
        "client_key": CK, "client_secret": CS, "code": kod,
        "grant_type": "authorization_code", "redirect_uri": YONLENDIRME},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if c != 200 or "refresh_token" not in (cev or {}):
        telegram(f"❌ TikTok bağlantısı kurulamadı ({kanal}): {str(cev)[:300]}")
        sys.exit(f"hata: {cev}")
    os.makedirs(os.path.join(KOK, "tokens"), exist_ok=True)
    _kaydet(kanal, cev, {})
    _, _, k = istek(f"{API}/user/info/?fields=display_name,username",
                    headers={"Authorization": f"Bearer {cev['access_token']}"})
    ad = ((k or {}).get("data") or {}).get("user", {})
    bilgi = tt_hesap(kanal)
    bilgi["kullanici"] = ad.get("username") or ad.get("display_name") or ""
    json.dump(bilgi, open(_yol(kanal, "json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    telegram(f"🎵 TikTok bağlandı: {kanal} (@{bilgi['kullanici']})")


def erisim_anahtari(kanal):
    yenileme = _coz(_yol(kanal, "enc"))
    c, _, cev = istek(f"{API}/oauth/token/", veri={
        "client_key": CK, "client_secret": CS, "grant_type": "refresh_token", "refresh_token": yenileme},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if c != 200 or "access_token" not in (cev or {}):
        raise RuntimeError(f"TikTok anahtarı yenilenemedi ({c}): {str(cev)[:300]}")
    _kaydet(kanal, cev)
    return cev["access_token"]


def taslak_yukle(kanal, video_yolu):
    """Videoyu TikTok uygulamasına taslak olarak gönderir. Döndürür: publish_id."""
    tok = erisim_anahtari(kanal)
    boyut = os.path.getsize(video_yolu)
    # Parça: 5–64 MB; 5 MB'tan küçük dosya tek parça. Son parça artanı da alır.
    parca = boyut if boyut <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    adet = max(1, boyut // parca)
    c, _, cev = istek(f"{API}/post/publish/inbox/video/init/", json_govde={"source_info": {
        "source": "FILE_UPLOAD", "video_size": boyut, "chunk_size": parca, "total_chunk_count": adet}},
        headers={"Authorization": f"Bearer {tok}"})
    veri = (cev or {}).get("data") or {}
    if c != 200 or "upload_url" not in veri:
        raise RuntimeError(f"TikTok yükleme başlatılamadı ({c}): {str(cev)[:300]}")
    with open(video_yolu, "rb") as f:
        for i in range(adet):
            bas = i * parca
            son = boyut - 1 if i == adet - 1 else bas + parca - 1
            f.seek(bas)
            c, _, r = istek(veri["upload_url"], method="PUT", ham=f.read(son - bas + 1), zaman=900,
                            headers={"Content-Type": "video/mp4", "Content-Length": str(son - bas + 1),
                                     "Content-Range": f"bytes {bas}-{son}/{boyut}"})
            if c not in (200, 201, 206):
                raise RuntimeError(f"TikTok parça yüklenemedi ({c}): {str(r)[:200]}")
    pid = veri["publish_id"]
    for _ in range(60):
        _, _, d = istek(f"{API}/post/publish/status/fetch/", json_govde={"publish_id": pid},
                        headers={"Authorization": f"Bearer {tok}"})
        durum = ((d or {}).get("data") or {}).get("status")
        if durum in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            return pid
        if durum == "FAILED":
            raise RuntimeError(f"TikTok videoyu işleyemedi: {d}")
        time.sleep(10)
    return pid


def durum(kanal, pid):
    tok = erisim_anahtari(kanal)
    _, _, d = istek(f"{API}/post/publish/status/fetch/", json_govde={"publish_id": pid},
                    headers={"Authorization": f"Bearer {tok}"})
    _, _, k = istek(f"{API}/user/info/?fields=open_id,display_name,username",
                    headers={"Authorization": f"Bearer {tok}"})
    print("DURUM:", d)
    print("HESAP:", k)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "durum":
        durum(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "link":
        link(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "kurulum":
        kurulum(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
