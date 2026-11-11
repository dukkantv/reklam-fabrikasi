# YouTube API denetim (audit) başvurusu — hazır cevaplar

**Durum (12.11.2026):** Google Cloud projesi `dukkantv-yayin` → Audience: **In production** (Yayında), 3/100 kullanıcı.
API ile yüklenen videolar şu an herkese açık yayına girebiliyor (ör. Kasa Kurgu "Gün 10/30" videosu). Yani başvuru
**şimdilik zorunlu değil**. Şu durumlardan biri olursa hemen gönder:
- YouTube Studio'da API ile yüklenen bir video "Gizli (kilitli)" görünür ya da "denetlenmemiş API projesi" uyarısı gelir,
- Günlük kota (10.000 birim) yetmez.

**Form adresi:** https://support.google.com/youtube/contact/yt_api_form → "YouTube API Services - Audit and Quota Extension Form"
Form İngilizce; aşağıdaki cevapları kopyala-yapıştır yapabilirsin. Giriş: dukkan.tvstudio@gmail.com.

| Alan | Cevap |
|---|---|
| Organization name | Dükkan TV |
| Organization website | https://dukkantv.github.io |
| Organization address | Yıldırım, Bursa, Türkiye |
| Contact email | dukkan.tvstudio@gmail.com |
| Google Cloud project ID | dukkantv-yayin |
| API client name | Dükkan TV Yayın (internal publishing tool) |
| Who uses the client? | Internal only — the owner's own 3 YouTube channels (Dükkan TV, Drama Bite, Kasa Kurgu). No third-party users. |
| APIs used | YouTube Data API v3 (videos.insert, videos.update, channels.list, videos.list), YouTube Analytics API (reports.query) |

**Use case (kutucuğa yapıştır):**

> We are a small local video studio in Bursa, Turkey. Our internal tool runs on GitHub Actions and publishes short
> videos that we produce ourselves to our own three YouTube channels. Every video is reviewed before upload: for the
> Dükkan TV channel the owner approves each video with a Telegram button; for our two story channels the videos are
> checked by our production pipeline. The tool uploads videos as private with a scheduled publish time (publishAt)
> so that our channels do not publish at the same moment, and it reads YouTube Analytics once a day to prepare an
> internal performance report for the owner. We do not access, store or display any other user's data, we do not
> download or modify other creators' content, and the tool is not offered to anyone outside our team. OAuth refresh
> tokens are stored encrypted and are only used for our own channels.

**Expected daily quota:** ~10 uploads × 1.600 + rapor ≈ 17.000 birim → istenecek kota: **25.000 units/day**.

**Ekran kaydı (formda istenirse):** Telegram'da onay butonu → GitHub Actions "YouTube Yayın" çalışması → YouTube Studio'da
planlı video. Kaydı telefondan alıp YouTube'a "Liste dışı" yükle, bağlantıyı forma yapıştır.
