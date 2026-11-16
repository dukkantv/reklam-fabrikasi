"""Senaryodaki her sahne için TEK çizim yapar (ses yok, video yok) ve gorseller/<ad>/NN.jpg olarak kaydeder.
Var olan resimleri atlar; kota biterse durur, ertesi gün kaldığı yerden devam eder.
Kullanım: python cizim_hazirla.py senaryolar/x.json dedektif [yeniden_cizilecek: 5,7,12]"""
import json, os, sys
import belgesel as b

senaryo, tur = sys.argv[1], sys.argv[2]
yeniden = {int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "").split(",") if x.strip()}
ad = os.path.splitext(os.path.basename(senaryo))[0]
klasor = os.path.join(b.KOK, "gorseller", ad)
os.makedirs(klasor, exist_ok=True)
s = json.load(open(senaryo, encoding="utf-8"))
b.CIZIM_KAPALI["pollinations"] = True  # sadece Cloudflare; ücretli/kapalı servislere gitme
b.CIZIM_KAPALI["gemini"] = True
yeni, kalan = 0, []
for i, sc in enumerate(s["sahneler"], 1):
    hedef = os.path.join(klasor, f"{i:02d}.jpg")
    if os.path.exists(hedef) and i not in yeniden:
        continue
    prompt = f"{sc['nesne']} clearly visible as the main subject. {sc['gorsel']}. {b.STILLER[tur]}. {b.ORTAK}"
    tohum = 1000 + i + (7 if i in yeniden else 0) * 13
    if b.resim_cf(prompt, hedef, tohum):
        yeni += 1
        print(f"Sahne {i}: çizildi")
    else:
        kalan.append(i)
        if b.CIZIM_KAPALI["cf"]:
            kalan += [j for j in range(i + 1, len(s["sahneler"]) + 1) if not os.path.exists(os.path.join(klasor, f"{j:02d}.jpg")) or j in yeniden]
            break
print(f"Yeni çizim: {yeni} · Eksik kalan: {kalan or 'yok'}")
open(os.path.join(klasor, "eksik.txt"), "w").write(",".join(map(str, kalan)))
