#!/usr/bin/env python3
"""Build BP 信号兑现率统计页（reports/intel_bp_verification_stats.html）。

数据源：docs/data/intel/bp_signals.json + champions.json（anchors）。
风格：SAP/Apple。输出：BP 记录 / 联赛分布 / 兑现率 / 联赛负锚池 / 选手×英雄锚点。

Usage: python3 tools/build_intel_bp_stats.py
"""

from __future__ import annotations

import datetime
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def verdict_class(v: str) -> str:
    if v.startswith("应验"):
        return 'class="ok"'
    if v.startswith("部分"):
        return 'class="part"'
    if v.startswith(("未应验", "未兑现", "打脸", "refuted")):
        return 'class="bad"'
    return 'class="pend"'


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed;--ok:#34c759;--part:#d97706;--bad:#ff3b30;--pend:#86868b}
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
table{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:600;font-size:12px}
.ok{color:var(--ok);font-weight:600}
.part{color:var(--part);font-weight:600}
.bad{color:var(--bad);font-weight:600}
.pend{color:var(--pend)}
.note{color:var(--sub);font-size:12px;line-height:1.7;margin-top:14px}
.tag{display:inline-block;border-radius:999px;padding:1px 9px;font-size:11px;margin-right:5px}
.tag.ok{background:#e9f9ee;color:var(--ok)}
.tag.part{background:#fff4e5;color:var(--part)}
.tag.bad{background:#ffefee;color:var(--bad)}
.tag.pend{background:#f0f0f2;color:var(--pend)}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
"""


def main() -> int:
    bp = json.load(open(ROOT / "docs/data/intel/bp_signals.json", encoding="utf-8"))["records"]
    ch = json.load(open(ROOT / "docs/data/intel/champions.json", encoding="utf-8"))["champions"]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    def vcat(v: str) -> str:
        if v.startswith("应验"):
            return "应验"
        if v.startswith("部分"):
            return "部分"
        if v.startswith(("未应验", "未兑现", "打脸")):
            return "未应验"
        return "待验证"

    cats = Counter(vcat(x.get("verdict", "")) for x in bp)
    leagues = Counter(x.get("league", "") for x in bp)

    # 负锚池：bp_signals 中 proficiency/audience_doubt 含"必败/필패/负锚/7 连败"等
    pool = []
    for x in bp:
        text = (x.get("bp_point", "") + x.get("proficiency", "") + x.get("audience_doubt", ""))
        if any(k in text for k in ["필패", "必败", "负锚", "连败", "判负", "零胜率"]):
            pool.append(x)

    rows = []
    for x in sorted(bp, key=lambda r: r.get("id", ""), reverse=True):
        rows.append(
            f"<tr><td>{esc(x.get('match',''))}<br><span class='pend'>{esc(x.get('league',''))}</span></td>"
            f"<td>{esc(x.get('team',''))}</td>"
            f"<td>{esc(x.get('bp_point',''))}</td>"
            f"<td>{esc(x.get('proficiency',''))[:120]}</td>"
            f"<td {verdict_class(x.get('verdict',''))}>{esc(x.get('verdict',''))[:60]}</td></tr>"
        )

    anchors = []
    for c in ch:
        for a in c.get("anchors", []):
            anchors.append((c["id"], a.get("player_id"), a.get("polarity"), a.get("verified", ""), a.get("match_id", "")))
    anchor_rows = "".join(
        f"<tr><td>{esc(p or '—')}</td><td>{esc(h)}</td>"
        f"<td>{'<span class=ok>正锚</span>' if pol=='正' else '<span class=bad>负锚</span>'}</td>"
        f"<td {verdict_class(v)}>{esc(v)}</td><td>{esc(m)}</td></tr>"
        for (h, p, pol, v, m) in anchors
    )

    pool_rows = "".join(
        f"<tr><td>{esc(x.get('team',''))}</td><td>{esc(x.get('bp_point',''))}</td>"
        f"<td {verdict_class(x.get('verdict',''))}>{esc(x.get('verdict',''))[:50]}</td>"
        f"<td>{esc(x.get('league',''))}</td></tr>"
        for x in pool
    )

    league_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k, v in sorted(leagues.items(), key=lambda kv: -kv[1])
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BP 信号兑现率统计 · 情报库</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>BP 信号兑现率统计</h1>
<p class="sub">情报库 · 信号域（BP 锚点）· 数据源 docs/data/intel/bp_signals.json + champions.json · 更新至 {now}（自动生成）</p>
<div class="stats">
<div class="stat"><div class="num">{len(bp)}</div><div class="lbl">BP 信号记录</div></div>
<div class="stat"><div class="num">{cats.get('应验',0)}</div><div class="lbl">应验</div></div>
<div class="stat"><div class="num">{cats.get('部分',0)}</div><div class="lbl">部分应验</div></div>
<div class="stat"><div class="num">{cats.get('未应验',0)}</div><div class="lbl">未应验(反例)</div></div>
</div>
<div class="card"><h2>一、按联赛</h2>
<table><tr><th>联赛</th><th>BP 信号数</th></tr>{league_rows}</table>
<p class="note">兑现口径：verdict 首词归类（应验/部分/未应验/待验证）；"未应验"= 负锚未兑现或正锚打脸，是反例样本。</p></div>
<div class="card"><h2>二、联赛负锚池（"必败/判负/连败/零胜率"类）</h2>
<p>从 BP 信号中聚合的负锚观察池；CL 今日已 4 例（杰斯/奥拉夫/烬/巴德），应验率与反例并存——负锚非铁律。</p>
<table><tr><th>指向队伍</th><th>负锚点</th><th>验证</th><th>联赛</th></tr>{pool_rows}</table></div>
<div class="card"><h2>三、选手 × 英雄 锚点速查（champions.anchors）</h2>
<table><tr><th>选手</th><th>英雄</th><th>方向</th><th>验证</th><th>出处</th></tr>{anchor_rows}</table></div>
<div class="card"><h2>四、全部 BP 信号记录（按 ID 倒序）</h2>
<table><tr><th>比赛</th><th>队伍</th><th>BP 点</th><th>熟练度/战绩情报</th><th>验证</th></tr>{''.join(rows)}</table></div>
<p class="note">数据：docs/data/intel/bp_signals.json、champions.json；弹幕为低可信度信号需聚合；负锚/正锚均为观众共识口径，赛后按官方结果回填。</p>
</div></body></html>"""

    out = ROOT / "reports" / "intel_bp_verification_stats.html"
    out.write_text(html, encoding="utf-8")
    print("written", out, len(html), "bytes | pool:", len(pool), "anchors:", len(anchors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
