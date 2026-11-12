# Uzun YouTube videosu (yatay 16:9) — TAMAMEN ÜCRETSİZ
#   tur=tarih    → Tarih & Gizem belgeseli: GERÇEK arşiv görselleri (Wikimedia Commons), yedek: çizim
#   tur=dedektif → Kasa Kurgu "Katil kim?" vakası: kara-film çizimleri
#   tur=hikaye   → Drama Bite duygusal hikâye: sıcak çizimler
#   Senaryo: Gemini · Ses: edge-tts · Montaj: ffmpeg · Her resim anlatılan cümleyle Gemini'ye kontrol ettirilir
# Kullanım: python belgesel.py "konu" [dakika] [tur]
import asyncio, base64, json, os, re, subprocess, sys, time, urllib.parse

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti", "belgesel")
GEMINI_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
TOKEN, CHAT = os.environ.get("TOKEN", "").strip(), os.environ.get("CHAT", "").strip()
SES = os.environ.get("BELGESEL_SES", "tr-TR-AhmetNeural")
W, H, FPS = 1920, 1080, 25
UA = {"User-Agent": "DukkanTV-Belgesel/1.0 (https://dukkantv.github.io)"}

STILLER = {
    "tarih": "detailed historical oil painting style, dramatic chiaroscuro light, rich colors, museum quality",
    "dedektif": "dark noir graphic novel illustration, strong ink lines, moody blue and amber light, rain, cinematic",
    "hikaye": "warm cinematic digital painting, soft light, emotional, realistic proportions, modern Turkey",
}
ORTAK = "no text, no letters, no captions, no signs with writing, no watermark, 16:9 wide composition"

TURLER = {
    "tarih": """Sen Türkiye'nin en çok izlenen tarih ve gizem belgesellerini yazan bir senaristsin. Konu: {konu}
Anlatıcı üçüncü şahısla, belgesel ciddiyetinde ama sürükleyici anlatır. YALNIZCA tarihçe kabul görmüş bilgileri
kullan; tartışmalı konularda "kaynaklara göre", "bir rivayete göre" de. Uydurma söz, uydurma rakam YOK.""",
    "dedektif": """Sen Türkiye'de "Katil kim?" türünde dedektif vakaları yazan bir polisiye yazarısın. Kanal: Kasa Kurgu.
Konu: {konu}. TAMAMEN KURGU: gerçek kişi, gerçek olay, marka YOK. Bir cinayet/olay, 3-4 şüpheli, her birinin sırrı,
dürüst ipuçları ve bir yanıltma. Sondan önce "Durdurun ve tahmin edin: katil kim? Yorumlara yazın." de, sonra
çözümü ipuçlarıyla açıkla. Kan, vahşet tarifi YOK; gerilim atmosferle kurulur.""",
    "hikaye": """Sen Türkiye'de çok izlenen duygusal hikâyeler anlatan bir senaristsin. Kanal: Drama Bite. Konu: {konu}.
Kurgusal, aile/vefa/pişmanlık/umut temalı, ibretlik ve gerçekçi. Gerçek kişi, marka, siyaset YOK.""",
}

ORTAK_KURAL = """
Toplam yaklaşık {dakika} dakika anlatım ({kelime} kelime civarı). İlk iki cümle çok güçlü bir kanca olsun (en
çarpıcı soruyu en başta sor). Sade, akıcı Türkçe. Sonunda abone olma ve yorum çağrısı.
{sahne} sahneye böl. Her sahnede anlatım 2-3 cümle (20-30 kelime). Her sahne için:
- "metin": Türkçe anlatım.
- "nesne": bu sahnede ekranda MUTLAKA görünmesi gereken ana şey (kişi, nesne veya mekân), İngilizce, 3-8 kelime.
  Anlatımda adı geçen somut şeyi seç (ör. "Ottoman war galley at sea", "brass tea glass on wooden table").
- "arama": Wikimedia Commons'ta bu sahneye uygun GERÇEK görseli bulacak İngilizce arama (2-5 kelime,
  ör. "Suleiman the Magnificent portrait", "Siege of Vienna 1683 painting", "Great Pyramid of Giza").
- "gorsel": İngilizce tek kare çizim tarifi; nesne ile BAŞLASIN, sonra mekân, eylem, ışık.
Tekrar eden karakterleri her seferinde aynı kıyafet ve görünüşle tarif et.

SADECE şu JSON:
{{"baslik": "en fazla 60 karakter, aranan kelime başta, merak uyandıran Türkçe YouTube başlığı",
  "kapak_yazi": "kapak için en fazla 3 kelimelik çarpıcı Türkçe yazı, BÜYÜK HARF",
  "aciklama": "ilk 2 cümlesi kanca olan 4-5 cümlelik YouTube açıklaması",
  "etiketler": ["8-12 Türkçe etiket"],
  "bolumler": [{{"sahne": 1, "ad": "Giriş"}}, {{"sahne": 9, "ad": "..."}}],
  "sahneler": [{{"metin": "...", "nesne": "...", "arama": "...", "gorsel": "..."}}]}}"""


