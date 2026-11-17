# Çarşı Ligi — sezon yöneticisi (Dükkan TV). Survivor'dan esinlenen yapı (ad/logo/müzik kullanılmaz):
#   Takım fazı (Kırmızı Tente / Mavi Tente), haftalık 7 bölüm:
#     0 ödül maçı (3'e 3) · 1-3 dokunulmazlık (kaybeden takımda en az müşteri toplayan potaya)
#     4 Esnaf Konseyi (yorumlarda adı en çok geçen pota adayı kurtulur; yorum yoksa Muhtar'ın kurası)
#     5 eleme düellosu (kaybeden çarşıya veda eder) · 6 haftanın özeti
#   9 esnaf kalınca birleşme → bireysel faz, 3 bölümlük döngü: 2 bireysel dokunulmazlık + düello
#   3 esnaf kalınca büyük final.
# Kullanım:
#   python3 carsi_sezon.py lansman <1-5> [--deneme]    1 geri sayım · 2 kura gecesi · 3/4 takım tanıtımı · 5 fragman
#   python3 carsi_sezon.py bolum [--deneme]             sıradaki sezon bölümü
# Çıktı: cikti/carsi/yayin.json (video, baslik, aciklama, etiketler, sabit_yayin?)
import datetime as dt, glob, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import carsi, carsi_ses, carsi_sahne  # noqa: E402
from carsi import ESNAF, TAKIM_AD, tr_ad, soru  # noqa: E402

KOK = carsi.KOK
DURUM = os.path.join(HERE, "carsi_sezon.json")
CIKTI = os.path.join(KOK, "cikti", "carsi")
TR = dt.timezone(dt.timedelta(hours=3))
LANSMAN = {  # adım: (yayın saati, başlık)
    1: ("2026-11-21T13:00:00+03:00", "Çarşı Ligi Geliyor! 15 Esnaf, 2 Takım, 1 Şampiyon 🏪 #shorts"),
    2: ("2026-11-22T13:00:00+03:00", "Çarşı Ligi Kura Gecesi: Hangi Esnaf Hangi Takımda? 🎲 #shorts"),
    3: ("2026-11-23T13:00:00+03:00", "Kırmızı Tente Takımıyla Tanışın! 🔴 Çarşı Ligi #shorts"),
    4: ("2026-11-24T13:00:00+03:00", "Mavi Tente Takımıyla Tanışın! 🔵 Çarşı Ligi #shorts"),
    5: ("2026-11-25T13:00:00+03:00", "Çarşı Ligi Yarın Başlıyor! İlk Maç: Ödül Maçı 🔴🔵 #shorts"),
}
BIRLESME, FINAL = 9, 3
ETIKET = "çarşı ligi,dükkan tv,brainrot,türk brainrot,esnaf,dokunulmazlık,eleme adayı,konsey,levent ve cemo"
HASHTAG = "#çarşıligi #dükkantv #dokunulmazlık #elemeadayı #brainrot #shorts"
ANAHTAR = {  # yorum sayımı: kelime başında eşleşir (ör. "kedi", "kediye")
    "simitci-kedi": ["kedi"], "borekci-baykus": ["baykuş", "baykus", "börekçi", "borekci"],
    "dondurmaci-keci": ["keçi", "keci", "dondurmacı", "dondurmaci"], "kokorec-ejderha": ["ejderha", "kokoreç", "kokorec"],
    "lahmacun-kaplumbaga": ["kaplumbağa", "kaplumbaga", "lahmacun"], "pide-timsah": ["timsah", "pideci", "pide"],
    "ayran-penguen": ["penguen", "ayran"], "cay-bardagi-tavsan": ["tavşan", "tavsan"],
    "caydanlik-pasa": ["çaydanlık", "caydanlik", "paşa", "pasa"], "dolmus-kopek": ["köpek", "kopek", "dolmuş", "dolmus"],
    "kumpir-ayi": ["ayı", "ayi", "kumpir"], "lokum-fil": ["fil", "lokum"], "nazar-baligi": ["nazar", "balık", "balik"],
    "simit-kapan-marti": ["martı", "marti"], "tavla-kurbaga": ["kurbağa", "kurbaga", "tavla"],
}


