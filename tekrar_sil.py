"""rapor/tekrar_kontrol.json'daki tekrar gruplarında birer kopya bırakıp fazlalarını siler (YouTube + Instagram).

Kalan kopya: en çok izlenen; eşitlikte yayın kuyruğunun kaydındaki (video_id / ig_id), o da yoksa ilk yüklenen.
Levent 24 Kas 2026'da onayladı ("Evet, hepsini sil"). Sadece son 3 günün tekrarları silinir.
Kullanım: python tekrar_sil.py [deneme]
"""
import datetime as dt
import glob
import json
import os
import sys

from yt_ortak import KOK, erisim_anahtari, istek

DENEME = len(sys.argv) > 1 and sys.argv[1] == "deneme"
SINIR = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)


def kuyruk_idleri():
    yt_ids, ig_ids = set(), set()
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")) + glob.glob(os.path.join(KOK, "kuyruk", "arsiv", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(k, dict):
            yt_ids.add(k.get("video_id"))
            ig_ids.add(k.get("ig_id"))
    return yt_ids, ig_ids


def zaman(x):
    z = x.get("yayin") or x.get("zaman") or ""
    try:
        return dt.datetime.strptime(z[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def main():
    d = json.load(open(os.path.join(KOK, "rapor", "tekrar_kontrol.json"), encoding="utf-8"))
    yt_ids, ig_ids = kuyruk_idleri()
    ozet = []
    for platform, kayitli in (("youtube", yt_ids), ("instagram", ig_ids)):
        for kanal, v in d.get(platform, {}).items():
            for g in v.get("tekrar", []):
                g = [x for x in g if zaman(x) >= SINIR]
                if len(g) < 2:
                    continue
                kalan = sorted(g, key=lambda x: (-(x.get("izlenme") or 0), x["id"] not in kayitli, zaman(x)))[0]
                silinecek = [x for x in g if x["id"] != kalan["id"]]
                print(f"[{platform}] {kanal}: '{kalan['baslik'][:50]}' kalan {kalan['id']} "
                      f"(izl {kalan.get('izlenme', '-')}), silinecek {len(silinecek)}")
                tamam = 0
                for x in silinecek:
                    if DENEME:
                        continue
                    if platform == "youtube":
                        tok = erisim_anahtari(kanal)
                        kod, _, r = istek(f"https://www.googleapis.com/youtube/v3/videos?id={x['id']}", method="DELETE",
                                          headers={"Authorization": f"Bearer {tok}"})
                        ok = kod == 204
                    else:
                        from ig_ortak import API, ig_hesap
                        h = ig_hesap(kanal)
                        kod, _, r = istek(f"{API}/{x['id']}?access_token={h['token']}", method="DELETE")
                        ok = kod == 200
                    if ok:
                        tamam += 1
                    else:
                        print(f"   silinemedi {x['id']}: {kod} {str(r)[:200]}")
                ozet.append({"platform": platform, "kanal": kanal, "baslik": kalan["baslik"][:80], "kalan": kalan["id"],
                             "silinecek": len(silinecek), "silinen": tamam})
    json.dump(ozet, open(os.path.join(KOK, "rapor", "tekrar_sil.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("TOPLAM:", sum(o["silinen"] for o in ozet), "/", sum(o["silinecek"] for o in ozet), "silindi")


if __name__ == "__main__":
    main()
