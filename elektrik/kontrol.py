# Seslendirme kontrolü: klon sesin söylediğini yazıya döker (faster-whisper), metinle karşılaştırmak için kaydeder.
import json, os
from faster_whisper import WhisperModel
KOK = os.path.dirname(os.path.abspath(__file__))
m = WhisperModel("medium", device="cpu", compute_type="int8")
out = {}
for ad in json.load(open(os.path.join(KOK, "metin.json"), encoding="utf-8"))["sahneler"]:
    segs, _ = m.transcribe(os.path.join(KOK, "ses", ad + ".mp3"), language="tr", word_timestamps=True)
    out[ad] = [{"s": round(w.start, 2), "e": round(w.end, 2), "w": w.word} for sg in segs for w in sg.words]
    print(ad, " ".join(x["w"] for x in out[ad]), flush=True)
json.dump(out, open(os.path.join(KOK, "ses", "dokum.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
