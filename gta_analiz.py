# Tek seferlik analiz: 19 Kasım 11:00 GTA 6 özel bölümü kanallara ne kazandırdı?
# YouTube: kanal toplamları + son 15 videonun yayın saati ve izlenme/beğeni/yorum sayıları
# Instagram: takipçi + son 15 gönderinin izlenme/erişim/beğeni/paylaşım/kaydetme sayıları
# Facebook: sayfa takipçisi + GTA videosunun izlenmesi. Çıktı: /tmp/gta_analiz.json
import datetime as dt
import glob
import json

from yt_ortak import analiz, erisim_anahtari, kanallar, yt

KANALLAR = ["dukkantv", "dramabite", "kasakurgu", "gizlitarih", "ilturnuva"]
sonuc = {"zaman": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).isoformat(timespec="minutes"), "yt": {}, "ig": {}, "fb": {}}

gta = {}
for p in glob.glob("kuyruk/arsiv/*.json") + glob.glob("kuyruk/*.json"):
    k = json.load(open(p))
    if "GTA" in k.get("baslik", "") and k.get("yayin", "").startswith("2026-11-19"):
        gta[k["kanal"]] = k

for kanal in KANALLAR:
    try:
        tok = erisim_anahtari(kanal)
        ch = yt(tok, "channels", part="statistics,contentDetails", mine="true")["items"][0]
        up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt(tok, "playlistItems", part="contentDetails", playlistId=up, maxResults=15)
        ids = [x["contentDetails"]["videoId"] for x in pl.get("items", [])]
        vs = yt(tok, "videos", part="snippet,statistics,contentDetails", id=",".join(ids)).get("items", [])
        videolar = [{"id": v["id"], "baslik": v["snippet"]["title"][:70], "yayin": v["snippet"]["publishedAt"],
                     "sure": v["contentDetails"]["duration"], **{a: int(b) for a, b in v["statistics"].items() if b.isdigit()}}
                    for v in vs]
        gunluk = {}
        try:
            r = analiz(tok, "2026-11-12", "2026-11-19", "views,subscribersGained,subscribersLost,likes", dimensions="day")
            gunluk = {row[0]: row[1:] for row in r.get("rows", [])}
        except Exception as e:
            gunluk = {"hata": str(e)[:200]}
        sonuc["yt"][kanal] = {"istatistik": ch["statistics"], "videolar": videolar, "gunluk": gunluk,
                              "gta_id": gta.get(kanal, {}).get("video_id")}
    except Exception as e:
        sonuc["yt"][kanal] = {"hata": str(e)[:300]}

try:
    from ig_ortak import API, ig_hesap
    from yt_ortak import istek
    for kanal in KANALLAR:
        try:
            h = ig_hesap(kanal)
            if not h:
                sonuc["ig"][kanal] = {"hata": "bağlı değil"}; continue
            tok, ig = h["token"], h["ig_id"]
            _, _, hes = istek(f"{API}/{ig}?fields=username,followers_count,media_count&access_token={tok}")
            _, _, med = istek(f"{API}/{ig}/media?fields=id,caption,timestamp,like_count,comments_count,media_product_type"
                              f"&limit=15&access_token={tok}")
            liste = (med or {}).get("data", [])
            for x in liste:
                x["caption"] = (x.get("caption") or "")[:60]
                kod, _, ins = istek(f"{API}/{x['id']}/insights?metric=views,reach,saved,shares,total_interactions,follows"
                                    f"&access_token={tok}")
                if kod != 200:
                    kod, _, ins = istek(f"{API}/{x['id']}/insights?metric=views,reach,saved,shares&access_token={tok}")
                if kod == 200:
                    x.update({d["name"]: (d.get("values") or [{}])[0].get("value", 0) for d in ins.get("data", [])})
            gunluk = {}
            kod, _, gi = istek(f"{API}/{ig}/insights?metric=follower_count&period=day&access_token={tok}")
            if kod == 200:
                gunluk = {v["end_time"][:10]: v["value"] for d in gi.get("data", []) for v in d.get("values", [])}
            sonuc["ig"][kanal] = {"hesap": hes, "medya": liste, "takipci_gunluk": gunluk,
                                  "gta_id": gta.get(kanal, {}).get("ig_id")}
            # Facebook: GTA videosu
            fid = gta.get(kanal, {}).get("fb_id")
            if fid:
                _, _, fv = istek(f"https://graph.facebook.com/v21.0/{fid}?fields=views,likes.summary(true),"
                                 f"comments.summary(true)&access_token={tok}")
                sonuc["fb"][kanal] = fv
        except Exception as e:
            sonuc["ig"][kanal] = {"hata": str(e)[:300]}
except Exception as e:
    sonuc["ig"]["genel_hata"] = str(e)[:300]

json.dump(sonuc, open("/tmp/gta_analiz.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: {kk: (vv.get("istatistik") if isinstance(vv, dict) else vv) for kk, vv in v.items()}
                  for k, v in sonuc.items() if k == "yt"}, ensure_ascii=False)[:2000])
