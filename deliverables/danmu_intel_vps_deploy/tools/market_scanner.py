#!/usr/bin/env python3
"""Opportunity scanner for discovery patterns.

It can scan local backtest JSON files or public live Polymarket data. It only
produces candidate lists and reports; it never places orders.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATTERN_CONFIG = ROOT / "config" / "discovery_patterns.json"
DEFAULT_WATCHLIST_CONFIG = ROOT / "config" / "market_watchlist.json"
DEFAULT_OUTPUT_JSON = ROOT / "runtime" / "opportunity_candidates.json"
DEFAULT_OUTPUT_EVENTS = ROOT / "runtime" / "watchlist_events.json"
DEFAULT_ACTION_QUEUE = ROOT / "runtime" / "candidate_action_queue.json"
DEFAULT_OUTPUT_REPORT = ROOT / "reports" / f"opportunity_scan_{datetime.now(timezone.utc):%Y-%m-%d}.md"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


@dataclass
class Candidate:
    event_title: str
    event_slug: str
    market_title: str
    market_slug: str
    pattern: str
    subtype: str
    route_to_strategy: str
    execution_mode: str
    required_execution_protection: str
    opportunity_score: int
    reasons: list[str]
    metrics: dict[str, Any]
    source_file: str


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def http_json(url: str, params: dict[str, Any] | None = None) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "polymarket-opportunity-scanner/0.1"},
    )
    last_exc: Exception | None = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:  # noqa: S310 - fixed public APIs
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry public data reads
            last_exc = exc
    raise RuntimeError(f"公共数据接口请求失败: {last_exc}") from last_exc


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def display_strategy(pattern: str, subtype: str) -> str:
    strategy_map = {
        "A_DEEP_REVERSAL": "S1_REVERSAL_GRID",
        "A2_MID_SERIES_REVERSAL": "S1_OBSERVATION_MID_REVERSAL",
        "B_FAVORITE_DIP": "S2_FAVORITE_DIP_GRID",
        "C_DOMINANT_COMPOUNDER": "S3_DOMINANT_PULLBACK_GRID",
        "D_POSITION_RESCUE": "S4_POSITION_MANAGEMENT",
    }
    display = strategy_map.get(pattern, pattern)
    return f"{display} / {subtype}"


def display_strategy_name(pattern: str) -> str:
    return display_strategy(pattern, "").split(" / ", 1)[0]


def strategy_maturity(strategy_id: str) -> str:
    maturity_map = {
        "S1_REVERSAL_GRID": "L3_SMALL_LIVE",
        "S1_OBSERVATION_MID_REVERSAL": "L2_SIMULATION",
        "S2_FAVORITE_DIP_GRID": "L3_SMALL_LIVE",
        "S3_DOMINANT_PULLBACK_GRID": "L2_EXPERIMENTAL",
        "S4_POSITION_MANAGEMENT": "L1_ADVISORY",
    }
    return maturity_map.get(strategy_id, "L0_OBSERVE")


def phenomenon_tags(metrics: dict[str, Any]) -> list[str]:
    tags = [str(tag) for tag in metrics.get("discovery_tags") or []]
    return sorted(set(tags))


def add_phenomenon_tag(candidate: Candidate, tag: str) -> None:
    tags = phenomenon_tags(candidate.metrics)
    tags.append(tag)
    candidate.metrics["discovery_tags"] = sorted(set(tags))
    candidate.metrics["phenomenon_tags"] = candidate.metrics["discovery_tags"]


def candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
    payload = candidate.__dict__.copy()
    metrics = dict(candidate.metrics)
    tags = phenomenon_tags(metrics)
    metrics["phenomenon_tags"] = tags
    metrics["recommended_strategy"] = display_strategy_name(candidate.pattern)
    metrics["recommended_strategy_detail"] = display_strategy(candidate.pattern, candidate.subtype)
    metrics["route_strategy"] = display_strategy_name(candidate.route_to_strategy)
    metrics["strategy_maturity"] = strategy_maturity(metrics["recommended_strategy"])
    payload["metrics"] = metrics
    payload["phenomenon_tags"] = tags
    payload["recommended_strategy"] = metrics["recommended_strategy"]
    payload["recommended_strategy_detail"] = metrics["recommended_strategy_detail"]
    payload["route_strategy"] = metrics["route_strategy"]
    payload["strategy_maturity"] = metrics["strategy_maturity"]
    return payload


def build_action_queue(candidates: list[Candidate], generated_at: str) -> list[dict[str, Any]]:
    """Build the candidate action queue (only actionable candidates)."""
    queue: list[dict[str, Any]] = []
    for candidate in candidates:
        action = str(candidate.metrics.get("action_recommendation") or "review_only")
        if action not in ("can_prepare_trade_plan", "manual_review_before_plan"):
            continue
        metrics = candidate_to_dict(candidate)["metrics"]
        start = candidate.metrics.get("event_start_time")
        try:
            expires = (datetime.fromisoformat(start) + timedelta(hours=4)).isoformat() if start else None
        except Exception:  # noqa: BLE001 - fall back to relative expiry
            expires = None
        if expires is None:
            try:
                expires = (datetime.fromisoformat(generated_at) + timedelta(hours=4)).isoformat()
            except Exception:  # noqa: BLE001 - keep None
                expires = None
        queue.append(
            {
                "queued_at": generated_at,
                "expires_at": expires,
                "event_slug": candidate.event_slug,
                "event_title": candidate.event_title,
                "market_slug": candidate.market_slug,
                "market_title": candidate.market_title,
                "outcome": str(candidate.metrics.get("outcome") or ""),
                "recommended_strategy": metrics.get("recommended_strategy"),
                "recommended_strategy_detail": metrics.get("recommended_strategy_detail"),
                "route_strategy": metrics.get("route_strategy"),
                "strategy_maturity": metrics.get("strategy_maturity"),
                "action_recommendation": action,
                "opportunity_score": candidate.opportunity_score,
                "liquidity_score": metrics.get("liquidity_score"),
                "reasons": candidate.reasons,
                "metrics": {
                    key: metrics.get(key)
                    for key in (
                        "first",
                        "min",
                        "max",
                        "last",
                        "rebound_from_min",
                        "crosses_50",
                        "spread",
                        "bid_depth_usd_3c",
                        "ask_depth_usd_3c",
                        "event_time_status",
                    )
                },
            }
        )
    return queue


def write_report(
    path: Path,
    candidates: list[Candidate],
    mode: str,
    events: list[dict[str, Any]] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 机会扫描报告",
        "",
        f"生成时间：{datetime.now(timezone.utc).isoformat()}",
        "",
        f"说明：当前模式为 `{mode}`，只做机会发现，不触发实盘下单。",
        "",
    ]
    if diagnostics is not None:
        lines.extend(
            [
                "## 扫描诊断",
                "",
                f"- 抓取事件：{diagnostics.get('fetched_events', '-')}",
                f"- 标题过滤后：{diagnostics.get('after_title_filter', '-')}",
                f"- 时间窗口内：{diagnostics.get('within_time_window', '-')}",
                f"- Watchlist 匹配：{diagnostics.get('watchlist_matches', '-')}",
                f"- 最终赛事：{diagnostics.get('final_events', '-')}",
                f"- 候选机会：{len(candidates)}",
                f"- 标题过滤词：{diagnostics.get('title_filter') or '-'}",
                f"- Watchlist：{'启用' if diagnostics.get('watchlist_enabled') else '未启用'}",
                "",
            ]
        )
        samples = diagnostics.get("sample_after_title_filter") or diagnostics.get("sample_fetched_events") or []
        if samples:
            lines.extend(["事件样本：", ""])
            for sample in samples[:5]:
                lines.append(
                    f"- {sample.get('start_time') or '-'} | {sample.get('title') or '-'} | `{sample.get('slug') or '-'}`"
                )
            lines.append("")
    if events is not None:
        lines.extend(["## 赛事时间线", ""])
        if not events:
            lines.extend(["暂无 watchlist 赛事。", ""])
        for idx, event in enumerate(events, start=1):
            lines.extend(
                [
                    f"{idx}. {event.get('start_time') or '-'} | {event.get('time_status') or '-'} | "
                    f"{event.get('watchlist_group') or '-'} | {event.get('title') or '-'}",
                    f"   slug: `{event.get('slug') or '-'}` | winner markets: {event.get('winner_market_count', 0)} | "
                    f"series markets: {event.get('series_market_count', 0)} | all markets: {event.get('market_count', 0)}",
                    "",
                ]
            )
    lines.extend(["## 候选机会", ""])
    if not candidates:
        lines.extend(["暂无候选。", ""])
    for idx, item in enumerate(candidates, start=1):
        metrics = item.metrics
        lines.extend(
            [
                f"### {idx}. {item.event_title}",
                "",
                f"- 建议策略：{display_strategy(item.pattern, item.subtype)}",
                f"- 现象标签：{', '.join(phenomenon_tags(metrics)) or '-'}",
                f"- 市场：{item.market_title}",
                f"- 路由策略：{display_strategy_name(item.route_to_strategy)}",
                f"- 成熟度：{strategy_maturity(display_strategy_name(item.pattern))}",
                f"- 执行模式：{item.execution_mode}",
                f"- 必须保护：{item.required_execution_protection}",
                f"- 机会分：{item.opportunity_score}",
                f"- 流动性分：{metrics.get('liquidity_score', '-')}",
                f"- 建议动作：{metrics.get('action_recommendation', 'review_only')}",
                f"- 方向：{metrics.get('outcome') or '-'}",
                f"- 价格：first {metrics.get('first')}, min {metrics.get('min')}, last {metrics.get('last')}, max {metrics.get('max')}, rebound {metrics.get('rebound_from_min')}",
                f"- 盘口：bid {metrics.get('best_bid', '-')}, ask {metrics.get('best_ask', '-')}, spread {metrics.get('spread', '-')}, depth3c bid ${metrics.get('bid_depth_usd_3c', '-')}, ask ${metrics.get('ask_depth_usd_3c', '-')}",
                f"- 50% 穿越：{metrics.get('crosses_50')}",
                f"- 来源：{item.source_file}",
                f"- 赛事池：{metrics.get('watchlist_group', '-')}",
                f"- 开始时间：{metrics.get('event_start_time', '-')}",
                "",
                "理由：",
                "",
            ]
        )
        lines.extend(f"- {reason}" for reason in item.reasons)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def is_series_market(market_title: str) -> bool:
    lowered = market_title.lower()
    return "match winner" in lowered or "series winner" in lowered


def is_game_or_map_market(market_title: str) -> bool:
    lowered = market_title.lower()
    return "game " in lowered or "map " in lowered or " game" in lowered or " map" in lowered


def is_bo_series(event_title: str) -> bool:
    return bool(re.search(r"\bBO[35]\b", event_title, flags=re.IGNORECASE))


def classify_e_values(
    *,
    event_title: str,
    event_slug: str,
    market_title: str,
    market_slug: str,
    outcome: str,
    summary: dict[str, Any],
    pattern: dict[str, Any],
    source_file: str,
    enforce_current_actionable: bool = False,
) -> Candidate | None:
    event_title = str(event_title or "")
    if not is_series_market(market_title):
        return None
    if not is_bo_series(event_title):
        return None

    first = float(summary.get("first", 0) or 0)
    min_price = float(summary.get("min", 0) or 0)
    max_price = float(summary.get("max", 0) or 0)
    last_price = float(summary.get("last", 0) or 0)
    before_min_max = float(summary.get("before_min_max", first) or first)
    rebound = float(summary.get("rebound_from_min", 0) or 0)
    crosses_50 = int(summary.get("crosses_50", 0) or 0)
    points = int(summary.get("points", 0) or 0)
    early_reference = max(first, before_min_max)

    routes = pattern["price_sequence_fallback"]["routes"]
    route: dict[str, Any] | None = None
    reasons = [
        "市场是 Match Winner / Series Winner。",
        "事件标题包含 BO3 / BO5。",
    ]

    if early_reference <= 0.35 and min_price <= 0.30 and rebound >= 0.25:
        route = next(r for r in routes if r["subtype"] == "E-A")
        reasons.append("早段价格不高，低点进入深度折价区，低点后修复空间足够。")
    elif early_reference >= 0.55 and 0.30 <= min_price <= 0.45 and rebound >= 0.25:
        route = next(r for r in routes if r["subtype"] == "E-A2")
        reasons.append("早段是热门/较强侧，随后跌入 30c-45c 中位反转区。")
    elif early_reference >= 0.55 and 0.55 <= min_price <= 0.70 and rebound >= 0.20:
        route = next(r for r in routes if r["subtype"] == "E-B2")
        reasons.append("早段是热门/较强侧，随后跌入 55c-70c 折价修复区。")

    if route is None:
        return None

    if enforce_current_actionable and (last_price <= 0.05 or last_price >= 0.92):
        return None

    score = 40
    score += 15 if rebound >= 0.25 else 0
    score += 10 if crosses_50 >= 3 else 0
    score += 10 if points >= 100 else 0
    score += 10 if max_price >= 0.80 else 0
    score += 15 if max_price >= 0.98 else 0
    score = min(score, 100)

    if route["subtype"] == "E-A2":
        reasons.append("A2 仍是新子类，第一版应先建议/模拟，预算低于标准 A。")
    if route["subtype"] == "E-B2" and min_price < float(route.get("stop_b2_below", 0.4)):
        reasons.append("价格已跌破 B2 失效线，需要重新评估，不应继续按 B2 加仓。")

    reasons.append("成交后必须接入 D2，不能只挂普通止盈。")

    return Candidate(
        event_title=event_title,
        event_slug=event_slug,
        market_title=market_title,
        market_slug=market_slug,
        pattern="E_BO3_SERIES_COMEBACK",
        subtype=str(route["subtype"]),
        route_to_strategy=str(route["route_to_strategy"]),
        execution_mode=str(route["execution_mode"]),
        required_execution_protection=str(pattern["required_execution_protection"]),
        opportunity_score=score,
        reasons=reasons,
        metrics={
            "first": first,
            "min": min_price,
            "max": max_price,
            "last": last_price,
            "before_min_max": before_min_max,
            "early_reference": early_reference,
            "rebound_from_min": rebound,
            "crosses_50": crosses_50,
            "points": points,
            "outcome": outcome,
        },
        source_file=source_file,
    )


def base_candidate(
    *,
    event_title: str,
    event_slug: str,
    market_title: str,
    market_slug: str,
    outcome: str,
    summary: dict[str, Any],
    source_file: str,
    pattern: str,
    subtype: str,
    route_to_strategy: str,
    execution_mode: str,
    score: int,
    reasons: list[str],
) -> Candidate:
    return Candidate(
        event_title=event_title,
        event_slug=event_slug,
        market_title=market_title,
        market_slug=market_slug,
        pattern=pattern,
        subtype=subtype,
        route_to_strategy=route_to_strategy,
        execution_mode=execution_mode,
        required_execution_protection="D2_PROFIT_LOCK",
        opportunity_score=max(0, min(100, score)),
        reasons=reasons,
        metrics={
            "first": float(summary.get("first", 0) or 0),
            "min": float(summary.get("min", 0) or 0),
            "max": float(summary.get("max", 0) or 0),
            "last": float(summary.get("last", 0) or 0),
            "before_min_max": float(summary.get("before_min_max", summary.get("first", 0)) or 0),
            "early_reference": max(
                float(summary.get("first", 0) or 0),
                float(summary.get("before_min_max", summary.get("first", 0)) or 0),
            ),
            "rebound_from_min": float(summary.get("rebound_from_min", 0) or 0),
            "crosses_50": int(summary.get("crosses_50", 0) or 0),
            "points": int(summary.get("points", 0) or 0),
            "outcome": outcome,
        },
        source_file=source_file,
    )


def classify_a_b_values(
    *,
    event_title: str,
    event_slug: str,
    market_title: str,
    market_slug: str,
    outcome: str,
    summary: dict[str, Any],
    source_file: str,
    enforce_current_actionable: bool = False,
) -> list[Candidate]:
    first = float(summary.get("first", 0) or 0)
    min_price = float(summary.get("min", 0) or 0)
    max_price = float(summary.get("max", 0) or 0)
    last_price = float(summary.get("last", 0) or 0)
    before_min_max = float(summary.get("before_min_max", first) or first)
    rebound = float(summary.get("rebound_from_min", 0) or 0)
    crosses_50 = int(summary.get("crosses_50", 0) or 0)
    points = int(summary.get("points", 0) or 0)
    early_reference = max(first, before_min_max)
    candidates: list[Candidate] = []

    if min_price <= 0.35 and rebound >= 0.15:
        if not enforce_current_actionable or 0.05 < last_price < 0.92:
            score = 45
            score += 20 if min_price <= 0.30 else 10
            score += 15 if rebound >= 0.25 else 5
            score += 10 if crosses_50 >= 1 else 0
            score += 10 if points >= 80 else 0
            score += 10 if max_price >= 0.60 else 0
            reasons = [
                "S1现象路由：目标方向出现低价折价区。",
                "低点后存在修复空间，适合按深度反转 / 彩票型观察。",
                "成交后必须接入 D2，不能只挂普通止盈。",
            ]
            if min_price < 0.10:
                reasons.append("价格曾低于 10c，只能按彩票子类处理，金额应更小。")
            candidate = base_candidate(
                event_title=event_title,
                event_slug=event_slug,
                market_title=market_title,
                market_slug=market_slug,
                outcome=outcome,
                summary=summary,
                source_file=source_file,
                pattern="A_DEEP_REVERSAL",
                subtype="A_LOW_PRICE_REVERSAL",
                route_to_strategy="A_DEEP_REVERSAL",
                execution_mode="small_live_allowed",
                score=score,
                reasons=reasons,
            )
            add_phenomenon_tag(candidate, "P1_LOW_PRICE_PANIC")
            if crosses_50 >= 3 or 0.35 <= min_price <= 0.45:
                add_phenomenon_tag(candidate, "P3_MID_RANGE_TANGLE")
            candidates.append(candidate)

    b_current_ok = 0.40 <= last_price <= 0.75 if enforce_current_actionable else min_price >= 0.40
    if early_reference >= 0.65 and min_price <= 0.75 and rebound >= 0.12 and b_current_ok:
        score = 40
        score += 20 if early_reference >= 0.75 else 10
        score += 15 if 0.55 <= last_price <= 0.75 else 5
        score += 15 if rebound >= 0.20 else 5
        score += 10 if min_price >= 0.40 else 0
        score += 10 if points >= 80 else 0
        reasons = [
            "S2现象路由：目标方向早段/赛前是较高概率方，后续出现临时回撤。",
            "当前或历史价格处于强队折价修复观察区。",
            "跌破 40c 后不继续按 S2 加仓，必须重新评估是否切换为 S1 或只观察。",
            "成交后必须接入 D2，不能只挂普通止盈。",
        ]
        candidate = base_candidate(
            event_title=event_title,
            event_slug=event_slug,
            market_title=market_title,
            market_slug=market_slug,
            outcome=outcome,
            summary=summary,
            source_file=source_file,
            pattern="B_FAVORITE_DIP",
            subtype="B_TEMPORARY_DISCOUNT",
            route_to_strategy="B_FAVORITE_DIP",
            execution_mode="small_live_allowed",
            score=score,
            reasons=reasons,
        )
        add_phenomenon_tag(candidate, "P2_FAVORITE_DIP")
        if crosses_50 >= 3:
            add_phenomenon_tag(candidate, "P3_MID_RANGE_TANGLE")
        candidates.append(candidate)

    return candidates


def classify_e_pattern(data: dict[str, Any], pattern: dict[str, Any], source_file: Path) -> Candidate | None:
    return classify_e_values(
        event_title=str(data.get("event_title") or ""),
        event_slug=str(data.get("event_slug") or ""),
        market_title=str(data.get("market_title") or ""),
        market_slug=str(data.get("market_slug") or ""),
        outcome=str(data.get("outcome") or ""),
        summary=data.get("summary") or {},
        pattern=pattern,
        source_file=str(source_file.relative_to(ROOT)),
    )


def attach_e_tag(candidate: Candidate, e_candidate: Candidate | None) -> None:
    if not e_candidate:
        return
    add_phenomenon_tag(candidate, "P5_BO_SERIES_COMEBACK")
    candidate.metrics["legacy_discovery_tag"] = "E_BO3_SERIES_COMEBACK"
    candidate.metrics["e_subtype"] = e_candidate.subtype
    candidate.metrics["phenomenon_subtype"] = e_candidate.subtype
    candidate.reasons.append(f"P5现象背景：BO3/BO5 整场反转，旧 E 子类 {e_candidate.subtype}。")


def classify_strategy_patterns(
    *,
    event_title: str,
    event_slug: str,
    market_title: str,
    market_slug: str,
    outcome: str,
    summary: dict[str, Any],
    source_file: str,
    e_pattern: dict[str, Any],
    enforce_current_actionable: bool = False,
) -> list[Candidate]:
    candidates = classify_a_b_values(
        event_title=event_title,
        event_slug=event_slug,
        market_title=market_title,
        market_slug=market_slug,
        outcome=outcome,
        summary=summary,
        source_file=source_file,
        enforce_current_actionable=enforce_current_actionable,
    )
    e_candidate = classify_e_values(
        event_title=event_title,
        event_slug=event_slug,
        market_title=market_title,
        market_slug=market_slug,
        outcome=outcome,
        summary=summary,
        pattern=e_pattern,
        source_file=source_file,
        enforce_current_actionable=enforce_current_actionable,
    )
    for candidate in candidates:
        attach_e_tag(candidate, e_candidate)
    return candidates


def report_json_from_seed(seed_report: str) -> Path:
    path = ROOT / seed_report
    if path.suffix == ".md":
        return path.with_suffix(".json")
    return path


def collect_source_files(pattern_config: dict[str, Any], all_reports: bool) -> list[Path]:
    if all_reports:
        return sorted((ROOT / "reports").glob("*match_winner*_backtest.json"))

    files: list[Path] = []
    for pattern in pattern_config.get("patterns", {}).values():
        for example in pattern.get("seed_examples", []):
            report = example.get("report")
            if report:
                files.append(report_json_from_seed(str(report)))
    return sorted(set(files))


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


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, timezone.utc)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def event_start_time(event: dict[str, Any]) -> datetime | None:
    # Gamma 语义：真实开赛时间主要在 market 的 gameStartTime 字段；
    # 事件级 startTime 部分赛事存在；startDate 是挂牌/创建时间，
    # 不能当作开赛时间（否则预挂盘会被误判为"正在进行"）。
    for key in ("startTime", "gameStartTime"):
        parsed = parse_datetime(event.get(key))
        if parsed:
            return parsed
    # 事件本身没有开赛时间时，从事件内各 market 的 gameStartTime 取最早值。
    # 同一事件下的 Game/Map/系列赛 market 通常共享同一个 gameStartTime。
    starts: list[datetime] = []
    for market in event.get("markets") or []:
        if not isinstance(market, dict):
            continue
        parsed = parse_datetime(market.get("gameStartTime"))
        if parsed:
            starts.append(parsed)
    if starts:
        return min(starts)
    # 无任何真实开赛信息（如赛季属性盘）时，退回挂牌时间。
    for key in ("startDate", "start_date"):
        parsed = parse_datetime(event.get(key))
        if parsed:
            return parsed
    return None


def event_end_time(event: dict[str, Any]) -> datetime | None:
    for key in ("endDate", "endTime", "closedTime", "end_date"):
        parsed = parse_datetime(event.get(key))
        if parsed:
            return parsed
    return None


def event_time_status(event: dict[str, Any], watchlist: dict[str, Any], now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    window = watchlist.get("time_window", {})
    upcoming_days = float(window.get("upcoming_days", 2))
    recent_started_days = float(window.get("recent_started_days", 2))
    include_unknown = bool(window.get("include_unknown_start_time", True))
    start = event_start_time(event)
    end = event_end_time(event)

    if start is None:
        return include_unknown, "unknown_start_time"
    if now <= start <= now + timedelta(days=upcoming_days):
        return True, "upcoming_within_window"
    if start <= now and start >= now - timedelta(days=recent_started_days):
        if end is None or end >= now or not event.get("closed"):
            return True, "started_recently_or_live"
    return False, "outside_time_window"


def time_status_rank(status: str | None) -> int:
    if status == "started_recently_or_live":
        return 0
    if status == "upcoming_within_window":
        return 1
    if status == "unknown_start_time":
        return 2
    if status == "manual_event_slug":
        return 3
    return 4


def event_time_sort_key(event: dict[str, Any]) -> tuple[int, datetime, int, str]:
    start = event_start_time(event)
    status = str(event.get("_scanner_time_status") or "")
    priority = int((event.get("_scanner_watchlist_group") or {}).get("priority", 0))
    return (
        time_status_rank(status),
        start or datetime.max.replace(tzinfo=timezone.utc),
        -priority,
        str(event.get("title") or event.get("slug") or ""),
    )


def candidate_time_sort_key(candidate: Candidate) -> tuple[int, datetime, int, int, str]:
    start = parse_datetime(candidate.metrics.get("event_start_time"))
    status = str(candidate.metrics.get("event_time_status") or "")
    priority = int(candidate.metrics.get("watchlist_priority") or 0)
    return (
        time_status_rank(status),
        start or datetime.max.replace(tzinfo=timezone.utc),
        -priority,
        -candidate.opportunity_score,
        candidate.event_title,
    )


def keyword_matches(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def watchlist_match(event: dict[str, Any], watchlist: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    title = f"{event.get('title', '')} {event.get('slug', '')}"
    best: dict[str, Any] | None = None
    for key, config in (watchlist.get("games") or {}).items():
        include_keywords = [str(item) for item in config.get("include_keywords", [])]
        league_keywords = [str(item) for item in config.get("league_keywords", [])]
        if include_keywords and not keyword_matches(title, include_keywords):
            continue
        if league_keywords and not keyword_matches(title, league_keywords):
            continue
        candidate = {
            "key": key,
            "name": config.get("name", key),
            "priority": int(config.get("priority", 0)),
        }
        if best is None or candidate["priority"] > int(best.get("priority", 0)):
            best = candidate
    return (best is not None, best or {})


def list_live_events(
    limit: int,
    pages: int,
    title_filter: str,
    watchlist: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    esports_cfg = (watchlist or {}).get("esports") or {}
    diagnostics: dict[str, Any] = {
        "limit": limit,
        "pages": pages,
        "sort_modes": ["ascending_start_date", "descending_start_date"],
        "title_filter": title_filter,
        "watchlist_enabled": bool(watchlist),
        "esports_tag_enabled": bool(esports_cfg.get("enabled", False)),
        "esports_tag_fetched": 0,
        "fetched_events": 0,
        "after_title_filter": 0,
        "within_time_window": None,
        "watchlist_matches": None,
        "final_events": 0,
        "rejected_outside_time_window": 0,
        "rejected_watchlist": 0,
        "sample_fetched_events": [],
        "sample_after_title_filter": [],
        "sample_rejected_outside_time_window": [],
        "sample_rejected_watchlist": [],
    }
    for ascending in ("true", "false"):
        for page in range(max(1, pages)):
            page_data = http_json(
                f"{GAMMA}/events",
                {
                    "active": "true",
                    "closed": "false",
                    "archived": "false",
                    "limit": limit,
                    "offset": page * limit,
                    "order": "startDate",
                    "ascending": ascending,
                },
            )
            if not isinstance(page_data, list) or not page_data:
                break
            diagnostics["fetched_events"] += len(page_data)
            for event in page_data:
                if not isinstance(event, dict):
                    continue
                slug = str(event.get("slug") or "")
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                data.append(event)
                if len(diagnostics["sample_fetched_events"]) < 10:
                    diagnostics["sample_fetched_events"].append(
                        {
                            "title": str(event.get("title") or ""),
                            "slug": slug,
                            "start_time": event_start_time(event).isoformat() if event_start_time(event) else None,
                            "sort_mode": "ascending_start_date" if ascending == "true" else "descending_start_date",
                        }
                    )
    # 电竞赛事用 Esports 标签（tag_id）抓取，避免"最老 + 最新"翻页漏掉
    # 中间段今天/明天的比赛（2026-08-16 实盘验证时发现漏抓 LCK/LPL/LEC/EWC/TI）。
    if esports_cfg.get("enabled", False):
        tag_id = str(esports_cfg.get("tag_id") or "64")
        for page in range(max(1, pages)):
            page_data = http_json(
                f"{GAMMA}/events",
                {
                    "tag_id": tag_id,
                    "closed": "false",
                    "archived": "false",
                    "limit": limit,
                    "offset": page * limit,
                    "order": "startDate",
                    "ascending": "false",
                },
            )
            if not isinstance(page_data, list) or not page_data:
                break
            added = 0
            for event in page_data:
                if not isinstance(event, dict):
                    continue
                slug = str(event.get("slug") or "")
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                data.append(event)
                added += 1
            diagnostics["esports_tag_fetched"] += added
            if added == 0:
                break
    diagnostics["fetched_events"] = len(data)
    if title_filter:
        lowered = title_filter.lower()
        data = [
            event
            for event in data
            if lowered in f"{event.get('title', '')} {event.get('slug', '')}".lower()
        ]
    diagnostics["after_title_filter"] = len(data)
    diagnostics["sample_after_title_filter"] = [
        {
            "title": str(event.get("title") or ""),
            "slug": str(event.get("slug") or ""),
            "start_time": event_start_time(event).isoformat() if event_start_time(event) else None,
        }
        for event in data[:10]
    ]
    if watchlist:
        filtered = []
        within_time = 0
        watchlist_matches = 0
        for event in data:
            in_window, time_status = event_time_status(event, watchlist)
            matches_watchlist, group = watchlist_match(event, watchlist)
            if in_window:
                within_time += 1
            else:
                diagnostics["rejected_outside_time_window"] += 1
                if len(diagnostics["sample_rejected_outside_time_window"]) < 10:
                    diagnostics["sample_rejected_outside_time_window"].append(
                        {
                            "title": str(event.get("title") or ""),
                            "slug": str(event.get("slug") or ""),
                            "start_time": event_start_time(event).isoformat() if event_start_time(event) else None,
                            "time_status": time_status,
                        }
                    )
            if matches_watchlist:
                watchlist_matches += 1
            else:
                diagnostics["rejected_watchlist"] += 1
                if len(diagnostics["sample_rejected_watchlist"]) < 10:
                    diagnostics["sample_rejected_watchlist"].append(
                        {
                            "title": str(event.get("title") or ""),
                            "slug": str(event.get("slug") or ""),
                            "start_time": event_start_time(event).isoformat() if event_start_time(event) else None,
                        }
                    )
            if not in_window or not matches_watchlist:
                continue
            event["_scanner_time_status"] = time_status
            event["_scanner_watchlist_group"] = group
            filtered.append(event)
        diagnostics["within_time_window"] = within_time
        diagnostics["watchlist_matches"] = watchlist_matches
        data = sorted(
            filtered,
            key=event_time_sort_key,
        )
    diagnostics["final_events"] = len(data)
    return data, diagnostics


def market_title(market: dict[str, Any], event: dict[str, Any]) -> str:
    return str(
        market.get("groupItemTitle")
        or market.get("question")
        or market.get("title")
        or event.get("title")
        or ""
    )


def market_slug(market: dict[str, Any], event: dict[str, Any]) -> str:
    return str(market.get("slug") or event.get("slug") or "")


def is_live_series_market(market: dict[str, Any], event: dict[str, Any]) -> bool:
    title = market_title(market, event)
    slug = market_slug(market, event)
    haystack = " ".join(
        str(market.get(key, ""))
        for key in ("question", "groupItemTitle", "slug", "sportsMarketType", "description")
    ).lower()
    if is_series_market(title):
        return True
    if "game" in haystack or "map" in haystack:
        return False
    if slug and slug == str(event.get("slug") or ""):
        return True
    return "winner" in haystack or "moneyline" in haystack


def is_live_winner_market(market: dict[str, Any], event: dict[str, Any]) -> bool:
    title = market_title(market, event).lower()
    haystack = " ".join(
        str(market.get(key, ""))
        for key in ("question", "groupItemTitle", "slug", "sportsMarketType", "description")
    ).lower()
    if any(bad in haystack for bad in ("first blood", "first kill", "total kills", "handicap")):
        return False
    if "winner" in title or "winner" in haystack:
        return True
    if "moneyline" in haystack:
        return True
    slug = market_slug(market, event)
    return bool(slug and slug == str(event.get("slug") or ""))


def summarize_watchlist_event(event: dict[str, Any]) -> dict[str, Any]:
    start = event_start_time(event)
    end = event_end_time(event)
    group = event.get("_scanner_watchlist_group") or {}
    markets = [market for market in event.get("markets") or [] if isinstance(market, dict)]
    series_markets = [market for market in markets if is_live_series_market(market, event)]
    winner_markets = [market for market in markets if is_live_winner_market(market, event)]
    return {
        "title": str(event.get("title") or ""),
        "slug": str(event.get("slug") or ""),
        "start_time": start.isoformat() if start else None,
        "end_time": end.isoformat() if end else None,
        "time_status": event.get("_scanner_time_status"),
        "watchlist_group": group.get("name") or group.get("key"),
        "watchlist_key": group.get("key"),
        "watchlist_priority": group.get("priority"),
        "active": event.get("active"),
        "closed": event.get("closed"),
        "market_count": len(markets),
        "winner_market_count": len(winner_markets),
        "series_market_count": len(series_markets),
        "volume": event.get("volume"),
        "volume24hr": event.get("volume24hr"),
    }


def price_points_from_history(token_id: str, interval: str, fidelity: int) -> list[dict[str, Any]]:
    data = http_json(f"{CLOB}/prices-history", {"market": token_id, "interval": interval, "fidelity": fidelity})
    history = data.get("history") if isinstance(data, dict) else None
    if not isinstance(history, list):
        return []
    points: list[dict[str, Any]] = []
    for item in history:
        if "t" in item and "p" in item:
            points.append({"t": int(item["t"]), "p": float(item["p"])})
    return sorted(points, key=lambda item: item["t"])


def summarize_prices(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not points:
        return None
    prices = [float(point["p"]) for point in points]
    min_i = min(range(len(points)), key=lambda i: prices[i])
    max_i = max(range(len(points)), key=lambda i: prices[i])
    crosses = 0
    for prev, cur in zip(prices, prices[1:]):
        if (prev < 0.5 <= cur) or (prev > 0.5 >= cur):
            crosses += 1
    after_min_max = max(prices[min_i:])
    before_min_max = max(prices[: min_i + 1])
    return {
        "first": prices[0],
        "last": prices[-1],
        "min": prices[min_i],
        "min_ts": points[min_i]["t"],
        "max": prices[max_i],
        "max_ts": points[max_i]["t"],
        "before_min_max": before_min_max,
        "after_min_max": after_min_max,
        "rebound_from_min": after_min_max - prices[min_i],
        "crosses_50": crosses,
        "points": len(points),
    }


def level_tuples(book: dict[str, Any], side: str) -> list[tuple[float, float]]:
    levels: list[tuple[float, float]] = []
    for item in book.get(side) or []:
        if not isinstance(item, dict):
            continue
        try:
            price = float(item.get("price"))
            size = float(item.get("size"))
        except (TypeError, ValueError):
            continue
        if price > 0 and size > 0:
            levels.append((price, size))
    return levels


def book_metrics(token_id: str, depth_window: float = 0.03) -> dict[str, Any]:
    book = http_json(f"{CLOB}/book", {"token_id": token_id})
    if not isinstance(book, dict):
        return {"has_book": False}
    bids = level_tuples(book, "bids")
    asks = level_tuples(book, "asks")
    best_bid = max((price for price, _size in bids), default=None)
    best_ask = min((price for price, _size in asks), default=None)
    spread = None
    if best_bid is not None and best_ask is not None:
        spread = round(max(0.0, best_ask - best_bid), 4)

    bid_depth_usd = 0.0
    ask_depth_usd = 0.0
    if best_bid is not None:
        bid_depth_usd = sum(price * size for price, size in bids if price >= best_bid - depth_window)
    if best_ask is not None:
        ask_depth_usd = sum(price * size for price, size in asks if price <= best_ask + depth_window)

    return {
        "has_book": bool(bids or asks),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "bid_depth_usd_3c": round(bid_depth_usd, 2),
        "ask_depth_usd_3c": round(ask_depth_usd, 2),
        "tick_size": book.get("tick_size"),
        "min_order_size": book.get("min_order_size"),
    }


def apply_liquidity_adjustment(candidate: Candidate) -> None:
    spread = candidate.metrics.get("spread")
    ask_depth = float(candidate.metrics.get("ask_depth_usd_3c") or 0)
    bid_depth = float(candidate.metrics.get("bid_depth_usd_3c") or 0)

    liquidity_score = 50
    if spread is None:
        liquidity_score = 0
        candidate.reasons.append("盘口数据缺失，暂不应自动执行。")
    else:
        spread_value = float(spread)
        if spread_value <= 0.02:
            liquidity_score += 25
        elif spread_value <= 0.05:
            liquidity_score += 10
        else:
            liquidity_score -= 25
            candidate.reasons.append("盘口 spread 偏大，执行时容易被滑点侵蚀。")

    if ask_depth >= 25 and bid_depth >= 25:
        liquidity_score += 25
    elif ask_depth >= 10 and bid_depth >= 10:
        liquidity_score += 10
    else:
        liquidity_score -= 15
        candidate.reasons.append("盘口深度偏薄，需要人工复核或降低金额。")

    liquidity_score = max(0, min(100, liquidity_score))
    candidate.metrics["liquidity_score"] = liquidity_score
    if liquidity_score < 40:
        candidate.opportunity_score = max(0, candidate.opportunity_score - 20)
        candidate.metrics["action_recommendation"] = "observe_only_liquidity_too_thin"
    elif liquidity_score < 60:
        candidate.opportunity_score = max(0, candidate.opportunity_score - 10)
        candidate.metrics["action_recommendation"] = "manual_review_before_plan"
    else:
        candidate.metrics["action_recommendation"] = "can_prepare_trade_plan"


def live_candidates_from_event(
    event: dict[str, Any],
    e_pattern: dict[str, Any],
    interval: str,
    fidelity: int,
    fetch_book: bool,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    title = str(event.get("title") or "")
    slug = str(event.get("slug") or "")

    for market in event.get("markets") or []:
        if not isinstance(market, dict) or not is_live_winner_market(market, event):
            continue
        if market.get("closed") or market.get("active") is False:
            continue
        outcomes = [str(item) for item in parse_json_array(market.get("outcomes"))]
        tokens = [str(item) for item in parse_json_array(market.get("clobTokenIds"))]
        if len(outcomes) != len(tokens):
            continue
        for outcome, token_id in zip(outcomes, tokens):
            try:
                points = price_points_from_history(token_id, interval=interval, fidelity=fidelity)
            except Exception:
                continue
            summary = summarize_prices(points)
            if not summary:
                continue
            strategy_candidates = classify_strategy_patterns(
                event_title=title,
                event_slug=slug,
                market_title=market_title(market, event),
                market_slug=market_slug(market, event),
                outcome=outcome,
                summary=summary,
                e_pattern=e_pattern,
                source_file=f"live:{slug}:{market_slug(market, event)}:{outcome}",
                enforce_current_actionable=True,
            )
            for candidate in strategy_candidates:
                group = event.get("_scanner_watchlist_group") or {}
                start = event_start_time(event)
                candidate.metrics["watchlist_group"] = group.get("name") or group.get("key")
                candidate.metrics["watchlist_priority"] = group.get("priority")
                candidate.metrics["event_start_time"] = start.isoformat() if start else None
                candidate.metrics["event_time_status"] = event.get("_scanner_time_status")
                candidate.reasons.append(
                    f"进入候选池：{candidate.metrics.get('watchlist_group') or 'watchlist'} / "
                    f"{candidate.metrics.get('event_time_status') or 'time_window'}。"
                )
                if fetch_book:
                    try:
                        candidate.metrics.update(book_metrics(token_id))
                    except Exception:
                        candidate.metrics["has_book"] = False
                    apply_liquidity_adjustment(candidate)
                candidates.append(candidate)
    return candidates


def collect_live_candidates(
    args: argparse.Namespace,
    pattern: dict[str, Any],
    watchlist: dict[str, Any] | None,
) -> tuple[list[Candidate], list[dict[str, Any]], dict[str, Any]]:
    if args.event_slug:
        events = [event_by_slug(slug) for slug in args.event_slug]
        diagnostics = {
            "limit": None,
            "pages": None,
            "title_filter": args.title_filter,
            "watchlist_enabled": bool(watchlist),
            "fetched_events": len(events),
            "after_title_filter": len(events),
            "within_time_window": len(events),
            "watchlist_matches": len(events),
            "final_events": len(events),
            "manual_event_slugs": list(args.event_slug),
        }
        if watchlist:
            for event in events:
                _matches, group = watchlist_match(event, watchlist)
                in_window, time_status = event_time_status(event, watchlist)
                event["_scanner_watchlist_group"] = group
                event["_scanner_time_status"] = time_status if in_window else "manual_event_slug"
        events = sorted(events, key=event_time_sort_key)
    else:
        events, diagnostics = list_live_events(args.live_limit, args.live_pages, args.title_filter, watchlist)

    watchlist_events = [summarize_watchlist_event(event) for event in events]
    candidates: list[Candidate] = []
    for event in events:
        candidates.extend(
            live_candidates_from_event(
                event,
                pattern,
                interval=args.history_interval,
                fidelity=args.fidelity,
                fetch_book=not args.skip_book,
            )
        )
    diagnostics["candidate_count"] = len(candidates)
    return candidates, watchlist_events, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan markets for opportunity candidates.")
    parser.add_argument("--patterns", default=str(DEFAULT_PATTERN_CONFIG), help="Discovery pattern config JSON.")
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST_CONFIG), help="Live market watchlist config JSON.")
    parser.add_argument("--no-watchlist", action="store_true", help="Disable live watchlist/time-window filtering.")
    parser.add_argument("--all-reports", action="store_true", help="Scan all local match winner backtest JSON files.")
    parser.add_argument("--live", action="store_true", help="Scan live public Polymarket events. Read-only.")
    parser.add_argument("--event-slug", action="append", default=[], help="Live scan a specific event slug. Can repeat.")
    parser.add_argument("--live-limit", type=int, default=100, help="How many active events to fetch per page in live mode.")
    parser.add_argument("--live-pages", type=int, default=5, help="How many active-event pages to scan before filtering.")
    parser.add_argument("--title-filter", default="", help="Optional live event title/slug filter, e.g. LoL or Dota.")
    parser.add_argument("--history-interval", default="1d", help="CLOB price-history interval in live mode.")
    parser.add_argument("--fidelity", type=int, default=5, help="CLOB price-history fidelity in minutes.")
    parser.add_argument("--skip-book", action="store_true", help="Do not fetch CLOB order books in live mode.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="Candidate JSON output.")
    parser.add_argument("--output-events", default=str(DEFAULT_OUTPUT_EVENTS), help="Live watchlist event JSON output.")
    parser.add_argument("--output-action-queue", default=str(DEFAULT_ACTION_QUEUE), help="Action queue JSON output.")
    parser.add_argument("--output-report", default=str(DEFAULT_OUTPUT_REPORT), help="Markdown report output.")
    args = parser.parse_args()

    pattern_config = load_json(Path(args.patterns))
    watchlist_config = None if args.no_watchlist else load_json(Path(args.watchlist))
    e_pattern = pattern_config["patterns"]["E_BO3_SERIES_COMEBACK"]
    candidates: list[Candidate] = []
    watchlist_events: list[dict[str, Any]] | None = None
    diagnostics: dict[str, Any] | None = None

    mode = "live_scan" if args.live else "offline_backtest_scan"
    if args.live:
        candidates, watchlist_events, diagnostics = collect_live_candidates(args, e_pattern, watchlist_config)
    else:
        for source in collect_source_files(pattern_config, args.all_reports):
            if not source.exists():
                continue
            data = load_json(source)
            candidates.extend(
                classify_strategy_patterns(
                    event_title=str(data.get("event_title") or ""),
                    event_slug=str(data.get("event_slug") or ""),
                    market_title=str(data.get("market_title") or ""),
                    market_slug=str(data.get("market_slug") or ""),
                    outcome=str(data.get("outcome") or ""),
                    summary=data.get("summary") or {},
                    source_file=str(source.relative_to(ROOT)),
                    e_pattern=e_pattern,
                    enforce_current_actionable=False,
                )
            )

    if args.live:
        candidates.sort(key=candidate_time_sort_key)
    else:
        candidates.sort(key=lambda item: item.opportunity_score, reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "count": len(candidates),
        "candidates": [candidate_to_dict(item) for item in candidates],
    }
    if diagnostics is not None:
        payload["diagnostics"] = diagnostics
    write_json(Path(args.output_json), payload)
    if args.live:
        events_payload = {
            "generated_at": payload["generated_at"],
            "mode": mode,
            "count": len(watchlist_events or []),
            "diagnostics": diagnostics or {},
            "events": watchlist_events or [],
        }
        write_json(Path(args.output_events), events_payload)
    queue = build_action_queue(candidates, payload["generated_at"])
    write_json(
        Path(args.output_action_queue),
        {
            "generated_at": payload["generated_at"],
            "mode": mode,
            "count": len(queue),
            "items": queue,
        },
    )
    write_report(Path(args.output_report), candidates, mode, watchlist_events, diagnostics)
    print(f"wrote {len(candidates)} candidates to {args.output_json}")
    if args.live:
        print(f"wrote {len(watchlist_events or [])} watchlist events to {args.output_events}")
    print(f"wrote {len(queue)} actionable items to {args.output_action_queue}")
    print(f"wrote report to {args.output_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
