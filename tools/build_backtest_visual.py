#!/usr/bin/env python3
"""Build visual backtest pages from compact backtest JSON files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/Users/ad/Documents/polymarket")
VIS_ROOT = Path("/Users/ad/.codex/visualizations/2026/08/03/019fc596-aebd-7080-819b-d3817a3dae59")


def load(name: str) -> dict:
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def compact(data: dict) -> dict:
    points = data["points"]
    if len(points) > 240:
        step = max(1, len(points) // 220)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
    else:
        sampled = points
    return {
        "event_title": data["event_title"],
        "game": data["game"],
        "strategy": data["strategy"],
        "shape_score": data["shape_score"],
        "outcome": data["outcome"],
        "market_title": data["market_title"],
        "summary": data["summary"],
        "points": sampled,
        "fills": data["fills"],
        "simulation": data["simulation"],
    }


DATA = [
    compact(load("lng_ig_game1_strategy_b_backtest.json")),
    compact(load("dnf_bro_game2_strategy_a_backtest.json")),
    compact(load("dota2_glyph_playti_game2_strategy_a_backtest.json")),
    compact(load("lol_ns_t1_game1_strategy_a_fullwindow_backtest.json")),
    compact(load("lol_ns_t1_match_winner_t1_fullwindow_backtest.json")),
    compact(load("lol_dnsc_dkc_game1_dk_strategy_a_backtest.json")),
]


FRAGMENT = f"""
<div id="strategy-ab-backtest-visual">
  <style>
    #strategy-ab-backtest-visual {{
      color: var(--foreground);
    }}
    #strategy-ab-backtest-visual .header-row {{
      display: block;
      margin-bottom: 14px;
    }}
    #strategy-ab-backtest-visual .sample-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }}
    #strategy-ab-backtest-visual .sample-btn {{
      appearance: none;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: color-mix(in srgb, var(--card) 74%, transparent);
      color: var(--foreground);
      padding: 8px 10px;
      cursor: pointer;
      text-align: left;
      max-width: 220px;
    }}
    #strategy-ab-backtest-visual .sample-btn[aria-pressed="true"] {{
      border-color: var(--viz-series-1);
      background: color-mix(in srgb, var(--viz-series-1) 12%, var(--card));
    }}
    #strategy-ab-backtest-visual .sample-btn b {{
      display: block;
      font-weight: 500;
    }}
    #strategy-ab-backtest-visual .sample-btn span {{
      color: var(--muted-foreground);
    }}
    #strategy-ab-backtest-visual .case-card {{
      border: 1px solid var(--border);
      border-radius: 8px;
      background: color-mix(in srgb, var(--card) 88%, transparent);
      padding: 12px;
      min-width: 0;
    }}
    #strategy-ab-backtest-visual .case-title {{
      font-weight: 500;
      margin-bottom: 6px;
    }}
    #strategy-ab-backtest-visual .case-meta {{
      color: var(--muted-foreground);
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    #strategy-ab-backtest-visual .metric-row {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    #strategy-ab-backtest-visual .metric {{
      border-top: 1px solid var(--border);
      padding-top: 8px;
      min-width: 0;
    }}
    #strategy-ab-backtest-visual .metric b {{
      display: block;
      font-weight: 500;
    }}
    #strategy-ab-backtest-visual .metric span {{
      color: var(--muted-foreground);
    }}
    #strategy-ab-backtest-visual .chart-grid {{
      display: block;
      margin-top: 8px;
    }}
    #strategy-ab-backtest-visual .chart-wrap {{
      min-width: 0;
    }}
    #strategy-ab-backtest-visual svg {{
      display: block;
      width: 100%;
      height: auto;
      overflow: visible;
    }}
    #strategy-ab-backtest-visual .axis {{
      stroke: var(--border);
      stroke-width: 1;
    }}
    #strategy-ab-backtest-visual .grid-line {{
      stroke: var(--border);
      stroke-width: 1;
      opacity: .55;
    }}
    #strategy-ab-backtest-visual .price-line {{
      fill: none;
      stroke: var(--viz-series-1);
      stroke-width: 2.5;
    }}
    #strategy-ab-backtest-visual .mid-line {{
      stroke: var(--muted-foreground);
      stroke-width: 1;
      stroke-dasharray: 5 5;
      opacity: .7;
    }}
    #strategy-ab-backtest-visual .buy-mark {{
      fill: var(--viz-series-2);
      stroke: var(--background);
      stroke-width: 2;
    }}
    #strategy-ab-backtest-visual .sell-mark {{
      fill: var(--viz-series-3);
      stroke: var(--background);
      stroke-width: 2;
    }}
    #strategy-ab-backtest-visual .risk-line {{
      stroke: var(--destructive);
      stroke-width: 1;
      stroke-dasharray: 3 5;
      opacity: .7;
    }}
    #strategy-ab-backtest-visual .label {{
      fill: var(--foreground);
      font-size: 12px;
    }}
    #strategy-ab-backtest-visual .muted {{
      fill: var(--muted-foreground);
      color: var(--muted-foreground);
    }}
    #strategy-ab-backtest-visual .template {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      margin-top: 14px;
    }}
    #strategy-ab-backtest-visual .step {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      background: color-mix(in srgb, var(--card) 72%, transparent);
    }}
    #strategy-ab-backtest-visual .step b {{
      display: block;
      font-weight: 500;
      margin-bottom: 4px;
    }}
    #strategy-ab-backtest-visual .step span {{
      color: var(--muted-foreground);
    }}
    #strategy-ab-backtest-visual .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      color: var(--muted-foreground);
      margin: 10px 0 0;
    }}
    #strategy-ab-backtest-visual .dot {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 4px;
      vertical-align: -1px;
    }}
    #strategy-ab-backtest-visual .buy-dot {{
      background: var(--viz-series-2);
    }}
    #strategy-ab-backtest-visual .sell-dot {{
      background: var(--viz-series-3);
    }}
    @media (max-width: 700px) {{
      #strategy-ab-backtest-visual .header-row,
      #strategy-ab-backtest-visual .chart-grid,
      #strategy-ab-backtest-visual .template {{
        grid-template-columns: 1fr;
      }}
      #strategy-ab-backtest-visual .metric-row {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
  <div class="sample-controls" id="sample-controls" aria-label="选择回测样本"></div>
  <div class="header-row" id="summary-cards"></div>
  <div class="chart-grid" id="charts"></div>
  <div class="legend">
    <span><span class="dot buy-dot"></span>固定金额买入</span>
    <span><span class="dot sell-dot"></span>成交后自动挂卖并触发</span>
    <span>虚线 50c 是中位线，B 型额外显示 40c 降级线</span>
  </div>
  <div class="template">
    <div class="step"><b>1 识别形态</b><span>A 看深度反转，B 看强队临时低估。</span></div>
    <div class="step"><b>2 固定预算</b><span>单轮示例 $25，不按账户比例动态放大。</span></div>
    <div class="step"><b>3 分层买入</b><span>触达限价即按固定金额挂买单。</span></div>
    <div class="step"><b>4 成交挂卖</b><span>买入成交后立刻生成多档卖单。</span></div>
    <div class="step"><b>5 保留彩票仓</b><span>卖完主要仓位，剩余固定成本等待极端命中。</span></div>
  </div>
  <script>
    (() => {{
      const data = {json.dumps(DATA, ensure_ascii=False)};
      const root = document.getElementById("strategy-ab-backtest-visual");
      const controls = root.querySelector("#sample-controls");
      const cards = root.querySelector("#summary-cards");
      const charts = root.querySelector("#charts");

      const fmtPct = v => `${{(v * 100).toFixed(v >= .995 ? 1 : 1)}}c`;
      const fmtUsd = v => `$${{Number(v).toFixed(2)}}`;
      const fmtTime = ts => new Date(ts * 1000).toLocaleTimeString([], {{ hour: "2-digit", minute: "2-digit" }});
      const roi = item => item.simulation.roi * 100;
      const esc = value => String(value).replace(/[&<>"']/g, ch => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }})[ch]);

      const shortTitle = item => item.event_title
        .replace("LoL: ", "")
        .replace("Dota 2: ", "")
        .split(" - ")[0];

      controls.innerHTML = data.map((item, index) => `
        <button class="sample-btn" type="button" data-index="${{index}}" aria-pressed="${{index === 0 ? "true" : "false"}}">
          <b>${{esc(item.strategy)}} · ${{esc(item.outcome)}}</b>
          <span>Game ${{item.game}} · ROI ${{roi(item).toFixed(1)}}%</span>
        </button>
      `).join("");

      function renderCard(item) {{
        cards.innerHTML = `
        <section class="case-card" aria-label="${{esc(item.strategy)}} 策略回测摘要">
          <div class="case-title">策略 ${{esc(item.strategy)}} · ${{esc(item.outcome)}} · Game ${{item.game}}</div>
          <div class="case-meta">
            <span>${{item.strategy === "A" ? "深度反转 / 彩票型" : "强队临时低估"}}</span>
            <span>形态分 ${{item.shape_score}}/100</span>
            <span>${{esc(shortTitle(item))}}</span>
          </div>
          <div class="metric-row">
            <div class="metric"><b>${{fmtPct(item.summary.min)}}</b><span>最低价</span></div>
            <div class="metric"><b>${{fmtPct(item.summary.after_min_max)}}</b><span>低点后最高</span></div>
            <div class="metric"><b>${{fmtUsd(item.simulation.pnl)}}</b><span>估算盈亏</span></div>
            <div class="metric"><b>${{roi(item).toFixed(1)}}%</b><span>估算 ROI</span></div>
          </div>
        </section>
      `;
      }}

      function nearestPoint(points, ts, price) {{
        let best = points[0];
        let bestDist = Infinity;
        for (const p of points) {{
          const d = Math.abs(p.t - ts) + Math.abs(p.p - price) * 5000;
          if (d < bestDist) {{
            best = p;
            bestDist = d;
          }}
        }}
        return best;
      }}

      function draw(item, index) {{
        const width = 720;
        const height = 330;
        const margin = {{ left: 46, right: 44, top: 28, bottom: 42 }};
        const innerW = width - margin.left - margin.right;
        const innerH = height - margin.top - margin.bottom;
        const points = item.points;
        const minT = points[0].t;
        const maxT = points[points.length - 1].t;
        const x = t => margin.left + ((t - minT) / Math.max(1, maxT - minT)) * innerW;
        const y = p => margin.top + (1 - p) * innerH;
        const path = points.map((p, i) => `${{i ? "L" : "M"}} ${{x(p.t).toFixed(1)}} ${{y(p.p).toFixed(1)}}`).join(" ");
        const ticks = [0, .25, .5, .75, 1];
        const timeTicks = [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]];
        const fillMarks = item.fills.map((fill, i) => {{
          const p = nearestPoint(points, fill.t, fill.price);
          const cx = x(p.t);
          const cy = y(fill.price);
          const cls = fill.action === "BUY" ? "buy-mark" : "sell-mark";
          const labelY = fill.action === "BUY" ? cy + 18 : cy - 12;
          return `
            <circle class="${{cls}}" cx="${{cx.toFixed(1)}}" cy="${{cy.toFixed(1)}}" r="5"></circle>
            <text class="label" x="${{Math.min(width - 90, cx + 7).toFixed(1)}}" y="${{Math.max(14, Math.min(height - 12, labelY)).toFixed(1)}}">${{fill.action === "BUY" ? "买" : "卖"}}${{i + 1}} ${{fmtPct(fill.price)}}</text>
          `;
        }}).join("");
        const minX = x(item.summary.min_ts);
        const maxX = x(item.summary.max_ts);
        return `
          <section class="chart-wrap" aria-label="${{esc(item.outcome)}} 价格走势">
            <svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="${{esc(item.outcome)}} 策略 ${{esc(item.strategy)}} 回测图">
              <title>${{esc(item.outcome)}} Game ${{item.game}} 策略 ${{esc(item.strategy)}} 回测</title>
              <desc>价格线展示历史赔率，圆点展示固定金额买入和自动卖出触发点。</desc>
              ${{ticks.map(t => `<line class="grid-line" x1="${{margin.left}}" y1="${{y(t).toFixed(1)}}" x2="${{width - margin.right}}" y2="${{y(t).toFixed(1)}}"></line><text class="label muted" x="${{width - margin.right + 8}}" y="${{(y(t) + 4).toFixed(1)}}">${{Math.round(t * 100)}}%</text>`).join("")}}
              <line class="mid-line" x1="${{margin.left}}" y1="${{y(.5).toFixed(1)}}" x2="${{width - margin.right}}" y2="${{y(.5).toFixed(1)}}"></line>
              ${{item.strategy === "B" ? `<line class="risk-line" x1="${{margin.left}}" y1="${{y(.4).toFixed(1)}}" x2="${{width - margin.right}}" y2="${{y(.4).toFixed(1)}}"></line><text class="label muted" x="${{margin.left + 4}}" y="${{(y(.4) - 6).toFixed(1)}}">40c 降级线</text>` : ""}}
              <path class="price-line" d="${{path}}"></path>
              <circle class="sell-mark" cx="${{minX.toFixed(1)}}" cy="${{y(item.summary.min).toFixed(1)}}" r="4"></circle>
              <text class="label" x="${{Math.min(width - 140, minX + 8).toFixed(1)}}" y="${{(y(item.summary.min) + 18).toFixed(1)}}">低点 ${{fmtPct(item.summary.min)}}</text>
              <circle class="sell-mark" cx="${{maxX.toFixed(1)}}" cy="${{y(item.summary.max).toFixed(1)}}" r="4"></circle>
              ${{fillMarks}}
              ${{timeTicks.map(p => `<text class="label muted" x="${{x(p.t).toFixed(1)}}" y="${{height - 12}}" text-anchor="middle">${{fmtTime(p.t)}}</text>`).join("")}}
              <text class="label" x="${{margin.left}}" y="16">策略 ${{esc(item.strategy)}} · ${{esc(item.market_title)}} · ${{esc(item.outcome)}}</text>
            </svg>
          </section>
        `;
      }}

      function renderSelected(index) {{
        const item = data[index];
        controls.querySelectorAll("button").forEach((button, buttonIndex) => {{
          button.setAttribute("aria-pressed", String(buttonIndex === index));
        }});
        renderCard(item);
        charts.innerHTML = draw(item, index);
      }}

      controls.addEventListener("click", event => {{
        const button = event.target.closest("button[data-index]");
        if (!button) return;
        renderSelected(Number(button.dataset.index));
      }});

      renderSelected(0);
    }})();
  </script>
</div>
"""


STANDALONE = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>策略 A/B 回测可视化</title>
  <style>
    :root {{
      --background: #f7f8fa;
      --foreground: #15181f;
      --card: #ffffff;
      --muted-foreground: #687282;
      --border: #dfe3ea;
      --destructive: #c23b3b;
      --viz-series-1: #315f9d;
      --viz-series-2: #21885b;
      --viz-series-3: #b26a22;
    }}
    body {{
      margin: 0;
      background: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 28px;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 28px;
      margin: 0 0 8px;
      font-weight: 600;
    }}
    .lead {{
      color: var(--muted-foreground);
      margin-bottom: 18px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>策略 A/B 回测可视化</h1>
    <div class="lead">固定金额买入，成交后自动挂卖，分批回收后保留彩票仓。</div>
    {FRAGMENT}
  </main>
</body>
</html>
"""


def main() -> None:
    (ROOT / "reports" / "strategy_ab_backtest_visual.html").write_text(STANDALONE, encoding="utf-8")
    VIS_ROOT.mkdir(parents=True, exist_ok=True)
    (VIS_ROOT / "strategy-ab-backtest.html").write_text(FRAGMENT, encoding="utf-8")
    print(ROOT / "reports" / "strategy_ab_backtest_visual.html")
    print(VIS_ROOT / "strategy-ab-backtest.html")


if __name__ == "__main__":
    main()
