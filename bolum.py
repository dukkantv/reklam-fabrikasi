# Kullanım: python bolum.py eserim
# Levent'in Maceraları gibi çizgi film bölümlerini birleştirir:
#  1) Önce reklamlar/<klasor>/klipler/ içindeki 01.mp4, 02.mp4 ... dosyalarını, ardından
#     Telegram botuna gönderilen klipleri (gönderiliş sırasıyla) kullanır
#  2) bolum.json'daki akışa göre klipleri, yazı kartlarını ve esnafın bilgi kartını dizer
#  3) Hepsini dikey 1080x1920 tek videoya çevirir: cikti/<dosya_adi>.mp4
import glob, json, os, subprocess, sys, urllib.request

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti")
TOKEN = os.environ.get("TOKEN", "")
CHAT = os.environ.get("CHAT", "")
VIDEO_AYAR = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30"]
SES_AYAR = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def calistir(*komut):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *komut], check=True)


def tg(metod, **params):
    url = f"https://api.telegram.org/bot{TOKEN}/{metod}?" + "&".join(f"{k}={v}" for k, v in params.items())
    return json.load(urllib.request.urlopen(url, timeout=60))


def telegramdan_klipler(hedef_klasor):
    """Bota gönderilmiş videoları sırayla indirir. Döndürür: (dosyalar, son_update_id)"""
    if not TOKEN:
        return [], None
    try:
        guncel = tg("getUpdates", timeout=0).get("result", [])
    except Exception as e:  # Onay dinleyicisi (webhook) açıkken Telegram getUpdates'e izin vermez
        print("Telegram'dan klip okunamadı (webhook açık olabilir):", e)
        return [], None
    mesajlar, son = [], None
    for u in guncel:
        son = u["update_id"]
        m = u.get("message") or {}
        if CHAT and str(m.get("chat", {}).get("id")) != str(CHAT):
            continue
        dosya = m.get("video") or m.get("document")
        if dosya and (m.get("video") or str(dosya.get("mime_type", "")).startswith("video")):
            mesajlar.append((m["message_id"], dosya["file_id"]))
    os.makedirs(hedef_klasor, exist_ok=True)
    dosyalar = []
    for i, (_, file_id) in enumerate(sorted(mesajlar), 1):
        yol = tg("getFile", file_id=file_id)["result"]["file_path"]
        hedef = os.path.join(hedef_klasor, f"{i:02d}.mp4")
        urllib.request.urlretrieve(f"https://api.telegram.org/file/bot{TOKEN}/{yol}", hedef)
        dosyalar.append(hedef)
        print(f"Telegram'dan klip {i} indirildi")
    return dosyalar, son


def ses_var_mi(dosya):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", dosya], capture_output=True, text=True).stdout
    return bool(out.strip())


def klibi_hazirla(girdi, cikis):
    """Yatay ya da dikey her klibi 1080x1920'ye oturtur (yatayda arkası bulanık doldurulur)."""
    filtre = ("[0:v]split[a][b];"
              "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:4[bg];"
              "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")
    if ses_var_mi(girdi):
        calistir("-i", girdi, "-filter_complex", filtre, "-map", "[v]", "-map", "0:a:0", *VIDEO_AYAR, *SES_AYAR, cikis)
    else:
        calistir("-i", girdi, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", filtre,
                 "-map", "[v]", "-map", "1:a", "-shortest", *VIDEO_AYAR, *SES_AYAR, cikis)


def resimden_video(png, sure, cikis):
    calistir("-framerate", "30", "-i", png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-vf", f"format=yuv420p,loop=-1:1,trim=duration={sure},fade=t=in:st=0:d=0.2",
             "-t", str(sure), *VIDEO_AYAR, *SES_AYAR, cikis)


def main(klasor):
    os.makedirs(CIKTI, exist_ok=True)
    kok = os.path.join(KOK, "reklamlar", klasor)
    bolum = json.load(open(os.path.join(kok, "bolum.json"), encoding="utf-8"))
    renk = json.load(open(os.path.join(kok, "bilgi.json"), encoding="utf-8")).get("renk", "#e3121b")

    # Önce depodaki hazır klipler (reklamlar/<klasor>/klipler/01.mp4 ...), sonra Telegram'dan gelenler
    depodaki = sorted(glob.glob(os.path.join(kok, "klipler", "*.mp4")))
    telegramdan, son_update = telegramdan_klipler(os.path.join(CIKTI, "klipler"))
    klipler = depodaki + telegramdan
    print(f"Depodan {len(depodaki)}, Telegram'dan {len(telegramdan)} klip")
    if not klipler:
        sys.exit("Hiç klip bulunamadı. Klipleri sırayla Dükkan TV botuna gönder, sonra tekrar çalıştır.")
    print(f"{len(klipler)} klip bulundu")

    parcalar = []
    for n, adim in enumerate(bolum["akis"]):
        cikis = os.path.join(CIKTI, f"parca_{n:02d}.mp4")
        if adim["tip"] == "klip":
            no = adim["no"]
            if no > len(klipler):
                print(f"Uyarı: {no}. klip gönderilmemiş, atlandı")
                continue
            klibi_hazirla(klipler[no - 1], cikis)
        elif adim["tip"] == "kart":
            png = os.path.join(CIKTI, f"kart_{n:02d}.png")
            subprocess.run(["node", os.path.join(KOK, "kart.js"), adim["yazi"], png, adim.get("stil", "gecis"), renk], check=True)
            resimden_video(png, adim.get("sure", 2), cikis)
        elif adim["tip"] == "bilgi_karti":
            sessiz = os.path.join(CIKTI, f"bilgi_{n:02d}.mp4")
            subprocess.run(["node", os.path.join(KOK, "uret.js"), klasor], check=True,
                           env={**os.environ, "KARE_BAS": "480", "KARE_BIT": "690", "CIKTI": sessiz})
            calistir("-i", sessiz, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                     "-shortest", *VIDEO_AYAR, *SES_AYAR, cikis)
        parcalar.append(cikis)
        print(f"Parça {len(parcalar)} hazır ({adim['tip']})")

    liste = os.path.join(CIKTI, "liste.txt")
    with open(liste, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parcalar)
    ad = bolum.get("dosya_adi", klasor + "_bolum")
    gecici = os.path.join(CIKTI, ad + "_yaziliyor.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", "-movflags", "+faststart", gecici)
    os.replace(gecici, os.path.join(CIKTI, ad + ".mp4"))
    print("Bölüm hazır: " + ad + ".mp4")

    # Kullanılan klipleri bot kuyruğundan temizle ki bir sonraki bölüme karışmasın
    if son_update is not None:
        tg("getUpdates", offset=son_update + 1, timeout=0)
        print("Telegram kuyruğu temizlendi")


if __name__ == "__main__":
    main(sys.argv[1])
