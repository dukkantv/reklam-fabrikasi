"""YouTube izni — 'masaüstü' istemcisiyle (yorum yazma izni dahil).

Cihaz-kodu yöntemi (yt_izin.py) Google'ın kuralı gereği yorum izni (youtube.force-ssl) veremiyor.
Bu betik iki adımlı çalışır:
  python3 yt_izin2.py link            → izin sayfasının adresini yazar (tarayıcıda açılır, hesap seçilir)
  KOD=... python3 yt_izin2.py kod KANAL → tarayıcının yönlendirildiği 127.0.0.1 adresindeki kodu izne çevirir
İzin şifrelenip tokens/<kanal>.enc'e yazılır; tokens/<kanal>.json'a "istemci": "masaustu" eklenir.
"""
import json
import os
import subprocess
import sys
import urllib.parse

from yt_ortak import CSEC, KOK, MASAUSTU_CID, MASAUSTU_KAPSAM, istek, telegram

YONLENDIR = "http://127.0.0.1:8765"

if sys.argv[1] == "link":
    print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": MASAUSTU_CID, "redirect_uri": YONLENDIR, "response_type": "code",
        "scope": MASAUSTU_KAPSAM, "access_type": "offline", "prompt": "consent select_account"}))
    sys.exit()

kanal = sys.argv[2]
gizli = os.environ["YT2_CLIENT_SECRET"].strip()
kod = os.environ["KOD"].strip()
if "code=" in kod:
    kod = urllib.parse.parse_qs(urllib.parse.urlparse(kod).query)["code"][0]
d, _, t = istek("https://oauth2.googleapis.com/token", veri={
    "client_id": MASAUSTU_CID, "client_secret": gizli, "code": kod,
    "redirect_uri": YONLENDIR, "grant_type": "authorization_code"})
if d != 200 or "refresh_token" not in t:
    telegram(f"❌ {kanal}: YouTube yorum izni alınamadı ({d}): {str(t)[:200]}")
    sys.exit(f"token hatası {d}: {t}")
d, _, v = istek("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                headers={"Authorization": f"Bearer {t['access_token']}"})
kanallar = (v or {}).get("items", [])
bilgi_yol = os.path.join(KOK, "tokens", f"{kanal}.json")
bilgi = json.load(open(bilgi_yol, encoding="utf-8"))
if not kanallar or kanallar[0]["id"] != bilgi["kanal_id"]:
    ad = kanallar[0]["snippet"]["title"] if kanallar else "kanal yok"
    telegram(f"⚠️ {bilgi['ad']} için yanlış hesap seçildi ({ad}). İzin kaydedilmedi, tekrar deneyelim.")
    sys.exit(f"yanlış kanal: {ad}")
sifre = {**os.environ, "YT_SIFRE": CSEC}
subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:YT_SIFRE",
                "-out", os.path.join(KOK, "tokens", f"{kanal}.enc")], input=t["refresh_token"].encode(), env=sifre, check=True)
subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:YT_SIFRE",
                "-out", os.path.join(KOK, "tokens", "istemci2.enc")], input=gizli.encode(), env=sifre, check=True)
bilgi["istemci"] = "masaustu"
json.dump(bilgi, open(bilgi_yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
telegram(f"✅ {bilgi['ad']}: yorum izni de alındı.")
print("tamam", bilgi["ad"])
