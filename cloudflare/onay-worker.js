// Dükkan TV — Telegram onay dinleyicisi (Cloudflare Worker, ücretsiz plan)
//
// Ne yapar?
//  1) Telegram'da "✅ Onayla" / "❌ Yayınlama" butonuna basıldığı AN çalışır.
//  2) Mesajı hemen "✅ ONAYLANDI" (ya da "❌ İPTAL") olarak değiştirir, butonları kaldırır.
//  3) Kararı KV deposuna (ONAY) yazar. GitHub'daki "YouTube Yayın" işi her kontrolde
//     buradan kararları okur ve videoyu yükler.
//
// Telegram bot anahtarı burada YOK: mesajı değiştirme isteği, Telegram'a verilen
// cevabın içinde gönderilir (webhook cevabı), o yüzden anahtar gerekmez.
//
// Gerekli ayarlar: "ONAY" adında KV namespace + "GIZLI" adında Worker gizli değişkeni
// (GIZLI, "Cloudflare Yükle" işinde bot anahtarından otomatik türetilir; kodda şifre yok).

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const GIZLI = env.GIZLI;
    if (!GIZLI) return new Response("GIZLI ayarlı değil", { status: 500 });

    // 1) Telegram'dan gelen buton basışları
    if (req.method === "POST" && url.pathname === "/telegram") {
      if (req.headers.get("X-Telegram-Bot-Api-Secret-Token") !== GIZLI) {
        return new Response("izin yok", { status: 403 });
      }
      const u = await req.json().catch(() => ({}));
      const cq = u.callback_query;
      if (!cq || !cq.data) return new Response("ok"); // butona basış değil, geç

      const [on, karar, id] = String(cq.data).split(":");
      if (on !== "yt" || !id || (karar !== "onay" && karar !== "iptal")) {
        return Response.json({ method: "answerCallbackQuery", callback_query_id: cq.id, text: "Bu buton artık geçerli değil." });
      }

      await env.ONAY.put(id, JSON.stringify({ karar, zaman: new Date().toISOString() }),
                         { expirationTtl: 7 * 24 * 3600 });

      const ek = karar === "onay"
        ? "\n\n✅ ONAYLANDI\nSıradaki boş akşam saatinde yayına girecek. YouTube'a yüklenince ayrıca haber vereceğim."
        : "\n\n❌ İPTAL EDİLDİ\nBu video yayınlanmayacak.";
      const m = cq.message;
      if (m && m.chat) {
        // Mesajı değiştir: butonlar kalkar, ne olduğu açıkça yazar
        return Response.json({
          method: "editMessageText",
          chat_id: m.chat.id,
          message_id: m.message_id,
          text: (m.text || "").slice(0, 3800) + ek,
        });
      }
      return Response.json({ method: "answerCallbackQuery", callback_query_id: cq.id,
                             text: karar === "onay" ? "✅ Onaylandı" : "❌ İptal edildi", show_alert: true });
    }

    // 2) GitHub işinin kararları okuması / okuduktan sonra silmesi
    if (url.pathname === "/onaylar") {
      if (url.searchParams.get("k") !== GIZLI) return new Response("izin yok", { status: 403 });
      if (req.method === "DELETE") {
        const id = url.searchParams.get("id");
        if (id) await env.ONAY.delete(id);
        return Response.json({ silindi: id });
      }
      const liste = await env.ONAY.list();
      const sonuc = {};
      for (const k of liste.keys) {
        const v = await env.ONAY.get(k.name);
        if (v) sonuc[k.name] = JSON.parse(v);
      }
      return Response.json(sonuc);
    }

    return new Response("Dükkan TV onay dinleyicisi çalışıyor ✅");
  },
};
