# -*- coding: utf-8 -*-
"""Başlık + etiket + kapak (thumbnail) iyileştirici. Her video yayın kuyruğuna girerken (yt_kuyruk.ekle) çalışır.

27 Kas 2026 (Levent: "her video için mükemmel kapak yap, 2-3 kelime veya sembol ile, başlıkları özenle seç,
rakiplerden iyi olsun"). Kurallar o gün yapılan rakip araştırmasından çıkarıldı:

  RAKİP ARAŞTIRMASI (YouTube Türkiye arama sonuçları, 27.11.2026)
  • Gizem/tarih: "ANTARKTİKA NEDEN BU KADAR KORUNUYOR?" (1,1 Mn), "SIRRI ÇÖZÜLEMEYEN 10 AKILALMAZ GİZEM" (792 B),
    "Doğru Bilinen Ama Yanlış 18 Bilgi" (1,3 Mn), "Nesli Tükendiği İçin ŞANSLI Olduğumuz 10 Hayvan" (8,3 Mn).
    Kapaklar: tek odak resim + 1-2 DEV kelime (AÇIKLANAMIYOR, YANLIŞ!, EN BÜYÜK GİZEMLER), beyaz/sarı, kalın
    siyah kontur, kırmızı vurgu (ok, uyarı üçgeni, kutu).
  • Ne Olur: "Osmanlı Yıkılmasaydı? #shorts" (96 B), "Yavuz Sultan Selim Daha Uzun Yaşasaydı?" (286 B) →
    kısa, tek soru, "-saydı?" kalıbı.
  • Hikâye: "Babası Ona Köyden Gelin Seçti… Kızı Küçümsedi, Kim Olduğunu Öğrenince Pişman Oldu!" →
    olay + üç nokta + ters köşe; kapakta tırnaklı tek cümle, kırmızı/sarı vurgulu kelime.
  • Dedektif: "Ne Kadar İyi Bir Dedektifsin! Olayı Çöz ve Katili Bul" (287 B), kapak "HANGİ BÜYÜKANNE
    TEHLİKELİ?" (889 B) → kapakta soru + şüpheliler, "KATİL KİM?" kırmızı.
  • Top yarışı: "100 Countries Marble Race" (11,8 Mn), "16 Countries, Only 1 Winner!" → sayı + "sadece 1 kazanır".
  • Para/YouTube eğitimi: "YAPAY ZEKA İLE GÜNDE 2 SAAT ÇALIŞARAK PARA KAZAN! (5 FARKLI YÖNTEM)" (149 B) →
    aranan ifade başta, sayı, yıl (2026), parantezli vaat.
  Bizim fark: kapakta EN FAZLA 3 kelime (rakipler kalabalık), dev yazı telefonda bile okunur, her kanalın sabit
  renk dili (izleyici kanalı kapaktan tanır), sembol rozeti (?, !, %1, sayı) ve dürüst başlık (kapaktaki vaat
  videoda var). Etiketler YouTube arama önerilerinden (insanların gerçekten yazdığı aramalar) seçilir.
"""
import json
import os
import re
import subprocess
import tempfile
import time

KOK = os.path.dirname(os.path.abspath(__file__))
FONT_KALIN = os.path.join(KOK, "yeni_format", "fontlar", "InterDisplay-Black.otf")
FONT_YEDEK = os.path.join(KOK, "yeni_format", "fontlar", "DejaVuSans-Bold.ttf")
GEMINI_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())

# ---------- Kanal kimliği: kapak renkleri ----------
KANAL = {
    "gizlitarih": {"ad": "Gizli Tarih", "vurgu": (255, 196, 0), "kutu": (200, 30, 30),
                   "konu": "tarih belgeselleri, dünyanın gizemleri, 'Ne Olur?' senaryoları, doğru bilinen yanlışlar, ilginç hayvanlar"},
    "kasakurgu": {"ad": "Kasa Kurgu", "vurgu": (255, 214, 0), "kutu": (215, 25, 35),
                  "konu": "'Katil Kim?' dedektif bulmaca vakaları ve '500 TL ile 50.000 TL' birikim dizisi"},
    "dramabite": {"ad": "Drama Bite", "vurgu": (255, 205, 60), "kutu": (190, 20, 60),
                  "konu": "kısa duygusal aile/hayat hikâyeleri, mesajlaşma hikâyeleri, ders veren hikâyeler"},
    "dukkantv": {"ad": "Dükkan TV", "vurgu": (0, 230, 255), "kutu": (255, 60, 120),
                 "konu": "Levent & Cemo mizah skeçleri ve yapay zekâ, YouTube, internetten para kazanma, telefon eğitim videoları"},
    "ilturnuva": {"ad": "81 İl Turnuvası", "vurgu": (255, 214, 0), "kutu": (227, 10, 23),
                  "konu": "Türkiye'nin 81 ili toplar hâlinde fizik oyununda yarışıyor (şehirler turnuvası)"},
}

