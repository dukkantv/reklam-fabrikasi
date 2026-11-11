# Dükkan TV — siteden gelen başvuruları taslağa çevirir.
#
#   python basvuru.py kontrol     -> (YouTube Yayın işi her çalıştığında) yeni başvurular için taslak işini,
#                                    onaylanan taslaklar için üretimi başlatır
#   python basvuru.py taslak ID   -> başvuruyu ve fotoğrafları indirir, reklamlar/<klasör>/ altına
#                                    bilgi.json yazar, Telegram'a taslağı + onay butonlarını gönderir
#
# Başvurular Cloudflare dinleyicisinde (cloudflare/onay-worker.js) saklanır.
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone

from yt_ortak import istek

KOK = os.path.dirname(os.path.abspath(__file__))
ONAY_URL = os.environ.get("ONAY_URL", "https://dukkantv-onay.dukkan-tvstudio.workers.dev").rstrip("/")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
GIZLI = hashlib.sha256(TOKEN.encode()).hexdigest()[:48]
GEMINI = "".join(os.environ.get("GEMINI_API_KEY", "").split())
MODELLER = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]  # 2.5 hızlı; "latest" bazen 4 dk+ düşünüyor
UA = {"User-Agent": "dukkantv-bot"}
TR = timezone(timedelta(hours=3))


# ---------- dinleyici ----------
def dinleyici(yol, method=None, json_govde=None, ham=False):
    sep = "&" if "?" in yol else "?"
    kod, _, v = istek(f"{ONAY_URL}{yol}{sep}k={GIZLI}", method=method, json_govde=json_govde, headers=UA)
    if kod != 200:
        raise RuntimeError(f"Dinleyici {yol} -> {kod}: {str(v)[:200]}")
    return v if ham else (json.loads(v) if isinstance(v, (bytes, str)) else v)


def durum_yaz(bid, durum, **ek):
    dinleyici(f"/durum?id={bid}&durum={durum}", method="POST", json_govde=ek)


# ---------- telegram ----------
def tg(metod, **veri):
    if not TOKEN or not CHAT:
        print(metod, json.dumps(veri, ensure_ascii=False)[:500])
        return {}
    kod, _, v = istek(f"https://api.telegram.org/bot{TOKEN}/{metod}",
                      json_govde={"chat_id": CHAT, **veri})
    if kod != 200:
        print("Telegram hata:", kod, str(v)[:300])
    return v


def tg_album(dosyalar, baslik):
    """Fotoğrafları albüm olarak gönderir (Telegram en fazla 10)."""
    if not TOKEN or not dosyalar:
        return
    import uuid
    sinir = uuid.uuid4().hex
    parcalar, medya = [], []
    for i, (yol, aciklama) in enumerate(dosyalar[:10]):
        ad = f"f{i}"
        medya.append({"type": "photo", "media": f"attach://{ad}",
                      **({"caption": baslik} if i == 0 else {})})
        parcalar.append((ad, os.path.basename(yol), open(yol, "rb").read()))
    govde = b""
    def alan(ad, deger):
        return (f"--{sinir}\r\nContent-Disposition: form-data; name=\"{ad}\"\r\n\r\n{deger}\r\n").encode()
    tek = len(parcalar) == 1
    govde += alan("chat_id", CHAT)
    if tek:  # Telegram albümü en az 2 fotoğraf ister; tek fotoğraf ayrı gönderilir
        govde += alan("caption", baslik)
        parcalar = [("photo",) + parcalar[0][1:]]
    else:
        govde += alan("media", json.dumps(medya, ensure_ascii=False))
    for ad, dosya, veri in parcalar:
        govde += (f"--{sinir}\r\nContent-Disposition: form-data; name=\"{ad}\"; filename=\"{dosya}\"\r\n"
                  f"Content-Type: image/jpeg\r\n\r\n").encode() + veri + b"\r\n"
    govde += f"--{sinir}--\r\n".encode()
    kod, _, v = istek(f"https://api.telegram.org/bot{TOKEN}/{'sendPhoto' if tek else 'sendMediaGroup'}", ham=govde,
                      headers={"Content-Type": f"multipart/form-data; boundary={sinir}"})
    if kod != 200:
        print("Albüm gönderilemedi:", kod, str(v)[:300])


# ---------- yardımcılar ----------
def slug(metin):
    t = metin.lower().replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s") \
        .replace("ö", "o").replace("ç", "c")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:30] or "dukkan"


