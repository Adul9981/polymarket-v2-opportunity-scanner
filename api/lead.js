/**
 * /api/lead — 订阅咨询 / 留资登记（参考 musk-tweet-quant-v2 同款实现）
 *
 * 把订阅页表单提交推送到站长 Telegram（环境变量 TELEGRAM_BOT_TOKEN /
 * TELEGRAM_CHAT_ID），可同时推送给小助手（TELEGRAM_CHAT_ID_ASSISTANT）；
 * 无需数据库；带 honeypot 字段防简单机器人。
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

  const body = typeof req.body === "object" && req.body !== null ? req.body : {};
  const name = String(body.name || "").trim();
  const contact = String(body.contact || "").trim();
  const plan = String(body.plan || "").trim();
  const note = String(body.note || "").trim();
  const website = String(body.website || "").trim(); // honeypot
  const lead = {
    ts: new Date().toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" }),
    name,
    contact,
    plan,
    note,
  };
  if (website) {
    return res.status(200).json({ success: true }); // 机器人，静默丢弃
  }
  if (!contact || contact.length < 2) {
    return res.status(400).json({ error: "请填写联系方式（Telegram 用户名或 QQ 号）" });
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatIds = [
    process.env.TELEGRAM_CHAT_ID,
    process.env.TELEGRAM_CHAT_ID_ASSISTANT,
  ].filter(Boolean);
  const statsVps = process.env.STATS_VPS;
  const statsSecret = process.env.STATS_SECRET;
  if ((!token || chatIds.length === 0) && !(statsVps && statsSecret)) {
    return res.status(500).json({ error: "not configured" });
  }

  const text = [
    "📥 新的订阅登记",
    `昵称：${lead.name || "未填写"}`,
    `联系方式：${lead.contact}`,
    `想开通：${lead.plan || "未选择"}`,
    `备注：${lead.note || "无"}`,
    `时间：${lead.ts}`,
  ].join("\n");

  // 1) 先写 Gist 台账（无论通知成败，登记一条都不漏）
  const leadRecord = { ...lead, notify: "pending" };
  const recorded = await appendToGist(leadRecord);

  // 2) 再发通知（站长 + 小助手，任一路送达即成功）
  let anyDelivered = false;
  try {
    const results = await Promise.allSettled(
      chatIds.map(async (chatId) => {
        const r = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chat_id: chatId, text }),
        });
        const data = await r.json();
        if (!data.ok) throw new Error(data.description || "telegram error");
      })
    );
    anyDelivered = results.some((r) => r.status === "fulfilled");
  } catch {
    anyDelivered = false;
  }

  // 3) 回写通知状态（best-effort）
  if (recorded) {
    await markNotifyStatus(lead.ts, anyDelivered).catch(() => {});
  }

  // 只有"台账没记上 + 通知也没发出"才算失败
  if (!recorded && !anyDelivered) {
    return res.status(502).json({ error: "record failed" });
  }
  return res.status(200).json({ success: true, notify: anyDelivered, recorded });
}

async function appendToGist(lead) {
  const gToken = process.env.GITHUB_TOKEN;
  const gistId = process.env.LEADS_GIST_ID;
  if (!gToken || !gistId) return false;
  const base = `https://api.github.com/gists/${gistId}`;
  const headers = {
    Authorization: `token ${gToken}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
  try {
    const r = await fetch(base, { headers, signal: AbortSignal.timeout(8000) });
    if (!r.ok) return false;
    const gist = await r.json();
    let d;
    try {
      d = JSON.parse(gist.files?.["leads.json"]?.content || '{"leads":[]}');
    } catch {
      d = { leads: [] };
    }
    if (!Array.isArray(d.leads)) d.leads = [];
    d.updated_at = new Date().toISOString().slice(0, 10);
    d.leads.push(lead);
    const upd = await fetch(base, {
      method: "PATCH",
      headers,
      body: JSON.stringify({
        files: { "leads.json": { content: JSON.stringify(d, null, 2) + "\n" } },
      }),
      signal: AbortSignal.timeout(8000),
    });
    return upd.ok;
  } catch {
    return false;
  }
}

async function markNotifyStatus(ts, ok) {
  const gToken = process.env.GITHUB_TOKEN;
  const gistId = process.env.LEADS_GIST_ID;
  if (!gToken || !gistId || !ts) return false;
  const base = `https://api.github.com/gists/${gistId}`;
  const headers = {
    Authorization: `token ${gToken}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
  try {
    const r = await fetch(base, { headers, signal: AbortSignal.timeout(8000) });
    if (!r.ok) return false;
    const gist = await r.json();
    const d = JSON.parse(gist.files?.["leads.json"]?.content || '{"leads":[]}');
    const hit = (Array.isArray(d.leads) ? d.leads : []).find((x) => x.ts === ts);
    if (!hit) return false;
    hit.notify = ok ? "sent" : "failed";
    const upd = await fetch(base, {
      method: "PATCH",
      headers,
      body: JSON.stringify({
        files: { "leads.json": { content: JSON.stringify(d, null, 2) + "\n" } },
      }),
      signal: AbortSignal.timeout(8000),
    });
    return upd.ok;
  } catch {
    return false;
  }
}
