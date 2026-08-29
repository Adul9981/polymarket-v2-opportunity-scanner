/**
 * /api/alert — 服务器资源预警 → Telegram（复用订阅登记的 bot token）。
 *
 * 供服务器 resource_watchdog 调用：POST {text} 即给站长推送一条告警。
 */
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    return res.status(204).end();
  }
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  const text = String((req.body && req.body.text) || "").trim();
  if (!text || text.length > 2000) {
    return res.status(400).json({ error: "text required (<=2000)" });
  }
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    return res.status(500).json({ error: "not configured" });
  }
  try {
    const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text: `⚠️ ${text}` }),
    });
    const data = await r.json();
    if (!data.ok) throw new Error(data.description || "telegram error");
    return res.status(200).json({ success: true });
  } catch (err) {
    return res.status(502).json({ error: "alert failed", message: err.message });
  }
}
