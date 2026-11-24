"""Her sabah 3 markanın (Dükkan TV, Drama Bite, Kasa Kurgu) YouTube / Instagram / TikTok raporu.

Bilgisayar gerekmez; GitHub'da çalışır. Telegram'a her platform AYRI mesaj olarak gelir:
  📺 YOUTUBE  →  📸 INSTAGRAM  →  🎵 TIKTOK  →  ⏳ Onay bekleyenler (butonlu) + ⚙️ sistem uyarıları
Sonuç rapor/<tarih>.json ve rapor/son.json dosyasına yazılır (Claude'un sabah görevi bunu okur).

"Son 24 saat" = dünkü rapor dosyasıyla bugünkü toplamların farkı (YouTube Analytics 1-2 gün geriden gelir).
"""
import datetime as dt
import glob
import json
import os
import time

from yt_ortak import KOK, analiz, erisim_anahtari, kanal_bilgi, kanallar, telegram, yt

TR = dt.timezone(dt.timedelta(hours=3))
bugun = dt.datetime.now(TR).date()
gun = lambda n: (bugun - dt.timedelta(days=n)).isoformat()
YETKI = {"dukkantv": "Yayın", "dramabite": "Yayın", "kasakurgu": "Yayın", "ilturnuva": "Yayın", "gizlitarih": "Yayın"}
SIRA = ["ilturnuva", "kasakurgu", "dramabite", "dukkantv"]
AD = {"dukkantv": "Dükkan TV", "dramabite": "Drama Bite", "kasakurgu": "Kasa Kurgu",
      "ilturnuva": "81 İl", "gizlitarih": "Gizli Tarih"}


def onceki_rapor():
    """Bugünden önceki en yeni rapor (24 saatlik fark için)."""
    for yol in sorted(glob.glob(os.path.join(KOK, "rapor", "20*.json")), reverse=True):
        if os.path.basename(yol)[:10] < bugun.isoformat():
            try:
                return json.load(open(yol, encoding="utf-8"))
            except Exception:
                pass
    return {}


ONCEKI = onceki_rapor()


def fark(yeni, eski):
    if yeni is None or eski is None:
        return "?"
    return f"{yeni - eski:+d}"


def sayi(n):
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)


def baslik(gonderi):
    satir = [x for x in (gonderi.get("caption") or "").splitlines() if x.strip()]
    return satir[0][:38] if satir else "(başlıksız)"


def tablo(cevap):
    adlar = [c["name"] for c in cevap.get("columnHeaders", [])]
    return [dict(zip(adlar, satir)) for satir in cevap.get("rows", []) or []]


