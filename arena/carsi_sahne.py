# Çarşı Ligi sahne videoları (fizik yok): geri sayım, kura gecesi, takım tanıtımı, fragman, konsey, haftalık özet.
# Her sahne "parça" listesidir: parça = (süre, konuşan, söz, çizici). Konuşan L/C/B (Levent, Cemo, Muhtar) ya da None.
# Önce sözler seslendirilir; parça süresi en az sesin uzunluğu kadar olur (sözler kesilmez).
import os, random, subprocess

import numpy as np
from PIL import Image, ImageDraw

import carsi
import carsi_ses
from carsi import W, H, FPS, SR, font, yazi, kes, gorsel, tr_ad, ESNAF, TAKIM_RENK, TAKIM_AD, CARSI

SLOGAN = {
    "simitci-kedi": "Sabahın köründe sıcak simit, miyav garantili!",
    "borekci-baykus": "Gece yarısı bile börek açar, çarşının en bilgesi!",
    "dondurmaci-keci": "Dondurmayı uzatır, müşteriyi kızdırır, sonra güldürür!",
    "kokorec-ejderha": "Ateşi kendinden, kokoreci efsane!",
    "lahmacun-kaplumbaga": "Yavaş ama emin adımlarla, bol yeşillikli lahmacun!",
    "pide-timsah": "Karadeniz'in en geniş ağızlı pidecisi!",
    "ayran-penguen": "Köpüğü buz gibi, kendisi daha da serin!",
    "cay-bardagi-tavsan": "Tavşan kanı çay, ince belli bardakta!",
    "caydanlik-pasa": "Çarşının en eski çaycısı, bıyığıyla meşhur!",
    "dolmus-kopek": "Durak kahyası: bir kişi daha alır, her zaman!",
    "kumpir-ayi": "Kumpiri o kadar dolu ki kapağı kapanmıyor!",
    "lokum-fil": "Pembe, tatlı ve kocaman: çarşının lokumu!",
    "nazar-baligi": "Rakiplerine bir bakar, nazar değer!",
    "simit-kapan-marti": "Simidi havada kapar, kimse elinden alamaz!",
    "tavla-kurbaga": "Zarı atar, rakibine mars yaptırır!",
}

_onbellek = {}


def resim(ad, boy):
    k = (ad, boy)
    if k not in _onbellek:
        yol = gorsel(ad) if not os.path.isabs(ad) else ad
        _onbellek[k] = kes(yol, boy) if yol and os.path.exists(yol) else None
    return _onbellek[k]


def dukkan(e, boy):
    return resim(f"dukkan-{e}.png", boy) or resim(os.path.join(carsi.GORSEL, e + ".png"), boy)


def veda(e, boy):
    return resim(f"veda-{e}.png", boy) or carsi.soluk(dukkan(e, boy))


def sevinc(e, boy):
    return resim(f"sevinc-{e}.png", boy) or dukkan(e, boy)


def takim_logosu(t, boy):
    return resim("takim-kirmizi.png" if t == "K" else "takim-mavi.png", boy)


def arka_plan(ad="carsi-aksam.png", koyu=120):
    yol = gorsel(ad) or gorsel("carsi-aksam.png")
    a = Image.open(yol).convert("RGB")
    a = a.resize((W, int(a.height * W / a.width)), Image.LANCZOS).crop((0, 0, W, H))
    kat = Image.new("RGBA", (W, H), (10, 8, 25, koyu))
    a.paste(kat, (0, 0), kat)
    return a


def ortala(im, r, cx, cy, olcek=1.0, alfa=1.0):
    if r is None:
        return
    if olcek != 1.0:
        r = r.resize((max(1, int(r.width * olcek)), max(1, int(r.height * olcek))))
    if alfa < 1.0:
        r = r.copy(); r.putalpha(r.getchannel("A").point(lambda v: int(v * alfa)))
    im.paste(r, (int(cx - r.width / 2), int(cy - r.height / 2)), r)


