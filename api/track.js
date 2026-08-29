/**
 * /api/track — 页面访问打点（浏览器调用）
 *
 * 中转：浏览器 -> Vercel(https) -> VPS stats server，避免 GitHub Pages
 * https 页面直接调 http 被 mixed-content 拦截。密钥由环境变量提供。
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
  const base = process.env.STATS_VPS;
  const secret = process.env.STATS_SECRET;
  if (!base || !secret) {
    return res.status(200).json({ ok: true }); // 未配置时静默
  }
  const body = typeof req.body === "object" && req.body !== null ? req.body : {};
  try {
    await fetch(`${base}/track`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Stats-Secret": secret,
      },
      body: JSON.stringify({
        page: String(body.page || "/").slice(0, 200),
        ref: String(body.ref || ""),
        visitor: String(body.visitor || "").slice(0, 64),
      }),
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    /* 统计失败不影响页面 */
  }
  return res.status(200).json({ ok: true });
}
