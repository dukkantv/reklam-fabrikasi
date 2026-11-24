# Haftalık UZUN (yatay) YouTube derlemesi — ücretsiz, yeni üretim yok.
# Son 7 günde yayın kuyruğuna giren kısa videolar ("arsiv" sürümündeki kopyaları) yan yana bulanık arka planlı
# 1920x1080 videoya dönüştürülür; açılış/kapanış kartı, bölümler (chapters) ve kapak resmi eklenir.
#   python haftalik_uzun.py ilturnuva     → "81 İl Turnuvası · Haftanın Tüm Maçları"
#   python haftalik_uzun.py dramabite     → "Haftanın Duygusal Hikâyeleri"
# Neden: uzun video izlenme saati tüm kanallarda 0; YPP için 4.000 saat uzun video izlenmesi gerekir.
# Kaynak: Onur Naci Öztürkler, "YouTube'a başlamadan önce bilmek istediğim 10 şey" (Shorts + yatay video karışımı).
# Sonuç: cikti/haftalik/yayin.json (+ video, kapak). Yayın kuyruğuna ekleme iş akışında yapılır.
import datetime as dt
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti", "haftalik")
FONTLAR = os.path.join(KOK, "arena", "fonts")
TR = dt.timezone(dt.timedelta(hours=3))
EN_AZ = 3   # bundan az video varsa derleme yapılmaz
W, H = 1920, 1080

KANAL = {
    "ilturnuva": {
        "renk": (255, 196, 61), "ust": "81 İL TURNUVASI", "alt": "HAFTANIN TÜM MAÇLARI",
        "baslik": "81 İl Turnuvası · Haftanın Tüm Maçları ({aralik}) 🏆 Senin şehrin tur atladı mı?",
        "giris": "Bu haftanın bütün maçları tek videoda! Şehrin hangi grupta, tur atladı mı?",
        "kapanis": ("ŞEHRİNİ YORUMLARA YAZ!", "Beğen · Abone ol · Her gün yeni maç"),
        "etiketler": ["81 il turnuvası", "türkiye", "şehirler", "simülasyon", "top yarışı", "il il", "marble race",
                      "derleme"],
        "kategori": "24",
        "son": "#81ilturnuvası #türkiye #simülasyon",
    },
    "dramabite": {
        "renk": (230, 90, 110), "ust": "DRAMA BITE", "alt": "HAFTANIN HİKÂYELERİ",
        "baslik": "Haftanın {n} Duygusal Hikâyesi 💔 Drama Bite ({aralik})",
        "giris": "Bu haftanın bütün hikâyeleri arka arkaya. Hangisi sana en çok dokundu? Yorumlara yaz.\n\nHikâyeler kurgusaldır.",
        "kapanis": ("HANGİSİ SANA DOKUNDU?", "Beğen · Abone ol · Her gün yeni hikâye"),
        "etiketler": ["duygusal hikayeler", "hikaye", "kısa hikayeler", "aile hikayeleri", "pişmanlık",
                      "ibretlik hikayeler", "drama bite", "derleme"],
        "kategori": "24",
        "son": "#hikaye #duygusalhikayeler #dramabite",
    },
    # Kasa Kurgu: haftanın "Katil Kim?" vakaları tek uzun videoda. Model: Dedektif Gözü kanalı (12-14 dk'lık
    # "12 dedektif bilmecesi" derlemeleri, başlıkta "Sadece %1 Çözer" kalıbı). 24 Kas 2026, Levent onayıyla.
    "kasakurgu": {
        "renk": (220, 60, 60), "ust": "KATİL KİM?", "alt": "HAFTANIN DOSYALARI",
        "baslik": "Katil Kim? Haftanın {n} Vakası 🕵️ Hepsini Sadece %1 Çözer! ({aralik})",
        "giris": ("Bu haftanın bütün Katil Kim? dosyaları arka arkaya. Her vakada ipuçlarını izle, şüphelini seç; "
                  "cevap bir sonraki vakanın başında açıklanıyor. Kaçını doğru bildin? Yorumlara yaz!\n\nVakalar kurgusaldır."),
        "kapanis": ("KAÇINI BİLDİN?", "0-2 Çaylak · 3-4 Komiser · 5+ Başkomiser"),
        "dusun": 5,   # her vakadan sonra 5 sn geri sayım kartı (Dedektif Gözü'ndeki "10 saniyen var" oyunu)
        "etiketler": ["katil kim", "dedektif bilmeceleri", "bilmeceler", "gizem", "kim yalan söylüyor",
                      "dikkat testi", "kasa kurgu", "derleme"],
        "kategori": "24",
        "son": "#katilkim #dedektif #bilmece",
        "filtre": "katil kim",
        "birim": "VAKA",
    },
}

AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
      "Aralık"]


def font(s, k="Black"):
    return ImageFont.truetype(os.path.join(FONTLAR, f"InterDisplay-{k}.otf"), s)


def calistir(*arg):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *arg], check=True)


def sure(yol):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                                capture_output=True, text=True, check=True).stdout.strip())


def ses_var(yol):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", yol], capture_output=True, text=True).stdout.strip())


def arsivden_al(kanal, gun=7, filtre=None):
    """Son `gun` günde arşive giren videolar (eski → yeni): [(yol, başlık, tarih)]
    filtre: başlıkta geçmesi gereken ifade (küçük harf). Aynı başlıklı kopyalar tek sayılır."""
    try:
        veri = json.loads(subprocess.run(
            ["gh", "api", "repos/{owner}/{repo}/releases/tags/arsiv"], capture_output=True, text=True,
            check=True).stdout)
    except subprocess.CalledProcessError:
        print("Arşiv sürümü yok.")
        return []
    sinir = dt.datetime.now(TR) - dt.timedelta(days=gun)
    secilen = []
    for a in veri.get("assets", []):
        ad = a["name"]
        if not ad.endswith(f"-{kanal}.mp4"):
            continue
        try:
            z = dt.datetime.strptime(ad[:15], "%Y%m%d-%H%M%S").replace(tzinfo=TR)
        except ValueError:
            continue
        if z >= sinir:
            secilen.append((z, ad, (a.get("label") or "").strip()))
    secilen.sort()
    if filtre:
        secilen = [x for x in secilen if filtre in x[2].lower().replace("İ", "i")]
    tekil, gorulen = [], set()
    for x in secilen:   # aynı videonun tekrar kopyaları derlemeye iki kez girmesin
        if x[2] and x[2] in gorulen:
            continue
        gorulen.add(x[2]); tekil.append(x)
    secilen = tekil
    klasor = os.path.join(CIKTI, "kaynak")
    os.makedirs(klasor, exist_ok=True)
    sonuc = []
    for z, ad, etiket in secilen:
        subprocess.run(["gh", "release", "download", "arsiv", "-p", ad, "-D", klasor, "--clobber"], check=True)
        sonuc.append((os.path.join(klasor, ad), etiket or ad, z))
    return sonuc


def temiz_baslik(b):
    """'81 İl Turnuvası · 1. Tur · C Grubu 🏆 Senin şehrin…' → '1. Tur · C Grubu' (bölüm adı)."""
    b = b.replace("#shorts", "").strip()
    if b.startswith("81 İl Turnuvası"):
        b = b.replace("81 İl Turnuvası", "", 1).strip(" ·")
        b = b.split("🏆")[0].strip() or "Büyük Final"
    if "Katil Kim" in b:   # 'Katil Kim? 🕵️ Dosya #20: Kırmızı Bere | Yorumlara…' veya 'Kırmızı Bere: Katil Kim? …'
        m = re.search(r"Dosya #\d+:\s*([^|]+)", b)
        b = m.group(1) if m else b.split(":")[0]
        b = b.split("|")[0].strip()
    b = "".join(c for c in b if c.isalnum() or c in " .,:;!?'’·-/()").strip(" ·-")
    return b or "Bölüm"


def kare(yol_video, an=1.0):
    hedef = os.path.join(CIKTI, "kare.jpg")
    calistir("-ss", f"{an:.2f}", "-i", yol_video, "-frames:v", "1", hedef)
    return Image.open(hedef).convert("RGB")


