#!/usr/bin/env python3
"""1-minute bar monitor + strategy state engine (execution layer).

Design per STRATEGY_RESEARCH_HANDOFF.md section 7 (2026-08-08 confirmed):

- Every 60s fetch a narrow window (last ~15 minutes) of 1-minute bars via
  CLOB /prices-history?market=<TOKEN_ID>&startTs=..&endTs=..&interval=1d&fidelity=1
  (wide windows get down-sampled to 5-13 minutes; narrow windows return 60s bars).
- Strategy engine evaluates current state: which price zone we are in, whether to
  switch strategy, which resting limit orders to recommend.
- Only resting limit orders are ever recommended; never market-chase.
- 1-minute bars lag ~40-60s, so stop-loss / drawdown protection uses the real-time
  mid price from /book (a 98.5c -> 0.05c move takes ~1 minute; bars cannot catch it).

Safety:
- Default is dry-run: this tool NEVER places orders. It writes a recommended action
  queue (runtime/bar_monitor_actions.jsonl + latest snapshot) that a human or the
  execution session consumes. The only real order entry stays tools/grid_plan_runner.py.
- --execute: also build a pending trade_config and invoke grid_plan_runner with
  --dry-run (prints what would be placed, no orders).
- --execute-live: invoke grid_plan_runner WITHOUT dry-run. This places real resting
  orders and requires the user to explicitly confirm by passing this flag.
- Position cap and stop lines are read from config/strategy_templates.json and
  config/risk_limits.json; autopilot flag is respected (off -> dry-run only).

Usage:
    python3 tools/bar_monitor_runner.py --slug <event-slug> --strategy B_FAVORITE_DIP
    python3 tools/bar_monitor_runner.py --slug <slug> --outcome "Team A" --watch --interval 60
    python3 tools/bar_monitor_runner.py --history-file tests/fixtures/bar_*.json  # offline test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DEFAULT_STATE_DIR = ROOT / "runtime" / "bar_monitor_state"
DEFAULT_ACTION_FILE = ROOT / "runtime" / "bar_monitor_actions.jsonl"
DEFAULT_ACTION_SNAPSHOT = ROOT / "runtime" / "bar_monitor_actions.json"
DEFAULT_PENDING_DIR = ROOT / "runtime" / "bar_monitor_pending"
CLASSIFIER = ROOT / "tools" / "classify_pattern.py"
GRID_RUNNER = ROOT / "tools" / "grid_plan_runner.py"

# Strategies with template keys in config/strategy_templates.json.
STRATEGY_KEYS = ("A_DEEP_REVERSAL", "A_STANDARD_MID_REVERSAL", "B_FAVORITE_DIP")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def append_line(path: Path, line: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def http_json(url: str, tries: int = 6) -> Any:
    last: Exception | None = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polymarket-bar-monitor/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed public APIs
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry public reads
            last = exc
            time.sleep(1.0)
    raise RuntimeError(f"fetch fail {url}: {last}")


def parse_list(market: dict[str, Any], key: str) -> list[Any]:
    value = market.get(key)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return value or []


def is_winner_market(market: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(market.get(key) or "")
        for key in ("groupItemTitle", "question", "slug", "sportsMarketType")
    ).lower()
    if any(bad in haystack for bad in ("both teams", "slay baron", "slay a dragon", "destroy inhibitors", "quadra kill", "penta kill", "odd/even", "handicap", "total games", "team to win map")):
        return False
    return "winner" in haystack or "moneyline" in haystack


def fetch_event(slug: str) -> dict[str, Any]:
    data = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
    if isinstance(data, list) and data:
        return data[0]
    data = http_json(f"{GAMMA}/events/slug/{urllib.parse.quote(slug)}")
    return data if isinstance(data, dict) else {}


def fetch_price_points(token_id: str, start_ts: int, end_ts: int) -> list[dict[str, Any]]:
    for interval, fidelity in (("1d", 1), ("1m", 10)):
        params = urllib.parse.urlencode(
            {
                "market": token_id,
                "startTs": start_ts,
                "endTs": end_ts,
                "interval": interval,
                "fidelity": fidelity,
            }
        )
        try:
            data = http_json(f"{CLOB}/prices-history?{params}")
        except Exception:
            continue
        history = data.get("history") if isinstance(data, dict) else None
        if not isinstance(history, list):
            continue
        points = [
            {"t": int(item["t"]), "p": float(item["p"])}
            for item in history
            if isinstance(item, dict) and "t" in item and "p" in item
        ]
        points.sort(key=lambda item: item["t"])
        if len(points) >= 2:
            return points
    return []


def fetch_book(token_id: str) -> dict[str, Any]:
    data = http_json(f"{CLOB}/book?token_id={urllib.parse.quote(token_id)}")
    return data if isinstance(data, dict) else {}


def book_mid(book: dict[str, Any]) -> float | None:
    bids = [item for item in book.get("bids") or [] if isinstance(item, dict)]
    asks = [item for item in book.get("asks") or [] if isinstance(item, dict)]
    best_bid = max((float(item["price"]) for item in bids if float(item.get("price", 0)) > 0), default=None)
    best_ask = min((float(item["price"]) for item in asks if float(item.get("price", 0)) > 0), default=None)
    if best_bid is not None and best_ask is not None:
        return round((best_bid + best_ask) / 2, 4)
    if best_bid is not None:
        return best_bid
    return best_ask


def spread_cents(book: dict[str, Any]) -> float | None:
    bids = [float(item["price"]) for item in book.get("bids") or [] if isinstance(item, dict)]
    asks = [float(item["price"]) for item in book.get("asks") or [] if isinstance(item, dict)]
    best_bid = max(bids, default=None)
    best_ask = min(asks, default=None)
    if best_bid is not None and best_ask is not None:
        return round((best_ask - best_bid) * 100, 2)
    return None


def bar_stats(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not points:
        return None
    prices = [float(p["p"]) for p in points]
    min_i = min(range(len(prices)), key=lambda i: prices[i])
    stats: dict[str, Any] = {
        "first": prices[0],
        "last": prices[-1],
        "min": prices[min_i],
        "max": max(prices),
        "window_minutes": round((points[-1]["t"] - points[0]["t"]) / 60, 1),
        "rebound_from_min": round(max(prices[min_i:]) - prices[min_i], 4),
        "last_change": round(prices[-1] - prices[-2], 4) if len(prices) >= 2 else 0.0,
        "points": len(prices),
    }
    return stats


def load_templates() -> dict[str, Any]:
    return load_json(ROOT / "config" / "strategy_templates.json")


def load_risk_limits() -> dict[str, Any]:
    return load_json(ROOT / "config" / "risk_limits.json")


def strategy_config(strategy_key: str) -> dict[str, Any]:
    templates = load_templates()
    template = templates["strategies"][strategy_key]
    risk = load_risk_limits()
    budget_row = risk.get("strategy_budgets", {}).get(strategy_key, {})
    cap = float(risk.get("global", {}).get("max_single_market_budget_usd", 80))
    budget = float(budget_row.get("default_cycle_budget_usd") or template.get("default_cycle_budget_usd") or 50)
    max_cycle = float(budget_row.get("max_cycle_budget_usd") or cap)
    budget = min(budget, max_cycle)
    ladders = template.get("standard_buy_ladders") or []
    total = sum(float(item.get("amount_usd") or 0) for item in ladders)
    scale = budget / total if total > 0 else 1.0
    buy_ladders = [
        {"price": float(item["price"]), "amount_usd": round(float(item["amount_usd"]) * scale, 2)}
        for item in ladders
    ]
    return {
        "key": strategy_key,
        "name": template.get("name", strategy_key),
        "budget": budget,
        "buy_ladders": buy_ladders,
        "sell_plan": template.get("standard_sell_plan") or [],
        "lottery_cost_basis_usd": float(template.get("lottery_cost_basis_usd") or 0),
        "no_entry_below": float(template.get("stop_new_entry_below") or 0),
        "no_entry_above": float(template.get("stop_new_entry_above") or 0.95),
        "spread_max_cents": float(load_risk_limits().get("market_filters", {}).get("max_spread_cents", 6)),
    }


def entry_zone(cfg: dict[str, Any]) -> tuple[float, float]:
    """Entry zone derived from the buy ladder extremes for the strategy."""
    prices = [item["price"] for item in cfg["buy_ladders"]]
    return (min(prices), max(prices))


def target_key(market: dict[str, Any], outcome: str) -> str:
    return f"{market.get('slug') or market.get('id') or '?'}|{outcome}"


def build_targets(event: dict[str, Any], only_outcome: str | None) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for market in event.get("markets") or []:
        if not isinstance(market, dict) or not is_winner_market(market):
            continue
        if market.get("closed") or market.get("active") is False:
            continue
        outcomes = [str(o) for o in parse_list(market, "outcomes")]
        tokens = [str(t) for t in parse_list(market, "clobTokenIds")]
        if not outcomes or len(outcomes) != len(tokens):
            continue
        for outcome, token_id in zip(outcomes, tokens):
            if only_outcome and outcome != only_outcome:
                continue
            targets.append(
                {
                    "market_slug": str(market.get("slug") or ""),
                    "market_title": str(market.get("groupItemTitle") or market.get("question") or ""),
                    "outcome": outcome,
                    "token_id": token_id,
                }
            )
    return targets


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = load_json(path)
            if isinstance(data, dict) and "targets" in data:
                return data
        except Exception:
            pass
    return {"version": 1, "slug": "", "targets": {}}


def action_key(action: str, side: str, price: float | None = None) -> str:
    return f"{action}|{side}|{price or ''}"


def tag_pattern(points: list[dict[str, Any]], market_type: str, side: str, window_path: Path) -> list[str]:
    """Classify the current bar window via tools/classify_pattern.py (subprocess, no cross-chain import)."""
    try:
        window_path.parent.mkdir(parents=True, exist_ok=True)
        with window_path.open("w", encoding="utf-8") as f:
            for point in points:
                row = {
                    "timestamp": datetime.fromtimestamp(point["t"], timezone.utc).isoformat(),
                    "price": float(point["p"]),
                }
                f.write(json.dumps(row) + "\n")
        result = subprocess.run(
            [
                sys.executable,
                str(CLASSIFIER),
                "--file",
                str(window_path),
                "--side",
                side,
                "--market-type",
                market_type,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return [str(label) for label in data.get("labels") or []]
    except Exception:  # noqa: BLE001 - tagging is best-effort
        return []


def market_type_of_target(target: dict[str, Any]) -> str:
    haystack = f"{target.get('market_slug') or ''} {target.get('market_title') or ''}".lower()
    return "moneyline" if "moneyline" in haystack else "game"


def build_trade_config(
    cfg: dict[str, Any],
    target: dict[str, Any],
    mid: float | None,
    place_buy_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a grid_plan_runner-compatible trade_config from current buy actions."""
    strategy_type = "A_DEEP_REVERSAL" if cfg["key"] == "A_STANDARD_MID_REVERSAL" else cfg["key"]
    config: dict[str, Any] = {
        "version": "mvp-0.2",
        "mode": "config_only",
        "amount_mode": "fixed_usd",
        "market_slug": target["market_slug"],
        "market_title": target["market_title"],
        "side": target["outcome"],
        "strategy_type": strategy_type,
        "current_price": mid,
        "match_budget": cfg["budget"],
        "cycle_budget": cfg["budget"],
        "buy_ladders": [
            {"price": float(action["price"]), "amount_usd": float(action["amount_usd"])}
            for action in place_buy_actions
        ],
        "sell_plan": [
            {"price": float(sell["price"]), "sell_cost_basis_usd": float(sell["sell_cost_basis_usd"])}
            for sell in cfg["sell_plan"]
        ],
        "lottery_cost_basis_usd": cfg["lottery_cost_basis_usd"],
        "max_cycles": 1,
        "stop_new_entry_below": cfg["no_entry_below"],
        "stop_new_entry_above": cfg["no_entry_above"],
        "operator_note": "由 bar_monitor_runner --execute 生成，人工确认后执行（resting 限价单，不市价追）。",
    }
    # D3: 非彩票型策略在计划里带交易所级止损卖单（monitor 成交后自动挂出）。
    if cfg["key"] in ("B_FAVORITE_DIP", "A_STANDARD_MID_REVERSAL"):
        config["stop_loss"] = {
            "price": cfg["no_entry_below"],
            "sell_cost_basis_usd": round(cfg["budget"], 2),
        }
    return config


