"""YouTube ve Telegram için ortak yardımcılar (rapor ve yayın işleri kullanır)."""
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

KOK = os.path.dirname(os.path.abspath(__file__))


def _temiz(anahtar, desen):
    deger = os.environ.get(anahtar, "")
    m = re.search(desen, deger)
    return m.group(0) if m else deger.strip()


CID = _temiz("YT_CLIENT_ID", r"[\w-]+\.apps\.googleusercontent\.com")
CSEC = _temiz("YT_CLIENT_SECRET", r"GOCSPX-[\w-]+")


def istek(url, veri=None, method=None, headers=None, json_govde=None, ham=None, zaman=120):
    h = dict(headers or {})
    govde = None
    if json_govde is not None:
        govde = json.dumps(json_govde).encode()
        h["Content-Type"] = "application/json; charset=UTF-8"
    elif veri is not None:
        govde = urllib.parse.urlencode(veri).encode()
    elif ham is not None:
        govde = ham
    req = urllib.request.Request(url, data=govde, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=zaman) as r:
            icerik = r.read()
            return r.status, dict(r.headers), (json.loads(icerik) if icerik.strip().startswith(b"{") else icerik)
    except urllib.error.HTTPError as e:
        icerik = e.read()
        try:
            return e.code, dict(e.headers), json.loads(icerik)
        except Exception:
            return e.code, dict(e.headers), icerik


def kanallar():
    """İzni alınmış kanallar: dukkantv, kasakurgu, dramabite..."""
    return sorted(f[:-4] for f in os.listdir(os.path.join(KOK, "tokens")) if f.endswith(".enc"))


def kanal_bilgi(kanal):
    return json.load(open(os.path.join(KOK, "tokens", f"{kanal}.json"), encoding="utf-8"))


MASAUSTU_CID = "1012697175361-vkv0tcgm4138dvgv1n2pd92h82rr44bg.apps.googleusercontent.com"
MASAUSTU_KAPSAM = ("https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.force-ssl "
                   "https://www.googleapis.com/auth/yt-analytics.readonly")


def erisim_anahtari(kanal):
    yol = os.path.join(KOK, "tokens", f"{kanal}.enc")
    yenileme = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:YT_SIFRE", "-in", yol],
        capture_output=True, check=True, env={**os.environ, "YT_SIFRE": CSEC}).stdout.decode().strip()
    cid, csec = CID, CSEC
    bilgi = os.path.join(KOK, "tokens", f"{kanal}.json")
    if os.path.exists(bilgi) and json.load(open(bilgi, encoding="utf-8")).get("istemci") == "masaustu":
        # Yorum izni (youtube.force-ssl) olan 'masaüstü' istemcisiyle alınmış izin
        cid = MASAUSTU_CID
        csec = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:YT_SIFRE",
                               "-in", os.path.join(KOK, "tokens", "istemci2.enc")],
                              capture_output=True, check=True, env={**os.environ, "YT_SIFRE": CSEC}).stdout.decode().strip()
    kod, _, t = istek("https://oauth2.googleapis.com/token", veri={
        "client_id": cid, "client_secret": csec, "refresh_token": yenileme, "grant_type": "refresh_token"})
    if kod != 200 or "access_token" not in t:
        raise RuntimeError(f"{kanal}: izin yenilenemedi ({kod}): {t}")
    return t["access_token"]


def yt(token, yol, **params):
    """YouTube Data API (yol 'videos' gibi) ya da tam URL ile GET isteği."""
    url = yol if yol.startswith("http") else f"https://www.googleapis.com/youtube/v3/{yol}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    kod, _, veri = istek(url, headers={"Authorization": f"Bearer {token}"})
    if kod != 200:
        raise RuntimeError(f"YouTube API hatası {kod}: {veri}")
    return veri


def analiz(token, baslangic, bitis, metrikler, **ek):
    return yt(token, "https://youtubeanalytics.googleapis.com/v2/reports",
              ids="channel==MINE", startDate=baslangic, endDate=bitis, metrics=metrikler, **ek)


def telegram(metin, **ek):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print(metin)
        return {}
    veri = {"chat_id": chat, "text": metin, "disable_web_page_preview": "true", **ek}
    return istek(f"https://api.telegram.org/bot{tok}/sendMessage", veri=veri)[2]
