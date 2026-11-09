# Dükkan TV · Reklam Fabrikası

Esnaf reklam videolarını otomatik üretir: animasyonlu sahneler + Türkçe seslendirme (edge-tts, ücretsiz) → dikey 1080x1920 MP4 → Telegram.

## Nasıl kullanılır (telefondan)
1. **Actions** sekmesi → **Reklam Üret** → **Run workflow**
2. Klasör adını yaz (örn. `eserim`) → yeşil **Run workflow**
3. Birkaç dakika sonra video Telegram'a gelir (ya da çalışmanın sayfasındaki **Artifacts** kısmından indirilir).

## Yeni esnaf eklemek
`reklamlar/` altına yeni klasör aç (örn. `kivam-pasta`), içine:
- `bilgi.json` — yazılar, telefon, adres, seslendirme cümleleri (`reklamlar/eserim/bilgi.json` örnek)
- logo, dükkan fotoğrafı, (izinle) dükkan sahibinin fotoğrafı

## Dosyalar
- `sablon/reklam.html` — 5 sahnelik reklam tasarımı
- `uret.js` — sahneleri kare kare çizip sessiz video yapar
- `seslendir.py` — cümleleri seslendirip videoya ekler
- `.github/workflows/reklam-uret.yml` — "Reklam Üret" düğmesi

## Çizgi film bölümü (Levent'in Maceraları)
1. Gemini/Kling'de ürettiğin klipleri **sırayla** Dükkan TV Telegram botuna gönder (1. klip önce).
2. **Actions** → **Bölüm Üret** → klasör adı (örn. `eserim`) → **Run workflow**.
3. Sistem klipleri bottan alır; `reklamlar/<klasor>/bolum.json` akışına göre başlık kartı, "Birkaç dakika sonra…" kartları ve esnafın bilgi kartıyla birleştirip Telegram'a gönderir. Kullanılan klipler bot kuyruğundan silinir.

## Tam otomatik bölüm (Levent'in Maceraları) — dudak senkronlu
Gizli anahtarlar: `FAL_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

**Actions → Otomatik Bölüm → Run workflow**
1. `karakter` (bir kez): Levent (yeni kostüm) ve Cemo için karakter kartları (önden/yandan/arkadan + 5 ifade). Her sahne bu kartlara bakılarak çizilir.
2. `ses` (bir kez): ElevenLabs Türkçe ses kütüphanesinden her role (levent, cemo, esnaf, erkek, kadin) ayrı, sabit bir ses seçilir; örnekler Telegram'a gelir. Beğenmediğin ses için "yeniden" kutusuna rolü yaz (ör. `cemo`).
3. `taslak`: Gemini senaryoyu plan/karşı plan olarak yazar (22-28 plan). Her plan çizilir ve Gemini yüzleri karakter kartıyla karşılaştırır; tutmayan plan otomatik yeniden çizilir. Beğenmediğin planlar için "yeniden" kutusuna `3,7` yaz.
4. `video`: konuşan planlar = karakterin sabit sesi + Kling AI Avatar ile birebir dudak senkronu; aksiyon planları = Seedance. Altyazı, KASA, başlık ve esnaf kartı eklenir, ~100 sn bölüm Telegram'a gelir.
- `hepsi`: taslak + video onaysız.  Kalite: `standart` · `pro` (daha net yüz/dudak).
- Yeni esnaf için `bilgi.json` içine `oto` bölümü ekle (`reklamlar/eserim/bilgi.json` örnek).

## Dükkan TV kendi tanıtım bölümü (kısa)
`reklamlar/dukkantv` klasörü Dükkan TV'nin kendi tanıtımıdır: hayali simitçi Hasan Amca, ~40 sn, telefon numarası yok (kapanışta site + hesaplar).
**Actions → Otomatik Bölüm → Run workflow** · klasör: `dukkantv` · aşama: `taslak` → planlar Telegram'a gelir → beğenince aşama: `video`.
Herhangi bir esnaf için kısa bölüm: `bilgi.json` → `oto` içine `"toplam_sure": "35-45"`, `"plan_sayisi": "10-13"`, `"dukkanda_en_az": 4` ekle.
Kapanış kartında `telefon`/`adres` boş bırakılırsa o satır gizlenir; `sosyal` satırı eklenebilir.

## YouTube otomasyonu (bilgisayar gerekmez)
- **YouTube Rapor**: her sabah 08:47 üç kanalın istatistiği Telegram'a gelir (`rapor/son.json`).
- **Yayın onayı**: Otomatik Bölüm videosu bitince Telegram'a "YouTube'a yüklensin mi?" mesajı gelir. ✅ Onayla → 19:00'da yayında. Cevapsız/iptal → yayınlanmaz.
- **YouTube İzin**: kanal izni (bir kez yapıldı: dukkantv, kasakurgu, dramabite).
- **Bütçe kilidi**: fal.ai harcaması `harcama/aylik.json` defterine yazılır; aylık limit 30 $ (`AYLIK_LIMIT`). Aşılacaksa iş başlamaz.
- Sahne kareleri artık Nano Banana 2 ile (0,08 $), bölümler varsayılan 30–40 sn, ilk plan en şaşırtıcı an (kanca).
