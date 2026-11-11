// Dükkan TV — Telegram onay dinleyicisi + başvuru kutusu (Cloudflare Worker, ücretsiz plan)
//
// Ne yapar?
//  1) Telegram'daki butonlara basıldığı AN çalışır, mesajı hemen değiştirir:
//     - YouTube yayın onayı   (yt:onay:ID / yt:iptal:ID)
//     - Başvuru taslak onayı  (bv:onay:ID / bv:yeniden:ID / bv:iptal:ID)
//  2) Siteden gelen başvuru formunu ve fotoğrafları alır (POST /basvuru), saklar
//     ve Levent'e Telegram'dan "yeni başvuru" haberi verir.
//  3) GitHub işleri (YouTube Yayın, Başvuru Taslak) kararları ve başvuruları buradan okur.
//
// Gerekli ayarlar ("Cloudflare Yükle" işi hepsini otomatik yapar, kodda şifre yok):
//   ONAY    : KV namespace
//   GIZLI   : GitHub işleriyle paylaşılan gizli değer (bot anahtarından türetilir)
//   TG_TOKEN, TG_CHAT : Telegram bildirimleri için

const SITE = "https://dukkantv.github.io";
const AZAMI_FOTO = 16;
const AZAMI_FOTO_BAYT = 4 * 1024 * 1024; // sıkıştırılmış tek fotoğraf en fazla 4 MB
const GUN = 24 * 3600;

const cors = (h = {}) => ({
  "Access-Control-Allow-Origin": SITE,
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  ...h,
});
const json = (v, durum = 200, h = {}) => new Response(JSON.stringify(v), {
  status: durum, headers: { "Content-Type": "application/json; charset=utf-8", ...h } });

function yeniId() {
  const s = new Date(Date.now() + 3 * 3600 * 1000).toISOString(); // Türkiye saati
  const r = Math.random().toString(36).slice(2, 6);
  return s.slice(0, 10).replaceAll("-", "") + "-" + s.slice(11, 19).replaceAll(":", "") + "-" + r;
}

async function telegram(env, metod, govde) {
  if (!env.TG_TOKEN || !env.TG_CHAT) return null;
  const r = await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/${metod}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: env.TG_CHAT, ...govde }) });
  return r.json().catch(() => null);
}

function b64ToBytes(b64) {
  const s = atob(b64);
  const a = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
  return a;
}

const temiz = (v, n = 400) => String(v ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, n);

async function basvuruAl(req, env) {
  let g;
  try { g = await req.json(); } catch { return json({ ok: false, hata: "Form okunamadı" }, 400, cors()); }
  if (g.hp) return json({ ok: true, id: "0" }, 200, cors()); // bot tuzağı: sessizce yut

  // Aynı adresten saatte en fazla 6 başvuru
  const ip = req.headers.get("CF-Connecting-IP") || "?";
  const sayKey = "rl:" + ip + ":" + new Date().toISOString().slice(0, 13);
  const say = +(await env.ONAY.get(sayKey) || 0);
  if (say >= 6) return json({ ok: false, hata: "Çok fazla deneme. Lütfen biraz sonra tekrar deneyin." }, 429, cors());
  await env.ONAY.put(sayKey, String(say + 1), { expirationTtl: 3600 });

  const f = g.form || {};
  const form = {};
  for (const [k, v] of Object.entries(f)) {
    form[temiz(k, 40)] = Array.isArray(v) ? v.slice(0, 20).map(x => temiz(x, 200))
      : (v && typeof v === "object") ? JSON.parse(JSON.stringify(v).slice(0, 3000)) : temiz(v, 1500);
  }
  if (!form.ad || !form.tel || !form.one) return json({ ok: false, hata: "Zorunlu alanlar eksik" }, 400, cors());

  const id = yeniId();
  const fotolar = [];
  for (const [i, p] of (Array.isArray(g.fotolar) ? g.fotolar : []).slice(0, AZAMI_FOTO).entries()) {
    try {
      const bayt = b64ToBytes(String(p.veri || "").replace(/^data:image\/\w+;base64,/, ""));
      if (bayt.length < 1000 || bayt.length > AZAMI_FOTO_BAYT) continue;
      const anahtar = `bvf:${id}:${i}`;
      await env.ONAY.put(anahtar, bayt, { expirationTtl: 60 * GUN });
      fotolar.push({ anahtar, kategori: temiz(p.kategori, 30), baslik: temiz(p.baslik, 60) });
    } catch { /* bozuk fotoğrafı atla */ }
  }

  const kayit = { id, zaman: new Date().toISOString(), durum: "yeni", form, fotolar };
  await env.ONAY.put("bv:" + id, JSON.stringify(kayit), {
    expirationTtl: 60 * GUN, metadata: { durum: "yeni", ad: form.ad.slice(0, 60) } });

  await telegram(env, "sendMessage", { text:
    `🆕 Yeni başvuru geldi!\n\n🏪 ${form.ad}\n📦 ${form.paket || "—"}\n📞 ${form.tel}\n📸 ${fotolar.length} fotoğraf\n\n` +
    `Taslak hazırlanıyor, hazır olunca onayına gelecek. (No: ${id})` });

  return json({ ok: true, id, foto: fotolar.length }, 200, cors());
}

