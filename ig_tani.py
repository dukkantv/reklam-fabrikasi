# Tanı: Drama Bite videosunu Instagram'a YAYINLAMADAN yükler (kapsayıcı + yükleme + işleme durumu).
# Hangi değişkenin (açıklama, ses, kodlama) reddedilmeye yol açtığını bulmak için. Kapsayıcılar yayınlanmaz.
import json, subprocess, sys, time
from ig_ortak import _kapsayici_yukle, ig_hesap, API
from yt_ortak import istek
import yt_kuyruk

kayit = json.load(open(sys.argv[1]))
kanal = kayit["kanal"]
subprocess.run(["gh", "release", "download", "kuyruk", "-p", kayit["dosya"], "-D", "/tmp", "--clobber"], check=True)
yol = "/tmp/" + kayit["dosya"]
ff = lambda *a: subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, *a], check=True)
ff("-c:v", "copy", "-an", "/tmp/sessiz.mp4")
ff("-c:v", "libx264", "-r", "30", "-g", "60", "-b:v", "3500k", "-c:a", "aac", "-ar", "48000", "-b:a", "128k", "-movflags", "+faststart", "/tmp/kod.mp4")
h = ig_hesap(kanal)
tok = h["token"]
print("Paylaşım sınırı:", istek(f"{API}/{h['ig_id']}/content_publishing_limit?fields=config,quota_usage&access_token={tok}")[2])
igk = yt_kuyruk.ig_kodla(yol)
gercek = yt_kuyruk.ig_aciklama(kayit)
denemeler = [("igkod_gercek_aciklama", igk, gercek), ("igkod_test", igk, "test"),
             ("orijinal_test", yol, "test"), ("sessiz_test", "/tmp/sessiz.mp4", "test"),
             ("yeniden_kod_test", "/tmp/kod.mp4", "test")]
for ad, dosya, acik in denemeler:
    try:
        kap = _kapsayici_yukle(kanal, dosya, acik)
        for _ in range(30):
            _, _, d = istek(f"{API}/{kap['id']}?fields=status_code,status&access_token={tok}")
            if d.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"):
                break
            time.sleep(10)
        print(f"SONUC {ad}: yükleme tamam, işleme: {d}")
    except Exception as e:
        print(f"SONUC {ad}: HATA {str(e)[:400]}")
print("açıklama:", repr(yt_kuyruk.ig_aciklama(kayit))[:600])
