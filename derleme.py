# Levent & Cemo derlemeleri — fal.ai'ye ÜCRETSİZ: önbellekteki dudak senkronlu klipler yeniden kurgulanır.
#   python derleme.py haftalik   → son 7 günde YAYINLANMIŞ skeçlerden dikey Shorts derlemesi (Pazar)
#   python derleme.py aylik      → geçen ayın tüm skeçleri, yatay uzun YouTube videosu (ayın 1'i, izlenme saati için)
#   python derleme.py elle mizah-02-hastane,mizah-05-berber  → seçilen skeçler (dikey)
# Sonuç: cikti/derleme/yayin.json (+ video, uzunda kapak). Yayın kuyruğuna ekleme iş akışında yapılır.
import datetime as dt
import glob
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KOK)
from oto_bolum import ass_zaman, calistir, efekt_uret, etiketsiz, sure  # noqa: E402
from bolum import SES_AYAR, VIDEO_AYAR  # noqa: E402
import muzik  # noqa: E402

CIKTI = os.path.join(KOK, "cikti", "derleme")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TR = dt.timezone(dt.timedelta(hours=3))
SAYAC = os.path.join(KOK, "derleme_sayac.json")


def klasorler_baslik():
    """senaryo başlığı → klasör eşlemesi (kuyruk kayıtlarını skeç klasörüne bağlamak için)."""
    es = {}
    for k in sorted(glob.glob(os.path.join(KOK, "reklamlar", "mizah-*"))):
        s = os.path.join(k, "oto", "senaryo.json")
        if os.path.exists(s) and os.path.exists(os.path.join(k, "oto", "klipler", "dizin.json")):
            es[json.load(open(s, encoding="utf-8"))["baslik"].strip().lower()] = k
    return es


def yayinlanmis(gun_bas, gun_son):
    """Bu tarih aralığında YouTube'da yayına girmiş Dükkan TV skeçleri (eski → yeni)."""
    es, sonuc = klasorler_baslik(), []
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")) + glob.glob(os.path.join(KOK, "kuyruk", "arsiv", "*.json")):
        k = json.load(open(p, encoding="utf-8"))
        if k.get("kanal") != "dukkantv" or k.get("durum") != "yuklendi" or not k.get("yayin") or k.get("derleme"):
            continue
        z = dt.datetime.fromisoformat(k["yayin"])
        ad = k.get("baslik", "").split("😂")[0].split("|")[0].strip().lower()
        if gun_bas <= z <= gun_son and ad in es:
            sonuc.append((z, es[ad]))
    return [k for _, k in sorted(sonuc)]


def kart(ust, alt, resim, d, hedef):
    """Bulanık sahne resmi üstünde başlık kartı (sessiz ses izli)."""
    def yazi(t):
        return t.replace("'", "’").replace(":", " ").replace("%", "")
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=18:2,eq=brightness=-0.25,"
          f"drawtext=fontfile={FONT}:text='{yazi(ust)}':fontsize=96:fontcolor=0xFFD23F:borderw=6:bordercolor=black:"
          "x=(w-text_w)/2:y=h*0.40,"
          f"drawtext=fontfile={FONT}:text='{yazi(alt)}':fontsize=70:fontcolor=white:borderw=5:bordercolor=black:"
          "x=(w-text_w)/2:y=h*0.50,fps=30,format=yuv420p")
    calistir("-loop", "1", "-i", resim, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-vf", vf,
             "-t", f"{d:.2f}", *VIDEO_AYAR, *SES_AYAR, "-shortest", hedef)