# Neon kapak (Shorts) renkleri: Dükkan TV neon tarzı (27 Kas 2026, Levent: "kısa videolarda neon tarzı olsun")
NEON = {"gizlitarih": (255, 190, 40), "kasakurgu": (255, 48, 72), "dramabite": (255, 70, 160),
        "dukkantv": (0, 229, 255), "ilturnuva": (60, 235, 140)}

# ---------- Etiket havuzu: YouTube arama önerilerinden (27.11.2026, hl=tr gl=tr) ----------
HAVUZ = {
    "gizlitarih": [
        "tarih belgeseli", "osmanlı tarihi", "osmanlı tarihi belgesel", "osmanlı padişahları", "kanuni sultan süleyman",
        "fatih sultan mehmet", "yavuz sultan selim", "tarihin gizemleri", "tarihin gizli sırları", "tarihte bugün",
        "tarihte bilinmeyen gerçekler", "dünyanın çözülemeyen gizemleri", "çözülemeyen gizemler", "dünyanın en gizemli yerleri",
        "dünyanın en gizemli olayları", "gizemli olaylar", "piramitlerin sırrı", "piramitlerin gizemi", "bilinmeyen gerçekler",
        "ilginç bilgiler", "ilginç bilgiler shorts", "doğru bilinen yanlışlar", "dünyanın en ilginç hayvanları",
        "en ilginç hayvanlar", "ilginç bilgiler hayvanlar hakkında", "belgesel türkçe", "ne olurdu", "olsaydı ne olurdu",
        "ya olsaydı", "uzayda bilinmeyen gerçekler", "dünyanın bilinmeyen gerçekleri", "gizemli yerler"],
    "kasakurgu": [
        "katil kim", "katil kim oyunu", "dedektif", "dedektif vakaları", "dedektif oyunu", "polisiye", "polisiye hikaye",
        "gizem çözme", "gizemli dosyalar", "cinayet dosyaları", "cinayet hikayeleri", "gerçek suç hikayeleri", "suç hikayesi",
        "zeka sorusu", "zeka soruları", "mantık sorusu", "bilmece", "bilmeceler ve cevapları", "katili bul",
        "500 tl ile bir gün", "para biriktirme", "para biriktirme yöntemleri", "para biriktirme taktikleri",
        "zengin olmak", "birikim", "kurgu hikaye"],
    "dramabite": [
        "duygusal hikayeler", "duygusal hikaye", "duygusal hikayeler shorts", "kısa hikayeler", "hikaye", "hayat hikayesi",
        "gerçek hayat hikayeleri", "ibretlik hikayeler", "ders veren hikayeler", "hayata dair ders veren hikayeler",
        "ağlatan hikayeler", "ağlatan hayat hikayeleri", "dramatik hikayeler", "dramatik hayat hikayeleri", "aile hikayeleri",
        "anne hikayesi", "fedakar anne hikayesi", "baba hikayesi", "pişmanlık", "mesajlaşma hikayeleri", "sesli hikaye dinle",
        "duygusal hikayeler dinle", "itiraflar"],
    "dukkantv": [
        "yapay zeka", "yapay zeka ile para kazanma", "yapay zeka ile para kazanma 2026", "yapay zeka video oluşturma",
        "yapay zeka videoları", "chatgpt nasıl kullanılır", "claude nasıl kullanılır", "claude kullanımı",
        "youtube kanalı nasıl açılır", "youtube kanalı nasıl açılır 2026", "youtube para kazanma", "youtube para kazanma şartları",
        "youtube shorts para kazanma", "youtube shorts izlenme arttırma", "internetten para kazanma", "evden para kazanma",
        "tiktok para kazanma", "telefon hızlandırma", "telefon ipuçları", "dolandırıcılık", "komik videolar",
        "komik videolar shorts", "komedi", "skeç", "kısa skeç", "levent ve cemo", "çizgi film", "esnaf"],
    "ilturnuva": [
        "81 il", "81 il turnuvası", "şehirler savaşıyor", "türkiye şehirler savaşı", "şehirler savaşı", "türkiye illeri",
        "türkiye illeri savaşıyor", "top yarışı", "top yarışı ülkeler", "top yarışı videoları", "marble race",
        "marble race countries", "marble race elimination", "ball race", "ball race 3d", "il plakaları", "81 il plakaları",
        "fizik oyunu", "istanbul vs ankara", "istanbul vs izmir", "hangi il kazanır", "şehir takımları", "simülasyon"],
}
SABIT = {  # her videoda olan marka/ana etiketler
    "gizlitarih": ["gizli tarih", "ilginç bilgiler"],
    "kasakurgu": ["kasa kurgu", "katil kim"],
    "dramabite": ["drama bite", "duygusal hikayeler"],
    "dukkantv": ["dükkan tv"],
    "ilturnuva": ["81 il turnuvası", "81 il"],
}
# Başlıkta geçiyorsa yeni başlıkta da AYNEN kalmalı (oynatma listesi kuralları ve seriler buna bakıyor)
KORU = ["Katil Kim", "500 TL", "Ne Olur", "Levent", "Cemo", "81 İl", "Drama Bite", "Gizli Tarih", "Dükkan TV",
        "BÜYÜK FİNAL", "Final"]