def paket_turu(paket):
    return "premium" if paket.lower().startswith("premium") else "ekonomik"


def gemini(parcalar):
    son = None
    for model in MODELLER:
        for _ in range(2):
            try:
                kod, _, v = istek(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI}",
                    json_govde={"contents": [{"parts": parcalar}],
                                "generationConfig": {"temperature": 0.9, "responseMimeType": "application/json"}},
                    zaman=240)
            except Exception as e:  # zaman aşımı vb.: aynı modeli bir kez daha, sonra sıradaki model
                son = f"{model}: {e}"
                print("Gemini bağlantı hatası:", son)
                continue
            if kod == 404:
                break
            if kod in (429, 500, 503):
                son = f"{model} {kod}"
                time.sleep(15)
                continue
            if kod == 200:
                try:
                    return json.loads(v["candidates"][0]["content"]["parts"][0]["text"])
                except Exception as e:
                    son = e
                    continue
            son = f"{model} {kod} {str(v)[:150]}"
            time.sleep(4)
    raise RuntimeError(f"Gemini cevap vermedi: {son}")


def kucuk_b64(yol, en=768):
    """Gemini'ye gidecek fotoğrafı küçültür (daha hızlı, daha ucuz)."""
    try:
        from PIL import Image
        import io
        im = Image.open(yol).convert("RGB")
        im.thumbnail((en, en))
        b = io.BytesIO()
        im.save(b, "JPEG", quality=80)
        return base64.b64encode(b.getvalue()).decode()
    except Exception:
        return base64.b64encode(open(yol, "rb").read()).decode()


ORNEK = json.load(open(os.path.join(KOK, "reklamlar", "eserim", "bilgi.json"), encoding="utf-8"))


def istem_yaz(form, fotolar_var):
    ornek = {k: ORNEK[k] for k in ("renk", "sahne1", "sahne2", "sahne3", "sahne4", "seslendirme")}
    ornek["kart"] = {k: ORNEK["kart"][k] for k in ("slogan1", "slogan2")}
    for k in ("kisi", "firma_kisa", "foto"):
        ornek["sahne3"].pop(k, None)
    ornek["sahne4"].pop("foto", None)
    return f"""Sen Dükkan TV'nin reklam yazarısın. Bursa'daki esnaf için 15-20 saniyelik, dikey, komik ve
akılda kalan Türkçe reklam videosu senaryosu yazacaksın. Video 5 sahneden oluşur:
1) Kanca: dikkat çeken komik bir durum (ust/alt kısa metin, ikon tek emoji, arka1/arka2 hex renk)
2) Sorun: yaşanan dert (kutu: sorunu anlatan 1-2 kelimelik BÜYÜK HARF etiket, bos: kısa ek, baslik: büyük vurucu cümle, alt: komik bir replik)
3) Çözüm: esnaf yetişiyor (ust: kısa giriş, baslik: esnafa seslenen tırnaklı cümle; <span class="vurgu">..</span> ile tek kelime vurgula)
4) Dükkân fotoğrafı üzerine yazı (ust, alt; damga: 1 kelimelik BÜYÜK HARF damga ya da boş)
5) Kapanış kartı (slogan1, slogan2: kısa, kafiyeli olursa iyi; <span class="vurgu">..</span> ile vurgu)
seslendirme: tam 5 madde, her sahne için 1 cümle (sahne 1..5, saniye 0.2-2.0 arası, metin en fazla 12 kelime).
Satır bölmek için <br> kullan. Metinler KISA olsun: ust/alt en fazla 32 karakter, baslik en fazla 40 karakter.
Esnafın verdiği bilgilere SADIK kal, olmayan kampanya, fiyat, ödül uydurma. Siyaset, din, argo, kumar yok.
Ton: {form.get('ton') or 'Samimi ve eğlenceli'}. renk: işletmeye yakışan koyu bir vurgu rengi (hex).
ÇOK ÖNEMLİ: Tüm metinleri ve seslendirmeyi doğru Türkçe karakterlerle yaz (ç, ğ, ı, İ, ö, ş, ü). "Sac" değil "Saç",
"kacan" değil "kaçan". İşletme adını formdaki gibi aynen yaz (harfi harfine).
Sadece "dosya_adi" alanı ASCII olsun: Dukkan_Adi_Konu biçiminde (Türkçe harf ve boşluk olmadan).
Premium çizgi film bölümü için kullanılacak ek alanlar da ver: "urunler" (ne satıyor/ne yapıyor, 1 cümle),
"esnaf_cinsiyet" ("erkek" ya da "kadın"; adından tahmin et, emin değilsen "erkek"), "konu" (bölüm için 1 cümlelik komik fikir).
{'Ekteki fotoğraflar esnafın dükkânından; sahneleri bunlara uygun yaz.' if fotolar_var else ''}

İşletmenin bilgileri:
{json.dumps(form, ensure_ascii=False, indent=1)}

Örnek (başka bir işletme için, SADECE BİÇİM örneği; içeriğini kopyalama):
{json.dumps(ornek, ensure_ascii=False)}

Sadece JSON döndür: {{"dosya_adi","renk","sahne1","sahne2","sahne3","sahne4","kart":{{"slogan1","slogan2"}},
"seslendirme","urunler","esnaf_cinsiyet","konu"}}"""