def skec(klasor, no):
    """Önbellekteki kliplerden tek skeçin gövdesi (altyazılı, efektli; müzik en sonda genel)."""
    oto = os.path.join(klasor, "oto")
    senaryo = json.load(open(os.path.join(oto, "senaryo.json"), encoding="utf-8"))
    dizin = json.load(open(os.path.join(oto, "klipler", "dizin.json"), encoding="utf-8"))
    parcalar, ass, zaman = [], [], 0.0
    for i, p in enumerate(senaryo["planlar"], 1):
        g = dizin.get(str(i))
        if not g:
            raise RuntimeError(f"{os.path.basename(klasor)} plan {i} klibi yok")
        klip = os.path.join(oto, "klipler", g["klip"])
        ses = os.path.join(oto, "klipler", g["ses"]) if g.get("ses") else None
        d = sure(ses) if ses else min(sure(klip), max(2, p.get("sure", 3)))
        cikis = os.path.join(CIKTI, f"s{no:02d}_{i:02d}.mp4")
        vf = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
              f"tpad=stop_mode=clone:stop_duration=3,trim=duration={d:.3f},setpts=PTS-STARTPTS[v]")
        efekt = efekt_uret(p.get("efekt"), d, oto)  # önbellekte var: ücret yok
        if ses:
            f = f";[1:a]aresample=44100,aformat=channel_layouts=stereo,apad,atrim=duration={d:.3f}"
            gir = ["-i", klip, "-i", ses]
            if efekt:
                gir += ["-i", efekt]
                f += (f"[k];[2:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.35,apad,"
                      f"atrim=duration={d:.3f}[e];[k][e]amix=inputs=2:normalize=0:duration=first")
            calistir(*gir, "-filter_complex", vf + f + "[a]", "-map", "[v]", "-map", "[a]", *VIDEO_AYAR, *SES_AYAR, cikis)
            b, s = g.get("aralik") or [0.2, d - 0.2]
            ass.append(f"Dialogue: 0,{ass_zaman(zaman + b)},{ass_zaman(zaman + s)},Alt,,0,0,0,,{etiketsiz(p['metin'])}")
        elif efekt:
            calistir("-i", klip, "-i", efekt, "-filter_complex",
                     vf + f";[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.9,apad,atrim=duration={d:.3f}[a]",
                     "-map", "[v]", "-map", "[a]", *VIDEO_AYAR, *SES_AYAR, cikis)
        else:
            calistir("-i", klip, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", vf,
                     "-map", "[v]", "-map", "1:a", "-t", f"{d:.3f}", *VIDEO_AYAR, *SES_AYAR, cikis)
        parcalar.append(cikis)
        zaman += d
    liste = os.path.join(CIKTI, f"s{no:02d}.txt")
    open(liste, "w").writelines(f"file '{x}'\n" for x in parcalar)
    govde = os.path.join(CIKTI, f"s{no:02d}_govde.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", govde)
    ass_yol = os.path.join(CIKTI, f"s{no:02d}.ass")
    open(ass_yol, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        "Style: Alt,Inter,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,360,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ass) + "\n")
    yazili = os.path.join(CIKTI, f"s{no:02d}_yazili.mp4")
    calistir("-i", govde, "-vf", f"ass={ass_yol}", *VIDEO_AYAR, "-c:a", "copy", yazili)
    return yazili, senaryo["baslik"], os.path.join(oto, "plan_01.jpg")


def uret(klasorler, tur):
    os.makedirs(CIKTI, exist_ok=True)
    sayac = json.load(open(SAYAC)) if os.path.exists(SAYAC) else {}
    n = sayac.get(tur, 0) + 1
    bolumler, basliklar = [], []
    for i, k in enumerate(klasorler, 1):
        yazili, bas, resim = skec(k, i)
        basliklar.append(bas)
        ara = os.path.join(CIKTI, f"kart_{i:02d}.mp4")
        kart(f"#{i}", bas, resim, 1.3, ara)
        bolumler += [ara, yazili]
    ilk_resim = os.path.join(klasorler[0], "oto", "plan_01.jpg")
    giris = os.path.join(CIKTI, "giris.mp4")
    ust = "HAFTANIN EN KOMİK" if tur == "haftalik" else "LEVENT & CEMO"
    alt = "SKEÇLERİ" if tur == "haftalik" else f"{len(klasorler)} SKEÇ BİR ARADA"
    kart(ust, alt, ilk_resim, 1.6, giris)
    cikis_k = os.path.join(CIKTI, "son.mp4")
    kart("ABONE OL", "Her gün yeni skeç", os.path.join(klasorler[-1], "oto", "plan_01.jpg"), 2.0, cikis_k)
    liste = os.path.join(CIKTI, "tum.txt")
    open(liste, "w").writelines(f"file '{x}'\n" for x in [giris, *bolumler, cikis_k])
    tum = os.path.join(CIKTI, "tum.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, *VIDEO_AYAR, *SES_AYAR, tum)
    m = muzik.uret(sure(tum), os.path.join(CIKTI, "muzik.wav"), bpm=112, tohum=n)
    son = os.path.join(CIKTI, f"Derleme_{tur}_{n:02d}.mp4")
    if tur == "aylik":  # yatay uzun video: dikey görüntü bulanık arka planla 16:9'a
        vf = ("[0:v]split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=30:3,"
              "eq=brightness=-0.2[bg];[b]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,format=yuv420p[v]")
    else:
        vf = "[0:v]null[v]"
    calistir("-i", tum, "-i", m, "-filter_complex",
             vf + ";[1:a]volume=0.07[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[ses]",
             "-map", "[v]", "-map", "[ses]", *VIDEO_AYAR, *SES_AYAR, "-movflags", "+faststart", son)
    toplam = sure(son)
    if tur == "haftalik":
        baslik = f"Haftanın En Komik Skeçleri #{n} 😂 | Levent & Cemo"
        aciklama = "Bu haftanın Levent & Cemo skeçleri bir arada! Hangisi daha komikti? Yorumlara yaz 👇\n\n" + \
                   "\n".join(f"#{i} {b}" for i, b in enumerate(basliklar, 1)) + "\n\n#shorts #komedi #mizah #esnaf"
    elif tur == "aylik":
        ay = (dt.datetime.now(TR).replace(day=1) - dt.timedelta(days=1)).strftime("%m.%Y")
        baslik = f"Levent & Cemo | Tüm Skeçler Bir Arada ({ay}) 😂"
        aciklama = (f"Levent & Cemo'nun {len(basliklar)} skeci tek videoda! Esnaf hayatının en komik halleri.\n\n"
                    + "\n".join(f"{i}. {b}" for i, b in enumerate(basliklar, 1)))
    else:
        baslik = f"Levent & Cemo En Komik Anlar #{n} 😂"
        aciklama = "\n".join(f"#{i} {b}" for i, b in enumerate(basliklar, 1))
    kapak = ""
    if tur == "aylik":
        from belgesel import kapak as kapak_yap
        kapak = os.path.join(CIKTI, "kapak.jpg")
        kapak_yap(ilk_resim, f"{len(basliklar)} SKEÇ BİR ARADA", kapak, "dedektif")
    sayac[tur] = n
    json.dump(sayac, open(SAYAC, "w"), indent=1)
    json.dump({"video": son, "baslik": baslik, "aciklama": aciklama, "kapak": kapak, "sure_dk": round(toplam / 60, 1),
               "etiketler": ["Levent ve Cemo", "komedi", "mizah", "skeç", "esnaf", "Dükkan TV"]},
              open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Hazır: {son} ({toplam:.0f} sn, {len(basliklar)} skeç)")
    return son


if __name__ == "__main__":
    tur = sys.argv[1] if len(sys.argv) > 1 else "haftalik"
    simdi = dt.datetime.now(TR)
    if tur == "haftalik":
        sec = yayinlanmis(simdi - dt.timedelta(days=7), simdi)
        if len(sec) < 3:
            print(f"Bu hafta {len(sec)} skeç yayınlanmış; derleme için en az 3 gerekir, atlandı")
            sys.exit(0)
        sec = sec[-5:]
    elif tur == "aylik":
        bu_ay = simdi.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        gecen = (bu_ay - dt.timedelta(days=1)).replace(day=1)
        sec = yayinlanmis(gecen, bu_ay)
        if len(sec) < 4:
            print(f"Geçen ay {len(sec)} skeç yayınlanmış; aylık derleme için en az 4 gerekir, atlandı")
            sys.exit(0)
    else:
        sec = [os.path.join(KOK, "reklamlar", x.strip()) for x in sys.argv[2].split(",") if x.strip()]
    print("Seçilen skeçler:", [os.path.basename(x) for x in sec])
    uret(sec, tur)