async function bvDurum(env, id, durum, ek = {}) {
  const v = await env.ONAY.get("bv:" + id);
  if (!v) return null;
  const kayit = { ...JSON.parse(v), ...ek, durum };
  await env.ONAY.put("bv:" + id, JSON.stringify(kayit), {
    expirationTtl: 60 * GUN, metadata: { durum, ad: String(kayit.form?.ad || "").slice(0, 60) } });
  return kayit;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const GIZLI = env.GIZLI;
    if (!GIZLI) return new Response("GIZLI ayarlı değil", { status: 500 });
    const yetkili = url.searchParams.get("k") === GIZLI;

    // 0) Siteden başvuru
    if (url.pathname === "/basvuru" && req.method === "OPTIONS") return new Response(null, { headers: cors() });
    if (url.pathname === "/basvuru" && req.method === "POST") return basvuruAl(req, env);

    // 1) Telegram'dan gelen buton basışları
    if (req.method === "POST" && url.pathname === "/telegram") {
      if (req.headers.get("X-Telegram-Bot-Api-Secret-Token") !== GIZLI) {
        return new Response("izin yok", { status: 403 });
      }
      const u = await req.json().catch(() => ({}));
      const cq = u.callback_query;
      if (!cq || !cq.data) return new Response("ok"); // butona basış değil, geç
      const [on, karar, id] = String(cq.data).split(":");
      const m = cq.message;
      const degistir = (ek) => (m && m.chat)
        ? Response.json({ method: "editMessageText", chat_id: m.chat.id, message_id: m.message_id,
                          text: (m.text || "").slice(0, 3800) + ek })
        : Response.json({ method: "answerCallbackQuery", callback_query_id: cq.id, text: ek.trim().split("\n")[0], show_alert: true });

      // YouTube yayın onayı
      if (on === "yt" && id && (karar === "onay" || karar === "iptal")) {
        await env.ONAY.put(id, JSON.stringify({ karar, zaman: new Date().toISOString() }),
                           { expirationTtl: 7 * GUN });
        return degistir(karar === "onay"
          ? "\n\n✅ ONAYLANDI\nSıradaki boş akşam saatinde yayına girecek. YouTube'a yüklenince ayrıca haber vereceğim."
          : "\n\n❌ İPTAL EDİLDİ\nBu video yayınlanmayacak.");
      }

      // Başvuru taslağı onayı
      if (on === "bv" && id && ["onay", "yeniden", "iptal"].includes(karar)) {
        const durum = { onay: "onaylandi", yeniden: "yeni", iptal: "iptal" }[karar];
        const k = await bvDurum(env, id, durum);
        if (!k) return degistir("\n\n⚠️ Bu başvuru bulunamadı (süresi dolmuş olabilir).");
        return degistir({
          onay: "\n\n✅ TASLAK ONAYLANDI\nVideo üretimi bir sonraki kontrolde başlayacak (en geç 1 saat). Bitince onayına gelecek.",
          yeniden: "\n\n🔄 YENİDEN YAZILACAK\nYeni taslak bir sonraki kontrolde hazırlanıp gelecek.",
          iptal: "\n\n❌ İPTAL EDİLDİ\nBu başvuru için video hazırlanmayacak.",
        }[karar]);
      }
      return Response.json({ method: "answerCallbackQuery", callback_query_id: cq.id, text: "Bu buton artık geçerli değil." });
    }

    // 2) GitHub işleri için uçlar (gizli değer şart)
    if (!yetkili) return new Response("Dükkan TV onay dinleyicisi çalışıyor ✅");

    if (url.pathname === "/onaylar") {
      if (req.method === "DELETE") {
        const id = url.searchParams.get("id");
        if (id && !id.includes(":")) await env.ONAY.delete(id);
        return json({ silindi: id });
      }
      const liste = await env.ONAY.list();
      const sonuc = {};
      for (const k of liste.keys) {
        if (k.name.includes(":")) continue; // başvuru/fotoğraf kayıtları değil, sadece yayın kararları
        const v = await env.ONAY.get(k.name);
        if (v) sonuc[k.name] = JSON.parse(v);
      }
      return json(sonuc);
    }

    if (url.pathname === "/basvurular") {
      const liste = await env.ONAY.list({ prefix: "bv:" });
      return json(liste.keys.map(k => ({ id: k.name.slice(3), ...(k.metadata || {}) })));
    }

    if (url.pathname === "/basvuru" && req.method === "GET") {
      const v = await env.ONAY.get("bv:" + url.searchParams.get("id"));
      return v ? new Response(v, { headers: { "Content-Type": "application/json; charset=utf-8" } }) : json({ hata: "yok" }, 404);
    }

    if (url.pathname === "/durum" && req.method === "POST") {
      const ek = await req.json().catch(() => ({}));
      const k = await bvDurum(env, url.searchParams.get("id"), url.searchParams.get("durum"), ek);
      return k ? json({ ok: true }) : json({ hata: "yok" }, 404);
    }

    if (url.pathname === "/foto") {
      const anahtar = url.searchParams.get("a") || "";
      if (!anahtar.startsWith("bvf:")) return json({ hata: "geçersiz" }, 400);
      const v = await env.ONAY.get(anahtar, { type: "arrayBuffer" });
      return v ? new Response(v, { headers: { "Content-Type": "image/jpeg" } }) : json({ hata: "yok" }, 404);
    }

    return new Response("Dükkan TV onay dinleyicisi çalışıyor ✅");
  },
};
