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

## Tam otomatik bölüm (Levent'in Maceraları) — elle klip üretmek YOK
Gizli anahtarlar: `FAL_KEY` (fal.ai), `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
1. **Actions → Otomatik Bölüm → Run workflow**, aşama: `karakter` (sadece ilk sefer: Levent'in yeni kostümü + Cemo çizilir, Telegram'a gelir).
2. Aşama: `taslak`, klasör: `eserim`, konu: (isteğe bağlı). Senaryo + 16-20 sahne resmi Telegram'a gelir (~100 TL).
3. Beğenmediğin sahne varsa aşama: `taslak`, "yeniden" kutusuna `3,7` yaz.
4. Aşama: `video` → sahneler hareketlendirilir, seslendirilir, altyazı + KASA + esnaf kartı eklenir, ~90-100 sn bölüm Telegram'a gelir.
- `hepsi` seçilirse onay beklemeden taslak + video birlikte yapılır.
- Kalite: `seedance-720p` (en ucuz) · `seedance-1080p` · `kling`.
- Yeni esnaf için `bilgi.json` içine `oto` bölümü ekle (`reklamlar/eserim/bilgi.json` örnek).
