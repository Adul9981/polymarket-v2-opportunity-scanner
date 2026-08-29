#!/usr/bin/env python3
"""Cancel live orders tracked by a grid runner state file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")
LIVE_STATUSES = {"LIVE", "OPEN", "ACTIVE"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Cancel live Polymarket orders from a grid state file.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--bot-root", default=str(DEFAULT_BOT_ROOT))
    parser.add_argument("--include-buys", action="store_true", help="Cancel tracked entry BUY orders.")
    parser.add_argument("--include-sells", action="store_true", help="Cancel tracked exit SELL orders.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cancelled without cancelling.")
    args = parser.parse_args()

    if not args.include_buys and not args.include_sells:
        raise SystemExit("Pass --include-buys and/or --include-sells.")

    bot_root = Path(args.bot_root).expanduser().resolve()
    sys.path.insert(0, str(bot_root))

    import trading  # noqa: WPS433
    from config import Config  # noqa: WPS433
    from py_clob_client_v2.clob_types import OrderPayload  # noqa: WPS433

    state_path = Path(args.state_file).expanduser().resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cfg = Config.load()
    client = trading.init_client(cfg)

    orders = _tracked_orders(state, include_buys=args.include_buys, include_sells=args.include_sells)
    print(f"market: {state.get('market_title') or state.get('market_slug')}")
    print(f"side: {state.get('side')}")
    print(f"tracked orders: {len(orders)}")

    cancelled = 0
    skipped = 0
    failed = 0
    for item in orders:
        order_id = item["order_id"]
        order = _get_order(client, order_id)
        status = str(order.get("status") or "").upper() if order else "UNKNOWN"
        side = order.get("side") if order else item["side"]
        price = order.get("price") if order else item.get("price")
        size = order.get("original_size") or order.get("size") if order else item.get("size")
        matched = order.get("size_matched") or order.get("matched_size") or order.get("filled_size") if order else None
        label = f"{item['kind']} {order_id[:16]}... side={side} status={status} price={price} size={size} matched={matched}"

        if status not in LIVE_STATUSES:
            skipped += 1
            print(f"SKIP {label}")
            continue
        if args.dry_run:
            print(f"DRY  {label}")
            continue
        try:
            response = client.cancel_order(OrderPayload(orderID=order_id))
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {label} error={exc}")
            continue
        cancelled += 1
        print(f"DONE {label} response={response}")

    print(f"summary: cancelled={cancelled} skipped={skipped} failed={failed}")
    return 1 if failed else 0


def _tracked_orders(state: dict[str, Any], *, include_buys: bool, include_sells: bool) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    if include_buys:
        for layer in state.get("layers", []):
            order_id = str(layer.get("order_id") or "")
            if order_id:
                orders.append(
                    {
                        "kind": "BUY",
                        "side": "BUY",
                        "order_id": order_id,
                        "price": layer.get("entry_price"),
                        "size": layer.get("shares"),
                    }
                )
    if include_sells:
        for step in state.get("sell_steps", []):
            for order_id in step.get("order_ids") or []:
                orders.append(
                    {
                        "kind": step.get("id") or "SELL",
                        "side": "SELL",
                        "order_id": str(order_id),
                        "price": step.get("price"),
                        "size": None,
                    }
                )
    return orders


def _get_order(client, order_id: str) -> dict[str, Any] | None:
    try:
        order = client.get_order(order_id)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN order status query failed {order_id[:16]}... error={exc}")
        return None
    if isinstance(order, dict):
        return order
    if hasattr(order, "__dict__"):
        return {k: v for k, v in vars(order).items() if not k.startswith("_")}
    return {"value": str(order)}


if __name__ == "__main__":
    raise SystemExit(main())
