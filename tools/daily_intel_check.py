#!/usr/bin/env python3
"""Daily Polymarket esports match check for the danmu-intel product.

Lists today's Polymarket-related esports matches from the latest live-scan
outputs and writes reports/intel_daily_matches_<date>.md.

Prereq: run the live scan first (tools/task2_pipeline.py / market_scanner),
which writes runtime/watchlist_events.json. Empty results must pass the
empty-result self-check (AGENTS 最高优先级防错规则 1) before reporting
"no matches today".
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path


def load_list(path: Path) -> list:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("events", data.get("items", data.get("matches", [])))


def main() -> None:
    today = datetime.date.today().isoformat()
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=today)
    ap.add_argument("--watchlist", default="runtime/watchlist_events.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--scan", action="store_true", help="run live scan first (needs network)")
    args = ap.parse_args()

    wl = Path(args.watchlist)
    lines: list[str] = []
    if args.scan:
        scan_report = f"reports/opportunity_scan_{args.date}.md"
        print(f"running live scan -> {wl} / {scan_report}")
        subprocess.run(
            [
                sys.executable,
                "tools/market_scanner.py",
                "--live",
                "--output-events",
                str(wl),
                "--output-report",
                scan_report,
            ],
            check=False,
        )
    if wl.exists():
        mtime = datetime.datetime.fromtimestamp(wl.stat().st_mtime)
        age_days = (datetime.datetime.now() - mtime).days
        if age_days >= 1:
            lines.append(f"> 警告：{wl.name} 已 {age_days} 天未更新，先跑 live scan 再判断今日无比赛。")
        for e in load_list(wl):
            d = str(e.get("start_date", e.get("startDate", e.get("date", ""))))[:10]
            if d == args.date:
                lines.append(
                    f"- {e.get('league', '-')} | {e.get('title', e.get('name', '-'))} "
                    f"| slug={e.get('slug', '-')} | {e.get('status', '-')}"
                )
    if not lines:
        lines.append(f"今日 {args.date} 未登记 Polymarket 电竞比赛——空结果必须过空结果自检，禁止直接报无比赛。")

    out = Path(args.out or f"reports/intel_daily_matches_{args.date}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"# 每日 Polymarket 电竞比赛检查（{args.date}）\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