SEMBOLLER = ("soru", "unlem", "ok", "carpi", "rozet", "yok")


# ---------- Türkçe yardımcılar ----------
def ust(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def alt(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def _kokler(metin):
    return {k[:5] for k in re.findall(r"[a-zçğıöşü0-9]+", alt(metin)) if len(k) >= 3}


# ---------- Etiketler ----------
def etiket_sec(kanal, baslik, aciklama="", mevcut=(), ek=(), sinir=450):
    """Mevcut + yapay zekâ önerisi + havuzdan başlığa en yakın aramalar + marka etiketleri; YouTube 500 karakter sınırı."""
    kok = _kokler(baslik + " " + aciklama[:400])
    puanli = []
    for i, e in enumerate(HAVUZ.get(kanal, [])):
        ek_kok = _kokler(e)
        ortak = len(ek_kok & kok)
        if ortak:
            puanli.append((-ortak / len(ek_kok), i, e))
    puanli.sort()
    aday = list(mevcut) + list(ek) + [e for _, _, e in puanli[:8]] + SABIT.get(kanal, [])
    aday += HAVUZ.get(kanal, [])[:4]   # en genel aramalar (kanal konusunu YouTube'a anlatır)
    cikti, gorulen, toplam = [], set(), 0
    for e in aday:
        e = re.sub(r"\s+", " ", str(e).replace("#", "").replace(",", " ")).strip()
        if not e or len(e) > 60 or alt(e) in gorulen:
            continue
        uz = len(e) + (2 if " " in e else 0) + 1   # YouTube boşluklu etiketi tırnakla sayar
        if toplam + uz > sinir:
            continue
        gorulen.add(alt(e))
        cikti.append(e)
        toplam += uz
    return cikti


# ---------- Gemini: başlık + kapak yazısı ----------
def _gemini(istem):
    if not GEMINI_KEY:
        return None
    import requests
    for model in ("gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"):
        for d in range(2):
            try:
                r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}",
                                  json={"contents": [{"parts": [{"text": istem}]}],
                                        "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"}},
                                  timeout=90)
                if r.status_code == 200:
                    t = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(re.sub(r"^```(json)?|```$", "", t.strip()).strip())
                print(f"kapak_seo: Gemini {model} {r.status_code}: {r.text[:100]}")
                if r.status_code in (429, 403):
                    break
            except Exception as e:
                print(f"kapak_seo: Gemini {model} hata: {str(e)[:100]}")
            time.sleep(4)
    return None


ISTEM = """Sen Türkiye'nin en iyi YouTube başlık ve kapak (thumbnail) uzmanısın. Kanal: {ad} ({konu}).
Video türü: {tur}. Mevcut başlık: "{baslik}"
Video açıklaması (özet): "{aciklama}"

Rakip araştırmasından çıkan kurallar:
- Başlık: insanların arama kutusuna yazdığı ifade BAŞTA; merak boşluğu bırak ama yalan vaat etme (videoda olmayanı yazma).
- Liste ise sayı kullan ("5 Yanlış", "7 Yol"); senaryo ise "...saydı?" / "Ne Olur?" sorusu; hikâyede olay + "…" + ters köşe.
- Uzunluk 35–65 karakter (Shorts'ta sonuna " #shorts" eklenecek, sen ekleme). En fazla 1 emoji, sonda.
- Başlıktaki seri ifadeleri AYNEN kalsın: {koru}
- Tamamı büyük harf yazma; yalnızca 1 kelime büyük harf olabilir.
Kapak yazısı: 1–3 kelime, en fazla 18 harf, BÜYÜK HARF, başlığı tekrar etmesin, tamamlasın (merak kancası:
"KİM YAPTI?", "YASAK ODA", "%1 ÇÖZER", "SON MESAJ", "BU YANLIŞ!"). Sembol: soru | unlem | ok | carpi | rozet | yok.
Rozet seçersen rozet_yazi en fazla 4 karakter ("%1", "7", "1730", "81").

SADECE JSON: {{"baslik": "...", "kapak_yazi": "...", "vurgu": "kapak yazısından tek kelime", "sembol": "...",
"rozet_yazi": "", "etiketler": ["insanların aradığı 6-10 Türkçe ifade, küçük harf"]}}"""


def baslik_gecerli(yeni, eski, kisa):
    if not yeni or not (20 <= len(yeni) <= 100):
        return False
    for k in KORU:
        if alt(k) in alt(eski) and alt(k) not in alt(yeni):
            return False
    for sayi in re.findall(r"\d+", eski):   # gün/bölüm/sayılar korunur (ör. "Gün 12", "%1", "1730")
        if sayi not in yeni:
            return False
    if sum(1 for c in yeni if c.isupper()) > 0.5 * sum(1 for c in yeni if c.isalpha()):
        return False
    return True


