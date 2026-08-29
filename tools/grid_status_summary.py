#!/usr/bin/env python3
"""Human-friendly status summary for a grid runner state file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarise grid trade status in Chinese.")
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

    buy_rows = [_order_row(client, layer.get("order_id"), layer, "BUY") for layer in state.get("layers", [])]
    sell_rows = []
    for step in state.get("sell_steps", []):
        order_ids = step.get("order_ids") or []
        if not order_ids:
            sell_rows.append(
                {
                    "id": step.get("id"),
                    "side": "SELL",
                    "status": "未挂出",
                    "price": step.get("price"),
                    "size": None,
                    "matched": 0.0,
                    "remaining": 0.0,
                    "expected_price": step.get("price"),
                }
            )
            continue
        for order_id in order_ids:
            sell_rows.append(_order_row(client, order_id, step, "SELL"))

    filled_buy_size = sum(row["matched"] for row in buy_rows)
    open_buy_count = sum(1 for row in buy_rows if row["status"] == "LIVE")
    open_sell_count = sum(1 for row in sell_rows if row["status"] == "LIVE")
    filled_sell_size = sum(row["matched"] for row in sell_rows)
    exposure = _exposure_summary(trading, client, state, buy_rows, sell_rows)

    print(f"市场：{state.get('market_title') or state.get('market_slug')}")
    print(f"买入方向：{state.get('side')}")
    print(f"策略：{state.get('strategy_name') or state.get('strategy_type')}")
    print()

    print("买入挂单：")
    for row in buy_rows:
        print(_format_order(row))
    print()

    print("已成交：")
    print(f"- 买入成交份额：{filled_buy_size:.2f}")
    print(f"- 卖出成交份额：{filled_sell_size:.2f}")
    print()

    print("止盈卖单：")
    for row in sell_rows:
        print(_format_order(row))
    print()

    print(f"彩票仓位：成本 {float(state.get('lottery_cost_basis_usd') or 0):.2f} USDC")
    print()

    print("D2 自动锁盈：")
    print(f"- 已投入成本：{exposure['buy_cost']:.2f} USDC")
    print(f"- 已锁定利润：{exposure['locked_profit']:.2f} USDC")
    print(f"- 剩余仓位成本：{exposure['remaining_cost']:.2f} USDC")
    if exposure["current_price"] is None:
        print("- 当前市值：暂时无法估算")
    else:
        print(f"- 当前市值：{exposure['remaining_value']:.2f} USDC @ {_fmt_price(exposure['current_price'])}")
        print(f"- 如果从这里归零，损失当前市值：{exposure['remaining_value']:.2f} USDC")
        print(f"- 未锁浮盈：{exposure['unlocked_profit']:.2f} USDC")
    print(f"- 彩票仓上限：{exposure['lottery_limit']:.2f} USDC")
    if exposure["excess_lottery_cost"] > 0:
        print(f"- 超出彩票仓上限：{exposure['excess_lottery_cost']:.2f} USDC，应继续锁盈/减仓。")
    else:
        print("- 剩余仓位在彩票仓上限内。")
    print()

    print("当前判断：")
    if open_buy_count or open_sell_count:
        print(f"- 仍有未成交挂单：买单 {open_buy_count} 张，卖单 {open_sell_count} 张。")
    else:
        print("- 当前没有已识别的 live 挂单。")
    if filled_buy_size > 0 and open_sell_count == 0:
        print("- 有买入成交但没有 live 止盈卖单，需要检查 monitor 是否在运行。")
    elif filled_buy_size > 0:
        print("- 已有买入成交，并且存在止盈卖单。")
    else:
        print("- 还没有识别到买入成交。")
    return 0


def _exposure_summary(
    trading,
    client,
    state: dict[str, Any],
    buy_rows: list[dict[str, Any]],
    sell_rows: list[dict[str, Any]],
) -> dict[str, float | None]:
    buy_cost = sum(
        float(row.get("matched") or 0) * float(row.get("expected_price") or row.get("price") or 0)
        for row in buy_rows
        if str(row.get("side") or "").upper() == "BUY"
    )
    filled_buy_size = sum(float(row.get("matched") or 0) for row in buy_rows)
    filled_sell_size = sum(float(row.get("matched") or 0) for row in sell_rows)
    sell_proceeds = sum(
        float(row.get("matched") or 0) * float(row.get("price") or row.get("expected_price") or 0)
        for row in sell_rows
    )
    avg_entry = buy_cost / filled_buy_size if filled_buy_size > 0 else 0.0
    sold_cost_basis = min(buy_cost, filled_sell_size * avg_entry)
    locked_profit = max(0.0, sell_proceeds - sold_cost_basis)
    remaining_size = max(0.0, filled_buy_size - filled_sell_size)
    remaining_cost = max(0.0, buy_cost - sold_cost_basis)
    current_price = _current_price(trading, client, str(state.get("token_id") or ""))
    remaining_value = remaining_size * current_price if current_price is not None else 0.0
    unlocked_profit = max(0.0, remaining_value - remaining_cost) if current_price is not None else 0.0
    lottery_limit = _lottery_limit(state, buy_cost)
    return {
        "buy_cost": buy_cost,
        "locked_profit": locked_profit,
        "remaining_cost": remaining_cost,
        "current_price": current_price,
        "remaining_value": remaining_value,
        "unlocked_profit": unlocked_profit,
        "lottery_limit": lottery_limit,
        "excess_lottery_cost": max(0.0, remaining_cost - lottery_limit),
    }


def _current_price(trading, client, token_id: str) -> float | None:
    if not token_id:
        return None
    try:
        market_data = trading.get_market_data(client, token_id)
    except Exception:  # noqa: BLE001
        return None
    for value in (
        getattr(market_data, "best_bid", None),
        getattr(market_data, "last_price", None),
        getattr(market_data, "mid", None),
        getattr(market_data, "best_ask", None),
    ):
        if value is not None:
            return float(value)
    return None


def _lottery_limit(state: dict[str, Any], buy_cost: float) -> float:
    plan = state.get("profit_lock_plan") or {}
    fixed_limit = _to_float(plan.get("max_lottery_cost_basis_usd"))
    ratio = _to_float(plan.get("max_lottery_cost_ratio"))
    configured_lottery = float(state.get("lottery_cost_basis_usd") or 0)
    candidates = []
    if fixed_limit is not None and fixed_limit > 0:
        candidates.append(fixed_limit)
    if ratio is not None and ratio > 0 and buy_cost > 0:
        candidates.append(buy_cost * ratio)
    if candidates:
        return min(candidates)
    return configured_lottery


def _order_row(client, order_id: Any, expected: dict[str, Any], default_side: str) -> dict[str, Any]:
    row = {
        "id": str(order_id or ""),
        "side": default_side,
        "status": "无订单",
        "price": expected.get("entry_price") or expected.get("price"),
        "size": expected.get("shares"),
        "matched": 0.0,
        "remaining": 0.0,
        "expected_price": expected.get("entry_price") or expected.get("price"),
    }
    if not order_id:
        return row
    try:
        order = client.get_order(str(order_id))
    except Exception as exc:  # noqa: BLE001
        row["status"] = "查询失败"
        row["error"] = str(exc)
        return row
    if not isinstance(order, dict):
        order = {k: v for k, v in vars(order).items() if not k.startswith("_")}

    size = _to_float(order.get("original_size") or order.get("size")) or 0.0
    matched = _to_float(order.get("size_matched") or order.get("matched_size") or order.get("filled_size"))
    status = str(order.get("status") or "").upper()
    if matched is None and status in {"MATCHED", "FILLED"}:
        matched = size
    matched = matched or 0.0
    row.update(
        {
            "side": order.get("side") or default_side,
            "status": status or "UNKNOWN",
            "price": _to_float(order.get("price")) or row["price"],
            "size": size or row["size"],
            "matched": matched,
            "remaining": max(0.0, size - matched) if size else 0.0,
        }
    )
    return row


def _format_order(row: dict[str, Any]) -> str:
    price = _fmt_price(row.get("price"))
    matched = float(row.get("matched") or 0)
    size = row.get("size")
    size_text = "-" if size is None else f"{float(size):.2f}"
    remaining = float(row.get("remaining") or 0)
    order_id = str(row.get("id") or "")
    order_text = order_id[:18] + "..." if order_id else "-"
    if row.get("status") == "查询失败":
        return f"- {row.get('side')} @ {price}：查询失败，订单 {order_text}"
    return (
        f"- {row.get('side')} @ {price}：{row.get('status')}，"
        f"数量 {size_text}，已成交 {matched:.2f}，剩余 {remaining:.2f}，订单 {order_text}"
    )


def _fmt_price(value: Any) -> str:
    try:
        return f"{round(float(value) * 100):.0f}c"
    except (TypeError, ValueError):
        return "-"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