def arka(resim):
    """Dikey kareden 1920x1080 bulanık ve koyulaştırılmış arka plan."""
    r = resim.copy()
    olc = max(W / r.width, H / r.height)
    r = r.resize((int(r.width * olc) + 1, int(r.height * olc) + 1))
    x, y = (r.width - W) // 2, (r.height - H) // 2
    r = r.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(28))
    return Image.blend(r, Image.new("RGB", (W, H), (0, 0, 0)), 0.55)


def yaz(d, xy, s, f, renk=(255, 255, 255), kenar=6):
    d.text(xy, s, font=f, fill=renk, anchor="mm", stroke_width=kenar, stroke_fill=(0, 0, 0))


def kart_resmi(arkaplan, ust, alt, renk, kucuk=None):
    im = arkaplan.copy(); d = ImageDraw.Draw(im)
    yaz(d, (W / 2, H * 0.40), ust, font(120), renk, 9)
    yaz(d, (W / 2, H * 0.55), alt, font(76), (255, 255, 255), 7)
    if kucuk:
        yaz(d, (W / 2, H * 0.68), kucuk, font(46, "Bold"), (225, 225, 235), 5)
    return im


def kart_video(resim, saniye, hedef):
    yol = hedef.replace(".mp4", ".jpg")
    resim.save(yol, quality=92)
    calistir("-loop", "1", "-i", yol, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{saniye:.2f}",
             "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-shortest", hedef)


def geri_sayim_video(arkaplan, renk, saniye, hedef):
    """'DÜŞÜN · 5…1' kartı; her saniyenin başında kısa tik sesi. kart_video ile aynı kodlama (concat -c copy için)."""
    resimler = []
    for i in range(saniye, 0, -1):
        im = kart_resmi(arkaplan, str(i), "DÜŞÜN · KATİL KİM?", renk, "Cevap bir sonraki vakanın başında")
        yol = hedef.replace(".mp4", f"_{i}.jpg"); im.save(yol, quality=92); resimler.append(yol)
    giris, zincir = [], ""
    for j, yol in enumerate(resimler):
        giris += ["-loop", "1", "-t", "1", "-i", yol]
        zincir += f"[{j}:v]fps=30,format=yuv420p,setsar=1[v{j}];"
    zincir += "".join(f"[v{j}]" for j in range(len(resimler))) + f"concat=n={len(resimler)}:v=1:a=0[v]"
    tik = "0.35*sin(2*PI*1400*t)*lt(mod(t\\,1)\\,0.06)"
    calistir(*giris, "-f", "lavfi", "-i", f"aevalsrc={tik}|{tik}:s=44100:d={saniye}",
             "-filter_complex", zincir, "-map", "[v]", "-map", f"{len(resimler)}:a", "-t", f"{saniye:.2f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", hedef)


def bolum_video(kaynak, etiket_png, hedef):
    """Dikey videoyu ortala, iki yanı aynı videonun bulanık hâli; sol üstte bölüm etiketi."""
    vf = ("[0:v]split[a][b];"
          "[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:3,eq=brightness=-0.28[bg];"
          "[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0[v1];[v1][1:v]overlay=0:0,fps=30,format=yuv420p[v]")
    giris = ["-i", kaynak, "-loop", "1", "-i", etiket_png]
    if ses_var(kaynak):
        ses = ["-map", "0:a"]
    else:
        giris += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        ses = ["-map", "2:a"]
    calistir(*giris, "-filter_complex", vf, "-map", "[v]", *ses, "-t", f"{sure(kaynak):.2f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", hedef)


def etiket_resmi(no, toplam, ad, renk, hedef):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sol = (W - 608) // 2   # dikey videonun soldaki boşluğu (~656 px)
    yaz(d, (sol / 2, 120), f"{no}/{toplam}", font(64), renk, 6)
    kelimeler, satir, satirlar = ad.split(), "", []
    for k in kelimeler:
        dene = (satir + " " + k).strip()
        if d.textlength(dene, font=font(46, "Bold")) > sol - 70 and satir:
            satirlar.append(satir); satir = k
        else:
            satir = dene
    satirlar.append(satir)
    for i, s in enumerate(satirlar[:4]):
        yaz(d, (sol / 2, 200 + i * 60), s, font(46, "Bold"), (255, 255, 255), 5)
    im.save(hedef)


