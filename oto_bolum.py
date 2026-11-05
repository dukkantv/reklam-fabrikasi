# Dükkan TV · Tam otomatik çizgi film bölümü ("Levent'in Maceraları")
#
# Kullanım (GitHub Actions'taki "Otomatik Bölüm" düğmesi bunları çağırır):
#   python oto_bolum.py karakter                    -> Levent'in yeni kostümlü hâli + Cemo çizilir
#   python oto_bolum.py taslak eserim "konu"        -> senaryo (Gemini) + sahne resimleri (fal.ai) -> Telegram
#   python oto_bolum.py taslak eserim "" "3,7"      -> sadece 3. ve 7. sahne resmini yeniden çizer
#   python oto_bolum.py video eserim                -> resimleri hareketlendirir, seslendirir, altyazı + KASA ekler -> Telegram
#
# Gizli anahtarlar (GitHub > Settings > Secrets): FAL_KEY, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import asyncio, base64, json, math, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
KARAKTER_KLASOR = os.path.join(KOK, "karakterler")
CIKTI = os.path.join(KOK, "cikti")
FAL_KEY = os.environ.get("FAL_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
TOKEN = os.environ.get("TOKEN", "")
CHAT = os.environ.get("CHAT", "")

# ---- Ayarlar (kalite / fiyat buradan değişir) ----
RESIM_MODEL = "fal-ai/nano-banana-2/edit"        # referanslı çizim, 1K resim ~0.08 $
RESIM_MODEL_YAZIDAN = "fal-ai/nano-banana-2"     # referanssız çizim (Cemo ilk kez)
VIDEO_MODEL = os.environ.get("VIDEO_MODEL", "seedance")   # seedance (ucuz) | kling (daha pahalı)
VIDEO_COZUNURLUK = os.environ.get("VIDEO_COZUNURLUK", "720p")  # 720p | 1080p
SANIYE_UCRETI = {("seedance", "720p"): 0.0216, ("seedance", "1080p"): 0.049, ("kling", "720p"): 0.07, ("kling", "1080p"): 0.07}
RESIM_UCRETI = 0.08
DOLAR_TL = float(os.environ.get("DOLAR_TL", "50"))
AYNI_ANDA = 6

KARAKTERLER = json.load(open(os.path.join(KARAKTER_KLASOR, "karakterler.json"), encoding="utf-8"))
harcama = {"resim": 0, "video_sn": 0.0}


# ------------------------------------------------------------------ yardımcılar
def tg(metod, dosyalar=None, **veri):
    if not TOKEN:
        return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metod}", data={"chat_id": CHAT, **veri},
                          files=dosyalar, timeout=300)
        return r.json()
    except Exception as e:
        print("Telegram hatası:", e)


def tg_mesaj(metin):
    print(metin)
    for i in range(0, len(metin), 3900):
        tg("sendMessage", text=metin[i:i + 3900])


def tg_albumler(resimler, basliklar=None):
    """Resimleri 10'arlı albümler hâlinde gönderir."""
    for bas in range(0, len(resimler), 10):
        grup = resimler[bas:bas + 10]
        medya, dosyalar = [], {}
        for j, yol in enumerate(grup):
            ad = f"r{j}"
            dosyalar[ad] = open(yol, "rb")
            m = {"type": "photo", "media": f"attach://{ad}"}
            if basliklar:
                m["caption"] = basliklar[bas + j][:1000]
            medya.append(m)
        tg("sendMediaGroup", dosyalar=dosyalar, media=json.dumps(medya))


def veri_uri(yol, en=1024):
    """Resmi küçültüp fal.ai'ye gönderilecek base64 data URI'ye çevirir."""
    gecici = os.path.join(CIKTI, "ref_" + os.path.basename(yol) + ".jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", yol, "-vf", f"scale='min({en},iw)':-2", "-q:v", "3", gecici], check=True)
    return "data:image/jpeg;base64," + base64.b64encode(open(gecici, "rb").read()).decode()


