#!/usr/bin/env python3
"""Run a fixed-USD grid trade plan through the existing Polymarket bot code.

This runner reads the local A/B ``trade_config.json`` format and reuses the
already-installed execution project for wallet auth and order placement.

It supports:
- multiple fixed-USD BUY ladders
- multiple SELL targets by cost basis
- a fixed cost-basis lottery remainder

The file intentionally lives in this strategy/project folder so the existing
bot can remain untouched until this flow is proven stable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")
MIN_CLOB_ORDER_SIZE = 5.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute an A/B fixed-USD grid plan with layered buys and staged sells."
    )
    parser.add_argument("--plan", required=True, help="Path to trade_config.json")
    parser.add_argument("--bot-root", default=str(DEFAULT_BOT_ROOT))
    parser.add_argument("--token-id", default="", help="CLOB outcome token id")
    parser.add_argument(
        "--resolve-token",
        action="store_true",
        help="Resolve token_id from plan.market_slug + plan.side via the existing resolver",
    )
    parser.add_argument("--label", default="", help="Display label in logs/state")
    parser.add_argument("--state-file", default="", help="State JSON path")
    parser.add_argument("--poll-interval", type=int, default=20)
    parser.add_argument("--place-only", action="store_true")
    parser.add_argument("--monitor-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print orders without placing them")
    parser.add_argument(
        "--skip-market-check",
        action="store_true",
        help="Skip Gamma accepting-orders check after manual verification.",
    )
    parser.add_argument(
        "--skip-balance-check",
        action="store_true",
        help="Skip the pre-order USDC balance pre-flight check.",
    )
    args = parser.parse_args()

    bot_root = Path(args.bot_root).expanduser().resolve()
    if not bot_root.exists():
        raise SystemExit(f"bot root not found: {bot_root}")
    sys.path.insert(0, str(bot_root))

    import trading  # noqa: WPS433
    from config import Config  # noqa: WPS433

    plan_path = Path(args.plan).expanduser().resolve()
    plan = _load_plan(plan_path)

    token_id = args.token_id.strip()
    if args.resolve_token and not token_id:
        token_id = _resolve_token_from_plan(bot_root, plan)
    if not token_id:
        raise SystemExit("token_id is required. Pass --token-id or use --resolve-token.")

    label = args.label.strip() or _default_label(plan)
    state_path = Path(args.state_file).expanduser() if args.state_file else _default_state_path(bot_root, plan)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    buy_layers = _buy_layers(plan)
    sell_steps = _sell_steps(plan)
    lottery_cost = float(plan.get("lottery_cost_basis_usd") or 0.0)

    _print_plan_summary(plan, token_id, label, buy_layers, sell_steps, lottery_cost, state_path)
    if args.dry_run:
        print("[grid] dry-run only; no orders were placed.")
        return 0

    cfg = Config.load()
    client = trading.init_client(cfg)

    if not args.monitor_only:
        if not args.dry_run and not args.skip_balance_check:
            balance_usd = _query_usdc_balance(client)
            required_usd = sum(float(layer["usdc"]) for layer in buy_layers)
            _preflight_balance(balance_usd, required_usd)
        if args.skip_market_check:
            print("[grid] skipped Gamma market check; use only after manual verification")
        else:
            _assert_market_accepting_orders(plan["market_slug"])
        state = _place_layers(
            trading=trading,
            client=client,
            cfg=cfg,
            token_id=token_id,
            label=label,
            plan=plan,
            layers=buy_layers,
            sell_steps=sell_steps,
            lottery_cost=lottery_cost,
            state_path=state_path,
        )
        _save_state(state_path, state)
        if args.place_only:
            return 0
    else:
        state = _load_state(state_path)

    print("[grid] monitor started")
    while True:
        try:
            state = _load_state(state_path)
            changed = _ensure_sell_coverage(trading, client, cfg, state)
            if changed:
                _save_state(state_path, state)
        except Exception as exc:  # noqa: BLE001
            print(f"[grid] monitor cycle failed; will retry: {exc}")
    time.sleep(max(3, args.poll_interval))


def _query_usdc_balance(client: Any) -> float | None:
    """Query authenticated CLOB balance-allowance and return USDC balance in dollars (1e6 units)."""
    try:
        from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams

        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        data = client.get_balance_allowance(params)
    except Exception as exc:  # noqa: BLE001
        print(f"[preflight] 余额查询失败，跳过预检：{exc}")
        return None

    def _extract(value: Any) -> float | None:
        if isinstance(value, dict):
            for key in ("usdc_balance", "collateral_balance"):
                raw = value.get(key)
                if raw is not None:
                    try:
                        return float(raw) / 1_000_000.0
                    except (TypeError, ValueError):
                        pass
            raw = value.get("balance")
            if raw is not None:
                try:
                    return float(raw) / 1_000_000.0
                except (TypeError, ValueError):
                    pass
            for nested in value.values():
                if isinstance(nested, dict):
                    result = _extract(nested)
                    if result is not None:
                        return result
        return None

    balance = _extract(data)
    if balance is None:
        print(f"[preflight] 未能解析余额响应：{str(data)[:200]}")
    return balance


def _preflight_balance(balance_usd: float | None, required_usd: float) -> None:
    if balance_usd is None:
        return
    buffer = required_usd * 1.05
    if balance_usd < buffer:
        raise SystemExit(
            f"[preflight] 余额不足：可用约 {balance_usd:.2f} USDC，计划需约 {required_usd:.2f} USDC"
            f"（含 5% 缓冲）。请先充值，或缩小预算（--cycle-budget / --match-budget）。未挂出任何订单。"
        )
    print(f"[preflight] 余额充足：可用约 {balance_usd:.2f} USDC，计划需约 {required_usd:.2f} USDC。")


def _load_plan(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("amount_mode") != "fixed_usd":
        raise ValueError("plan.amount_mode must be fixed_usd")
    if not data.get("market_slug"):
        raise ValueError("plan.market_slug is required")
    if not data.get("side"):
        raise ValueError("plan.side is required")
    if not data.get("buy_ladders"):
        raise ValueError("plan.buy_ladders is required")
    if not data.get("sell_plan"):
        raise ValueError("plan.sell_plan is required")
    return data


def _buy_layers(plan: dict[str, Any]) -> list[dict[str, float]]:
    layers: list[dict[str, float]] = []
    for raw in plan["buy_ladders"]:
        price = _price(raw["price"])
        usdc = round(float(raw["amount_usd"]), 2)
        shares = _floor_size(usdc / price)
        if shares <= 0:
            continue
        layers.append({"entry_price": price, "usdc": usdc, "shares": shares})
    return layers


def _sell_steps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for idx, raw in enumerate(plan["sell_plan"], start=1):
        cost = round(float(raw["sell_cost_basis_usd"]), 2)
        if cost <= 0:
            continue
        steps.append(
            {
                "id": f"sell_{idx}",
                "price": _price(raw["price"]),
                "sell_cost_basis_usd": cost,
                "order_ids": [],
            }
        )
    stop = plan.get("stop_loss")
    if isinstance(stop, dict):
        cost = round(float(stop.get("sell_cost_basis_usd") or 0), 2)
        price_raw = stop.get("price")
        if cost > 0 and price_raw is not None:
            steps.append(
                {
                    "id": "stop",
                    "price": _price(price_raw),
                    "sell_cost_basis_usd": cost,
                    "order_ids": [],
                }
            )
    return steps


def _place_layers(
    *,
    trading,
    client,
    cfg,
    token_id: str,
    label: str,
    plan: dict[str, Any],
    layers: list[dict[str, float]],
    sell_steps: list[dict[str, Any]],
    lottery_cost: float,
    state_path: Path | None = None,
) -> dict[str, Any]:
    baseline_size, baseline_avg = _get_portfolio_position(cfg, token_id)
    state: dict[str, Any] = {
        "version": "grid-runner-0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "market_slug": plan["market_slug"],
        "market_title": plan.get("market_title", ""),
        "strategy_type": plan.get("strategy_type", ""),
        "strategy_name": plan.get("strategy_name", ""),
        "side": plan.get("side", ""),
        "token_id": token_id,
        "label": label,
        "baseline_position_size": baseline_size,
        "baseline_position_avg": baseline_avg,
        "lottery_cost_basis_usd": lottery_cost,
        "profit_lock_plan": plan.get("profit_lock_plan") or {},
        "layers": [],
        "sell_steps": sell_steps,
    }

    for layer in layers:
        existing = _has_matching_open_order(
            client, token_id, "BUY", layer["entry_price"], layer["shares"]
        )
        if existing is None:
            raise RuntimeError("could not confirm open orders before entry")
        layer_state = dict(layer)
        if existing:
            print(
                "[grid] skip BUY, matching open order already exists "
                f"{layer['shares']} @ {layer['entry_price']}"
            )
            layer_state["status"] = "existing_open_order"
        else:
            print(
                "[grid] placing BUY "
                f"{layer['shares']} @ {layer['entry_price']} ({layer['usdc']} USDC)"
            )
            try:
                response = trading.enter_position(
                    client, token_id, "BUY", layer["shares"], layer["entry_price"]
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[grid] BUY failed; preserving prior state and entering monitor: {exc}")
                layer_state["status"] = "failed"
                layer_state["error"] = str(exc)
                state["layers"].append(layer_state)
                if state_path is not None:
                    _save_state(state_path, state)
                break
            order_id = _order_id(response)
            if not order_id:
                raise RuntimeError(
                    "entry order submission did not return an order ID; "
                    "check open orders before retrying"
                )
            if not _verify_placed_order(client, order_id):
                print(
                    "[grid] BUY reported success but order NOT persisted on exchange "
                    "(INVALID/absent); marking failed. Re-verify with tools/check_open_orders.py"
                )
                layer_state["status"] = "failed"
                layer_state["error"] = "order not persisted on exchange (INVALID/absent)"
                state["layers"].append(layer_state)
                if state_path is not None:
                    _save_state(state_path, state)
                break
            layer_state["status"] = "submitted"
            layer_state["order_id"] = order_id
        state["layers"].append(layer_state)
        if state_path is not None:
            _save_state(state_path, state)
    return state


def _ensure_sell_coverage(trading, client, cfg, state: dict[str, Any]) -> bool:
    token_id = state["token_id"]
    lottery_cost = float(state.get("lottery_cost_basis_usd") or 0.0)
    changed = _reconcile_tracked_exit_orders(client, token_id, state)

    position_size: float | None = None
    avg_price_live: float | None = None
    try:
        position_size, avg_price_live = _get_portfolio_position(cfg, token_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[grid] portfolio position check failed; using order-status fallback: {exc}")

    buy_filled_size, buy_filled_cost = _tracked_buy_fill(client, token_id, state)
    if buy_filled_size <= 0 or buy_filled_cost <= 0:
        print("[grid] status no managed BUY fill yet")
        return False

    avg_entry = buy_filled_cost / buy_filled_size
    total_exit_filled = sum(
        _tracked_exit_fill_size(client, token_id, step)
        for step in state.get("sell_steps", [])
    )
    total_exit_open = sum(
        _tracked_exit_open_remaining(client, token_id, step)
        for step in state.get("sell_steps", [])
    )
    managed_remaining = _floor_size(max(0.0, buy_filled_size - total_exit_filled))
    available_unreserved = _floor_size(max(0.0, managed_remaining - total_exit_open))

    sellable_cost = max(0.0, buy_filled_cost - lottery_cost)
    desired_total_sell_size = _floor_size(sellable_cost / avg_entry) if avg_entry > 0 else 0.0
    print(
        "[grid] status "
        f"position={position_size} avg_live={avg_price_live} "
        f"managed_buy={buy_filled_size} avg_entry={avg_entry:.4f} "
        f"lottery_cost={lottery_cost} sellable_cost={sellable_cost:.2f} "
        f"filled_sell={total_exit_filled} open_sell={total_exit_open} "
        f"desired_sell={desired_total_sell_size} managed_remaining={managed_remaining} "
        f"available_unreserved={available_unreserved}"
    )
    if _floor_size(total_exit_filled + total_exit_open) >= _floor_size(desired_total_sell_size - 0.05):
        print("[grid] sell coverage already sufficient; no new SELL needed")
        return False

    remaining_cost = sellable_cost
    for step in state.get("sell_steps", []):
        step_cost = min(float(step["sell_cost_basis_usd"]), remaining_cost)
        remaining_cost = max(0.0, remaining_cost - step_cost)
        desired_size = _floor_size(step_cost / avg_entry) if avg_entry > 0 else 0.0
        if desired_size <= 0:
            continue

        covered = _floor_size(
            _tracked_exit_fill_size(client, token_id, step)
            + _tracked_exit_open_remaining(client, token_id, step)
        )
        missing = _floor_size(desired_size - covered)
        if missing <= 0.05:
            continue

        place_size = _floor_size(min(missing, available_unreserved))
        if place_size < MIN_CLOB_ORDER_SIZE:
            print(
                f"[grid] sell step {step['id']} skipped; "
                f"size {place_size} below minimum {MIN_CLOB_ORDER_SIZE}"
            )
            continue
        if place_size <= 0.05:
            print(f"[grid] sell step {step['id']} waiting; no unreserved position")
            continue

        price = float(step["price"])
        print(f"[grid] placing SELL {place_size} @ {price} for {step['id']}")
        try:
            response = trading.exit_position(client, token_id, "SELL", place_size, price)
        except Exception as exc:  # noqa: BLE001
            print(f"[grid] sell step {step['id']} failed; will keep existing state: {exc}")
            continue
        order_id = _order_id(response)
        if order_id:
            step.setdefault("order_ids", []).append(order_id)
        available_unreserved = _floor_size(available_unreserved - place_size)
        changed = True
    return changed


def _reconcile_tracked_exit_orders(client, token_id: str, state: dict[str, Any]) -> bool:
    """Attach matching live SELL orders to state after a previous partial failure."""
    changed = False
    open_orders = _safe_open_orders(client)
    for step in state.get("sell_steps", []):
        tracked = _state_order_ids(step, "order_ids")
        price = float(step["price"])
        for order in open_orders:
            if not _order_matches_token_side(order, token_id, "SELL"):
                continue
            order_id = _object_order_id(order)
            if not order_id or order_id in tracked:
                continue
            order_price = _to_float(order.get("price"))
            if not _close_enough(order_price, price, 0.005, 0.01):
                continue
            step.setdefault("order_ids", []).append(order_id)
            tracked.add(order_id)
            changed = True
            print(f"[grid] reconciled existing SELL {order_id} @ {price} into {step['id']}")
    return changed


def _tracked_buy_fill(client, token_id: str, state: dict[str, Any]) -> tuple[float, float]:
    total_size = 0.0
    total_cost = 0.0
    trades = _safe_trades(client)
    open_orders = _safe_open_orders(client)

    for layer in state.get("layers", []):
        order_id = str(layer.get("order_id") or "")
        if not order_id:
            continue
        entry_price = float(layer["entry_price"])
        target_size = float(layer["shares"])
        filled_candidates: list[float] = []

        for order in open_orders:
            if _object_order_id(order) != order_id:
                continue
            if _order_matches_token_side(order, token_id, "BUY"):
                filled_candidates.append(_filled_size_from_order(order))

        order = _get_order_with_retries(client, order_id)
        if order and _order_matches_token_side(order, token_id, "BUY"):
            filled_candidates.append(_filled_size_from_order(order))

        trade_size = 0.0
        for trade in trades:
            if not _trade_matches_order_ids(trade, {order_id}):
                continue
            if not _trade_matches_token_side(trade, token_id, "BUY"):
                continue
            trade_size += _trade_size(trade)
        filled_candidates.append(trade_size)

        filled = _floor_size(min(target_size, max(filled_candidates or [0.0])))
        total_size += filled
        total_cost += filled * entry_price
    return _floor_size(total_size), round(total_cost, 6)


def _tracked_exit_fill_size(client, token_id: str, step: dict[str, Any]) -> float:
    order_ids = _state_order_ids(step, "order_ids")
    if not order_ids:
        return 0.0
    filled = 0.0
    for order_id in order_ids:
        order = _get_order_with_retries(client, order_id)
        if order and _order_matches_token_side(order, token_id, "SELL"):
            filled += _filled_size_from_order(order)
    return _floor_size(filled)


def _tracked_exit_open_remaining(client, token_id: str, step: dict[str, Any]) -> float:
    order_ids = _state_order_ids(step, "order_ids")
    if not order_ids:
        return 0.0
    remaining = 0.0
    for order in _safe_open_orders(client):
        if _object_order_id(order) not in order_ids:
            continue
        if not _order_matches_token_side(order, token_id, "SELL"):
            continue
        original_size = _to_float(order.get("original_size") or order.get("size")) or 0.0
        matched_size = _to_float(order.get("size_matched")) or 0.0
        remaining += max(0.0, original_size - matched_size)
    return _floor_size(remaining)


def _assert_market_accepting_orders(slug: str) -> None:
    markets = _get_json_with_retries(
        "https://gamma-api.polymarket.com/markets", params={"slug": slug}
    )
    if not markets:
        raise RuntimeError(f"market slug not found: {slug}")
    market = markets[0]
    if market.get("closed") or not market.get("active") or not market.get("acceptingOrders"):
        raise RuntimeError(
            "market is not accepting orders: "
            f"active={market.get('active')} closed={market.get('closed')} "
            f"acceptingOrders={market.get('acceptingOrders')}"
        )


def _resolve_token_from_plan(bot_root: Path, plan: dict[str, Any]) -> str:
    sys.path.insert(0, str(bot_root))
    import market_resolver as resolver  # noqa: WPS433

    ev = resolver.resolve_slug(plan["market_slug"])
    side = str(plan["side"]).strip().lower()
    candidates: list[tuple[str, str, str]] = []
    for sub in ev.sub_markets:
        question = sub.question.lower()
        for outcome in sub.outcomes:
            outcome_name = outcome.outcome.lower()
            if side == outcome_name or side in outcome_name:
                candidates.append((outcome.token_id, sub.question, outcome.outcome))
            elif side in question and outcome_name in {"yes", "y"}:
                candidates.append((outcome.token_id, sub.question, outcome.outcome))

    if len(candidates) == 1:
        token_id, question, outcome = candidates[0]
        print(f"[grid] resolved token: {question} :: {outcome}")
        return token_id
    if not candidates:
        raise RuntimeError(f"could not resolve side '{plan['side']}' from slug {plan['market_slug']}")
    preview = "\n".join(f"- {q} :: {o} token={tid[:16]}…" for tid, q, o in candidates[:10])
    raise RuntimeError(f"side matched multiple outcomes; pass --token-id explicitly:\n{preview}")


def _get_portfolio_position(cfg, token_id: str) -> tuple[float, float]:
    if not cfg.funder:
        return (0.0, 0.0)
    data = _get_json_with_retries(
        "https://data-api.polymarket.com/positions",
        params={"user": cfg.funder, "limit": 200, "sizeThreshold": 0},
    )
    items = data if isinstance(data, list) else []
    for item in items:
        item_token_id = str(item.get("asset") or item.get("assetId") or item.get("tokenId") or "")
        if item_token_id == token_id:
            return float(item.get("size") or 0.0), float(item.get("avgPrice") or 0.0)
    return (0.0, 0.0)


def _get_json_with_retries(url: str, *, params: dict[str, Any], attempts: int = 4) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[grid] http check failed attempt={attempt}: {exc}")
            time.sleep(2)
    raise RuntimeError(f"http check failed after {attempts} attempts: {last_error}")


def _safe_open_orders(client) -> list[dict[str, Any]]:
    try:
        orders = client.get_open_orders()
    except Exception:
        return []
    return [_plain_dict(order) for order in orders or []]


def _safe_trades(client) -> list[dict[str, Any]]:
    try:
        trades = client.get_trades()
    except Exception:
        return []
    return [_plain_dict(trade) for trade in trades or []]


def _has_matching_open_order(client, token_id: str, side: str, price: float, size: float) -> bool | None:
    try:
        orders = client.get_open_orders()
    except Exception:
        return None
    for raw in orders or []:
        order = _plain_dict(raw)
        if not _order_matches_token_side(order, token_id, side):
            continue
        order_price = _to_float(order.get("price"))
        order_size = _to_float(order.get("original_size") or order.get("size"))
        if _close_enough(order_price, price, 0.005, 0.02) and _close_enough(order_size, size, 0.05, 0.02):
            return True
    return False


def _get_order_with_retries(client, order_id: str, *, attempts: int = 3) -> dict[str, Any] | None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _plain_dict(client.get_order(order_id))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[grid] get_order failed order_id={order_id} attempt={attempt}: {exc}")
            time.sleep(1)
    print(f"[grid] get_order unavailable order_id={order_id}: {last_error}")
    return None


def _order_matches_token_side(order: dict[str, Any], token_id: str, side: str) -> bool:
    order_token = str(
        order.get("asset_id")
        or order.get("token_id")
        or order.get("assetId")
        or order.get("tokenId")
        or order.get("asset")
        or order.get("market")
        or ""
    )
    order_side = str(order.get("side") or order.get("taker_side") or "").upper()
    return order_token == token_id and order_side == side.upper()


def _filled_size_from_order(order: dict[str, Any]) -> float:
    matched_size = _to_float(order.get("size_matched") or order.get("matched_size") or order.get("filled_size"))
    if matched_size is not None:
        return matched_size
    status = str(order.get("status") or "").upper()
    if status in {"MATCHED", "FILLED"}:
        return _to_float(order.get("original_size") or order.get("size")) or 0.0
    return 0.0


def _trade_matches_token_side(trade: dict[str, Any], token_id: str, side: str) -> bool:
    trade_token = str(
        trade.get("asset_id")
        or trade.get("token_id")
        or trade.get("asset")
        or trade.get("market")
        or ""
    )
    trade_side = str(trade.get("side") or trade.get("taker_side") or "").upper()
    return (not trade_token or trade_token == token_id) and (not trade_side or trade_side == side.upper())


def _trade_matches_order_ids(trade: dict[str, Any], order_ids: set[str]) -> bool:
    for key in ("order_id", "maker_order_id", "taker_order_id", "orderID"):
        if str(trade.get(key) or "") in order_ids:
            return True
    return False


def _trade_size(trade: dict[str, Any]) -> float:
    for key in ("size", "amount", "matched_size", "share_size"):
        value = _to_float(trade.get(key))
        if value is not None:
            return value
    return 0.0


def _state_order_ids(state: dict[str, Any], key: str) -> set[str]:
    return {str(order_id) for order_id in state.get(key, []) if order_id}


def _order_id(response: Any) -> str:
    if not isinstance(response, dict):
        return ""
    return str(response.get("orderID") or response.get("order_id") or response.get("id") or "")


def _verify_placed_order(client, order_id: str) -> bool:
    """Verify an order actually persisted on the exchange (not INVALID/absent).

    2026-08-05 reliability lesson: under network flakiness the SDK can return
    "success" for an order that never persisted (status INVALID). Always verify.
    """
    for attempt in range(3):
        try:
            order = client.get_order(order_id)
            order = order if isinstance(order, dict) else getattr(order, "__dict__", {})
            status = str(order.get("status") or "").upper()
            return bool(status and status != "INVALID")
        except Exception:
            time.sleep(2)
    return False


def _object_order_id(obj: dict[str, Any]) -> str:
    return str(obj.get("id") or obj.get("orderID") or obj.get("order_id") or "")


def _plain_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {"value": str(obj)}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_label(plan: dict[str, Any]) -> str:
    title = plan.get("market_title") or plan.get("market_slug") or "Polymarket"
    return f"{title} - {plan.get('side', '')}".strip(" -")


def _default_state_path(bot_root: Path, plan: dict[str, Any]) -> Path:
    raw = "-".join(
        str(x)
        for x in (
            plan.get("market_slug", "market"),
            plan.get("side", "side"),
            plan.get("strategy_type", "grid"),
        )
        if x
    )
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-").lower()
    return bot_root / ".runtime" / f"{name}.json"


def _print_plan_summary(
    plan: dict[str, Any],
    token_id: str,
    label: str,
    buy_layers: list[dict[str, float]],
    sell_steps: list[dict[str, Any]],
    lottery_cost: float,
    state_path: Path,
) -> None:
    print("[grid] plan")
    print(f"  market: {plan.get('market_title') or plan.get('market_slug')}")
    print(f"  side: {plan.get('side')}  token={token_id[:16]}…")
    print(f"  label: {label}")
    print("  buy ladders:")
    for layer in buy_layers:
        print(f"    BUY {layer['shares']} @ {layer['entry_price']} ({layer['usdc']} USDC)")
    print("  sell plan:")
    for step in sell_steps:
        tag = " (stop)" if step.get("id") == "stop" else ""
        print(f"    SELL cost {step['sell_cost_basis_usd']} USDC @ {step['price']}{tag}")
    print(f"  lottery cost basis: {lottery_cost} USDC")
    print(f"  state file: {state_path}")


def _price(value: Any) -> float:
    price = round(float(value), 4)
    if price <= 0 or price >= 1:
        raise ValueError(f"price must be between 0 and 1: {value}")
    return price


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _close_enough(actual: float | None, expected: float, min_abs: float, rel: float) -> bool:
    if actual is None:
        return False
    return abs(actual - expected) <= max(min_abs, abs(expected) * rel)


def _floor_size(value: float) -> float:
    return math.floor(max(0.0, value) * 100) / 100


if __name__ == "__main__":
    raise SystemExit(main())
