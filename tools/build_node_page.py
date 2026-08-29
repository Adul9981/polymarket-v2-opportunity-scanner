#!/usr/bin/env python3
"""Build a node intel page following the 10-section INTEL_HTML_TEMPLATE.

Every node (pre / bp / mid / review / series) gets a complete page with a
fixed 10-section skeleton; missing data shows "待补充 / 样本不足" (structure
never deleted). Optional --data JSON fills sections.

Usage:
  python3 tools/build_node_page.py --match-id 2026-08-18_dns_ns --game g1 --node bp \
      --out .danmu_intel_site/intel/node_2026-08-18_dns_ns_g1_bp.html \
      [--data docs/data/intel/node_data/...json]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def esc(s) -> str:
    return html.escape(str(s), quote=True)


SECTIONS = [
    ("1", "结果总览 / 当前进度"),
    ("2", "本局复盘 / 时间线"),
    ("3", "队伍画像"),
    ("4", "人员画像"),
    ("5", "灰信号汇总（观众质疑，非结论）"),
    ("6", "联赛规律与版本"),
    ("7", "预测验证"),
    ("8", "盘口讨论"),
    ("9", "情报含义与后续观察"),
    ("10", "数据与溯源"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--game", required=True, help="g1/g2/g3/series")
    ap.add_argument("--node", required=True, help="pre/bp/mid/review/series")
    ap.add_argument("--teams", default="")
    ap.add_argument("--league", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--window", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default="")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    args = ap.parse_args()

    match = {}
    p = Path(args.matches_json)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        match = next((m for m in data.get("matches", []) if m.get("id") == args.match_id), {})
    teams = args.teams or " vs ".join(match.get("teams", [])) or args.match_id
    league = args.league or match.get("league", "-")
    date = args.date or match.get("date", args.match_id[:10])

    fill: dict = {}
    if args.data:
        fill = json.loads(Path(args.data).read_text(encoding="utf-8"))
    window = args.window or fill.get("window", "")
    result = fill.get("result", match.get("result_inferred", ""))
    status = fill.get("status", "弹幕口径 · 官方待回填" if result else "结果待确认")

    cards = ""
    for num, title in SECTIONS:
        lines = fill.get("sections", {}).get(num, [])
        body = ""
        if lines:
            body = "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in lines) + "</ul>"
        else:
            body = '<div class="note">待补充 / 样本不足（结构保留，数据到位后自动回填）</div>'
        cards += f'<div class="card"><h2><span class="no">{num}</span>{title}</h2>{body}</div>'

    node_name = {"pre": "赛前", "bp": "BP", "mid": "局中", "review": "复盘", "series": "系列复盘"}.get(args.node, args.node)
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(teams)} · {esc(args.game)} {esc(node_name)} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.65;padding:26px 16px 60px}}
.wrap{{max-width:900px;margin:0 auto}}
h1{{font-size:22px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.result{{background:#eaf7ef;border:1px solid #bfe6cd;border-radius:14px;padding:12px 18px;margin-bottom:14px;font-size:13px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}}
.card h2{{font-size:13.5px;font-weight:800;margin-bottom:8px;display:flex;align-items:center;gap:8px}}
.card h2 .no{{font-size:10.5px;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:1px 7px}}
ul{{margin-left:18px;font-size:13px}}li{{margin:3px 0}}
.note{{color:var(--sub);font-size:12px}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>{esc(teams)} · {esc(args.game)} {esc(node_name)}</h1>
<div class="sub">{esc(league)} · {esc(date)} · 节点情报页（10 段标准模板）· 窗口：{esc(window or "待补充")}</div>
<div class="result"><b>{esc(result or "结果待确认")}</b> · {esc(status)}</div>
{cards}
<footer>弹幕情报库 · 节点情报页（build_node_page）· {esc(date)}</footer>
</div></body></html>"""

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
