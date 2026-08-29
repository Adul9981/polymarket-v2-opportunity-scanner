#!/usr/bin/env python3
"""List open orders with loud failure on API errors.

2026-08-05 reliability lesson: get_open_orders can silently return empty when the
API is flaky. This tool never treats a failed query as "no orders":
it retries, and exits non-zero on repeated failure so operators re-check.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


DEFAULT_BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")


def main() -> int:
    parser = argparse.ArgumentParser(description="List open orders with loud failure on API errors.")
    parser.add_argument("--bot-root", default=str(DEFAULT_BOT_ROOT))
    parser.add_argument("--token-id", default="", help="Filter by token id (optional)")
    parser.add_argument("--attempts", type=int, default=4)
    args = parser.parse_args()

    sys.path.insert(0, args.bot_root)
    import trading  # noqa: WPS433
    from config import Config  # noqa: WPS433

    cfg = Config.load()
    client = trading.init_client(cfg)

    last_error: Exception | None = None
    orders = None
    for attempt in range(1, args.attempts + 1):
        try:
            orders = client.get_open_orders()
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"open orders query attempt {attempt}/{args.attempts} failed: {exc}", file=sys.stderr)
            time.sleep(3)
    if orders is None:
        print(f"ERROR: open orders query failed after {args.attempts} attempts: {last_error}", file=sys.stderr)
        print("This is NOT a confirmed empty book. Re-check manually before acting.", file=sys.stderr)
        return 1

    mine = []
    for raw in orders or []:
        o = raw if isinstance(raw, dict) else getattr(raw, "__dict__", {})
        tid = str(o.get("asset_id") or o.get("token_id") or o.get("tokenId") or "")
        if args.token_id and tid != args.token_id:
            continue
        mine.append(
            {
                "id": o.get("id"),
                "side": o.get("side"),
                "price": o.get("price"),
                "original_size": o.get("original_size") or o.get("size"),
                "size_matched": o.get("size_matched") or o.get("matched_size") or 0,
                "status": o.get("status"),
                "asset_id": tid,
            }
        )

    print(f"confirmed open orders: {len(mine)}")
    for order in mine:
        print(json.dumps(order, ensure_ascii=False)[:240])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
