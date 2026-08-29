#!/usr/bin/env python3
"""生成「赛前速览」情报页：结合已有情报库，比赛前快速查询一页看全。

用法：
  python3 tools/build_intel_pregame.py --teams KC,SHFT --league LEC --date 2026-08-24
  python3 tools/build_intel_pregame.py --teams A,B --league LPL --date 2026-08-25 --slug lol-a-b-2026-08-25
输出：reports/intel_pregame_<A>-<B>_<date>.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"
OUT = ROOT / "reports"


def load(name: str) -> dict:
    return json.loads((INTEL / name).read_text(encoding="utf-8"))


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.7;padding:28px 16px 60px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:25px;font-weight:700;margin-bottom:6px}
.sub{color:var(--sub);font-size:14px;margin-bottom:22px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px}
.stat{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.stat .num{font-size:22px;font-weight:700;color:var(--accent)}
.stat .lbl{color:var(--sub);font-size:12px;margin-top:2px}
.card{background:var(--card);border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h2{font-size:18px;font-weight:700;margin-bottom:10px}
h3{font-size:14px;font-weight:600;margin-bottom:6px;color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:600}
ul{margin:0 0 8px 18px}li{margin-bottom:4px;font-size:14px}
.warn{background:#fff7f0;border-left:4px solid #ff9500;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:12px}
.ok{background:#f2f9f2;border-left:4px solid #34c759;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:12px}
.chip{display:inline-block;border-radius:999px;padding:2px 10px;font-size:11px;margin:2px 4px 2px 0}
.neg{background:#fff0f0;color:#d0021b}.pos{background:#eaf6ec;color:#1d7a35}.neu{background:#f0f4ff;color:#0071e3}
.note{color:var(--sub);font-size:12px;margin-top:20px;line-height:1.8}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teams", required=True, help="A,B")
    ap.add_argument("--league", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--slug", default="", help="Polymarket event slug（可选）")
    args = ap.parse_args()
    teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    if len(teams) != 2:
        print("需要两个队伍 A,B")
        return 1
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = args.slug

    teams_data = {t["id"]: t for t in load("teams.json")["teams"]}
    players = load("players.json")["players"]
    champs = load("champions.json")["champions"]
    comps = load("compositions.json")["compositions"]
    leagues = {l["id"]: l for l in load("leagues.json")["leagues"]}
    matches = load("matches.json")["matches"]

    def norm(s: str) -> str:
        return re.sub(r"[（(].*?[）)]", "", str(s)).strip().lower().replace(" ", "_")

    def team_block(tid: str) -> str:
        t = teams_data.get(tid, {})
        name = t.get("name", tid)
        danmu = t.get("danmu", {})
        gh = t.get("gray_history", {})
        tags = danmu.get("tags", [])
        tplayers = [p for p in players if norm(p.get("team", "")) == tid or norm(str(p.get("team", ""))) == norm(name)]
        tchamps = [c for c in champs if any(a.get("team") == tid for a in c.get("anchors", [])) or any(f.get("team_id") == tid for f in c.get("team_fit", []))]
        tcomps = [co for co in comps if any(x.get("team_id") == tid for x in co.get("teams", []))]
        seq = []
        for m in sorted(matches, key=lambda x: str(x.get("date", ""))):
            if tid not in [norm(x) for x in m.get("teams", [])]:
                continue
            r = str(m.get("result_inferred", ""))
            won = any(s in r for s in ("2:0", "2:1", "3:0", "3:1")) or tid in r and ":" in r and r.index(tid) < r.index(":")
            seq.append("胜" if (tid in r and any(s in r for s in ("2:0", "2:1", "3:0", "3:1"))) else ("负" if tid in r and any(s in r for s in ("0:2", "1:2", "0:3", "1:3")) else "?"))
        body = f'<div class="card"><h2>队伍 · {esc(name)}</h2>'
        body += ul([
            "基调：" + esc(danmu.get("tone", "未记录")),
            "信任：" + esc(t.get("trust", "未定")),
            "灰历史：" + (esc(f"{gh.get('total_signals',0)} 条 · {gh.get('status','')}") if gh else "无记录"),
            "近期走势：" + esc(" → ".join(seq[-6:])) if seq else "近期走势：样本不足",
        ])
        if tags:
            body += '<div class="block"><h3>标签</h3>' + "".join(f'<span class="chip neu">{esc(x)}</span>' for x in tags[:6]) + "</div>"
        if tplayers:
            body += '<div class="block"><h3>选手</h3><ul>' + "".join(
                f'<li><a href="intel_profile_player_{esc(p["id"])}.html">{esc(p.get("name") or p["id"])}</a>（{esc(p.get("role","待确认"))}）</li>' for p in tplayers[:8]) + "</ul></div>"
        body += "</div>"
        return body

    def champ_block() -> str:
        rows = []
        for c in champs:
            rel_teams = [a.get("team") for a in c.get("anchors", [])] + [f.get("team_id") for f in c.get("team_fit", [])]
            if not any(t in rel_teams for t in teams):
                continue
            sign = (c.get("version_sign") or {}).get("label", "待观察")
            polarity = "neg" if "负" in sign or "判负" in sign else ("pos" if "正" in sign or "绝活" in sign else "neu")
            rows.append(f'<span class="chip {polarity}">{esc(c.get("name"))}：{esc(sign)}</span>')
        return '<div class="card"><h2>相关英雄锚点（两队）</h2>' + ("".join(rows) if rows else '<div class="ok">暂无两队直接相关的英雄锚点。</div>') + "</div>"

    def comp_block() -> str:
        rel = [co for co in comps if any(t.get("team_id") in teams for t in co.get("teams", []))]
        rows = []
        for co in rel:
            rows.append(f'<span class="chip neu">{esc(co.get("name"))}</span>')
        return '<div class="card"><h2>体系偏好</h2>' + ("".join(rows) if rows else '<div class="ok">暂无登记体系。</div>') + "</div>"

    def league_block() -> str:
        lid = norm(args.league) if args.league else ""
        l = leagues.get(lid, {})
        if not l:
            return '<div class="card"><h2>联赛背景</h2><div class="ok">未登记该联赛档案。</div></div>'
        return f'<div class="card"><h2>联赛背景 · {esc(l.get("name"))}</h2>' + ul([
            "灰风险：" + esc(l.get("gray_risk", "待观察")),
            "特征：" + esc(l.get("notes", "样本不足")),
        ]) + "</div>"

    def h2h_block() -> str:
        rows = []
        for m in matches:
            ms = [norm(x) for x in m.get("teams", [])]
            if set(teams).issubset(ms) and len(ms) == 2:
                rows.append(f'<li>{esc(m.get("date"))} · {esc(" vs ".join(m.get("teams", [])))} → {esc((m.get("result_inferred") or "")[:60])}</li>')
        return '<div class="card"><h2>历史交手</h2>' + (ul(rows) if rows else '<div class="ok">暂无同对阵建档记录。</div>') + "</div>"

    def watch_block() -> str:
        lines = []
        for c in champs:
            for a in c.get("anchors", []):
                if a.get("team") in teams:
                    lines.append(f'{"⚠️" if a.get("polarity") == "负" else "✅"} {esc(c.get("name"))} × {esc(a.get("team"))}：{esc(a.get("quote",""))[:50]}（{esc(a.get("verified","待验证"))}）')
        return '<div class="card"><h2>BP 看点 / 可验证悬念</h2>' + (ul(lines) if lines else '<div class="ok">暂无锚点级看点。</div>') + "</div>"

    body = f"""<div class="stats">
