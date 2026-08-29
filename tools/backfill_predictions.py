#!/usr/bin/env python3
"""Backfill predictions from existing intel report HTML into matches.json.

Extracts the 预测验证 table (and （落空）/（待确认） notes) from each
reports/intel_danmu_<A>-<B>_<date>.html, maps it to the matches.json entry by
date + teams, and appends structured predictions (status=pending unless the
report already states 命中/落空).

Usage:
  python3 tools/backfill_predictions.py [--reports reports] [--matches-json docs/data/intel/matches.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_closed_loop  # noqa: E402


def map_report_to_match(data: dict, report_name: str) -> dict | None:
    m = re.match(r"intel_danmu_([A-Za-z0-9]+)-([A-Za-z0-9]+)_(\d{4}-\d{2}-\d{2})\.html$", report_name)
    if not m:
        return None
    a, b, date = m.group(1).lower(), m.group(2).lower(), m.group(3)
    want = {a, b}
    items = data.get("matches", []) if isinstance(data, dict) else data
    for entry in items:
        if entry.get("date") != date:
            continue
        teams = {str(t).lower() for t in entry.get("teams", [])}
        if teams == want:
            return entry
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    args = ap.parse_args()

    path = Path(args.matches_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for report in sorted(Path(args.reports).glob("intel_danmu_*-*_*.html")):
        entry = map_report_to_match(data, report.name)
        if entry is None:
            continue
        text = build_closed_loop.plain_text(report.read_text(encoding="utf-8"))
        rows = build_closed_loop.extract_predictions(text)
        if not rows:
            continue
        entry.setdefault("predictions", [])
        existing = {p.get("text") for p in entry["predictions"]}
        for r in rows:
            if r["pred"] in existing:
                continue
            if r["status"] == "待确认":
                continue  # skip unverdictable rows (signals / observations), keep predictions clean
            entry["predictions"].append(
                {
                    "text": r["pred"],
                    "time": "",
                    "category": "result",
                    "status": {"命中": "hit", "落空": "miss", "待确认": "pending"}.get(
                        r["status"], "pending"
                    ),
                    "note": r["detail"],
                }
            )
            existing.add(r["pred"])
            added += 1
        print(f"{report.name} -> {entry.get('id')}: +{len(rows)} rows")

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total added: {added}")


if __name__ == "__main__":
    main()
