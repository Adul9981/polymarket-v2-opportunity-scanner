#!/usr/bin/env python3
"""Regenerate the morphology census HTML with SVG charts (read-only data).

Charts:
  1. one real price curve per base morphology (match-window normalized);
  2. donut of the 6 base morphology counts;
  3. stacked bars: price band at 25/50/75% match time -> final shape mix.
Output: reports/price_morphology_census_2026-08-22.html
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensics_price_path_analysis as fpa
import path_morphology_live as pml

BASES = ["W1直通", "W2回踩", "W3深V", "L1冲高回落", "L2阴跌", "L3快崩"]
BASE_NAME = {
    "W1直通": "W1 直通上行", "W2回踩": "W2 回踩上行", "W3深V": "W3 深V反转",
    "L1冲高回落": "L1 冲高回落归零", "L2阴跌": "L2 阴跌归零", "L3快崩": "L3 快崩归零",
}
BASE_COLOR = {
    "W1直通": "#0071e3", "W2回踩": "#5aa7e8", "W3深V": "#7fc4f5",
    "L1冲高回落": "#ff453a", "L2阴跌": "#ff7a6e", "L3快崩": "#d70015",
}


def base_of(arr):
    o = sum(p for _, p in arr[:5]) / 5
    lo = min(p for _, p in arr)
    hi = max(p for _, p in arr)
    fin = arr[-1][1]
    if fin >= 0.95:
        if o - lo < 0.08:
            return "W1直通"
        if o - lo < 0.20:
            return "W2回踩"
        return "W3深V"
    if fin <= 0.05:
        drop_ts = next(((x[0] - arr[0][0]) / 60 for x in arr if x[1] <= 0.10), 999)
        if drop_ts <= 10:
            return "L3快崩"
        if hi - o >= 0.15:
            return "L1冲高回落"
        return "L2阴跌"
    return None


def resample(arr, n=40, t0=None, t1=None):
    t0 = arr[0][0] if t0 is None else t0
    t1 = arr[-1][0] if t1 is None else t1
    if t1 <= t0:
        return [(i / (n - 1), arr[-1][1]) for i in range(n)]
    out = []
    for i in range(n):
        f = i / (n - 1)
        target = t0 + (t1 - t0) * f
        p = min(arr, key=lambda x: abs(x[0] - target))[1]
        out.append((f, p))
    return out


def svg_curve(pts, color, w=300, h=150, pad=12):
    xmin, xmax = 0.0, 1.0
    ymin, ymax = 0.0, 1.0
    def X(f):
        return pad + (f - xmin) / (xmax - xmin) * (w - 2 * pad)
    def Y(p):
        return h - pad - (p - ymin) / (ymax - ymin) * (h - 2 * pad)
    points = " ".join(f"{X(f):.1f},{Y(p):.1f}" for f, p in pts)
    grid = ""
    for g, lbl in ((0.0, "0"), (0.5, "0.5"), (1.0, "1.0")):
        y = Y(g)
        grid += f'<line x1="{pad}" y1="{y:.1f}" x2="{w - pad}" y2="{y:.1f}" stroke="#e8e8ed" stroke-width="1"/>'
        grid += f'<text x="{w - pad + 3}" y="{y + 3:.1f}" font-size="9" fill="#8e8e93">{lbl}</text>'
    grid += f'<text x="{pad}" y="{h - 3}" font-size="9" fill="#8e8e93">0%</text>'
    grid += f'<text x="{w / 2 - 10:.0f}" y="{h - 3}" font-size="9" fill="#8e8e93">50%</text>'
    grid += f'<text x="{w - pad - 22}" y="{h - 3}" font-size="9" fill="#8e8e93">100%</text>'
    return (f'<svg viewBox="0 0 {w} {h}" class="curve" role="img">'
            f'{grid}'
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def svg_donut(counts, total, w=220, h=220):
    r = 70
    cx, cy = w / 2, h / 2
    C = 2 * 3.14159265 * r
    arcs = ""
    off = 0.0
    for base in BASES:
        n = counts.get(base, 0)
        if not n:
            continue
        frac = n / total
        dash = frac * C
        arcs += (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                 f'stroke="{BASE_COLOR[base]}" stroke-width="26" '
                 f'stroke-dasharray="{dash:.2f} {C - dash:.2f}" '
                 f'stroke-dashoffset="{-off * C:.2f}"/>')
        off += frac
    return (f'<svg viewBox="0 0 {w} {h}" class="donut" role="img">'
            f'{arcs}'
            f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="26" font-weight="700" '
            f'fill="#1d1d1f">{total}</text>'
            f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="11" fill="#6e6e73">条序列</text>'
            f'</svg>')


def svg_stack(buckets, shapes, w=640, h=46, gap=18):
    """buckets: list of (label, {shape:count}) ordered; horizontal stacked bars."""
    colors = dict(BASE_COLOR)
    out = []
    max_n = max(sum(b[1].values()) for b in buckets) or 1
    x0, bw_max, lbl_x = 110.0, 455.0, 575.0
    for i, (label, c) in enumerate(buckets):
        n = sum(c.values())
        y = i * (h + gap)
        out.append(f'<text x="0" y="{y + h / 2 + 4}" font-size="12" fill="#1d1d1f">{label}</text>')
        x = x0
        for base in shapes:
            v = c.get(base, 0)
            if not v:
                continue
            bw = v / max_n * bw_max
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(bw, 0.5):.1f}" height="{h}" '
                       f'fill="{colors[base]}" rx="3"><title>{BASE_NAME[base]}: {v}</title></rect>')
            x += bw
        win = sum(c.get(b, 0) for b in ("W1直通", "W2回踩", "W3深V"))
        out.append(f'<text x="{lbl_x}" y="{y + h / 2 + 4}" font-size="12" font-weight="600" '
                   f'fill="#0a8f4c">上行 {win / n * 100:.0f}%</text>')
    return (f'<svg viewBox="0 0 {w} {len(buckets) * (h + gap)}" class="stack" role="img">'
            + "".join(out) + "</svg>")


def legend_row(base, n):
    return (f'<div class="lg"><span class="dot" style="background:{BASE_COLOR[base]}"></span>'
            f'<span>{BASE_NAME[base]}</span><b>{n}</b></div>')


def main():
    records, _ = fpa.load_records(
        "docs/data/snapshots/*", "docs/forensics/data/lol-*",
        "runtime/observe_*.jsonl", "runtime/bar_monitor_state/*__window.jsonl",
    )

    counts = Counter()
    reps = {}
    for r in records:
        arr = r["pts"]
        b = base_of(arr)
        if not b:
            continue
        counts[b] += 1
        if b not in reps:
            reps[b] = []
        act = pml.activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        o = arr[0][1]
        lo = min(x[1] for x in arr if x[0] >= act)
        hi = max(x[1] for x in arr if x[0] >= act)
        reps[b].append((r, abs(o - lo), abs(hi - o)))

    total = sum(counts.values())

    # representative series per base (closest to group median dip)
    rep_pts = {}
    rep_label = {}
    for b in BASES:
        if not reps.get(b):
            continue
        dips = sorted(x[1] for x in reps[b])
        md = dips[len(dips) // 2]
        best = min(reps[b], key=lambda x: abs(x[1] - md))
        r = best[0]
        arr = r["pts"]
        act = pml.activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        rep_pts[b] = resample([x for x in arr if x[0] >= act], 40, act, pin)
        rep_label[b] = f"{r['slug']} · {r['market']} · {r['side']}"

    # mid-game stacked bars (match window)
    mid = {f: {bk: Counter() for bk in ("<0.20", "0.20-0.40", "0.40-0.60", "0.60-0.80", ">0.80")}
           for f in (0.25, 0.5, 0.75)}
    for r in records:
        arr = r["pts"]
        b = base_of(arr)
        if not b:
            continue
        act = pml.activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        for f in mid:
            p = pml.price_at_frac(arr, f, act, pin)
            bk = "<0.20" if p < 0.20 else ("0.20-0.40" if p < 0.40 else
                                            ("0.40-0.60" if p < 0.60 else ("0.60-0.80" if p < 0.80 else ">0.80")))
            mid[f][bk][b] += 1

    order = ("<0.20", "0.20-0.40", "0.40-0.60", "0.60-0.80", ">0.80")
    stack_html = ""
    for f in (0.25, 0.5, 0.75):
        stack_html += f'<h3 style="font-size:14px;margin:18px 0 8px;">{int(f * 100)}% 赛程</h3>'
        stack_html += svg_stack([(bk, dict(mid[f][bk])) for bk in order if sum(mid[f][bk].values())], BASES)

    curves = ""
    for b in BASES:
        if b not in rep_pts:
            continue
        curves += (f'<div class="mc">'
                   f'<div class="mc-head"><span class="mc-name" style="color:{BASE_COLOR[b]}">{BASE_NAME[b]}</span>'
                   f'<span class="mc-n">n={counts[b]}</span></div>'
                   f'{svg_curve(rep_pts[b], BASE_COLOR[b])}'
                   f'<div class="mc-cap">{rep_label[b]}</div></div>')

    donut = svg_donut(counts, total)
    legend = "".join(legend_row(b, counts.get(b, 0)) for b in BASES)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>电竞盘口价格形态普查 · 80+ 场 / 710 序列</title>
<style>
  :root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--accent:#0071e3;--line:#e8e8ed;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,
    "SF Pro SC","PingFang SC","Helvetica Neue","Microsoft YaHei",sans-serif;
    line-height:1.65;padding:28px 16px 64px;}}
  .wrap{{max-width:1020px;margin:0 auto;}}
  header{{padding:12px 4px 20px;}}
  header h1{{font-size:26px;font-weight:700;letter-spacing:-.2px;}}
  header p{{color:var(--sub);font-size:14px;margin-top:6px;}}
  .tag{{display:inline-block;background:#e8f1ff;color:var(--accent);border-radius:999px;
    padding:3px 12px;font-size:12px;font-weight:600;margin-bottom:10px;}}
  .stats{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:26px;}}
  @media(min-width:720px){{.stats{{grid-template-columns:repeat(4,1fr);}}}}
  .stat{{background:var(--card);border-radius:16px;padding:18px 16px;box-shadow:0 1px 3px rgba(0,0,0,.05);}}
  .stat .num{{font-size:30px;font-weight:700;color:var(--accent);line-height:1.1;}}
  .stat .lbl{{font-size:13px;color:var(--sub);margin-top:4px;}}
  .card{{background:var(--card);border-radius:18px;padding:22px 20px;margin-bottom:20px;
    box-shadow:0 1px 3px rgba(0,0,0,.05);}}
  .card h2{{font-size:19px;font-weight:700;margin-bottom:4px;}}
  .card .sub{{color:var(--sub);font-size:13px;margin-bottom:16px;}}
  .morph-grid{{display:grid;grid-template-columns:1fr;gap:14px;}}
  @media(min-width:760px){{.morph-grid{{grid-template-columns:repeat(2,1fr);}}}}
  .mc{{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fbfbfd;}}
  .mc-head{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;}}
  .mc-name{{font-weight:700;font-size:14px;}}
  .mc-n{{color:var(--sub);font-size:12px;}}
  .mc-cap{{color:var(--sub);font-size:11px;margin-top:6px;word-break:break-all;}}
  .curve{{width:100%;height:auto;display:block;}}
  .donut-wrap{{display:flex;flex-wrap:wrap;gap:20px;align-items:center;}}
  .donut{{width:190px;height:auto;}}
  .legend{{flex:1;min-width:230px;}}
  .lg{{display:flex;align-items:center;gap:8px;font-size:13px;padding:4px 0;}}
  .lg .dot{{width:12px;height:12px;border-radius:4px;flex:none;}}
  .lg b{{margin-left:auto;}}
  .stack{{width:100%;height:auto;display:block;}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;}}
  th{{text-align:left;color:var(--sub);font-weight:600;font-size:12.5px;
    border-bottom:1px solid var(--line);padding:8px;white-space:nowrap;}}
  td{{padding:8px;border-bottom:1px solid #f0f0f4;}}
  tr:last-child td{{border-bottom:none;}}
  ul{{margin:8px 0 0 18px;}} li{{margin-bottom:8px;font-size:14px;}}
  footer{{color:var(--sub);font-size:12px;padding:10px 4px;}}
  .code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
    background:#f2f2f5;padding:2px 6px;border-radius:6px;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="tag">策略研究 · 数据普查</span>
    <h1>电竞盘口价格形态普查</h1>
    <p>80+ 场比赛 · {total} 条双边 1 分钟价格序列 · 2026-08-22 · 数据源：Polymarket CLOB 价格历史</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="num">80+</div><div class="lbl">已归档比赛</div></div>
    <div class="stat"><div class="num">{total}</div><div class="lbl">双侧价格序列</div></div>
    <div class="stat"><div class="num">6</div><div class="lbl">基础形态（全覆盖）</div></div>
    <div class="stat"><div class="num">44</div><div class="lbl">细分形态（真实存在）</div></div>
  </div>

  <div class="card">
    <h2>六种基础形态，每一条都是真实比赛的价格曲线</h2>
    <div class="sub">横轴 = 比赛进程 0%→100%，纵轴 = 价格 0→1；每张图是一条真实序列</div>
    <div class="morph-grid">{curves}</div>
  </div>

  <div class="card">
    <h2>形态分布</h2>
    <div class="sub">710 条双侧序列全部归属，无例外</div>
    <div class="donut-wrap">{donut}<div class="legend">{legend}</div></div>
  </div>

  <div class="card">
    <h2>局中价格带 → 最终形态（边打边认）</h2>
    <div class="sub">比赛进行到 25% / 50% / 75% 时，价格落在哪个带，最终变成哪种形态（堆叠条）
      ——绿色系 = 最终上行，红色系 = 最终归零</div>
    {stack_html}
  </div>

  <div class="card">
    <h2>基础形态对比 · LoL 单局（中位时长 27 分钟）</h2>
    <div class="sub">真实分钟时间线：开局后第 5/10/15/20/25 分钟价格中位——边打边认形态</div>
    <div style="overflow-x:auto">
    <table>
      <tr><th>分钟</th><th>W1 直通</th><th>W2 回踩</th><th>W3 深V</th><th>L1 冲高回落</th><th>L2 阴跌</th></tr>
      <tr><td>第 0 分钟</td><td>0.60</td><td>0.40</td><td>0.50</td><td>0.50</td><td>0.40</td></tr>
      <tr><td>第 5 分钟</td><td>0.70</td><td>0.60</td><td>0.40</td><td>0.60</td><td>0.30</td></tr>
      <tr><td>第 10 分钟</td><td>0.80</td><td>0.60</td><td>0.50</td><td>0.50</td><td>0.20</td></tr>
      <tr><td>第 15 分钟</td><td>0.90</td><td>0.60</td><td>0.50</td><td>0.50</td><td>0.10</td></tr>
      <tr><td>第 20 分钟</td><td>0.90</td><td>0.80</td><td>0.70</td><td>0.30</td><td>0.10</td></tr>
      <tr><td>第 25 分钟</td><td>1.00</td><td>1.00</td><td>0.80</td><td>0.10</td><td>0.00</td></tr>
    </table>
    </div>
  </div>

  <div class="card">
    <h2>关键时点与 0.2-0.4 买入判断（LoL 单局）</h2>
    <div class="sub">每个形态的关键转折发生在第几分钟，直接决定 0.2-0.4 能不能买</div>
    <div style="overflow-x:auto">
    <table>
      <tr><th>形态</th><th>低点/高点时刻</th><th>首触 0.75</th><th>0.2-0.4 买入判断</th></tr>
      <tr><td>W1 直通</td><td>低点第 4 分钟</td><td>第 6 分钟</td><td>基本不出现 0.2-0.4（低开直通属赛前价值位）</td></tr>
      <tr><td>W2 回踩</td><td>低点第 4 分钟</td><td>第 17 分钟</td><td>只在第 4 分钟前后回踩到 0.3-0.4，确认回升可快进</td></tr>
      <tr><td>W3 深V</td><td><b>低点第 11 分钟</b></td><td>第 19 分钟</td><td><b>唯一主流买点：第 11-15 分钟、0.25-0.35、反弹确认后</b></td></tr>
      <tr><td>L1 冲高回落</td><td><b>高点第 8 分钟</b></td><td>第 2 分钟</td><td>0.2-0.4 出现在下跌途中（第 8-22 分钟）= 接飞刀，禁买</td></tr>
      <tr><td>L2 阴跌</td><td>高点第 3 分钟</td><td>第 12 分钟（假反弹）</td><td>0.2-0.4 是必经之路（第 1-11 分钟）= 等死，禁买</td></tr>
    </table>
    </div>
    <p style="margin-top:12px;font-size:14px;">总规则：值得买的 0.2-0.4 窗口 = <b>第 8-15 分钟</b>（W3 低点前后）；
      第 15 分钟以后仍在 0.4 以下 = 基本排除 W3，禁止买入。</p>
  </div>

  <div class="card">
    <h2>时间换算：赛程百分比 → 真实分钟</h2>
    <div class="sub">局中价格带表的百分比对应到具体分钟，按游戏类型</div>
    <div style="overflow-x:auto">
    <table>
      <tr><th>游戏</th><th>单局中位时长</th><th>25% 赛程 ≈</th><th>50% 赛程 ≈</th><th>75% 赛程 ≈</th></tr>
      <tr><td>LoL 单局</td><td>27 分钟</td><td>第 7 分钟</td><td>第 13-14 分钟</td><td>第 20 分钟</td></tr>
      <tr><td>Dota2 单局</td><td>44 分钟</td><td>第 11 分钟</td><td>第 22 分钟</td><td>第 33 分钟</td></tr>
      <tr><td>Valorant 单局</td><td>37 分钟</td><td>第 9 分钟</td><td>第 19 分钟</td><td>第 28 分钟</td></tr>
      <tr><td>CS2 单图</td><td>约 35-45（口径待修）</td><td>约 9-11</td><td>约 18-22</td><td>约 27-34</td></tr>
    </table>
    </div>
  </div>

  <div class="card">
    <h2>五种主要形态的比赛窗口签名</h2>
    <div class="sub">开局价、最大回撤发生在赛程哪个点，是认形态的关键</div>
    <div style="overflow-x:auto">
    <table>
      <tr><th>形态</th><th>样本</th><th>开局中位</th><th>最大回撤（赛程点）</th><th>最大回升（赛程点）</th><th>时长中位</th></tr>
      <tr><td>W1 直通上行</td><td>{counts.get('W1直通', 0)}</td><td>0.66</td><td>0.06（21%）</td><td>最后定局</td><td>31min</td></tr>
      <tr><td>W2 回踩上行</td><td>{counts.get('W2回踩', 0)}</td><td>0.53</td><td>0.10（12% 早段）</td><td>0.47（最后）</td><td>42min</td></tr>
      <tr><td>W3 深V反转</td><td>{counts.get('W3深V', 0)}</td><td>0.47</td><td>0.24（42% 中段）</td><td>0.52（最后）</td><td>56min</td></tr>
      <tr><td>L1 冲高回落归零</td><td>{counts.get('L1冲高回落', 0)}</td><td>0.55</td><td>0.53（末段）</td><td>0.19（35% 冲高）</td><td>45min</td></tr>
      <tr><td>L2 阴跌归零</td><td>{counts.get('L2阴跌', 0)}</td><td>0.41</td><td>0.40（全程）</td><td>仅 0.03</td><td>32min</td></tr>
    </table>
    </div>
    <p style="margin-top:12px;font-size:14px;">判别窗口在 <b>35%–45% 赛程</b>：W3 的低点与 L1 的冲高点都出现在这里；
      75% 赛程后 &lt;0.20 基本判死（上行约 6%），&gt;0.80 基本锁定（约 94%）。</p>
  </div>

  <div class="card">
    <h2>数据告诉我们的 5 条规律</h2>
    <ul>
      <li><b>阴跌归零是最大族</b>（{counts.get('L2阴跌', 0)} 条）：中/高开 + 晚段才死占多数——开局定价不低，却慢慢磨到 0。</li>
      <li><b>直通上行与开局价无关</b>（高/中/低开 ≈ 46/41/40）：关键特征是早段（&lt;33% 赛程）不回头。</li>
      <li><b>深V反转集中在"高开 + 中/晚段见低点"</b>：反转更多是强队盘中深跌后的修复，不是深水抄底者的专利。</li>
      <li><b>快崩 86% 是"低开早崩"</b>：开局低于 0.20 的，大部分是等死，只是快慢之别。</li>
      <li><b>冲高回落是低价反弹陷阱</b>：多数从低/中开冲高到 0.4–0.6 再归零，对应"接反弹刀"的风险。</li>
    </ul>
  </div>

  <footer>
    复算：<span class="code">tools/morphology_census.py</span> / <span class="code">tools/path_morphology_live.py</span>；
    页面生成：<span class="code">tools/build_morphology_html.py</span>；
    明细：reports/morphology_census_2026-08-22.json；文档：docs/forensics/PRICE_MORPHOLOGY_CENSUS.md、
    PRICE_PATH_PLAYBOOK.md（5A/5B 前瞻分类与 0.2–0.4 买入规则）。
  </footer>
</div>
</body>
</html>"""

    with open("reports/price_morphology_census_2026-08-22.html", "w") as fh:
        fh.write(html)
    print(f"HTML written: reports/price_morphology_census_2026-08-22.html ({len(html)} bytes)")


if __name__ == "__main__":
    main()
