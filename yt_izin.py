"""YouTube kanalı için kalıcı izin alır (bir kere çalıştırılır).

Akış: Telegram'a bir kod gelir → telefonda google.com/device açılır → kod girilir
→ ilgili kanalın Google hesabı seçilir → "İzin ver". İzin anahtarı şifrelenip
tokens/<kanal>.enc olarak depoya kaydedilir (şifre: YT_CLIENT_SECRET).
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

KANAL = os.environ["KANAL"]
import re
# Kopyalarken boşluk/etiket gelmiş olabilir: sadece asıl değeri al
CID = (re.search(r"[\w-]+\.apps\.googleusercontent\.com", os.environ["YT_CLIENT_ID"]) or re.search(r"\S+", os.environ["YT_CLIENT_ID"])).group(0)
CSEC = (re.search(r"GOCSPX-[\w-]+", os.environ["YT_CLIENT_SECRET"]) or re.search(r"\S+", os.environ["YT_CLIENT_SECRET"])).group(0)
os.environ["YT_CLIENT_SECRET"] = CSEC
print(f"Kontrol: client id sonu {CID[-27:]}, secret uzunluğu {len(CSEC)}, GOCSPX ile başlıyor: {CSEC.startswith('GOCSPX-')}")
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
SCOPE = "https://www.googleapis.com/auth/youtube"
HESAP = {"gizlitarih": "Gizli Tarih kanalını açtığın hesap (kanal listesinden Gizli Tarih'i seç)",
         "dukkantv": "dukkan.tvstudio@gmail.com",
         "kasakurgu": "kasakurgu.tr@gmail.com",
         "dramabite": "dramabitetr@gmail.com"}


def post(url, veri):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(veri).encode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def telegram(metin):
    post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
         {"chat_id": TG_CHAT, "text": metin, "disable_web_page_preview": "true"})


kod = post("https://oauth2.googleapis.com/device/code", {"client_id": CID, "scope": SCOPE})
if "user_code" not in kod:
    telegram(f"❌ YouTube izin kodu alınamadı: {kod}")
    sys.exit(f"device/code hatası: {kod}")

print("ONAY KODU:", kod["user_code"], flush=True)
telegram(
    f"📺 YouTube izni — {KANAL}\n\n"
    f"1) Telefonda şu adresi aç: {kod['verification_url']}\n"
    f"2) Bu kodu yaz: {kod['user_code']}\n"
    f"3) Hesap olarak {HESAP.get(KANAL, '')} seç\n"
    f"4) Uyarı çıkarsa 'Gelişmiş → Dukkan TV Yayin'e git' de, sonra 'İzin ver'.\n\n"
    f"Kodun süresi {int(kod['expires_in']) // 60} dakika.")

bitis = time.time() + int(kod["expires_in"])
aralik = int(kod.get("interval", 5))
token = None
while time.time() < bitis:
    time.sleep(aralik)
    t = post("https://oauth2.googleapis.com/token", {
        "client_id": CID, "client_secret": CSEC, "device_code": kod["device_code"],
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
    if "refresh_token" in t:
        token = t
        break
    if t.get("error") == "slow_down":
        aralik += 5
    elif t.get("error") not in ("authorization_pending",):
        telegram(f"❌ İzin verilmedi ya da hata oldu: {t.get('error')}")
        sys.exit(f"token hatası: {t}")

if not token:
    telegram("⌛ Kodun süresi doldu. 'YouTube İzin' işini tekrar çalıştır.")
    sys.exit("süre doldu")

istek = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
                               headers={"Authorization": f"Bearer {token['access_token']}"})
with urllib.request.urlopen(istek, timeout=60) as r:
    kanallar = json.load(r).get("items", [])
if not kanallar:
    telegram("⚠️ İzin verildi ama bu Google hesabında YouTube kanalı bulunamadı. Doğru hesabı seçtiğinden emin ol.")
    sys.exit("kanal yok")

os.makedirs("tokens", exist_ok=True)
subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:YT_CLIENT_SECRET",
                "-out", f"tokens/{KANAL}.enc"], input=token["refresh_token"].encode(), check=True)
k = kanallar[0]
json.dump({"kanal": KANAL, "kanal_id": k["id"], "ad": k["snippet"]["title"]},
          open(f"tokens/{KANAL}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
telegram(f"✅ {k['snippet']['title']} kanalı bağlandı! "
         f"({k['statistics'].get('subscriberCount', '?')} abone). Artık bilgisayar kapalıyken de çalışabilirim.")
print("Bağlandı:", k["snippet"]["title"])
