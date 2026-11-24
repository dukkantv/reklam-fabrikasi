"""Kanallarda aynı videonun birden fazla yüklenip yüklenmediğini kontrol eder (YouTube, Instagram, Facebook).

Başlık/açıklama normalize edilip karşılaştırılır; aynı (ya da çok benzer) olanlar 'tekrar' sayılır.
Sonuç rapor/tekrar_kontrol.json'a yazılır ve günlüğe basılır.
Kullanım: python tekrar_kontrol.py
"""
import datetime as dt
import json
import os
import re

from yt_ortak import KOK, erisim_anahtari, istek, kanallar, yt

YT_KANALLAR = [k for k in kanallar() if not k.startswith(("ig_", "tt_"))]
IG_KANALLAR = ["dukkantv", "dramabite", "kasakurgu", "gizlitarih", "ilturnuva"]


def norm(s):
    s = (s or "").lower().replace("i̇", "i")
    s = re.sub(r"#\w+", " ", s)
    s = re.sub(r"[^\wçğıöşü/ ]", " ", s)   # "/" kalsın: "Gün 19/30" ile "Gün 20/30" ayrı
    return " ".join(s.split())[:200]


def tekrarlar(liste, anahtar="metin"):
    """[(norm_metin, öğe)] içinde aynı/çok benzer olanları gruplar."""
    gruplar, kullanildi = [], set()
    for i, a in enumerate(liste):
        if i in kullanildi or not a[anahtar]:
            continue
        g = [a]
        for j in range(i + 1, len(liste)):
            b = liste[j]
            if j in kullanildi or not b[anahtar]:
                continue
            if a[anahtar] == b[anahtar]:   # birebir aynı (seri bölümleri "Gün 19/20", "C Grubu" tekrar sayılmaz)
                g.append(b)
                kullanildi.add(j)
        if len(g) > 1:
            gruplar.append(g)
    return gruplar


def youtube():
    sonuc = {}
    for k in YT_KANALLAR:
        try:
            tok = erisim_anahtari(k)
            up = yt(tok, "channels", part="contentDetails", mine="true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            ids, sayfa = [], None
            while True:
                p = {"part": "contentDetails", "playlistId": up, "maxResults": 50}
                if sayfa:
                    p["pageToken"] = sayfa
                r = yt(tok, "playlistItems", **p)
                ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
                sayfa = r.get("nextPageToken")
                if not sayfa:
                    break
            videolar = []
            for i in range(0, len(ids), 50):
                for v in yt(tok, "videos", part="snippet,status,contentDetails,statistics", id=",".join(ids[i:i + 50]))["items"]:
                    videolar.append({"id": v["id"], "baslik": v["snippet"]["title"],
                                     "yayin": v["snippet"]["publishedAt"], "durum": v["status"]["privacyStatus"],
                                     "planli": v["status"].get("publishAt"), "sure": v["contentDetails"]["duration"],
                                     "izlenme": int(v.get("statistics", {}).get("viewCount", 0)),
                                     "metin": norm(v["snippet"]["title"]) + "|" + v["contentDetails"]["duration"]})
            sonuc[k] = {"video_sayisi": len(videolar), "videolar": videolar, "tekrar": tekrarlar(videolar)}
        except Exception as e:
            sonuc[k] = {"hata": str(e)[:300]}
    return sonuc


def meta():
    from ig_ortak import API, ig_hesap
    ig_s, fb_s = {}, {}
    for k in IG_KANALLAR:
        try:
            h = ig_hesap(k)
        except Exception as e:
            ig_s[k] = {"hata": str(e)[:200]}
            continue
        if not h:
            continue
        tok = h["token"]
        if h.get("ig_id"):
            liste, url = [], (f"{API}/{h['ig_id']}/media?fields=id,caption,media_product_type,timestamp,permalink"
                              f"&limit=50&access_token={tok}")
            while url and len(liste) < 300:
                kod, _, r = istek(url)
                if kod != 200:
                    ig_s[k] = {"hata": f"{kod}: {str(r)[:200]}"}
                    break
                liste += r.get("data", [])
                url = (r.get("paging") or {}).get("next")
            g = [{"id": x["id"], "zaman": x.get("timestamp"), "link": x.get("permalink"),
                  "baslik": (x.get("caption") or "")[:90], "metin": norm(x.get("caption"))} for x in liste]
            ig_s.setdefault(k, {}).update({"gonderi_sayisi": len(g), "gonderiler": g, "tekrar": tekrarlar(g)})
        if h.get("sayfa_id"):
            liste, url = [], (f"{API}/{h['sayfa_id']}/videos?fields=id,title,description,created_time,permalink_url,length"
                              f"&limit=50&access_token={tok}")
            while url and len(liste) < 300:
                kod, _, r = istek(url)
                if kod != 200:
                    fb_s[k] = {"hata": f"{kod}: {str(r)[:200]}"}
                    break
                liste += r.get("data", [])
                url = (r.get("paging") or {}).get("next")
            g = [{"id": x["id"], "zaman": x.get("created_time"), "link": x.get("permalink_url"),
                  "baslik": (x.get("title") or x.get("description") or "")[:90],
                  "metin": norm(x.get("title") or x.get("description")) + "|" + str(round(x.get("length") or 0))}
                 for x in liste]
            fb_s.setdefault(k, {}).update({"video_sayisi": len(g), "videolar": g, "tekrar": tekrarlar(g)})
    return ig_s, fb_s


def kuyruk():
    """Yayın kuyruğunda aynı videonun birden fazla kaydı var mı?"""
    klasor = os.path.join(KOK, "kuyruk")
    kayit = []
    for f in sorted(os.listdir(klasor)):
        if f.endswith(".json"):
            j = json.load(open(os.path.join(klasor, f), encoding="utf-8"))
            kayit.append({"id": j.get("id"), "kanal": j.get("kanal"), "durum": j.get("durum"),
                          "baslik": j.get("baslik"), "metin": j.get("kanal", "") + ":" + norm(j.get("baslik"))})
    return {"kayit_sayisi": len(kayit), "kayitlar": kayit, "tekrar": tekrarlar(kayit)}


def main():
    ig, fb = meta()
    sonuc = {"zaman": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).isoformat(timespec="minutes"),
             "youtube": youtube(), "instagram": ig, "facebook": fb, "kuyruk": kuyruk()}
    os.makedirs(os.path.join(KOK, "rapor"), exist_ok=True)
    json.dump(sonuc, open(os.path.join(KOK, "rapor", "tekrar_kontrol.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for platform in ("youtube", "instagram", "facebook"):
        for k, v in sonuc[platform].items():
            if "hata" in v:
                print(f"[{platform}] {k}: HATA {v['hata']}")
                continue
            n = v.get("video_sayisi", v.get("gonderi_sayisi"))
            print(f"[{platform}] {k}: {n} içerik, {len(v['tekrar'])} tekrar grubu")
            for g in v["tekrar"]:
                print("   TEKRAR:", " || ".join(f"{x.get('baslik', '')[:60]} ({x.get('id')}, {x.get('yayin') or x.get('zaman')},"
                                               f" {x.get('durum', '')})" for x in g))
    print(f"[kuyruk] {sonuc['kuyruk']['kayit_sayisi']} kayıt, {len(sonuc['kuyruk']['tekrar'])} tekrar grubu")


if __name__ == "__main__":
    main()
