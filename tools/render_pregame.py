#!/usr/bin/env python3
"""赛前页（S0）规则层渲染：1 队伍交手情况 + 2 队伍比赛近况。

赛前节点页从 Codex 4 段改为纯历史数据页（2026-11-22 用户定稿）：
  1 队伍交手情况：H2H 交战表（行=时间，列=两队，单元格=胜负）+ 表下各自交手胜率总结
  2 队伍比赛近况：两队各自近期交战表
数据来自 tools/fetch_team_history.py（Riot getSchedule / Liquipedia），
规则层注入，AI 不写、不编；样本不足如实显示，不硬撑。

用法：
  python3 tools/render_pregame.py --game lol --teams "T1,GEN" --league LCK \
      --date 2026-11-22 --slug lol-t1-gen-2026-11-22 --out reports/intel_pregame_T1-GEN.html
"""

from __future__ import annotations

import argparse
import html as _html
from pathlib import Path

from fetch_team_history import fetch_lol, fetch_cs2, norm

ROOT = Path(__file__).resolve().parents[1]

CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed;--win:#1d7a35;--loss:#d0021b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.7;padding:28px 16px 60px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:24px;font-weight:700;margin-bottom:4px}
.sub{color:var(--sub);font-size:14px;margin-bottom:22px}
.card{background:var(--card);border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h2{font-size:18px;font-weight:700;margin-bottom:12px}
h2 .no{display:inline-block;min-width:24px;height:24px;line-height:24px;text-align:center;background:var(--accent);color:#fff;border-radius:6px;font-size:13px;margin-right:8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:center;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--sub);font-weight:600;font-size:12px}
td.left,th.left{text-align:left}
.win{color:var(--win);font-weight:600}
.loss{color:var(--loss);font-weight:600}
.q{color:var(--sub)}
.summary{background:#f7f9fc;border-radius:10px;padding:12px 14px;margin-top:12px;font-size:13px;color:#3a3a3c}
.summary b{color:var(--ink)}
.gap{background:#fff7f0;border-left:4px solid #ff9500;padding:10px 14px;border-radius:8px;font-size:13px;margin-top:10px;color:#5b4636}
.ok{background:#f2f9f2;border-left:4px solid #34c759;padding:10px 14px;border-radius:8px;font-size:13px;margin-top:10px}
.note{color:var(--sub);font-size:12px;margin-top:20px;line-height:1.8}
h3{font-size:14px;font-weight:600;margin:14px 0 6px;color:var(--accent)}
@media(max-width:640px){.wrap{max-width:100%}}
"""


def esc(x) -> str:
    return _html.escape(str(x if x is not None else ""))


def _win_cell(win: bool) -> str:
    return '<span class="win">胜</span>' if win else '<span class="loss">负</span>'


def _h2h_side(rec: dict, teams: list[str]) -> tuple[bool, bool]:
    """teams[0]/teams[1] 在这条 H2H 里各自是否获胜（按归一队名匹配 winner）。"""
    ta, tb = norm(teams[0]), norm(teams[1])
    w = norm(rec.get("winner") or "")
    return (w == ta, w == tb)


def _h2h_block(h2h: list[dict], teams: list[str], game: str) -> str:
    if not h2h:
        return '<div class="ok">暂无两队同对阵记录（历史数据源未覆盖）。</div>'
    head = "".join(f"<th>{esc(t)}</th>" for t in teams)
    rows = []
    aw = bw = 0
    for r in h2h:
        a, b = _h2h_side(r, teams)
        aw += 1 if a else 0
        bw += 1 if b else 0
        extra = ""
        if game == "lol" and r.get("score"):
            extra = f' <span class="q">({esc(r["score"])})</span>'
        elif game == "cs2" and r.get("tournament"):
            extra = f' <span class="q">({esc(r["tournament"])})</span>'
        rows.append(
            f'<tr><td class="left">{esc(r.get("date", ""))}</td>'
            f"<td>{_win_cell(a)}{extra}</td>"
            f"<td>{_win_cell(b)}{extra}</td></tr>"
        )
    n = len(h2h)
    pa = round(aw / n * 100) if n else 0
    pb = round(bw / n * 100) if n else 0
    summary = (
        f'<div class="summary">交手 <b>{n}</b> 场：'
        f'<b>{esc(teams[0])}</b> {aw} 胜 {bw} 负（胜率 {pa}%）· '
        f'<b>{esc(teams[1])}</b> {bw} 胜 {aw} 负（胜率 {pb}%）</div>'
    )
    return (
        f'<table><thead><tr><th class="left">时间</th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>{summary}"
    )


def _recent_table(team: str, rows: list[dict], game: str) -> str:
    if not rows:
        return f'<h3>{esc(team)}</h3><div class="gap">样本不足（历史数据源未覆盖该队近期场次）。</div>'
    if game == "lol":
        trs = []
        w = 0
        for r in rows[:5]:
            win = r.get("result") == "win"
            w += 1 if win else 0
            trs.append(
                f'<tr><td class="left">{esc(r.get("date", ""))}</td>'
                f'<td>{esc(r.get("opponent", ""))}</td>'
                f"<td>{_win_cell(win)}</td></tr>"
            )
        shown = len(rows[:5])
        rate = round(w / shown * 100) if shown else 0
        return (
            f'<h3>{esc(team)}</h3>'
            f'<table><thead><tr><th class="left">时间</th><th>对手</th><th>胜负</th></tr></thead>'
            f"<tbody>{''.join(trs)}</tbody></table>"
            f'<div class="summary">近 {shown} 场：{w} 胜 {shown - w} 负（胜率 {rate}%）</div>'
        )
    # CS2：锦标赛级（名次 + 决赛比分 + 对手）
    trs = []
    for r in rows[:5]:
        place = esc(r.get("place", ""))
        res = esc(r.get("result", ""))
        trs.append(
            f'<tr><td class="left">{esc(r.get("date", ""))}</td>'
            f'<td>{esc(r.get("tournament", ""))}</td>'
            f'<td>{esc(r.get("opponent", ""))}</td>'
            f'<td>{place} <span class="q">({res})</span></td></tr>'
        )
    return (
        f'<h3>{esc(team)}</h3>'
        f'<table><thead><tr><th class="left">时间</th><th>赛事</th><th>对手</th><th>名次（决赛比分）</th></tr></thead>'
        f"<tbody>{''.join(trs)}</tbody></table>"
        f'<div class="q" style="margin-top:8px">口径：锦标赛级（名次+决赛比分），非逐场胜负。</div>'
    )


def render_pregame_html(teams: list[str], date: str, league: str, slug: str,
                        history: dict) -> str:
    game = history.get("game", "")
    h2h = history.get("h2h", [])
    recent = history.get("recent", {teams[0]: [], teams[1]: []})
    gaps = history.get("gaps", [])

    body = (
        '<div class="card"><h2><span class="no">1</span>队伍交手情况</h2>'
        + _h2h_block(h2h, teams, game)
        + "</div>"
    )
    body += (
        '<div class="card"><h2><span class="no">2</span>队伍比赛近况</h2>'
        + _recent_table(teams[0], recent.get(teams[0], []), game)
        + _recent_table(teams[1], recent.get(teams[1], []), game)
        + "</div>"
    )
    gap_html = "".join(f'<div class="gap">{esc(g)}</div>' for g in gaps) if gaps else ""

    title = f"{' vs '.join(teams)} · 赛前速览"
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><div class=\"wrap\">\n"
        f"<h1>{esc(title)}</h1>\n"
        f'<p class="sub">赛前速览 · 联赛 {esc(league)} · {esc(date)} · slug {esc(slug)}</p>\n'
        f"{body}\n{gap_html}\n"
        '<p class="note">数据来源：Riot getSchedule（LoL）/ Liquipedia（CS2）+ 本地台账，规则层拉取注入，'
        "AI 不写。样本不足时如实显示，不硬撑。</p>\n"
        "</div></body></html>\n"
    )


def build_pregame(game: str, teams: list[str], date: str, league: str, slug: str,
                  out: Path, before: str | None = None) -> dict:
    history = fetch_lol(teams, league, before) if game == "lol" else fetch_cs2(teams, before)
    # 渲染用 fetch 层归一化后的 abbr（与 recent 字典 key 一致，且符合队伍命名标准：
    # 页面统一 abbr 展示）。pipeline 传入的 teams 可能是全名（如 "Bilibili Gaming"）。
    teams_canon = history.get("teams", teams) or teams
    page = render_pregame_html(teams_canon, date, league, slug, history)
    out.write_text(page, encoding="utf-8")
    return history


def main() -> int:
    ap = argparse.ArgumentParser(description="赛前页规则层渲染（历史数据两栏）")
    ap.add_argument("--game", choices=["lol", "cs2"], required=True)
    ap.add_argument("--teams", required=True, help="A,B")
    ap.add_argument("--league", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--before", default="", help="本场开赛时间/日期，排除自身及之后")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    if len(teams) != 2:
        print("需要两个队伍 A,B")
        return 1
    out = Path(args.out)
    build_pregame(args.game, teams, args.date, args.league, args.slug, out, args.before or None)
    print(f"generated {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
