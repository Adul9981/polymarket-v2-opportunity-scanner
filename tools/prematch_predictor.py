#!/usr/bin/env python3
"""V2-S2 pre-match pattern prediction + pre-match resting order plan (执行准备链).

Before a match starts, predict which pattern is likely to appear today
(pattern climate + team profiles + intel signals + league reputation +
pre-match odds), then generate a pre-match resting limit order plan from the
matched strategy template. Dry-run only by default: it prints the plan and the
exact grid_plan_runner command; real placement stays with grid_plan_runner
(the only order entry) after human confirmation.

Usage:
    python3 tools/prematch_predictor.py --slug <event-slug>
    python3 tools/prematch_predictor.py --event-file tests/fixtures/prematch_event.json
    python3 tools/prematch_predictor.py --slug <slug> --strategy B_FAVORITE_DIP --budget 50
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GAMMA = "https://gamma-api.polymarket.com"
GRID_RUNNER = ROOT / "tools" / "grid_plan_runner.py"
DEFAULT_PENDING_DIR = ROOT / "runtime" / "prematch_pending"

TEMPLATE_KEY_MAP = {
    "S2_FAVORITE_DIP": "B_FAVORITE_DIP",
    "S1_DEEP_REVERSAL": "A_DEEP_REVERSAL",
    "S1_MID_REVERSAL": "A_STANDARD_MID_REVERSAL",
}

LEAGUE_REPUTATION = {
    "LCK": {"label": "LCK：假赛少，反转样本可靠", "scale": 1.0},
    "LPL": {"label": "LPL：假赛风险高，同形态降档或不做", "scale": 0.5},
    "LEC": {"label": "LEC：常打满+明眼假赛疑似，降档并需交叉验证", "scale": 0.5},
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def http_json(url: str, tries: int = 6) -> Any:
    last: Exception | None = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polymarket-prematch/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed public APIs
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            import time

            time.sleep(1.2)
    raise RuntimeError(f"fetch fail {url}: {last}")


def fetch_event(slug: str) -> dict[str, Any]:
    data = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
    if isinstance(data, list) and data:
        return data[0]
    data = http_json(f"{GAMMA}/events/slug/{urllib.parse.quote(slug)}")
    return data if isinstance(data, dict) else {}


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return value or []


def event_start_time(event: dict[str, Any]) -> datetime | None:
    for key in ("startTime", "gameStartTime", "startDate", "start_date"):
        raw = event.get(key)
        if not raw:
            continue
        text = str(raw).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            continue
    return None


def winner_market(event: dict[str, Any]) -> dict[str, Any]:
    markets = [m for m in event.get("markets") or [] if isinstance(m, dict)]
    for market in markets:
        hay = " ".join(
            str(market.get(k) or "") for k in ("groupItemTitle", "question", "slug")
        ).lower()
        if "game 1 winner" in hay or "map 1 winner" in hay or "match winner" in hay or "moneyline" in hay:
            return market
    return markets[0] if markets else {}


def favorite_underdog(event: dict[str, Any]) -> tuple[str, str, float, float]:
    market = winner_market(event)
    outcomes = [str(o) for o in parse_list(market.get("outcomes"))]
    prices = parse_list(market.get("outcomePrices"))
    if len(outcomes) >= 2 and len(prices) >= 2:
        a, b = float(prices[0]), float(prices[1])
        if a >= b:
            return outcomes[0], outcomes[1], a, b
        return outcomes[1], outcomes[0], b, a
    return "", "", 0.5, 0.5


def load_team_profiles() -> dict[str, dict[str, Any]]:
    """Parse knowledge/TEAM_PROFILES.md table into {team: profile}."""
    path = ROOT / "knowledge" / "TEAM_PROFILES.md"
    profiles: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return profiles
    in_table = False
    for line in path.open("r", encoding="utf-8"):
        stripped = line.strip()
        if stripped.startswith("|") and "队伍" in stripped and "形态倾向" in stripped:
            in_table = True
            continue
        if not in_table or not stripped.startswith("|"):
            continue
        if re.search(r"\|---", stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 6:
            continue
        team_cell, region, style, tendency, evidence, trust = cells[:6]
        keys = [k.strip() for k in re.split(r"[/、]", team_cell) if k.strip()]
        for key in keys:
            profiles[key] = {
                "region": region,
                "style": style,
                "tendency": tendency,
                "evidence": evidence,
                "trust": trust,
            }
    return profiles


def pattern_climate() -> dict[str, Any]:
    """Compute reversal-vs-collapse climate from the classifier golden set."""
    path = ROOT / "docs" / "data" / "classifier_golden_set.json"
    if not path.exists():
        return {"climate": "unknown", "a": 0, "b": 0, "reasons": ["无 golden set 数据"]}
    labels: Counter[str] = Counter()
    for row in load_json(path).get("rows") or []:
        for label in row.get("labels") or []:
            labels[str(label)] += 1
    a = sum(n for lab, n in labels.items() if re.match(r"^A\d", lab))
    b = sum(n for lab, n in labels.items() if re.match(r"^B\d", lab))
    reasons = [
        f"反转类 A 类 {a} 条，崩塌类 B 类 {b} 条",
        "反转日（A 高频）：低错杀位买、高位不追、连续亏损减半",
        "崩塌日（B 高频）：上调 D2 锁盈优先级、下调深反彩票仓位",
    ]
    if a >= 3 and a >= 2 * b:
        climate = "reversal"
    elif b >= 3 and b >= 2 * a:
        climate = "collapse"
    else:
        climate = "mixed"
    return {"climate": climate, "a": a, "b": b, "reasons": reasons}


def team_intel(team: str) -> list[dict[str, Any]]:
    path = ROOT / "knowledge" / "intel_signals.json"
    if not path.exists():
        return []
    signals = load_json(path).get("signals") or []
    hits: list[dict[str, Any]] = []
    for signal in signals:
        blob = " ".join(
            str(signal.get(k) or "") for k in ("object", "object_type", "direction", "quote")
        )
        if team and team.lower() in blob.lower():
            hits.append(
                {
                    "date": signal.get("date"),
                    "credibility": signal.get("credibility"),
                    "quote": str(signal.get("quote") or "")[:80],
                }
            )
    return hits


def predict(
    event: dict[str, Any],
    team_profiles: dict[str, dict[str, Any]],
    strategy_override: str,
) -> dict[str, Any]:
    climate = pattern_climate()
    favorite, underdog, fav_price, und_price = favorite_underdog(event)
    title = str(event.get("title") or "")
    region = "LCK" if "LCK" in title else ("LPL" if "LPL" in title else ("LEC" if "LEC" in title else ""))
    league = LEAGUE_REPUTATION.get(region, {"label": "未知赛区", "scale": 1.0})

    predictions: list[dict[str, Any]] = []
    reasons: list[str] = [f"赛前定价：热门 {favorite} {fav_price:.2f} / 下狗 {underdog} {und_price:.2f}"]
    reasons.append(f"形态气候：{climate['climate']}（{climate['reasons'][0]}）")
    reasons.append(league["label"])

    fav_profile = team_profiles.get(favorite) if favorite else None
    und_profile = team_profiles.get(underdog) if underdog else None
    if fav_profile:
        reasons.append(f"热门画像：{favorite} {fav_profile['tendency']}")
    if und_profile:
        reasons.append(f"下狗画像：{underdog} {und_profile['tendency']}")

    if fav_price >= 0.65:
        predictions.append(
            {
                "pattern": "S2_FAVORITE_DIP",
                "confidence": "high" if fav_price >= 0.75 else "medium",
                "reason": f"热门 {favorite} 赛前 {fav_price:.0%}，盘中回撤到 40-50c 是主攻形态",
            }
        )
    if und_profile and any(k in und_profile["tendency"] for k in ("反转", "翻盘", "A1", "A2", "下狗")):
        predictions.append(
            {
                "pattern": "S1_DEEP_REVERSAL",
                "confidence": "medium",
                "reason": f"下狗 {underdog} 画像倾向反转（{und_profile['tendency']}），极低位彩票仓",
            }
        )
    if fav_profile and any(k in fav_profile["tendency"] for k in ("崩塌", "B1", "领先会浪", "送")):
        predictions.append(
            {
                "pattern": "B1_COLLAPSE_WATCH",
                "confidence": "medium",
                "reason": f"热门 {favorite} 画像有领先崩塌倾向（{fav_profile['tendency']}），高位不追、锁盈优先",
            }
        )
    if climate["climate"] == "reversal":
        predictions.append(
            {
                "pattern": "A_CLASS_REVERSAL_DAY",
                "confidence": "medium",
                "reason": "反转日：低错杀位买入优先，高位不追",
            }
        )
    if not predictions:
        predictions.append(
            {
                "pattern": "OBSERVE_ONLY",
                "confidence": "low",
                "reason": "无强预测信号，赛前仅观察，等盘中形态确认",
            }
        )

    if strategy_override and strategy_override != "auto":
        recommended = strategy_override
    else:
        candidates = [p["pattern"] for p in predictions if p["pattern"].startswith("S")]
        recommended = candidates[0] if candidates else ""
    return {
        "event": str(event.get("title") or ""),
        "event_slug": str(event.get("slug") or ""),
        "start_time": event_start_time(event).isoformat() if event_start_time(event) else None,
        "favorite": favorite,
        "underdog": underdog,
        "fav_price": fav_price,
        "und_price": und_price,
        "region": region,
        "league_scale": league["scale"],
        "climate": climate["climate"],
        "predictions": predictions,
        "recommended_strategy": recommended,
        "reasons": reasons,
    }


def build_plan(prediction: dict[str, Any], budget_override: float | None) -> dict[str, Any]:
    strategy_key = prediction["recommended_strategy"]
    template_key = TEMPLATE_KEY_MAP.get(strategy_key, strategy_key)
    templates = load_json(ROOT / "config" / "strategy_templates.json")
    risk = load_json(ROOT / "config" / "risk_limits.json")
    if template_key not in templates["strategies"]:
        return {}
    template = templates["strategies"][template_key]
    default_budget = float(
        risk.get("strategy_budgets", {})
        .get(template_key, {})
        .get("default_cycle_budget_usd")
        or template.get("default_cycle_budget_usd")
        or 50
    )
    budget = float(budget_override or default_budget) * float(prediction.get("league_scale") or 1.0)
    budget = min(budget, float(risk.get("global", {}).get("max_single_market_budget_usd", 80)))
    ladders = template.get("standard_buy_ladders") or []
    total = sum(float(item.get("amount_usd") or 0) for item in ladders)
    scale = budget / total if total > 0 else 1.0
    buy_ladders = [
        {"price": float(item["price"]), "amount_usd": round(float(item["amount_usd"]) * scale, 2)}
        for item in ladders
    ]
    plan: dict[str, Any] = {
        "version": "mvp-0.2",
        "mode": "config_only",
        "amount_mode": "fixed_usd",
        "market_slug": str(prediction["event_slug"]),
        "market_title": str(prediction["event"]),
        "side": prediction["favorite"] if template_key == "B_FAVORITE_DIP" else prediction["underdog"],
        "strategy_type": template_key,
        "match_budget": round(budget, 2),
        "cycle_budget": round(budget, 2),
        "buy_ladders": buy_ladders,
        "sell_plan": [
            {"price": float(s["price"]), "sell_cost_basis_usd": float(s["sell_cost_basis_usd"])}
            for s in (template.get("standard_sell_plan") or [])
        ],
        "lottery_cost_basis_usd": float(template.get("lottery_cost_basis_usd") or 0),
        "max_cycles": 1,
        "stop_new_entry_below": float(template.get("stop_new_entry_below") or 0),
        "stop_new_entry_above": float(template.get("stop_new_entry_above") or 0.95),
        "operator_note": "由 prematch_predictor 赛前预测生成；执行前确认预测与档位。",
    }
    if template_key in ("B_FAVORITE_DIP", "A_STANDARD_MID_REVERSAL"):
        plan["stop_loss"] = {
            "price": float(template.get("stop_new_entry_below") or 0),
            "sell_cost_basis_usd": round(budget, 2),
        }
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="V2-S2 pre-match pattern prediction + order plan")
    parser.add_argument("--slug", default="")
    parser.add_argument("--event-file", default="", help="Offline test: event JSON.")
    parser.add_argument(
        "--strategy",
        default="auto",
        choices=["auto", "B_FAVORITE_DIP", "A_DEEP_REVERSAL", "A_STANDARD_MID_REVERSAL"],
    )
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--pending-dir", default=str(DEFAULT_PENDING_DIR))
    args = parser.parse_args()

    if args.event_file:
        event = load_json(Path(args.event_file))
    elif args.slug:
        event = fetch_event(args.slug)
    else:
        parser.error("需要 --slug 或 --event-file")
    if not event:
        raise SystemExit("event not found")

    team_profiles = load_team_profiles()
    prediction = predict(event, team_profiles, args.strategy)
    plan = build_plan(prediction, args.budget)

    print("=== V2-S2 赛前预测 ===")
    print(f"比赛：{prediction['event']} @ {prediction['start_time']}")
    print(f"热门：{prediction['favorite']} {prediction['fav_price']:.2f} / 下狗：{prediction['underdog']} {prediction['und_price']:.2f}")
    print(f"赛区：{prediction['region']}（仓位系数 {prediction['league_scale']}） | 形态气候：{prediction['climate']}")
    for p in prediction["predictions"]:
        print(f"  预测 {p['pattern']} [{p['confidence']}]：{p['reason']}")
    for reason in prediction["reasons"]:
        print(f"  依据：{reason}")
    print(f"推荐策略：{prediction['recommended_strategy'] or '（观察，不挂单）'}")

    if not plan:
        print("无推荐策略，赛前不挂单（等盘中形态确认）。")
        return 0

    pending_dir = Path(args.pending_dir)
    pending_dir.mkdir(parents=True, exist_ok=True)
    config_path = pending_dir / f"{prediction['event_slug']}__{prediction['recommended_strategy']}.json"
    write_json(config_path, plan)
    print(f"\n=== 赛前预挂单计划（dry-run）===")
    cmd = [
        sys.executable,
        str(GRID_RUNNER),
        "--plan",
        str(config_path),
        "--resolve-token",
        "--dry-run",
    ]
    try:
        subprocess.run(cmd, check=False)
    except Exception as exc:  # noqa: BLE001 - prediction/plan still valid without dry-run
        print(f"[prematch] dry-run 未执行（{exc}）；计划文件已生成，可手动运行执行命令。")
    print(f"\n计划文件：{config_path}")
    print(
        f"真实执行（确认后）：python3 tools/grid_plan_runner.py --plan {config_path} "
        f"--resolve-token --place-only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
