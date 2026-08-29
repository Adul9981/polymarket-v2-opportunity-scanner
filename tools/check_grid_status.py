#!/usr/bin/env python3
"""Read-only status check for a grid runner state file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Polymarket order status for a grid state file.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--bot-root", default=str(DEFAULT_BOT_ROOT))
    args = parser.parse_args()

    bot_root = Path(args.bot_root).expanduser().resolve()
    sys.path.insert(0, str(bot_root))

    import trading  # noqa: WPS433
    from config import Config  # noqa: WPS433

    state_path = Path(args.state_file).expanduser().resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    cfg = Config.load()
    client = trading.init_client(cfg)

    print(f"market: {state.get('market_title') or state.get('market_slug')}")
    print(f"side: {state.get('side')}")
    print(f"token: {str(state.get('token_id', ''))[:16]}...")
    print()

    print("BUY orders")
    for layer in state.get("layers", []):
        order_id = str(layer.get("order_id") or "")
        print(_line_for_order(client, order_id, layer.get("entry_price"), layer.get("shares")))

    print()
    print("SELL orders")
    for step in state.get("sell_steps", []):
        order_ids = step.get("order_ids") or []
        if not order_ids:
            print(f"{step.get('id')} @ {step.get('price')}: no order yet")
            continue
        for order_id in order_ids:
            print(_line_for_order(client, str(order_id), step.get("price"), None, prefix=step.get("id")))

    return 0


def _line_for_order(
    client,
    order_id: str,
    expected_price: Any,
    expected_size: Any,
    *,
    prefix: str | None = None,
) -> str:
    if not order_id:
        return f"{prefix or 'order'}: no order id"
    try:
        order = client.get_order(order_id)
    except Exception as exc:  # noqa: BLE001
        return f"{prefix or 'order'} {order_id[:16]}...: status query failed: {exc}"
    if not isinstance(order, dict):
        order = {k: v for k, v in vars(order).items() if not k.startswith("_")}
    status = order.get("status")
    side = order.get("side")
    price = order.get("price")
    size = order.get("original_size") or order.get("size")
    matched = order.get("size_matched") or order.get("matched_size") or order.get("filled_size")
    return (
        f"{prefix or 'order'} {order_id[:16]}... "
        f"side={side} status={status} price={price} size={size} matched={matched} "
        f"expected_price={expected_price} expected_size={expected_size}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
