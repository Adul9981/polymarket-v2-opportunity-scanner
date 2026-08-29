#!/usr/bin/env python3
"""Inject Pro paywall into premium intel pages (idempotent).

免费层 = 赛后复盘（intel_danmu_<A>-<B>_<date>.html / _full_）、画像、灰信号、
可验证痕迹、历史库（match_* 时间轴壳免费进）。
Pro 层 = 实时/赛前节点情报（文件名含 _pre / _live / _BP_ / _G1_ / _G2_ / _G3_）
——节点页加载时校验会员（localStorage 24h 缓存，否则弹验证输入框：
TG 用户名 / QQ 号 -> /api/verify-member），通过后解锁。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SITE = Path(".danmu_intel_site") / "intel"
API = "https://danmu-intel-api.vercel.app"

PRO_RE = re.compile(r"intel_danmu_.*_(pre|live|bp|g[1-9])(?:[_.].*)?\.html$", re.I)
SLUG_RE = re.compile(
    r"(?:slug[=：]\s*)?((?:lol|cs2|dota2?)-[a-z0-9][a-z0-9-]*-\d{4}-\d{2}-\d{2})",
    re.I,
)
PAYWALL_RE = re.compile(r"<script>\s*\(function \(\) \{\s*var KEY = \"danmu_member_v1\";.*?</script>", re.S)

SCRIPT = f"""
<script>
(function () {{
  var KEY = "danmu_member_v1";
  try {{
    var c = JSON.parse(localStorage.getItem(KEY));
    if (c && c.member && c.checkedAt && Date.now() - c.checkedAt < 86400000) return;
  }} catch (e) {{}}
  var d = document.createElement("div");
  d.id = "paywall";
  d.style.cssText = "position:fixed;inset:0;background:rgba(245,245,247,.96);z-index:9999;display:flex;align-items:center;justify-content:center;padding:24px;font-family:-apple-system,'PingFang SC',sans-serif";
  d.innerHTML =
    '<div style="max-width:440px;width:100%;background:#fff;border:1px solid #e5e5ea;border-radius:20px;padding:32px 28px;box-shadow:0 16px 48px rgba(0,0,0,.10)">' +
    '<div style="text-align:center">' +
    '<div style="width:52px;height:52px;margin:0 auto 12px;border-radius:14px;background:linear-gradient(135deg,#0071e3,#5ac8fa);display:grid;place-items:center">' +
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg></div>' +
    '<div style="font-size:12px;font-weight:700;color:#0071e3;margin-bottom:6px">Pro · 实时情报</div>' +
    '<div style="font-size:20px;font-weight:800;color:#1d1d1f;margin-bottom:8px">此内容需要订阅</div>' +
    '<div style="font-size:13px;color:#6e6e73;margin-bottom:14px">局中情报 / 节点时间轴为付费内容 · 赛后复盘免费开放</div>' +
    '</div>' +
    '<div style="background:#fff7f0;border:1px solid #ffd8a8;border-radius:14px;padding:12px 14px;margin-bottom:14px;font-size:12.5px;color:#7a4a12;line-height:1.75">' +
    '🔥 早鸟 <b>$39/月</b>（限前 20 名，或 9/15 截止）· 季付 $105 · 年付 $390<br>' +
    '满 20 人涨价（正式 $59 起 · <b>$99 封顶</b>）· 订阅后终身锁价</div>' +
    '<a href="../subscribe.html#join" style="display:block;text-align:center;background:#0071e3;color:#fff;border-radius:12px;padding:13px;font-size:15px;font-weight:700;text-decoration:none;margin-bottom:12px">立即订阅 · $39/月 →</a>' +
    '<div style="display:flex;align-items:center;gap:10px;color:#c7c7cc;font-size:12px;margin:4px 0 12px"><div style="flex:1;height:1px;background:#e5e5ea"></div>已订阅？验证解锁<div style="flex:1;height:1px;background:#e5e5ea"></div></div>' +
    '<input id="pwId" placeholder="TG 用户名或 QQ 号" style="width:100%;border:1px solid #e5e5ea;border-radius:12px;padding:12px 14px;font-size:14px;font-family:inherit;margin-bottom:10px">' +
    '<button id="pwBtn" style="width:100%;background:#fff;color:#0071e3;border:1px solid #0071e3;border-radius:12px;padding:12px;font-size:14px;font-weight:600;cursor:pointer">验证解锁</button>' +
    '<div id="pwMsg" style="font-size:12px;color:#c92a2a;margin-top:10px;text-align:center"></div>' +
    '<div style="font-size:11px;color:#aeaeb2;text-align:center;margin-top:10px">免费看赛后复盘 · 历史情报库 · 画像与灰信号统计<br><a href="../subscribe.html#join" style="color:#0071e3">想先体验？$1 试用 3 天 →</a></div>' +
    '</div>';
  document.body.appendChild(d);
  document.getElementById("pwBtn").addEventListener("click", function () {{
    var id = document.getElementById("pwId").value.trim();
    var msg = document.getElementById("pwMsg");
    if (!id) {{ msg.textContent = "请输入账号"; return; }}
    msg.textContent = "验证中…";
    fetch("{API}/api/verify-member", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ identifier: id }})
    }}).then(function (r) {{ return r.json(); }}).then(function (data) {{
      if (data.member) {{
        localStorage.setItem(KEY, JSON.stringify({{ member: true, expires: data.expires || null, checkedAt: Date.now() }}));
        d.remove();
      }} else {{
        msg.textContent = data.freePeriod ? "当前为免费体验期" : "未找到该会员，请确认账号或先订阅";
      }}
    }}).catch(function () {{ msg.textContent = "验证服务暂不可用，请稍后再试"; }});
  }});
}})();
</script>"""

_TEAM_ALIAS: dict[str, str] = {}
_REG = Path(__file__).resolve().parents[1] / "docs" / "data" / "intel" / "team_names.json"
if _REG.exists():
    try:
        for _t in json.loads(_REG.read_text(encoding="utf-8")).get("teams", []):
            for _k in [_t["abbr"], _t["full"], *_t.get("aliases", [])]:
                _TEAM_ALIAS[str(_k).lower()] = _t["id"]
    except Exception:  # noqa: BLE001
        pass


def _norm_team(t: str) -> str:
    low = str(t).lower()
    if low in _TEAM_ALIAS:
        return _TEAM_ALIAS[low]
    stripped = re.sub(r"[.\s]", "", low)
    return _TEAM_ALIAS.get(stripped, stripped)


def page_key(name: str) -> str | None:
    """文件名 -> 'date|team1|team2'（归一，队伍排序），供已结束判定兜底（旧页无 slug 场景）。

    2026-08-26 修复（教训：LEC-FNC-NAVI_G1 旧文件名带联赛前缀且队伍顺序与
    结算名单相反，导致已结束比赛节点页仍被锁）：
    1) 先剥联赛前缀（LEC-/LCK-/LPL-…）；
    2) 队伍 id 排序后拼 key，与 finished_keys 侧一致，顺序无关。
    """
    body = name
    m0 = re.match(r"intel_danmu_(.*)", body)
    if m0:
        body = m0.group(1)
    body = re.sub(
        r"^(?:LCK CL|KeSPA Cup|LEC|LCK|LPL|LCP|CS2|Dota2|Valorant)[-_]",
        "",
        body,
        flags=re.I,
    )
    m = re.match(r"(.+?)-(.+?)_(\d{4}-\d{2}-\d{2})", body)
    if not m:
        return None
    # 队伍名后可能带节点后缀（_G1/_BP/_pre/_g1_bp/_live_0357），先剥离
    a = re.sub(r"_[A-Za-z0-9]+$", "", m.group(1))
    b = re.sub(r"_[A-Za-z0-9]+$", "", m.group(2))
    a, b, date = _norm_team(a), _norm_team(b), m.group(3)
    return f"{date}|{'-'.join(sorted([a, b]))}"


def inject_all(
    site_dir: Path = SITE,
    finished_slugs: frozenset[str] = frozenset(),
    finished_keys: frozenset[str] = frozenset(),
) -> int:
    """注入付费墙（Pro 页 = 实时/赛前节点）。

    2026-08-26 产品规则：**已结束比赛的实时情报对免费用户开放**——页面里能提取到
    slug 且 slug 在 finished_slugs 中的节点页不注入付费墙（赛后免费复盘闭环）。
    幂等：先清除旧脚本再按最新规则重注入。
    """
    changed = 0
    for p in site_dir.glob("*.html"):
        text = p.read_text(encoding="utf-8")
        clean = PAYWALL_RE.sub("", text)
        clean = re.sub(r"\n{2,}", "\n", clean)
        wants = bool(PRO_RE.search(p.name))
        if wants:
            m = SLUG_RE.search(clean)
            pk = page_key(p.name)
            if (m and m.group(1).lower() in finished_slugs) or (pk and pk in finished_keys):
                wants = False  # 已结束比赛：全部节点免费
        if wants and "</body>" in clean:
            clean = clean.replace("</body>", SCRIPT + "</body>", 1)
        if clean != text:
            p.write_text(clean, encoding="utf-8")
            changed += 1
    return changed
    print(f"injected paywall into {changed} Pro pages")
    return changed


def main() -> None:
    inject_all()


if __name__ == "__main__":
    main()
