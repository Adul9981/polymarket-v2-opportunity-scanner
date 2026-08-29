#!/usr/bin/env python3
"""Backtest A/B grid strategy shape on a Polymarket event.

This tool is read-only. It fetches public Polymarket metadata and price history,
then simulates the fixed-USD grid rules used by this project.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


@dataclass
class PricePoint:
    ts: int
    price: float


@dataclass
class Fill:
    ts: int
    action: str
    price: float
    amount_usd: float
    shares: float
    note: str


def http_json(url: str, params: dict[str, Any] | None = None) -> Any:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=25,
                headers={"User-Agent": "polymarket-grid-backtester/0.1"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - public data fetch retry
            last_exc = exc
            if attempt < 2:
                continue
    raise RuntimeError(f"公共数据接口请求失败: {last_exc}") from last_exc


def parse_slug(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if "event" in parts:
            return parts[parts.index("event") + 1]
        return parts[-1]
    return value


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return []


def event_by_slug(slug: str) -> dict[str, Any]:
    try:
        data = http_json(f"{GAMMA}/events/slug/{slug}")
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    data = http_json(f"{GAMMA}/events", {"slug": slug})
    if isinstance(data, list) and data:
        return data[0]
    raise RuntimeError(f"找不到事件 slug: {slug}")


def market_matches_game(market: dict[str, Any], game: int) -> bool:
    needle_variants = [
        f"game {game} winner",
        f"game {game}:",
        f"g{game} winner",
        f"map {game} winner",
        f"map {game}:",
    ]
    haystack = " ".join(
        str(market.get(key, ""))
        for key in ("question", "slug", "groupItemTitle", "description", "sportsMarketType")
    ).lower()
    if any(needle in haystack for needle in needle_variants):
        if "winner" in haystack or "moneyline" in haystack:
            return True
    return market.get("sportsMarketType") in {f"game_{game}_moneyline", f"map_{game}_moneyline"}


def find_game_winner_market(event: dict[str, Any], game: int) -> dict[str, Any]:
    markets = event.get("markets") or []
    matches = [m for m in markets if market_matches_game(m, game)]
    if len(matches) == 1:
        return matches[0]
    if matches:
        non_props = [
            m for m in matches
            if "kill" not in str(m.get("sportsMarketType", "")).lower()
            and "first blood" not in str(m.get("question", "")).lower()
        ]
        if non_props:
            return non_props[0]
        return matches[0]

    candidates = []
    for m in markets:
        title = str(m.get("groupItemTitle") or m.get("question") or m.get("slug") or "")
        if "Game" in title or "game" in title or "G" in title:
            candidates.append(title)
    raise RuntimeError(
        f"找不到 Game {game} Winner 市场。候选项: "
        + "; ".join(candidates[:20])
    )


def find_market_by_slug(event: dict[str, Any], slug: str) -> dict[str, Any]:
    for market in event.get("markets") or []:
        if market.get("slug") == slug:
            return market
    raise RuntimeError(f"找不到市场 slug: {slug}")


def choose_token(market: dict[str, Any], side: str | None) -> tuple[str, str]:
    outcomes = [str(x) for x in parse_json_array(market.get("outcomes"))]
    tokens = [str(x) for x in parse_json_array(market.get("clobTokenIds"))]
    prices = parse_json_array(market.get("outcomePrices"))
    if len(outcomes) != len(tokens):
        raise RuntimeError("市场 outcomes 和 clobTokenIds 数量不一致")

    if side:
        side_lower = side.lower()
        for outcome, token in zip(outcomes, tokens):
            if side_lower in outcome.lower() or outcome.lower() in side_lower:
                return outcome, token
        raise RuntimeError(f"找不到目标方向: {side}; 可选: {', '.join(outcomes)}")

    if prices and len(prices) == len(outcomes):
        idx = max(range(len(prices)), key=lambda i: float(prices[i]))
        return outcomes[idx], tokens[idx]

    return outcomes[0], tokens[0]


def fetch_history(token_id: str, start_ts: int | None, end_ts: int | None, fidelity: int) -> list[PricePoint]:
    params: dict[str, Any] = {"market": token_id, "fidelity": fidelity}
    if start_ts and end_ts:
        params["startTs"] = start_ts
        params["endTs"] = end_ts
    else:
        params["interval"] = "1d"
    data = http_json(f"{CLOB}/prices-history", params)
    raw = data.get("history") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise RuntimeError("价格历史返回格式异常")
    points = [
        PricePoint(ts=int(x["t"]), price=float(x["p"]))
        for x in raw
        if "t" in x and "p" in x
    ]
    return sorted(points, key=lambda x: x.ts)


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def price_summary(points: list[PricePoint]) -> dict[str, Any]:
    prices = [p.price for p in points]
    min_i = min(range(len(points)), key=lambda i: points[i].price)
    max_i = max(range(len(points)), key=lambda i: points[i].price)
    crosses = 0
    for prev, cur in zip(prices, prices[1:]):
        if (prev < 0.5 <= cur) or (prev > 0.5 >= cur):
            crosses += 1
    after_min_max = max(p.price for p in points[min_i:])
    before_min_max = max(p.price for p in points[: min_i + 1])
    return {
        "first": prices[0],
        "last": prices[-1],
        "min": prices[min_i],
        "min_ts": points[min_i].ts,
        "max": prices[max_i],
        "max_ts": points[max_i].ts,
        "before_min_max": before_min_max,
        "after_min_max": after_min_max,
        "rebound_from_min": after_min_max - prices[min_i],
        "crosses_50": crosses,
        "points": len(points),
    }


def first_signal(points: list[PricePoint], strategy: str) -> int:
    if strategy == "A":
        for i, p in enumerate(points):
            if 0.10 <= p.price <= 0.30:
                return i
        for i, p in enumerate(points):
            if p.price < 0.10:
                return i
    else:
        rolling_high = points[0].price
        for i, p in enumerate(points):
            rolling_high = max(rolling_high, p.price)
            if 0.60 <= p.price <= 0.80 and rolling_high >= 0.75 and rolling_high - p.price >= 0.07:
                return i
        for i, p in enumerate(points):
            if 0.60 <= p.price <= 0.80:
                return i
    return 0


def strategy_plan(strategy: str, signal_price: float, cycle_budget: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]], float]:
    if strategy == "A":
        if signal_price < 0.12:
            buys = [(signal_price, cycle_budget * 0.50), (signal_price - 0.03, cycle_budget * 0.30), (signal_price - 0.06, cycle_budget * 0.20)]
            sells = [(min(signal_price * 3, 0.99), cycle_budget * 0.35), (min(signal_price * 5, 0.99), cycle_budget * 0.35), (0.75, cycle_budget * 0.10)]
            lottery = cycle_budget * 0.20
        else:
            base = min(max(signal_price, 0.20), 0.30)
            buys = [(base, cycle_budget * 0.40), (base - 0.05, cycle_budget * 0.40), (base - 0.10, cycle_budget * 0.20)]
            sells = [(0.40, cycle_budget * 0.30), (0.50, cycle_budget * 0.30), (0.60, cycle_budget * 0.25)]
            lottery = cycle_budget * 0.15
    else:
        if signal_price >= 0.70:
            buys = [(signal_price, cycle_budget * 0.65), (signal_price - 0.04, cycle_budget * 0.35)]
        else:
            buys = [(signal_price, cycle_budget * 0.60), (signal_price - 0.05, cycle_budget * 0.40)]
        sells = [(min(signal_price + 0.12, 0.99), cycle_budget * 0.40), (min(signal_price + 0.22, 0.99), cycle_budget * 0.40), (0.98, cycle_budget * 0.15)]
        lottery = cycle_budget * 0.05
    buys = [(round(max(0.01, min(0.99, p)), 3), round(a, 2)) for p, a in buys if a > 0]
    sells = [(round(max(0.01, min(0.99, p)), 3), round(a, 2)) for p, a in sells if a > 0]
    return buys, sells, round(lottery, 2)


def sell_by_cost_basis(cost_basis: float, shares: float, sell_cost_basis: float) -> tuple[float, float]:
    if cost_basis <= 0 or shares <= 0:
        return 0.0, 0.0
    avg = cost_basis / shares
    sell_shares = min(shares, sell_cost_basis / avg)
    actual_cost = sell_shares * avg
    return actual_cost, sell_shares


def simulate(points: list[PricePoint], strategy: str, cycle_budget: float) -> dict[str, Any]:
    signal_i = first_signal(points, strategy)
    signal = points[signal_i]
    buy_plan, sell_plan, lottery_amount = strategy_plan(strategy, signal.price, cycle_budget)
    fills: list[Fill] = []
    bought: set[int] = set()
    sold: set[int] = set()
    cost_basis = 0.0
    shares = 0.0
    proceeds = 0.0

    for p in points[signal_i:]:
        for i, (limit_price, amount) in enumerate(buy_plan):
            if i not in bought and p.price <= limit_price:
                fill_shares = amount / limit_price
                bought.add(i)
                cost_basis += amount
                shares += fill_shares
                fills.append(Fill(p.ts, "BUY", limit_price, amount, fill_shares, f"买入阶梯 {i + 1}"))
        for i, (limit_price, sell_cost) in enumerate(sell_plan):
            active_cost = max(0.0, cost_basis - lottery_amount)
            if i not in sold and shares > 0 and active_cost > 0 and p.price >= limit_price:
                actual_cost, sell_shares = sell_by_cost_basis(cost_basis, shares, sell_cost)
                if sell_shares > 0:
                    sold.add(i)
                    shares -= sell_shares
                    cost_basis -= actual_cost
                    proceeds += sell_shares * limit_price
                    fills.append(Fill(p.ts, "SELL", limit_price, actual_cost, sell_shares, f"卖出阶梯 {i + 1}"))

    spent = sum(f.amount_usd for f in fills if f.action == "BUY")
    remaining_value = shares * points[-1].price
    total_value = proceeds + remaining_value
    pnl = total_value - spent
    roi = pnl / spent if spent else 0.0
    return {
        "signal_ts": signal.ts,
        "signal_price": signal.price,
        "buy_plan": buy_plan,
        "sell_plan": sell_plan,
        "lottery_cost_basis_usd": lottery_amount,
        "fills": fills,
        "spent": spent,
        "proceeds": proceeds,
        "remaining_shares": shares,
        "remaining_cost_basis": cost_basis,
        "remaining_value_at_last": remaining_value,
        "last_price": points[-1].price,
        "pnl": pnl,
        "roi": roi,
    }


def shape_score(summary: dict[str, Any], strategy: str) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    if strategy == "A":
        checks = [
            (summary["min"] <= 0.30, 25, "进入 20-30c 深度反转买入区"),
            (summary["rebound_from_min"] >= 0.25, 25, "低位后反弹空间超过 25c"),
            (summary["after_min_max"] >= 0.60, 20, "反弹触达 60c 附近，符合分批卖出窗口"),
            (summary["crosses_50"] >= 1, 15, "至少穿越一次 50% 中位线"),
            (summary["last"] >= 0.90, 15, "最终接近命中，彩票仓有意义"),
        ]
    else:
        checks = [
            (summary["before_min_max"] >= 0.75, 25, "前段曾处于强队热门区"),
            (0.60 <= summary["min"] <= 0.80, 25, "回落落在 B 型核心低估区"),
            (summary["min"] >= 0.40, 15, "没有跌破 40c 的 B 型失效线"),
            (summary["after_min_max"] - summary["min"] >= 0.20, 20, "低估后修复空间超过 20c"),
            (summary["last"] >= 0.90, 15, "最终修复至高概率/命中区"),
        ]
    for ok, points, reason in checks:
        if ok:
            score += points
            reasons.append(f"+{points} {reason}")
        else:
            reasons.append(f"+0 {reason}")
    return score, reasons


def render_report(args: argparse.Namespace, event: dict[str, Any], market: dict[str, Any], outcome: str, token_id: str, points: list[PricePoint], sim: dict[str, Any], summary: dict[str, Any]) -> str:
    score, reasons = shape_score(summary, args.strategy)
    verdict = "高度符合" if score >= 80 else "部分符合" if score >= 55 else "不够典型"
    market_label = f"Game {args.game}" if args.game else (market.get("groupItemTitle") or market.get("question") or "Market")
    fills = sim["fills"]
    lines = [
        f"# {event.get('title')} - {market_label} 策略{args.strategy}回测",
        "",
        f"- 结论：{verdict}策略 {args.strategy}，形态分 {score}/100",
        f"- 目标方向：{outcome}",
        f"- 市场：{market.get('groupItemTitle') or market.get('question')}",
        f"- token_id：`{token_id}`",
        f"- 价格点：{summary['points']} 个，{iso(points[0].ts)} 至 {iso(points[-1].ts)}",
        "",
        "## 走势特征",
        "",
        f"- 起始价：{summary['first']:.3f}",
        f"- 最低价：{summary['min']:.3f}（{iso(summary['min_ts'])}）",
        f"- 最高价：{summary['max']:.3f}（{iso(summary['max_ts'])}）",
        f"- 低点后最高：{summary['after_min_max']:.3f}",
        f"- 从低点反弹：{summary['rebound_from_min']:.3f}",
        f"- 50% 穿越次数：{summary['crosses_50']}",
        f"- 收盘/最终价：{summary['last']:.3f}",
        "",
        "## 形态判断",
        "",
    ]
    lines.extend(f"- {x}" for x in reasons)
    lines.extend([
        "",
        "## 固定金额网格回测",
        "",
        f"- 信号时间：{iso(sim['signal_ts'])}",
        f"- 信号价：{sim['signal_price']:.3f}",
        f"- 买入计划：{', '.join(f'{p:.3f} / ${a:.2f}' for p, a in sim['buy_plan'])}",
        f"- 卖出计划：{', '.join(f'{p:.3f} / ${a:.2f}成本份额' for p, a in sim['sell_plan'])}",
        f"- 彩票仓成本：${sim['lottery_cost_basis_usd']:.2f}",
        "",
        "| 时间 | 动作 | 价格 | 金额/成本 | shares | 说明 |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ])
    if fills:
        for fill in fills:
            lines.append(
                f"| {iso(fill.ts)} | {fill.action} | {fill.price:.3f} | "
                f"${fill.amount_usd:.2f} | {fill.shares:.4f} | {fill.note} |"
            )
    else:
        lines.append("| - | - | - | - | - | 没有触发成交 |")
    lines.extend([
        "",
        f"- 实际投入：${sim['spent']:.2f}",
        f"- 已卖出回收：${sim['proceeds']:.2f}",
        f"- 剩余 shares：{sim['remaining_shares']:.4f}",
        f"- 剩余仓位按最终价估值：${sim['remaining_value_at_last']:.2f}",
        f"- 估算总盈亏：${sim['pnl']:.2f}",
        f"- 估算 ROI：{sim['roi'] * 100:.1f}%",
        "",
        "## 说明",
        "",
        "- 这是价格序列层面的回测，未计入实际盘口深度、排队、滑点和手续费。",
        "- BUY 按限价触达视为成交；SELL 按目标价触达视为成交。",
        "- `sell_cost_basis_usd` 按剩余持仓均价换算为卖出 shares。",
    ])
    return "\n".join(lines) + "\n"


def json_ready(
    args: argparse.Namespace,
    event: dict[str, Any],
    market: dict[str, Any],
    outcome: str,
    token_id: str,
    points: list[PricePoint],
    sim: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    score, reasons = shape_score(summary, args.strategy)
    return {
        "event_title": event.get("title"),
        "event_slug": event.get("slug"),
        "game": args.game,
        "strategy": args.strategy,
        "shape_score": score,
        "shape_reasons": reasons,
        "outcome": outcome,
        "market_title": market.get("groupItemTitle") or market.get("question"),
        "market_slug": market.get("slug"),
        "token_id": token_id,
        "summary": summary,
        "points": [{"t": p.ts, "p": round(p.price, 4)} for p in points],
        "simulation": {
            key: value
            for key, value in sim.items()
            if key != "fills"
        },
        "fills": [
            {
                "t": fill.ts,
                "action": fill.action,
                "price": round(fill.price, 4),
                "amount_usd": round(fill.amount_usd, 2),
                "shares": round(fill.shares, 4),
                "note": fill.note,
            }
            for fill in sim["fills"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest Polymarket A/B fixed-USD grid strategy.")
    parser.add_argument("url_or_slug")
    parser.add_argument("--game", type=int, choices=[1, 2, 3])
    parser.add_argument("--market-slug", help="Use a specific market slug, e.g. the Match Winner market.")
    parser.add_argument("--strategy", required=True, choices=["A", "B"])
    parser.add_argument("--side", help="Outcome/team to backtest. Omit to use resolved winner/current highest price.")
    parser.add_argument("--cycle-budget", type=float, default=25.0)
    parser.add_argument("--start-ts", type=int)
    parser.add_argument("--end-ts", type=int)
    parser.add_argument("--fidelity", type=int, default=1)
    parser.add_argument("--output", help="Markdown report path.")
    parser.add_argument("--json-output", help="Compact JSON data path for visualizations.")
    args = parser.parse_args()

    slug = parse_slug(args.url_or_slug)
    event = event_by_slug(slug)
    if args.market_slug:
        market = find_market_by_slug(event, args.market_slug)
    else:
        if args.game is None:
            raise RuntimeError("需要提供 --game，或用 --market-slug 指定具体市场。")
        market = find_game_winner_market(event, args.game)
    outcome, token_id = choose_token(market, args.side)

    start_ts = args.start_ts
    end_ts = args.end_ts
    if not start_ts or not end_ts:
        start_raw = market.get("gameStartTime") or event.get("startTime") or event.get("startDate")
        end_raw = market.get("closedTime") or market.get("endDate") or event.get("closedTime") or event.get("endDate")
        if start_raw and end_raw:
            start_dt = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
            start_ts = math.floor(start_dt.timestamp()) - 60 * 90
            end_ts = math.ceil(end_dt.timestamp()) + 60 * 15

    points = fetch_history(token_id, start_ts, end_ts, args.fidelity)
    if not points:
        raise RuntimeError("没有拿到价格历史；可尝试放大时间窗口或调高 fidelity。")

    summary = price_summary(points)
    sim = simulate(points, args.strategy, args.cycle_budget)
    report = render_report(args, event, market, outcome, token_id, points, sim, summary)
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                json_ready(args, event, market, outcome, token_id, points, sim, summary),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(str(output))
    else:
        print(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