def fal(model, girdi, deneme=2):
    """fal.ai kuyruğuna iş gönderir, bitene kadar bekler, sonucu döndürür."""
    if not FAL_KEY:
        sys.exit("FAL_KEY gizli anahtarı yok. GitHub > Settings > Secrets > Actions kısmına ekle.")
    bas = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
    for d in range(deneme + 1):
        try:
            is_ = requests.post(f"https://queue.fal.run/{model}", headers=bas, json=girdi, timeout=120)
            is_.raise_for_status()
            is_ = is_.json()
            bitis = time.time() + 900
            while time.time() < bitis:
                durum = requests.get(is_["status_url"], headers=bas, timeout=60).json()
                if durum.get("status") == "COMPLETED":
                    sonuc = requests.get(is_["response_url"], headers=bas, timeout=120)
                    sonuc.raise_for_status()
                    return sonuc.json()
                if durum.get("status") in ("FAILED", "ERROR"):
                    raise RuntimeError(str(durum)[:300])
                time.sleep(4)
            raise TimeoutError("fal.ai 15 dakikada bitirmedi")
        except Exception as e:
            print(f"fal.ai hatası ({model}, deneme {d + 1}): {str(e)[:300]}")
            if d == deneme:
                raise
            time.sleep(8)


def indir(url, hedef):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(hedef, "wb") as f:
            for parca in r.iter_content(1 << 16):
                f.write(parca)
    return hedef


def resim_ciz(prompt, referanslar, hedef, oran="9:16"):
    if referanslar:
        sonuc = fal(RESIM_MODEL, {"prompt": prompt, "image_urls": [veri_uri(r) for r in referanslar],
                                  "aspect_ratio": oran, "resolution": "1K", "output_format": "jpeg", "num_images": 1})
    else:
        sonuc = fal(RESIM_MODEL_YAZIDAN, {"prompt": prompt, "aspect_ratio": oran, "resolution": "1K",
                                          "output_format": "jpeg", "num_images": 1})
    harcama["resim"] += 1
    return indir(sonuc["images"][0]["url"], hedef)


def maliyet_ozeti():
    rs = harcama["resim"] * RESIM_UCRETI
    vs = harcama["video_sn"] * SANIYE_UCRETI[(VIDEO_MODEL, VIDEO_COZUNURLUK)]
    top = rs + vs
    return (f"💰 Bu çalışmanın tahmini maliyeti: {top:.2f} $ ≈ {top * DOLAR_TL:.0f} TL\n"
            f"   • {harcama['resim']} resim: {rs:.2f} $\n   • {harcama['video_sn']:.0f} sn video: {vs:.2f} $")


def sure(dosya):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", dosya]).strip())


# ------------------------------------------------------------------ 1) karakterler
def karakter(yenile=False):
    os.makedirs(CIKTI, exist_ok=True)
    stil = KARAKTERLER["stil"].replace(", vertical 9:16 frame", "")
    cizilen = []
    for kid, k in KARAKTERLER["karakterler"].items():
        hedef = os.path.join(KARAKTER_KLASOR, kid + ".jpg")
        if os.path.exists(hedef) and not yenile:
            print(f"{k['ad']} zaten hazır: {hedef}")
            continue
        refs = [os.path.join(KARAKTER_KLASOR, r) for r in k["kaynak"]]
        prompt = (f"{stil}. Character reference sheet on a plain light grey background: the same character shown "
                  f"full body front view on the left and a close-up of the face on the right. {k['kostum']} "
                  f"No text, no logos except the 'DTV' cube if mentioned.")
        resim_ciz(prompt, refs, hedef, oran="16:9")
        cizilen.append(hedef)
        print(f"{k['ad']} çizildi")
    if cizilen:
        tg_albumler(cizilen, [f"Karakter: {os.path.basename(c)}" for c in cizilen])
        tg_mesaj("🎨 Karakterler hazır. Beğenmezsen 'Otomatik Bölüm' > aşama: karakter-yenile ile tekrar çizdir.\n" + maliyet_ozeti())


