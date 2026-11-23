#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度情报页生成器（固定提示词 + 数据 -> API -> 结论填入骨架）。

2026-08-30 用户定稿（朋友建议落地）：程序负责页面骨架/规则数据/发布；
大模型只通过接口做「变量数据 -> 分析结论」，用 prompts/intel_full.md 固定提示词。
不依赖服务器上的 Codex agent。
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from llm_client import chat, parse_json  # noqa: E402
from render_fast_intel import CSS, esc, player_rows, sample_list, team_rows  # noqa: E402


def condensed_payload(intel: dict, meta: dict) -> str:
    """把规则层数据压缩成给 LLM 的输入（只给统计与样本，不裸喂整窗弹幕）。"""
    m = intel.get("meta", {})
    teams = sorted(intel.get("teams", {}).items(), key=lambda kv: -kv[1].get("mentions", 0))[:8]
    players = sorted(intel.get("players", {}).items(), key=lambda kv: -kv[1].get("mentions", 0))[:8]
    lines = [f"比赛元数据：{json.dumps(meta, ensure_ascii=False)}"]
    lines.append(
        f"弹幕窗口：{m.get('window_utc')}；总量 {m.get('total')} 条 / 活跃 {m.get('active_users')} / "
        f"{m.get('density_per_min')} 条分"
    )
    if teams:
        lines.append("队伍情绪（提及/正负/样本）：")
        for n, d in teams:
            s = (d.get("samples") or ["（无样本）"])[0][:60]
            lines.append(f"- {n}: {d.get('mentions')}（正{d.get('pos')}/负{d.get('neg')}）| {s}")
    if players:
        lines.append("选手提及：")
        for n, d in players:
            s = (d.get("samples") or ["（无样本）"])[0][:60]
            lines.append(f"- {n}: {d.get('mentions')}（正{d.get('pos')}/负{d.get('neg')}）| {s}")
    g = intel.get("gray_signals", {})
    lines.append(f"灰信号：{g.get('count', 0)} 条（观众质疑·非结论）")
    for s in (g.get("samples") or [])[:5]:
        lines.append(f"  - {str(s)[:80]}")
    o = intel.get("odds_discussion", {})
    lines.append(f"盘口/数字讨论：{o.get('count', 0)} 条")
    for s in (o.get("samples") or [])[:5]:
        lines.append(f"  - {str(s)[:80]}")
    st = intel.get("situation", {})
    lines.append(f"局势线索：{st.get('count', 0)} 条")
    for s in (st.get("samples") or [])[:5]:
        lines.append(f"  - {str(s)[:80]}")
    b = intel.get("density_bursts", []) or []
    lines.append("密度峰值：" + "、".join(
        f"{x.get('minute_utc')} UTC {x.get('count')} 条/分" for x in b[:3]
    ) or "无")
    return "\n".join(lines)


def speedcard_html(analysis: dict, series: str, node_label: str, badge: str) -> str:
    items = analysis.get("speedcard") or []
    if not items:
        return (
            '<div class="warnbox"><b>深度分析未返回速览卡</b>，以下为规则直出摘要；'
            "可用新密钥重试深度版。</div>"
        )
    blocks = ""
    color = {"风险": "var(--bad)", "锚点": "var(--accent)", "盘口": "var(--sub)", "共识": "var(--purple)"}
    for it in items[:5]:
        t = it.get("type", "信号")
        sig = esc(it.get("signal", ""))
        val = esc(it.get("value", ""))
        sec = esc(it.get("section", ""))
        blocks += (
            f'<div class="sig"><span class="tag" style="color:{color.get(t, "var(--ink)")}">{esc(t)}</span>'
            f"<span><b>{sig}</b>——{val} <span class=meta>→ 详 {sec}</span></span></div>"
        )
    return (
        f'<div class="top"><span class="score-big">{esc(series)}</span>'
        f'<span class="badge {badge}">{esc(node_label)}</span>'
        '<span class="badge b-anchor">深度版 · LLM 分析</span></div>'
        f"<div style=\"margin-top:8px\">{blocks}</div>"
    )


