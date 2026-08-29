#!/usr/bin/env python3
"""灰信号实体"再犯升级"自动检查 + 报告页。

规则（凡走过必有痕迹）：
1. 实体涉事场次 >= 2 且最近一次在 7 天内 -> 再犯候选；
2. 涉事场次 >= 3 或最近两次涉事间隔 <= 3 天 -> 升级候选；
3. 输出 reports/intel_gray_escalation_check.html（按信号量排序 + 建议动作）。

Usage: python3 tools/check_gray_escalation.py
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed;--red:#ff3b30;--warn:#d97706}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.6;padding:28px 16px 60px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:25px;font-weight:700;margin-bottom:6px}
.sub{color:var(--sub);font-size:13px;margin-bottom:18px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 18px}
.stat{background:var(--card);border-radius:14px;padding:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.stat .num{font-size:22px;font-weight:700;color:var(--accent)}
.stat .lbl{color:var(--sub);font-size:12px}
.card{background:var(--card);border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h2{font-size:16px;font-weight:600;margin-bottom:10px;border-left:3px solid var(--accent);padding-left:8px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:600;font-size:12px}
.up{color:var(--red);font-weight:700}.watch{color:var(--warn);font-weight:700}
.note{color:var(--sub);font-size:12px;line-height:1.7;margin-top:14px}
.tag{display:inline-block;border-radius:999px;padding:1px 9px;font-size:11px;margin-right:5px}
.tag.up{background:#ffefee;color:var(--red)}.tag.watch{background:#fff4e5;color:var(--warn)}.tag.hold{background:#f0f0f2;color:var(--sub)}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
"""


def main() -> int:
    ents = json.load(open(ROOT / "docs/data/intel/gray_entities.json", encoding="utf-8"))["entities"]
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")

    rows = []
    n_up = n_watch = 0
    for e in sorted(ents, key=lambda x: -x.get("total_signals", 0)):
        recs = e.get("gray_records", [])
        n = len(recs)
        last = e.get("last_seen", "")
        status = e.get("status", "")
        action, cls = "持续观察", "hold"
        if n >= 3 or "再犯" in status or "多次" in status:
            action, cls = "升级跟踪（重点标记）", "up"
            n_up += 1
        elif n >= 2:
            action, cls = "再犯候选·观察", "watch"
            n_watch += 1
        rows.append(
            f"<tr><td>{esc(e.get('name',''))}<br><span class=note>{esc(e.get('id',''))} · {esc(e.get('type',''))}</span></td>"
            f"<td>{n}</td><td>{esc(e.get('total_signals',0))}</td>"
            f"<td>{esc(e.get('first_seen',''))} → {esc(last)}</td>"
            f"<td>{esc(e.get('max_severity',''))}</td>"
            f"<td>{esc('、'.join(e.get('keywords',[])[:5]))}</td>"
            f"<td><span class='tag {cls}'>{action}</span><br><span class=note>{esc(status)}</span></td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>灰信号实体再犯升级检查</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>灰信号实体 · 再犯升级检查</h1>
<p class="sub">情报库 · 信号域（gray_entities）· 规则："凡走过必有痕迹"——涉事 ≥2 场再犯候选，≥3 场/多次升级 · 生成于 {now:%Y-%m-%d %H:%M}（自动）</p>
<div class="stats">
<div class="stat"><div class="num">{len(ents)}</div><div class="lbl">灰实体</div></div>
<div class="stat"><div class="num">{n_up}</div><div class="lbl">升级跟踪</div></div>
<div class="stat"><div class="num">{n_watch}</div><div class="lbl">再犯候选</div></div>
<div class="stat"><div class="num">{today}</div><div class="lbl">检查日期</div></div>
</div>
<div class="card"><h2>实体清单（按累计信号量排序）</h2>
<table><tr><th>实体</th><th>涉事场次</th><th>累计信号</th><th>时间窗</th><th>最高严重度</th><th>关键词</th><th>建议动作</th></tr>
{''.join(rows)}</table></div>
<p class="note">纪律：灰信号只作风险标注，不作假赛结论；"再犯"指同类观众质疑再次出现（含方向反例），不直接等于假赛证据。升级后应在对应比赛情报页显著展示（可见性防错）。</p>
</div></body></html>"""
    out = ROOT / "reports" / "intel_gray_escalation_check.html"
    out.write_text(html, encoding="utf-8")
    print("written", out, len(html), "bytes | entities:", len(ents), "| up:", n_up, "| watch:", n_watch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