def kural_paketi(kanal, baslik):
    """Gemini yoksa: başlıktan kapak yazısı ve sembol çıkarır (kurala dayalı)."""
    b = re.sub(r"#\w+", "", baslik)
    b = re.sub(r"[^\w\s%?!.,:…'’\"“”-]", "", b).strip()
    a = alt(b)
    if "katil kim" in a:
        return {"kapak_yazi": "KATİL KİM?", "vurgu": "KATİL", "sembol": "rozet" if "%1" in b else "soru", "rozet_yazi": "%1" if "%1" in b else ""}
    if "ne olur" in a or "saydı" in a or "seydi" in a:
        bos = {"dünyada", "dünyadaki", "dünya", "bir", "gün", "hiç", "bütün", "tüm", "eğer", "birden", "aniden", "herkes", "her"}
        kel = [w for w in re.split(r"\s+", re.sub(r"(?i)ne olur(du)?\??|[?!.,…:]", " ", b)) if w and alt(w) not in bos]
        sec = kel[-2:] if kel else ["NE", "OLUR"]
        return {"kapak_yazi": ust(" ".join(sec)) + "?", "vurgu": ust(sec[0]), "sembol": "soru"}
    if "hangisi" in a or "tur atlar" in a or "final" in a:
        return {"kapak_yazi": "KİM KAZANIR?" if "final" not in a else "BÜYÜK FİNAL", "vurgu": "KAZANIR?" if "final" not in a else "FİNAL", "sembol": "rozet", "rozet_yazi": "81"}
    sayi = re.search(r"\b(\d{1,3})\b", b)
    alinti = re.search(r"[“\"']([^”\"']{3,18})[”\"']", b)
    if alinti:   # başlıkta tırnaklı söz varsa kapağın kendisi o olur ("GELEMİYORUM")
        s_ = ust(alinti.group(1).strip())
        return {"kapak_yazi": f"“{s_}”", "vurgu": "", "sembol": "unlem"}
    m = re.search(r"(?:(\w+)\s+)?(\d{1,3})\s+(\w+)", b)
    if m:   # "Bilmediğin 5 Şey", "7 Yol" → kapakta sayılı ifade
        s_ = ust(" ".join(x for x in m.groups() if x))
        if len(s_) > 18:
            s_ = ust(f"{m.group(2)} {m.group(3)}")
        return {"kapak_yazi": s_, "vurgu": ust(m.group(3)), "sembol": "unlem"}
    parca, toplam = [], 0
    for w in re.split(r"[:…?!.,–—-]", b)[0].replace("“", "").replace("”", "").split():
        if len(parca) == 3 or toplam + len(w) > 18:
            break
        parca.append(w)
        toplam += len(w) + 1
    yazi = ust(" ".join(parca)) or ust(b.split()[0])[:18]
    return {"kapak_yazi": yazi, "vurgu": ust(parca[-1]) if parca else "", "sembol": "rozet" if sayi else "unlem",
            "rozet_yazi": sayi.group(1) if sayi else ""}


def paket(kanal, baslik, aciklama="", kisa=True, mevcut_etiketler=()):
    """Döndürür: {baslik, kapak_yazi, vurgu, sembol, rozet_yazi, etiketler}"""
    k = KANAL.get(kanal, {"ad": kanal, "konu": ""})
    temiz = re.sub(r"\s*#shorts\b", "", baslik, flags=re.I).strip()
    sonuc = {"baslik": baslik}
    g = _gemini(ISTEM.format(ad=k["ad"], konu=k["konu"], tur="YouTube Shorts (dikey, 1 dk altı)" if kisa else "uzun YouTube videosu",
                             baslik=temiz, aciklama=re.sub(r"\s+", " ", aciklama)[:600],
                             koru=", ".join(x for x in KORU if alt(x) in alt(temiz)) or "(yok)"))
    if isinstance(g, dict):
        yeni = re.sub(r"\s*#shorts\b", "", str(g.get("baslik", "")), flags=re.I).strip().strip('"')
        if kisa and yeni:
            yeni = (yeni[:90] + " #shorts") if "#shorts" in baslik.lower() else yeni[:100]
        if baslik_gecerli(yeni, baslik, kisa):
            sonuc["baslik"] = yeni
        else:
            print(f"kapak_seo: önerilen başlık kurallara uymadı, eski kaldı: {yeni!r}")
        yazi = ust(str(g.get("kapak_yazi", "")).strip())
        if 2 <= len(yazi) <= 22 and len(yazi.split()) <= 3:
            sonuc.update(kapak_yazi=yazi, vurgu=ust(str(g.get("vurgu", ""))),
                         sembol=g.get("sembol") if g.get("sembol") in SEMBOLLER else "yok",
                         rozet_yazi=str(g.get("rozet_yazi") or "")[:4])
        ek = [str(e) for e in (g.get("etiketler") or []) if isinstance(e, str)][:10]
    else:
        ek = []
    if "kapak_yazi" not in sonuc:
        sonuc.update(kural_paketi(kanal, baslik))
    sonuc["etiketler"] = etiket_sec(kanal, sonuc["baslik"], aciklama, mevcut_etiketler, ek)
    return sonuc


