# Konu analizi (23 Kas 2026, Levent: "insanlar en çok hangi konularda izliyorsa o tarafa ağırlık ver").
# Her sabah rapordan sonra çalışır. Gizli Tarih "Ne Olur?" bölümlerini konu gruplarına ayırır, son 28 günün
# YouTube sayılarına göre grupları puanlar ve henüz üretilmemiş bölümleri en çok izlenen gruplar öne gelecek
# şekilde yeniden sıralar. Levent'in özel isteği: telefon ve "doğru bilinen yanlışlar" konuları zayıf çıksa da
# bırakılmaz, en az her 4 bölümde bir gelir. Veri yetersizse hiçbir şeyi değiştirmez.
import datetime as dt
import json
import os
import re

KOK = os.path.dirname(os.path.abspath(__file__))
BOLUMLER = os.path.join(KOK, "neolur", "bolumler.json")
DURUM = os.path.join(KOK, "neolur", "durum.json")
CIKTI = os.path.join(KOK, "rapor", "konu_analizi.json")

GRUP = {  # bölüm id → konu grubu
    "afet_uzay": {"gunes", "ay", "buzlar", "yagmur", "uydular", "insanlar", "okyanus", "agaclar", "bocekler",
                  "arilar", "donme", "yercekimi", "gece"},
    "hayatin_icinden": {"internet", "elektrik", "telefon", "yanlis-para", "dogruluk", "sessizlik", "zipla",
                        "sifreler", "trafik", "arabalar"},
    "dogru_bilinen_yanlislar": {"yanlislar1", "yanlislar2", "telefon-yanlis"},
    "telefon_bilgi": {"telefon-bilgi"},
}
# Bölüm listesinde olmayan eski videolar (başlıktaki parça → grup)
EK_BASLIK = {"Elektrikler Tamamen Kesilirse": "hayatin_icinden"}
KORUNAN = {"dogru_bilinen_yanlislar", "telefon_bilgi"}   # Levent'in isteği: sürekli denensin


def grup_bul(bid):
    for g, idler in GRUP.items():
        if bid in idler:
            return g
    if bid.startswith("yanlis"):
        return "dogru_bilinen_yanlislar"
    if "telefon" in bid:
        return "telefon_bilgi"
    return "diger"


def sade(t):
    return re.sub(r"[^a-zçğıöşü0-9 ]", "", t.lower().replace("#shorts", "")).split()


def eslestir(baslik, bolumler):
    k = set(sade(baslik))
    en, puan = None, 0
    for b in bolumler:
        o = len(k & set(sade(b["baslik"]))) / max(1, len(set(sade(b["baslik"]))))
        if o > puan:
            en, puan = b, o
    return en if puan >= 0.7 else None


def main():
    son = json.load(open(os.path.join(KOK, "rapor", "son.json"), encoding="utf-8"))
    videolar = son.get("kanallar", {}).get("gizlitarih", {}).get("videolar_28gun") or []
    d = json.load(open(BOLUMLER, encoding="utf-8"))
    durum = json.load(open(DURUM, encoding="utf-8"))
    bolumler = d["bolumler"]
    sinir = (dt.date.today() - dt.timedelta(days=2)).isoformat()
    toplam = {}
    for v in videolar:
        if (v.get("yayin") or "9999") > sinir:
            continue   # sayıları henüz oturmadı
        b = eslestir(v.get("baslik", ""), bolumler)
        grup = grup_bul(b["id"]) if b else next((g for p, g in EK_BASLIK.items() if p in v.get("baslik", "")), None)
        if not grup:
            continue
        g = toplam.setdefault(grup, {"video": 0, "izlenme": 0, "yuzde": 0.0})
        g["video"] += 1
        g["izlenme"] += v.get("views", 0)
        g["yuzde"] += v.get("averageViewPercentage", 0) or 0
    skor = {g: round(x["izlenme"] / x["video"], 1) for g, x in toplam.items() if x["video"] >= 2}
    sonuc = {"tarih": dt.date.today().isoformat(), "gruplar": {g: dict(x, ortalama=round(x["izlenme"] / x["video"], 1),
             ort_yuzde=round(x["yuzde"] / x["video"], 1)) for g, x in toplam.items()}, "degisiklik": "yok"}
    if len(skor) >= 2:
        sira = durum["sira"]
        bekleyen = bolumler[sira:]
        # Puanı olmayan gruplar ortalamanın biraz altında sayılır (denenmemiş konular da şans bulsun)
        ort = sum(skor.values()) / len(skor)
        puan = lambda b: skor.get(grup_bul(b["id"]), ort * 0.9)
        yeni = sorted(bekleyen, key=puan, reverse=True)
        # Korunan konular en az her 4 bölümde bir
        sonuc_sira, korunan = [], [b for b in yeni if grup_bul(b["id"]) in KORUNAN]
        diger = [b for b in yeni if grup_bul(b["id"]) not in KORUNAN]
        while korunan or diger:
            son3 = sonuc_sira[-3:]
            if korunan and (len(son3) == 3 and all(grup_bul(x["id"]) not in KORUNAN for x in son3) or not diger
                            or puan(korunan[0]) >= puan(diger[0])):
                sonuc_sira.append(korunan.pop(0))
            else:
                sonuc_sira.append(diger.pop(0))
        if [b["id"] for b in sonuc_sira] != [b["id"] for b in bekleyen]:
            d["bolumler"] = bolumler[:sira] + sonuc_sira
            json.dump(d, open(BOLUMLER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            en_iyi = max(skor, key=skor.get)
            sonuc["degisiklik"] = f"en çok izlenen grup '{en_iyi}' ({skor[en_iyi]:g}/video) öne alındı; sıradaki: " + \
                ", ".join(b["id"] for b in sonuc_sira[:4])
    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    json.dump(sonuc, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(sonuc, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