def invoke_grid_runner(config_path: Path, token_id: str, label: str, live: bool) -> bool:
    """Invoke tools/grid_plan_runner.py (the only real order entry)."""
    cmd = [
        sys.executable,
        str(GRID_RUNNER),
        "--plan",
        str(config_path),
        "--token-id",
        token_id,
        "--label",
        label,
        "--place-only",
    ]
    if not live:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def plan_fingerprint(cfg: dict[str, Any], target: dict[str, Any], mid: float | None, buys: list[dict[str, Any]]) -> str:
    payload = {
        "strategy": cfg["key"],
        "market_slug": target["market_slug"],
        "outcome": target["outcome"],
        "buy_ladders": [[float(a["price"]), float(a["amount_usd"])] for a in buys],
        "mid": mid,
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()  # noqa: S324 - dedupe key only


def count_active_plans(state_dir: Path) -> int:
    """Count markets with a pending plan or an estimated position across state files."""
    if not state_dir.exists():
        return 0
    active = 0
    for path in state_dir.glob("*.json"):
        try:
            data = load_json(path)
        except Exception:  # noqa: BLE001
            continue
        for target_state in (data.get("targets") or {}).values():
            if target_state.get("pending_plan") or float(target_state.get("spent_usd") or 0) > 0:
                active += 1
    return active


def spawn_monitor(config_path: Path, token_id: str) -> int:
    """Start grid_plan_runner monitor mode in the background (fills -> TP + stop sells)."""
    cmd = [
        sys.executable,
        str(GRID_RUNNER),
        "--plan",
        str(config_path),
        "--token-id",
        token_id,
        "--monitor-only",
        "--skip-market-check",
    ]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return process.pid


def confirm_live(args: argparse.Namespace) -> bool:
    """Explicit human confirmation before placing real-money orders."""
    if args.yes:
        return True
    if not sys.stdin.isatty():
        print("[bar_monitor] 非交互环境无法确认；真实下单请加 --yes 显式确认")
        return False
    answer = input(
        "[bar_monitor] 即将使用真实资金挂单（resting 买单 + 成交后止盈/止损卖单）。\n"
        "输入 yes 确认，其它任意输入取消："
    ).strip().lower()
    return answer == "yes"


def run_engine(
    cfg: dict[str, Any],
    stats: dict[str, Any],
    mid: float | None,
    spread: float | None,
    target_state: dict[str, Any],
    now: datetime,
    quiet: bool,
) -> list[dict[str, Any]]:
    """Run the strategy state machine for one side of one market. Returns actions."""
    actions: list[dict[str, Any]] = []
    zone_min, zone_max = entry_zone(cfg)
    stop_below = cfg["no_entry_below"]
    above = cfg["no_entry_above"]
    budget = cfg["budget"]
    spent = float(target_state.get("spent_usd") or 0)
    last_zone = target_state.get("last_zone") or "unknown"
    filled_prices = {float(level.get("price")) for level in target_state.get("filled_levels") or []}

    def add(
        action: str,
        price: float | None = None,
        side: str = "buy",
        reason: str = "",
        amount_usd: float | None = None,
    ) -> None:
        key = action_key(action, side, price)
        if key == target_state.get("last_action_key") and target_state.get("last_zone") == last_zone:
            return
        row: dict[str, Any] = {
            "ts": now.isoformat(),
            "ts_epoch": int(now.timestamp()),
            "action": action,
            "side": side,
            "price": price,
            "zone": last_zone,
            "mid": mid,
            "last_bar": stats["last"],
            "window_min": stats["min"],
            "window_max": stats["max"],
            "rebound_from_min": stats["rebound_from_min"],
            "spent_usd": round(spent, 2),
            "budget_usd": budget,
            "reason": reason,
        }
        if amount_usd is not None:
            row["amount_usd"] = amount_usd
        actions.append(row)
        target_state["last_action_key"] = key

    # Liquidity gate first.
    if mid is None:
        target_state["last_zone"] = "no_book"
        add("skip_liquidity", reason="实时盘口缺失，不产生下单动作")
        return actions
    if spread is not None and spread > cfg["spread_max_cents"]:
        target_state["last_zone"] = "spread_too_wide"
        add("skip_liquidity", reason=f"spread {spread}c 超过上限 {cfg['spread_max_cents']}c")
        return actions

    zone = "above_entry"
    if mid <= stop_below:
        zone = "below_stop"
    elif mid >= above:
        zone = "terminal_high"
    elif zone_min <= mid <= zone_max:
        zone = "in_entry"
    elif mid < zone_min:
        zone = "below_entry"
    target_state["last_zone"] = zone

    if zone == "below_stop":
        add("stop_new_entry", reason=f"实时中间价 {mid} 跌破止损线 {stop_below}")
        if cfg["key"] == "B_FAVORITE_DIP":
            add("switch_to_s1_eval", reason="S2 热门跌破止损线，重新评估是否切 S1 深反")
        return actions
    if zone == "terminal_high":
        add("no_entry_high", reason=f"实时中间价 {mid} 接近封顶（>= {above}），不新开")
        return actions

    # Rebound / rally signals for deep reversal (lottery machine trigger layer).
    if stats["min"] < 0.10:
        if stats["last_change"] >= 0.10:
            add("single_bar_rally", reason=f"极低位（min {stats['min']}）单根 bar 拉升 {stats['last_change']}")
        if stats["rebound_from_min"] >= 0.15:
            add("rebound_confirmed", reason=f"极低位（min {stats['min']}）累计反弹 {stats['rebound_from_min']} >= 15c")

    if zone == "in_entry":
        remaining = budget - spent
        for level in cfg["buy_ladders"]:
            price = level["price"]
            amount = level["amount_usd"]
            if price in filled_prices:
                continue  # never re-recommend a level that already filled (no repeat buys).
            if price >= mid:
                continue  # resting buy must stay below the current mid, never market-chase.
            if amount > remaining + 1e-6:
                add("budget_capped", price=price, reason=f"剩余预算 {remaining:.2f} 不足以覆盖 {price} 档")
                break
            add(
                "place_buy",
                price=price,
                amount_usd=amount,
                reason=f"进入买入区 {zone_min}-{zone_max}，挂 resting 买单 {price}",
            )
            target_state.setdefault("active_buy_levels", []).append(
                {"price": price, "amount_usd": amount, "ts": now.isoformat()}
            )

    # Estimated fills: if the real-time mid crossed below an active resting buy level,
    # treat it as a (simulated) fill for position/stop accounting.
    active = target_state.get("active_buy_levels") or []
    remaining_active: list[dict[str, Any]] = []
    for level in active:
        if mid is not None and mid <= level["price"]:
            target_state["spent_usd"] = round(spent + level["amount_usd"], 2)
            target_state.setdefault("filled_levels", []).append(
                {"price": level["price"], "amount_usd": level["amount_usd"], "ts": now.isoformat()}
            )
            filled_prices.add(level["price"])
            add("estimated_fill", price=level["price"], reason=f"中间价 {mid} 穿至 {level['price']} 档，估算成交")
        else:
            remaining_active.append(level)
    target_state["active_buy_levels"] = remaining_active

    # Take-profit / D2 protection only when we hold an estimated position.
    if spent > 0 and mid is not None:
        for sell in cfg["sell_plan"]:
            sell_price = float(sell["price"])
            if mid >= sell_price:
                add("place_take_profit", price=sell_price, side="sell", reason=f"中间价 {mid} 到达止盈档 {sell_price}")
        if mid >= 0.60:
            add("d2_profit_lock_zone", reason=f"中间价 {mid} 进入 D2 锁盈区（>=60c），剩余仓位按彩票仓管理")

    # D3 / D2 trailing protection (only when holding an estimated position).
    spent_now = float(target_state.get("spent_usd") or 0)
    high = float(target_state.get("high_water") or 0)
    if mid is not None:
        high = max(high, mid)
        target_state["high_water"] = high
    d3 = str(target_state.get("d3_state") or "normal")
    stop_price = None
    if spent_now > 0 and mid is not None:
        if cfg["key"] == "A_DEEP_REVERSAL":
            if high >= 0.85:
                stop_price = 0.75
            elif high >= 0.70:
                stop_price = 0.58
        else:
            if high >= 0.80:
                stop_price = 0.72
            elif high >= 0.75:
                stop_price = 0.68
        if stop_price is not None:
            if mid <= stop_price:
                if d3 != "stop_triggered":
                    target_state["d3_state"] = "stop_triggered"
                    add("d3_stop_triggered", side="sell", reason=f"中间价 {mid} 跌破跟踪止损 {stop_price}（高位 {high}）")
                if zone == "in_entry":
                    add("re_entry_eval", reason="止损后重新评估：形态符合则用新预算独立进场，成本不继承")
            elif d3 != "protection":
                target_state["d3_state"] = "protection"
                add("d2_trailing_active", reason=f"浮盈保护激活：高位 {high}，跟踪止损 {stop_price}")

    if spent_now >= budget:
        add("budget_capped", reason=f"已用预算 {spent_now:.2f} 达到上限 {budget}")
    return actions


def load_offline(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    history = load_json(Path(args.history_file))
    points = history.get("points") if isinstance(history, dict) else history
    if not isinstance(points, list):
        raise ValueError("--history-file 需要 {\"points\": [{\"t\": epoch, \"p\": price}]}")
    book = {}
    if args.book_file:
        book = load_json(Path(args.book_file))
        if not isinstance(book, dict):
            book = {}
    target = {
        "market_slug": args.slug or "offline-test",
        "market_title": "offline",
        "outcome": args.outcome or "side-a",
        "token_id": "offline-token",
    }
    return [target], {"points": points, "book": book}


def process_target(
    target: dict[str, Any],
    points: list[dict[str, Any]],
    book: dict[str, Any],
    cfg: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
    quiet: bool,
    source: str,
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    key = target_key({"slug": target["market_slug"]}, target["outcome"])
    tstate = state["targets"].setdefault(
        key,
        {
            "strategy": cfg["key"],
            "spent_usd": 0.0,
            "active_buy_levels": [],
            "filled_levels": [],
            "last_zone": "unknown",
        },
    )
    stats = bar_stats(points)
    if stats is None:
        return []
    mid = book_mid(book)
    spread = spread_cents(book)
    actions = run_engine(cfg, stats, mid, spread, tstate, now, quiet)
    if len(points) >= 3 and not getattr(args, "no_tag", False):
        pattern_labels = tag_pattern(
            points,
            market_type_of_target(target),
            target["outcome"],
            Path(args.state_dir) / f"{state['slug']}__window.jsonl",
        )
        if pattern_labels:
            tstate["last_pattern_labels"] = pattern_labels
    pattern_labels = tstate.get("last_pattern_labels") or []
    for action in actions:
        action["event_slug"] = state["slug"]
        action["market_slug"] = target["market_slug"]
        action["market_title"] = target["market_title"]
        action["outcome"] = target["outcome"]
        action["strategy"] = cfg["key"]
        action["source"] = source
        action["pattern_labels"] = pattern_labels

    buys = [a for a in actions if a["action"] == "place_buy"] if actions else []

    # Manual dry-run path (no autopilot): print what grid_plan_runner would place.
    if args.execute and not args.autopilot and buys:
        pending_dir = Path(args.pending_dir)
        pending_dir.mkdir(parents=True, exist_ok=True)
        config_path = (
            pending_dir
            / f"{state['slug']}__{target['market_slug']}__{target['outcome']}.json"
        )
        write_json(config_path, build_trade_config(cfg, target, mid, buys))
        label = f"{state['slug']}-{target['outcome']}"
        ok = invoke_grid_runner(config_path, target["token_id"], label, live=False)
        print(
            f"[bar_monitor] execute dry-run for {target['market_slug']} "
            f"{target['outcome']}: {'OK' if ok else 'FAILED'}"
        )

    # Autopilot: signal -> plan -> dry-run -> pending confirmation (no orders yet).
    if args.autopilot and buys:
        risk = load_risk_limits()
        ap = risk.get("autopilot") or {}
        if not ap.get("enabled"):
            print(f"[bar_monitor] autopilot 未开启（enabled=false），仅信号不下单：{target['outcome']}")
        elif cfg["key"] not in (ap.get("allowed_strategies") or []):
            print(f"[bar_monitor] autopilot 不允许策略 {cfg['key']}，仅信号：{target['outcome']}")
        elif float(tstate.get("spent_usd") or 0) >= cfg["budget"]:
            print(f"[bar_monitor] 预算已满，仅信号：{target['outcome']}")
        else:
            pending = tstate.get("pending_plan") or {}
            fingerprint = plan_fingerprint(cfg, target, mid, buys)
            if (
                pending.get("fingerprint") == fingerprint
                and Path(str(pending.get("config_path") or "")).exists()
            ):
                print(f"[bar_monitor] 待确认计划已存在，跳过重复生成：{target['outcome']}")
            else:
                max_concurrent = int(risk.get("global", {}).get("max_concurrent_markets", 3))
                if count_active_plans(Path(args.state_dir)) >= max_concurrent:
                    print(f"[bar_monitor] 并发市场已达上限 {max_concurrent}，仅信号：{target['outcome']}")
                else:
                    pending_dir = Path(args.pending_dir)
                    pending_dir.mkdir(parents=True, exist_ok=True)
                    config_path = (
                        pending_dir
                        / f"{state['slug']}__{target['market_slug']}__{target['outcome']}.json"
                    )
                    write_json(config_path, build_trade_config(cfg, target, mid, buys))
                    label = f"{state['slug']}-{target['outcome']}"
                    ok = invoke_grid_runner(config_path, target["token_id"], label, live=False)
                    if ok:
                        tstate["pending_plan"] = {
                            "fingerprint": fingerprint,
                            "config_path": str(config_path),
                            "ts": now.isoformat(),
                            "status": "awaiting_confirmation",
                        }
                        print(
                            f"[bar_monitor] 待确认计划已生成：{config_path}\n"
                            f"  确认执行：python3 tools/bar_monitor_runner.py --history-file ... "
                            f"--execute-live --slug {state['slug']} --outcome {target['outcome']} "
                            f"--strategy {cfg['key']}"
                        )

    # Confirmed execution: place the pending plan live, then auto-start monitor.
    if args.execute_live:
        pending = tstate.get("pending_plan") or {}
        config_path = Path(str(pending.get("config_path") or ""))
        risk = load_risk_limits()
        ap = risk.get("autopilot") or {}
        if not ap.get("enabled"):
            print("[bar_monitor] --execute-live 需要 autopilot 开启（risk_limits.autopilot.enabled=true）")
        elif pending.get("status") != "awaiting_confirmation" or not config_path.exists():
            print("[bar_monitor] 没有待确认计划；先跑 --autopilot 生成计划并确认")
        elif not confirm_live(args):
            print("[bar_monitor] 已取消真实下单（未确认）")
        else:
            label = f"{state['slug']}-{target['outcome']}"
            ok = invoke_grid_runner(config_path, target["token_id"], label, live=True)
            if ok:
                tstate["pending_plan"]["status"] = "executed"
                pid = spawn_monitor(config_path, target["token_id"])
                tstate["monitor_pid"] = pid
                print(
                    f"[bar_monitor] 已挂单并拉起 monitor（pid={pid}）；"
                    f"成交后自动配止盈 + 止损卖单"
                )
    return actions


def replay_series(
    target: dict[str, Any],
    points: list[dict[str, Any]],
    cfg: dict[str, Any],
    state: dict[str, Any],
    now: datetime,
    quiet: bool,
    source: str,
    args: argparse.Namespace,
    window_points: int = 15,
    step: int = 5,
) -> list[dict[str, Any]]:
    """Replay a full price series through the engine with rolling windows.

    Simulates the monitor across the whole match: fills accumulate, D3 state
    machine and trailing stops can trigger, and the final state file reflects
    the full lifecycle. Used for historical validation (no network needed).
    """
    all_actions: list[dict[str, Any]] = []
    for i in range(0, len(points), step):
        window = points[max(0, i - window_points + 1) : i + 1]
        if len(window) < 3:
            continue
        last = float(window[-1]["p"])
        book = {
            "bids": [{"price": round(max(0.0, last - 0.005), 4), "size": 1}],
            "asks": [{"price": round(min(1.0, last + 0.005), 4), "size": 1}],
        }
        actions = process_target(
            target, window, book, cfg, state, now, quiet, source, args
        )
        all_actions.extend(actions)
    return all_actions


def main() -> int:
    parser = argparse.ArgumentParser(description="1-minute bar monitor + strategy state engine")
    parser.add_argument("--slug", default="", help="Event slug to monitor (live mode).")
    parser.add_argument("--outcome", default="", help="Only monitor this outcome (team name).")
    parser.add_argument("--strategy", choices=STRATEGY_KEYS, default="B_FAVORITE_DIP")
    parser.add_argument("--watch", action="store_true", help="Keep polling every --interval seconds.")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval seconds (default 60).")
    parser.add_argument("--window-minutes", type=int, default=15, help="Sliding window size (default 15).")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="State directory.")
    parser.add_argument("--action-file", default=str(DEFAULT_ACTION_FILE), help="Action JSONL output.")
    parser.add_argument(
        "--pending-dir",
        default=str(DEFAULT_PENDING_DIR),
        help="Pending trade_config output dir (used with --execute).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Build pending trade config + invoke grid_plan_runner with --dry-run (no orders).",
    )
    parser.add_argument(
        "--execute-live",
        action="store_true",
        help="Invoke grid_plan_runner WITHOUT --dry-run. REAL RESTING ORDERS; explicit confirmation required.",
    )
    parser.add_argument(
        "--autopilot",
        action="store_true",
        help="V2 autopilot: signal -> plan -> dry-run -> pending confirmation "
        "(requires risk_limits.autopilot.enabled=true; no orders until --execute-live).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="真实下单时跳过交互确认（仅 --execute-live 用；非交互环境必须加）。",
    )
    parser.add_argument("--history-file", default="", help="Offline replay: JSON with points+optional book.")
    parser.add_argument("--book-file", default="", help="Offline replay: book snapshot JSON.")
    parser.add_argument(
        "--replay-series",
        action="store_true",
        help="Offline validation: replay the full series through rolling windows "
        "(fills + D3 state machine accumulate).",
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip pattern tagging (faster replay; live/single-pass keeps tags).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress per-action stdout.")
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    action_file = Path(args.action_file)
    cfg = strategy_config(args.strategy)
    offline = bool(args.history_file)

    if not offline and not args.slug:
        parser.error("live 模式需要 --slug；离线测试用 --history-file")

    while True:
        now = datetime.now(timezone.utc)
        if offline:
            targets, offline_data = load_offline(args)
            slug = args.slug or "offline"
        else:
            event = fetch_event(args.slug)
            if not event:
                print(f"[bar_monitor] event not found: {args.slug}")
                return 2
            slug = args.slug
            targets = build_targets(event, args.outcome or None)

        state_path = state_dir / f"{slug}.json"
        state = load_state(state_path)
        state["slug"] = slug
        all_actions: list[dict[str, Any]] = []

        if offline:
            for target in targets:
                if args.replay_series:
                    actions = replay_series(
                        target,
                        offline_data["points"],
                        cfg,
                        state,
                        now,
                        args.quiet,
                        "series-replay",
                        args,
                    )
                else:
                    actions = process_target(
                        target,
                        offline_data["points"],
                        offline_data["book"],
                        cfg,
                        state,
                        now,
                        args.quiet,
                        "offline-replay",
                        args,
                    )
                all_actions.extend(actions)
        else:
            end_ts = int(now.timestamp())
            start_ts = end_ts - args.window_minutes * 60
            for target in targets:
                try:
                    points = fetch_price_points(target["token_id"], start_ts, end_ts)
                    book = fetch_book(target["token_id"])
                except Exception as exc:  # noqa: BLE001 - skip a single market, keep going
                    print(f"[bar_monitor] skip {target['market_slug']} {target['outcome']}: {exc}")
                    continue
                actions = process_target(
                    target, points, book, cfg, state, now, args.quiet, "gamma-poll", args
                )
                all_actions.extend(actions)

        write_json(state_path, state)
        for action in all_actions:
            append_line(action_file, action)
            if not args.quiet:
                print(json.dumps(action, ensure_ascii=False))
        if all_actions:
            write_json(ROOT / "runtime" / "bar_monitor_actions.json", all_actions[-1])
        print(f"[bar_monitor] pass done: {len(all_actions)} action(s), {len(targets)} target(s)")

        if offline or not args.watch:
            break
        time.sleep(max(10, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
