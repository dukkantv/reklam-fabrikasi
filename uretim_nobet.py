# Günlük üretim nöbetçisi (23 Kas 2026).
# GitHub'ın planlı tetiklemeleri (cron) üretimleri 7–8 saat geç başlatıyordu (ör. 12:07'lik Drama Bite 23:28'de
# çalıştı), bu yüzden videolar ya çok geç saate ya da ertesi güne kayıyordu. "YouTube Yayın" işi her çalıştığında bu
# betik çağrılır: hedef saati gelmiş ve bugün henüz çalışmamış üretim işlerini hemen başlatır (workflow_dispatch
# gecikmesiz çalışır). Böylece her kanalın videosu sabah hazırlanır, öğleden sonra/akşam yayına girer.
#
# Kullanım: python3 uretim_nobet.py          → gerekenleri başlatır
#           python3 uretim_nobet.py saatler  → bugünün kalan hedef saatlerini yazar (nobet.py kullanır)
import datetime as dt
import glob
import json
import os
import subprocess
import sys

TR = dt.timezone(dt.timedelta(hours=3))
KOK = os.path.dirname(os.path.abspath(__file__))
DEPO = os.environ.get("GITHUB_REPOSITORY", "dukkantv/reklam-fabrikasi")

# iş dosyası: (günlük hedef saatler (TR), dispatch girdileri)
# Saat sayısı = o iş için günde kaç çalışma isteniyor.
ISLER = {
    "youtube-rapor.yml": (["08:00"], {}),       # sabah raporu + konu analizi (09:47 Claude raporundan önce hazır olsun)
    "ne-olur.yml":     (["06:30", "13:00"], {}),   # Gizli Tarih: günde 2 (12:30 ve 20:00)            # Gizli Tarih "Ne Olur?" (her gün; gerek yoksa iş kendisi atlar)
    # 23 Kas 2026 (Levent): odak kanallar Dükkan TV, Drama Bite, Gizli Tarih → Drama Bite günde 2 hikâye
    "drama-bite.yml":  (["07:00", "11:30"], {}),   # Drama Bite hikâyesi
    "katil-kim.yml":   (["07:20", "10:30"], {}),   # Kasa Kurgu: günde 2 Katil Kim? vakası
    "arena.yml":       (["07:40"], {}),            # 81 İl Turnuvası maçı
}


def gh(*a):
    return subprocess.run(["gh", *a], capture_output=True, text=True)


def bugun_calisan(is_dosyasi, bugun):
    """Bugün (TR) başlatılmış, iptal edilmemiş çalışma sayısı."""
    bas = dt.datetime(bugun.year, bugun.month, bugun.day, tzinfo=TR).astimezone(dt.timezone.utc)
    r = gh("api", f"repos/{DEPO}/actions/workflows/{is_dosyasi}/runs?per_page=30&created=%3E%3D{bas:%Y-%m-%dT%H:%M:%SZ}")
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:200])
    kosular = json.loads(r.stdout).get("workflow_runs", [])
    return sum(1 for k in kosular if k.get("conclusion") not in ("cancelled", "skipped"))


def arena_gerekli():
    """arena.yml'deki 'Bekleyen maç var mı?' kontrolünün aynısı (elle başlatma bu kontrolü atladığı için)."""
    simdi = dt.datetime.now(dt.timezone.utc)
    for p in glob.glob(os.path.join(KOK, "kuyruk", "*.json")):
        try:
            k = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if k.get("kanal") == "ilturnuva" and (not k.get("yayin") or
                                             dt.datetime.fromisoformat(k["yayin"]) > simdi + dt.timedelta(hours=8)):
            return False
    return os.path.exists(os.path.join(KOK, "tokens", "ilturnuva.enc"))


def saat(bugun, s):
    hh, mm = map(int, s.split(":"))
    return dt.datetime(bugun.year, bugun.month, bugun.day, hh, mm, tzinfo=TR)


def calistir():
    simdi = dt.datetime.now(TR)
    bugun = simdi.date()
    for is_dosyasi, (saatler, girdi) in ISLER.items():
        gecen = sum(1 for s in saatler if saat(bugun, s) <= simdi)
        if not gecen:
            continue
        try:
            n = bugun_calisan(is_dosyasi, bugun)
        except Exception as e:
            print(f"{is_dosyasi}: çalışmalar okunamadı ({e})")
            continue
        if n >= gecen:
            print(f"{is_dosyasi}: bugün {n} çalışma var, tamam")
            continue
        if is_dosyasi == "arena.yml" and not arena_gerekli():
            print("arena.yml: yarına planlı maç zaten var, atlandı")
            continue
        ek = [x for k, v in girdi.items() for x in ("-f", f"{k}={v}")]
        r = gh("workflow", "run", is_dosyasi, "--ref", "main", "-R", DEPO, *ek)
        print(f"{is_dosyasi}: başlatıldı ({n}/{gecen})" if r.returncode == 0 else f"{is_dosyasi}: başlatılamadı {r.stderr[:200]}")


def kalan_saatler():
    """nobet.py için: bugün ve yarın sabah gelecek hedef saatler."""
    simdi = dt.datetime.now(TR)
    sonuc = []
    for gun in (0, 1):
        g = (simdi + dt.timedelta(days=gun)).date()
        for saatler, _ in ISLER.values():
            for s in saatler:
                z = saat(g, s) + dt.timedelta(minutes=2)
                if z > simdi:
                    sonuc.append(z)
    return sorted(sonuc)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "saatler":
        print("\n".join(z.isoformat() for z in kalan_saatler()))
    else:
        calistir()
