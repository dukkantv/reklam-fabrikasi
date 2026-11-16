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

KANALLAR = ["dukkantv", "dramabite", "kasakurgu", "gizlitarih", "ilturnuva"]
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


FB_WEB = {"dukkantv": "https://dukkantv.github.io/",
          "dramabite": "https://www.youtube.com/@dramabitetr",
          "kasakurgu": "https://www.youtube.com/@kasakurgu",
          "ilturnuva": "https://www.youtube.com/@81ilturnuvasi"}


def facebook():
    """Facebook sayfalarına web sitesi linki ve kapak fotoğrafı (bannerlar/fb_<kanal>.jpg) koyar."""
    import subprocess
    from ig_ortak import API, ig_hesap
    for kanal, web in FB_WEB.items():
        h = ig_hesap(kanal)
        pid = h and (h.get("sayfa_id") or h.get("page_id"))
        if not pid:
            print(kanal, "Facebook sayfası bilgisi yok")
            continue
        tok = h["token"]
        kod, _, v = istek(f"{API}/{pid}", veri={"website": web, "access_token": tok})
        print(kanal, "web sitesi:", "tamam" if kod == 200 else f"HATA {kod} {str(v)[:250]}")
        yol = os.path.join(KOK, "bannerlar", f"fb_{kanal}.jpg")
        if not os.path.exists(yol):
            continue
        r = subprocess.run(["curl", "-sS", "-F", f"source=@{yol}", "-F", "published=false",
                            "-F", f"access_token={tok}", f"{API}/{pid}/photos"], capture_output=True, text=True)
        try:
            foto = json.loads(r.stdout).get("id")
        except Exception:
            foto = None
        if not foto:
            print(kanal, "kapak yüklenemedi:", (r.stdout or r.stderr)[:250])
            continue
        kod, _, v = istek(f"{API}/{pid}", veri={"cover": foto, "access_token": tok})
        print(kanal, "kapak fotoğrafı:", "tamam" if kod == 200 else f"HATA {kod} {str(v)[:250]}")


def liste_adi(kanal, eski, yeni):
    for p in yt_get(kanal, "playlists?part=snippet&mine=true&maxResults=50").get("items", []):
        if p["snippet"]["title"] == eski:
            sn = p["snippet"]
            sn["title"] = yeni
            kod, _, v = istek(f"{YT}/playlists?part=snippet", method="PUT",
                              headers={"Authorization": f"Bearer {erisim_anahtari(kanal)}"},
                              json_govde={"id": p["id"], "snippet": {"title": yeni, "description": sn.get("description", "")}})
            print(kanal, "liste adı:", eski, "→", yeni, "tamam" if kod == 200 else f"HATA {kod} {str(v)[:200]}")


ESKI_ISARETLER = ("Reklam Çektik", "Öz Getirenler", "Eserim", "Bursa Dedektifleri", "reklam videosu",
                  "Toptan Gıda", "Perde mi lazım")


