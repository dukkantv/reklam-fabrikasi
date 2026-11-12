"""Kanal profil ayarları: YouTube kanallarını (ve Instagram hesaplarını) denetler, YouTube ayarlarını günceller.

Kullanım:
  python3 kanal_ayar.py denetle                 # 3 kanalın eksiklerini yazdırır
  python3 kanal_ayar.py guncelle                # kanal_ayarlari.json'daki YouTube ayarlarını uygular
"""
import json
import os
import sys

from yt_ortak import KOK, erisim_anahtari, istek

KANALLAR = ["dukkantv", "dramabite", "kasakurgu"]
YT = "https://www.googleapis.com/youtube/v3"


def yt_get(kanal, yol):
    tok = erisim_anahtari(kanal)
    kod, _, veri = istek(f"{YT}/{yol}", headers={"Authorization": f"Bearer {tok}"})
    if kod != 200:
        raise RuntimeError(f"{kanal} {yol}: {kod} {str(veri)[:300]}")
    return veri


def denetle():
    for kanal in KANALLAR:
        print(f"\n===================== {kanal} (YouTube)")
        try:
            c = yt_get(kanal, "channels?part=snippet,brandingSettings,status,statistics,contentDetails&mine=true")["items"][0]
        except Exception as e:
            print("HATA:", e)
            continue
        sn, br, st = c["snippet"], c.get("brandingSettings", {}), c.get("status", {})
        ch = br.get("channel", {})
        print(json.dumps({
            "ad": sn.get("title"), "kullanici_adi": sn.get("customUrl"),
            "aciklama": sn.get("description"), "ulke": sn.get("country") or ch.get("country"),
            "dil": sn.get("defaultLanguage") or ch.get("defaultLanguage"),
            "anahtar_kelimeler": ch.get("keywords"), "tanitim_videosu": ch.get("unsubscribedTrailer"),
            "cocuklara_yonelik": st.get("madeForKids"), "istatistik": c.get("statistics"),
            "banner": bool(br.get("image", {}).get("bannerExternalUrl")),
            "profil_resmi": sn.get("thumbnails", {}).get("default", {}).get("url", "")[:60],
        }, ensure_ascii=False, indent=1))
        try:
            pl = yt_get(kanal, "playlists?part=snippet&mine=true&maxResults=50")
            print("Oynatma listeleri:", [p["snippet"]["title"] for p in pl.get("items", [])])
        except Exception as e:
            print("Oynatma listesi okunamadı:", e)
        ig_denetle(kanal)


def ig_denetle(kanal):
    try:
        from ig_ortak import API, ig_hesap
        h = ig_hesap(kanal)
        if not h:
            print("Instagram bağlı değil")
            return
        _, _, d = istek(f"{API}/{h['ig_id']}?fields=username,name,biography,website,followers_count,media_count,"
                        f"profile_picture_url&access_token={h['token']}")
        d.pop("id", None)
        d["profile_picture_url"] = bool(d.get("profile_picture_url"))
        print("Instagram:", json.dumps(d, ensure_ascii=False))
        if h.get("sayfa_id") or h.get("page_id"):
            pid = h.get("sayfa_id") or h.get("page_id")
            _, _, p = istek(f"{API}/{pid}?fields=name,about,website,category_list,emails,phone&access_token={h['token']}")
            print("Facebook sayfası:", json.dumps(p, ensure_ascii=False)[:500])
    except Exception as e:
        print("Instagram okunamadı:", str(e)[:200])


def guncelle():
    ayar = json.load(open(os.path.join(KOK, "kanal_ayarlari.json"), encoding="utf-8"))
    for kanal, a in ayar.items():
        if kanal.startswith("_"):
            continue
        c = yt_get(kanal, "channels?part=snippet,brandingSettings&mine=true")["items"][0]
        br = c.get("brandingSettings", {})
        ch = br.get("channel", {})
        ch["description"] = a["aciklama"]
        ch["keywords"] = a["anahtar_kelimeler"]
        ch["country"] = "TR"
        ch["defaultLanguage"] = "tr"
        govde = {"id": c["id"], "brandingSettings": {"channel": ch}}
        tok = erisim_anahtari(kanal)
        kod, _, veri = istek(f"{YT}/channels?part=brandingSettings", method="PUT",
                             headers={"Authorization": f"Bearer {tok}"}, json_govde=govde)
        print(kanal, "güncellendi" if kod == 200 else f"HATA {kod} {str(veri)[:300]}")


if __name__ == "__main__":
    {"denetle": denetle, "guncelle": guncelle}[sys.argv[1]]()