def gemini(parcalar, json_mu=True, modeller=("gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"),
           deneme=3, zaman=240):
    for model in modeller:
        for d in range(deneme):
            try:
                cfg = {"temperature": 0.9}
                if json_mu:
                    cfg["responseMimeType"] = "application/json"
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                                  f"?key={GEMINI_KEY}", timeout=zaman,
                                  json={"contents": [{"parts": parcalar}], "generationConfig": cfg})
                if r.status_code == 200:
                    t = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(re.sub(r"^```(json)?|```$", "", t.strip()).strip()) if json_mu else t
                print(f"Gemini {model} {r.status_code}: {r.text[:120]}")
                if r.status_code == 429:
                    break
            except Exception as e:
                print(f"Gemini {model} hata: {str(e)[:120]}")
            time.sleep(6 * (d + 1))
    return None


KONTROL_KAPALI = False


def alakali_mi(img, metin, nesne):
    """Gemini resme bakar: anlatılanla alakalı mı? (0-10). Kota biterse kontrolü kapatır, resmi kabul eder."""
    global KONTROL_KAPALI
    if KONTROL_KAPALI or not GEMINI_KEY:
        return 10
    veri = base64.b64encode(open(img, "rb").read()).decode()
    c = gemini([{"inlineData": {"mimeType": "image/jpeg", "data": veri}},
                {"text": f'Bir belgesel videosunda bu resim şu anlatımın üstünde gösterilecek: "{metin}". '
                         f'Görünmesi gereken ana şey: "{nesne}". Resim bu anlatımla ne kadar alakalı? '
                         'Resimde yazı/harf, filigran, modern alakasız öğe, bozuk yüz/el varsa puanı düşür. '
                         'SADECE JSON: {"puan": 0-10, "neden": "kısa"}'}],
               modeller=("gemini-flash-lite-latest", "gemini-flash-latest"), deneme=2, zaman=60)
    if c is None:
        print("Görsel kontrolü kota/hata nedeniyle kapatıldı")
        KONTROL_KAPALI = True
        return 10
    print(f"   kontrol {c.get('puan')}/10 — {c.get('neden', '')[:70]}")
    try:
        return float(c.get("puan", 0))
    except Exception:
        return 0


# ---------- GERÇEK GÖRSEL: Wikimedia Commons (kamu malı / özgür lisans) ----------
KULLANILAN, KAYNAKCA = set(), []
IZINLI = ("public domain", "pd", "cc0", "cc by", "cc-by")


def commons_ara(sorgu, adet=6):
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=40, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
            "gsrsearch": f"{sorgu} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 2400})
        sayfalar = (r.json().get("query") or {}).get("pages", {})
    except Exception as e:
        print("Commons hata:", str(e)[:100])
        return []
    sonuc = []
    for p in sorted(sayfalar.values(), key=lambda x: x.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lisans = meta.get("LicenseShortName", {}).get("value", "").lower()
        if ii.get("width", 0) < 900 or ii.get("height", 0) < 500 or p["title"] in KULLANILAN:
            continue
        if not any(l in lisans for l in IZINLI) or "nc" in lisans.split() or "-nd" in lisans:
            continue
        yazar = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:60]
        sonuc.append({"url": ii.get("thumburl") or ii["url"], "baslik": p["title"], "lisans": lisans,
                      "yazar": yazar or "Wikimedia Commons"})
        if len(sonuc) >= adet:
            break
    return sonuc


