// Kullanım: node kart.js "Birkaç dakika sonra…" cikti/kart.png [stil]
// Bölümlerin arasına giren yazı kartlarını (başlık, "birkaç dakika sonra" vb.) resim olarak çizer.
// stil: "gecis" (kırmızı, komik geçiş) veya "baslik" (siyah, bölüm adı)
const { chromium } = require('playwright');

(async () => {
  const [yazi, hedef, stil = 'gecis', renk = '#e3121b'] = process.argv.slice(2);
  const arka = stil === 'baslik'
    ? `radial-gradient(circle at 50% 40%, #2a2a2a, #0b0b0b 70%)`
    : `repeating-conic-gradient(from 0deg at 50% 50%, ${renk} 0 10deg, #b80d14 10deg 20deg)`;
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{margin:0;width:1080px;height:1920px;overflow:hidden}
    body{background:${arka};display:flex;align-items:center;justify-content:center;
      font-family:"Inter Display","Inter","DejaVu Sans",sans-serif}
    .k{max-width:900px;text-align:center;color:#fff;font-weight:900;font-size:${stil === 'baslik' ? 104 : 120}px;
      line-height:1.05;letter-spacing:-2px;text-shadow:0 8px 0 rgba(0,0,0,.35);transform:rotate(${stil === 'baslik' ? 0 : -4}deg)}
    .k span{display:block;font-size:46px;letter-spacing:4px;color:#ffd34d;margin-bottom:28px}
    .alt{position:absolute;bottom:90px;left:0;right:0;text-align:center;color:rgba(255,255,255,.6);font:600 32px "Inter",sans-serif}
  </style></head><body><div class="k">${yazi}</div><div class="alt">Dükkan TV</div></body></html>`;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.setContent(html);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: hedef, type: 'png' });
  await b.close();
})();
