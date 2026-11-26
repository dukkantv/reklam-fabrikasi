# Sohbet tarzı anlatım denemesi (26 Kas 2026): aynı bölümü eski (tek ton) ve yeni (cümle cümle ton) olarak üretir.
# Kullanım: ANLATIM=duz python sohbet_deneme.py eski   /   ANLATIM=sohbet python sohbet_deneme.py yeni
import json, os, sys
import uzun, kit
ad = sys.argv[1]
sen = json.load(open("uzun_senaryolar/01-internetten-para-kazanma.json", encoding="utf-8"))
kes = next(i for i, s in enumerate(sen["sahneler"]) if s.get("bolum") == "Altın kural")
sen["sahneler"] = sen["sahneler"][:kes]
os.makedirs("out", exist_ok=True); os.makedirs("/tmp/dn", exist_ok=True)
v = uzun.Uzun(sen, lambda i, j, m, tz="samimi", hz=1.0: kit.seslendir(tz, m, f"/tmp/dn/{ad}_{i}_{j}.wav", hz)[0])
print(ad, round(v.DUR, 1), "sn")
v.render(f"out/_{ad}_v.mp4")
v.audio(f"out/_{ad}_a.wav")
kit.sikistir(f"out/_{ad}_v.mp4", f"out/{ad}.mp4", f"out/_{ad}_a.wav")
etiket = "ESKİ: tek ton" if ad == "eski" else "YENİ: sohbet tarzı (yavaş / hızlı / heyecanlı / merak)"
kit.tg_video(f"out/{ad}.mp4", f"🎙 Anlatım denemesi · {etiket}")