# ───────────────────────────── YOUTUBE ─────────────────────────────
def youtube():
    sonuc, satirlar = {}, ["📺 YOUTUBE — " + bugun.strftime("%d.%m.%Y")]
    eski = ONCEKI.get("kanallar", {})
    for k in sorted((x for x in kanallar() if not x.startswith(("ig_", "tt_"))),
                    key=lambda x: SIRA.index(x) if x in SIRA else 9):
        bilgi = kanal_bilgi(k)
        etiket = f"{AD.get(k, bilgi.get('ad', k))} ({YETKI.get(k, '?')})"
        try:
            token = erisim_anahtari(k)
            ist = yt(token, "channels", part="statistics", mine="true")["items"][0]["statistics"]

            def toplam(bas, bit, metrik, **ek):
                try:
                    s = tablo(analiz(token, bas, bit, metrik, **ek))
                    return s[0] if s else {}
                except Exception as e:
                    print(k, "analiz hatası:", metrik, e)
                    return None

            def tur_bazli(bas, metrik):
                try:
                    return {r["creatorContentType"]: r[metrik] for r in
                            tablo(analiz(token, bas, gun(0), metrik, dimensions="creatorContentType"))}
                except Exception as e:
                    print(k, "tür tablosu alınamadı:", e)
                    return None

            m = "views,estimatedMinutesWatched,subscribersGained,subscribersLost"
            son28 = toplam(gun(28), gun(0), m) or {}
            son7 = toplam(gun(7), gun(0), m + ",averageViewPercentage,likes,comments") or {}
            once7 = toplam(gun(14), gun(8), "views") or {}
            t365, t90 = tur_bazli(gun(365), "estimatedMinutesWatched"), tur_bazli(gun(90), "views")
            saat_uzun = None if t365 is None else round(t365.get("videoOnDemand", t365.get("VIDEO_ON_DEMAND", 0)) / 60, 1)
            s90 = None if t90 is None else t90.get("shorts", t90.get("SHORTS", 0))

            enler = []
            # "engagedViews": ilk saniyelerden sonra izlemeye devam edenler (Shorts'ta kancanın en güçlü sinyali).
            # Analytics API bu metriği vermezse eski metriklerle devam edilir.
            for metrikler in ("views,engagedViews,averageViewDuration,averageViewPercentage,likes,comments",
                              "views,averageViewDuration,averageViewPercentage,likes,comments"):
                try:
                    enler = tablo(analiz(token, gun(7), gun(0), metrikler,
                                         dimensions="video", sort="-views", maxResults=10))
                    break
                except Exception as e:
                    print(k, "video tablosu alınamadı:", metrikler.split(",")[1], e)
            if enler:
                adlar = {v["id"]: v["snippet"]["title"] for v in
                         yt(token, "videos", part="snippet", id=",".join(r["video"] for r in enler))["items"]}
                for r in enler:
                    r["baslik"] = adlar.get(r["video"], r["video"])

            # 23 Kas 2026: konu analizi için son 28 günün bütün videoları (hangi konu daha çok izleniyor?)
            tum28 = []
            for metrikler in ("views,engagedViews,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
                              "views,averageViewDuration,averageViewPercentage,likes,comments"):
                try:
                    tum28 = tablo(analiz(token, gun(28), gun(0), metrikler,
                                         dimensions="video", sort="-views", maxResults=50))
                    break
                except Exception as e28:
                    print(k, "28 günlük video tablosu alınamadı:", e28)
            if tum28:
                try:
                    ad28 = {v["id"]: (v["snippet"]["title"], v["snippet"]["publishedAt"][:10]) for v in
                            yt(token, "videos", part="snippet", id=",".join(r["video"] for r in tum28))["items"]}
                    for r in tum28:
                        r["baslik"], r["yayin"] = ad28.get(r["video"], (r["video"], ""))
                except Exception as e28:
                    print(k, "28 günlük başlıklar alınamadı:", e28)

            abone, izl = int(ist.get("subscriberCount", 0)), int(ist.get("viewCount", 0))
            e = eski.get(k, {})
            sonuc[k] = {"ad": bilgi["ad"], "abone": abone, "toplam_izlenme": izl,
                        "video_sayisi": int(ist.get("videoCount", 0)), "son28": son28, "son7": son7,
                        "onceki7_izlenme": once7.get("views"), "uzun_video_saat_365": saat_uzun,
                        "shorts_izlenme_90": s90, "en_iyi_7gun": enler[:5], "videolar_28gun": tum28,
                        "en_kotu_7gun": [r for r in enler if r.get("views", 0) > 0][-1:] if len(enler) > 1 else [],
                        "son24": {"izlenme": fark(izl, e.get("toplam_izlenme")),
                                  "abone": fark(abone, e.get("abone"))}}

            satirlar.append(f"\n▶️ {etiket}")
            satirlar.append(f"   24 saat: {sonuc[k]['son24']['izlenme']} izlenme, {sonuc[k]['son24']['abone']} abone"
                            f" · toplam {abone} abone")
            v7, v_once = son7.get("views", 0), once7.get("views")
            degisim = ""
            if v_once:
                oran = round((v7 - v_once) / v_once * 100)
                degisim = f" ({oran:+d}% önceki haftaya göre{' ⚠️ düşüş' if oran <= -30 else ''})"
            satirlar.append(f"   7 gün: {sayi(v7)} izlenme{degisim}, ort. %{round(son7.get('averageViewPercentage', 0))} izlendi,"
                            f" {son7.get('likes', 0)} beğeni, {son7.get('comments', 0)} yorum")
            def kanca(r):
                """İzlemeye devam edenlerin oranı (varsa): ' · kanca %38'"""
                v, e = r.get("views", 0), r.get("engagedViews")
                return f" · kanca %{round(e / v * 100)}" if e is not None and v else ""
            if enler:
                r = enler[0]
                satirlar.append(f"   🥇 {r['baslik'][:38]} — {sayi(r['views'])} izl., %{round(r.get('averageViewPercentage', 0))}{kanca(r)}")
                if sonuc[k]["en_kotu_7gun"]:
                    r = sonuc[k]["en_kotu_7gun"][0]
                    satirlar.append(f"   🔻 {r['baslik'][:38]} — {sayi(r['views'])} izl., %{round(r.get('averageViewPercentage', 0))}{kanca(r)}")
                toplam_v = sum(r.get("views", 0) for r in enler)
                toplam_e = sum(r.get("engagedViews", 0) or 0 for r in enler)
                if toplam_v and any("engagedViews" in r for r in enler):
                    satirlar.append(f"   🎣 Kanca: izleyicilerin %{round(toplam_e / toplam_v * 100)}'i ilk saniyelerden sonra videoda kaldı"
                                    f" (Kasım verisi: %35+ olanlar katlarca fazla izlendi)")
            yuzde = lambda a, b: f"%{a / b * 100:.1f}".replace(".0", "") if a < b else "✅"
            yeni_kural = bugun >= dt.date(2027, 2, 1)
            saat_h, shorts_h = (8000, 20_000_000) if yeni_kural else (4000, 10_000_000)
            reklam = [f"abone {abone}/1000 ({yuzde(abone, 1000)})"]
            ara = [f"abone {abone}/500 ({yuzde(abone, 500)})"]
            if s90 is not None:
                reklam.append(f"Shorts {sayi(s90)}/{shorts_h // 1_000_000}M ({yuzde(s90, shorts_h)})")
                ara.append(f"Shorts {sayi(s90)}/3M ({yuzde(s90, 3_000_000)})")
            if saat_uzun is not None:
                reklam.append(f"saat {saat_uzun}/{saat_h} ({yuzde(saat_uzun, saat_h)})")
                ara.append(f"saat {saat_uzun}/3000 ({yuzde(saat_uzun, 3000)})")
            satirlar.append("   💰 Reklam geliri: " + " · ".join(reklam))
            satirlar.append("   🎁 Ara basamak: " + " · ".join(ara))
            sonuc[k]["ypp_puan"] = min(abone / 1000, 1) + min(max((s90 or 0) / shorts_h, (saat_uzun or 0) / saat_h), 1)
        except Exception as ex:
            sonuc[k] = {"ad": bilgi.get("ad", k), "hata": str(ex)[:300]}
            satirlar.append(f"\n⚠️ {etiket}: okunamadı — {str(ex)[:120]}")
            if "invalid_grant" in str(ex):
                satirlar.append("   → İzin süresi bitmiş. Actions → YouTube İzin ile bu kanalı yeniden bağla.")
    adaylar = sorted((v for v in sonuc.values() if "ypp_puan" in v), key=lambda v: -v["ypp_puan"])
    if adaylar:
        satirlar.append(f"\n🏁 Para kazanmaya en yakın kanal: {adaylar[0]['ad']}")
        if bugun < dt.date(2027, 2, 1):
            satirlar.append("   ⏳ 1 Şubat 2027'den sonra başvuranlara şart 8.000 saat / 20M Shorts'a çıkıyor; "
                            "öncesinde girilirse eski şartlar geçerli.")
    return sonuc, satirlar


