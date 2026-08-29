#!/usr/bin/env python3
"""反事实复盘：给定价格序列 + 交易参数，计算"若按 D2 锁盈 / D3 止损规则执行"的结果。

回答"这笔亏损/盈利到底是运气还是流程"：
把实际结果和"规则化执行"的结果对比，差值就是流程带来的（正=规则本可避免的损失）。

Usage:
    python3 tools/counterfactual_review.py --snapshot-file <jsonl> --side <方向> \
        --entry 0.60 --budget 100 --tp 0.80 --tp-ratio 0.8 --stop-ratio 0.5

规则（默认）：首次触达 tp 价卖出 tp_ratio 比例成本（买80回收），剩余彩票持有到末价；
          触达止损价（entry*stop_ratio）先于 tp -> 全部离场（亏损 = stop_ratio-1）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def load_series(path: str) -> list[tuple[float, float]]:
    pts = []
    for line in open(path, encoding="utf-8"):
        row = json.loads(line)
        ts = row["timestamp"].replace("Z", "+00:00")
        pts.append((datetime.fromisoformat(ts).timestamp(), float(row["price"])))
    pts.sort()
    return pts


def simulate(pts: list[tuple[float, float]], entry: float, budget: float, tp: float, tp_ratio: float, stop_ratio: float):
    idx = next((i for i, (_, p) in enumerate(pts) if p <= entry), None)
    if idx is None:
        return {"status": "未入场（价格从未到 entry）"}
    stop = entry * stop_ratio
    for i in range(idx, len(pts)):
        p = pts[i][1]
        if p >= tp:
            floor = budget * (tp_ratio * tp / entry) - budget
            end = pts[-1][1]
            total = budget * (tp_ratio * tp / entry + (1 - tp_ratio) * end / entry) - budget
            return {
                "status": "止盈达成",
                "floor": round(floor, 2),
                "total_to_end": round(total, 2),
                "tp_time": datetime.fromtimestamp(pts[i][0], tz=timezone.utc).strftime("%H:%M"),
            }
        if p <= stop:
            loss = budget * (stop / entry) - budget
            return {"status": "触发止损", "floor": round(loss, 2), "total_to_end": round(loss, 2),
                    "stop_time": datetime.fromtimestamp(pts[i][0], tz=timezone.utc).strftime("%H:%M")}
    end = pts[-1][1]
    return {"status": "持有到末段", "floor": round(budget * end / entry - budget, 2),
            "total_to_end": round(budget * end / entry - budget, 2)}


def main() -> int:
    parser = argparse.ArgumentParser(description="反事实复盘：规则化执行 vs 实际结果")
    parser.add_argument("--snapshot-file", required=True)
    parser.add_argument("--side", default="")
    parser.add_argument("--entry", type=float, required=True, help="实际入场价（c，如 0.60）")
    parser.add_argument("--budget", type=float, default=100.0)
    parser.add_argument("--tp", type=float, default=0.80, help="止盈价（D2 锁盈位）")
    parser.add_argument("--tp-ratio", type=float, default=0.8, help="止盈卖出的成本比例")
    parser.add_argument("--stop-ratio", type=float, default=0.5, help="止损 = entry*此比例")
    parser.add_argument("--actual-pnl", type=float, default=None, help="实际盈亏（USDC）")
    args = parser.parse_args()

    pts = load_series(args.snapshot_file)
    r = simulate(pts, args.entry, args.budget, args.tp, args.tp_ratio, args.stop_ratio)
    print(f"=== 反事实复盘：{args.side or args.snapshot_file} ===")
    print(f"入场 {args.entry}，预算 {args.budget}，规则：{args.tp_ratio*100:.0f}% 成本 @ {args.tp} 止盈、止损 {args.entry*args.stop_ratio}")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if args.actual_pnl is not None and r.get("total_to_end") is not None:
        diff = r["total_to_end"] - args.actual_pnl
        print(f"实际盈亏: {args.actual_pnl} USDC")
        print(f"规则化执行: {r['total_to_end']} USDC")
        print(f"差值（正=规则本可避免/多赚）: {diff:.2f} USDC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
