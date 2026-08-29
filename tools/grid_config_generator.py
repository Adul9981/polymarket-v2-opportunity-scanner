#!/usr/bin/env python3
"""Generate trade_config JSON for prediction-market grid strategies.

This is intentionally conservative: it creates an execution config, but it does
not place orders. The existing execution layer should read the generated JSON.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_PATH = PROJECT_ROOT / "config" / "strategy_templates.json"


@dataclass
class Ladder:
    price: float
    amount_usd: float


@dataclass
class SellStep:
    price: float
    sell_cost_basis_usd: float


def cents(value: float) -> float:
    return round(max(0.01, min(0.99, value)), 2)


def money(value: float) -> float:
    return round(value, 2)


def weighted_ladders(prices: list[float], weights: list[float], budget: float) -> list[Ladder]:
    return [
        Ladder(price=cents(price), amount_usd=money(budget * weight))
        for price, weight in zip(prices, weights)
    ]


def fixed_sell_steps(prices: list[float], amounts: list[float]) -> list[SellStep]:
    return [
        SellStep(price=cents(price), sell_cost_basis_usd=money(amount))
        for price, amount in zip(prices, amounts)
        if amount > 0
    ]


def d2_profit_lock_plan() -> dict[str, Any]:
    return {
        "name": "D2：浮盈保护 / 自动锁盈",
        "type": "execution_protection",
        "applies_to": [
            "A_DEEP_REVERSAL",
            "B_FAVORITE_DIP",
            "C_DOMINANT_COMPOUNDER",
            "P_PRE_POSITION",
        ],
        "trigger_min_profit_price": 0.60,
        "major_lock_price": 0.75,
        "final_trim_price": 0.80,
        "max_lottery_cost_basis_usd": 10.0,
        "max_lottery_cost_ratio": 0.20,
        "trailing_protection": [
            {"after_touch": 0.75, "stop_price": 0.68},
            {"after_touch": 0.80, "stop_price": 0.72},
        ],
        "principle": "系统不是为了赚到最后一分钱，而是防止把已经赚到的钱还回去。",
    }


def load_strategy_template(key: str) -> dict[str, Any] | None:
    """Read a strategy template from config/strategy_templates.json (single source of truth)."""
    try:
        data = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        return data.get("strategies", {}).get(key)
    except Exception:
        return None


def template_config(
    key: str,
    strategy_type: str,
    strategy_name: str,
    cycle_budget: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build the plan from the template, scaling amounts to cycle_budget."""
    tpl = load_strategy_template(key)
    if not tpl:
        return None
    buys = tpl.get("standard_buy_ladders") or []
    sells = tpl.get("standard_sell_plan") or []
    total = sum(float(x.get("amount_usd", 0)) for x in buys)
    scale = cycle_budget / total if total else 1.0
    scaled_buys = [Ladder(price=float(x["price"]), amount_usd=money(float(x["amount_usd"]) * scale)) for x in buys]
    scaled_sells = [
        SellStep(price=float(x["price"]), sell_cost_basis_usd=money(float(x["sell_cost_basis_usd"]) * scale))
        for x in sells
    ]
    config: dict[str, Any] = {
        "strategy_type": strategy_type,
        "strategy_name": strategy_name,
        "amount_mode": "fixed_usd",
        "buy_ladders": [asdict(x) for x in scaled_buys],
        "sell_plan": [asdict(x) for x in scaled_sells],
        "lottery_cost_basis_usd": money(float(tpl.get("lottery_cost_basis_usd") or 0) * scale),
        "profit_lock_plan": d2_profit_lock_plan(),
        "max_cycles": int(tpl.get("max_cycles", 1)),
        "stop_new_entry_below": float(tpl.get("stop_new_entry_below") or 0),
        "stop_new_entry_above": float(tpl.get("stop_new_entry_above") or 1),
        "profile_note": str(tpl.get("use_case") or tpl.get("name") or ""),
        "execution_note": "sell_cost_basis_usd 表示从已成交买入批次中，按该成本金额对应的 shares 计算卖出数量。",
        "entry_checks": [
            "按 config/strategy_templates.json 模板生成的固定档位执行（Mid80 中位80 家族）",
            "买入为回撤挂单，跌到才成交；成交后自动补止盈",
            "跌破 stop_new_entry_below 停止加仓",
        ],
    }
    if extra:
        config.update(extra)
    return config


