#!/usr/bin/env python3
"""Build the gray-signal verification stats page from structured data.

Reads gray_entities.json / gray_signals.json / matches.json and emits a
per-entity verification-status table (known verdicts vs "待积累").

Usage:
  python3 tools/build_gray_stats.py [--out .danmu_intel_site/intel/intel_gray_verification_stats.html]
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def esc(s) -> str:
    return html.escape(str(s), quote=True)


KNOWN = {
    "monki": ("已判定", "2/3 方向兑现（08-19 兑现 / 08-21 未兑现 / 08-22 兑现）"),
    "we": ("已判定", "08-19 被疑方向与结果一致（口径待正式回填）"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entities", default="docs/data/intel/gray_entities.json")
    ap.add_argument("--signals", default="docs/data/intel/gray_signals.json")
    ap.add_argument("--out", default=".danmu_intel_site/intel/intel_gray_verification_stats.html")
    ap.add_argument("--report-out", default="reports/intel_gray_verification_stats.html")
    args = ap.parse_args()

    ed = json.loads(Path(args.entities).read_text(encoding="utf-8"))
    entities = ed.get("entities", ed.get("items", [])) if isinstance(ed, dict) else ed
    sd = json.loads(Path(args.signals).read_text(encoding="utf-8"))
    records = sd.get("records", []) if isinstance(sd, dict) else sd

    total_signals = sum(x.get("total_signals", 0) for x in entities)
    high = sum(1 for x in entities if x.get("max_severity") == "高")
    leagues = sorted({r.get("league", "-") for r in records})

    rows = ""
    for x in sorted(entities, key=lambda e: -e.get("total_signals", 0)):
        status, note = KNOWN.get(str(x.get("id", "")).lower(), ("待积累", "样本 / 判定随复盘回填"))
        rows += (
            f'<tr><td>{esc(x.get("name", x.get("id", "-")))}</td>'
            f'<td>{esc(x.get("type", "-"))}</td>'
            f'<td>{x.get("total_signals", 0)}</td>'
            f'<td>{esc(x.get("max_severity", "-"))}</td>'
            f'<td>{len(x.get("gray_records", []))}</td>'
            f'<td>{esc(status)}</td><td>{esc(note)}</td></tr>'
        )

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="灰信号主体验证状态统计 · 弹幕情报库">
<title>灰信号兑现率统计 · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3;--green:#1e8e3e;--amber:#b45309}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:26px 16px 60px}}
.wrap{{max-width:920px;margin:0 auto}}
h1{{font-size:23px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:18px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}}
.stat .num{{font-size:22px;font-weight:800;color:var(--accent)}}.stat .lbl{{font-size:12px;color:var(--sub);margin-top:2px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:14px}}
.card h2{{font-size:14px;font-weight:800;margin-bottom:8px}}
.row{{display:flex;justify-content:space-between;gap:12px;padding:7px 0;font-size:13px;border-bottom:1px solid var(--line)}}
.row:last-child{{border-bottom:0}}.row .k{{color:var(--sub)}}
table{{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}}
th{{font-size:10.5px;color:var(--sub);text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}}
td{{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
.warn{{background:#fff7f0;border-left:4px solid #ff9500;border-radius:8px;padding:11px 14px;font-size:12.5px;margin:10px 0}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>灰信号兑现率统计</h1>
<p class="sub">弹幕情报库 · 观众质疑（灰信号）→ 结果验证 · 数据源 gray_entities / gray_signals / matches</p>
<div class="stats">
  <div class="stat"><div class="num">{len(entities)}</div><div class="lbl">灰信号主体</div></div>
  <div class="stat"><div class="num">{total_signals}</div><div class="lbl">信号总量</div></div>
  <div class="stat"><div class="num">{len(records)}</div><div class="lbl">场次级记录</div></div>
  <div class="stat"><div class="num">{high}</div><div class="lbl">高预警主体</div></div>
</div>
<div class="card"><h2>主体验证状态（按信号量排序）</h2>
<table><thead><tr><th>主体</th><th>类型</th><th>信号量</th><th>最高预警</th><th>覆盖场次</th><th>验证状态</th><th>说明</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="card"><h2>覆盖与边界</h2>
<div class="row"><span class="k">覆盖联赛</span><span>{esc("、".join(leagues) or "-")}</span></div>
<div class="row"><span class="k">判定规则</span><span>兑现 = 被质疑方向与最终结果一致（弱 / 强分级中）；未判定主体显示"待积累"</span></div>
<div class="warn" style="margin-bottom:0">灰信号纪律：观众质疑 ≠ 假赛证据；只作风险标注与盘口对照素材。</div></div>
<footer>弹幕情报库 · 灰信号兑现率统计（自动生成）· 2026-08-24</footer>
</div></body></html>"""

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    Path(args.report_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_out).write_text(page, encoding="utf-8")
    print(f"wrote {out} + {args.report_out} ({len(entities)} entities)")


if __name__ == "__main__":
    main()
