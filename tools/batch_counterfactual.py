#!/usr/bin/env python3
"""Batch counterfactual review across all snapshot series (发现回测链, 只读).

Runs the rule-based D2/D3 execution (counterfactual_review.simulate) over every
1-minute series with two parameter sets (S2 favorite dip and S1 deep reversal),
and writes a report with rule-based PnL per series + status summary.

Usage:
    python3 tools/batch_counterfactual.py
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from counterfactual_review import load_series, simulate

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "docs" / "data" / "snapshots"

PARAM_SETS = {
    "S2_FAVORITE_DIP": {"entry": 0.45, "tp": 0.62, "tp_ratio": 0.8, "stop_ratio": 0.78, "budget": 100.0},
    "S1_DEEP_REVERSAL": {"entry": 0.08, "tp": 0.50, "tp_ratio": 0.8, "stop_ratio": 0.1, "budget": 100.0},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch counterfactual review over snapshots.")
    parser.add_argument(
        "--output-report",
        default=str(ROOT / "reports" / f"counterfactual_batch_{datetime.now(timezone.utc):%Y-%m-%d}.md"),
    )
    args = parser.parse_args()

    files = sorted(SNAPSHOT_ROOT.glob("*/*_price_1m.jsonl"))
    summary = {name: Counter() for name in PARAM_SETS}
    pnl = {name: [] for name in PARAM_SETS}
    lines = [
        "# 反事实复盘批量（规则化执行 vs 快照全量）",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        f"序列数：{len(files)}（docs/data/snapshots）。预算每套 $100。",
        "",
        "规则参数：",
        "",
    ]
    for name, params in PARAM_SETS.items():
        lines.append(
            f"- {name}：entry {params['entry']} / TP {params['tp']}（{int(params['tp_ratio']*100)}% 成本）/ "
            f"stop {round(params['entry']*params['stop_ratio'], 3)}"
        )
    lines.extend(["", "## 逐序列", "", "| 快照 | 序列 | S2 规则结果 | S2 盈亏 | S1 规则结果 | S1 盈亏 |", "| --- | --- | --- | --- | --- | --- |"])

    for path in files:
        pts = load_series(str(path))
        snap = path.parent.name
        row = [snap, path.stem]
        for name in PARAM_SETS:
            params = PARAM_SETS[name]
            result = simulate(
                pts,
                params["entry"],
                params["budget"],
                params["tp"],
                params["tp_ratio"],
                params["stop_ratio"],
            )
            status = result.get("status", "?")
            summary[name][status] += 1
            value = result.get("total_to_end")
            if value is not None:
                pnl[name].append(float(value))
            row.extend([status, f"{value if value is not None else '-'}"])
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(["", "## 汇总", ""])
    for name in PARAM_SETS:
        counter = summary[name]
        values = pnl[name]
        lines.append(f"### {name}")
        lines.append("")
        for status, count in counter.most_common():
            lines.append(f"- {status}: {count}")
        if values:
            avg = sum(values) / len(values)
            wins = sum(1 for v in values if v > 0)
            lines.append(f"- 序列数 {len(values)}，平均规则盈亏 {avg:+.1f} USDC，盈利 {wins}/{len(values)}")
        lines.append("")
    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(files)} series to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
