# Dükkan TV · İçerik Fabrikası

Üç içerik markasının videolarını otomatik üretir ve yayınlar: **Dükkan TV** (Levent & Cemo çizgi film skeçleri), **Drama Bite** (duygusal hikâyeler), **Kasa Kurgu** (Katil Kim? vakaları, 500 TL → 50.000 TL dizisi) ve **Gizli Tarih** (belgeseller).

**Gelir düzeni (14 Kasım 2026):** yalnızca GVK 20/B kapsamı — platform gelirleri (YouTube, Instagram, TikTok, Facebook) ve Play Store uygulamaları. Esnafa ücretli reklam videosu ve dijital ürün satışı yapılmaz; video açıklamalarına satış linki eklenmez (`urunler.json` boş).

## İçerik işleri (Actions)
- **Mizah Serisi / Otomatik Bölüm / Bölüm Üret** — Levent & Cemo skeçleri (konular `reklamlar/mizah-XX-*/bilgi.json`; meslek karakterleri hayalidir).
- **Levent & Cemo Derleme** — haftalık Shorts derlemesi ve aylık uzun video (ücretsiz, önbellekteki kliplerden).
- **Drama Bite Hikaye** — günlük duygusal hikâye, onaysız yayın.
- **Katil Kim Vakası / Kasa Kurgu Günlük** — Kasa Kurgu dizileri, onaysız yayın.
- **Uzun Video (Belgesel)** — Gizli Tarih ve uzun dedektif videoları.
- **Kanal Ayar** — kanal açıklamaları, oynatma listeleri, bannerlar (`kanal_ayarlari.json`, `bannerlar/`).

## YouTube otomasyonu (bilgisayar gerekmez)
- **YouTube Rapor** (sabah raporu): her sabah 08:47 üç markanın YouTube, Instagram ve TikTok raporu Telegram'a AYRI mesajlar hâlinde gelir; sonda onay bekleyen Dükkan TV videoları Onayla/Reddet butonlarıyla ve sistem uyarıları (izin süresi vb.) gelir (`rapor/son.json`).
- **Yayın yetkisi**: Dükkan TV = Levent'in onayı şart. Drama Bite ve Kasa Kurgu = onaysız otomatik yayın (Telegram'a "Durdur" butonlu bilgi gelir).
- **Yayın onayı**: Otomatik Bölüm videosu bitince Telegram'a "YouTube'a yüklensin mi?" mesajı gelir. ✅ Onayla → 19:00'da yayında. Cevapsız/iptal → yayınlanmaz.
- **YouTube İzin**: kanal izni (bir kez yapıldı: dukkantv, kasakurgu, dramabite).
- **Bütçe kilidi**: fal.ai harcaması `harcama/aylik.json` defterine yazılır; aylık limit 30 $ (`AYLIK_LIMIT`). Aşılacaksa iş başlamaz.
- Sahne kareleri artık Nano Banana 2 ile (0,08 $), bölümler varsayılan 30–40 sn, ilk plan en şaşırtıcı an (kanca).

## TikTok (taslak olarak)
- Gizli anahtarlar: `TT_CLIENT_KEY`, `TT_CLIENT_SECRET` (developers.tiktok.com → uygulama).
- **Actions → TikTok İzin** → kanal seç, kod boş → izin bağlantısı Telegram'a gelir → izin ver → açılan sayfadaki kodu kopyala → aynı işi kodla tekrar çalıştır.
- Yayın saatinde (19:00) video TikTok uygulamasına **taslak** olarak düşer; Telegram'a açıklama metni gelir. TikTok'ta bildirimi aç → açıklamayı yapıştır → Paylaş.
- TikTok denetimi onaylanınca doğrudan (otomatik) paylaşıma geçilecek.