def sigdir(d, xy, metin, en, boy=36, anchor="lm", **k):
    """Yazıyı 'en' piksel genişliğe sığana kadar küçültür."""
    while boy > 16 and d.textlength(metin, font=font(boy, "Bold")) > en:
        boy -= 2
    yazi(d, xy, metin, font(boy, "Bold"), anchor=anchor, **k)


def balon(d, kim, metin, y=1700):
    """Altta konuşma şeridi: kim konuşuyor + söz."""
    ad = {"L": "LEVENT", "C": "CEMO", "B": "ÇARŞI MUHTARI"}[kim]
    renk = {"L": (255, 210, 60), "C": (120, 200, 255), "B": (240, 150, 90)}[kim]
    d.rounded_rectangle([40, y - 70, W - 40, y + 95], 30, fill=(255, 255, 255), outline=renk, width=6)
    yazi(d, (W / 2, y - 70), f" {ad} ", font(30), dolgu=renk, kenar=4)
    f = font(36 if len(metin) < 42 else 31 if len(metin) < 52 else 27, "Bold")
    satir = metin if len(metin) < 52 else None
    if satir:
        d.text((W / 2, y + 15), metin, font=f, fill=(20, 20, 30), anchor="mm")
    else:   # iki satır
        kel = metin.split(); yar = len(kel) // 2
        d.text((W / 2, y - 8), " ".join(kel[:yar]), font=f, fill=(20, 20, 30), anchor="mm")
        d.text((W / 2, y + 38), " ".join(kel[yar:]), font=f, fill=(20, 20, 30), anchor="mm")


