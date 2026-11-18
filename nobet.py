# Yayın nöbetçisi: GitHub'ın planlı tetiklemeleri (cron) sık sık atlandığı için, "YouTube Yayın" işi
# her çalışmanın sonunda sıradaki paylaşım saatine kadar bekler ve kendini yeniden başlatır.
# Çıktı: beklenecek saniye (en fazla AZAMI). Ayrıntılar stderr'e yazılır.
import datetime as dt
import glob
import json
import os
import sys

TR = dt.timezone(dt.timedelta(hours=3))
AZAMI = 5 * 3600 + 30 * 60      # bir iş en fazla 6 saat sürebilir; 5,5 saatte bir zincir tazelenir
YENIDEN = 10 * 60               # paylaşılmayı bekleyen geçmiş video varsa 10 dk sonra tekrar dene

SOSYAL = {"dukkantv", "dramabite", "kasakurgu", "ilturnuva"}  # Instagram/Facebook paylaşımı olan kanallar
KOK = os.path.dirname(os.path.abspath(__file__))


def bekleme():
    simdi = dt.datetime.now(TR)
    adaylar = []
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(k, dict) or not k.get("yayin") or k.get("uzun"):
            continue
        z = dt.datetime.fromisoformat(k["yayin"])
        paylasilmadi = k.get("kanal") in SOSYAL and k.get("ig") not in ("paylasildi", "hata")
        if z > simdi:
            adaylar.append((z + dt.timedelta(minutes=2), k["id"], "yayın saati"))
        elif paylasilmadi and simdi - z < dt.timedelta(hours=30):
            adaylar.append((simdi + dt.timedelta(seconds=YENIDEN), k["id"], "paylaşım bekliyor"))
    # Onay/yükleme kontrolleri için gündüz en az saatte bir çalış
    adaylar.append((simdi + dt.timedelta(hours=1) if 6 <= simdi.hour < 23 else simdi + dt.timedelta(seconds=AZAMI),
                    "-", "düzenli kontrol"))
    z, kid, neden = min(adaylar)
    sn = max(60, min(AZAMI, int((z - simdi).total_seconds())))
    print(f"Sonraki çalışma: {simdi + dt.timedelta(seconds=sn):%d.%m %H:%M} ({neden}: {kid})", file=sys.stderr)
    return sn


if __name__ == "__main__":
    print(bekleme())