# ------------------------------------------------------------------ 2) senaryo + sahne resimleri
def gemini(prompt):
    if not GEMINI_KEY:
        sys.exit("GEMINI_API_KEY gizli anahtarı yok.")
    for model in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
        for d in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0}},
                    timeout=180)
                if r.status_code in (429, 500, 503):
                    raise RuntimeError(f"{r.status_code} {r.text[:200]}")
                r.raise_for_status()
                metin = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                metin = re.sub(r"^```(json)?|```$", "", metin.strip()).strip()
                return json.loads(metin)
            except Exception as e:
                print(f"Gemini ({model}) deneme {d + 1}: {str(e)[:200]}")
                time.sleep(5 * (d + 1))
    sys.exit("Gemini senaryo yazamadı.")


def esnaf_bilgisi(klasor):
    kok = os.path.join(KOK, "reklamlar", klasor)
    b = json.load(open(os.path.join(kok, "bilgi.json"), encoding="utf-8"))
    oto = b.get("oto", {})
    kart = b.get("kart", {})
    temiz = lambda s: re.sub(r"<[^>]+>", " ", s or "").replace("  ", " ").strip()
    return kok, b, {
        "firma": oto.get("firma", temiz(kart.get("slogan1", klasor))),
        "sektor": oto.get("sektor", ""),
        "esnaf_adi": oto.get("esnaf_adi", ""),
        "esnaf_cinsiyet": oto.get("esnaf_cinsiyet", "erkek"),
        "esnaf_tarif": oto.get("esnaf_tarif", ""),
        "esnaf_foto": oto.get("esnaf_foto"),
        "dukkan_fotolari": oto.get("dukkan_fotolari", []),
        "logo": oto.get("logo", kart.get("logo")),
        "urunler": oto.get("urunler", ""),
        "adres": kart.get("adres", ""),
        "telefon": kart.get("telefon", ""),
        "slogan": temiz(kart.get("slogan2", "")),
        "notlar": oto.get("notlar", ""),
    }