def indir(url, hedef):
    try:
        r = requests.get(url, headers=UA, timeout=90)
        if r.status_code == 200 and len(r.content) > 15000:
            open(hedef, "wb").write(r.content)
            return True
    except Exception as e:
        print("indirme hata:", str(e)[:80])
    return False


# ---------- ÇİZİM: Pollinations, yedek Gemini resim ----------
def resim_pollinations(prompt, hedef, tohum):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:900]) +
           f"?width=1344&height=768&model=flux&seed={tohum}&nologo=true&private=true")
    r = requests.get(url, timeout=180)
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
        open(hedef, "wb").write(r.content)
        return True
    print(f"Pollinations {r.status_code} {len(r.content)}")
    return False


def resim_gemini(prompt, hedef):
    for model in ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                              f"?key={GEMINI_KEY}", timeout=180,
                              json={"contents": [{"parts": [{"text": prompt + " Landscape 16:9."}]}],
                                    "generationConfig": {"responseModalities": ["IMAGE"]}})
            if r.status_code == 200:
                for p in r.json()["candidates"][0]["content"]["parts"]:
                    if "inlineData" in p:
                        open(hedef, "wb").write(base64.b64decode(p["inlineData"]["data"]))
                        return True
            print(f"Gemini resim {model} {r.status_code}")
        except Exception as e:
            print("Gemini resim hata:", str(e)[:80])
    return False


def ciz(sc, tur, hedef, tohum):
    # Nesne EN BAŞTA: model önce anlatılan şeyi çizsin, stil sonra gelsin
    prompt = f"{sc['nesne']} clearly visible as the main subject. {sc['gorsel']}. {STILLER[tur]}. {ORTAK}"
    for d in range(3):
        try:
            if resim_pollinations(prompt, hedef, tohum + d * 97):
                return True
        except Exception as e:
            print("Pollinations hata:", str(e)[:80])
        time.sleep(8 * (d + 1))
    return resim_gemini(prompt, hedef)


def sahne_resmi(sc, tur, i):
    """Önce gerçek arşiv görseli (tarih), olmazsa çizim. Her aday anlatımla kontrol edilir."""
    son = os.path.join(CIKTI, f"r_{i:03d}.jpg")
    if os.path.exists(son) and os.path.getsize(son) > 15000:
        return son
    ham = os.path.join(CIKTI, f"ham_{i:03d}")
    en_iyi, en_puan = None, -1
    if tur == "tarih":
        for aday in commons_ara(sc.get("arama") or sc["nesne"])[:3]:
            if not indir(aday["url"], ham):
                continue
            puan = alakali_mi(ham, sc["metin"], sc["nesne"])
            if puan > en_puan:
                os.replace(ham, son); en_iyi, en_puan = aday, puan
            if puan >= 7:
                break
        if en_iyi and en_puan >= 6:
            KULLANILAN.add(en_iyi["baslik"])
            KAYNAKCA.append(f"{en_iyi['baslik'].replace('File:', '')} — {en_iyi['yazar']} ({en_iyi['lisans']})")
            return son
    for d in range(2):  # çizim, gerekirse bir kez daha
        if ciz(sc, tur, ham, 1000 + i + d * 31):
            puan = alakali_mi(ham, sc["metin"], sc["nesne"])
            if puan > en_puan:
                os.replace(ham, son); en_puan = puan
            if puan >= 6:
                break
    return son if os.path.exists(son) else None


def kadraj(src, hedef):
    """Dikey/kare resimleri kesmeden 16:9'a oturtur: arka plan bulanık, resim ortada."""
    calistir("-i", src, "-filter_complex",
             "[0:v]split[a][b];[a]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,boxblur=30:3,"
             "eq=brightness=-0.15[bg];[b]scale=3200:1800:force_original_aspect_ratio=decrease[fg];"
             "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuvj420p", "-frames:v", "1", "-q:v", "3", hedef)


def calistir(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def sure(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).strip())