def _paketler():
    """Pillow/numpy yüklü olmayan iş akışlarında (ör. kuyruga-ekle) sessizce kurar."""
    try:
        import numpy, PIL  # noqa: F401
    except ImportError:
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow", "numpy"], timeout=300)


# ---------- Videodan en iyi kare ----------
def kare_sec(video, adet=9):
    """Videonun %12–%85 arasından kareler alır; en renkli + en net + en aydınlık kareyi seçer."""
    _paketler()
    import numpy as np
    from PIL import Image
    try:
        sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                    capture_output=True, text=True, timeout=60).stdout.strip())
    except Exception:
        sure = 30.0
    gecici = tempfile.mkdtemp()
    en_iyi, en_puan = None, -1
    for i in range(adet):
        t = sure * (0.12 + 0.73 * i / max(1, adet - 1))
        yol = os.path.join(gecici, f"k{i}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "2", yol],
                       timeout=120)
        if not os.path.exists(yol):
            continue
        im = np.asarray(Image.open(yol).convert("RGB").resize((320, 320)), dtype=np.float32)
        r, g, b = im[..., 0], im[..., 1], im[..., 2]
        rg, yb = r - g, 0.5 * (r + g) - b
        renk = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
        gri = im.mean(axis=2)
        net = np.abs(np.diff(gri, axis=0)).mean() + np.abs(np.diff(gri, axis=1)).mean()
        isik = gri.mean()
        puan = renk * (1 + net / 20) * (0.4 if isik < 45 else 1.0) * (0.6 if isik > 225 else 1.0)
        if puan > en_puan:
            en_iyi, en_puan = yol, puan
    return en_iyi


# ---------- Kapak çizimi ----------
def _font(boy):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_KALIN, boy)
    except Exception:
        return ImageFont.truetype(FONT_YEDEK, boy)


def _satirla(yazi, dikey=False):
    k = yazi.split()[:4]
    if dikey:   # dikeyde her kelime ayrı satır: yazı en büyük hâlini alır (en fazla 3 satır)
        return k if len(k) <= 3 else [" ".join(k[:2])] + k[2:]
    if len(k) <= 1 or len(" ".join(k)) <= 11:
        return [" ".join(k)]
    # en dengeli iki satır
    en = min(range(1, len(k)), key=lambda i: abs(len(" ".join(k[:i])) - len(" ".join(k[i:]))))
    return [" ".join(k[:en]), " ".join(k[en:])]


