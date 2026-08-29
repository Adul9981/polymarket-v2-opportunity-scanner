#!/usr/bin/env python3
"""Export a classifier golden set from all snapshot classification.jsonl files.

发现回测链（只读）。Aggregates every snapshot's classification into one
human-reviewable reference table (review_status defaults to 待复核) plus a
machine-readable JSON, so the classifier can be regression-tested against a
fixed label set.

Usage:
    python3 tools/export_golden_set.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "docs" / "data" / "snapshots"
DEFAULT_OUTPUT_MD = ROOT / "reports" / f"classifier_golden_set_{datetime.now(timezone.utc):%Y-%m-%d}.md"
DEFAULT_OUTPUT_JSON = ROOT / "docs" / "data" / "classifier_golden_set.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export classifier golden set.")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    freq: Counter[str] = Counter()
    if SNAPSHOT_ROOT.exists():
        for snap_dir in sorted(SNAPSHOT_ROOT.iterdir()):
            classification = snap_dir / "classification.jsonl"
            if not snap_dir.is_dir() or not classification.exists():
                continue
            for line in classification.open("r", encoding="utf-8"):
                row = json.loads(line)
                labels = [str(x) for x in row.get("labels") or []]
                for label in labels:
                    freq[label] += 1
                rows.append(
                    {
                        "snapshot": snap_dir.name,
                        "series": str(row.get("file") or ""),
                        "labels": labels,
                        "low": row.get("low"),
                        "high": row.get("high"),
                        "low_time": row.get("low_time"),
                        "review_status": "待复核",
                        "note": "",
                    }
                )

    lines = [
        "# 形态分类器 Golden Set（人工复核标准集）",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        f"序列数：{len(rows)}。复核流程：逐行确认 labels 是否符合形态定义；确认后把",
        "review_status 改为 已复核，labels 有异议的在 note 里写修正建议。",
        "",
        "## 标签频率",
        "",
    ]
    for label, count in freq.most_common():
        lines.append(f"- {label}: {count}")
    lines.extend(
        [
            "",
            "## 逐序列",
            "",
            "| 快照 | 序列 | 标签 | 低点 | 高点 | 低点时间 | 复核状态 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['snapshot']} | {row['series']} | {'/'.join(row['labels']) or '-'} "
            f"| {row['low']} | {row['high']} | {row['low_time'] or '-'} "
            f"| {row['review_status']} | {row['note']} |"
        )
    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(rows), "rows": rows},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"golden set: {len(rows)} rows -> {md_path}")
    print(f"json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
