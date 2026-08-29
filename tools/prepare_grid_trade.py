#!/usr/bin/env python3
"""Prepare a fixed-USD grid trade from a Polymarket URL.

This script is the task-1 glue layer:

URL + Game/Map + Strategy
-> resolve the Polymarket market
-> pick the sub-market and side
-> generate a trade plan
-> create one-click run / monitor / status launchers

It does not place orders by itself.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/Users/ad/Documents/polymarket")
BOT_ROOT = Path("/Users/ad/Documents/polydata/polymarket_trading_bot_strategy")
BOT_PYTHON = BOT_ROOT / ".venv/bin/python"
RUNNER = PROJECT_ROOT / "tools/grid_plan_runner.py"
SUMMARY = PROJECT_ROOT / "tools/grid_status_summary.py"
CANCEL = PROJECT_ROOT / "tools/cancel_grid_orders.py"
REVIEW = PROJECT_ROOT / "tools/create_trade_review.py"
RUNTIME = PROJECT_ROOT / "runtime"
LOGS = RUNTIME / "logs"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a Polymarket grid trade plan.")
    parser.add_argument("--url", "--market-url", dest="url", required=True)
    parser.add_argument(
        "--strategy",
        default="auto",
        choices=["auto", "A", "B", "C", "D", "a", "b", "c", "d"],
        help="A/B executable strategies, C/D advisory-only, or auto.",
    )
    parser.add_argument("--game", type=int, help="Pick Game N winner market.")
    parser.add_argument("--map", dest="map_no", type=int, help="Pick Map N winner market.")
    parser.add_argument("--keyword", default="", help="Manual keyword for sub-market question/slug.")
    parser.add_argument("--submarket-index", type=int, help="Use a specific resolved sub-market index.")
    parser.add_argument("--side", default="", help="Outcome/team to buy. If omitted, choose by strategy.")
    parser.add_argument("--note", "--description", dest="note", default="", help="Natural-language match/trade note.")
    parser.add_argument("--match-budget", type=float, default=100.0)
    parser.add_argument("--cycle-budget", type=float, default=25.0)
    parser.add_argument("--pre-match-price", type=float)
    parser.add_argument("--name", default="", help="Stable runtime name.")
    parser.add_argument(
        "--allow-experimental",
        action="store_true",
        help="Allow C experimental pilot execution plan generation. D remains advisory-only.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(BOT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "tools"))

    import market_resolver  # noqa: WPS433
    import grid_config_generator as generator  # noqa: WPS433

    event = market_resolver.resolve_slug(args.url, fetch_book=False)
    sub_index, sub = _pick_submarket(event, args)
    _fill_selected_books(market_resolver, sub)
    side_pick = _pick_side(sub, args.side, args.strategy, args.note)
    current_price = _execution_price(side_pick["outcome"])
    strategy_code, strategy_reason = _pick_strategy(args.strategy, args.note, current_price, args.pre_match_price)

    name = args.name or _slugify(
        "-".join(
            [
                event.slug,
                sub.market_slug or sub.question,
                side_pick["outcome"].outcome,
                strategy_code,
            ]
        )
    )

    if strategy_code == "D" or (strategy_code == "C" and not args.allow_experimental):
        advisory_path = RUNTIME / f"{name}_advisory.json"
        RUNTIME.mkdir(parents=True, exist_ok=True)
        advisory = {
            "version": "advisory-0.1",
            "event_slug": event.slug,
            "event_title": event.title,
            "market_slug": sub.market_slug,
            "market_title": sub.question,
            "side": side_pick["outcome"].outcome,
            "current_price": current_price,
            "strategy_code": strategy_code,
            "strategy_status": "advisory_only",
            "strategy_reason": strategy_reason,
            "operator_note": args.note,
            "next_step": _advisory_next_step(strategy_code),
            "resolved": {
                "submarket_index": sub_index,
                "token_id": side_pick["outcome"].token_id,
                "best_bid": side_pick["outcome"].best_bid,
                "best_ask": side_pick["outcome"].best_ask,
                "gamma_price": side_pick["outcome"].current_price,
            },
        }
        advisory_path.write_text(json.dumps(advisory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _print_advisory(advisory, advisory_path)
        return 0

    if strategy_code == "A":
        strategy_config = generator.strategy_a_deep_reversal(current_price, args.cycle_budget)
    elif strategy_code == "B":
        strategy_config = generator.strategy_b_favorite_dip(
            current_price,
            args.pre_match_price,
            args.cycle_budget,
        )
    elif strategy_code == "C":
        strategy_config = generator.strategy_c_dominant_compounder(current_price, args.cycle_budget)
        strategy_reason = f"{strategy_reason} 已开启 --allow-experimental，生成C型小额试单计划。"
    else:
        raise SystemExit(f"策略 {strategy_code} 暂不支持执行计划。")

    plan = {
        "version": "mvp-0.1",
        "mode": "config_only",
        "market_slug": sub.market_slug,
        "market_title": sub.question,
        "event_slug": event.slug,
        "event_title": event.title,
        "side": side_pick["outcome"].outcome,
        "league": "",
        "current_price": current_price,
        "pre_match_price": args.pre_match_price,
        "match_budget": round(args.match_budget, 2),
        "cycle_budget": round(args.cycle_budget, 2),
        "operator_note": side_pick["reason"],
        "strategy_inference": {
            "requested_strategy": args.strategy,
            "strategy_code": strategy_code,
            "reason": strategy_reason,
            "note": args.note,
        },
        "resolved": {
            "event_id": event.event_id,
            "event_slug": event.slug,
            "event_title": event.title,
            "submarket_index": sub_index,
            "submarket_slug": sub.market_slug,
            "submarket_question": sub.question,
            "condition_id": sub.condition_id,
            "side_outcome_index": side_pick["outcome"].outcome_index,
            "token_id": side_pick["outcome"].token_id,
            "best_bid": side_pick["outcome"].best_bid,
            "best_ask": side_pick["outcome"].best_ask,
            "gamma_price": side_pick["outcome"].current_price,
        },
        **strategy_config,
    }

    plan_path = RUNTIME / f"{name}.json"
    state_path = BOT_ROOT / ".runtime" / f"{name}.json"
    run_path = RUNTIME / f"run_{name}.command"
    monitor_path = RUNTIME / f"monitor_{name}.command"
    status_path = RUNTIME / f"status_{name}.command"
    close_path = RUNTIME / f"close_{name}.command"
    review_path = RUNTIME / f"review_{name}.command"

    RUNTIME.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_run_launcher(run_path, plan, plan_path, state_path, side_pick["outcome"].token_id, name)
    _write_monitor_launcher(monitor_path, plan, plan_path, state_path, side_pick["outcome"].token_id, name)
    _write_status_launcher(status_path, state_path, name)
    _write_close_launcher(close_path, state_path, name)
    _write_review_launcher(review_path, state_path, name)

    _print_summary(plan, plan_path, state_path, run_path, monitor_path, status_path, close_path, review_path)
    return 0


def _pick_submarket(event: Any, args: argparse.Namespace) -> tuple[int, Any]:
    subs = list(event.sub_markets)
    if args.submarket_index is not None:
        if 0 <= args.submarket_index < len(subs):
            return args.submarket_index, subs[args.submarket_index]
        raise SystemExit(f"submarket index out of range: {args.submarket_index}")

    keywords = _submarket_keywords(args)
    candidates: list[tuple[int, Any]] = []
    for idx, sub in enumerate(subs):
        haystack = f"{sub.question} {sub.market_slug}".lower()
        if not keywords:
            if "winner" in haystack:
                candidates.append((idx, sub))
            continue
        if any(keyword in haystack for keyword in keywords):
            candidates.append((idx, sub))

    if args.game is not None or args.map_no is not None:
        winner_candidates = [
            (idx, sub)
            for idx, sub in candidates
            if "winner" in f"{sub.question} {sub.market_slug}".lower()
        ]
        if len(winner_candidates) == 1:
            return winner_candidates[0]
        if winner_candidates:
            candidates = winner_candidates

    if len(candidates) == 1:
        return candidates[0]
    if not candidates and len(subs) == 1:
        return 0, subs[0]

    print("需要选择具体子市场：")
    for idx, sub in enumerate(subs):
        outcomes = ", ".join(
            f"{o.outcome}({ _fmt_price(_execution_price(o)) })" for o in sub.outcomes
        )
        print(f"[{idx}] {sub.question} | {sub.market_slug} | {outcomes}")
    if candidates:
        print()
        print("当前关键词匹配到多个候选，请用 --submarket-index 指定。")
    raise SystemExit(2)


def _fill_selected_books(market_resolver: Any, sub: Any) -> None:
    for outcome in sub.outcomes:
        bid, ask, _neg_risk, _tick_size, _min_order_size = market_resolver.fetch_book_summary(
            outcome.token_id
        )
        outcome.best_bid = bid
        outcome.best_ask = ask


def _submarket_keywords(args: argparse.Namespace) -> list[str]:
    raw: list[str] = []
    if args.keyword:
        raw.append(args.keyword)
    if args.game is not None:
        raw.extend([f"game {args.game}", f"game{args.game}"])
    if args.map_no is not None:
        raw.extend([f"map {args.map_no}", f"map{args.map_no}"])
    return [x.lower().strip() for x in raw if x.strip()]


def _pick_side(sub: Any, requested_side: str, strategy: str, note: str = "") -> dict[str, Any]:
    outcomes = list(sub.outcomes)
    if requested_side.strip():
        name = requested_side.strip().lower()
        matches = [o for o in outcomes if o.outcome.lower() == name or name in o.outcome.lower()]
        if len(matches) == 1:
            return {"outcome": matches[0], "reason": f"用户指定方向：{matches[0].outcome}"}
        print("可选方向：")
        for outcome in outcomes:
            print(f"- {outcome.outcome}: {_fmt_price(_execution_price(outcome))}")
        raise SystemExit(f"无法唯一匹配方向：{requested_side}")

    priced = [(o, _execution_price(o)) for o in outcomes]
    priced = [(o, p) for o, p in priced if p is not None]
    if not priced:
        raise SystemExit("没有可用价格，无法自动选择方向。")

    if strategy.upper() == "A" or _note_prefers_low_side(note):
        chosen, price = min(priced, key=lambda item: item[1])
        return {
            "outcome": chosen,
            "reason": f"未指定方向，默认选择低价反转侧：{chosen.outcome} @ {_fmt_price(price)}",
        }

    chosen, price = max(priced, key=lambda item: item[1])
    return {
        "outcome": chosen,
        "reason": f"未指定方向，默认选择当前高价热门侧：{chosen.outcome} @ {_fmt_price(price)}",
    }


def _note_prefers_low_side(note: str) -> bool:
    text = note.lower()
    return any(
        keyword in text
        for keyword in (
            "弱势",
            "反转",
            "彩票",
            "低位",
            "掉到",
            "跌到",
            "三十",
            "30",
            "二十",
            "20",
            "四六",
            "拉扯",
        )
    )


def _pick_strategy(
    requested: str,
    note: str,
    current_price: float,
    pre_match_price: float | None,
) -> tuple[str, str]:
    requested_upper = requested.upper()
    if requested_upper in {"A", "B", "C", "D"}:
        return requested_upper, f"用户指定策略 {requested_upper}"

    text = note.lower()
    if _contains_any(text, ("持仓", "旧仓", "救援", "不想止损", "补仓", "成本", "套住")):
        return "D", "描述包含已有仓位/成本管理语义，归为策略D：持仓救援。"
    if _contains_any(text, ("理财", "碾压", "强势", "一路", "稳", "压制")):
        return "C", "描述包含强势碾压/理财局语义，归为策略C。"
    if _contains_any(text, ("强队", "热门", "回撤", "低估", "暂时落后", "二八", "三七")):
        return "B", "描述包含热门方回撤语义，归为策略B。"
    if _contains_any(text, ("四六", "拉扯", "反转", "彩票", "弱势", "掉到", "跌到", "纠缠")):
        return "A", "描述包含低位拉扯/反转语义，归为策略A。"

    if pre_match_price is not None and pre_match_price >= 0.65 and 0.40 <= current_price <= 0.80:
        return "B", "赛前价格较高且当前处于回撤区间，自动归为策略B。"
    if current_price <= 0.35:
        return "A", "当前价格处于低位区间，自动归为策略A。"
    if current_price >= 0.78:
        return "C", "当前价格处于高价优势区，自动归为策略C；当前仅建议，不自动实盘。"
    if current_price >= 0.55:
        return "B", "当前价格偏高，默认按热门方回撤策略B准备。"
    return "A", "当前价格偏低，默认按低位反转策略A准备。"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _advisory_next_step(strategy_code: str) -> str:
    if strategy_code == "C":
        return (
            "策略C当前只做建议：确认不是终局追高；等待优势方回撤到 70-78c；"
            "spread 和盘口深度达标后，再考虑小金额执行。"
        )
    return (
        "策略D当前只做建议：先读取已有仓位、平均成本和未成交挂单；"
        "优先设计减仓/回本方案，不默认继续补仓。"
    )


def _print_advisory(advisory: dict[str, Any], advisory_path: Path) -> None:
    print("策略建议已生成，暂不进入自动实盘")
    print()
    print(f"市场：{advisory['market_title']}")
    print(f"方向：{advisory['side']}")
    print(f"当前价格：{_fmt_price(advisory['current_price'])}")
    print(f"识别策略：{advisory['strategy_code']}")
    print(f"原因：{advisory['strategy_reason']}")
    print(f"下一步：{advisory['next_step']}")
    print()
    print(f"建议文件：{advisory_path}")


def _execution_price(outcome: Any) -> float:
    price = outcome.best_ask
    if price is None:
        price = outcome.current_price
    if price is None:
        raise SystemExit(f"方向 {outcome.outcome} 没有可用价格。")
    return round(float(price), 2)


def _write_run_launcher(
    path: Path,
    plan: dict[str, Any],
    plan_path: Path,
    state_path: Path,
    token_id: str,
    name: str,
) -> None:
    log_file = LOGS / f"{name}.log"
    content = f"""#!/bin/zsh