SENARYO_ISTEMI = """Sen Türkiye'de çok izlenen, Pixar tarzı 3D yapay zekâ çizgi film skeçleri yazan komik bir senaristsin.
Dizinin adı "Levent'in Maceraları". Dikey (9:16) TikTok/Instagram bölümü yazacaksın, toplam ~90-100 saniye.

KARAKTERLER
- levent: {levent_rol} Görünüş: {levent_tarif}
- cemo: {cemo_rol} Görünüş: {cemo_tarif}
- esnaf: {esnaf_adi} — {firma} işletmesinin sahibi ({esnaf_cinsiyet}). {esnaf_tarif}
- erkek / kadin: gerekirse kısa görünen yan karakterler (müşteri, komşu vb.)

SPONSOR ESNAF (hikâyenin doğal bir parçası olmalı, reklam kokmamalı ama ürün ve dükkân net görünmeli)
- İşletme: {firma}  Sektör: {sektor}
- Ürün/hizmetler: {urunler}
- Adres: {adres}  Telefon: {telefon}  Slogan: {slogan}
- Notlar: {notlar}

BÖLÜM KONUSU: {konu}

KURALLAR
- 16 ile 20 arası sahne. Her sahne 4-8 saniye. Bir sahnede EN FAZLA 2 replik, sahne başına toplam en fazla 16 kelime.
- 1. sahne merak uyandıran güçlü bir kanca olsun (ilk 2 saniyede izleyiciyi yakala).
- 3 perde: dert/macera başlar -> yolları esnafa düşer (en az 5 sahne dükkânda, ürünler gösterilir, esnaf da konuşur) -> komik çözüm + başa dönen bir espriyle kapanış.
- Ekranda bir "KASA" (Levent ile Cemo'nun bütçesi, TL) olsun: ilk sahnede başlangıç değeri, para harcanan/kazanılan sahnelerde yeni değer. Değişmeyen sahnelerde kasa: null.
- Günlük, samimi İstanbul/Bursa Türkçesi; abartısız, herkesin güleceği temiz mizah. Siyaset, din alayı, +18, kumar, şiddet, sağlık iddiası, rakip kötüleme YOK. Fiyat/indirim uydurma YOK.
- Son sahnede Levent esnafın sloganını ya da adını doğal bir şekilde söylesin.
- "gorsel": İngilizce, tek bir kareyi tarif et: mekân, kamera açısı, karakterlerin ne yaptığı ve yüz ifadesi. Karakterleri sadece "Levent", "Cemo", "the shop owner" diye an; kıyafetlerini tarif etme (referans resimler eklenecek). Resimde yazı/altyazı olmasın; sadece dükkân tabelasında işletme adı yazabilir.
- "hareket": İngilizce, o 5 saniyelik klipte ne hareket edeceğini kısa yaz (ör. "Levent turns to camera and talks excitedly, Cemo yawns, slow push-in").
- "dukkan": sahne esnafın dükkânında/işinde geçiyorsa true.

SADECE şu JSON'u döndür:
{{"baslik": "kısa bölüm adı",
  "sahneler": [
    {{"karakterler": ["levent","cemo"], "dukkan": false,
      "gorsel": "...", "hareket": "...",
      "replikler": [{{"kim": "levent", "metin": "..."}}, {{"kim": "cemo", "metin": "..."}}],
      "kasa": 3000}}
  ]}}"""