def render_page(intel: dict, analysis: dict, out: Path, *, title: str, sub: str,
                series: str, node_label: str, badge: str, official_note: str = "",
                data_sources: str = "", meta: dict | None = None) -> None:
    m = intel.get("meta", {})
    win = m.get("window_utc") or ["-", "-"]
    win_cn = f"{win[0]} ~ {win[1]} (UTC)"
    gray = intel.get("gray_signals", {})
    gray_n = gray.get("count", 0)
    gray_s = sample_list(gray.get("samples") or [], 4)
    odds = intel.get("odds_discussion", {})
    odds_s = sample_list(odds.get("samples") or [], 4)
    sit = intel.get("situation", {})
    sit_s = sample_list(sit.get("samples") or [], 4)

    direction = analysis.get("direction") or {}
    d_row = lambda k, label: (  # noqa: E731
        f"<tr><td>{label}</td><td>{esc(direction.get(k) or '今日无')}</td></tr>"
    )
    consensus = analysis.get("consensus_table") or []
    cons_rows = "".join(
        f"<tr><td>{esc(r.get('theme',''))}</td><td>{esc(r.get('direction',''))}</td>"
        f"<td>{esc(r.get('count',''))}</td><td>{esc(r.get('sample',''))[:60]}</td>"
        f"<td>{esc(r.get('multi_source',''))}</td></tr>"
        for r in consensus[:8]
    ) or '<tr><td colspan="5" class="meta">无共识样本</td></tr>'
    top = analysis.get("key_info_top") or []
    top_li = "".join(
        f"<li><b>[{esc(t.get('type',''))}]</b> {esc(t.get('text',''))} "
        f"<span class=meta>· {esc(t.get('confidence',''))}</span></li>"
        for t in top[:7]
    ) or "<li class=meta>无</li>"

    now_cn = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>{esc(title)}</h1><p class="meta">{esc(sub)}</p>
<div class="card speed"><h2><span class="no">0</span>核心情报速览</h2>{speedcard_html(analysis, series, node_label, badge)}
  {f'<div class="act"><b>决策落点：</b>{esc(analysis.get("implications") or "以规则数据为准")}</div>' if analysis.get("implications") else ''}
  {f'<div class="warnbox"><b>官方说明：</b>{esc(official_note)}</div>' if official_note else ''}
</div>
<div class="card"><h2><span class="no">1</span>比赛信息与结果总览</h2>
  <p class="meta">弹幕窗口：{esc(win_cn)} · 总量 {m.get('total')} 条 / 活跃 {m.get('active_users')} / {m.get('density_per_min')} 条分</p>
  <p class="meta">状态：{esc(node_label)} · 结果口径以官方源为准（LoL=Riot / CS2=HLTV-Liquipedia）</p>
</div>
<div class="card"><h2><span class="no">2</span>灰信号汇总（风险 · 观众质疑非结论）</h2>
  <p><b>{gray_n} 条</b>（规则词表统计）</p>{gray_s}
  <div class="warnbox"><b>纪律声明：</b>灰信号只作风险标注与统计，观众质疑·非结论，不上升为假赛证据。</div>
</div>
<div class="card"><h2><span class="no">3</span>BP 锚点与选人情报</h2>
  <p>{esc(analysis.get("bp_analysis") or "无 BP 讨论样本（规则层未覆盖）")}</p>
</div>
<div class="card"><h2><span class="no">4</span>盘口与市场讨论（{odds.get('count', 0)} 条）</h2>
  {odds_s}<p class="meta">{esc(analysis.get("odds_analysis") or "无盘口样本")}</p>
