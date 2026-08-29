#!/usr/bin/env python3
"""Build a match-detail page with the unified two-level selector shell.

Level 1 = game (G1/G2/G3.../series review); Level 2 = time node
(pre / BP / mid / review). Mid node uses node_<id>_gN.html if present,
otherwise falls back to the match report page; missing nodes show a
"暂无" placeholder (never 404).

Usage:
  python3 tools/build_match_page.py --match-id 2026-08-22_we_lgd [--push]
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path


def esc(s) -> str:
    return html.escape(str(s), quote=True)


SHELL = """<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>比赛详情 · {title} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3;--green:#1e8e3e}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 56px}}
.wrap{{max-width:980px;margin:0 auto}}
.top{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--line)}}
.brand{{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14px;color:var(--ink);text-decoration:none}}
.logo{{width:26px;height:26px;border-radius:8px;background:linear-gradient(135deg,#0071e3,#5ac8fa);color:#fff;display:grid;place-items:center;font-weight:800;font-size:12px}}
.crumb{{font-size:12px;color:var(--sub)}}.crumb b{{color:var(--ink)}}
.navi{{font-size:12px;color:var(--sub);text-decoration:none;margin-left:4px}}.navi:hover{{color:var(--accent)}}
h1{{font-size:24px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13.5px;margin-bottom:14px}}
.result{{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:#eaf7ef;border:1px solid #bfe6cd;border-radius:16px;padding:12px 20px;margin-bottom:16px}}
.score{{font-size:22px;font-weight:800}}
.st{{color:var(--green);font-size:12.5px;font-weight:600}}
.mkt{{font-size:12.5px;color:var(--sub);margin-bottom:14px}}.mkt a{{color:var(--accent);text-decoration:none}}
.picker{{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}}
.row{{display:flex;gap:8px;flex-wrap:wrap}}
.gbtn{{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:9px 18px;font-size:14px;font-weight:700;color:var(--sub);cursor:pointer}}
.gbtn:hover{{color:var(--accent)}}.gbtn[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
.nbtn{{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:7px 14px;font-size:12.5px;font-weight:600;color:var(--sub);cursor:pointer}}
.nbtn:hover{{color:var(--accent)}}.nbtn[aria-pressed="true"]{{background:#e8f1fd;border-color:var(--accent);color:var(--accent)}}
.nbtn .s{{display:block;font-size:10px;font-weight:400;opacity:.85}}
.frame{{width:100%;height:820px;border:1px solid var(--line);border-radius:16px;background:#fff}}
.ph{{border:1px dashed var(--line);border-radius:16px;padding:34px;color:var(--sub);font-size:13px;text-align:center}}
.note{{color:var(--sub);font-size:12px;margin-top:12px}}
footer{{margin-top:18px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<div class="top">
  <a class="brand" href="intel_danmu_index.html"><span class="logo">DI</span>弹幕情报库</a>
  <span class="crumb">首页 › 今日比赛 › <b>{title}</b></span>
  <span style="margin-left:auto"><a class="navi" href="intel_danmu_index.html">首页</a>
  <a class="navi" href="intel_danmu_index.html">情报索引</a>
  <a class="navi" href="intel_gray_verification_stats.html">灰信号</a></span>
</div>
<h1>{title}</h1>
<div class="sub">{league} · {date} · 两级选择：先选局，再选时间点</div>
<div class="result"><div class="score">{result_disp}</div><div class="st">{status}</div></div>
{market}
<div class="picker">
  <div class="row" id="games">{game_btns}</div>
  <div class="row" id="nodes"></div>
</div>
<div id="ph" class="ph" hidden>该时间点暂无情报页（待产出）——数据采集后会自动接入，不会出现空白或 404。</div>
<iframe id="view" class="frame" title="时间点情报"></iframe>
<div class="note">按时间节点组织（不按直播间来源）：同一节点中韩情报合并展示；缺失节点显示"暂无"，不 404。</div>
<footer>弹幕情报库 · 比赛详情（统一模板）· {date}</footer>
</div>
<script>
(function () {{
  var VIEWS = {views_json};
  var games = document.querySelectorAll(".gbtn");
  var nodesBox = document.getElementById("nodes");
  var view = document.getElementById("view");
  var ph = document.getElementById("ph");
  var current = {{ game: Object.keys(VIEWS)[0], src: null }};
  function renderNodes(game) {{
    nodesBox.innerHTML = "";
    VIEWS[game].forEach(function (v) {{
      var b = document.createElement("button");
      b.className = "nbtn";
      b.setAttribute("aria-pressed", v.src === current.src ? "true" : "false");
      b.innerHTML = "<span class='t'>" + v.n + "</span><span class='s'>" + v.s + "</span>";
      b.addEventListener("click", function () {{ current.src = v.src; show(v.src); renderNodes(game); }});
      nodesBox.appendChild(b);
    }});
  }}
  function show(src) {{
    if (src === "__none__") {{ view.hidden = true; ph.hidden = false; }}
    else {{ view.hidden = false; ph.hidden = true; view.src = src; }}
  }}
  games.forEach(function (g) {{
    g.addEventListener("click", function () {{
      games.forEach(function (x) {{ x.setAttribute("aria-pressed", x === g ? "true" : "false"); }});
      current.game = g.getAttribute("data-game");
      var first = VIEWS[current.game].find(function (v) {{ return v.src !== "__none__"; }});
      current.src = first ? first.src : "__none__";
      renderNodes(current.game);
      show(current.src);
    }});
  }});
  var first = VIEWS[current.game].find(function (v) {{ return v.src !== "__none__"; }});
  current.src = first ? first.src : "__none__";
  renderNodes(current.game);
  show(current.src);
}})();
</script>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    ap.add_argument("--site-dir", default=".danmu_intel_site")
    ap.add_argument("--out-dir", default="", help="覆盖输出目录（默认 <site-dir>/intel）")
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--teams", default="", help="fallback teams A,B when match not in matches.json")
    ap.add_argument("--league", default="", help="fallback league when match not in matches.json")
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()

    site = Path(args.site_dir) / "intel"
    if args.out_dir:
        site = Path(args.out_dir)
    site.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(args.matches_json).read_text(encoding="utf-8"))
    match = next((m for m in data.get("matches", []) if m.get("id") == args.match_id), {})
    mid = args.match_id
    if not match and args.teams:
        match = {"id": mid, "teams": args.teams.split(","), "league": args.league, "date": mid[:10], "result_inferred": ""}
    teams = " vs ".join(match.get("teams", [])) or mid
    league = match.get("league", "-")
    date = match.get("date", "-")
    result = match.get("result_inferred", "")

    def has(name: str) -> bool:
        return (site / name).exists()

    team_slug = "-".join(str(t).replace(" ", "") for t in match.get("teams", []))
    report = f"intel_danmu_{team_slug}_{date}.html"
    # 命名变体：兼容 _full / _BP / _G<N> 等本库既有报告
    report_full = f"intel_danmu_{team_slug}_full_{date}.html"
    report_bp = f"intel_danmu_{team_slug}_BP_{date}.html"
    report_g = {g: f"intel_danmu_{team_slug}_G{g}_{date}.html" for g in range(1, args.games + 1)}
    views: dict[str, list[dict]] = {}
    for g in range(1, args.games + 1):
        key = f"g{g}"
        node_mid = f"node_{mid}_g{g}.html"
        node_pre = f"node_{mid}_g{g}_pre.html"
        node_bp = f"node_{mid}_g{g}_bp.html"
        node_review = f"node_{mid}_g{g}_review.html"
        g_report = report_g.get(g, report)
        mid_src = node_mid if has(node_mid) else (g_report if has(g_report) else (report if has(report) else "__none__"))
        bp_src = node_bp if has(node_bp) else (report_bp if has(report_bp) else "__none__")
        review_src = node_review if has(node_review) else (g_report if has(g_report) else mid_src)
        views[key] = [
            {"n": "赛前", "s": "完整页" if has(node_pre) else "暂无", "src": node_pre if has(node_pre) else "__none__"},
            {"n": "BP", "s": "完整页" if bp_src != "__none__" else "暂无", "src": bp_src},
            {"n": "局中", "s": "完整情报页" if mid_src != "__none__" else "暂无 · 待产出", "src": mid_src},
            {"n": "复盘", "s": "整场复盘（节点细分待产出）" if review_src != "__none__" else "暂无", "src": review_src},
        ]
    series_src = (
        f"match_{mid}_series.html"
        if has(f"match_{mid}_series.html")
        else (report_full if has(report_full) else (report if has(report) else "__none__"))
    )
    views["series"] = [
        {"n": "系列复盘", "s": "10 段完整页" if series_src != "__none__" else "暂无", "src": series_src}
    ]

    game_btns = "".join(
        f'<button class="gbtn" data-game="{k}"' + (' aria-pressed="true"' if i == 0 else ' aria-pressed="false"') + f'>{esc(k.upper() if k != "series" else "系列复盘")}</button>'
        for i, k in enumerate(views.keys())
    )
    page = SHELL.format(
        title=esc(teams),
        league=esc(league),
        date=esc(date),
        result=esc(result),
        status="弹幕口径 · 官方确认回填中" if result else "结果待确认",
        game_btns=game_btns,
    views_json=json.dumps(views, ensure_ascii=False),
    result_disp=esc(result or "结果待确认"),
    market=(
        f'<div class="mkt">Polymarket 市场：<a href="https://polymarket.com/event/{esc(match.get("event_slug", ""))}" target="_blank" rel="noopener">{esc(match.get("event_slug", ""))} →</a></div>'
        if match.get("event_slug")
        else '<div class="mkt">Polymarket 市场：链接待补</div>'
    ),
    )
    out = site / f"match_{mid}.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")

    if args.push:
        subprocess.run(["git", "-C", str(site.parent), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(site.parent), "commit", "-m", f"match shell {mid}", "-q"], check=True)
        subprocess.run(["git", "-C", str(site.parent), "push", "-q"], check=True)
        print("pushed")


if __name__ == "__main__":
    main()
