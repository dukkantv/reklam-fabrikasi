// Kullanım: node uret.js eserim
// reklamlar/<klasor>/bilgi.json ve fotoğrafları okuyup sessiz videoyu cikti/ klasörüne yazar.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

(async () => {
  const klasor = process.argv[2];
  if (!klasor) { console.error('Klasör adı ver: node uret.js eserim'); process.exit(1); }
  const kok = __dirname;
  const veri = JSON.parse(fs.readFileSync(path.join(kok, 'reklamlar', klasor, 'bilgi.json'), 'utf8'));
  fs.mkdirSync(path.join(kok, 'cikti'), { recursive: true });
  const ad = veri.dosya_adi || klasor;
  const gecici = path.join(kok, 'cikti', ad + '_yaziliyor.mp4');
  const hedef = path.join(kok, 'cikti', ad + '_sessiz.mp4');

  const tarayici = await chromium.launch();
  const sayfa = await tarayici.newPage({ viewport: { width: 1080, height: 1920 } });
  await sayfa.goto('file://' + path.join(kok, 'sablon', 'reklam.html'));
  await sayfa.evaluate(([d, k]) => yukle(d, k), [veri, '../reklamlar/' + klasor]);
  await sayfa.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))));
  await sayfa.evaluate(() => document.fonts.ready);
  const toplam = await sayfa.evaluate(() => TOTAL);
  // Seslendirme adımı sahne başlangıçlarını bilsin diye kaydediyoruz
  fs.writeFileSync(path.join(kok, 'cikti', 'sahneler.json'), JSON.stringify(await sayfa.evaluate(() => SAHNELER)));

  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', gecici],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < toplam; f++) {
    await sayfa.evaluate(x => setFrame(x), f);
    const kare = await sayfa.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(kare)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 90 === 0) console.log(`kare ${f}/${toplam}`);
  }
  ff.stdin.end();
  const kod = await new Promise(r => ff.on('close', r));
  await tarayici.close();
  if (kod !== 0) { console.error('ffmpeg hata verdi'); process.exit(1); }
  fs.renameSync(gecici, hedef);
  console.log('Sessiz video hazır: ' + hedef);
})();