def zaman(s):
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def main(kanal):
    k = KANAL[kanal]
    os.makedirs(CIKTI, exist_ok=True)
    videolar = arsivden_al(kanal, filtre=k.get("filtre"))
    if len(videolar) < EN_AZ:
        print(f"{kanal}: son 7 günde {len(videolar)} video var, en az {EN_AZ} gerekir. Derleme yok.")
        return
    bas, son = videolar[0][2], videolar[-1][2]
    aralik = (f"{bas.day}-{son.day} {AY[son.month]}" if bas.month == son.month
              else f"{bas.day} {AY[bas.month]} - {son.day} {AY[son.month]}")
    ilk_kare = kare(videolar[0][0], 1.0)
    ab = arka(ilk_kare)

    parcalar, bolumler, t = [], [], 0.0
    giris = os.path.join(CIKTI, "00_giris.mp4")
    kart_video(kart_resmi(ab, k["ust"], k["alt"], k["renk"], aralik), 4.0, giris)
    parcalar.append(giris); t += sure(giris)
    for i, (yol, etiket, _) in enumerate(videolar, 1):
        ad = temiz_baslik(etiket)
        png = os.path.join(CIKTI, f"{i:02d}_etiket.png")
        etiket_resmi(i, len(videolar), ad, k["renk"], png)
        hedef = os.path.join(CIKTI, f"{i:02d}_bolum.mp4")
        bolum_video(yol, png, hedef)
        # YouTube bölümleri: ilki 0:00 olmalı, her biri en az 10 sn (giriş kartı ilk bölüme katılır)
        bolumler.append((0.0 if i == 1 else t, ad)); parcalar.append(hedef); t += sure(hedef)
        if k.get("dusun") and i < len(videolar):
            ara = os.path.join(CIKTI, f"{i:02d}_dusun.mp4")
            geri_sayim_video(ab, k["renk"], k["dusun"], ara)
            parcalar.append(ara); t += sure(ara)
    kapanis = os.path.join(CIKTI, "99_kapanis.mp4")
    kart_video(kart_resmi(arka(kare(videolar[-1][0], 1.0)), k["kapanis"][0], k["kapanis"][1], k["renk"]), 5.0, kapanis)
    parcalar.append(kapanis); t += sure(kapanis)

    liste = os.path.join(CIKTI, "liste.txt")
    with open(liste, "w", encoding="utf-8") as f:
        f.writelines(f"file '{p}'\n" for p in parcalar)
    video = os.path.join(CIKTI, f"haftalik-{kanal}.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", "-movflags", "+faststart", video)

    # Kapak (1280x720): ortada büyük yazı, iki yanında ilk ve son videonun kareleri
    kapak_im = kart_resmi(ab, k["ust"], k["alt"], k["renk"], f"{len(videolar)} {k.get('birim') or ('MAÇ' if kanal == 'ilturnuva' else 'HİKÂYE')} · {aralik.upper()}")
    kapak = os.path.join(CIKTI, "kapak.jpg")
    kapak_im.resize((1280, 720)).save(kapak, quality=90)

    baslik = k["baslik"].format(aralik=aralik, n=len(videolar))[:100]
    bolum_metni = "\n".join(f"{zaman(s)} {ad}" for s, ad in bolumler)
    aciklama = f"{k['giris']}\n\n{bolum_metni}\n\n{k['son']}"
    meta = {"video": video, "baslik": baslik, "aciklama": aciklama, "etiketler": k["etiketler"],
            "kapak": kapak, "kategori": k["kategori"], "sure": round(t, 1), "adet": len(videolar)}
    json.dump(meta, open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{baslik} · {len(videolar)} video · {zaman(t)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ilturnuva")
