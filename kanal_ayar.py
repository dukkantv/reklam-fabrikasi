"""Kanal profil ayarları: YouTube kanallarını (ve Instagram hesaplarını) denetler, YouTube ayarlarını günceller.

Kullanım:
  python3 kanal_ayar.py denetle                 # 3 kanalın eksiklerini yazdırır
  python3 kanal_ayar.py guncelle                # kanal_ayarlari.json'daki YouTube ayarlarını uygular
  python3 kanal_ayar.py listeler                # oynatma listelerini kurar, eski videoları kurallara göre ekler
  python3 kanal_ayar.py banner                  # bannerlar/<kanal>.png dosyalarını kapak görseli yapar
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


def ayarlar():
    return json.load(open(os.path.join(KOK, "kanal_ayarlari.json"), encoding="utf-8"))


def kural_uyar(kural, baslik):
    if kural == "*":
        return True
    if kural.startswith("!"):
        return kural[1:].lower() not in baslik.lower()
    return kural.lower() in baslik.lower()


def yt_post(kanal, yol, govde, method="POST"):
    tok = erisim_anahtari(kanal)
    kod, _, veri = istek(f"{YT}/{yol}", method=method, headers={"Authorization": f"Bearer {tok}"}, json_govde=govde)
    if kod not in (200, 201):
        raise RuntimeError(f"{kanal} {yol}: {kod} {str(veri)[:300]}")
    return veri


def kanal_listeleri(kanal, olustur=False):
    """Kurallardaki oynatma listelerinin id'lerini döndürür; olustur=True ise eksikleri açar."""
    mevcut = {p["snippet"]["title"]: p["id"] for p in
              yt_get(kanal, "playlists?part=snippet&mine=true&maxResults=50").get("items", [])}
    sonuc = []
    for l in ayarlar().get(kanal, {}).get("listeler", []):
        pid = mevcut.get(l["ad"])
        if not pid and olustur:
            pid = yt_post(kanal, "playlists?part=snippet,status", {
                "snippet": {"title": l["ad"], "description": l["aciklama"], "defaultLanguage": "tr"},
                "status": {"privacyStatus": "public"}})["id"]
            print(f"{kanal}: liste açıldı → {l['ad']}")
        if pid:
            sonuc.append((pid, l))
    return sonuc


def listeye_ekle(kanal, video_id, baslik, listeler=None):
    """Yeni yüklenen videoyu kuralına uyan oynatma listesine ekler (yt_kuyruk.py yüklemeden sonra çağırır)."""
    for pid, l in (listeler if listeler is not None else kanal_listeleri(kanal)):
        if kural_uyar(l["kural"], baslik):
            yt_post(kanal, "playlistItems?part=snippet", {"snippet": {
                "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": video_id}}})
            print(f"{kanal}: {baslik[:40]} → {l['ad']}")


def listeler():
    for kanal in KANALLAR:
        ls = kanal_listeleri(kanal, olustur=True)
        yuklemeler = yt_get(kanal, "channels?part=contentDetails&mine=true")["items"][0]["contentDetails"][
            "relatedPlaylists"]["uploads"]
        videolar, sayfa = [], ""
        while True:
            v = yt_get(kanal, f"playlistItems?part=snippet,status&maxResults=50&playlistId={yuklemeler}{sayfa}")
            videolar += v.get("items", [])
            if not v.get("nextPageToken"):
                break
            sayfa = "&pageToken=" + v["nextPageToken"]
        for pid, l in ls:
            try:
                icinde = {i["snippet"]["resourceId"]["videoId"] for i in
                          yt_get(kanal, f"playlistItems?part=snippet&maxResults=50&playlistId={pid}").get("items", [])}
            except RuntimeError:  # yeni açılan liste birkaç saniye görünmeyebilir: boş say
                import time
                time.sleep(5)
                icinde = set()
            # eskiden yeniye ekle ki liste sırası doğal olsun
            for it in reversed(videolar):
                vid, bas = it["snippet"]["resourceId"]["videoId"], it["snippet"]["title"]
                if vid in icinde or not kural_uyar(l["kural"], bas):
                    continue
                try:
                    yt_post(kanal, "playlistItems?part=snippet", {"snippet": {
                        "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}})
                    print(f"{kanal}: + {bas[:50]} → {l['ad']}")
                except Exception as e:
                    print("Eklenemedi:", bas[:40], str(e)[:150])


def banner():
    for kanal in KANALLAR:
        yol = os.path.join(KOK, "bannerlar", f"{kanal}.png")
        if not os.path.exists(yol):
            continue
        tok = erisim_anahtari(kanal)
        kod, _, veri = istek("https://www.googleapis.com/upload/youtube/v3/channelBanners/insert?uploadType=media",
                             method="POST", ham=open(yol, "rb").read(),
                             headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/png"})
        if kod not in (200, 201) or "url" not in veri:
            print(kanal, "banner yüklenemedi:", kod, str(veri)[:300])
            continue
        c = yt_get(kanal, "channels?part=brandingSettings&mine=true")["items"][0]
        br = c.get("brandingSettings", {})
        govde = {"id": c["id"], "brandingSettings": {"channel": br.get("channel", {}),
                                                     "image": {"bannerExternalUrl": veri["url"]}}}
        kod, _, v2 = istek(f"{YT}/channels?part=brandingSettings", method="PUT",
                           headers={"Authorization": f"Bearer {tok}"}, json_govde=govde)
        print(kanal, "banner ayarlandı" if kod == 200 else f"HATA {kod} {str(v2)[:300]}")


if __name__ == "__main__":
    {"denetle": denetle, "guncelle": guncelle, "listeler": listeler, "banner": banner}[sys.argv[1]]()
