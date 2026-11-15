# 81 İl Turnuvası — fikstür görseli (9:16). Sezon tablosundan otomatik çizilir, her maçtan sonra güncellenir.
# Tur atlayan iller yeşil, elenenler soluk, oynanmamış gruplar beyaz; bugünün maçı vurgulanır.
import datetime as dt
import json
import os
import sys

from PIL import Image, ImageDraw

from iller import AD
from motor import SARI, font, renk, yazi

KOK = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
YESIL, SOLUK = (90, 230, 120), (110, 115, 140)
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def gosterim_gunu():
    """Sonucu gösterilebilecek son grup günü: maç videosu akşam yayına girdiği için 21:00'dan önce dün."""
    simdi = dt.datetime.now(dt.timezone(dt.timedelta(hours=3)))
    return simdi.date() if simdi.hour >= 21 else simdi.date() - dt.timedelta(days=1)


def _kuyruk():
    import glob
    k = os.path.join(KOK, "..", "kuyruk")
    for p in glob.glob(os.path.join(k, "*.json")) + glob.glob(os.path.join(k, "arsiv", "*.json")):
        d = json.load(open(p, encoding="utf-8"))
        if d.get("kanal") == "ilturnuva" and d.get("yayin"):
            yield d


def yayinlanan_basliklar():
    simdi = dt.datetime.now(dt.timezone.utc)
    return " ".join(d["baslik"] for d in _kuyruk() if dt.datetime.fromisoformat(d["yayin"]) <= simdi)


def planli_basliklar():
    return " ".join(d["baslik"] for d in _kuyruk())


def ciz(s, cikti, ilk_gun=None, goster=None):
    goster = goster or gosterim_gunu()
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(14 + 20 * k), int(16 + 6 * k), int(40 + 30 * k)))
    yazi(d, (W / 2, 95), "81 İL TURNUVASI", font(82), SARI, 8)
    yazi(d, (W / 2, 180), f"SEZON {s['sezon']} · FİKSTÜR", font(50), kenar=5)
    maclar = [m for m in s["maclar"] if m["tur"] == 1]
    # Henüz yayınlanmamış maçların sonucu gösterilmez (spoiler olmasın)
    yayinda = yayinlanan_basliklar()
    acik = lambda k, m: bool(m.get("atlayan")) and (m["baslik"].title() in yayinda or (
        m["baslik"].title() not in planli_basliklar() and (not ilk_gun or ilk_gun + dt.timedelta(days=k) <= goster)))
    siradaki = next((m for k, m in enumerate(maclar) if not acik(k, m)), None)
    kw, kh, x0, y0, bosluk = 340, 395, 22, 250, 12
    for k, m in enumerate(maclar):
        cx, cy = x0 + (k % 3) * (kw + bosluk), y0 + (k // 3) * (kh + bosluk)
        oynandi = acik(k, m); bugun = siradaki is m
        d.rounded_rectangle([cx, cy, cx + kw, cy + kh], 22, fill=(26, 30, 54),
                            outline=SARI if bugun else (60, 66, 100), width=6 if bugun else 2)
        grup = m["baslik"].split("·")[-1].strip()
        yazi(d, (cx + kw / 2, cy + 34), grup, font(36), SARI if bugun else (255, 255, 255), 3)
        if ilk_gun:
            gun = ilk_gun + dt.timedelta(days=k)
            yazi(d, (cx + kw / 2, cy + 72), f"{gun.day} Kasım {GUNLER[gun.weekday()]}" if gun.month == 11
                 else f"{gun:%d.%m} {GUNLER[gun.weekday()]}", font(22, "Bold"), (180, 190, 230), 2)
        for j, p in enumerate(m["plakalar"]):
            yy = cy + 108 + j * 31
            if oynandi:
                c = YESIL if p in m["atlayan"] else SOLUK
            else:
                c = (240, 240, 255)
            d.ellipse([cx + 22, yy - 10, cx + 42, yy + 10], fill=renk(p) if (not oynandi or p in m["atlayan"]) else SOLUK)
            d.text((cx + 54, yy), f"{p} {AD[p]}" + ("  ✓" if oynandi and p in m["atlayan"] else ""),
                   font=font(24, "Bold"), fill=c, anchor="lm")
    yb = y0 + 3 * (kh + bosluk) + 20
    yazi(d, (W / 2, yb + 10), "2. TUR: 27 il · 3 grup   →   BÜYÜK FİNAL: 9 il", font(34), kenar=4)
    yazi(d, (W / 2, yb + 70), "Her grubun son 3 kalanı tur atlar · Her gün yeni maç", font(30, "Bold"), (200, 210, 255), 3)
    if ilk_gun:
        t2, fn = ilk_gun + dt.timedelta(days=9), ilk_gun + dt.timedelta(days=12)
        ay = lambda g: f"{g.day} {['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'][g.month - 1]}"
        yazi(d, (W / 2, yb + 145), f"2. TUR: {ay(t2)} – {ay(t2 + dt.timedelta(days=2))}", font(44), kenar=5)
        son = f"ŞAMPİYON: {s['sampiyon']} {AD[s['sampiyon']]}" if s.get("sampiyon") else f"BÜYÜK FİNAL: {ay(fn)} {GUNLER[fn.weekday()]}"
        yazi(d, (W / 2, yb + 215), son, font(52), SARI, 6)
    yazi(d, (W / 2, yb + 295), "Her akşam yeni maç · @81ilturnuvasi", font(36, "Bold"), kenar=4)
    yazi(d, (W / 2, H - 60), "Şehrin hangi grupta? Yorumlara yaz!", font(40), kenar=4)
    im.save(cikti, quality=92)
    return cikti


if __name__ == "__main__":
    s = json.load(open(os.path.join(KOK, "sezon.json"), encoding="utf-8"))
    ilk = dt.date.fromisoformat(sys.argv[2] if len(sys.argv) > 2 else s.get("baslangic", "")) if (len(sys.argv) > 2 or s.get("baslangic")) else None
    print(ciz(s, sys.argv[1] if len(sys.argv) > 1 else "fikstur.jpg", ilk))