def yukle():
    if os.path.exists(DURUM):
        return json.load(open(DURUM, encoding="utf-8"))
    return {"sezon": 1, "faz": "lansman", "takimlar": None, "kalan": list(ESNAF), "elenen": [], "pota": [],
            "dokunulmaz": None, "duello": None, "hafta": 1, "adim": 0, "bolum_no": 0, "lansman": [],
            "hafta_olay": {}, "bolumler": []}


def kaydet(d):
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def ad(e):
    return tr_ad(ESNAF[e][0])


def yaz_yayin(video, baslik, aciklama, sabit=None, ek=None):
    os.makedirs(CIKTI, exist_ok=True)
    b = {"video": video, "baslik": baslik[:100], "aciklama": aciklama, "etiketler": ETIKET}
    if sabit:
        b["sabit_yayin"] = sabit
    b.update(ek or {})
    json.dump(b, open(os.path.join(CIKTI, "yayin.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in b.items() if k != "aciklama"}, ensure_ascii=False))


def oyna(cikti, esnaflar, tur, takimlar=None, ust="", kanca=None, arka_no=1):
    """Sessiz oynat → yorumları seslendir → aynı tohumla görüntülü oynat (sonuç birebir aynı olmalı)."""
    tohum = random.randrange(1, 10 ** 9)
    taslak = carsi.mac("x", esnaflar, tohum, tur=tur, takimlar=takimlar, ust=ust, kanca=kanca, arka_no=arka_no, cizme=True)
    sesler = carsi_ses.balonlar(taslak["balon"])
    sonuc = carsi.mac(cikti, esnaflar, tohum, tur=tur, takimlar=takimlar, ust=ust, kanca=kanca, arka_no=arka_no,
                      konusmalar=sesler)
    if sonuc["puan"] != taslak["puan"]:
        sys.exit("HATA: sessiz ve görüntülü oynatma farklı sonuç verdi")
    sonuc["tohum"] = tohum
    return sonuc


# ───────────────────────── lansman ─────────────────────────
def lansman(d, adim, video):
    saat, baslik = LANSMAN[adim]
    if adim == 1:
        carsi_sahne.geri_sayim(video)
        aciklama = ("Çarşıda kepenkler kapalı… ama çok yakında! 15 esnaf, 2 takım, tek şampiyon.\n"
                    "Çarşı Ligi 26 Kasım akşam 19:00'da Dükkan TV'de başlıyor! 🏪\n\n"
                    "Favori esnafını yorumlara yaz 👇\n\n" + HASHTAG)
    elif adim == 2:
        if not d["takimlar"]:
            es = list(ESNAF); random.shuffle(es)
            d["takimlar"] = {"K": es[:8], "M": es[8:]}
        carsi_sahne.kura_gecesi(video, d["takimlar"])
        aciklama = ("Kura çekildi! 15 esnaf iki takıma ayrıldı: Kırmızı Tente 🔴 ve Mavi Tente 🔵\n"
                    "Senin favorin hangi takımda? Takımını yorumlara yaz 👇\n\n" + HASHTAG)
    elif adim in (3, 4):
        if not d["takimlar"]:
            if "--deneme" not in sys.argv:
                sys.exit("Önce kura gecesi (lansman 2) üretilmeli")
            es = list(ESNAF); random.shuffle(es); d["takimlar"] = {"K": es[:8], "M": es[8:]}
        t_ = "K" if adim == 3 else "M"
        carsi_sahne.takim_tanitim(video, t_, d["takimlar"][t_])
        aciklama = (f"{TAKIM_AD[t_].title()} takımının esnafları: " + ", ".join(ad(e) for e in d["takimlar"][t_]) +
                    "\nBu takımı tutuyor musun? Yorumlara yaz 👇\nÇarşı Ligi 26 Kasım 19:00'da başlıyor!\n\n" + HASHTAG)
    else:
        carsi_sahne.fragman(video, d["takimlar"])
        aciklama = ("Çarşı Ligi yarın akşam 19:00'da başlıyor! İlk maç: Ödül Maçı. Kırmızı mı kazanır, Mavi mi?\n"
                    "Her hafta bir esnaf çarşıya veda edecek; konseyde kaderleri senin yorumlarına bağlı!\n\n" + HASHTAG)
    if adim not in d["lansman"]:
        d["lansman"].append(adim)
    if len(d["lansman"]) == 5 and d["faz"] == "lansman":
        d["faz"] = "takim"
    yaz_yayin(video, baslik, aciklama, sabit=saat)


# ───────────────────────── konsey yorum sayımı ─────────────────────────
def yorum_say(d, adaylar):
    """Bu haftanın yayınlanmış bölümlerine gelen yorumlarda adayların adlarını say (kanalın kendi yorumları hariç)."""
    try:
        sys.path.insert(0, KOK)
        from yt_ortak import erisim_anahtari, istek
        tok = erisim_anahtari("dukkantv")
        h = {"Authorization": f"Bearer {tok}"}
        _, _, kanal = istek("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers=h)
        biz = kanal["items"][0]["id"]
        kidler = {b["kid"] for b in d["bolumler"] if b.get("hafta") == d["hafta"] and b.get("kid")}
        vidler = []
        for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")) + glob.glob(os.path.join(KOK, "kuyruk", "arsiv", "*.json")):
            k = json.load(open(p, encoding="utf-8"))
            if k.get("id") in kidler and k.get("video_id"):
                vidler.append(k["video_id"])
        sayim = {e: 0 for e in adaylar}
        for v in vidler:
            kod, _, veri = istek(f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&videoId={v}"
                                 f"&maxResults=100&textFormat=plainText", headers=h)
            for it in (veri.get("items", []) if kod == 200 else []):
                sn = it["snippet"]["topLevelComment"]["snippet"]
                if sn.get("authorChannelId", {}).get("value") == biz:
                    continue
                metin = sn.get("textDisplay", "").replace("I", "ı").replace("İ", "i").lower()
                for e in adaylar:
                    if any(re.search(r"(^|[^\wçğıöşü])" + re.escape(a), metin) for a in ANAHTAR[e]):
                        sayim[e] += 1
        print("konsey yorum sayımı:", sayim, "videolar:", vidler)
        return sayim
    except Exception as ex:
        print("yorumlar okunamadı:", ex)
        return {e: 0 for e in adaylar}


# ───────────────────────── sezon bölümü ─────────────────────────
def kadro(d, takim, kac=3):
    uye = list(d["takimlar"][takim])
    pota_disi = [e for e in uye if e not in d["pota"]]
    havuz = pota_disi if len(pota_disi) >= kac else uye
    return random.sample(havuz, min(kac, len(havuz)))


def bolum(d, video):
    if d["faz"] == "lansman":
        sys.exit("Lansman bitmeden sezon bölümü üretilmez")
    if d["faz"] == "bitti":
        sys.exit("Sezon bitti")
    d["bolum_no"] += 1
    h, a = d["hafta"], d["adim"]
    olay = d["hafta_olay"]
    kayit = {"no": d["bolum_no"], "hafta": h, "adim": a, "faz": d["faz"]}

    if d["faz"] == "takim":
        if a == 0:
            k, m = kadro(d, "K"), kadro(d, "M")
            s = oyna(video, k + m, "odul", takimlar=list("KKKMMM"), ust=f"{h}. HAFTA · ÖDÜL MAÇI",
                     kanca=("3'E 3 · ÖDÜL MAÇI", "KIRMIZI MI MAVİ Mİ?"), arka_no=d["bolum_no"])
            olay["odul"] = s["kazanan_takim"]
            baslik = f"Çarşı Ligi {h}. Hafta | Ödül Maçı: Kırmızı mı Mavi mi? 🔴🔵 #shorts"
            aciklama = (f"{h}. haftanın ödül maçı! Kırmızı Tente: {', '.join(ad(e) for e in k)}. "
                        f"Mavi Tente: {', '.join(ad(e) for e in m)}.\nTakımını yorumlara yaz 👇\n\n{HASHTAG}")
        elif a in (1, 2, 3):
            k, m = kadro(d, "K"), kadro(d, "M")
            s = oyna(video, k + m, "dokunulmazlik", takimlar=list("KKKMMM"), ust=f"{h}. HAFTA · {a}. DOKUNULMAZLIK",
                     kanca=(f"{a}. DOKUNULMAZLIK", "KİM POTAYA GİDECEK?"), arka_no=d["bolum_no"])
            d["pota"].append(s["eleme_adayi"])
            olay.setdefault("dok", {"K": 0, "M": 0})[s["kazanan_takim"]] += 1
            baslik = f"Çarşı Ligi | {a}. Dokunulmazlık: Eleme Adayı Kim Oldu? 🔴🔵 #shorts"
            aciklama = (f"{h}. haftanın {a}. dokunulmazlık maçı! Kaybeden takımda en az müşteri toplayan esnaf potaya gidiyor.\n"
                        "Konseyde yorumlarda adı en çok geçen esnaf kurtulur. Sence kim kurtulmalı? 👇\n\n" + HASHTAG)
        elif a == 4:
            s = konsey_bolumu(d, video, h)
            baslik = "Çarşı Ligi | Esnaf Konseyi: Yorumlar Kimi Kurtardı? ⚖️ #shorts"
            aciklama = (f"{h}. haftanın konseyi! Potadakiler: {', '.join(ad(e) for e in d['pota'])}.\n"
                        f"Kurtulan: {ad(s['kurtulan'])}. Yarın eleme düellosu: {ad(d['duello'][0])} – {ad(d['duello'][1])}!\n"
                        "Sence kim kalmalı? 👇\n\n" + HASHTAG)
        elif a == 5:
            a_, b_ = d["duello"]
            s = oyna(video, [a_, b_], "duello", ust=f"{h}. HAFTA · ELEME DÜELLOSU",
                     kanca=("ELEME DÜELLOSU", "KİM ÇARŞIYA VEDA EDECEK?"), arka_no=d["bolum_no"])
            vd = s["veda"]; elen(d, vd); olay["veda"] = vd
            if len(d["kalan"]) <= BIRLESME:
                olay["birlesme"] = True
            baslik = f"Çarşı Ligi | Eleme Düellosu: {ad(a_)} {soru(ad(a_))} {ad(b_)} {soru(ad(b_))}? 😢 #shorts"
            aciklama = (f"{ad(a_)} ve {ad(b_)} eleme düellosunda! Kaybeden çarşıya veda ediyor…\n"
                        "Veda eden esnafa yorumlarda bir mesaj bırak 👇\n\n" + HASHTAG)
        else:
            carsi_sahne.ozet(video, h, d, olay)
            baslik = f"Çarşı Ligi {h}. Haftanın Özeti: Kim Veda Etti? 📺 #shorts"
            aciklama = (f"{h}. haftada neler oldu? Ödül, dokunulmazlıklar, konsey ve veda… Çarşıda {len(d['kalan'])} esnaf kaldı!\n"
                        "Favori esnafını yorumlara yaz 👇\n\n" + HASHTAG)
            if olay.get("birlesme"):
                d["faz"] = "bireysel"; d["takimlar"] = None
            d["hafta"] += 1; d["adim"] = -1; d["pota"] = []; d["duello"] = None; d["hafta_olay"] = {}
    elif d["faz"] == "bireysel":
        if a in (0, 1):
            oyuncu = random.sample(d["kalan"], min(6, len(d["kalan"])))
            s = oyna(video, oyuncu, "bireysel", ust=f"{h}. HAFTA · BİREYSEL DOKUNULMAZLIK",
                     kanca=("BİREYSEL DOKUNULMAZLIK", "HERKES KENDİ DÜKKÂNI İÇİN!"), arka_no=d["bolum_no"])
            sira = [e for e in reversed(s["sira"]) if e not in d["pota"] and e != d.get("dokunulmaz")]
            aday = sira[0] if sira else s["eleme_adayi"]
            d["pota"].append(aday)
            if a == 0:
                d["dokunulmaz"] = s["kazanan"]
            baslik = "Çarşı Ligi | Bireysel Dokunulmazlık: Kim Potaya Gitti? #shorts"
            aciklama = (f"Takımlar dağıldı, herkes kendi dükkânı için yarışıyor! Potaya giden: {ad(aday)}.\n"
                        "Sence kim finale kalır? 👇\n\n" + HASHTAG)
        else:
            a_, b_ = d["pota"][:2]
            s = oyna(video, [a_, b_], "duello", ust=f"{h}. HAFTA · ELEME DÜELLOSU",
                     kanca=("ELEME DÜELLOSU", "KİM ÇARŞIYA VEDA EDECEK?"), arka_no=d["bolum_no"])
            elen(d, s["veda"])
            baslik = f"Çarşı Ligi | Eleme Düellosu: {ad(a_)} {soru(ad(a_))} {ad(b_)} {soru(ad(b_))}? 😢 #shorts"
            aciklama = (f"Finale giden yolda bir veda daha… Çarşıda {len(d['kalan'])} esnaf kaldı!\n"
                        "Şampiyon sence kim olur? 👇\n\n" + HASHTAG)
            d["pota"] = []; d["dokunulmaz"] = None; d["adim"] = -1; d["hafta"] += 1
            if len(d["kalan"]) <= FINAL:
                d["faz"] = "final"
    else:   # final
        s = oyna(video, list(d["kalan"]), "final", ust="BÜYÜK FİNAL", kanca=("BÜYÜK FİNAL", "SEZONUN ŞAMPİYONU KİM?"),
                 arka_no=d["bolum_no"])
        d["sampiyon"] = s["kazanan"]; d["faz"] = "bitti"
        baslik = "Çarşı Ligi BÜYÜK FİNAL: Sezonun Şampiyonu Kim? 🏆 #shorts"
        aciklama = (f"Sezonun son maçı! {', '.join(ad(e) for e in d['kalan'])} kupa için karşı karşıya.\n"
                    "Yeni sezon yakında! Yorumlara yaz 👇\n\n" + HASHTAG)
    d["adim"] += 1
    kayit.update(baslik=baslik)
    d["bolumler"].append(kayit)
    yaz_yayin(video, baslik, aciklama)


def elen(d, e):
    d["elenen"].append(e)
    d["kalan"] = [x for x in d["kalan"] if x != e]
    if d.get("takimlar"):
        for t_ in ("K", "M"):
            d["takimlar"][t_] = [x for x in d["takimlar"][t_] if x != e]


def konsey_bolumu(d, video, h):
    pota = d["pota"][:3]
    sayim = yorum_say(d, pota)
    en = max(sayim.values()) if sayim else 0
    if sum(sayim.values()) >= 3 and list(sayim.values()).count(en) == 1:
        kurtulan, nasil = max(sayim, key=sayim.get), "yorum"
    else:
        kurtulan, nasil = random.choice(pota), "kura"
    d["duello"] = [e for e in pota if e != kurtulan][:2]
    carsi_sahne.konsey(video, h, pota, sayim, kurtulan, nasil)
    return {"kurtulan": kurtulan, "nasil": nasil, "sayim": sayim}


def main():
    deneme = "--deneme" in sys.argv
    arg = [x for x in sys.argv[1:] if not x.startswith("--")]
    d = yukle()
    os.makedirs(CIKTI, exist_ok=True)
    if arg[0] == "lansman":
        adim = int(arg[1])
        lansman(d, adim, os.path.join(CIKTI, f"lansman_{adim}.mp4"))
    elif arg[0] == "bolum":
        if deneme and d["faz"] == "lansman":   # deneme: takımları geçici kurayla oluştur (kaydedilmez)
            es = list(ESNAF); random.shuffle(es)
            d["takimlar"] = d["takimlar"] or {"K": es[:8], "M": es[8:]}; d["faz"] = "takim"
        bolum(d, os.path.join(CIKTI, f"bolum_{d['bolum_no'] + 1:03d}.mp4"))
    elif arg[0] == "kid":   # yayın kuyruğuna eklenen son bölümün kimliğini kaydet (konsey yorum sayımı için)
        if d["bolumler"]:
            d["bolumler"][-1]["kid"] = arg[1]
    if not deneme:
        kaydet(d)


if __name__ == "__main__":
    main()