<div class="stat"><div class="num">{esc(" vs ".join(teams))}</div><div class="lbl">对阵</div></div>
<div class="stat"><div class="num">{esc(args.league or "?")}</div><div class="lbl">联赛</div></div>
<div class="stat"><div class="num">{esc(date)}</div><div class="lbl">日期</div></div>
<div class="stat"><div class="num">{esc(slug or "待补")}</div><div class="lbl">Polymarket</div></div>
</div>"""
    body += team_block(teams[0]) + team_block(teams[1])
    body += champ_block() + comp_block() + league_block() + h2h_block() + watch_block()
    title = f"{' vs '.join(teams)} · 赛前速览"
    page = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><div class=\"wrap\">\n"
        f"<h1>{esc(title)}</h1>\n<p class=\"sub\">赛前速览 · 结合弹幕情报库既有数据自动生成 · 比赛开始后本页信息需以实际 BP/局势为准</p>\n{body}\n"
        '<p class="note">数据来源：docs/data/intel/（teams/players/champions/compositions/leagues/matches）· 生成：tools/build_intel_pregame.py · 灰信号纪律：观众质疑非结论。</p>\n'
        "</div></body></html>\n"
    )
    fname = OUT / f"intel_pregame_{teams[0]}-{teams[1]}_{date}.html"
    fname.write_text(page, encoding="utf-8")
    print(f"generated {fname.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