def strategy_a_deep_reversal(current_price: float, cycle_budget: float) -> dict[str, Any]:
    """A type: real adversity / deep reversal / lottery-compatible."""
    template_cfg = template_config(
        "A_STANDARD_MID_REVERSAL",
        "A_STANDARD_MID_REVERSAL",
        "中位80-S1：S1-标准中位反转（保守版）",
        cycle_budget,
    )
    if template_cfg is not None:
        return template_cfg

    if current_price <= 0.12:
        buy_prices = [current_price, current_price - 0.03, current_price - 0.06]
        buy_weights = [0.50, 0.30, 0.20]
        lottery_amount = cycle_budget * 0.20
        sell_steps = fixed_sell_steps(
            [current_price * 3, current_price * 5, 0.75],
            [cycle_budget * 0.35, cycle_budget * 0.35, cycle_budget * 0.10],
        )
        profile_note = "A型彩票子类：低于12c，买入即接受大概率归零，靠少数大赢覆盖。"
    else:
        base = min(max(current_price, 0.20), 0.30)
        buy_prices = [base, base - 0.05, base - 0.10]
        buy_weights = [0.40, 0.40, 0.20]
        lottery_amount = cycle_budget * 0.15
        sell_steps = fixed_sell_steps(
            [0.40, 0.50, 0.60],
            [cycle_budget * 0.30, cycle_budget * 0.30, cycle_budget * 0.25],
        )
        profile_note = "A型标准子类：20-30c 分层买，40/50/60c 分批卖，保留彩票仓。"

    return {
        "strategy_type": "A_DEEP_REVERSAL",
        "strategy_name": "A型：深度反转 / 彩票型",
        "amount_mode": "fixed_usd",
        "buy_ladders": [asdict(x) for x in weighted_ladders(buy_prices, buy_weights, cycle_budget)],
        "sell_plan": [asdict(x) for x in sell_steps],
        "lottery_cost_basis_usd": money(lottery_amount),
        "profit_lock_plan": d2_profit_lock_plan(),
        "max_cycles": 2,
        "stop_new_entry_below": 0.05,
        "stop_new_entry_above": 0.92,
        "profile_note": profile_note,
        "execution_note": "sell_cost_basis_usd 表示从已成交买入批次中，按该成本金额对应的 shares 计算卖出数量。",
        "entry_checks": [
            "价格处于深度低估区间，优先 20-30c；10c 以下只按彩票仓处理",
            "不要追高；只接回落挂单",
            "若已接近封顶/归零，只管理已有仓位",
        ],
    }


def strategy_b_favorite_dip(
    current_price: float,
    pre_match_price: float | None,
    cycle_budget: float,
) -> dict[str, Any]:
    """B type: pre-match favorite temporarily discounted."""
    warnings: list[str] = []
    if pre_match_price is None:
        warnings.append("B型建议提供赛前热门赔率；缺失时只能按当前价生成弱配置。")
    elif pre_match_price < 0.65:
        warnings.append("赛前赔率低于65%，不满足标准B型热门条件。")

    template_cfg = template_config(
        "B_FAVORITE_DIP",
        "B_FAVORITE_DIP",
        "中位80-S2：热门深回撤（主攻）",
        cycle_budget,
        extra={"risk_tier": "good", "warnings": warnings},
    )
    if template_cfg is not None:
        return template_cfg

    if current_price < 0.40:
        warnings.append("当前价跌破40%，B型失效，需切换到A型逻辑重新评估。")

    if current_price >= 0.70:
        buy_prices = [current_price, current_price - 0.04]
        buy_weights = [0.65, 0.35]
        risk_tier = "best"
    elif current_price >= 0.60:
        buy_prices = [current_price, current_price - 0.05]
        buy_weights = [0.60, 0.40]
        risk_tier = "good"
    else:
        buy_prices = [current_price, current_price - 0.05]
        buy_weights = [0.50, 0.50]
        risk_tier = "risky"
        warnings.append("40-60% 区间波动更大，按小仓执行。")

    sell_steps = [
        SellStep(price=cents(current_price + 0.12), sell_cost_basis_usd=money(cycle_budget * 0.40)),
        SellStep(price=cents(current_price + 0.22), sell_cost_basis_usd=money(cycle_budget * 0.40)),
        SellStep(price=0.98, sell_cost_basis_usd=money(cycle_budget * 0.15)),
    ]

    return {
        "strategy_type": "B_FAVORITE_DIP",
        "strategy_name": "B型：强队临时低估",
        "risk_tier": risk_tier,
        "amount_mode": "fixed_usd",
        "buy_ladders": [asdict(x) for x in weighted_ladders(buy_prices, buy_weights, cycle_budget)],
        "sell_plan": [asdict(x) for x in sell_steps],
        "lottery_cost_basis_usd": money(cycle_budget * 0.05),
        "profit_lock_plan": d2_profit_lock_plan(),
        "max_cycles": 1,
        "stop_new_entry_below": 0.40,
        "stop_new_entry_above": 0.95,
        "profile_note": "B型只买赛前热门的短暂恐慌回落；跌破40%不再按B型加仓。",
        "execution_note": "sell_cost_basis_usd 表示从已成交买入批次中，按该成本金额对应的 shares 计算卖出数量。",
        "entry_checks": [
            "赛前热门最好 >65%，更理想 >75%",
            "70-80% 是最优回落区，60-70% 次优，40-60% 小仓谨慎",
            "跌破40% 停止B型执行，重新判断是否转A型",
        ],
        "warnings": warnings,
    }