cd "{PROJECT_ROOT}" || exit 1

LOG_FILE="{log_file}"
STATE_FILE="{state_path}"
mkdir -p "{LOGS}"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Market: {plan.get('market_title')}"
echo "Side: {plan.get('side')}"
echo "Strategy: {plan.get('strategy_name') or plan.get('strategy_type')}"
echo "Plan: {plan_path}"
echo "State: $STATE_FILE"
echo "Log: $LOG_FILE"
echo "============================================================"
echo

if [ -f "$STATE_FILE" ]; then
  echo "State file already exists. To avoid duplicate BUY orders, use the monitor launcher instead:"
  echo "{RUNTIME / f'monitor_{name}.command'}"
  exit 1
fi

"{BOT_PYTHON}" -u \\
  "{RUNNER}" \\
  --plan "{plan_path}" \\
  --token-id "{token_id}" \\
  --state-file "$STATE_FILE" \\
  --poll-interval 20

echo
echo "Finished at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Runner stopped. Press Enter to close this window."
read _
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _write_monitor_launcher(
    path: Path,
    plan: dict[str, Any],
    plan_path: Path,
    state_path: Path,
    token_id: str,
    name: str,
) -> None:
    log_file = LOGS / f"{name}_monitor.log"
    content = f"""#!/bin/zsh
cd "{PROJECT_ROOT}" || exit 1

LOG_FILE="{log_file}"
STATE_FILE="{state_path}"
mkdir -p "{LOGS}"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Started monitor at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Market: {plan.get('market_title')}"
echo "Side: {plan.get('side')}"
echo "State: $STATE_FILE"
echo "Log: $LOG_FILE"
echo "This monitor will not place new BUY orders."
echo "============================================================"
echo

if [ ! -f "$STATE_FILE" ]; then
  echo "State file not found. Run the first-execution launcher before monitor-only."
  exit 1
fi

"{BOT_PYTHON}" -u \\
  "{RUNNER}" \\
  --plan "{plan_path}" \\
  --token-id "{token_id}" \\
  --state-file "$STATE_FILE" \\
  --poll-interval 20 \\
  --monitor-only

echo
echo "Monitor stopped at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Press Enter to close this window."
read _
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _write_status_launcher(path: Path, state_path: Path, name: str) -> None:
    log_file = LOGS / f"{name}_status.log"
    content = f"""#!/bin/zsh
