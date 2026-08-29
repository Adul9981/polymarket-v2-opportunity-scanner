#!/usr/bin/env python3
"""Build 选手 × 英雄 锚点速查表（reports/intel_champion_anchor_lookup.html）。

数据源：champions.json（anchors）+ players.json（昵称）+ bp_signals.json。
浏览器内即时过滤（按 选手/英雄/方向/验证/联赛）。
Usage: python3 tools/build_intel_champion_lookup.py
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed;--ok:#34c759;--bad:#ff3b30;--part:#d97706}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.6;padding:28px 16px 60px}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:25px;font-weight:700;margin-bottom:6px}
.sub{color:var(--sub);font-size:13px;margin-bottom:18px}
.card{background:var(--card);border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
input{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:14px;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:600;font-size:12px;position:sticky;top:0;background:var(--card)}
.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}.part{color:var(--part);font-weight:600}
.tag{display:inline-block;border-radius:999px;padding:1px 9px;font-size:11px}
.tag.ok{background:#e9f9ee;color:var(--ok)}.tag.bad{background:#ffefee;color:var(--bad)}
.note{color:var(--sub);font-size:12px;margin-top:14px}
"""


def main() -> int:
    ch = json.load(open(ROOT / "docs/data/intel/champions.json", encoding="utf-8"))["champions"]
    pl = json.load(open(ROOT / "docs/data/intel/players.json", encoding="utf-8"))["players"]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    nick = {p["id"]: "、".join(p.get("nicknames", [])[:3]) for p in pl}

    rows = []
    for c in ch:
        for a in c.get("anchors", []):
            pid = a.get("player_id")
            v = a.get("verified", "")
            cls = "ok" if v.startswith("应验") else ("part" if v.startswith("部分") else ("bad" if v.startswith(("未应验", "未兑现", "打脸")) else ""))
            rows.append(
                f"<tr><td>{esc(pid or '—')}<br><span class=note>{esc(nick.get(pid,''))}</span></td>"
                f"<td>{esc(c['name'])}</td>"
                f"<td><span class='tag {cls if a.get('polarity')=='正' else 'bad'}'>{'正锚' if a.get('polarity')=='正' else '负锚'}</span></td>"
                f"<td {('class='+cls) if cls else ''}>{esc(v)}</td>"
                f"<td>{esc(a.get('match_id',''))}</td></tr>"
            )
    body = "".join(rows)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>选手 × 英雄 锚点速查表</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>选手 × 英雄 锚点速查表</h1>
<p class="sub">情报库 · 实体域 · BP 一出即可查"某选手 × 某英雄"的历史战绩/胜率锚 · 更新至 {now}（自动生成）</p>
<div class="card"><input id="q" placeholder="输入 选手 / 英雄 / 比赛 / 验证 过滤…">
<table><thead><tr><th>选手</th><th>英雄</th><th>方向</th><th>验证</th><th>出处比赛</th></tr></thead>
<tbody id="tb">{body}</tbody></table></div>
<p class="note">数据：docs/data/intel/champions.json（anchors）+ players.json；锚点为观众共识口径，赛后按官方结果回填。</p>
</div>
<script>const q=document.getElementById('q'),tb=document.getElementById('tb'),trs=tb.querySelectorAll('tr');
q.addEventListener('input',()=>{{const s=q.value.trim().toLowerCase();trs.forEach(r=>{{r.style.display=r.textContent.toLowerCase().includes(s)?'':'none';}});}});</script>
</body></html>"""
    out = ROOT / "reports" / "intel_champion_anchor_lookup.html"
    out.write_text(html, encoding="utf-8")
    print("written", out, len(html), "bytes | rows:", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