# ──────────────────────────── INSTAGRAM ────────────────────────────
def instagram():
    from ig_ortak import API, ig_hesap
    from yt_ortak import istek

    sonuc, satirlar, uyari = {}, ["📸 INSTAGRAM — " + bugun.strftime("%d.%m.%Y")], []
    eski = ONCEKI.get("instagram", {})
    sinir = int(time.time()) - 7 * 86400
    for k in SIRA:
        etiket = f"{AD[k]} ({YETKI[k]})"
        try:
            h = ig_hesap(k)
        except Exception as ex:
            print(k, "Instagram anahtarı çözülemedi:", ex)
            h = None
        if not h:
            satirlar.append(f"\n⚠️ {etiket}: Instagram bağlı değil")
            continue
        tok, ig = h["token"], h["ig_id"]
        try:
            kod, _, hesap = istek(f"{API}/{ig}?fields=username,followers_count,media_count&access_token={tok}")
            if kod != 200:
                raise RuntimeError(f"{kod}: {str(hesap)[:150]}")
            kod, _, medya = istek(f"{API}/{ig}/media?fields=id,caption,media_product_type,timestamp,like_count,"
                                  f"comments_count,permalink&limit=20&access_token={tok}")
            liste = (medya or {}).get("data", []) if kod == 200 else []
            yeni = [x for x in liste if dt.datetime.strptime(x["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
                    .replace(tzinfo=dt.timezone.utc).timestamp() >= sinir]
            icgoru = True
            for x in yeni:
                kod, _, ins = istek(f"{API}/{x['id']}/insights?metric=views,reach,saved,shares&access_token={tok}")
                if kod == 200:
                    x.update({d["name"]: (d.get("values") or [{}])[0].get("value", 0) for d in ins.get("data", [])})
                else:
                    icgoru = False
                    print(k, "medya içgörüsü alınamadı:", str(ins)[:200])
                    break
            takipci = hesap.get("followers_count")
            e = eski.get(k, {})
            sonuc[k] = {"kullanici": hesap.get("username"), "takipci": takipci, "gonderi": hesap.get("media_count"),
                        "son7_gonderi": yeni, "icgoru": icgoru,
                        "son24_takipci": fark(takipci, e.get("takipci"))}
            satirlar.append(f"\n▶️ {etiket} @{hesap.get('username')}")
            satirlar.append(f"   Takipçi {takipci} ({sonuc[k]['son24_takipci']} / 24 saat) · 7 günde {len(yeni)} paylaşım")
            if yeni:
                if icgoru:
                    izl = sum(x.get("views", 0) for x in yeni)
                    satirlar.append(f"   7 gün: {sayi(izl)} görüntülenme, {sum(x.get('like_count', 0) for x in yeni)} beğeni, "
                                    f"{sum(x.get('comments_count', 0) for x in yeni)} yorum, {sum(x.get('saved', 0) for x in yeni)} kayıt")
                    en = sorted(yeni, key=lambda x: x.get("views", 0), reverse=True)
                    satirlar.append(f"   🥇 {baslik(en[0])} — {sayi(en[0].get('views', 0))} görüntülenme")
                    if len(en) > 1:
                        satirlar.append(f"   🔻 {baslik(en[-1])} — {sayi(en[-1].get('views', 0))} görüntülenme")
                else:
                    satirlar.append(f"   7 gün: {sum(x.get('like_count', 0) for x in yeni)} beğeni, "
                                    f"{sum(x.get('comments_count', 0) for x in yeni)} yorum "
                                    f"(görüntülenme okunamadı: içgörü izni yok)")
            # Anahtar sağlığı: sayfa anahtarı süresizdir ama Meta'nın "veri erişimi" 90 günde bir yenilenmeli
            kod, _, dbg = istek(f"{API}/debug_token?input_token={tok}&access_token={tok}")
            d = (dbg or {}).get("data", {}) if kod == 200 else {}
            bitis = d.get("data_access_expires_at") or 0
            if d and not d.get("is_valid", True):
                uyari.append(f"❌ Instagram {AD[k]}: anahtar geçersiz → Actions → Instagram Kurulum yeniden çalıştırılmalı")
            elif bitis:
                kalan = int((bitis - time.time()) / 86400)
                sonuc[k]["veri_erisimi_kalan_gun"] = kalan
                if kalan <= 14:
                    uyari.append(f"⏰ Instagram {AD[k]}: Meta veri erişimi {kalan} gün sonra bitiyor → "
                                 f"Graph API Explorer'dan yeni anahtar alıp Instagram Kurulum'u çalıştıralım")
        except Exception as ex:
            sonuc[k] = {"hata": str(ex)[:300]}
            satirlar.append(f"\n⚠️ {etiket}: okunamadı — {str(ex)[:120]}")
    return sonuc, satirlar, uyari


# ───────────────────────────── TIKTOK ─────────────────────────────
def tiktok():
    sonuc, satirlar, uyari = {}, ["🎵 TIKTOK — " + bugun.strftime("%d.%m.%Y")], []
    taslak7 = {}
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")) + glob.glob(os.path.join(KOK, "kuyruk", "arsiv", "*.json")):
        try:
            r = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if r.get("tt") == "taslak" and r["id"][:8] >= (bugun - dt.timedelta(days=7)).strftime("%Y%m%d"):
            taslak7[r["kanal"]] = taslak7.get(r["kanal"], 0) + 1
    for k in SIRA:
        etiket = f"{AD[k]} ({YETKI[k]})"
        yol = os.path.join(KOK, "tokens", f"tt_{k}.json")
        if os.path.exists(yol):
            b = json.load(open(yol, encoding="utf-8"))
            kalan = int((b.get("yenileme_bitis", 0) - time.time()) / 86400)
            sonuc[k] = {"bagli": True, "taslak_7gun": taslak7.get(k, 0), "izin_kalan_gun": kalan}
            satirlar.append(f"\n▶️ {etiket}: bağlı (taslak modu) · 7 günde {taslak7.get(k, 0)} video taslağa gönderildi")
            if kalan <= 30:
                uyari.append(f"⏰ TikTok {AD[k]}: izin {kalan} gün sonra bitiyor → Actions → TikTok İzin")
        else:
            sonuc[k] = {"bagli": False}
            satirlar.append(f"\n▶️ {etiket}: bulut bağlantısı yok → elle / Chrome ile yükleniyor")
    satirlar.append("\nℹ️ TikTok uygulaması incelemede; onay gelene kadar izlenme/takipçi sayıları bulutta "
                    "okunamıyor, Claude'un sabah görevi TikTok Studio'dan (Chrome) okur.")
    return sonuc, satirlar, uyari


# ─────────────────── YAYIN DURUMU (platform platform) ───────────────────
PLATFORMLAR = [("▶️ YOUTUBE", "yt", ["dukkantv", "dramabite", "kasakurgu", "ilturnuva", "gizlitarih"]),
               ("📸 INSTAGRAM", "ig", ["dukkantv", "dramabite", "kasakurgu", "ilturnuva"]),
               ("🎵 TIKTOK", "tt", ["dukkantv", "dramabite", "kasakurgu", "ilturnuva"]),
               ("📘 FACEBOOK", "fb", ["dukkantv", "dramabite", "kasakurgu", "ilturnuva"])]


def kisa_ad(baslik):
    """Raporda telefonda okunacak kısa video adı."""
    import html, re
    for desen, sablon in ((r"Gün\s*(\d+)\s*/", "500 TL · Gün {}"), (r"Dosya\s*#\s*(\d+)", "Katil Kim · Dosya #{}"),
                          (r"Tur\s*·\s*(\w+)\s*Grubu", "81 İl · {} Grubu")):
        m = re.search(desen, baslik)
        if m:
            return sablon.format(m.group(1))
    ad = re.split(r"[|#]| — ", baslik)[0].strip()
    return html.escape(ad[:32] + ("…" if len(ad) > 32 else ""))


def yayin_durumu(simdi=None):
    """Levent'in istediği düzen (Kasım 2026): her platform ayrı başlık, altında bütün kanallar;
    dün ve bugün için ✅ yayınlandı / 🕒 saat / ❌ gitmedi / 📩 TikTok taslağı."""
    simdi = simdi or dt.datetime.now(TR)
    gunler = {simdi.date() - dt.timedelta(days=1): "dün", simdi.date(): "bugün"}
    kayitlar = []
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")) + glob.glob(os.path.join(KOK, "kuyruk", "arsiv", "*.json")):
        try:
            r = json.load(open(p, encoding="utf-8"))
            z = dt.datetime.fromisoformat(r["yayin"]).astimezone(TR) if r.get("yayin") else None
        except Exception:
            continue
        if z and z.date() in gunler and r.get("durum") == "yuklendi":
            kayitlar.append((z, r))
    kayitlar.sort(key=lambda x: x[0])
    satirlar = []
    for baslik_, alan, kanallar_ in PLATFORMLAR:
        satirlar.append(f"\n<b>{baslik_}</b>")
        for k in kanallar_:
            parca = []
            for z, r in (x for x in kayitlar if x[1]["kanal"] == k):
                ne = f"{gunler[z.date()]} {z:%H:%M} {kisa_ad(r['baslik'])}"
                gecti = z <= simdi
                if alan == "yt":
                    isaret = "✅" if gecti else "🕒"
                elif r.get("uzun"):
                    continue  # uzun videolar yalnızca YouTube'a gider
                else:
                    deger = r.get(alan)
                    if deger == "paylasildi":
                        isaret = "✅"
                    elif alan == "tt" and deger == "taslak":
                        isaret = "📩"
                    elif deger == "hata" or (gecti and alan != "tt"):
                        isaret = "❌"
                    elif not gecti:
                        isaret = "🕒"
                    else:
                        isaret = "❌"
                parca.append(f"{isaret} {ne}")
            if len(parca) <= 1:
                satirlar.append(f"{AD[k]}: " + (parca[0] if parca else "yayın yok"))
            else:
                satirlar.append(f"{AD[k]}:")
                satirlar += [f"   {x}" for x in parca]
    satirlar.append("\n✅ yayınlandı · 🕒 planlı · 📩 TikTok taslağı (senin paylaşmanı bekliyor) · ❌ gitmedi")
    return satirlar


# ─────────────────────── KISA SABAH RAPORU ───────────────────────
def kisa_rapor(yt_sonuc, ig_sonuc):
    """Levent'in istediği tek, net tablo: abone, hedefe giden izlenme, haftalık gidiş + birkaç yorum satırı."""
    import html
    k_sayi = lambda n: (f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.1f}B" if n >= 1e3 else str(int(n))).replace(".0", "")
    satir, yorum, buyuyen, dusen = [], [], [], []
    for k, v in sorted(yt_sonuc.items(), key=lambda x: -x[1].get("ypp_puan", -1)):
        ad = AD.get(k, v.get("ad", k))[:11]
        if "hata" in v:
            satir.append(f"{ad:<11} okunamadı"); continue
        if k == "gizlitarih":
            hedef = f"{v.get('uzun_video_saat_365') or 0:g} sa"
        else:
            hedef = k_sayi(v.get("shorts_izlenme_90") or 0)
        v7, o7 = v.get("son7", {}).get("views", 0), v.get("onceki7_izlenme")
        if o7:
            oran = round((v7 - o7) / o7 * 100)
            gidis = f"{oran:+d}%"
            (buyuyen if oran >= 10 else dusen if oran <= -30 else []).append(f"{AD.get(k, k)} ({oran:+d}%)")
        else:
            gidis = "yeni"
        satir.append(f"{ad:<11}{v.get('abone', 0):>6}{hedef:>8}{gidis:>7}")
    tablo_ = f"{'Kanal':<11}{'Abone':>6}{'İzlenme':>8}{'Hafta':>7}\n" + "\n".join(satir)
    adaylar = [v for v in yt_sonuc.values() if "ypp_puan" in v]
    if adaylar:
        en = max(adaylar, key=lambda v: v["ypp_puan"])
        yorum.append(f"🏁 Para kazanmaya en yakın: {html.escape(AD.get(next(k for k, x in yt_sonuc.items() if x is en), en['ad']))} "
                     f"(abone %{min(en['abone'] / 10, 100):.1f})".replace(".0)", ")"))
    if buyuyen:
        yorum.append("📈 Büyüyen: " + ", ".join(buyuyen))
    if dusen:
        yorum.append("📉 Düşen: " + ", ".join(dusen))
    ig = [f"{AD[k]} {x['takipci']}" + (f" ({x['son24_takipci']})" if x.get("son24_takipci") not in (None, "?", "+0") else "")
          for k, x in ig_sonuc.items() if isinstance(x, dict) and "takipci" in x and k in AD]
    metin = [f"📊 <b>Sabah Raporu · {bugun:%d.%m.%Y}</b>", "",
             f"<pre>{html.escape(tablo_)}</pre>",
             "Hedef: 1.000 abone + 90 günde 10M Shorts izlenmesi (Gizli Tarih: 4.000 saat uzun video)."
             + (" 1 Şubat 2027'den sonra başvuranlarda 8.000 saat / 20M." if bugun < dt.date(2027, 2, 1) else ""),
             ""] + yorum
    if ig:
        metin.append("📸 Instagram takipçi: " + html.escape(" · ".join(ig)))
    metin.append("ℹ️ YouTube sayıları 1–2 gün geriden gelir.")
    return metin


# ───────────────────────── ONAY BEKLEYENLER ─────────────────────────
def bekleyenler():
    satirlar, butonlar, liste, bugunkuler = [], [], [], []
    for p in sorted(glob.glob(os.path.join(KOK, "kuyruk", "*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        if not isinstance(r, dict) or "kanal" not in r:
            continue  # durum dosyası, video kaydı değil
        ad = AD.get(r["kanal"], r["kanal"])
        if r.get("durum") == "bekliyor":
            liste.append({"id": r["id"], "kanal": r["kanal"], "baslik": r["baslik"]})
            satirlar.append(f"• {ad}: {r['baslik'][:45]}")
            butonlar.append([{"text": f"✅ Onayla: {r['baslik'][:18]}", "callback_data": f"yt:onay:{r['id']}"},
                             {"text": "❌ Reddet", "callback_data": f"yt:iptal:{r['id']}"}])
        elif r.get("yayin") and r["yayin"][:10] == bugun.isoformat():
            bugunkuler.append(f"🕖 {r['yayin'][11:16]} {ad}: {r['baslik'][:40]}")
    return liste, satirlar, butonlar[:5], bugunkuler


if __name__ == "__main__":
    yt_sonuc, yt_satir = youtube()
    try:
        ig_sonuc, ig_satir, ig_uyari = instagram()
    except Exception as ex:
        ig_sonuc, ig_satir, ig_uyari = {"hata": str(ex)[:300]}, ["📸 INSTAGRAM", f"⚠️ okunamadı: {str(ex)[:150]}"], []
    tt_sonuc, tt_satir, tt_uyari = tiktok()
    bek, bek_satir, butonlar, bugunkuler = bekleyenler()

    sonuc = {"tarih": bugun.isoformat(), "olusturuldu": dt.datetime.now(TR).isoformat(timespec="minutes"),
             "kanallar": yt_sonuc, "instagram": ig_sonuc, "tiktok": tt_sonuc,
             "bekleyen": bek, "bugun_yayin": bugunkuler, "uyarilar": ig_uyari + tt_uyari}
    os.makedirs(os.path.join(KOK, "rapor"), exist_ok=True)
    for ad in (f"{bugun.isoformat()}.json", "son.json"):
        json.dump(sonuc, open(os.path.join(KOK, "rapor", ad), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    import html as _h
    son = kisa_rapor(yt_sonuc, ig_sonuc)
    try:
        son += ["", "📡 <b>Yayın durumu (dün + bugün)</b>"] + yayin_durumu()
    except Exception as ex:
        print("yayın durumu hazırlanamadı:", ex)
        if bugunkuler:
            son += ["", "📅 Bugün yayına girecekler:"] + [_h.escape(x) for x in bugunkuler]
    if bek_satir:
        son += ["", "⏳ Onayını bekleyen videolar:"] + [_h.escape(x) for x in bek_satir] + ["Aşağıdaki butonlarla karar ver 👇"]
    if sonuc["uyarilar"]:
        son += ["", "⚙️ Sistem uyarıları:"] + [_h.escape(x) for x in sonuc["uyarilar"]]
    ek = {"reply_markup": json.dumps({"inline_keyboard": butonlar})} if butonlar else {}
    telegram("\n".join(son)[:4000], parse_mode="HTML", **ek)
    print("\n\n".join(["\n".join(yt_satir), "\n".join(ig_satir), "\n".join(tt_satir), "\n".join(son)]))
