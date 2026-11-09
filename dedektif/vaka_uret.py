"""Katil Kim? vaka stoku azalınca Gemini ile yeni vakalar yazar.

Her yeni vaka iki kez kontrol edilir:
1) Biçim: 3 şüpheli, 2 ipucu, doğru cevap 0-2, çözüm doğru şüphelinin adını içerir, başlık tekrar etmez.
2) Adillik: Gemini'ye çözümü göstermeden vaka sorulur; ipuçlarından AYNI cevaba ulaşamazsa vaka atılır.
Böylece izleyiciye çözülemeyen ya da birden çok cevabı olan vaka gitmez.
"""
import json
import os
import random
import re
import sys
import time

import requests

KLASOR = os.path.dirname(os.path.abspath(__file__))
VAKALAR = os.path.join(KLASOR, "vakalar_v2.json")
DURUM = os.path.join(KLASOR, "state.json")
ANAHTAR = "".join(os.environ.get("GEMINI_API_KEY", "").split())
ESIK = int(os.environ.get("STOK_ESIGI", "7"))      # kalan vaka bundan azsa yenisi yazılır
ADET = int(os.environ.get("YENI_VAKA", "10"))      # bir seferde kaç vaka yazılsın
MODELLER = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-flash-lite-latest"]

ORNEK = {
    "baslik": "Kırık Vitrin",
    "olay": "Kuyumcunun vitrini kırılıp bir yüzük alındı. Camdaki kırılma izi çok net.",
    "ipuclari": ["Cam, sol taraftan vurularak kırılmış. Uzmanlara göre bu vuruşu ancak solak biri yapabilir.",
                 "Üç şüpheli çay içerken izlendi. Taner bardağı sağ elle tuttu. Pınar sol elle tuttu. Oya sağ elle tuttu."],
    "supheliler": [{"ad": "Taner", "rol": "tamirci"}, {"ad": "Oya", "rol": "komşu"}, {"ad": "Pınar", "rol": "kasiyer"}],
    "dogru": 2,
    "cozum": "Vuruş izi solak birine aitti. Çay içerken yalnızca Pınar bardağı sol eliyle tuttu.",
}


def gemini(istem, json_mod=True):
    for model in MODELLER:
        for deneme in range(3):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={ANAHTAR}",
                    json={"contents": [{"parts": [{"text": istem}]}],
                          "generationConfig": {"temperature": 0.9 if json_mod else 0.0,
                                               **({"responseMimeType": "application/json"} if json_mod else {})}},
                    timeout=120)
                if r.status_code == 404:
                    break
                if r.status_code == 429:
                    time.sleep(20 * (deneme + 1))
                    continue
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                print(f"Gemini ({model}) hata: {str(e)[:150]}")
                time.sleep(5)
    raise RuntimeError("Gemini cevap vermedi")


def bicim_dogru(v, basliklar):
    try:
        sup = v["supheliler"]
        assert isinstance(v["baslik"], str) and 2 <= len(v["baslik"]) <= 30
        assert v["baslik"].lower() not in basliklar
        assert len(v["olay"]) <= 220 and len(v["ipuclari"]) == 2
        assert all(15 <= len(i) <= 200 for i in v["ipuclari"])
        assert len(sup) == 3 and len({s["ad"] for s in sup}) == 3
        assert all(s["ad"] and s["rol"] and len(s["ad"]) <= 12 and len(s["rol"]) <= 18 for s in sup)
        assert v["dogru"] in (0, 1, 2)
        assert sup[v["dogru"]]["ad"] in v["cozum"]
        return True
    except Exception:
        return False


def adil_mi(v):
    """Çözümü görmeden doğru şüpheliyi bulabiliyor mu?"""
    sec = "\n".join(f"{'ABC'[i]}) {s['ad']} ({s['rol']})" for i, s in enumerate(v["supheliler"]))
    istem = (f"Bir dedektif bilmecesi. Olay: {v['olay']}\nİpucu 1: {v['ipuclari'][0]}\nİpucu 2: {v['ipuclari'][1]}\n"
             f"Şüpheliler:\n{sec}\nSadece ipuçlarına dayanarak suçlu kim? Tek harf yaz: A, B ya da C. "
             f"İpuçları tek bir kişiyi kesin göstermiyorsa X yaz.")
    cevaplar = []
    for _ in range(2):
        m = re.search(r"\b([ABCX])\b", gemini(istem, json_mod=False).strip().upper())
        cevaplar.append(m.group(1) if m else "X")
    return all(c == "ABC"[v["dogru"]] for c in cevaplar)


def main():
    vakalar = json.load(open(VAKALAR, encoding="utf-8"))
    durum = json.load(open(DURUM, encoding="utf-8")) if os.path.exists(DURUM) else {}
    kalan = len(vakalar) - durum.get("v2_index", 0)
    print(f"Kalan vaka: {kalan} (eşik {ESIK})")
    if kalan >= ESIK and "--zorla" not in sys.argv:
        return
    basliklar = {v["baslik"].lower() for v in vakalar}
    mekanlar = ["fırın", "berber", "kırtasiye", "otobüs durağı", "kütüphane", "spor salonu", "çiçekçi", "pazar yeri",
                "otel lobisi", "sinema", "eczane", "kafe", "terzi", "oyuncakçı", "balıkçı", "apartman", "okul kantini",
                "hastane bahçesi", "tren garı", "düğün salonu", "kayak oteli", "yazlık site", "hal", "kargo şubesi"]
    istem = (
        "Türkçe, kısa (Shorts için 45 sn), aile dostu dedektif bilmeceleri yaz. Şiddet ve kan YOK; suçlar hırsızlık, "
        "kayıp eşya, şaka, kırılan eşya gibi hafif olaylar. Her vakada 3 şüpheli (farklı Türkçe isimler ve meslekler), "
        "tam 2 ipucu ve TEK doğru cevap olsun. Cevap, iki ipucu birlikte düşünülünce mantıkla kesin bulunmalı "
        "(alibi, sol/sağ el, saat, ayak izi, koku, renk, boy, dil sürçmesi gibi somut detaylar). İpuçları kısa ve net "
        "cümleler olsun, yanıltıcı ama hileli olmasın. 'dogru' alanı doğru şüphelinin 0'dan başlayan sırası; doğru "
        "şüpheliyi her seferinde farklı sıraya koy. 'cozum' 1-2 cümle, doğru şüphelinin adını içersin.\n"
        f"Mekân fikirleri: {', '.join(random.sample(mekanlar, 10))}.\n"
        f"Şu başlıkları KULLANMA: {', '.join(sorted(basliklar))}.\n"
        f"Örnek biçim: {json.dumps(ORNEK, ensure_ascii=False)}\n"
        f"Tam olarak {ADET + 4} vaka yaz. SADECE JSON dizi döndür."
    )
    adaylar = json.loads(gemini(istem))
    eklenen = []
    for v in adaylar:
        if len(eklenen) >= ADET:
            break
        v = {k: v.get(k) for k in ORNEK}
        if not bicim_dogru(v, basliklar):
            print("Biçim uygun değil, atlandı:", v.get("baslik"))
            continue
        if not adil_mi(v):
            print("Adil değil (ipuçlarından çözülemiyor), atlandı:", v["baslik"])
            continue
        basliklar.add(v["baslik"].lower())
        eklenen.append(v)
        print("Eklendi:", v["baslik"])
    vakalar += eklenen
    json.dump(vakalar, open(VAKALAR, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(eklenen)} yeni vaka eklendi. Toplam {len(vakalar)}.")


if __name__ == "__main__":
    main()