def ass_zaman(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def altyazi_parcala(metin, bas, son):
    cumleler = re.split(r"(?<=[.!?…])\s+", metin.strip())
    parcalar = []
    for c in cumleler:
        k = c.split()
        while len(k) > 14:
            parcalar.append(" ".join(k[:12])); k = k[12:]
        if k:
            parcalar.append(" ".join(k))
    toplam = sum(len(p.split()) for p in parcalar) or 1
    t, satirlar = bas, []
    for p in parcalar:
        d = (son - bas) * len(p.split()) / toplam
        satirlar.append((t, t + d, p)); t += d
    return satirlar


def kapak(img, yazi, hedef, tur):
    renk = {"tarih": "0xF2C14E", "dedektif": "0xE63946", "hikaye": "0xFF9F1C"}[tur]
    k = yazi.upper().replace("'", "’").replace(":", " ").split()[:5]
    satirlar = [" ".join(k)] if len(" ".join(k)) <= 14 else [" ".join(k[:len(k) // 2 + len(k) % 2]), " ".join(k[len(k) // 2 + len(k) % 2:])]
    fs = min(130, int(1180 / (0.66 * max(len(x) for x in satirlar))))
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    vf = ("scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=contrast=1.15:saturation=1.25,"
          f"drawbox=x=0:y=ih-{len(satirlar) * fs * 1.15 + 50:.0f}:w=iw:h=ih:color=black@0.55:t=fill")
    for j, sat in enumerate(satirlar):
        y = 720 - 30 - (len(satirlar) - j) * fs * 1.15
        vf += (f",drawtext=fontfile={font}:text='{sat}':fontsize={fs}:fontcolor={renk}:borderw=6:bordercolor=black:"
               f"x=(w-text_w)/2:y={y:.0f}")
    calistir("-i", img, "-vf", vf, "-frames:v", "1", "-q:v", "2", hedef)


def main(konu, dakika=10, tur="tarih"):
    os.makedirs(CIKTI, exist_ok=True)
    sahne = max(10, int(dakika * 60 / 10))
    yol = os.path.join(CIKTI, "senaryo.json")
    if os.path.exists(yol):
        s = json.load(open(yol, encoding="utf-8"))
    else:
        istem = TURLER[tur].format(konu=konu) + ORTAK_KURAL.format(dakika=dakika, kelime=int(dakika * 135), sahne=sahne)
        s = gemini([{"text": istem}]) or sys.exit("Senaryo yazılamadı (Gemini kotası?)")
        json.dump(s, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(s["baslik"], "|", len(s["sahneler"]), "sahne")

    import edge_tts
    parcalar, ass, zaman, eksik, baslangic = [], [], 0.0, [], {}
    for i, sc in enumerate(s["sahneler"], 1):
        print(f"Sahne {i}: {sc['nesne']}")
        src = sahne_resmi(sc, tur, i)
        if not src:
            eksik.append(i)
            continue
        img = os.path.join(CIKTI, f"k_{i:03d}.jpg")
        if not os.path.exists(img):
            kadraj(src, img)
        mp3 = os.path.join(CIKTI, f"s_{i:03d}.mp3")
        if not os.path.exists(mp3):
            asyncio.run(edge_tts.Communicate(sc["metin"], SES, rate="-4%").save(mp3))
        d = sure(mp3) + 0.6
        out = os.path.join(CIKTI, f"p_{i:03d}.mp4")
        kare = int(d * FPS)
        yon = ["zoom+0.0005", "zoom+0.0005", "1.10-0.0005*on"][i % 3]
        x = ["iw/2-(iw/zoom/2)", "iw/2-(iw/zoom/2)+on*0.25", "iw/2-(iw/zoom/2)-on*0.25"][i % 3]
        calistir("-loop", "1", "-i", img, "-i", mp3, "-filter_complex",
                 f"[0:v]zoompan=z='min(max({yon},1.0),1.12)':x='{x}':y='ih/2-(ih/zoom/2)':"
                 f"d={kare}:s={W}x{H}:fps={FPS},format=yuv420p[v];[1:a]apad=pad_dur=0.6[a]",
                 "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", out)
        for a, b, p in altyazi_parcala(sc["metin"], zaman + 0.1, zaman + d - 0.5):
            ass.append(f"Dialogue: 0,{ass_zaman(a)},{ass_zaman(b)},Alt,,0,0,0,,{p}")
        baslangic[i] = zaman
        zaman += d
        parcalar.append(out)
    if eksik:
        print("Resmi bulunamayan sahneler (atlandı):", eksik)
    if len(eksik) > len(s["sahneler"]) * 0.2:
        sys.exit(f"Çok fazla eksik resim ({len(eksik)}) — video kalitesiz olur, durduruldu")

    liste = os.path.join(CIKTI, "liste.txt")
    open(liste, "w").writelines(f"file '{p}'\n" for p in parcalar)
    govde = os.path.join(CIKTI, "govde.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", govde)
    ass_yol = os.path.join(CIKTI, "alt.ass")
    open(ass_yol, "w", encoding="utf-8").write(
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        "Style: Alt,Inter,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,160,160,60,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ass) + "\n")
    sys.path.insert(0, KOK)
    import muzik
    bpm = {"tarih": 72, "dedektif": 64, "hikaye": 80}[tur]
    m = muzik.uret(sure(govde), os.path.join(CIKTI, "muzik.wav"), bpm=bpm, tohum=len(konu))
    ad = re.sub(r"[^A-Za-z0-9]+", "_", s["baslik"].translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")))[:50]
    son = os.path.join(CIKTI, f"Uzun_{ad}.mp4")
    calistir("-i", govde, "-i", m, "-filter_complex",
             f"[0:v]ass={ass_yol}[v];[1:a]volume=0.09[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,"
             f"alimiter=limit=0.95[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "22", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", son)
    toplam = sure(son)
    print(f"Hazır: {son} ({toplam / 60:.1f} dk)")

    # Kapak: ilk sahnenin resmi + 3 kelime
    kapak_yol = os.path.join(CIKTI, "kapak.jpg")
    ilk = next(iter(baslangic))
    kapak(os.path.join(CIKTI, f"k_{ilk:03d}.jpg"), s.get("kapak_yazi", s["baslik"][:20]), kapak_yol, tur)

    # Açıklama: kanca + bölümler + kaynaklar
    bolum = []
    for b in s.get("bolumler", []):
        t = baslangic.get(int(b.get("sahne", 0)))
        if t is not None:
            bolum.append(f"{int(t // 60):02d}:{int(t % 60):02d} {b['ad']}")
    if bolum and not bolum[0].startswith("00:00"):
        bolum.insert(0, "00:00 Giriş")
    aciklama = s.get("aciklama", "")
    if len(bolum) >= 3:
        aciklama += "\n\n📌 Bölümler\n" + "\n".join(bolum)
    if KAYNAKCA:
        aciklama += "\n\n🖼 Görseller (Wikimedia Commons, özgür lisans):\n" + "\n".join(KAYNAKCA[:40])
    aciklama += "\n\nAnlatım yapay zekâ seslendirmesidir; senaryo ve kurgu kanal ekibimize aittir."
    json.dump({"video": son, "kapak": kapak_yol, "baslik": s["baslik"], "aciklama": aciklama,
               "etiketler": s.get("etiketler", []), "tur": tur, "sure_dk": round(toplam / 60, 1)},
              open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if TOKEN:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", timeout=120,
                      data={"chat_id": CHAT, "caption": f"🖼 Kapak: {s['baslik']}"},
                      files={"photo": open(kapak_yol, "rb")})
        tg = os.path.join(CIKTI, "telegram.mp4")
        hk = int(44 * 8 * 1024 / max(toplam, 1)) - 100
        calistir("-i", son, "-vf", "scale=854:480", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{max(hk, 250)}k",
                 "-maxrate", f"{max(hk, 250)}k", "-bufsize", "2M", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", tg)
        with open(tg, "rb") as f:
            print(requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", timeout=900,
                                data={"chat_id": CHAT, "supports_streaming": "true",
                                      "caption": f"🎞 PİLOT (yayınlanmadı) [{tur}]: {s['baslik']} · {toplam / 60:.1f} dk"},
                                files={"video": f}).json().get("ok"))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 10, sys.argv[3] if len(sys.argv) > 3 else "tarih")
