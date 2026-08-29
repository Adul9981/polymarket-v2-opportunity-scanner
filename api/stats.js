/**
 * /api/stats — 网站统计查询（管理员）
 */
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  const base = process.env.STATS_VPS;
  const secret = process.env.STATS_SECRET;
  if (!base || !secret) {
    return res.status(200).json({ error: "not configured" });
  }
  try {
    const r = await fetch(`${base}/stats?secret=${encodeURIComponent(secret)}`, {
      signal: AbortSignal.timeout(6000),
    });
    const data = await r.json();
    // 用户透明度：附上会员登记数（供订阅页/首页展示"登记人数/在用人数"）
    try {
      const mr = await fetch(`${base}/members?secret=${encodeURIComponent(secret)}`, {
        signal: AbortSignal.timeout(6000),
      });
      data.members_status = mr.status;
      if (mr.ok) {
        const md = await mr.json();
        const members = Array.isArray(md?.members) ? md.members : [];
        const now = Date.now();
        const active = members.filter((m) => {
          if (!m?.expires) return true;
          return Date.parse(m.expires) >= now;
        });
        data.members_total = members.length;
        data.members_active = active.length;
        data.members_plans = active.reduce((acc, m) => {
          const p = m?.plan || "free";
          acc[p] = (acc[p] || 0) + 1;
          return acc;
        }, {});
      }
    } catch (err) {
      data.members_total = null;
      data.members_active = null;
      data.members_error = String(err?.message || err);
    }
    return res.status(200).json(data);
  } catch (err) {
    return res.status(502).json({ error: "stats fetch failed", message: err.message });
  }
}