cd "{PROJECT_ROOT}" || exit 1

LOG_FILE="{log_file}"
STATE_FILE="{state_path}"
mkdir -p "{LOGS}"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Status check at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "State: $STATE_FILE"
echo "============================================================"
echo

if [ ! -f "$STATE_FILE" ]; then
  echo "State file not found. No live grid state is available yet."
  exit 1
fi

"{BOT_PYTHON}" \\
  "{SUMMARY}" \\
  --state-file "$STATE_FILE"

echo
echo "Status check finished. Press Enter to close this window."
read _
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _write_close_launcher(path: Path, state_path: Path, name: str) -> None:
    log_file = LOGS / f"{name}_close.log"
    content = f"""#!/bin/zsh
cd "{PROJECT_ROOT}" || exit 1

LOG_FILE="{log_file}"
STATE_FILE="{state_path}"
mkdir -p "{LOGS}"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Close orders at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "State: $STATE_FILE"
echo "Action: stop monitor, then cancel live BUY/SELL orders tracked in state."
echo "This does NOT sell filled positions."
echo "============================================================"
echo

if [ ! -f "$STATE_FILE" ]; then
  echo "State file not found. No tracked grid orders to close."
  exit 1
fi

echo "Stopping monitor/runner processes for this state file..."
/usr/bin/pkill -f "grid_plan_runner.py.*$STATE_FILE" || true
sleep 1

echo
echo "Cancelling tracked live orders..."
"{BOT_PYTHON}" \\
  "{CANCEL}" \\
  --state-file "$STATE_FILE" \\
  --include-buys \\
  --include-sells

echo
echo "Close action finished. Press Enter to close this window."
read _
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _write_review_launcher(path: Path, state_path: Path, name: str) -> None:
    log_file = LOGS / f"{name}_review.log"
    content = f"""#!/bin/zsh
