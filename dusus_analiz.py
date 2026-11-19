# Tek seferlik: son 14 günün video bazlı YouTube metrikleri (kanca, izlenme süresi) -> /tmp/gta_analiz.json
import json
from yt_ortak import analiz, erisim_anahtari, yt
S = {}
for k in ["dukkantv", "dramabite", "kasakurgu", "ilturnuva", "gizlitarih"]:
    try:
        tok = erisim_anahtari(k)
        r = analiz(tok, "2026-11-05", "2026-11-19", "views,engagedViews,averageViewDuration,averageViewPercentage,likes,subscribersGained",
                   dimensions="video", sort="-views", maxResults=40)
        ids = [x[0] for x in r.get("rows", [])]
        bas = {}
        for i in range(0, len(ids), 50):
            for v in yt(tok, "videos", part="snippet,contentDetails", id=",".join(ids[i:i+50])).get("items", []):
                bas[v["id"]] = (v["snippet"]["publishedAt"], v["snippet"]["title"][:50], v["contentDetails"]["duration"])
        kaynak = analiz(tok, "2026-11-05", "2026-11-19", "views", dimensions="day,insightTrafficSourceType")
        S[k] = {"satirlar": [x + list(bas.get(x[0], ("", "", ""))) for x in r.get("rows", [])], "kaynak": kaynak.get("rows", [])}
    except Exception as e:
        S[k] = {"hata": str(e)[:300]}
json.dump(S, open("/tmp/gta_analiz.json", "w"), ensure_ascii=False)
