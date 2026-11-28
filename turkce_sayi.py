# Rakamları Türkçe okunuşa çevirir — ses klonu (Chatterbox) rakam okuyamadığı için metin sese gitmeden önce çalışır.
# Sadece SES metnini değiştirir; ekrandaki altyazılar rakamla kalır.
#   "29 Mayıs 1453'te"  -> "yirmi dokuz Mayıs bin dört yüz elli üçte"
#   "II. Mehmet"        -> "İkinci Mehmet"      "19. yüzyıl" -> "on dokuzuncu yüzyıl"
#   "%40" / "40%"       -> "yüzde kırk"         "1,5 milyon" -> "bir virgül beş milyon"
#   "1.500.000 TL"      -> "bir milyon beş yüz bin lira"   "M.Ö. 3000" -> "milattan önce üç bin"
#   "1914-1918"         -> "bin dokuz yüz on dört ile bin dokuz yüz on sekiz"   "19:30" -> "on dokuz otuz"
# Kullanım: from turkce_sayi import duzelt;  python turkce_sayi.py "metin"  (deneme)
import re
import sys

BIRLER = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
ONLAR = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
BUYUK = [(10 ** 12, "trilyon"), (10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")]

SIRA_EKI = {"bir": "birinci", "iki": "ikinci", "üç": "üçüncü", "dört": "dördüncü", "beş": "beşinci",
            "altı": "altıncı", "yedi": "yedinci", "sekiz": "sekizinci", "dokuz": "dokuzuncu", "on": "onuncu",
            "yirmi": "yirminci", "otuz": "otuzuncu", "kırk": "kırkıncı", "elli": "ellinci", "altmış": "altmışıncı",
            "yetmiş": "yetmişinci", "seksen": "sekseninci", "doksan": "doksanıncı", "yüz": "yüzüncü",
            "bin": "bininci", "milyon": "milyonuncu", "milyar": "milyarıncı", "trilyon": "trilyonuncu",
            "sıfır": "sıfırıncı"}

ROMA = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
BIRIM = {"km": "kilometre", "kg": "kilogram", "cm": "santimetre", "mm": "milimetre", "m²": "metrekare",
         "m2": "metrekare", "km²": "kilometrekare", "gb": "gigabayt", "mb": "megabayt", "tb": "terabayt",
         "mah": "miliamper saat", "°c": "derece", "°": "derece", "tl": "lira", "₺": "lira", "$": "dolar",
         "€": "avro", "dk": "dakika", "sn": "saniye", "km/sa": "kilometre", "km/s": "kilometre"}


def _yuzler(n):
    y, k = divmod(n, 100)
    o, b = divmod(k, 10)
    parca = ([] if y == 0 else (["yüz"] if y == 1 else [BIRLER[y], "yüz"])) + ([ONLAR[o]] if o else []) + ([BIRLER[b]] if b else [])
    return parca


def sayi(n):
    """Tam sayıyı Türkçe yazıya çevirir: 1453 -> 'bin dört yüz elli üç'."""
    n = int(n)
    if n == 0:
        return "sıfır"
    if n < 0:
        return "eksi " + sayi(-n)
    parca = []
    for deger, ad in BUYUK:
        if n >= deger:
            kac, n = divmod(n, deger)
            parca += [ad] if (kac == 1 and deger == 1000) else [sayi(kac), ad]
    parca += _yuzler(n)
    return " ".join(p for p in parca if p)


def sira(n):
    """Sıra sayısı: 19 -> 'on dokuzuncu', 2 -> 'ikinci'."""
    kelimeler = sayi(n).split(" ")
    kelimeler[-1] = SIRA_EKI.get(kelimeler[-1], kelimeler[-1])
    return " ".join(kelimeler)


def _rakam_dizisi(s):
    """Baştaki sıfırlar ya da uzun numaralar (telefon vb.) için tek tek okur."""
    return " ".join("sıfır" if c == "0" else BIRLER[int(c)] for c in s)


def _tam(s):
    s = s.replace(".", "")
    if len(s) > 1 and s.startswith("0"):
        return _rakam_dizisi(s)
    if len(s) > 15:
        return _rakam_dizisi(s)
    return sayi(int(s))


def _roma(r):
    t, onceki = 0, 0
    for c in reversed(r):
        v = ROMA[c]
        t, onceki = (t - v, onceki) if v < onceki else (t + v, v)
    return t


SIRALI_ADLAR = "|".join(["Dünya", "Lig", "Murat", "Murad", "Selim", "Mehmet", "Mehmed", "Ahmet", "Ahmed", "Mustafa",
    "Abdülhamit", "Abdülhamid", "Bayezid", "Beyazıt", "Osman", "Mahmut", "Mahmud", "Süleyman", "İbrahim", "Meclis",
    "Ordu", "Kolordu", "Napolyon", "Louis", "Wilhelm", "Henry", "Elizabeth", "Katerina", "Petro", "Ramses", "Haçlı",
    "Viyana", "İnönü", "Sezon", "Bölüm", "Sınıf", "Kat", "Perde", "Cumhurbaşkanı", "Dönem", "Balkan", "Kosova"])

# Sayı kalıbı: 1.500.000 (binlik nokta) | 1,5 (ondalık virgül) | 2.5 (ondalık nokta) | 1453
SAYI = r"\d{1,3}(?:\.\d{3})+(?!\d)|\d+(?:,\d+)?|\d+\.\d+"


def _sayi_oku(s):
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
        return _tam(s)
    if "," in s:
        a, b = s.split(",")
        return f"{_tam(a)} virgül {_tam(b) if not b.startswith('0') else _rakam_dizisi(b)}"
    if "." in s:
        a, b = s.split(".")
        return f"{_tam(a)} nokta {_rakam_dizisi(b) if b.startswith('0') else _tam(b)}"
    return _tam(s)


def _ek_birlestir(m):
    # "1453'te" -> "bin dört yüz elli üçte" (kesme işareti kalkar, ek sayıya yapışır)
    return m.group(1) + m.group(2)


def duzelt(metin):
    t = metin
    # Kısaltmalar
    t = re.sub(r"\bM\.\s?Ö\.?", "milattan önce", t)
    t = re.sub(r"\bM\.\s?S\.?(?=\s*\d)", "milattan sonra", t)
    t = re.sub(r"\bMÖ\b", "milattan önce", t)
    t = re.sub(r"\bMS\b(?=\s*\d)", "milattan sonra", t)
    # Roma rakamlı hükümdar / yüzyıl: "II. Mehmet", "XIV. Louis", "XIX. yüzyıl"
    t = re.sub(r"\b([IVXLCDM]{1,6})\.(?=\s+\w)",
               lambda m: _ilk_buyuk(sira(_roma(m.group(1)))) if re.fullmatch(
                   r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", m.group(1)) else m.group(0), t)
    # Yüzde
    t = re.sub(r"%\s?(" + SAYI + ")", lambda m: "yüzde " + _sayi_oku(m.group(1)), t)
    t = re.sub(r"(" + SAYI + r")\s?%", lambda m: "yüzde " + _sayi_oku(m.group(1)), t)
    # Saat: 19:30, 16.33'te gibi "saat" ile kullanılanlar
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b(?:['’]([a-zçğıöşü]+))?",
               lambda m: sayi(int(m.group(1))) + ("" if m.group(2) == "00" else " " + _tam(m.group(2))) + (m.group(3) or ""), t)
    # Aralık: 1914-1918 (yıl) -> "ile", 2-3 -> "iki üç"
    t = re.sub(r"\b(\d{3,4})\s?[-–]\s?(\d{2,4})\b",
               lambda m: f"{_tam(m.group(1))} ile {_tam(m.group(2))}", t)
    t = re.sub(r"\b(\d{1,2})\s?[-–]\s?(\d{1,2})\b(?!\s*:)", lambda m: f"{_tam(m.group(1))} {_tam(m.group(2))}", t)
    # Sıra sayısı: "19. yüzyıl", "3. bölüm" (ardından küçük harfle başlayan kelime gelir; cümle sonu değil)
    t = re.sub(r"\b(\d+)\.(?=\s+[a-zçğıöşü])", lambda m: sira(int(m.group(1))), t)
    # Büyük harfle devam eden bilinen sıra kalıpları: "2. Dünya Savaşı", "3. Selim", "1. Lig" (cümle sonu "1481. Dünyanın" değil)
    t = re.sub(r"\b(\d{1,3})\.(?=\s+(?:" + SIRALI_ADLAR + r")\b)", lambda m: _ilk_buyuk(sira(int(m.group(1)))), t)
    # Harfe yapışık sayı: "GTA6" -> "GTA 6", "4K" -> "4 K"
    t = re.sub(r"(?<=[A-Za-zÇĞİÖŞÜçğıöşü])(?=\d)", " ", t)
    t = re.sub(r"(?<=\d)(?=[A-ZÇĞİÖŞÜ])", " ", t)
    # Para birimi önde: "$500", "₺200", "€10"
    t = re.sub(r"([$€₺])\s?(" + SAYI + ")", lambda m: _sayi_oku(m.group(2)) + " " + BIRIM[m.group(1)], t)
    # Sayı + birim: "500 TL", "42 km", "6000 mAh", "35°C"
    birimler = "|".join(sorted((re.escape(b) for b in BIRIM if b not in "$€₺"), key=len, reverse=True))
    t = re.sub(r"(" + SAYI + r")\s?(" + birimler + r")(?![a-zçğıöşü])",
               lambda m: _sayi_oku(m.group(1)) + " " + BIRIM[m.group(2).lower()], t, flags=re.I)
    # Kalan bütün sayılar (ekleriyle): "1453'te", "1920'lerde", "GTA6"
    t = re.sub(r"(" + SAYI + r")(?:['’]([a-zçğıöşü]+))?",
               lambda m: _sayi_oku(m.group(1)) + (m.group(2) or ""), t)
    # Okunuşta sorun çıkaran işaretler
    t = t.replace("&", " ve ").replace("+", " artı ")
    return re.sub(r"\s{2,}", " ", t).strip()


def _ilk_buyuk(s):
    return ("İ" + s[1:]) if s.startswith("i") else s[:1].upper() + s[1:]


if __name__ == "__main__":
    print(duzelt(" ".join(sys.argv[1:])))
