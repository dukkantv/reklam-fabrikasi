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

## Büyüme kuralları (23 Kasım 2026 · Onur Naci Öztürkler "YouTube'a başlamadan önce bilmek istediğim 10 şey" incelemesi)
- **100 video kuralı:** hiçbir seri 100. videodan önce bırakılmaz, tutan biçim (başlık kalıbı, kanca, süre) sık sık değiştirilmez. 500 TL serisi 30. güne kadar tamamlanır.
- **Shorts + uzun karışımı:** YPP için 4.000 saat uzun video izlenmesi gerekir (Shorts izlenmesi saymaz). **Haftalık Uzun Video** işi her Pazar 11:23'te 81 İl Turnuvası ("Haftanın Tüm Maçları") ve Drama Bite ("Haftanın Hikâyeleri") için haftanın kısa videolarından ücretsiz yatay uzun video yapar; bölümler (chapters) ve kapak otomatik. Kısa videoların kalıcı kopyası `arsiv` sürümünde tutulur (`yt_kuyruk.py` → `arsive_koy`).
- **Tutanı tekrarla:** 16–22 Kasım haftasında GTA 6 haber videosu üç kanalda birden en çok izlenen oldu → 11:00 güncel haber kuralı (fayda sağlayacağı kesinse) daha sık kullanılır.
- **Beğeni çağrısı:** 81 İl maç sonunda "Şehrin tur atladıysa BEĞEN, yorumlara yaz!" (1.592 izlenmeye 10 beğeni vardı).
- **Başlık ve kanca önce:** Drama Bite 3 kanca adayı yazıp en güçlüsünü seçer; başlıklar kısa ve merak uyandıran tek ifade (15 Kasım analizi).

## Başlık, etiket ve kapak (27 Kasım 2026 · `kapak_seo.py`)
- Her video yayın kuyruğuna girerken (`yt_kuyruk.ekle`) başlık, etiket ve kapak otomatik iyileştirilir. Kapatmak için `KAPAK_SEO=0`.
- **Başlık:** Gemini, rakip araştırmasından çıkan kurallarla (aranan ifade başta, 35–65 karakter, sayı/soru kalıbı, yalan vaat yok) yeniden yazar. Seri ifadeleri ("Katil Kim", "500 TL", "Ne Olur", "81 İl", "Levent & Cemo") ve sayılar korunmazsa eski başlık kalır.
- **Etiketler:** YouTube arama önerilerinden derlenmiş kanal havuzundan başlığa en yakın aramalar + marka etiketleri (500 karakter sınırı).
- **Kapak:** Shorts NEON tarzında (koyu sahne, kanal renginde parlayan yazı, neon çerçeve ve rozet; eski tarz için `KAPAK_STIL=klasik`). Uzun videolarda 1–3 kelime, dev kalın yazı, siyah kontur, kırmızı kutu vurgusu, sembol rozeti (?, !, %1, yıl, sayı). Shorts'ta 1080x1920, yazı ana sayfanın 4:5 kırpmasına sığar; YouTube'a video işlendikten sonra (`kapaklar`), Instagram'a Reels kapak resmi olarak gider. Belgesellerde temiz sahne resminden 1280x720.
- **Neon şablon (27 Kas 2026):** "Ne Olur?", güncel haber, Doğru Bilinen Yanlışlar, hayvanlar ve telefon kısaları (`neolur/render.py`) Dükkan TV neon dilinde: koyu neon gece, parlayan yazılar, neon çerçeveli başlık ve kartlar, neon zaman çizelgesi, üstte seri etiketi (`ust_yazi`, haberde GÜNDEM), altta ilerleme çubuğu, "Yorumlara yaz" neon düğmesi.
- Kanal anahtar kelimeleri `kanal_ayarlari.json`'da Studio'daki güncel hâliyle aynı (27 Kasım'da arama verisine göre genişletildi).

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