cd "{PROJECT_ROOT}" || exit 1

LOG_FILE="{log_file}"
STATE_FILE="{state_path}"
mkdir -p "{LOGS}"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Create review at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "State: $STATE_FILE"
echo "============================================================"
echo

if [ ! -f "$STATE_FILE" ]; then
  echo "State file not found. No trade review can be created yet."
  exit 1
fi

"{BOT_PYTHON}" \\
  "{REVIEW}" \\
  --state-file "$STATE_FILE"

echo
echo "Review created. Press Enter to close this window."
read _
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _print_summary(
    plan: dict[str, Any],
    plan_path: Path,
    state_path: Path,
    run_path: Path,
    monitor_path: Path,
    status_path: Path,
    close_path: Path,
    review_path: Path,
) -> None:
    print("交易准备完成")
    print()
    print(f"市场：{plan['market_title']}")
    print(f"方向：{plan['side']}")
    print(f"策略：{plan['strategy_name']}")
    print(f"价格：{_fmt_price(plan['current_price'])}")
    print(f"理由：{plan['operator_note']}")
    print()
    print("买入挂单：")
    for layer in plan["buy_ladders"]:
        print(f"- BUY {layer['amount_usd']} USDC @ {_fmt_price(layer['price'])}")
    print("止盈卖单：")
    for step in plan["sell_plan"]:
        print(f"- SELL 成本 {step['sell_cost_basis_usd']} USDC @ {_fmt_price(step['price'])}")
    print(f"彩票仓：成本 {plan.get('lottery_cost_basis_usd', 0)} USDC")
    warnings = plan.get("warnings") or []
    if warnings:
        print()
        print("提示：")
        for warning in warnings:
            print(f"- {warning}")
    print()
    print(f"计划文件：{plan_path}")
    print(f"状态文件：{state_path}")
    print(f"首次执行：{run_path}")
    print(f"只监控：{monitor_path}")
    print(f"查状态：{status_path}")
    print(f"关闭订单：{close_path}")
    print(f"生成复盘：{review_path}")


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{round(float(value) * 100):.0f}c"


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()
    return value[:160] or "grid-trade"


if __name__ == "__main__":
    raise SystemExit(main())