def strategy_c_dominant_compounder(current_price: float, cycle_budget: float) -> dict[str, Any]:
    """C type: dominant-side small pullback / high-price compounder pilot."""
    warnings: list[str] = []
    if current_price >= 0.90:
        warnings.append("当前价已高于90c，C型不追高；买单只挂回撤价。")
    if current_price < 0.65:
        warnings.append("当前价低于65c，不是标准理财局，需重新判断是否更像A/B。")

    base = min(current_price, 0.78)
    base = max(base, 0.68)
    buy_prices = [base, base - 0.04]
    buy_weights = [0.60, 0.40]

    if cycle_budget < 15:
        warnings.append("C型小于15 USDC时只挂一档核心止盈，避免单张卖单低于最小数量。")
        sell_steps = [
            SellStep(price=cents(base + 0.08), sell_cost_basis_usd=money(cycle_budget * 0.80)),
        ]
    else:
        sell_steps = [
            SellStep(price=cents(base + 0.08), sell_cost_basis_usd=money(cycle_budget * 0.40)),
            SellStep(price=cents(base + 0.15), sell_cost_basis_usd=money(cycle_budget * 0.35)),
            SellStep(price=0.98, sell_cost_basis_usd=money(cycle_budget * 0.15)),
        ]

    return {
        "strategy_type": "C_DOMINANT_COMPOUNDER",
        "strategy_name": "C型：强势碾压 / 理财局",
        "risk_tier": "experimental",
        "amount_mode": "fixed_usd",
        "buy_ladders": [asdict(x) for x in weighted_ladders(buy_prices, buy_weights, cycle_budget)],
        "sell_plan": [asdict(x) for x in sell_steps],
        "lottery_cost_basis_usd": money(cycle_budget * 0.10),
        "profit_lock_plan": d2_profit_lock_plan(),
        "max_cycles": 1,
        "stop_new_entry_below": 0.62,
        "stop_new_entry_above": 0.90,
        "profile_note": "C型实验策略：只买强势方小回撤，不追高，收益空间小但要求高胜率和好流动性。",
        "execution_note": "C型为实验性小额策略；sell_cost_basis_usd 按已成交买入成本换算 shares。",
        "entry_checks": [
            "只在优势方回撤到70-78c附近时接，不追90c以上",
            "spread 必须小，盘口深度要足够",
            "临近终局或价格长时间不更新时不新开",
        ],
        "warnings": warnings,
    }


def build_config(args: argparse.Namespace) -> dict[str, Any]:
    match_budget = float(args.match_budget)
    cycle_budget = float(args.cycle_budget) if args.cycle_budget else match_budget * 0.25
    current_price = float(args.current_price)
    pre_match_price = float(args.pre_match_price) if args.pre_match_price is not None else None

    if args.strategy.upper() == "A":
        strategy = strategy_a_deep_reversal(current_price, cycle_budget)
    elif args.strategy.upper() == "B":
        strategy = strategy_b_favorite_dip(current_price, pre_match_price, cycle_budget)
    elif args.strategy.upper() == "C":
        strategy = strategy_c_dominant_compounder(current_price, cycle_budget)
    else:
        raise ValueError("strategy must be A, B, or C")

    return {
        "version": "mvp-0.1",
        "mode": "config_only",
        "market_slug": args.market_slug,
        "market_title": args.market_title,
        "side": args.side,
        "league": args.league,
        "current_price": current_price,
        "pre_match_price": pre_match_price,
        "match_budget": match_budget,
        "cycle_budget": money(cycle_budget),
        "operator_note": args.note,
        **strategy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grid trade_config JSON.")
    parser.add_argument("--strategy", required=True, choices=["A", "B", "C", "a", "b", "c"])
    parser.add_argument("--market-slug", required=True)
    parser.add_argument("--side", required=True, help="Outcome/team to buy.")
    parser.add_argument("--current-price", required=True, type=float)
    parser.add_argument("--match-budget", required=True, type=float)
    parser.add_argument("--cycle-budget", type=float)
    parser.add_argument("--pre-match-price", type=float)
    parser.add_argument("--market-title", default="")
    parser.add_argument("--league", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--output", default="trade_config.json")
    args = parser.parse_args()

    config = build_config(args)
    output = Path(args.output)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    main()