def ciz(arka, yazi, hedef, kanal="gizlitarih", dikey=False, vurgu="", sembol="yok", rozet_yazi=""):
    """1280x720 (uzun) ya da 1080x1920 (Shorts) kapak. Dikeyde yazı 4:5 kırpmaya (ana sayfa) dayanıklı ortada."""
    _paketler()
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    W, H = (1080, 1920) if dikey else (1280, 720)
    renk = KANAL.get(kanal, KANAL["gizlitarih"])
    im = Image.open(arka).convert("RGB")
    o = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * o + 1), int(im.height * o + 1)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x0, y0, x0 + W, y0 + H))
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = ImageEnhance.Color(im).enhance(1.35)
    im = ImageEnhance.Sharpness(im).enhance(1.4)
    # Kenar karartma (vinyet) + yazı bölgesine koyu geçiş: yazı her zeminde okunur
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    maske = np.clip((d - 0.55) * 0.9, 0, 0.55)
    if dikey:
        bant = np.exp(-((yy - H * 0.60) / (H * 0.16)) ** 2) * 0.55
    else:
        bant = np.clip((yy - H * 0.38) / (H * 0.62), 0, 1) ** 1.3 * 0.75
    karanlik = np.clip(maske + bant, 0, 0.8)
    arr = np.asarray(im, dtype=np.float32) * (1 - karanlik[..., None])
    im = Image.fromarray(arr.clip(0, 255).astype("uint8"))
    ciz_ = ImageDraw.Draw(im)

    satirlar = _satirla(ust(yazi.strip()), dikey)
    gen_sinir = W * (0.90 if dikey else 0.86)
    yuk_sinir = H * (0.34 if dikey else 0.50)
    boy = 400
    while boy > 40:
        f = _font(boy)
        genis = max(ciz_.textlength(s, font=f) for s in satirlar)
        yuk = len(satirlar) * boy * 1.02
        if genis <= gen_sinir and yuk <= yuk_sinir:
            break
        boy -= 6
    f = _font(boy)
    kontur = max(4, int(boy * 0.085))
    satir_y = boy * 1.02
    toplam = satir_y * len(satirlar)
    ust_y = H * 0.60 - toplam / 2 if dikey else H - toplam - H * 0.07
    vurgu_u = ust(vurgu.strip()) if vurgu else ""
    for i, s in enumerate(satirlar):
        g = ciz_.textlength(s, font=f)
        x = (W - g) / 2
        y = ust_y + i * satir_y
        vurgulu = vurgu_u and vurgu_u in s.split() and len(satirlar) > 1
        if vurgulu and len(s.split()) == 1:
            # Tek kelimelik vurgulu satır: kırmızı kutu içinde beyaz (rakiplerde en çok tıklanan biçim)
            pad = boy * 0.14
            kutu = [x - pad, y + boy * 0.10, x + g + pad, y + boy * 1.05]
            ciz_.rounded_rectangle([kutu[0] + 8, kutu[1] + 10, kutu[2] + 8, kutu[3] + 10], radius=int(boy * .12), fill=(0, 0, 0))
            ciz_.rounded_rectangle(kutu, radius=int(boy * .12), fill=renk["kutu"])
            ciz_.text((x, y), s, font=f, fill=(255, 255, 255))
            continue
        # gölge + kalın siyah kontur
        ciz_.text((x + boy * .05, y + boy * .06), s, font=f, fill=(0, 0, 0), stroke_width=kontur, stroke_fill=(0, 0, 0))
        if vurgu_u and vurgu_u in s.split():
            # satır içinde vurgulu kelime sarı, diğerleri beyaz
            xx_ = x
            for j, kel in enumerate(s.split()):
                parca = kel + (" " if j < len(s.split()) - 1 else "")
                ciz_.text((xx_, y), kel, font=f, fill=renk["vurgu"] if kel == vurgu_u else (255, 255, 255),
                          stroke_width=kontur, stroke_fill=(0, 0, 0))
                xx_ += ciz_.textlength(parca, font=f)
        else:
            ciz_.text((x, y), s, font=f, fill=renk["vurgu"] if (i == len(satirlar) - 1 and len(satirlar) > 1 and not vurgu_u) else (255, 255, 255),
                      stroke_width=kontur, stroke_fill=(0, 0, 0))

    # Sembol / rozet (sağ üst; dikeyde yazının üstünde, 4:5 güvenli alan içinde)
    if sembol and sembol != "yok":
        r = int((H * 0.085) if dikey else (H * 0.16))
        # dikeyde 4:5 kırpmanın (y 285–1635) sağ üst köşesi; yatayda sağ üst
        cx, cy = (W - r - 60, 285 + r + 70) if dikey else (W - r - 40, r + 40)
        if sembol == "ok":
            # kalın kırmızı ok: yazıya doğru aşağı
            gov = r * 0.45
            nokt = [(cx - gov / 2, cy - r), (cx + gov / 2, cy - r), (cx + gov / 2, cy + r * 0.1), (cx + r * 0.8, cy + r * 0.1),
                    (cx, cy + r), (cx - r * 0.8, cy + r * 0.1), (cx - gov / 2, cy + r * 0.1)]
            ciz_.polygon([(a + 8, b + 8) for a, b in nokt], fill=(0, 0, 0))
            ciz_.polygon(nokt, fill=renk["kutu"], outline=(255, 255, 255), width=6)
        elif sembol == "carpi":
            k_ = r * 0.75
            for dx, dy in ((8, 8), (0, 0)):
                c = (0, 0, 0) if dx else renk["kutu"]
                ciz_.line([(cx - k_ + dx, cy - k_ + dy), (cx + k_ + dx, cy + k_ + dy)], fill=c, width=int(r * .38))
                ciz_.line([(cx + k_ + dx, cy - k_ + dy), (cx - k_ + dx, cy + k_ + dy)], fill=c, width=int(r * .38))
        else:
            metin = {"soru": "?", "unlem": "!"}.get(sembol) or (rozet_yazi or "!")
            zemin = renk["kutu"] if sembol in ("unlem", "rozet") else renk["vurgu"]
            yazi_renk = (255, 255, 255) if zemin == renk["kutu"] else (0, 0, 0)
            ciz_.ellipse([cx - r + 8, cy - r + 10, cx + r + 8, cy + r + 10], fill=(0, 0, 0))
            ciz_.ellipse([cx - r, cy - r, cx + r, cy + r], fill=zemin, outline=(255, 255, 255), width=max(6, r // 12))
            fb = int(r * (1.35 if len(metin) == 1 else 1.05 if len(metin) == 2 else 0.78 if len(metin) == 3 else 0.62))
            ff = _font(fb)
            bb = ciz_.textbbox((0, 0), metin, font=ff)
            ciz_.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), metin, font=ff, fill=yazi_renk)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    q = 92
    im.save(hedef, quality=q, optimize=True)
    while os.path.getsize(hedef) > 1_900_000 and q > 60:   # YouTube sınırı 2 MB
        q -= 8
        im.save(hedef, quality=q, optimize=True)
    return hedef