def dogrula(t):
    duz = lambda s: re.sub(r"<[^>]+>", "", str(s or ""))
    for s in ("sahne1", "sahne2", "sahne3", "sahne4"):
        assert isinstance(t.get(s), dict), s
    assert duz(t["sahne1"]["ust"]) and duz(t["sahne2"]["baslik"]) and duz(t["sahne3"]["baslik"])
    for s, alan, n in [("sahne1", "ust", 40), ("sahne1", "alt", 40), ("sahne2", "baslik", 48),
                       ("sahne3", "baslik", 52), ("sahne4", "ust", 40), ("sahne4", "alt", 44)]:
        assert len(duz(t[s].get(alan))) <= n, f"{s}.{alan} uzun"
    assert isinstance(t.get("kart"), dict) and duz(t["kart"].get("slogan1")) and duz(t["kart"].get("slogan2"))
    sl = t.get("seslendirme")
    assert isinstance(sl, list) and len(sl) == 5 and all(1 <= int(x["sahne"]) <= 5 and x["metin"] for x in sl)
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", t.get("renk", "")), "renk"
    # Türkçe harfsiz (ASCII'ye çevrilmiş) metni kabul etme: bu uzunlukta Türkçe metinde mutlaka bulunur
    hepsi = " ".join(duz(t[s].get(a)) for s in ("sahne1", "sahne2", "sahne3", "sahne4") for a in ("ust", "alt", "baslik", "bos"))
    hepsi += " " + " ".join(x["metin"] for x in sl)
    assert re.search(r"[çğıöşüÇĞİÖŞÜ]", hepsi), "Türkçe karakter yok (ASCII yazılmış)"


# ---------- komutlar ----------
def kontrol():
    try:
        liste = dinleyici("/basvurular")
    except Exception as e:
        print("Başvurular okunamadı:", e)
        return
    print("Başvurular:", [(b["id"], b.get("durum")) for b in liste])
    for b in liste:
        bid, durum = b["id"], b.get("durum")
        if durum == "yeni":
            durum_yaz(bid, "taslak_hazirlaniyor")
            subprocess.run(["gh", "workflow", "run", "basvuru-taslak.yml", "-f", f"id={bid}"], check=True)
            print("Taslak işi başlatıldı:", bid)
        elif durum == "onaylandi":
            k = dinleyici(f"/basvuru?id={bid}")
            klasor = k.get("klasor")
            if not klasor:
                print("Klasör yok, atlandı:", bid)
                continue
            if k.get("paket_tur") == "premium":
                subprocess.run(["gh", "workflow", "run", "otomatik-bolum.yml", "-f", "asama=taslak",
                                "-f", f"klasor={klasor}", "-f", f"konu={k.get('konu', '')}"], check=True)
                bilgi = "Premium bölüm taslağı (Levent'in Maceraları) hazırlanıyor; sahne planı onayına gelecek."
            else:
                subprocess.run(["gh", "workflow", "run", "reklam-uret.yml", "-f", f"klasor={klasor}"], check=True)
                bilgi = "Ekonomik reklam videosu çiziliyor; birkaç dakika içinde Telegram'a gelecek."
            durum_yaz(bid, "uretimde")
            tg("sendMessage", text=f"🎬 {k['form'].get('ad')}: üretim başladı.\n{bilgi}")


