#!/usr/bin/env python3
"""Historical validation: replay snapshot series through the bar monitor engine.

发现回测链（只读）。For every 1-minute series under docs/data/snapshots/, converts
it to the bar monitor history format and replays the full lifecycle (rolling
windows, fills + D3 state machine accumulate) through tools/bar_monitor_runner.py
for S1 deep and S2 favorite-dip strategies, then aggregates which signals fired.

Usage:
    python3 tools/replay_bar_monitor.py
    python3 tools/replay_bar_monitor.py --strategies A_DEEP_REVERSAL B_FAVORITE_DIP
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "docs" / "data" / "snapshots"
BAR_RUNNER = ROOT / "tools" / "bar_monitor_runner.py"

WATCH_ACTIONS = (
    "single_bar_rally",
    "rebound_confirmed",
    "place_buy",
    "estimated_fill",
    "d2_trailing_active",
    "d3_stop_triggered",
    "stop_new_entry",
    "switch_to_s1_eval",
    "re_entry_eval",
    "budget_capped",
)


def load_series(path: Path) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for line in path.open("r", encoding="utf-8"):
        row = json.loads(line)
        ts = str(row["timestamp"]).replace("Z", "+00:00")
        points.append(
            {
                "t": int(datetime.fromisoformat(ts).timestamp()),
                "p": float(row["price"]),
            }
        )
    points.sort(key=lambda p: p["t"])
    return points


def series_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    if not SNAPSHOT_ROOT.exists():
        return files
    for snap_dir in sorted(SNAPSHOT_ROOT.iterdir()):
        if not snap_dir.is_dir():
            continue
        for path in sorted(snap_dir.glob("*_price_1m.jsonl")):
            files.append((snap_dir.name, path))
    return files


def run_one(
    snap: str,
    path: Path,
    strategy: str,
    workdir: Path,
    idx: int,
) -> tuple[list[str], list[str]]:
    points = load_series(path)
    history = workdir / f"h_{idx}.json"
    history.write_text(json.dumps({"points": points}, ensure_ascii=False))
    action_file = workdir / f"a_{idx}.jsonl"
    state_dir = workdir / "state"
    cmd = [
        sys.executable,
        str(BAR_RUNNER),
        "--replay-series",
        "--no-tag",
        "--history-file",
        str(history),
        "--slug",
        snap,
        "--outcome",
        path.stem,
        "--strategy",
        strategy,
        "--state-dir",
        str(state_dir),
        "--action-file",
        str(action_file),
        "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return [f"ERROR:{result.stderr[:80]}"], []
    except Exception as exc:  # noqa: BLE001
        return [f"ERROR:{str(exc)[:80]}"], []
    actions: list[str] = []
    labels: list[str] = []
    if action_file.exists():
        for line in action_file.open("r", encoding="utf-8"):
            row = json.loads(line)
            actions.append(str(row.get("action") or ""))
            for label in row.get("pattern_labels") or []:
                if label not in labels:
                    labels.append(label)
    return actions, labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay snapshots through the bar monitor engine.")
    parser.add_argument(
        "--strategies",
        nargs="*",
        default=["A_DEEP_REVERSAL", "B_FAVORITE_DIP"],
        help="Strategies to replay (default: S1 deep + S2 favorite dip).",
    )
    parser.add_argument(
        "--output-report",
        default=str(ROOT / "reports" / f"bar_monitor_replay_{datetime.now(timezone.utc):%Y-%m-%d}.md"),
    )
    args = parser.parse_args()

    files = series_files()
    if not files:
        raise SystemExit(f"no snapshot series under {SNAPSHOT_ROOT}")

    summary: dict[str, Counter] = {s: Counter() for s in args.strategies}
    rows: list[list[str]] = []
    with tempfile.TemporaryDirectory(prefix="bar_replay_") as tmp:
        workdir = Path(tmp)
        idx = 0
        for snap, path in files:
            for strategy in args.strategies:
                actions, labels = run_one(snap, path, strategy, workdir, idx)
                idx += 1
                seen: list[str] = []
                for action in actions:
                    if action in WATCH_ACTIONS:
                        summary[strategy][action] += 1
                    if action not in seen:
                        seen.append(action)
                rows.append(
                    [
                        snap,
                        path.stem,
                        strategy,
                        "/".join(seen) or "-",
                        "/".join(labels) or "-",
                    ]
                )

    lines = [
        "# Bar 监控历史回放验证",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        f"数据源：{SNAPSHOT_ROOT}，共 {len(files)} 条 1 分钟序列，"
        f"策略 {len(args.strategies)} 组，滚动窗口回放（fills + D3 状态机累计）。",
        "",
        "## 信号汇总（按策略）",
        "",
    ]
    for strategy in args.strategies:
        counter = summary[strategy]
        lines.append(f"### {strategy}")
        lines.append("")
        for action in WATCH_ACTIONS:
            count = counter.get(action, 0)
            if count:
                lines.append(f"- {action}: {count}")
        lines.append("")
    lines.extend(
        [
            "## 逐序列明细",
            "",
            "| 快照 | 序列 | 策略 | 触发动作 | 形态标签 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for snap, series, strategy, actions, labels in rows:
        lines.append(f"| {snap} | {series} | {strategy} | {actions} | {labels} |")
    lines.append("")
    report_path = Path(args.output_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
