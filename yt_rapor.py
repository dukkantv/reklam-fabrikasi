"""Her sabah 3 YouTube kanalının istatistiğini toplar → Telegram'a özet + rapor/<tarih>.json.

Bilgisayar gerekmez; GitHub'da çalışır.
"""
import datetime as dt
import json
import os

from yt_ortak import analiz, erisim_anahtari, kanal_bilgi, kanallar, telegram, yt

bugun = dt.date.today()
gun = lambda n: (bugun - dt.timedelta(days=n)).isoformat()


def tablo(cevap):
    adlar = [c["name"] for c in cevap.get("columnHeaders", [])]
    return [dict(zip(adlar, satir)) for satir in cevap.get("rows", []) or []]


def toplam(token, bas, metrik, filtre=None):
    ek = {"filters": filtre} if filtre else {}
    try:
        satir = tablo(analiz(token, bas, gun(0), metrik, **ek))
        return satir[0] if satir else {}
    except Exception as e:
        print("analiz hatası:", metrik, filtre, e)
        return None


sonuc = {"tarih": bugun.isoformat(), "kanallar": {}}
mesaj = [f"📊 YouTube günlük rapor — {bugun.strftime('%d.%m.%Y')}"]

for k in kanallar():
    bilgi = kanal_bilgi(k)
    try:
        token = erisim_anahtari(k)
        ch = yt(token, "channels", part="statistics,snippet", mine="true")["items"][0]
        ist = ch["statistics"]
        son28 = toplam(token, gun(28), "views,estimatedMinutesWatched,subscribersGained,subscribersLost") or {}
        yil_uzun = toplam(token, gun(365), "estimatedMinutesWatched", "creatorContentType==VIDEO_ON_DEMAND")
        shorts90 = toplam(token, gun(90), "views", "creatorContentType==SHORTS")

        # Son 7 günün en çok izlenen videoları
        enler = []
        try:
            enler = tablo(analiz(token, gun(7), gun(0),
                                 "views,averageViewDuration,averageViewPercentage,likes,comments",
                                 dimensions="video", sort="-views", maxResults=5))
        except Exception as e:
            print("video tablosu alınamadı:", e)
        if enler:
            adlar = {v["id"]: v["snippet"]["title"] for v in
                     yt(token, "videos", part="snippet", id=",".join(r["video"] for r in enler))["items"]}
            for r in enler:
                r["baslik"] = adlar.get(r["video"], r["video"])

        abone = int(ist.get("subscriberCount", 0))
        saat_uzun = round((yil_uzun or {}).get("estimatedMinutesWatched", 0) / 60, 1) if yil_uzun is not None else None
        s90 = (shorts90 or {}).get("views") if shorts90 is not None else None
        sonuc["kanallar"][k] = {"ad": bilgi["ad"], "abone": abone, "toplam_izlenme": int(ist.get("viewCount", 0)),
                                "video_sayisi": int(ist.get("videoCount", 0)), "son28": son28,
                                "uzun_video_saat_365": saat_uzun, "shorts_izlenme_90": s90, "en_iyi_7gun": enler}

        net = son28.get("subscribersGained", 0) - son28.get("subscribersLost", 0)
        satirlar = [f"\n▶️ {bilgi['ad']}: {abone} abone ({net:+d} / 28 gün)",
                    f"   28 gün: {son28.get('views', 0)} izlenme, {round(son28.get('estimatedMinutesWatched', 0) / 60, 1)} saat"]
        hedef = [f"abone %{min(100, abone / 10):.1f}"]
        if saat_uzun is not None:
            hedef.append(f"saat {saat_uzun}/8000")
        if s90 is not None:
            hedef.append(f"Shorts {s90:,}/20M (90 gün)".replace(",", "."))
        satirlar.append("   Para kazanma: " + " · ".join(hedef))
        for r in enler[:3]:
            satirlar.append(f"   • {r['baslik'][:40]} — {r['views']} izl., ort. %{round(r.get('averageViewPercentage', 0))} izlendi")
        mesaj += satirlar
    except Exception as e:
        sonuc["kanallar"][k] = {"ad": bilgi["ad"], "hata": str(e)[:300]}
        mesaj.append(f"\n⚠️ {bilgi['ad']}: veri alınamadı ({str(e)[:120]})")

os.makedirs("rapor", exist_ok=True)
json.dump(sonuc, open(f"rapor/{bugun.isoformat()}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(sonuc, open("rapor/son.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
telegram("\n".join(mesaj))
print("\n".join(mesaj))
