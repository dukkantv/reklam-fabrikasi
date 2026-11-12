# "Eskiden Bursa'da Esnaf Olmak" — çizgi roman tarzı, anlatıcılı uzun video (yatay 16:9) — TAMAMEN ÜCRETSİZ
#   Senaryo: Gemini (ücretsiz anahtar) · Resim: Pollinations (ücretsiz, anahtarsız), yedek: Gemini resim
#   Ses: edge-tts (ücretsiz) · Montaj: ffmpeg (yavaş yakınlaşma + altyazı + kısık müzik)
# Kullanım: python belgesel.py "konu" [dakika]
import asyncio, json, os, re, subprocess, sys, time, urllib.parse, base64

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti", "belgesel")
GEMINI_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
TOKEN, CHAT = os.environ.get("TOKEN", "").strip(), os.environ.get("CHAT", "").strip()
SES = os.environ.get("BELGESEL_SES", "tr-TR-AhmetNeural")
W, H, FPS = 1920, 1080, 25

STIL = ("hand-drawn graphic novel comic illustration, clean confident ink outlines, flat muted warm colors with soft "
        "shading, nostalgic 1990s Turkey, cinematic wide composition, characters drawn with simple round heads and "
        "minimal faces (two small dot eyes, tiny mouth), consistent simple style, no text, no letters, no captions, "
        "no watermark")

SENARYO = """Sen Türkiye'de çok izlenen nostaljik YouTube belgesel-hikâyeleri yazan bir senaristsin.
Seri adı: "Eskiden Bursa'da Esnaf Olmak". Konu: {konu}
Toplam yaklaşık {dakika} dakika anlatım ({kelime} kelime civarı), tek bir anlatıcı ikinci tekil şahısla anlatır
("Yıl 1990. Bursa'dasın..."). İzleyici kendini o dönemin esnafı gibi hisseder.

KURALLAR
- Kurgusal bir hikâye; ama dönemin gündelik hayatı gerçekçi: mahalle, komşuluk, veresiye defteri, kasa, tüp gaz,
  ankesörlü telefon, enflasyon, zam haberleri, bayram alışverişi gibi. Kesin rakam (fiyat, maaş) VERME;
  "o zamanlar bir ekmek birkaç bin lira" gibi genel ve doğru kalan ifadeler kullan. Gerçek kişi, marka, siyasetçi YOK.
- İlk iki cümle güçlü bir kanca olsun (izleyici merak edip kalsın). Sonunda duygusal, düşündüren bir kapanış ve
  "Sen olsan ne yapardın? Yorumlara yaz." çağrısı.
- {sahne} sahneye böl. Her sahnede anlatım 2-3 cümle (yaklaşık 20-30 kelime), sade, sıcak, akıcı Türkçe.
- "gorsel": o sahnenin İngilizce tek kare çizim tarifi (mekân, kişiler, eylem, ışık). Ana karakteri her seferinde aynı
  tarif et: "the shopkeeper: a man in his 30s with short black hair and a thin mustache, grey knitted vest over a
  white shirt". Yazı, tabela, rakam isteme.

SADECE şu JSON:
{{"baslik": "merak uyandıran Türkçe YouTube başlığı", "aciklama": "2-3 cümlelik YouTube açıklaması",
  "sahneler": [{{"metin": "...", "gorsel": "..."}}]}}"""


def gemini_metin(istem):
    for model in ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]:
        for d in range(3):
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                                  f"?key={GEMINI_KEY}", timeout=240,
                                  json={"contents": [{"parts": [{"text": istem}]}],
                                        "generationConfig": {"temperature": 0.9, "responseMimeType": "application/json"}})
                if r.status_code == 200:
                    t = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(re.sub(r"^```(json)?|```$", "", t.strip()).strip())
                print(f"Gemini {model} {r.status_code}: {r.text[:150]}")
            except Exception as e:
                print(f"Gemini {model} hata: {str(e)[:150]}")
            time.sleep(8 * (d + 1))
    sys.exit("Senaryo yazılamadı")


def resim_pollinations(prompt, hedef, tohum):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           f"?width=1344&height=768&model=flux&seed={tohum}&nologo=true&private=true")
    r = requests.get(url, timeout=180)
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
        open(hedef, "wb").write(r.content)
        return True
    print(f"Pollinations {r.status_code} {r.headers.get('content-type')} {len(r.content)}")
    return False


def resim_gemini(prompt, hedef):
    for model in ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                          timeout=180, json={"contents": [{"parts": [{"text": prompt + " Landscape 16:9."}]}],
                                             "generationConfig": {"responseModalities": ["IMAGE"]}})
        if r.status_code == 200:
            for p in r.json()["candidates"][0]["content"]["parts"]:
                if "inlineData" in p:
                    open(hedef, "wb").write(base64.b64decode(p["inlineData"]["data"]))
                    return True
        print(f"Gemini resim {model} {r.status_code}: {r.text[:150]}")
    return False


