"""Günün haberi için ücretsiz, özgür lisanslı fotoğraflar (Wikimedia Commons + Openverse).

Haber sitelerinin fotoğrafları telifli olduğu için KULLANILMAZ; yalnızca kamu malı / CC0 / CC BY / CC BY-SA.
İki aşama:
  1) aday:  bolum["gorsel_ara"] sorgularıyla aday fotoğrafları bulur, haber/gorsel_aday.json ve
            haber/gorsel_onizleme.jpg (numaralı önizleme) yazar. Claude önizlemeye bakıp uygunları seçer.
  2) indir: sahnelere yazılan "gorsel" seçimlerini indirir, sahneye "arka" (yerel yol) ekler.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

KLASOR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(KLASOR)
sys.path.insert(0, KOK)
ADAY_JSON = os.path.join(KLASOR, "gorsel_aday.json")
ONIZLEME = os.path.join(KLASOR, "gorsel_onizleme.jpg")
F_BOLD = os.path.join(KOK, "arena", "fonts", "InterDisplay-Bold.otf")


def _kaynaklar():
    import belgesel   # commons_ara / openverse_ara / indir (lisans süzgeçli) belgesel.py'de
    return belgesel


def adaylar(bolum, sorgu_basi=4):
    """Her sorgu için en fazla 4 aday indirir, numaralı önizleme yapar."""
    bg = _kaynaklar()
    os.makedirs("/tmp/haber_aday", exist_ok=True)
    liste, gorulen = [], set()
    for q in bolum.get("gorsel_ara", [])[:5]:
        bulunan = bg.commons_ara(q, 4) + bg.openverse_ara(q, 3)
        say = 0
        for a in bulunan:
            if a["url"] in gorulen or say >= sorgu_basi:
                continue
            yol = f"/tmp/haber_aday/{len(liste) + 1:02d}.jpg"
            if not bg.indir(a["url"], yol):
                continue
            try:
                Image.open(yol).verify()
            except Exception:
                continue
            gorulen.add(a["url"])
            say += 1
            liste.append({"no": len(liste) + 1, "ara": q, "url": a["url"], "lisans": a["lisans"], "yazar": a["yazar"],
                          "ad": (a.get("ad") or a["baslik"].replace("File:", ""))[:80]})
    json.dump(liste, open(ADAY_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if liste:
        sutun = 6
        satir = (len(liste) + sutun - 1) // sutun
        sayfa = Image.new("RGB", (sutun * 300, satir * 330), (20, 20, 28))
        d = ImageDraw.Draw(sayfa)
        f = ImageFont.truetype(F_BOLD, 34)
        for i, a in enumerate(liste):
            im = Image.open(f"/tmp/haber_aday/{a['no']:02d}.jpg").convert("RGB")
            o = max(270 / im.width, 300 / im.height)   # videodaki gibi dikey kırpılmış hali
            im = im.resize((max(270, round(im.width * o)), max(300, round(im.height * o))))
            x0, y0 = (im.width - 270) // 2, (im.height - 300) // 3
            x, y = (i % sutun) * 300 + 15, (i // sutun) * 330 + 15
            sayfa.paste(im.crop((x0, y0, x0 + 270, y0 + 300)), (x, y))
            d.rectangle([x, y, x + 64, y + 46], fill=(200, 30, 40))
            d.text((x + 32, y + 23), str(a["no"]), font=f, fill="white", anchor="mm")
        sayfa.save(ONIZLEME, quality=82)
    print(f"{len(liste)} aday görsel → {ONIZLEME}")
    return liste


def indir(bolum):
    """Sahnelerdeki "gorsel" seçimlerini indirir; sahneye "arka" ekler. Döndürür: kaynakça satırları."""
    bg = _kaynaklar()
    os.makedirs("/tmp/haber_gorsel", exist_ok=True)
    kaynakca, onbellek = [], {}
    for i, s in enumerate(bolum["sahneler"]):
        g = s.get("gorsel")
        if not g:
            continue
        if g["url"] not in onbellek:
            yol = f"/tmp/haber_gorsel/{len(onbellek) + 1:02d}.jpg"
            if not bg.indir(g["url"], yol):
                print("Görsel indirilemedi, sahne kodla çizilecek:", g["url"])
                onbellek[g["url"]] = None
                continue
            onbellek[g["url"]] = yol
            kaynakca.append(f"{g.get('ad', 'Fotoğraf')} — {g.get('yazar', 'Wikimedia Commons')} ({g.get('lisans', '')})")
        if onbellek[g["url"]]:
            s["arka"] = onbellek[g["url"]]
    return kaynakca