def taslak(bid):
    k = dinleyici(f"/basvuru?id={bid}")
    form = k["form"]
    tur = paket_turu(form.get("paket", ""))
    klasor = f"m-{slug(form.get('ad', ''))}-{bid[-4:]}"
    yol = os.path.join(KOK, "reklamlar", klasor)
    os.makedirs(yol, exist_ok=True)
    json.dump(k, open(os.path.join(yol, "basvuru.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # Fotoğrafları indir: on1.jpg, ic1.jpg, is1.jpg, logo1.jpg, sahip1.jpg ...
    sayac, dosyalar = {}, {}
    for f in k.get("fotolar", []):
        kat = re.sub(r"[^a-z]", "", f.get("kategori", "")) or "diger"
        sayac[kat] = sayac.get(kat, 0) + 1
        ad = f"{kat}{sayac[kat]}.jpg"
        veri = dinleyici(f"/foto?a={f['anahtar']}", ham=True)
        open(os.path.join(yol, ad), "wb").write(veri)
        dosyalar.setdefault(kat, []).append(ad)
    ilk = lambda *katlar: next((dosyalar[c][0] for c in katlar if dosyalar.get(c)), None)
    hepsi = [a for c in ("on", "ic", "is", "logo", "sahip", "diger") for a in dosyalar.get(c, [])]

    gorunmesin = "görünmek istemiyorum" in form.get("gorunum", "").lower()
    sahip = None if gorunmesin else ilk("sahip")
    dukkan = ilk("on", "ic", "is")
    eksik = []
    if not dukkan:
        eksik.append("dükkân fotoğrafı yok (dükkân önü / içi / iş başında)")
    if not ilk("logo"):
        eksik.append("logo yok — kapanış kartında dükkân önü fotoğrafı kullanılacak")
    if not gorunmesin and not ilk("sahip"):
        eksik.append("esnafın kendi fotoğrafı yok — 3. sahnede dükkân fotoğrafı kullanılacak")
    if "çizgi film" in form.get("gorunum", "").lower() and tur == "ekonomik":
        eksik.append("esnaf çizgi film hâlini istedi; Ekonomik videoda gerçek fotoğrafı yuvarlak çerçevede kullanılır")

    # Gemini'ye en fazla 4 fotoğraf göster
    parcalar = [{"text": istem_yaz(form, bool(hepsi))}]
    for ad in hepsi[:4]:
        parcalar.append({"inline_data": {"mime_type": "image/jpeg", "data": kucuk_b64(os.path.join(yol, ad))}})
    t, son_hata = None, None
    for _ in range(2):
        try:
            aday = gemini(parcalar)
            dogrula(aday)
            t = aday
            break
        except Exception as e:
            son_hata = e
            print("Taslak beğenilmedi, yeniden:", e)
    if t is None:
        raise RuntimeError(f"Taslak yazılamadı: {son_hata}")

    ad = form.get("ad", "")
    kisi = form.get("yetkili") or ad
    yedek = dukkan or ilk("logo", "sahip")
    if not yedek:  # hiç fotoğraf yoksa video yine çizilebilsin diye Dükkan TV logosu konur
        import shutil
        shutil.copy(os.path.join(KOK, "reklamlar", "dukkantv", "logo.png"), os.path.join(yol, "dtv_logo.png"))
        yedek = "dtv_logo.png"
        eksik.insert(0, "HİÇ FOTOĞRAF GELMEDİ — fotoğrafların yerine Dükkan TV logosu konacak; esnaftan WhatsApp'tan fotoğraf iste")
    bilgi = {
        "dosya_adi": re.sub(r"[^A-Za-z0-9_]", "", t.get("dosya_adi") or slug(ad).replace("-", "_"))[:40] or klasor,
        "renk": t["renk"], "ses": "tr-TR-AhmetNeural",
        "sahne1": t["sahne1"], "sahne2": t["sahne2"],
        "sahne3": {**t["sahne3"], "kisi": kisi, "firma_kisa": ad, "foto": sahip or yedek},
        "sahne4": {**t["sahne4"], "foto": ilk("is", "ic", "on") or yedek},
        "kart": {"logo": ilk("logo") or yedek, "slogan1": t["kart"]["slogan1"], "slogan2": t["kart"]["slogan2"],
                 "adres": form.get("adres", ""), "telefon": form.get("tel", ""),
                 **({"sosyal": form["insta"]} if form.get("insta") else {})},
        "seslendirme": [{"sahne": int(x["sahne"]), "saniye": float(x.get("saniye", 0.4)), "metin": x["metin"]}
                        for x in t["seslendirme"]],
        "efektler": [],
        "oto": {"firma": ad, "dukkan_adi": ad,
                "sektor": f"{form.get('sektor_adi') or form.get('sektor', '')} ({form.get('adres', '')})",
                "esnaf_adi": kisi, "esnaf_cinsiyet": t.get("esnaf_cinsiyet", "erkek"),
                "esnaf_foto": sahip, "dukkan_fotolari": [a for c in ("on", "ic", "is") for a in dosyalar.get(c, [])][:4],
                "logo": ilk("logo"), "urunler": t.get("urunler", ""),
                "notlar": f"Öne çıkan: {form.get('one', '')}. Kampanya: {form.get('kampanya') or 'yok'}. "
                          f"Müşteriler: {form.get('hedef') or '-'}. Görünüm isteği: {form.get('gorunum', '')}."},
    }
    json.dump(bilgi, open(os.path.join(yol, "bilgi.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    duz = lambda s: re.sub(r"<[^>]+>", " ", str(s or "")).replace("  ", " ").strip()
    s1, s2, s3, s4, kt = bilgi["sahne1"], bilgi["sahne2"], bilgi["sahne3"], bilgi["sahne4"], bilgi["kart"]
    seslendirme = "\n".join(f"  {x['sahne']}. “{x['metin']}”" for x in bilgi["seslendirme"])
    metin = (
        f"📝 TASLAK — {ad}\n"
        f"📦 {form.get('paket', '')}\n"
        f"📞 {form.get('tel', '')} · 📍 {form.get('adres', '')}\n"
        f"🕘 {form.get('saat') or '—'}\n"
        f"⭐ Öne çıkan: {form.get('one', '')}\n"
        + (f"🎁 Kampanya: {form['kampanya']}\n" if form.get("kampanya") else "")
        + f"🧑 Görünüm: {form.get('gorunum', '')}\n\n"
        f"🎬 SAHNELER\n"
        f"1) {s1.get('ikon', '')} {duz(s1['ust'])} — {duz(s1['alt'])}\n"
        f"2) [{duz(s2['kutu'])}] {duz(s2['baslik'])} — {duz(s2['alt'])}\n"
        f"3) {duz(s3['ust'])} {duz(s3['baslik'])} (fotoğraf: {s3['foto']})\n"
        f"4) {duz(s4['ust'])} {duz(s4['alt'])}{' · ' + duz(s4['damga']) if s4.get('damga') else ''} (fotoğraf: {s4['foto']})\n"
        f"5) Kart: {duz(kt['slogan1'])} / {duz(kt['slogan2'])}\n\n"
        f"🎙️ SESLENDİRME\n{seslendirme}\n"
        + (f"\n💡 Premium bölüm fikri: {t.get('konu', '')}\n" if tur == "premium" else "")
        + ("\n⚠️ EKSİKLER\n" + "\n".join("• " + e for e in eksik) + "\n" if eksik else "")
        + f"\n{'✅ Onaylarsan Premium bölüm planı hazırlanır.' if tur == 'premium' else '✅ Onaylarsan video çizilip Telegram’a gelir.'}"
        + "\n⚠️ Onaylamadan önce ödemenin yattığını kontrol et."
    )
    tg_album([(os.path.join(yol, a), a) for a in hepsi], f"📸 {ad} — gönderilen fotoğraflar")
    tg("sendMessage", text=metin[:4000], reply_markup={"inline_keyboard": [[
        {"text": "✅ Onayla", "callback_data": f"bv:onay:{bid}"},
        {"text": "🔄 Yeniden yaz", "callback_data": f"bv:yeniden:{bid}"},
        {"text": "❌ İptal", "callback_data": f"bv:iptal:{bid}"}]]})
    durum_yaz(bid, "taslak_hazir", klasor=klasor, paket_tur=tur, konu=t.get("konu", ""))
    print("Taslak hazır:", klasor)


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "kontrol"
    if komut == "kontrol":
        kontrol()
    elif komut == "taslak":
        try:
            taslak(sys.argv[2])
        except Exception:
            # 3 denemeye kadar bir sonraki kontrolde yeniden denensin, sonra "hata"da kalsın
            try:
                k = dinleyici(f"/basvuru?id={sys.argv[2]}")
                deneme = int(k.get("deneme", 0)) + 1
                durum_yaz(sys.argv[2], "yeni" if deneme < 3 else "hata", deneme=deneme)
            except Exception as e2:
                print("Durum yazılamadı:", e2)
            raise
    else:
        print(__doc__)