def resim(prompt, hedef, tohum):
    if os.path.exists(hedef) and os.path.getsize(hedef) > 20000:
        return True
    for d in range(4):
        try:
            if resim_pollinations(prompt, hedef, tohum + d):
                return True
        except Exception as e:
            print("Pollinations hata:", str(e)[:120])
        time.sleep(10 * (d + 1))
    try:
        return resim_gemini(prompt, hedef)
    except Exception as e:
        print("Gemini resim hata:", str(e)[:120])
        return False


def calistir(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def sure(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).strip())


def ass_zaman(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def altyazi_parcala(metin, bas, son):
    """Uzun anlatımı ekranda 2 satırı geçmeyecek parçalara böler, süreyi kelime sayısına göre dağıtır."""
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


def main(konu, dakika=5):
    os.makedirs(CIKTI, exist_ok=True)
    sahne = max(8, int(dakika * 60 / 9))
    yol = os.path.join(CIKTI, "senaryo.json")
    if os.path.exists(yol):
        s = json.load(open(yol, encoding="utf-8"))
    else:
        s = gemini_metin(SENARYO.format(konu=konu, dakika=dakika, kelime=dakika * 130, sahne=sahne))
        json.dump(s, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(s["baslik"], "|", len(s["sahneler"]), "sahne")

    import edge_tts
    parcalar, ass, zaman, eksik = [], [], 0.0, []
    for i, sc in enumerate(s["sahneler"], 1):
        img = os.path.join(CIKTI, f"r_{i:03d}.jpg")
        if not resim(f"{STIL}. {sc['gorsel']}", img, 1000 + i):
            eksik.append(i)
            continue
        time.sleep(3)  # ücretsiz servise nazik ol
        mp3 = os.path.join(CIKTI, f"s_{i:03d}.mp3")
        if not os.path.exists(mp3):
            asyncio.run(edge_tts.Communicate(sc["metin"], SES, rate="-4%").save(mp3))
        d = sure(mp3) + 0.6
        out = os.path.join(CIKTI, f"p_{i:03d}.mp4")
        kare = int(d * FPS)
        yon = ["zoom+0.0006", "zoom+0.0006", "1.12-0.0006*on"][i % 3]  # çoğu yakınlaşma, arada uzaklaşma
        x = ["iw/2-(iw/zoom/2)", "iw/2-(iw/zoom/2)+on*0.3", "iw/2-(iw/zoom/2)-on*0.3"][i % 3]
        calistir("-loop", "1", "-i", img, "-i", mp3, "-filter_complex",
                 f"[0:v]scale=3840:-2,zoompan=z='min(max({yon},1.0),1.15)':x='{x}':y='ih/2-(ih/zoom/2)':"
                 f"d={kare}:s={W}x{H}:fps={FPS},format=yuv420p[v];[1:a]apad=pad_dur=0.6[a]",
                 "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "21", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", out)
        for a, b, p in altyazi_parcala(sc["metin"], zaman + 0.1, zaman + d - 0.5):
            ass.append(f"Dialogue: 0,{ass_zaman(a)},{ass_zaman(b)},Alt,,0,0,0,,{p}")
        zaman += d
        parcalar.append(out)
        print(f"Sahne {i}/{len(s['sahneler'])} hazır ({d:.1f} sn)")
    if eksik:
        print("Resmi üretilemeyen sahneler:", eksik)

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
        "Style: Alt,Inter,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,160,160,60,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ass) + "\n")
    sys.path.insert(0, KOK)
    import muzik
    m = muzik.uret(sure(govde), os.path.join(CIKTI, "muzik.wav"), bpm=84, tohum=11)
    ad = re.sub(r"[^A-Za-z0-9]+", "_", s["baslik"].translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")))[:50]
    son = os.path.join(CIKTI, f"Belgesel_{ad}.mp4")
    calistir("-i", govde, "-i", m, "-filter_complex",
             f"[0:v]ass={ass_yol}[v];[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,"
             f"alimiter=limit=0.95[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "22", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", son)
    print(f"Hazır: {son} ({sure(son) / 60:.1f} dk)")
    json.dump({"video": son, "baslik": s["baslik"], "aciklama": s.get("aciklama", "")},
              open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False)
    if TOKEN:
        tg = os.path.join(CIKTI, "telegram.mp4")
        hk = int(44 * 8 * 1024 / max(sure(son), 1)) - 130
        calistir("-i", son, "-vf", "scale=1280:720", "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{max(hk, 400)}k",
                 "-maxrate", f"{max(hk, 400)}k", "-bufsize", "3M", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", tg)
        with open(tg, "rb") as f:
            print(requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", timeout=600,
                                data={"chat_id": CHAT, "supports_streaming": "true",
                                      "caption": f"🎞 DENEME (yayınlanmadı): {s['baslik']} · {sure(son) / 60:.1f} dk\n"
                                                 f"Ücretsiz araçlarla: Gemini + Pollinations + edge-tts"},
                                files={"video": f}).json().get("ok"))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 5)