def taslak(klasor, konu, yeniden=""):
    os.makedirs(CIKTI, exist_ok=True)
    kok, bilgi, e = esnaf_bilgisi(klasor)
    oto = os.path.join(kok, "oto")
    os.makedirs(oto, exist_ok=True)
    senaryo_yol = os.path.join(oto, "senaryo.json")
    kar = KARAKTERLER["karakterler"]
    for kid in kar:
        if not os.path.exists(os.path.join(KARAKTER_KLASOR, kid + ".jpg")):
            karakter()
            break

    if yeniden.strip() and os.path.exists(senaryo_yol):
        senaryo = json.load(open(senaryo_yol, encoding="utf-8"))
        cizilecek = [int(x) for x in re.findall(r"\d+", yeniden)]
    else:
        istem = SENARYO_ISTEMI.format(
            levent_rol=kar["levent"]["rol"], levent_tarif=kar["levent"]["tarif"],
            cemo_rol=kar["cemo"]["rol"], cemo_tarif=kar["cemo"]["tarif"],
            konu=konu or "Levent ile Cemo'nun başı derde girer, çözüm bu esnafta çıkar.", **e)
        senaryo = gemini(istem)
        json.dump(senaryo, open(senaryo_yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        for eski in os.listdir(oto):
            if eski.startswith("sahne_"):
                os.remove(os.path.join(oto, eski))
        cizilecek = list(range(1, len(senaryo["sahneler"]) + 1))

    stil = KARAKTERLER["stil"]

    def ciz(no):
        s = senaryo["sahneler"][no - 1]
        refs, kim = [], []
        for kid in s.get("karakterler", []):
            if kid in kar:
                refs.append(os.path.join(KARAKTER_KLASOR, kid + ".jpg"))
                kim.append(f"{kar[kid]['ad']} is {kar[kid]['tarif']} (see reference image {len(refs)})")
        if "esnaf" in s.get("karakterler", []) and e["esnaf_foto"]:
            refs.append(os.path.join(kok, e["esnaf_foto"]))
            kim.append(f"the shop owner looks like the person in reference image {len(refs)}, drawn as a Pixar-style 3D cartoon")
        elif "esnaf" in s.get("karakterler", []) and e["esnaf_tarif"]:
            kim.append(f"the shop owner is {e['esnaf_tarif']}")
        if s.get("dukkan"):
            for f in e["dukkan_fotolari"][:2] + ([e["logo"]] if e["logo"] else []):
                refs.append(os.path.join(kok, f))
            kim.append(f"the shop is '{e['firma']}'; use the shop/product photos and logo references for the real look of the "
                       f"place and its sign, redrawn in the same 3D animated style")
        prompt = (f"{stil}. {s['gorsel']} Characters: {'; '.join(kim)}. Keep every character exactly consistent with "
                  f"their reference (face, hair, outfit). No subtitles, no captions, no watermark.")
        hedef = os.path.join(oto, f"sahne_{no:02d}.jpg")
        resim_ciz(prompt, refs[:10], hedef)
        print(f"Sahne {no} çizildi")
        return hedef

    with ThreadPoolExecutor(AYNI_ANDA) as h:
        list(h.map(ciz, cizilecek))

    # Telegram'a hikâye taslağı
    satirlar = [f"📝 {senaryo.get('baslik', '')} — {len(senaryo['sahneler'])} sahne"]
    basliklar = []
    for i, s in enumerate(senaryo["sahneler"], 1):
        rep = " / ".join(f"{r['kim'].capitalize()}: {r['metin']}" for r in s.get("replikler", []))
        kasa = f" [KASA {s['kasa']:,} TL]".replace(",", ".") if s.get("kasa") is not None else ""
        satirlar.append(f"{i}. {rep}{kasa}")
        basliklar.append(f"{i}. {rep}{kasa}")
    tg_mesaj("\n".join(satirlar))
    tg_albumler([os.path.join(oto, f"sahne_{n:02d}.jpg") for n in cizilecek], [basliklar[n - 1] for n in cizilecek])
    sn = sum(tahmini_sure(s) for s in senaryo["sahneler"])
    tahmin = sn * SANIYE_UCRETI[(VIDEO_MODEL, VIDEO_COZUNURLUK)]
    tg_mesaj(maliyet_ozeti() + f"\n\n▶️ Beğendiysen 'Otomatik Bölüm' > aşama: video. Videolaştırma ≈ {tahmin:.2f} $ "
             f"(≈ {tahmin * DOLAR_TL:.0f} TL) tutar.\n🔁 Bazı sahneler kötü ise aşama: taslak, 'yeniden çiz' kutusuna "
             f"sahne numaralarını yaz (ör. 3,7).")


def tahmini_sure(s):
    kelime = sum(len(r["metin"].split()) for r in s.get("replikler", []))
    return max(4, min(10, math.ceil(kelime / 2.6 + 1.2)))


# ------------------------------------------------------------------ 3) video
def ses_ayari(kim):
    kar = KARAKTERLER["karakterler"]
    if kim in kar:
        return kar[kim]
    return KARAKTERLER["diger_sesler"].get(kim, KARAKTERLER["diger_sesler"]["erkek"])


async def seslendir(metin, kim, hedef):
    import edge_tts
    a = ses_ayari(kim)
    await edge_tts.Communicate(metin, a["ses"], rate=a.get("hiz", "+0%"), pitch=a.get("perde", "+0Hz")).save(hedef)


def klip_uret(resim, hareket, saniye, hedef):
    uri = veri_uri(resim, en=1280)
    if VIDEO_MODEL == "kling":
        saniye = 5 if saniye <= 5 else 10
        sonuc = fal("fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
                    {"prompt": hareket, "image_url": uri, "duration": str(saniye)})
    else:
        sonuc = fal("fal-ai/bytedance/seedance/v1/pro/fast/image-to-video",
                    {"prompt": hareket, "image_url": uri, "duration": str(saniye), "resolution": VIDEO_COZUNURLUK,
                     "aspect_ratio": "9:16"})
    harcama["video_sn"] += saniye
    return indir(sonuc["video"]["url"], hedef)


def ass_zaman(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def video(klasor):
    sys.path.insert(0, KOK)
    from bolum import calistir, resimden_video, VIDEO_AYAR, SES_AYAR

    os.makedirs(CIKTI, exist_ok=True)
    kok, bilgi, e = esnaf_bilgisi(klasor)
    oto = os.path.join(kok, "oto")
    senaryo = json.load(open(os.path.join(oto, "senaryo.json"), encoding="utf-8"))
    sahneler = senaryo["sahneler"]

    # a) Sesler: her sahnenin repliklerini seslendir, sahne süresini konuşmaya göre belirle
    plan = []
    for i, s in enumerate(sahneler, 1):
        t, parcalar = 0.35, []
        for j, r in enumerate(s.get("replikler", [])):
            yol = os.path.join(CIKTI, f"ses_{i:02d}_{j}.mp3")
            asyncio.run(seslendir(r["metin"], r["kim"], yol))
            d = sure(yol)
            parcalar.append((yol, t, t + d, r["metin"]))
            t += d + 0.25
        saniye = max(4, min(12, math.ceil(t + 0.3)))
        plan.append({"no": i, "saniye": saniye, "sesler": parcalar, "kasa": s.get("kasa")})
    toplam = sum(p["saniye"] for p in plan)
    print(f"Toplam süre ≈ {toplam} sn")

    # b) Klipler: tüm sahneleri aynı anda fal.ai'de hareketlendir
    def uret(p):
        hedef = os.path.join(CIKTI, f"klip_{p['no']:02d}.mp4")
        resim = os.path.join(oto, f"sahne_{p['no']:02d}.jpg")
        s = sahneler[p["no"] - 1]
        hareket = (s.get("hareket", "") + ". Characters' mouths move naturally while talking. Pixar-style 3D animation, "
                   "smooth, no text.")
        klip_uret(resim, hareket, p["saniye"], hedef)
        print(f"Klip {p['no']} hazır")
        return hedef

    with ThreadPoolExecutor(AYNI_ANDA) as h:
        klipler = list(h.map(uret, plan))

    # c) Her sahne: klibi 1080x1920'ye oturt, süreye kes, seslerini ekle
    govde_parcalari, ass_satirlari, zaman, son_kasa = [], [], 0.0, None
    for p, klip in zip(plan, klipler):
        cikis = os.path.join(CIKTI, f"sahne_{p['no']:02d}.mp4")
        d = p["saniye"]
        girdiler = ["-i", klip]
        for yol, bas, _, _ in p["sesler"]:
            girdiler += ["-i", yol]
        filtre = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30,"
                  f"tpad=stop_mode=clone:stop_duration=12,trim=duration={d}[v]")
        if p["sesler"]:
            sesler = []
            for k, (_, bas, _, _) in enumerate(p["sesler"]):
                filtre += (f";[{k + 1}:a]aresample=44100,aformat=channel_layouts=stereo,"
                           f"adelay=delays={int(bas * 1000)}:all=1[s{k}]")
                sesler.append(f"[s{k}]")
            filtre += f";{''.join(sesler)}amix=inputs={len(sesler)}:normalize=0,apad,atrim=duration={d}[a]"
            calistir(*girdiler, "-filter_complex", filtre, "-map", "[v]", "-map", "[a]", "-t", str(d),
                     *VIDEO_AYAR, *SES_AYAR, cikis)
        else:
            calistir(*girdiler, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", filtre,
                     "-map", "[v]", "-map", f"{len(girdiler) // 2}:a", "-t", str(d), *VIDEO_AYAR, *SES_AYAR, cikis)
        for _, bas, bit, metin in p["sesler"]:
            ass_satirlari.append(f"Dialogue: 0,{ass_zaman(zaman + bas)},{ass_zaman(zaman + bit)},Alt,,0,0,0,,{metin}")
        if p["kasa"] is not None:
            son_kasa = p["kasa"]
        if son_kasa is not None:
            yazi = f"KASA: {son_kasa:,} TL".replace(",", ".")
            ass_satirlari.append(f"Dialogue: 1,{ass_zaman(zaman)},{ass_zaman(zaman + d)},Kasa,,0,0,0,,{yazi}")
        zaman += d
        govde_parcalari.append(cikis)

    # d) Gövdeyi birleştir + altyazı ve KASA yaz
    liste = os.path.join(CIKTI, "govde.txt")
    open(liste, "w").writelines(f"file '{p}'\n" for p in govde_parcalari)
    govde = os.path.join(CIKTI, "govde.mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", govde)
    ass = os.path.join(CIKTI, "altyazi.ass")
    open(ass, "w", encoding="utf-8").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Alt,Inter,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,2,70,70,360,1\n"
        "Style: Kasa,Inter,54,&H00FFFFFF,&H00FFFFFF,&H003130D6,&H003130D6,-1,0,0,0,100,100,0,0,3,14,0,9,40,50,170,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(ass_satirlari) + "\n")
    govde_yazili = os.path.join(CIKTI, "govde_yazili.mp4")
    calistir("-i", govde, "-vf", f"ass={ass}", *VIDEO_AYAR, "-c:a", "copy", govde_yazili)

    # e) Başlık kartı + gövde + esnaf bilgi kartı
    renk = bilgi.get("renk", "#e3121b")
    baslik_png = os.path.join(CIKTI, "baslik.png")
    subprocess.run(["node", os.path.join(KOK, "kart.js"),
                    f"<span>LEVENT'İN MACERALARI</span>{senaryo.get('baslik', '')}", baslik_png, "baslik", renk], check=True)
    baslik = os.path.join(CIKTI, "baslik.mp4")
    resimden_video(baslik_png, 1.8, baslik)
    parcalar = [baslik, govde_yazili]
    if bilgi.get("kart"):
        sessiz = os.path.join(CIKTI, "bilgi_sessiz.mp4")
        subprocess.run(["node", os.path.join(KOK, "uret.js"), klasor], check=True,
                       env={**os.environ, "KARE_BAS": "480", "KARE_BIT": "690", "CIKTI": sessiz})
        bilgi_mp4 = os.path.join(CIKTI, "bilgi.mp4")
        calistir("-i", sessiz, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                 "-shortest", *VIDEO_AYAR, *SES_AYAR, bilgi_mp4)
        parcalar.append(bilgi_mp4)
    liste2 = os.path.join(CIKTI, "son.txt")
    open(liste2, "w").writelines(f"file '{p}'\n" for p in parcalar)
    ad = re.sub(r"[^A-Za-z0-9_]+", "_", f"Levent_{klasor}_{senaryo.get('baslik', 'bolum')}".translate(
        str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")))[:60]
    son = os.path.join(CIKTI, ad + ".mp4")
    calistir("-f", "concat", "-safe", "0", "-i", liste2, "-c", "copy", "-movflags", "+faststart", son)
    print(f"Bölüm hazır: {son} ({sure(son):.0f} sn)")

    if TOKEN:
        with open(son, "rb") as f:
            tg("sendVideo", dosyalar={"video": f}, supports_streaming="true",
               caption=f"🎬 Levent'in Maceraları: {senaryo.get('baslik', '')} ({sure(son):.0f} sn)")
        tg_mesaj(maliyet_ozeti())


if __name__ == "__main__":
    komut = sys.argv[1]
    if komut == "karakter":
        karakter(yenile="yenile" in sys.argv[2:])
    elif komut == "taslak":
        taslak(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "", sys.argv[4] if len(sys.argv) > 4 else "")
    elif komut == "video":
        video(sys.argv[2])
    else:
        sys.exit("Komut: karakter | taslak | video")