def render(cikti, parcalar, arka="carsi-aksam.png", koyu=120, sesli=True, ust=None):
    """parcalar: [(min_süre, konuşan|None, söz|None, çizici(im, d, t, p, i))]"""
    sesler, sureler = [], []
    for sure, kim, soz, _ in parcalar:
        dalga = carsi_ses.tek(soz, kim) if (sesli and kim and soz) else None
        uzun = (len(dalga) / SR + 0.35) if dalga is not None else (carsi_ses.tahmini_sure(soz) if soz else 0)
        sesler.append(dalga); sureler.append(max(sure, uzun))
    toplam = sum(sureler)
    bg = arka_plan(arka, koyu)
    if ust:
        yazi(ImageDraw.Draw(bg), (W / 2, 70), ust, font(54 if len(ust) < 24 else 44), dolgu=(255, 210, 60), kenar=7)
    ses = carsi.Ses(toplam)
    vid = f"/tmp/sahne_v_{os.getpid()}.mp4"; wav = f"/tmp/sahne_s_{os.getpid()}.wav"
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                             "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    bas = 0.0
    for i, ((_, kim, soz, ciz), sure, dalga) in enumerate(zip(parcalar, sureler, sesler)):
        if dalga is not None:
            ses.ekle(bas + 0.15, dalga, 1.0)
        ses.ekle(bas, carsi.Ses.ton(660 if i % 2 else 523, 0.12, 25), 0.15)   # geçiş "tık"ı
        for k in range(int(round(sure * FPS))):
            t = k / FPS
            im = bg.copy(); d = ImageDraw.Draw(im)
            ciz(im, d, t, min(1.0, t / max(0.01, sure)), i)
            d = ImageDraw.Draw(im)
            if kim and soz:
                balon(d, kim, soz)
            proc.stdin.write(im.tobytes())
        bas += sure
    # hafif altlık: yavaş davul
    for b in np.arange(0, toplam, 1.0):
        ses.ekle(b, carsi.Ses.ton(55, 0.25, 12), 0.18)
    proc.stdin.close(); proc.wait()
    ses.kaydet(wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", cikti], check=True)
    for p in (vid, wav):
        if os.path.exists(p):
            os.remove(p)
    return toplam


# ───────────────────────── sahneler ─────────────────────────
def giris(p, gecikme=0.0, sure=0.35):
    return max(0.0, min(1.0, (p - gecikme) / sure)) if sure else 1.0


def geri_sayim(cikti, tarih_yazi="26 KASIM · 19:00", sesli=True):
    esnaflar = list(ESNAF)
    rnd = random.Random(7)

    def kepenk(im, d, t, p, i):
        yazi(d, (W / 2, 820), "ÇARŞI", font(90), dolgu=(255, 210, 60), kenar=8)
        yazi(d, (W / 2, 930), "BOMBOŞ... ŞİMDİLİK!", font(72), kenar=7)

    def isiklar(im, d, t, p, i):
        yazi(d, (W / 2, 260), "15 ESNAF", font(90), dolgu=(255, 210, 60), kenar=8)
        acik = int(p * 15 * 1.15)
        for j, e in enumerate(esnaflar):
            x = 120 + (j % 5) * 210; y = 520 + (j // 5) * 300
            r = dukkan(e, 190)
            ortala(im, r if j < acik else carsi.soluk(r), x, y, alfa=1.0 if j < acik else 0.35)

    def takimlar(im, d, t, p, i):
        for k_, (t_, x) in enumerate((("K", W * 0.27), ("M", W * 0.73))):
            lg = takim_logosu(t_, 380)
            if lg:
                ortala(im, lg, x, 800, olcek=0.6 + 0.4 * giris(p, k_ * 0.2))
            else:
                d.ellipse([x - 170, 630, x + 170, 970], fill=TAKIM_RENK[t_], outline=(255, 255, 255), width=8)
                yazi(d, (x, 800), TAKIM_AD[t_].replace(" ", "\n"), font(48), kenar=5)
        yazi(d, (W / 2, 800), "VS", font(96), dolgu=(255, 210, 60), kenar=8)
        yazi(d, (W / 2, 1150), "2 TAKIM · 1 ŞAMPİYON", font(64), kenar=7)

    def son(im, d, t, p, i):
        ortala(im, resim("logo.png", 640), W / 2, 760, olcek=0.7 + 0.3 * giris(p))
        yazi(d, (W / 2, 1210), tarih_yazi, font(80), dolgu=(255, 210, 60), kenar=8)
        yazi(d, (W / 2, 1310), "DÜKKAN TV'DE BAŞLIYOR", font(54), kenar=6)
    parcalar = [
        (3.0, "L", "Gece yarısı... Çarşı bomboş. Ama bu sessizlik uzun sürmeyecek.", kepenk),
        (4.0, "C", "Abi on beş esnaf geliyor! Simitçisi, kokoreççisi, dondurmacısı, hepsi!", isiklar),
        (3.5, "L", "İki takım: Kırmızı Tente ve Mavi Tente. Her hafta biri çarşıya veda edecek.", takimlar),
        (3.5, "C", "Çarşı Ligi, yirmi altı Kasım akşam yedide Dükkan TV'de! Kaçırmayın!", son),
    ]
    arka = "kepenk-kapali.png" if gorsel("kepenk-kapali.png") else "carsi-aksam.png"
    return render(cikti, parcalar, arka=arka, koyu=90 if arka == "kepenk-kapali.png" else 170, sesli=sesli)


def kura_gecesi(cikti, takimlar, sesli=True):
    """takimlar: {"K": [...], "M": [...]} — çekiliş sırası K, M, K, M..."""
    sira = []
    for j in range(max(len(takimlar["K"]), len(takimlar["M"]))):
        for t_ in ("K", "M"):
            if j < len(takimlar[t_]):
                sira.append((t_, takimlar[t_][j]))
    muhtar = resim("muhtar-kursu.png", 520) or resim("carsi-muhtari-bakkal.png", 520)

    def ac(im, d, t, p, i):
        ortala(im, muhtar, W / 2, 720, olcek=0.8 + 0.2 * giris(p))
        yazi(d, (W / 2, 1150), "KURA GECESİ", font(96), dolgu=(255, 210, 60), kenar=8)
        yazi(d, (W / 2, 1250), "HANGİ ESNAF HANGİ TAKIMDA?", font(48), kenar=6)

    def tablo(im, d, gosterilen, vurgulu=None, p=1.0):
        for t_, x in (("K", W * 0.25), ("M", W * 0.75)):
            d.rounded_rectangle([x - 240, 180, x + 240, 250], 30, fill=TAKIM_RENK[t_], outline=(255, 255, 255), width=4)
            yazi(d, (x, 215), TAKIM_AD[t_], font(40), kenar=4)
        say = {"K": 0, "M": 0}
        for (t_, e) in gosterilen:
            x0 = 40 if t_ == "K" else W // 2 + 20; y = 330 + say[t_] * 160; say[t_] += 1
            ortala(im, dukkan(e, 150), x0 + 75, y)
            sigdir(d, (x0 + 160, y), tr_ad(ESNAF[e][0]), en=W // 2 - 220, kenar=4,
                   dolgu=(255, 210, 60) if e in (vurgulu or ()) else (255, 255, 255))

    def cekilis(k):
        def ciz(im, d, t, p, i):
            tablo(im, d, sira[:k], vurgulu=[e for _, e in sira[max(0, k - 2):k]])
        return ciz
    parcalar = [(3.0, "B", "Kura gecesine hoş geldiniz! On beş esnaf, iki takım. Torbada isimler var.", ac)]
    yorum = {4: ("C", "Abi kalbim duracak, benim favorim hangi takıma düşecek?"),
             10: ("L", "Takımlar şekilleniyor, rekabet şimdiden kızıştı!")}
    k = 0
    while k < len(sira):   # ikişer ikişer: biri Kırmızı'ya, biri Mavi'ye
        cift = sira[k:k + 2]; k += len(cift)
        soz = ", ".join(f"{tr_ad(ESNAF[e][0])} {tr_ad(TAKIM_AD[t_])}'ye" for t_, e in cift) + "!"
        parcalar.append((2.2, "B", soz, cekilis(k)))
        if k in yorum:
            parcalar.append((2.2, *yorum[k], cekilis(k)))
    parcalar.append((4.0, "B", "Takımlar belli oldu! Sence hangisi kazanır? Yorumlara yaz!", cekilis(len(sira))))
    return render(cikti, parcalar, koyu=165, sesli=sesli, ust="ÇARŞI LİGİ · KURA GECESİ")


def takim_tanitim(cikti, takim, esnaflar, sesli=True):
    lg = takim_logosu(takim, 460)

    def ac(im, d, t, p, i):
        if lg:
            ortala(im, lg, W / 2, 760, olcek=0.7 + 0.3 * giris(p))
        else:
            d.ellipse([W / 2 - 230, 530, W / 2 + 230, 990], fill=TAKIM_RENK[takim], outline=(255, 255, 255), width=10)
        yazi(d, (W / 2, 1150), TAKIM_AD[takim], font(100), dolgu=TAKIM_RENK[takim], kenar=10, kenar_renk=(255, 255, 255))
        yazi(d, (W / 2, 1260), f"{len(esnaflar)} ESNAF · TEK HEDEF", font(52), kenar=6)

    def kart(e, j):
        def ciz(im, d, t, p, i):
            d.rounded_rectangle([60, 300, W - 60, 1470], 40, fill=(20, 16, 40), outline=TAKIM_RENK[takim], width=10)
            yazi(d, (W / 2, 370), f"{j + 1} / {len(esnaflar)}", font(40, "Bold"), dolgu=TAKIM_RENK[takim], kenar=4,
                 kenar_renk=(255, 255, 255))
            ortala(im, dukkan(e, 760), W / 2 - (1 - giris(p)) * 300, 860)
            yazi(d, (W / 2, 1330), ESNAF[e][0], font(68 if len(ESNAF[e][0]) < 15 else 54), kenar=7)
        return ciz

    def son(im, d, t, p, i):
        for j, e in enumerate(esnaflar):
            x = W * ((j % 4) + 0.5) / 4; y = 560 + (j // 4) * 330
            ortala(im, dukkan(e, 230), x, y)
        yazi(d, (W / 2, 1300), "ÇARŞI LİGİ · 26 KASIM 19:00", font(52), dolgu=(255, 210, 60), kenar=6)
    parcalar = [(3.0, "L", f"İşte {tr_ad(TAKIM_AD[takim])}! Bu takımın esnaflarıyla tanışın!", ac)]
    for j, e in enumerate(esnaflar):
        parcalar.append((2.4, "L" if j % 2 == 0 else "C", f"{tr_ad(ESNAF[e][0])}! {SLOGAN[e]}", kart(e, j)))
    parcalar.append((3.5, "C", f"{tr_ad(TAKIM_AD[takim])} hazır! Sen bu takımı tutuyor musun? Yorumlara yaz!", son))
    return render(cikti, parcalar, koyu=150, sesli=sesli, ust=f"TAKIM TANITIMI · {TAKIM_AD[takim]}")


def fragman(cikti, takimlar, sesli=True):
    import math

    def vs(im, d, t, p):
        for t_, x in (("K", W * 0.27), ("M", W * 0.73)):
            lg = takim_logosu(t_, 380)
            if lg:
                ortala(im, lg, x, 520)
        yazi(d, (W / 2, 520), "VS", font(int(110 * (1 + 0.08 * math.sin(t * 6)))), dolgu=(255, 210, 60), kenar=9)

    def esnaflar(im, d, t, p, tek_tek=False):
        for k_, (t_, x) in enumerate((("K", W * 0.27), ("M", W * 0.73))):
            for j, e in enumerate(takimlar[t_]):
                g = giris(p, gecikme=j * 0.08, sure=0.15) if tek_tek else 1.0
                if g > 0:
                    ortala(im, dukkan(e, 150), x + (-90 if j % 2 == 0 else 90), 800 + (j // 2) * 170, olcek=0.4 + 0.6 * g)

    def ac(im, d, t, p, i):
        vs(im, d, t, p); esnaflar(im, d, t, p, tek_tek=True)

    def tam(im, d, t, p, i):
        vs(im, d, t, p); esnaflar(im, d, t, p)

    def muhtar(im, d, t, p, i):
        ortala(im, resim("muhtar-kursu.png", 760) or resim("carsi-muhtari-bakkal.png", 640), W / 2,
               820 - (1 - giris(p)) * 120, alfa=giris(p))
        yazi(d, (W / 2, 330), "HER HAFTA BİR VEDA", font(76), dolgu=(255, 90, 80), kenar=8)

    def son(im, d, t, p, i):
        vs(im, d, t, p)
        yazi(d, (W / 2, 900), "YARIN 19:00", font(120), dolgu=(255, 210, 60), kenar=10)
        yazi(d, (W / 2, 1040), "TAKIMINI YORUMLARA YAZ!", font(60), kenar=6)
    parcalar = [
        (3.0, "L", "Yarın akşam yedide Çarşı Ligi başlıyor!", ac),
        (3.0, "C", "İlk maç ödül maçı abi! Kırmızı mı kazanır, Mavi mi?", tam),
        (3.0, "B", "Her hafta bir esnaf çarşıya veda edecek. Kaderleri sizin yorumlarınızda!", muhtar),
        (2.5, "L", "Takımını seç, yorumlara yaz! Yarın 19:00, Dükkan TV!", son),
    ]
    return render(cikti, parcalar, koyu=160, sesli=sesli, ust="ÇARŞI LİGİ · YARIN BAŞLIYOR")


def konsey(cikti, hafta, pota, sayim, kurtulan, nasil, sesli=True):
    """pota: 3 esnaf; sayim: {esnaf: yorum_sayisi}; nasil: 'yorum' | 'kura'"""
    muhtar = resim("muhtar-kursu.png", 420) or resim("carsi-muhtari-bakkal.png", 420)
    kalan = [e for e in pota if e != kurtulan]
    en = max(1, max(sayim.values()) if sayim else 1)

    def ust_kisim(im, d):
        ortala(im, muhtar, W / 2, 380)

    def adaylar(im, d, t, p, i, goster_sayim=False, vurgu=None):
        ust_kisim(im, d)
        for j, e in enumerate(pota):
            x = W * (j + 0.5) / 3
            r = dukkan(e, 300)
            if vurgu and e != vurgu:
                r = carsi.soluk(r)
            ortala(im, r, x, 860, olcek=1.12 if e == vurgu else 1.0)
            yazi(d, (x, 1060), tr_ad(ESNAF[e][0]), font(30 if len(ESNAF[e][0]) < 14 else 24, "Bold"), kenar=4)
            if goster_sayim:
                v = sayim.get(e, 0); h = int(260 * giris(p, 0, 0.8) * v / en)
                d.rounded_rectangle([x - 50, 1400 - h, x + 50, 1400], 12, fill=(255, 210, 60))
                yazi(d, (x, 1440), f"{v} yorum", font(32, "Bold"), kenar=4)

    parcalar = [
        (3.0, "B", f"Esnaf Konseyi'ne hoş geldiniz. {hafta}. haftanın potası belli.",
         lambda im, d, t, p, i: adaylar(im, d, t, p, i)),
        (3.0, "B", f"{', '.join(tr_ad(ESNAF[e][0]) for e in pota)}. Kaderiniz izleyicilerin elinde.",
         lambda im, d, t, p, i: adaylar(im, d, t, p, i)),
    ]
    if nasil == "yorum":
        parcalar.append((3.5, "C", "Abi yorumlar sayıldı, kalbim yerinden çıkacak!",
                         lambda im, d, t, p, i: adaylar(im, d, t, p, i, goster_sayim=True)))
        parcalar.append((3.5, "B", f"İzleyicilerin kurtardığı esnaf: {tr_ad(ESNAF[kurtulan][0])}!",
                         lambda im, d, t, p, i: adaylar(im, d, t, p, i, goster_sayim=True, vurgu=kurtulan)))
    else:
        parcalar.append((3.5, "C", "Abi bu hafta yeterince yorum yok, karar muhtarın kurasında!",
                         lambda im, d, t, p, i: adaylar(im, d, t, p, i)))
        parcalar.append((3.5, "B", f"Kuradan çıkan isim: {tr_ad(ESNAF[kurtulan][0])}! Bu hafta kurtuldun!",
                         lambda im, d, t, p, i: adaylar(im, d, t, p, i, vurgu=kurtulan)))

    def duello_ciz(im, d, t, p, i):
        ust_kisim(im, d)
        for j, e in enumerate(kalan):
            ortala(im, dukkan(e, 360), W * (0.27 if j == 0 else 0.73), 900)
        yazi(d, (W / 2, 900), "VS", font(100), dolgu=(240, 80, 80), kenar=8)
        yazi(d, (W / 2, 1200), "ELEME DÜELLOSU", font(70), dolgu=(240, 80, 80), kenar=7)
        yazi(d, (W / 2, 1290), "YARIN · KAYBEDEN ÇARŞIYA VEDA EDER", font(38, "Bold"), kenar=5)
    parcalar.append((4.0, "B", f"{tr_ad(ESNAF[kalan[0]][0])} ve {tr_ad(ESNAF[kalan[1]][0])}, yarın düelloda karşılaşacaksınız!",
                     duello_ciz))
    parcalar.append((3.0, "L", "Sence kim kalmalı? Yorumlara yaz, yarın görüşürüz!", duello_ciz))
    arka = "konsey.png" if gorsel("konsey.png") else "carsi-aksam.png"
    return render(cikti, parcalar, arka=arka, koyu=90 if arka == "konsey.png" else 170, sesli=sesli,
                  ust=f"ESNAF KONSEYİ · {hafta}. HAFTA")


def ozet(cikti, hafta, durum, olaylar, sesli=True):
    """olaylar: {"odul": "K"/"M"/None, "dok": {"K": 2, "M": 1}, "veda": esnaf, "birlesme": bool}"""
    kalanlar = durum["takimlar"]["K"] + durum["takimlar"]["M"] if durum["faz"] == "takim" else durum["kalan"]
    elenen = durum["elenen"]

    def ciz_sonuc(im, d, t, p, i):
        y = 300
        if olaylar.get("odul"):
            yazi(d, (W / 2, y), f"ÖDÜL: {TAKIM_AD[olaylar['odul']]}", font(52), dolgu=TAKIM_RENK[olaylar['odul']], kenar=6,
                 kenar_renk=(255, 255, 255)); y += 100
        if olaylar.get("dok"):
            yazi(d, (W / 2, y), f"DOKUNULMAZLIK  KIRMIZI {olaylar['dok'].get('K', 0)} – {olaylar['dok'].get('M', 0)} MAVİ",
                 font(40, "Bold"), kenar=5); y += 90
        if olaylar.get("veda"):
            yazi(d, (W / 2, y + 40), "ÇARŞIYA VEDA EDEN", font(56), dolgu=(240, 90, 90), kenar=6)
            ortala(im, veda(olaylar["veda"], 520), W / 2, y + 420)
            yazi(d, (W / 2, y + 740), ESNAF[olaylar["veda"]][0], font(60), kenar=7)

    def ciz_kadro(im, d, t, p, i):
        yazi(d, (W / 2, 250), "ÇARŞIDA KALANLAR", font(64), dolgu=(255, 210, 60), kenar=7)
        tum = kalanlar + elenen
        for j, e in enumerate(tum):
            x = W * ((j % 4) + 0.5) / 4; y = 480 + (j // 4) * 300
            r = dukkan(e, 220)
            ortala(im, carsi.soluk(r) if e in elenen else r, x, y, alfa=0.45 if e in elenen else 1.0)
            if durum["faz"] == "takim" and e in kalanlar:
                t_ = "K" if e in durum["takimlar"]["K"] else "M"
                d.rounded_rectangle([x - 60, y + 112, x + 60, y + 124], 6, fill=TAKIM_RENK[t_])
    parcalar = [(3.5, "L", f"{hafta}. haftanın özeti! Neler oldu neler!", ciz_sonuc)]
    if olaylar.get("odul"):
        parcalar.append((3.0, "C", f"Ödülü {tr_ad(TAKIM_AD[olaylar['odul']])} kaptı abi, ziyafet çektiler!", ciz_sonuc))
    if olaylar.get("veda"):
        parcalar.append((3.5, "L", f"Ve {tr_ad(ESNAF[olaylar['veda']][0])} çarşıya veda etti. Kepenkleri kapandı.", ciz_sonuc))
    parcalar.append((3.5, "C", f"Çarşıda {len(kalanlar)} esnaf kaldı. Rekabet kızışıyor!", ciz_kadro))
    if olaylar.get("birlesme"):
        parcalar.append((4.0, "B", "Büyük haber! Takımlar dağılıyor. Artık herkes kendi dükkânı için yarışacak!", ciz_kadro))
    parcalar.append((3.0, "L", "Yarın yeni hafta başlıyor. Takip etmeyi unutmayın!", ciz_kadro))
    return render(cikti, parcalar, koyu=165, sesli=sesli, ust=f"ÇARŞI LİGİ · {hafta}. HAFTANIN ÖZETİ")
