# GTA 6 özel bölümünün 5 kanaldaki planlı videosunu ElevenLabs sesli sürümle değiştirir:
# - Instagram/Facebook/TikTok, yayın saatinde release'teki dosyayı kullandığı için dosya yenisiyle değiştirilir.
# - YouTube'da planlı videonun dosyası değiştirilemez: eski planlı video silinir, kayıt "onaylandi"ya döner,
#   YouTube Yayın işi yeni dosyayı aynı sabit saate (11:00) yeniden planlar.
import glob, json, os, shutil, subprocess, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
from yt_ortak import erisim_anahtari, istek  # noqa: E402

YENI = os.path.join(KOK, "gta6", "cikti_eleven.mp4")


def main():
    assert os.path.exists(YENI), "cikti_eleven.mp4 yok"
    kayitlar = []
    for p in sorted(glob.glob(os.path.join(KOK, "kuyruk", "20261119-0637*.json"))):
        k = json.load(open(p, encoding="utf-8"))
        if "GTA 6" in k["baslik"]:
            kayitlar.append((p, k))
    print("Değişecek:", [k["id"] for _, k in kayitlar])
    for p, k in kayitlar:
        hedef = os.path.join("/tmp", k["dosya"])
        shutil.copy(YENI, hedef)
        subprocess.run(["gh", "release", "upload", "kuyruk", hedef, "--clobber"], check=True)
        print(k["kanal"], "dosya yenilendi")
        if k.get("video_id"):
            tok = erisim_anahtari(k["kanal"])
            kod, _, cevap = istek(f"https://www.googleapis.com/youtube/v3/videos?id={k['video_id']}",
                                  method="DELETE", headers={"Authorization": f"Bearer {tok}"})
            print(k["kanal"], "eski YouTube videosu silindi" if kod == 204 else f"silme {kod}: {cevap}")
            if kod not in (204, 404):
                continue  # silinemediyse dokunma: eski sürüm yayına girer, iki kopya oluşmaz
            eski = k.pop("video_id")
            k.pop("yayin", None)
            k["durum"] = "onaylandi"
            k.setdefault("eski_video_idler", []).append(eski)
        json.dump(k, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