def esnaf_gizle():
    """Dükkan TV'de eski esnaf reklam sisteminden kalan videoları GİZLİ yapar (silmez, geri açılabilir)."""
    from yt_ortak import yt
    tok = erisim_anahtari("dukkantv")
    up = yt(tok, "channels", part="contentDetails", mine="true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           yt(tok, "playlistItems", part="contentDetails", playlistId=up, maxResults=50).get("items", [])]
    for it in yt(tok, "videos", part="snippet,status", id=",".join(ids)).get("items", []):
        sn, stt = it["snippet"], it["status"]
        metin = sn["title"] + " " + sn.get("description", "")
        eski = any(i.lower() in metin.lower() for i in ESKI_ISARETLER)
        print(("GİZLE " if eski else "kalsın"), stt.get("privacyStatus"), "|", sn["title"][:70])
        if eski and stt.get("privacyStatus") != "private":
            kod, _, v = istek(f"{YT}/videos?part=status", method="PUT", headers={"Authorization": f"Bearer {tok}"},
                              json_govde={"id": it["id"], "status": {"privacyStatus": "private",
                                                                    "selfDeclaredMadeForKids": False}})
            print("   →", "gizlendi" if kod == 200 else f"HATA {kod} {str(v)[:200]}")


def profil():
    """Kasım 2026 profesyonel profil düzenlemesi: bannerlar + Facebook + liste adı."""
    banner()
    facebook()
    liste_adi("dukkantv", "Esnaf Reklamları 🏪", "Esnaf Videoları 🏪")


def videolar():
    """Her kanalın son 20 yüklemesi: durum, yayın zamanı, başlık (çift/yanlış zamanlama denetimi)."""
    for kanal in KANALLAR:
        try:
            up = yt_get(kanal, "channels?part=contentDetails&mine=true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            ids = [i["contentDetails"]["videoId"] for i in
                   yt_get(kanal, f"playlistItems?part=contentDetails&maxResults=20&playlistId={up}")["items"]]
            v = yt_get(kanal, "videos?part=snippet,status,statistics,contentDetails&id=" + ",".join(ids))["items"]
            print(f"\n===== {kanal}")
            for x in v:
                s = x["status"]
                print("VID", kanal, x["id"], s["privacyStatus"], s.get("publishAt", x["snippet"]["publishedAt"])[:16],
                      "cocuk=" + str(s.get("madeForKids")), "izl=" + x.get("statistics", {}).get("viewCount", "?"),
                      x["contentDetails"]["duration"], "|", x["snippet"]["title"][:60])
        except Exception as e:
            print(kanal, "HATA", e)


def turnuva_profil():
    """81 İl Turnuvası: YouTube kapak + oynatma listesi, Facebook sayfası kapak/profil fotoğrafı/web/açıklama."""
    global KANALLAR, FB_WEB
    import subprocess
    from ig_ortak import API, ig_hesap
    eski_k, eski_f = KANALLAR, FB_WEB
    KANALLAR, FB_WEB = ["ilturnuva"], {"ilturnuva": eski_f["ilturnuva"]}
    try:
        guncelle(); banner(); facebook(); listeler()
    finally:
        KANALLAR, FB_WEB = eski_k, eski_f
    h = ig_hesap("ilturnuva")
    pid, tok = h.get("sayfa_id") or h.get("page_id"), h["token"]
    yol = os.path.join(KOK, "bannerlar", "ilturnuva-profil.png")
    r = subprocess.run(["curl", "-sS", "-F", f"source=@{yol}", "-F", f"access_token={tok}", f"{API}/{pid}/picture"],
                       capture_output=True, text=True)
    print("facebook profil fotoğrafı:", r.stdout[:200] or r.stderr[:200])
    aciklama = json.load(open(os.path.join(KOK, "kanal_ayarlari.json"), encoding="utf-8"))["ilturnuva"]["aciklama"]
    for alan, deger in (("about", "81 il fizik oyunlarında kapışıyor! Her akşam yeni maç 🏆"), ("description", aciklama)):
        kod, _, v = istek(f"{API}/{pid}", veri={alan: deger, "access_token": tok})
        print("facebook", alan, "tamam" if kod == 200 else f"HATA {kod} {str(v)[:200]}")


def fikstur_paylas():
    """81 İl fikstür görselini (spoilersiz) Facebook sayfasına ve Instagram'a fotoğraf olarak paylaşır."""
    import subprocess, time, datetime as dt
    sys.path.insert(0, os.path.join(KOK, "arena"))
    from fikstur import ciz
    from ig_ortak import API, ig_hesap
    s = json.load(open(os.path.join(KOK, "arena", "sezon.json"), encoding="utf-8"))
    yol = ciz(s, "/tmp/fikstur.jpg", dt.date.fromisoformat(s["baslangic"]))
    metin = (f"🗓 81 İl Turnuvası · Sezon {s['sezon']} fikstürü!\n\n"
             "9 grup, 81 il. Her grubun son 3 kalanı tur atlar, 9 il büyük finalde kapışır. "
             "Her akşam yeni maç 🏆\n\nŞehrin hangi grupta? Yorumlara yaz, takımını destekle! 👇\n\n"
             "#81ilturnuvası #türkiye #fikstür #şehirler #simülasyon #ilil")
    h = ig_hesap("ilturnuva")
    tok, sayfa, ig = h["token"], h.get("sayfa_id") or h.get("page_id"), h["ig_id"]
    r = subprocess.run(["curl", "-sS", "-F", f"source=@{yol}", "-F", f"caption={metin}", "-F", "published=true",
                        "-F", f"access_token={tok}", f"{API}/{sayfa}/photos"], capture_output=True, text=True)
    fb = json.loads(r.stdout or "{}")
    print("facebook:", fb)
    foto = fb.get("id")
    if not foto:
        return
    _, _, d = istek(f"{API}/{foto}?fields=images&access_token={tok}")
    url = max(d["images"], key=lambda i: i["width"])["source"]
    kod, _, kap = istek(f"{API}/{ig}/media", veri={"image_url": url, "caption": metin, "access_token": tok})
    print("instagram kapsayıcı:", kod, kap)
    for _ in range(12):
        _, _, st = istek(f"{API}/{kap['id']}?fields=status_code&access_token={tok}")
        if (st or {}).get("status_code") == "FINISHED":
            break
        time.sleep(5)
    kod, _, yay = istek(f"{API}/{ig}/media_publish", veri={"creation_id": kap["id"], "access_token": tok})
    print("instagram:", kod, yay)


def yorum_dene():
    """Mevcut 'youtube' izniyle kanal adına yorum yazılabiliyor mu? (81 İl A Grubu videosuna seri listesi yorumu)"""
    pid = kanal_listeleri("ilturnuva")[0][0]
    try:
        v = yt_post("ilturnuva", "commentThreads?part=snippet", {"snippet": {
            "videoId": "IBiS8dwf2Tk", "topLevelComment": {"snippet": {"textOriginal":
                f"🏆 Bütün maçlar sırayla burada 👉 https://www.youtube.com/playlist?list={pid}\n"
                "Şehrin hangi grupta? Yorumlara yaz, takip et, maçını kaçırma!"}}}})
        print("YORUM TAMAM", v.get("id"))
    except Exception as e:
        print("YORUM HATA", str(e)[:400])


def tanitim():
    """Her kanalın en çok izlenen herkese açık videosunu kanal sayfasının tanıtım videosu (abone olmayanlara
    gösterilen) yapar. Daha iyi bir video öne geçerse tekrar çalıştırmak yeterli."""
    for kanal in KANALLAR:
        try:
            yuk = yt_get(kanal, "channels?part=contentDetails&mine=true")["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            idler = [v["contentDetails"]["videoId"] for v in
                     yt_get(kanal, f"playlistItems?part=contentDetails&maxResults=50&playlistId={yuk}").get("items", [])]
            if not idler:
                print(kanal, "video yok"); continue
            vs = yt_get(kanal, "videos?part=statistics,status,snippet&id=" + ",".join(idler[:50])).get("items", [])
            vs = [v for v in vs if v["status"].get("privacyStatus") == "public"]
            if not vs:
                print(kanal, "herkese açık video yok"); continue
            en = max(vs, key=lambda v: int(v["statistics"].get("viewCount", 0)))
            c = yt_get(kanal, "channels?part=brandingSettings&mine=true")["items"][0]
            ch = c.get("brandingSettings", {}).get("channel", {})
            if ch.get("unsubscribedTrailer") == en["id"]:
                print(kanal, "tanıtım videosu zaten:", en["snippet"]["title"][:50]); continue
            ch["unsubscribedTrailer"] = en["id"]
            yt_post(kanal, "channels?part=brandingSettings", {"id": c["id"], "brandingSettings": {"channel": ch}}, method="PUT")
            print(kanal, "tanıtım videosu:", en["snippet"]["title"][:50], en["statistics"].get("viewCount"), "izlenme")
        except Exception as e:
            print(kanal, "tanıtım HATA:", str(e)[:300])


def eksikleri_tamamla():
    """16 Kasım 2026 denetimi: tanıtım videoları, eksik oynatma listeleri (Gizli Tarih), Facebook web bağlantıları."""
    for ad, fn in (("tanıtım", tanitim), ("listeler", listeler), ("facebook", facebook)):
        print(f"\n######## {ad}")
        try:
            fn()
        except Exception as e:
            print(ad, "HATA:", str(e)[:300])


if __name__ == "__main__":
    {"denetle": denetle, "guncelle": guncelle, "listeler": listeler, "banner": banner,
     "facebook": facebook, "profil": profil, "esnaf_gizle": esnaf_gizle, "videolar": videolar, "turnuva_profil": turnuva_profil, "fikstur_paylas": fikstur_paylas, "yorum_dene": yorum_dene,
     "tanitim": tanitim, "eksikleri_tamamla": eksikleri_tamamla}[sys.argv[1]]()
