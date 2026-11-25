# Tanı: videoyu Instagram'a YAYINLAMADAN farklı yollarla dener (kapsayıcılar yayınlanmaz).
# 25 Kas 2026: doğrudan (rupload) yükleme ile video_url (Facebook kopyası / GitHub sürüm adresi) yollarını karşılaştırır.
import json, subprocess, sys, time
from ig_ortak import _kapsayici_yukle, ig_hesap, API
from yt_ortak import istek
import yt_kuyruk

kayit = json.load(open(sys.argv[1]))
kanal = kayit["kanal"]
h = ig_hesap(kanal)
tok, ig = h["token"], h["ig_id"]


def bekle(kid):
    d = {}
    for _ in range(30):
        _, _, d = istek(f"{API}/{kid}?fields=status_code,status&access_token={tok}")
        if (d or {}).get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
            break
        time.sleep(10)
    return d


def url_dene(ad, url):
    kod, _, kap = istek(f"{API}/{ig}/media", veri={"media_type": "REELS", "video_url": url, "caption": "test",
                                                   "access_token": tok})
    if kod != 200 or "id" not in (kap or {}):
        print(f"SONUC {ad}: kapsayıcı HATA {kod} {str(kap)[:300]}")
        return
    print(f"SONUC {ad}: {bekle(kap['id'])}")


print("Paylaşım sınırı:", istek(f"{API}/{ig}/content_publishing_limit?fields=config,quota_usage&access_token={tok}")[2])
if kayit.get("fb_id"):
    _, _, v = istek(f"{API}/{kayit['fb_id']}?fields=source&access_token={tok}")
    if (v or {}).get("source"):
        url_dene("fb_kaynak", v["source"])
    else:
        print("SONUC fb_kaynak: adres yok", v)
gh_url = f"https://github.com/dukkantv/reklam-fabrikasi/releases/download/kuyruk/{kayit['dosya']}"
url_dene("github_url", gh_url)
subprocess.run(["gh", "release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber"], check=True)
yol = "/tmp/" + kayit["dosya"]
igk = yt_kuyruk.ig_kodla(yol)
for ad, dosya in [("dogrudan_igkod", igk), ("dogrudan_orijinal", yol)]:
    try:
        kap = _kapsayici_yukle(kanal, dosya, "test")
        print(f"SONUC {ad}: {bekle(kap['id'])}")
    except Exception as e:
        print(f"SONUC {ad}: HATA {str(e)[:300]}")
    time.sleep(60)
