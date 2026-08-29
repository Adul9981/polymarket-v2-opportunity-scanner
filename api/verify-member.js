/**
 * /api/verify-member — 会员校验（参考 musk-tweet-quant-v2 同款实现）
 *
 * 免费体验期（FREE_UNTIL 之前）任何用户视为会员；之后读取名单
 * （优先 VPS：STATS_VPS + STATS_SECRET -> /members；回退私有 Gist：
 * MEMBERS_GIST_RAW_URL），
 * 按 Telegram 用户名（忽略 @、大小写）或数字 ID（QQ 号）匹配；
 * expires 过期视为非会员。
 *
 * 名单格式见 data/members.example.json。
 */
const FREE_UNTIL = Date.parse(process.env.FREE_UNTIL || "2026-08-24T00:00:00+08:00");

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

  const now = Date.now();
  if (now < FREE_UNTIL) {
    return res.status(200).json({ member: true, freePeriod: true, expires: null });
  }

  const body = typeof req.body === "object" && req.body !== null ? req.body : {};
  const identifier = String(body.identifier || "").trim().replace(/^@/, "").toLowerCase();
  if (!identifier) {
    return res.status(400).json({ error: "请输入登记的会员账号（TG 用户名或 QQ 号）" });
  }

  const gistUrl = process.env.MEMBERS_GIST_RAW_URL;
  const statsVps = process.env.STATS_VPS;
  const statsSecret = process.env.STATS_SECRET;

  try {
    let data = { members: [] };
    if (statsVps && statsSecret) {
      const r = await fetch(`${statsVps}/members?secret=${encodeURIComponent(statsSecret)}`, {
        signal: AbortSignal.timeout(6000),
      });
      if (r.ok) data = await r.json();
    }
    if ((!Array.isArray(data?.members) || data.members.length === 0) && gistUrl) {
      const r = await fetch(gistUrl, {
        headers: { "User-Agent": "danmu-intel" },
        signal: AbortSignal.timeout(8000),
      });
      if (r.ok) data = await r.json();
    }
    const members = Array.isArray(data?.members) ? data.members : [];
    const hit = members.find((m) => {
      const tg = String(m.tg || "").replace(/^@/, "").toLowerCase();
      const id = String(m.id || "").toLowerCase();
      return tg === identifier || id === identifier;
    });
    if (!hit) {
      return res.status(200).json({ member: false, freePeriod: false });
    }
    const expires = hit.expires ? Date.parse(hit.expires) : Infinity;
    const ok = expires >= now;
    return res.status(200).json({
      member: ok,
      freePeriod: false,
      plan: hit.plan || null,
      expires: ok ? hit.expires || null : null,
    });
  } catch (err) {
    return res.status(502).json({ error: "membership check failed", message: err.message });
  }
}
