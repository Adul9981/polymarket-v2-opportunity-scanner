#!/usr/bin/env python3
"""Create a one-click macOS launcher for a prepared grid trade plan."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BOT_PYTHON = "/Users/ad/Documents/polydata/polymarket_trading_bot_strategy/.venv/bin/python"
RUNNER = "/Users/ad/Documents/polymarket/tools/grid_plan_runner.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a .command launcher for one grid trade.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--token-id", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--poll-interval", type=int, default=20)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    plan_path = Path(args.plan).expanduser().resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    name = args.name or _slugify(
        "-".join(
            str(x)
            for x in (
                plan.get("market_slug", "market"),
                plan.get("side", "side"),
                plan.get("strategy_type", "grid"),
            )
            if x
        )
    )

    output = Path(args.output).expanduser().resolve() if args.output else (
        Path("/Users/ad/Documents/polymarket/runtime") / f"run_{name}.command"
    )
    log_file = Path("/Users/ad/Documents/polymarket/runtime/logs") / f"{name}.log"

    content = f"""#!/bin/zsh
cd /Users/ad/Documents/polymarket || exit 1

LOG_DIR="/Users/ad/Documents/polymarket/runtime/logs"
LOG_FILE="{log_file}"
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Market: {plan.get('market_title') or plan.get('market_slug')}"
echo "Side: {plan.get('side')}"
echo "Strategy: {plan.get('strategy_name') or plan.get('strategy_type')}"
echo "Plan: {plan_path}"
echo "Log: $LOG_FILE"
echo "============================================================"
echo

"{BOT_PYTHON}" -u \\
  "{RUNNER}" \\
  --plan "{plan_path}" \\
  --token-id "{args.token_id}" \\
  --poll-interval {args.poll_interval}

echo
echo "Finished at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Runner stopped. Press Enter to close this window."
read _
"""
    output.write_text(content, encoding="utf-8")
    output.chmod(0o755)
    print(output)
    print(log_file)


def _slugify(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()
    return name or "grid-trade"


if __name__ == "__main__":
    main()
