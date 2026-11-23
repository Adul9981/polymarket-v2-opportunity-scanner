#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则直出情报页（极简极省 · 零 LLM Token）。

2026-08-30 用户定稿：网站情报输出极简化——不再调 Codex/DeepSeek，
由规则层情报 JSON（danmu_intel.py 产出）固定模板直出 HTML。
结构：速览卡（比分/进度 + TOP 信号 + 决策落点）→ 队伍/选手情绪（带量）→
灰信号（观众质疑·非结论）→ 盘口/局势线索 → 密度峰值 → 数据与溯源。
页面显著标注「速览版·规则直出」，后续如需 Codex 完整版可同 URL 升级覆盖。
"""

import argparse
import html
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def esc(s) -> str:
    return html.escape(str(s), quote=True)


CSS = """
  :root { --bg:#f5f5f7; --card:#fff; --ink:#1d1d1f; --sub:#6e6e73; --accent:#0b6bcb;
          --line:#e3e3e8; --good:#1a7f37; --bad:#c0392b; --warn:#b45309; --purple:#6d4fc4; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,
         "SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.62;
         padding:22px 12px 56px; }
  .wrap { max-width:920px; margin:0 auto; }
  .card { background:var(--card); border-radius:16px; padding:20px 22px; margin:14px 0;
          box-shadow:0 1px 4px rgba(0,0,0,.05); }
  h1 { font-size:22px; font-weight:700; }
  h2 { font-size:16px; font-weight:650; margin:10px 0 8px; display:flex; align-items:center; gap:7px; }
  h2 .no { flex:0 0 22px; height:22px; background:var(--accent); color:#fff; border-radius:7px;
           font-size:12px; display:inline-flex; align-items:center; justify-content:center; }
  .meta { color:var(--sub); font-size:12px; margin-top:6px; }
  .badge { display:inline-block; border-radius:999px; padding:2px 9px; font-size:11px;
           margin:2px 4px 2px 0; }
  .b-ok { background:#e8f6ec; color:var(--good); }
  .b-risk { background:#fdeaea; color:var(--bad); }
  .b-anchor { background:#eaf2fb; color:var(--accent); }
  .b-pend { background:#fdf0e6; color:var(--warn); }
  .speed { background:linear-gradient(180deg,#fbfcff,#f4f7fd); border:1px solid #dbe5f5; }
  .speed .top { display:flex; flex-wrap:wrap; gap:8px; align-items:center;
                border-bottom:1px solid var(--line); padding-bottom:10px; }
  .score-big { font-size:20px; font-weight:750; color:var(--accent); }
  .sig { display:flex; gap:10px; padding:9px 0; border-bottom:1px dashed var(--line); font-size:13px; }
  .sig:last-child { border-bottom:none; }
  .sig .tag { flex:0 0 52px; font-size:11px; font-weight:650; padding-top:2px; }
  .act { background:#f0faf3; border:1px solid #cfe8d8; border-radius:12px; padding:11px 14px;
         margin-top:10px; font-size:13.5px; }
  .warnbox { background:#fdf6ec; border-left:3px solid var(--warn); padding:8px 12px;
             border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
  th { text-align:left; color:var(--sub); font-weight:600; font-size:11px; padding:6px 7px;
       border-bottom:1px solid var(--line); }
  td { padding:6px 7px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  ul { padding-left:20px; margin:6px 0; } li { margin:4px 0; font-size:13.5px; }
  .footer { color:var(--sub); font-size:11.5px; text-align:center; margin-top:18px; }
"""


def sample_list(samples, n: int = 6) -> str:
    if not samples:
        return '<span class="meta">无样本</span>'
    lis = "".join(f"<li>{esc(s)[:90]}</li>" for s in samples[:n])
    return f"<ul>{lis}</ul>"


def team_rows(intel: dict) -> str:
    teams = intel.get("teams", {})
    if not teams:
        return '<p class="meta">样本不足</p>'
    rows = ""
    for name, d in sorted(teams.items(), key=lambda kv: -kv[1].get("mentions", 0))[:10]:
        s = d.get("samples") or []
        ex = "<br>".join(esc(x)[:70] for x in s[:2]) if s else "—"
        rows += (
            f"<tr><td><b>{esc(name)}</b></td><td>{d.get('mentions', 0)}</td>"
            f"<td>{d.get('pos', 0)} / {d.get('neg', 0)}</td><td>{ex}</td></tr>"
        )
    return (
        "<table><tr><th>队伍</th><th>提及</th><th>正/负</th><th>代表样本</th></tr>"
        f"{rows}</table>"
    )


def player_rows(intel: dict) -> str:
    players = intel.get("players", {})
    if not players:
        return '<p class="meta">无选手提及样本</p>'
    rows = ""
    for name, d in sorted(players.items(), key=lambda kv: -kv[1].get("mentions", 0))[:10]:
        s = d.get("samples") or []
        ex = "<br>".join(esc(x)[:70] for x in s[:2]) if s else "—"
        rows += (
            f"<tr><td><b>{esc(name)}</b></td><td>{d.get('mentions', 0)}</td>"
            f"<td>{d.get('pos', 0)} / {d.get('neg', 0)}</td><td>{ex}</td></tr>"
        )
    return (
        "<table><tr><th>选手</th><th>提及</th><th>正/负</th><th>代表样本</th></tr>"
        f"{rows}</table>"
    )


def render(intel: dict, out: Path, *, title: str, sub: str, series: str,
           node_label: str, status_badge: str, official_note: str = "",
           data_sources: str = "") -> None:
    m = intel.get("meta", {})
    total = m.get("total", 0)
    act = m.get("active_users", 0)
    dpm = m.get("density_per_min", 0)
    win = m.get("window_utc") or ["-", "-"]
    win_cn = f"{win[0]} ~ {win[1]} (UTC)"

    gray = intel.get("gray_signals", {})
    gray_n = gray.get("count", 0)
    gray_s = sample_list(gray.get("samples") or [], 3)
    odds = intel.get("odds_discussion", {})
    odds_n = odds.get("count", 0)
    odds_s = sample_list(odds.get("samples") or [], 3)
    sit = intel.get("situation", {})
    sit_n = sit.get("count", 0)
    sit_s = sample_list(sit.get("samples") or [], 3)
    bursts = intel.get("density_bursts", []) or []
    peak = "、".join(f'{esc(b.get("minute_utc"))} UTC {b.get("count")} 条/分' for b in bursts[:5]) or "无峰值"
    peak_rows = "".join(
        f"<tr><td>{esc(b.get('minute_utc'))} UTC</td><td>{b.get('count')} 条/分</td>"
        f"<td>{esc((b.get('samples') or ['（无）'])[0][:60])}</td></tr>"
        for b in bursts[:6]
    ) or '<tr><td colspan="3" class="meta">无密度峰值</td></tr>'

    top_teams = sorted(intel.get("teams", {}).items(),
                       key=lambda kv: -kv[1].get("mentions", 0))[:2]
    top_sig = "、".join(f"{esc(n)}（{d.get('mentions',0)} 条）" for n, d in top_teams) or "样本不足"
    top_players = sorted(intel.get("players", {}).items(),
                         key=lambda kv: -kv[1].get("mentions", 0))[:2]
    top_psig = "、".join(f"{esc(n)}（{d.get('mentions',0)} 条）" for n, d in top_players) or "无"

    speed_sigs = ""
    speed_sigs += (
        f'<div class="sig"><span class="tag" style="color:var(--accent)">锚点</span>'
        f"<span><b>队伍情绪（带量）</b>：{top_sig}；选手焦点：{top_psig}——"
        f"<b>说明</b> 讨论热度集中在上述对象，后续盯其表现与盘口对照 <span class=meta>→ 详 §1/§2</span></span></div>"
    )
    speed_sigs += (
        f'<div class="sig"><span class="tag" style="color:var(--bad)">风险</span>'
        f"<span><b>灰信号 {gray_n} 条</b>（观众质疑·非结论，样本见 §3）——<b>需注意</b> 只作风险标注，"
        f"不上升结论 <span class=meta>→ 详 §3</span></span></div>"
    )
    speed_sigs += (
        f'<div class="sig"><span class="tag" style="color:var(--sub)">盘口</span>'
        f"<span><b>盘口/数字讨论 {odds_n} 条</b>、局势线索 {sit_n} 条——<b>表明</b> "
        f"本窗口{'有' if odds_n or sit_n else '无'}可对照信号，样本见 §4/§5 <span class=meta>→ 详 §4/§5</span></span></div>"
    )
    speed_sigs += (
        f'<div class="sig"><span class="tag" style="color:var(--purple)">共识</span>'
        f"<span><b>弹幕规模 {total} 条 / {act} 活跃 / {dpm} 条分</b>，峰值 {peak}——"
        f"<b>意味着</b> 数据密度充足，结论可溯源（规则直出）<span class=meta>→ 详 §6</span></span></div>"
    )

    now_cn = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>{esc(title)}</h1><p class="meta">{esc(sub)}</p>
<div class="card speed"><h2><span class="no">0</span>核心情报速览</h2>
  <div class="top">
    <span class="score-big">{esc(series)}</span>
    <span class="badge {status_badge}">{esc(node_label)}</span>
    <span class="badge b-pend">速览版·规则直出（零 LLM）</span>
  </div>
  <div style="margin-top:8px">{speed_sigs}</div>
  <div class="act"><b>决策落点：</b>本节点边际信息 = 讨论热度对象（队伍/选手）与灰信号风险标注；
  具体方向需结合盘口/价格与后续节点验证，灰信号不作交易结论。</div>
  {f'<div class="warnbox"><b>官方说明：</b>{esc(official_note)}</div>' if official_note else ''}
</div>
<div class="card"><h2><span class="no">1</span>队伍情绪（带量）</h2>{team_rows(intel)}</div>
<div class="card"><h2><span class="no">2</span>选手提及（带量）</h2>{player_rows(intel)}</div>
<div class="card"><h2><span class="no">3</span>灰信号汇总（风险 · 观众质疑非结论）</h2>
  <p><b>{gray_n} 条</b>（规则词表统计）</p>{gray_s}
  <div class="warnbox"><b>纪律声明：</b>以上均为观众质疑/玩梗，非假赛证据；灰信号只作风险标注与统计，不上升结论。</div>
</div>
<div class="card"><h2><span class="no">4</span>盘口/数字讨论（{odds_n} 条）</h2>{odds_s}</div>
<div class="card"><h2><span class="no">5</span>局势线索（{sit_n} 条）</h2>{sit_s}</div>
<div class="card"><h2><span class="no">6</span>弹幕密度</h2>
  <p>总 {total} 条 / 活跃 {act} / {dpm} 条分；峰值：{peak}</p>
  <table><tr><th>时刻</th><th>条/分</th><th>代表样本</th></tr>{peak_rows}</table>
</div>
<div class="card"><h2><span class="no">7</span>数据与溯源</h2>
  <p class="meta">弹幕窗口：{esc(win_cn)}</p>
  <p class="meta">数据源：{esc(data_sources or '虎牙（多路）')}</p>
  <p class="meta">情报输出时间：{now_cn}（北京时间）· 本页为规则直出速览版，不含 LLM 生成</p>
  <p class="meta">结果口径：以官方源为准（LoL=Riot / CS2=HLTV-Liquipedia）；弹幕仅过程佐证</p>
</div>
<div class="footer">弹幕情报 · 速览版·规则直出 · 观众质疑非结论 · Polymarket 电竞情报项目</div>
</div></body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="规则直出情报页（零 LLM）")
    ap.add_argument("--intel", required=True, help="规则层情报 JSON")
    ap.add_argument("--out", required=True, help="输出 HTML 路径")
    ap.add_argument("--title", default="弹幕情报")
    ap.add_argument("--sub", default="")
    ap.add_argument("--series", default="进度以弹幕口径为准")
    ap.add_argument("--node-label", default="速览版")
    ap.add_argument("--status", default="b-pend", help="badge 类名")
    ap.add_argument("--official-note", default="")
    ap.add_argument("--data-sources", default="")
    args = ap.parse_args()
    intel = json.loads(Path(args.intel).read_text(encoding="utf-8"))
    render(
        intel, Path(args.out),
        title=args.title, sub=args.sub, series=args.series,
        node_label=args.node_label, status_badge=args.status,
        official_note=args.official_note, data_sources=args.data_sources,
    )
    print(f"[render_fast] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