</div>
<div class="card"><h2><span class="no">5</span>方向性情报板</h2>
  <table>{d_row('positive', '正锚点')}{d_row('negative', '负锚点')}{d_row('consensus', '共识')}{d_row('gray_condition', '灰信号条件预测')}</table>
</div>
<div class="card"><h2><span class="no">6</span>情报含义与决策落点</h2>
  <p>{esc(analysis.get("implications") or "待深度分析（规则层无结论）")}</p>
  <p class="meta">共识→信号链：{esc(analysis.get("consensus_chain") or "（未提供）")}</p>
</div>
<div class="card"><h2><span class="no">7</span>逐局复盘（证据层）</h2>
  <p>{esc(analysis.get("game_review") or "待观察")}</p>
  <p class="meta">局势线索（{sit.get('count', 0)} 条）：</p>{sit_s}
</div>
<div class="card"><h2><span class="no">8</span>队伍 / 人员画像（带提及量）</h2>
  {team_rows(intel)}{player_rows(intel)}
</div>
<div class="card"><h2><span class="no">9</span>联赛规律与版本（沉淀层）</h2>
  <p>{esc(analysis.get("league_patterns") or "样本不足")}</p>
</div>
<div class="card"><h2><span class="no">10</span>预测验证回填</h2>
  <p>{esc(analysis.get("prediction_verify") or "无预测样本")}</p>
</div>
<div class="card"><h2><span class="no">11</span>弹幕共识提炼 + 关键信息 TOP</h2>
  <table><tr><th>主题</th><th>方向</th><th>条数</th><th>关键样本</th><th>多源状态</th></tr>{cons_rows}</table>
  <p class="meta">关键信息 TOP：</p><ul>{top_li}</ul>
</div>
<div class="card"><h2><span class="no">12</span>数据与溯源</h2>
  <p class="meta">弹幕窗口：{esc(win_cn)}</p>
  <p class="meta">数据源：{esc(data_sources or '虎牙（多路）')}</p>
  <p class="meta">情报输出时间：{now_cn}（北京时间）· 深度版：程序骨架 + LLM 分析（固定提示词 prompts/intel_full.md）</p>
</div>
<div class="footer">弹幕情报 · 深度版 · 观众质疑非结论 · 结果以官方源为准 · Polymarket 电竞情报项目</div>
</div></body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="深度情报页（固定提示词 + 直接调 API）")
    ap.add_argument("--intel", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="弹幕情报")
    ap.add_argument("--sub", default="")
    ap.add_argument("--series", default="")
    ap.add_argument("--node-label", default="深度版")
    ap.add_argument("--status", default="b-anchor")
    ap.add_argument("--official-note", default="")
    ap.add_argument("--data-sources", default="")
    ap.add_argument("--meta", default="{}", help="比赛元数据 JSON（对局/节点/比分）")
    args = ap.parse_args()

    intel = json.loads(Path(args.intel).read_text(encoding="utf-8"))
    meta = json.loads(args.meta)
    system = (ROOT / "prompts" / "intel_full.md").read_text(encoding="utf-8")
    user = condensed_payload(intel, meta)
    raw = chat(system, user, json_mode=True)
    analysis = parse_json(raw) or {}
    if not analysis:
        print("[gen_deep_intel] LLM 未返回有效 JSON，回退规则直出", flush=True)
        from render_fast_intel import render as fast_render
        fast_render(
            intel, Path(args.out),
            title=args.title, sub=args.sub, series=args.series,
            node_label=args.node_label, status_badge="b-pend",
            official_note=args.official_note, data_sources=args.data_sources,
        )
        return 0
    render_page(
        intel, analysis, Path(args.out),
        title=args.title, sub=args.sub, series=args.series,
        node_label=args.node_label, badge=args.status,
        official_note=args.official_note, data_sources=args.data_sources, meta=meta,
    )
    print(f"[gen_deep_intel] {args.out}（analysis keys: {list(analysis.keys())}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
