#!/usr/bin/env python3
"""Template-based game-node intel page renderer.

AI fills structured content fields (JSON) only; this module assembles the
SAP/Apple node page (速览卡 + 编号卡片 0.5/1/1.5/2–11) from those fields +
rule-layer stats. This is the "治本" latency fix: the LLM no longer writes
HTML/CSS, so output tokens drop and generation speeds up (2026-10-18).
【比赛局势】(1.5) 为纯规则层块：胜率来自 stats.win_signal、评分来自虎扑 ratings。

Usage (dry-run / offline test):
  python3 tools/render_node_page.py \
      --data path/to/ai_fields.json --stats path/to/rule_intel.json \
      --teams "A,B" --date 2026-10-18 --game 1 --phase bp \
      --slug lol-a-b-2026-10-18 --max-games 5 --out path/to/out.html
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from intel_html import card, esc, page, sig, src_box, speed_block

# 速览卡条目类型 -> 标签色（SAP/Apple 语义色）
_TAG_COLOR = {
    "风险": "var(--bad)",
    "锚点": "var(--accent)",
    "盘口": "var(--good)",
    "共识": "var(--purple)",
}
_CONFIDENCE = {"多源确认", "单源待验证", "弹幕口径·待官方"}
_BLUE = "#0071e3"   # 队伍1（胜率/评分 统一蓝色）
_RED = "#ff3b30"    # 队伍2（统一红色）
_PHASE_LABEL = {
    "bp": "BP 后/开局（S0 · EARLY-GAME）",
    "mid": "局中（S1-S3 · MID-GAME）",
    "end": "局末/局间（S4 · GAME-REVIEW）",
}


def _conf(c) -> str:
    c = str(c or "").strip()
    return c if c in _CONFIDENCE else "单源待验证"


def _li(text: str) -> str:
    return f"<li>{esc(text)}</li>"


def _table(headers: list[str], rows: list[list]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _details(summary: str, body: str) -> str:
    if not body:
        return ""
    return f"<details><summary>{esc(summary)}</summary>{body}</details>"


def _league_of(slug_id: str) -> str:
    first = (slug_id or "").split("-")[0].lower()
    if first.startswith("cs"):
        return "CS2"
    if first.startswith("dota") or first.startswith("ti"):
        return "Dota2"
    return "LoL"


# --------------------------------------------------------------------------- sections

def _speed(data: dict) -> str:
    """0 核心情报速览：进度一行 + 关键信息（信号→价值→详 §N）+ 决策落点。"""
    progress = str(data.get("progress_line") or "进行中 · 结果待官方回填").strip()
    signals = data.get("top_signals") or []
    sigs_html = ""
    if isinstance(signals, list):
        for it in signals:
            if not isinstance(it, dict):
                continue
            typ = str(it.get("type") or "锚点").strip()
            signal = str(it.get("signal") or "").strip()
            value = str(it.get("value") or "").strip()
            # 去重：AI 偶发把置信写进 value，先剥掉尾部置信词再统一由 conf 字段补
            value = re.sub(
                r"[（(]\s*(多源确认|单源待验证|弹幕口径·待官方)\s*[)）]\s*$",
                "", value,
            ).strip()
            conf = _conf(it.get("confidence"))
            ref = re.sub(r"^详\s*§?", "", str(it.get("source_ref") or "")).strip()
            parts = [signal] if signal else []
            if value:
                parts.append(f"{value}（{conf}）")
            else:
                parts.append(conf)
            item = " → ".join(parts)
            if ref:
                item += f" → 详 §{ref}"
            if item:
                sigs_html += sig(typ, _TAG_COLOR.get(typ, "var(--accent)"), item)
    if not sigs_html:
        # 诚实空态；带「单源待验证」保证 speedcard_consistency 不判 empty/no_value
        sigs_html = sig(
            "共识", "var(--purple)",
            "本节点样本不足 → 意味着暂无可确认信号、观望为主 → 单源待验证",
        )
    decision = str(data.get("decision") or "待更多信号").strip()
    return speed_block(progress, [], sigs_html, decision)


def _key_vars_and_lineup(data: dict) -> str:
    """1 关键变量卡 + 阵容裁决卡。"""
    blocks = []
    kvs = data.get("key_variables") or []
    if kvs:
        rows = [
            [kv.get("name", ""), kv.get("role", ""), str(kv.get("mentions", "")), kv.get("direction", "")]
            for kv in kvs
            if isinstance(kv, dict)
        ]
        blocks.append(
            '<h3 style="font-size:14px;margin:2px 0 6px">关键变量卡</h3>'
            + _table(["变量", "作用/机制", "提及量", "方向"], rows)
        )
    la = data.get("lineup_adjudication") or []
    if la:
        rows = [
            [str(l.get("game", "")), l.get("lineup", ""), l.get("verdict", ""), l.get("result", "")]
            for l in la
            if isinstance(l, dict)
        ]
        blocks.append(
            '<h3 style="font-size:14px;margin:10px 0 6px">阵容裁决卡</h3>'
            + _table(["局", "阵容（弹幕口径·待官方）", "裁决", "结果"], rows)
        )
    return "".join(blocks) if blocks else '<p class="note">本节点暂无关键变量/阵容裁决信息。</p>'


def _status(data: dict, stats: dict, teams: list[str], gi: int, gphase: str,
            slug_id: str, max_games: int, end_basis: str) -> str:
    """2 结果总览/状态核验：元数据 + 关键数据 + 跨源一致性。"""
    meta = stats.get("meta") or {}
    win = " / ".join(meta.get("window_utc") or ["-"]) if isinstance(meta.get("window_utc"), list) else str(meta.get("window_utc") or "-")
    lines = [
        f"对阵：{teams[0]} vs {teams[1]}（BO{max_games}，本场共 {max_games} 局）",
        f"节点：G{gi} {_PHASE_LABEL.get(gphase, gphase)}",
        f"联赛：{_league_of(slug_id)} · Polymarket slug：{esc(slug_id)}",
        f"数据窗口：{esc(win)}",
        f"弹幕关键数据：累计 {meta.get('total', 0)} 条 / {meta.get('active_users', 0)} 人 / "
        f"{meta.get('density_per_min', 0)} 条·分 / 样本状态 {meta.get('sample_status', '-')}",
        f"状态：{'已结束·待官方回填' if gphase == 'end' else '进行中·非终局，结果待定'}"
        + (f"（结束依据：{end_basis}）" if gphase == "end" and end_basis else ""),
    ]
    src = data.get("sources") or {}
    consistency = str(src.get("cross_source") or "多源交叉待验证（见 §13 数据与溯源）").strip()
    lines.append(f"跨源一致性：{consistency}")
    return "<ul>" + "".join(_li(x) for x in lines) + "</ul>"


def _gray(data: dict) -> str:
    """4 灰信号汇总（风险红线，观众质疑·非结论）。"""
    gray = data.get("gray_signals") or []
    if not gray:
        return '<p class="note">今日无灰信号。</p>'
    items = []
    for g in gray:
        if not isinstance(g, dict):
            continue
        text = str(g.get("text") or "").strip()
        target = str(g.get("target") or "").strip()
        warn = str(g.get("warning") or "中").strip()
        label = f"指向：{target} · 风险 {warn}" if target else f"风险 {warn}"
        items.append(f'<div class="warnbox"><b>观众质疑·非结论</b>（{esc(label)}）<br>{esc(text)}</div>')
    if not items:
        return '<p class="note">今日无灰信号。</p>'
    return "".join(items)


def _bp(data: dict) -> str:
    """5 BP 锚点与选人情报（弹幕讨论·非确认）。"""
    anchors = data.get("bp_anchors") or []
    if not anchors:
        return '<p class="note">今日无锚点 / 无战绩情报提及。</p>'
    items = []
    for a in anchors:
        if not isinstance(a, dict):
            continue
        typ = str(a.get("type") or "").strip()
        lineup = str(a.get("lineup") or "").strip()
        content = str(a.get("content") or "").strip()
        bp_note = str(a.get("bp_note") or "无战绩情报提及").strip()
        head = f"<b>{'正锚' if typ == '正' else '负锚' if typ == '负' else '锚点'}</b>"
        if lineup:
            head += f" · 阵容（弹幕口径·待官方）：{esc(lineup)}"
        items.append(
            f'<div style="padding:6px 0;border-bottom:1px dashed var(--line)">{head}'
            f"<br>{esc(content)}<div class=\"note\">BP 后战绩情报：{esc(bp_note)}</div></div>"
        )
    return "".join(items)


def _market(data: dict) -> str:
    """6 盘口与市场讨论。"""
    txt = str(data.get("market_discussion") or "").strip()
    return f"<p>{esc(txt)}</p>" if txt else '<p class="note">今日无盘口信号。</p>'


def _direction(data: dict) -> str:
    """7 方向性情报板：正锚 × 负锚 × 群体共识 × 灰信号条件预测。"""
    d = data.get("direction") or {}
    pos = d.get("positive") or []
    neg = d.get("negative") or []
    cons = str(d.get("consensus") or "").strip()
    gc = d.get("gray_conditional") or []
    parts = []
    parts.append('<div class="badge b-anchor">正锚</div>' + ("<ul>" + "".join(_li(str(x)) for x in pos) + "</ul>" if pos else '<p class="note">今日无锚点</p>'))
    parts.append('<div class="badge b-risk">负锚</div>' + ("<ul>" + "".join(_li(str(x)) for x in neg) + "</ul>" if neg else '<p class="note">今日无锚点</p>'))
    parts.append('<div class="badge b-con">群体共识</div>' + (f"<p>{esc(cons)}</p>" if cons else '<p class="note">共识不足</p>'))
    parts.append('<div class="badge b-pend">灰信号条件预测</div>' + ("<ul>" + "".join(_li(str(x)) for x in gc) + "</ul>" if gc else '<p class="note">今日无灰信号</p>'))
    return "".join(f'<div style="margin:8px 0">{p}</div>' for p in parts)


def _decision(data: dict) -> str:
    """8 情报含义与决策落点（LONG/SHORT + 观察点）。"""
    dl = data.get("decision_landing") or {}
    long_t = str(dl.get("long") or "").strip()
    short_t = str(dl.get("short") or "").strip()
    watch = dl.get("watch") or []
    out = []
    out.append(f'<div class="act"><b>LONG：</b>{esc(long_t) if long_t else "—"}</div>')
    out.append(f'<div class="act"><b>SHORT：</b>{esc(short_t) if short_t else "—"}</div>')
    out.append("<b>本场观察点：</b>" + ("<ul>" + "".join(_li(str(w)) for w in watch) + "</ul>" if watch else "—"))
    return "".join(out)


def _replay(data: dict, stats: dict) -> str:
    """9 本局复盘：复盘叙事 + 密度峰值时间线（证据层）。"""
    txt = str(data.get("replay") or "").strip()
    parts = []
    if txt:
        parts.append(f"<p>{esc(txt)}</p>")
    bursts = stats.get("density_bursts") or []
    if bursts:
        rows = []
        for b in bursts[:8]:
            if not isinstance(b, dict):
                continue
            sample = (b.get("samples") or [""])[0] if isinstance(b.get("samples"), list) else ""
            rows.append([b.get("minute_utc", ""), str(b.get("count", "")), b.get("tone", ""), str(sample)[:40]])
        parts.append('<h3 style="font-size:14px;margin:8px 0 6px">弹幕密度峰值时间线</h3>' + _table(["时刻", "条数", "情绪", "样本"], rows))
    return "".join(parts) if parts else '<p class="note">本局暂无复盘样本。</p>'


def _profiles(data: dict, stats: dict) -> str:
    """10 队伍/人员画像（带提及量，硬信息）。"""
    profs = data.get("profiles") or []
    rows = []
    if profs:
        for p in profs:
            if not isinstance(p, dict):
                continue
            rows.append([p.get("name", ""), str(p.get("mentions", "")), str(p.get("pos", "")), str(p.get("neg", "")), p.get("eval", "")])
    if not rows:
        # 回退到规则层统计（提及量/正负向），保证硬信息不丢
        for name, v in (stats.get("teams") or {}).items():
            rows.append([name, str(v.get("mentions", "")), str(v.get("pos", "")), str(v.get("neg", "")), "（规则层统计）"])
        for name, v in (stats.get("players") or {}).items():
            rows.append([name, str(v.get("mentions", "")), str(v.get("pos", "")), str(v.get("neg", "")), "（规则层统计）"])
    if not rows:
        return '<p class="note">本节点暂无画像样本。</p>'
    return _table(["选手/队伍", "提及量", "正向", "负向", "评价"], rows)


def _patterns(data: dict) -> str:
    """11 联赛规律与版本（沉淀层）。"""
    txt = str(data.get("patterns") or "").strip()
    return f"<p>{esc(txt)}</p>" if txt and txt != "无" else '<p class="note">暂无跨场规律沉淀。</p>'


def _prediction(data: dict) -> str:
    """12 预测验证回填明细（闭环）。"""
    preds = data.get("prediction_verification") or []
    if not preds:
        return '<p class="note">待回填（比赛结束后验证命中）。</p>'
    rows = [
        [str(p.get("time", "")), str(p.get("prediction", "")), str(p.get("result", "待回填"))]
        for p in preds
        if isinstance(p, dict)
    ]
    return _table(["时刻", "预测", "验证结果"], rows) if rows else '<p class="note">待回填。</p>'


def _sources(data: dict, stats: dict) -> str:
    """13 数据与溯源：三栏 + 来源标签。"""
    src = data.get("sources") or {}
    actual = str(src.get("actual") or "本场弹幕切片")
    expect = str(src.get("expected") or "已登记直播源")
    gap = str(src.get("gap") or "无（见采集清单）")
    out = [src_box(actual, expect, gap)]
    tags = src.get("source_tags") or []
    if tags:
        out.append('<div class="note">来源标签：' + esc(" / ".join(str(t) for t in tags)) + "</div>")
    return "".join(out)


# --------------------------------------------------------------------------- 比赛局势

def _match_index(hupu_name: str, teams: list[str]) -> int | None:
    """虎扑队名 -> teams 下标（0/1），模糊包含匹配；无法对齐返回 None。"""
    n = str(hupu_name or "").strip().lower()
    if not n:
        return None
    for i, t in enumerate(teams[:2]):
        tn = str(t or "").strip().lower()
        if tn and (n == tn or n in tn or tn in n):
            return i
    return None


def _player_rows(players: list[dict], color: str) -> str:
    """一列选手评分行（名字 / 分数 / 评分人数），按分数降序。"""
    rows = []
    for p in sorted(players, key=lambda x: _score_val(x), reverse=True):
        name = str((p or {}).get("name") or "").strip()
        if not name:
            continue
        score = _score_str(p)
        cnt = (p or {}).get("count") or 0
        rows.append(
            '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
            'border-bottom:1px dashed var(--line);font-size:12.5px">'
            f'<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap">{esc(name)}</span>'
            f'<span style="font-weight:750;color:{color};min-width:34px;text-align:right">{score}</span>'
            f'<span style="color:var(--sub);font-size:11px;min-width:44px;text-align:right">{cnt}人评</span>'
            '</div>'
        )
    return "".join(rows) if rows else '<div class="note">暂无评分</div>'


def _score_val(p: dict) -> float:
    try:
        return float((p or {}).get("score"))
    except (TypeError, ValueError):
        return -1.0


def _score_str(p: dict) -> str:
    try:
        return f"{float((p or {}).get('score')):.1f}"
    except (TypeError, ValueError):
        return "—"


def _rating_cols(ratings: dict | None, teams: list[str]) -> str:
    """两队队员评分双列（蓝=队1/红=队2，与胜率条同色对齐）。"""
    if not isinstance(ratings, dict):
        return ""
    players = [p for p in (ratings.get("players") or []) if isinstance(p, dict)]
    if not players:
        return ""
    home = ratings.get("home") or {}
    away = ratings.get("away") or {}
    home_tid = str(home.get("team_id") or "")
    away_tid = str(away.get("team_id") or "")
    home_name = str(home.get("name") or "").strip()
    away_name = str(away.get("name") or "").strip()

    home_players, away_players = [], []
    for p in players:
        tid = str(p.get("team_id") or "")
        if away_tid and tid == away_tid:
            away_players.append(p)
        else:
            home_players.append(p)

    # 蓝列恒 = teams[0]，红列恒 = teams[1]；按虎扑队名对齐到 teams，对齐失败回退主客序
    home_idx = _match_index(home_name, teams)
    away_idx = _match_index(away_name, teams)
    if home_idx == 1 and away_idx == 0:
        left, right = away_players, home_players
        left_label, right_label = away_name, home_name
    else:
        left, right = home_players, away_players
        left_label, right_label = home_name, away_name
    left_color, right_color = _BLUE, _RED
    left_label = left_label or (teams[0] if teams else "队伍1")
    right_label = right_label or (teams[1] if len(teams) > 1 else "队伍2")

    col = (
        '<div style="flex:1;min-width:0">'
        '<div style="font-weight:700;font-size:13px;margin-bottom:4px;color:{c}">{l}</div>'
        '{rows}'
        '</div>'
    )
    return (
        '<div style="display:flex;gap:20px;flex-wrap:wrap">{}{}</div>'.format(
            col.format(c=left_color, l=esc(left_label), rows=_player_rows(left, left_color)),
            col.format(c=right_color, l=esc(right_label), rows=_player_rows(right, right_color)),
        )
    )


_WIN_BEGIN = "<!-- SITUATION:WIN:BEGIN -->"
_WIN_END = "<!-- SITUATION:WIN:END -->"
_RAT_BEGIN = "<!-- SITUATION:RATINGS:BEGIN -->"
_RAT_END = "<!-- SITUATION:RATINGS:END -->"


def situation_win_block(ws: dict | None, teams: list[str]) -> str:
    """比赛局势·胜率子块（本小局弹幕口径，局内实时、局末冻结；含 WIN 标记供就地替换）。"""
    t0 = teams[0] if teams else (ws or {}).get("team_a", "队伍1")
    t1 = teams[1] if len(teams) > 1 else (ws or {}).get("team_b", "队伍2")
    parts = []
    if ws and ws.get("sample_status") == "ready":
        for name, pct, color in ((t0, int(ws.get("pct_a") or 0), _BLUE), (t1, int(ws.get("pct_b") or 0), _RED)):
            parts.append(
                '<div style="display:flex;align-items:center;gap:10px;margin:7px 0">'
                f'<span style="flex:0 0 96px;font-weight:650;color:{color};font-size:13px">{esc(name)}</span>'
                '<div style="flex:1;background:#eef0f3;border-radius:8px;height:18px;overflow:hidden">'
                f'<div style="height:100%;width:{pct}%;background:{color};border-radius:8px"></div></div>'
                f'<span style="flex:0 0 56px;text-align:right;font-weight:750;color:{color};font-size:14px">{pct}%</span>'
                '</div>'
            )
        win = max(int((ws.get("window_seconds") or 300) // 60), 1)
        if ws.get("basis") == "recent":
            basis_note = f"近 {win} 分钟胜负弹幕 {ws.get('total', 0)} 条（阈值 {ws.get('threshold', 10)}），实时随弹幕更新，两队相加恒为 100%。"
        else:
            basis_note = f"整场胜负弹幕 {ws.get('total', 0)} 条（阈值 {ws.get('threshold', 10)}；近 {win} 分钟样本不足，回退累积），两队相加恒为 100%。"
        parts.append(f'<div class="note">{basis_note}</div>')
    else:
        total = (ws or {}).get("total", 0)
        th = (ws or {}).get("threshold", 10)
        parts.append(
            '<div class="note">样本不足'
            f'{"（显式胜负弹幕 " + str(total) + " 条" if total else ""} < 阈值 {th}'
            '），暂不给出胜率，随弹幕更新。</div>'
        )
    return _WIN_BEGIN + "".join(parts) + _WIN_END


def situation_ratings_block(ratings: dict | None, teams: list[str]) -> str:
    """比赛局势·评分子块（本小局评分，局内实时、局末冻结；含 RATINGS 标记供就地替换）。"""
    cols = _rating_cols(ratings, teams)
    if cols:
        game = (ratings or {}).get("game") or {}
        gname = str(game.get("name") or "") or f"第{game.get('num')}局" if game.get("num") else "本局"
        fetched = str((ratings or {}).get("fetched_at_utc") or "")
        body = (
            cols
            + '<div class="note">来源：虎扑通用评分（每小局独立）· '
            + f'{esc(gname)} · 抓取于 {esc(fetched[:19].replace("T", " ") if fetched else "-")}</div>'
        )
    else:
        body = '<div class="note">暂未获取到虎扑选手评分（本场/本局评分尚未生成，或数据源缺失）。</div>'
    return _RAT_BEGIN + body + _RAT_END


def _situation(stats: dict, ratings: dict | None, teams: list[str]) -> str:
    """3 比赛局势：两队胜率（观众口径·非结论）+ 虎扑队员评分。

    局内实时、局末冻结（2026-10-18 定稿）：胜率 = 本小局弹幕口径（近 5 分钟，2026-10-19
    改）、评分 = 本小局评分，当前小局进行中随弹幕/评分实时刷新，本局结束生成 end 节点后
    冻结，不随后续小局变化；G1 页永远显示 G1 的数据。胜率/评分子块各外包 BEGIN/END 标记，
    供 refresh_situation 就地替换。
    """
    ws = (stats or {}).get("win_signal")
    if not isinstance(ws, dict):
        ws = None
    out = [
        '<h3 style="font-size:14px;margin:2px 0 8px">两队胜率（观众口径·非结论）</h3>',
        situation_win_block(ws, teams),
        '<h3 style="font-size:14px;margin:14px 0 8px">队员评分（虎扑·实时）</h3>',
        situation_ratings_block(ratings, teams),
    ]
    return "".join(out)


def situation_card(stats: dict, ratings: dict | None, teams: list[str]) -> str:
    """【比赛局势】完整卡片（含 <div class="card"> 包裹），供后置注入 codex 页使用。"""
    return card("3", "比赛局势", _situation(stats, ratings, teams))


# --------------------------------------------------------------------------- main

def render(
    data: dict,
    stats: dict,
    *,
    teams: list[str],
    date: str,
    gi: int,
    gphase: str,
    slug_id: str,
    max_games: int = 5,
    end_basis: str = "",
    late: bool = False,
    ratings: dict | None = None,
) -> str:
    data = data or {}
    stats = stats or {}
    phase_label = _PHASE_LABEL.get(gphase, gphase)
    title = f"{teams[0]} vs {teams[1]} · G{gi} {phase_label} · {date}"
    sub = (
        f"节点 G{gi} · {phase_label} · BO{max_games} · {esc(slug_id)}"
        + (" · 补发（窗口后生成）" if late else "")
    )
    sections = [
        ("1", "关键变量卡 + 阵容裁决卡", _key_vars_and_lineup(data)),
        ("2", "结果总览 / 状态核验", _status(data, stats, teams, gi, gphase, slug_id, max_games, end_basis)),
        ("3", "比赛局势", _situation(stats, ratings, teams)),
        ("4", "灰信号汇总", _gray(data)),
        ("5", "BP 锚点与选人情报", _bp(data)),
        ("6", "盘口与市场讨论", _market(data)),
        ("7", "方向性情报板", _direction(data)),
        ("8", "情报含义与决策落点", _decision(data)),
        ("9", "本局复盘", _replay(data, stats)),
        ("10", "队伍 / 人员画像", _profiles(data, stats)),
        ("11", "联赛规律与版本", _patterns(data)),
        ("12", "预测验证回填明细", _prediction(data)),
        ("13", "数据与溯源", _sources(data, stats)),
    ]
    footer = (
        "弹幕为低可信度信号需聚合；灰信号只作风险标注非证据；结果待官方确认。"
        "模板渲染 · tools/render_node_page.py"
    )
    return page(title, sub, _speed(data), sections, footer)


def main() -> int:
    ap = argparse.ArgumentParser(description="离线渲染一个情报节点页（AI 字段 JSON -> HTML）")
    ap.add_argument("--data", required=True, help="AI 结构化字段 JSON 路径")
    ap.add_argument("--stats", default=None, help="规则层 danmu_intel JSON 路径（可选）")
    ap.add_argument("--teams", required=True, help="逗号分隔两队，如 A,B")
    ap.add_argument("--date", required=True)
    ap.add_argument("--game", type=int, required=True)
    ap.add_argument("--phase", required=True, choices=["bp", "mid", "end"])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--max-games", type=int, default=5)
    ap.add_argument("--end-basis", default="")
    ap.add_argument("--late", action="store_true")
    ap.add_argument("--ratings", default=None, help="虎扑选手评分 JSON 路径（可选，fetch_hupu_player_ratings.py 产出）")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    stats = {}
    if args.stats:
        stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    ratings = None
    if args.ratings:
        ratings = json.loads(Path(args.ratings).read_text(encoding="utf-8"))
    teams = [t.strip() for t in args.teams.split(",")]
    if len(teams) != 2:
        raise SystemExit("--teams 需要恰好两个队伍，逗号分隔")
    html = render(
        data, stats,
        teams=teams, date=args.date, gi=args.game, gphase=args.phase,
        slug_id=args.slug, max_games=args.max_games, end_basis=args.end_basis,
        late=args.late, ratings=ratings,
    )
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"已渲染 {args.out}（{len(html)} bytes）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