def ciz_neon(arka, yazi, hedef, kanal="dukkantv", dikey=True, vurgu="", sembol="yok", rozet_yazi=""):
    """Neon kapak: koyu, kısılmış sahne + kanal renginde neon ışıma, parlayan dev yazı, neon çerçeve ve neon rozet.
    Yazı ve rozet dikeyde 4:5 kırpmanın (y 285–1635) içinde kalır."""
    _paketler()
    import numpy as np
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    W, H = (1080, 1920) if dikey else (1280, 720)
    neon = NEON.get(kanal, (0, 229, 255))
    im = Image.open(arka).convert("RGB")
    o = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * o + 1), int(im.height * o + 1)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x0, y0, x0 + W, y0 + H))
    im = ImageEnhance.Color(im).enhance(0.75)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    yy, xx = np.mgrid[0:H, 0:W]
    arr = np.asarray(im, dtype=np.float32)
    # sahne kısılır (gece görünümü), yazı bandı daha da koyu
    merkez_y = H * (0.60 if dikey else 0.66)
    bant = np.exp(-((yy - merkez_y) / (H * (0.17 if dikey else 0.30))) ** 2)
    kis = 0.46 - 0.28 * bant
    alt_kisim = np.clip((yy - H * 0.68) / (H * 0.14), 0, 1) if dikey else np.zeros_like(bant)
    kis = kis * (1 - 0.75 * alt_kisim)   # karedeki eski altyazılar kapakla yarışmasın
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    kis = kis * np.clip(1.15 - 0.55 * d, 0.35, 1)
    arr = arr * kis[..., None] + np.array([9, 8, 12]) * (1 - kis[..., None])
    # kanal renginde yumuşak neon ışık havuzu (yazının arkasında)
    isik = np.exp(-(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - merkez_y) / (H * (0.20 if dikey else 0.35))) ** 2))
    arr = arr + isik[..., None] * np.array(neon) * 0.32
    im = Image.fromarray(arr.clip(0, 255).astype("uint8")).convert("RGBA")

    def isilt(katman, yaricap, guc):
        b = katman.filter(ImageFilter.GaussianBlur(yaricap))
        a = np.asarray(b, dtype=np.float32)
        a[..., 3] = np.clip(a[..., 3] * guc, 0, 255)
        return Image.fromarray(a.astype("uint8"))

    # neon çerçeve (dikeyde 4:5 alanını da çevreler gibi görünür, kenara yakın)
    cer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = 26
    ImageDraw.Draw(cer).rounded_rectangle([m, m, W - m, H - m], radius=46, outline=neon + (255,), width=7)
    im = Image.alpha_composite(im, isilt(cer, 26, 3.5))
    im = Image.alpha_composite(im, isilt(cer, 8, 2.5))
    im = Image.alpha_composite(im, cer)

    olcum = ImageDraw.Draw(im)
    satirlar = _satirla(ust(yazi.strip()), dikey)
    gen_sinir, yuk_sinir = W * (0.84 if dikey else 0.84), H * (0.32 if dikey else 0.52)
    boy = 380
    while boy > 40:
        f = _font(boy)
        if max(olcum.textlength(s_, font=f) for s_ in satirlar) <= gen_sinir and len(satirlar) * boy * 1.04 <= yuk_sinir:
            break
        boy -= 6
    f = _font(boy)
    satir_y = boy * 1.04
    ust_y = merkez_y - satir_y * len(satirlar) / 2 - boy * 0.08
    vurgu_u = ust(vurgu.strip()) if vurgu else ""
    if not vurgu_u or not any(vurgu_u in s_.split() for s_ in satirlar):
        vurgu_u = satirlar[-1].split()[-1] if len(satirlar) > 1 else ""
    yazi_k = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    isik_k = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dy, di = ImageDraw.Draw(yazi_k), ImageDraw.Draw(isik_k)
    for i, s_ in enumerate(satirlar):
        x = (W - olcum.textlength(s_, font=f)) / 2
        y = ust_y + i * satir_y
        for j, kel in enumerate(s_.split()):
            renk = neon if kel == vurgu_u else (255, 255, 255)
            dy.text((x, y), kel, font=f, fill=renk + (255,), stroke_width=max(3, boy // 30), stroke_fill=(10, 8, 14, 255))
            di.text((x, y), kel, font=f, fill=neon + (255,), stroke_width=max(4, boy // 22), stroke_fill=neon + (255,))
            x += olcum.textlength(kel + " ", font=f)
    im = Image.alpha_composite(im, isilt(isik_k, boy * 0.30, 3.0))   # geniş hale
    im = Image.alpha_composite(im, isilt(isik_k, boy * 0.12, 3.2))   # parlak hale
    im = Image.alpha_composite(im, isilt(isik_k, boy * 0.04, 2.0))   # tüp ışığı
    im = Image.alpha_composite(im, yazi_k)
    # ince neon alt çizgi
    cz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cy_ = ust_y + satir_y * len(satirlar) + boy * 0.12
    ImageDraw.Draw(cz).rounded_rectangle([W * 0.30, cy_, W * 0.70, cy_ + 10], radius=5, fill=neon + (255,))
    im = Image.alpha_composite(im, isilt(cz, 14, 2.5))
    im = Image.alpha_composite(im, cz)

    if sembol and sembol != "yok":
        r = int(H * 0.075) if dikey else int(H * 0.15)
        cx, cy = (W - r - 80, 285 + r + 70) if dikey else (W - r - 60, r + 55)
        rk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(rk)
        if sembol == "ok":
            gov = r * 0.42
            dr.polygon([(cx - gov / 2, cy - r), (cx + gov / 2, cy - r), (cx + gov / 2, cy + r * 0.1), (cx + r * 0.8, cy + r * 0.1),
                        (cx, cy + r), (cx - r * 0.8, cy + r * 0.1), (cx - gov / 2, cy + r * 0.1)], outline=neon + (255,), width=9)
        elif sembol == "carpi":
            k_ = r * 0.7
            dr.line([(cx - k_, cy - k_), (cx + k_, cy + k_)], fill=neon + (255,), width=int(r * .2))
            dr.line([(cx + k_, cy - k_), (cx - k_, cy + k_)], fill=neon + (255,), width=int(r * .2))
        else:
            metin = {"soru": "?", "unlem": "!"}.get(sembol) or (rozet_yazi or "!")
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(12, 10, 18, 235), outline=neon + (255,), width=max(7, r // 11))
            fb = int(r * (1.25 if len(metin) == 1 else 0.98 if len(metin) == 2 else 0.74 if len(metin) == 3 else 0.58))
            ff = _font(fb)
            bb = dr.textbbox((0, 0), metin, font=ff)
            dr.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), metin, font=ff, fill=(255, 255, 255, 255))
        im = Image.alpha_composite(im, isilt(rk, 24, 3.5))
        im = Image.alpha_composite(im, isilt(rk, 7, 2.5))
        im = Image.alpha_composite(im, rk)
    im = im.convert("RGB")
    q = 92
    im.save(hedef, quality=q, optimize=True)
    while os.path.getsize(hedef) > 1_900_000 and q > 60:
        q -= 8
        im.save(hedef, quality=q, optimize=True)
    return hedef


def hazirla(kanal, video, baslik, aciklama="", etiketler="", kisa=True):
    """yt_kuyruk.ekle için tek giriş: (yeni_baslik, etiket_listesi, kapak_yolu|None)."""
    mevcut = [e.strip() for e in (etiketler.split(",") if isinstance(etiketler, str) else etiketler) if str(e).strip()]
    p = paket(kanal, baslik, aciklama, kisa, mevcut)
    kapak = None
    if kisa and video and os.path.exists(video):
        try:
            kare = kare_sec(video)
            if kare:
                kapak = os.path.join(tempfile.mkdtemp(), "kapak.jpg")
                # Shorts kapakları neon tarzında (27 Kas 2026, Levent). Eski tarz için KAPAK_STIL=klasik
                cizici = ciz if os.environ.get("KAPAK_STIL") == "klasik" else ciz_neon
                cizici(kare, p["kapak_yazi"], kapak, kanal, dikey=True, vurgu=p.get("vurgu", ""),
                       sembol=p.get("sembol", "yok"), rozet_yazi=p.get("rozet_yazi", ""))
        except Exception as e:
            print("kapak_seo: kapak çizilemedi:", str(e)[:200])
            kapak = None
    print(f"kapak_seo: başlık → {p['baslik']!r} | kapak → {p.get('kapak_yazi')!r} ({p.get('sembol')}) | "
          f"{len(p['etiketler'])} etiket")
    return p["baslik"], p["etiketler"], kapak, p


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "ciz":   # python kapak_seo.py ciz resim.jpg "YAZI" cikti.jpg kanal dikey vurgu sembol rozet
        a = sys.argv[2:]
        ciz(a[0], a[1], a[2], a[3] if len(a) > 3 else "gizlitarih", (a[4] == "1") if len(a) > 4 else False,
            a[5] if len(a) > 5 else "", a[6] if len(a) > 6 else "yok", a[7] if len(a) > 7 else "")
    elif sys.argv[1] == "neon":   # python kapak_seo.py neon resim.jpg "YAZI" cikti.jpg kanal vurgu sembol rozet
        a = sys.argv[2:]
        ciz_neon(a[0], a[1], a[2], a[3] if len(a) > 3 else "dukkantv", True, a[4] if len(a) > 4 else "",
                 a[5] if len(a) > 5 else "yok", a[6] if len(a) > 6 else "")
    elif sys.argv[1] == "paket":
        print(json.dumps(paket(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""), ensure_ascii=False, indent=1))
