#!/usr/bin/env python3
"""Build the read-only Stake pre-match intelligence page.

The page normalizes schedule, teams, competitions and main-market prices from
the official Stake Sports Data API. It covers the registered LoL / CS2 / Dota 2
watchlist plus selected football competitions and the NBA.

The tool never logs in, places bets, bypasses access controls, or reads account
credentials. An optional API key is accepted only through STAKE_ODDS_API_KEY.
It never mixes decimal bookmaker odds with Polymarket 0-1 prices.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html
import json
import math
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import prematch_detail
import stake_lmt
import stake_oddin

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "stake_prematch.json"
DEFAULT_WATCHLIST = ROOT / "config" / "market_watchlist.json"
DEFAULT_OUT = ROOT / "reports" / "intel_prematch.html"
DEFAULT_JSON_OUT = ROOT / "reports" / "intel_prematch.json"
DEFAULT_DETAIL_DIR = ROOT / "reports"
BJ = dt.timezone(dt.timedelta(hours=8))

BLOCKED_MARKET_TERMS = (
    "half",
    "quarter",
    "period",
    "minutes",
    "1st ",
    "2nd ",
    "3rd ",
    "4th ",
    "&",
    "total",
    "handicap",
    "correct score",
    "booking",
    "shots",
    "corner",
)
ESPORT_WINNER_NAMES = {
    "match winner",
    "match winner - twoway",
    "moneyline",
}
NBA_WINNER_NAMES = {
    "winner",
    "winner (incl. overtime)",
    "moneyline",
}
FOOTBALL_WINNER_NAMES = {"1x2"}


def parse_ts(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 1000 if number > 10_000_000_000 else number
    raw = str(value).strip()
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", raw):
            number = float(raw)
            return number / 1000 if number > 10_000_000_000 else number
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.timestamp()


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def iso_utc(ts: float | None) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds")


def bj_time(ts: float | None) -> str:
    if not ts:
        return "时间待定"
    return dt.datetime.fromtimestamp(ts, BJ).strftime("%m-%d %H:%M")


def bj_date(ts: float | None) -> str:
    if not ts:
        return "日期待定"
    return dt.datetime.fromtimestamp(ts, BJ).strftime("%Y-%m-%d")


def bj_weekday(ts: float | None) -> str:
    if not ts:
        return ""
    labels = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
    return labels[dt.datetime.fromtimestamp(ts, BJ).weekday()]


def esc(value: Any) -> str:
    if value is None or value == "":
        return ""
    return html.escape(str(value), quote=True)


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def api_json(base_url: str, pathname: str, *, api_key: str = "", tries: int = 3,
             timeout: int = 25) -> Any:
    url = f"{base_url.rstrip('/')}/{pathname.lstrip('/')}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "polymarket-stake-prematch/1.0",
    }
    if api_key:
        headers["X-API-KEY"] = api_key
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(max(1, tries)):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (401, 403, 404, 451):
                break
        except Exception as exc:  # noqa: BLE001 - bounded public read retry
            last_error = exc
        if attempt + 1 < tries:
            time.sleep(min(3.0, 0.5 * (2 ** attempt)))
    raise RuntimeError(f"Stake API request failed: {url}: {last_error}") from last_error


def watchlist_match(event: dict[str, Any], watchlist: dict[str, Any],
                    game_key: str) -> bool:
    game = (watchlist.get("games") or {}).get(game_key) or {}
    text = f"{event.get('title', '')} {event.get('slug', '')}".lower()
    includes = [str(item).lower() for item in game.get("include_keywords", [])]
    leagues = [str(item).lower() for item in game.get("league_keywords", [])]
    return (
        bool(includes)
        and bool(leagues)
        and any(keyword in text for keyword in includes)
        and any(keyword in text for keyword in leagues)
    )


def competitor_names(fixture: dict[str, Any]) -> list[str]:
    competitors = [str(item).strip() for item in fixture.get("competitors") or [] if str(item).strip()]
    if len(competitors) >= 2:
        return competitors[:2]
    name = str(fixture.get("name") or "").strip()
    parts = [part.strip() for part in name.split(" - ", 1)]
    return parts if len(parts) == 2 and all(parts) else []


def flatten_markets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if node.get("id") and node.get("name") and isinstance(node.get("outcomes"), list):
            found[str(node["id"])] = node
            return
        for value in node.values():
            walk(value)

    walk(payload.get("groups") or [])
    return list(found.values())


def grouped_markets(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Flatten markets while retaining the provider's group name."""
    found: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}

    def walk(node: Any, group_name: str) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, group_name)
            return
        if not isinstance(node, dict):
            return
        if node.get("id") and node.get("name") and isinstance(node.get("outcomes"), list):
            found[(group_name.lower(), str(node["id"]))] = (group_name.lower(), node)
            return
        for value in node.values():
            walk(value, group_name)

    for group in payload.get("groups") or []:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name") or "").strip().lower()
        walk(group.get("markets") or [], name)
    return list(found.values())


def player_prop_metric(market_name: str) -> str:
    name = market_name.lower()
    for needle, label in (
        ("total headshots", "爆头"),
        ("total kills", "击杀"),
        ("total assists", "助攻"),
        ("total deaths", "死亡"),
        ("total damage", "伤害"),
        ("total points", "得分"),
        ("total rebounds", "篮板"),
        ("total threes", "三分"),
        ("anytime goalscorer", "进球"),
        ("player goals", "进球"),
        ("player to be carded", "牌"),
    ):
        if needle in name:
            return label
    return ""


def over_under_projection(market: dict[str, Any]) -> dict[str, Any] | None:
    spec_threshold = re.search(
        r"(?:^|\|)threshold=([0-9]+(?:\.[0-9]+)?)(?:\||$)",
        str(market.get("specifiers") or ""),
    )
    outcomes = market.get("outcomes") or []
    over = 0.0
    under = 0.0
    for item in outcomes:
        if not bool(item.get("active")):
            continue
        outcome_name = str(item.get("name") or "").strip().lower()
        odds = parse_float(item.get("odds"), 0.0)
        if outcome_name.startswith("over"):
            over = odds
        elif outcome_name.startswith("under"):
            under = odds
    if None in (over, under) or not over or not under or over <= 1.0 or under <= 1.0:
        return None
    raw_over, raw_under = 1.0 / over, 1.0 / under
    total = raw_over + raw_under
    return {
        "line": parse_float(spec_threshold.group(1), 0.0) if spec_threshold else None,
        "over_fair_probability": round(raw_over / total, 6),
        "under_decimal_odds": round(under, 4),
        "over_decimal_odds": round(over, 4),
    }


def extract_team_market_intel(
    markets: list[dict[str, Any]],
    teams: list[str],
    sport_key: str,
) -> dict[str, Any]:
    """Extract team-level kill baselines from the current fixture markets."""
    if sport_key not in {"lol", "cs2", "dota2"} or len(teams) != 2:
        return {}
    best: dict[str, tuple[float, dict[str, Any]]] = {}
    for market in markets:
        name = str(market.get("name") or "").lower()
        side = ""
        if "match home total kills" in name or "match team1 total kills" in name:
            side = "home"
        elif "match away total kills" in name or "match team2 total kills" in name:
            side = "away"
        if not side:
            continue
        projection = over_under_projection(market)
        if not projection or not projection.get("line"):
            continue
        distance = abs(parse_float(projection.get("over_fair_probability"), 0.5) - 0.5)
        current = best.get(side)
        if current is None or distance < current[0]:
            best[side] = (distance, projection)
    out: dict[str, Any] = {}
    for side, team in (("home", teams[0]), ("away", teams[1])):
        if side in best:
            projection = best[side][1]
            out[team] = {
                "kills_line": projection.get("line"),
                "over_fair_probability": projection.get("over_fair_probability"),
            }
    return out


def normalized_person_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value or "").lower())


def extract_platform_player_intel(
    detail: dict[str, Any],
    teams: list[str],
    sport_key: str,
) -> dict[str, Any]:
    """Extract only participants explicitly exposed by this fixture's markets.

    Esports books expose paired "Duel of Player Kills" markets for each map.
    Their ordered outcomes align to the fixture's home/away order, so the
    participants can be listed without consulting the stale local profiles.
    This is still a market-derived roster, not an official starting lineup.
    """
    if sport_key not in {"lol", "cs2", "dota2"} or len(teams) != 2:
        return {
            "status": "not_applicable",
            "method": "",
            "team_players": {teams[0]: [], teams[1]: []} if len(teams) == 2 else {},
            "unassigned": [],
            "note": "当前板块未把平台球员盘口当作首发阵容。",
        }
    group_rows = [
        market for group_name, market in grouped_markets(detail)
        if group_name == "players"
    ]
    duel_slots: dict[int, tuple[str, str]] = {}
    prop_metrics: dict[str, set[str]] = {}
    prop_projections: dict[str, dict[str, dict[str, Any]]] = {}
    discovered_names: set[str] = set()

    for market in group_rows:
        name = str(market.get("name") or "")
        lowered = name.lower()
        specifiers = str(market.get("specifiers") or "")
        outcomes = market.get("outcomes") or []
        slot_match = re.search(r"(?:^|\|)slot=(\d+)(?:\||$)", specifiers)
        if "duel of player kills" in lowered and slot_match and len(outcomes) >= 2:
            left = str(outcomes[0].get("name") or "").strip()
            right = str(outcomes[1].get("name") or "").strip()
            if left and right and all(item.lower() not in {"draw", "under", "over"} for item in (left, right)):
                duel_slots[int(slot_match.group(1))] = (left, right)
                discovered_names.update((left, right))
        metric = player_prop_metric(name)
        if metric:
            # The prop market name starts with the player identity. Keep only
            # the prefix before the statistic phrase.
            prefix = re.split(
                r"\s+total\s+(?:headshots|kills|assists|deaths|damage|points|rebounds|threes)\b",
                name,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            prefix = re.sub(r"^map\s+\d+\s*-\s*", "", prefix, flags=re.IGNORECASE).strip()
            if prefix and len(prefix) <= 40:
                discovered_names.add(prefix)
                norm = normalized_person_name(prefix)
                prop_metrics.setdefault(norm, set()).add(metric)
                projection = over_under_projection(market)
                if projection:
                    line = parse_float(projection.get("line"), 0.0)
                    distance = abs(parse_float(projection.get("over_fair_probability"), 0.5) - 0.5)
                    current = prop_projections.setdefault(norm, {}).get(metric)
                    current_distance = (
                        abs(parse_float(current.get("over_fair_probability"), 0.5) - 0.5)
                        if current else float("inf")
                    )
                    if distance < current_distance:
                        projection["line"] = line or None
                        prop_projections[norm][metric] = projection

    team_players: dict[str, list[dict[str, Any]]] = {teams[0]: [], teams[1]: []}
    assigned: set[str] = set()
    for slot in sorted(duel_slots):
        left, right = duel_slots[slot]
        for team_index, player_name in ((0, left), (1, right)):
            norm = normalized_person_name(player_name)
            if not norm or norm in assigned:
                continue
            assigned.add(norm)
            team_players[teams[team_index]].append(
                {
                    "name": player_name,
                    "slot": slot,
                    "metrics": sorted(prop_metrics.get(norm, set())),
                    "projections": prop_projections.get(norm, {}),
                }
            )

    unassigned = []
    for player_name in sorted(discovered_names, key=str.lower):
        norm = normalized_person_name(player_name)
        if not norm or norm in assigned:
            continue
        unassigned.append(
            {
                "name": player_name,
                "metrics": sorted(prop_metrics.get(norm, set())),
                "projections": prop_projections.get(norm, {}),
            }
        )

    count = sum(len(items) for items in team_players.values())
    if count >= 10:
        status = "full"
    elif count:
        status = "partial"
    else:
        status = "missing"
    return {
        "status": status,
        "method": "比赛内选手对位盘口＋单人数据盘",
        "team_players": team_players,
        "unassigned": unassigned[:10],
        "note": "盘口可识别参赛选手，但不等于官方首发；角色、替补和临时换人仍需官方确认。",
    }


def winner_market_candidates(markets: list[dict[str, Any]], sport_key: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if sport_key == "football":
        allowed = FOOTBALL_WINNER_NAMES
        expected_sizes = {3}
    elif sport_key == "nba":
        allowed = NBA_WINNER_NAMES
        expected_sizes = {2}
    else:
        allowed = ESPORT_WINNER_NAMES
        expected_sizes = {2}
    for market in markets:
        name = re.sub(r"\s+", " ", str(market.get("name") or "").strip().lower())
        if name not in allowed:
            continue
        # Football has 1x2 variants such as "1x2 (1up)"; only the plain market
        # is comparable. Esports "Match Winner - Twoway" legitimately carries a
        # way=two specifier, so specifiers cannot be rejected globally.
        if sport_key == "football" and str(market.get("specifiers") or "").strip():
            continue
        outcomes = market.get("outcomes") or []
        if len(outcomes) not in expected_sizes:
            continue
        candidates.append(market)
    return candidates


def classify_market_state(markets: list[dict[str, Any]], sport_key: str) -> tuple[str, str]:
    candidates = winner_market_candidates(markets, sport_key)
    if not candidates:
        return "missing", "主市场缺失"
    if any(str(item.get("status") or "").lower() == "active" for item in candidates):
        active = next(item for item in candidates if str(item.get("status") or "").lower() == "active")
        outcomes = active.get("outcomes") or []
        if all(bool(outcome.get("active")) and parse_float(outcome.get("odds"), 0.0) > 1.0 for outcome in outcomes):
            return "available", "有效报价"
        return "partial", "报价不完整"
    if any(str(item.get("status") or "").lower() == "suspended" for item in candidates):
        return "suspended", "盘口暂停"
    return "missing", "主市场不可用"


def normalize_winner(markets: list[dict[str, Any]], sport_key: str) -> dict[str, Any] | None:
    candidates = winner_market_candidates(markets, sport_key)
    if not candidates:
        return None
    active = [
        item for item in candidates
        if str(item.get("status") or "").lower() == "active"
    ]
    if not active:
        return None
    market = active[0]
    outcomes = market.get("outcomes") or []
    odds = [parse_float(item.get("odds"), 0.0) for item in outcomes]
    if not all(bool(item.get("active")) and value > 1.0 for item, value in zip(outcomes, odds)):
        return None
    implied = [1.0 / value for value in odds]
    overround = sum(implied)
    if not (0.9 <= overround <= 2.0):
        return None
    fair = [value / overround for value in implied]
    return {
        "market_id": str(market.get("id") or ""),
        "market_name": str(market.get("name") or ""),
        "market_status": str(market.get("status") or ""),
        "market_type": "three_way" if len(outcomes) == 3 else "two_way",
        "margin": round(overround - 1.0, 6),
        "payout_rate": round(1.0 / overround, 6),
        "updated_at": iso_utc(parse_ts(market.get("updatedAt"))),
        "updated_ts": parse_ts(market.get("updatedAt")) or 0.0,
        "outcomes": [
            {
                "name": str(item.get("name") or ""),
                "decimal_odds": round(odds[index], 4),
                "raw_implied": round(implied[index], 6),
                "fair_probability": round(fair[index], 6),
            }
            for index, item in enumerate(outcomes)
        ],
    }


def tournament_refs_for_sport(
    *,
    config: dict[str, Any],
    sport: dict[str, Any],
    watchlist: dict[str, Any],
    base_url: str,
    api_key: str,
    errors: list[str],
) -> list[dict[str, str]]:
    sport_slug = str(sport.get("sport_slug") or "")
    mode = str(sport.get("mode") or "")
    if mode == "competitions":
        return [
            {
                "category": str(item.get("category") or ""),
                "tournament": str(item.get("tournament") or ""),
                "label": str(item.get("label") or item.get("tournament") or ""),
            }
            for item in sport.get("competitions") or []
            if item.get("category") and item.get("tournament")
        ]
    if mode != "esports_watchlist":
        errors.append(f"{sport.get('key')}: unsupported mode {mode}")
        return []
    try:
        payload = api_json(base_url, f"sports/{sport_slug}/categories", api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - collect as a source gap
        errors.append(f"{sport.get('key')} categories: {exc}")
        return []
    refs: list[dict[str, str]] = []
    include_prefix = str(sport.get("include_prefix") or "")
    for category in payload.get("categories", []) if isinstance(payload, dict) else []:
        if not isinstance(category, dict) or category.get("enabled") is not True:
            continue
        category_slug = str(category.get("slug") or "")
        if not category_slug:
            continue
        try:
            tournaments = api_json(
                base_url,
                f"sports/{sport_slug}/{category_slug}/tournaments",
                api_key=api_key,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{sport.get('key')} {category_slug} tournaments: {exc}")
            continue
        for tournament in tournaments.get("tournaments", []) if isinstance(tournaments, dict) else []:
            if not isinstance(tournament, dict) or tournament.get("enabled") is not True:
                continue
            tournament_slug = str(tournament.get("slug") or "")
            tournament_name = str(tournament.get("name") or "")
            if not tournament_slug:
                continue
            pseudo = {
                "title": f"{include_prefix} Upcoming - {tournament_name}",
                "slug": f"{sport_slug}/{category_slug}/{tournament_slug}",
            }
            if not watchlist_match(pseudo, watchlist, str(sport.get("game_key") or "")):
                continue
            refs.append(
                {
                    "category": category_slug,
                    "tournament": tournament_slug,
                    "label": tournament_name or tournament_slug,
                }
            )
    return refs


def fixture_format(sport_key: str, market: dict[str, Any] | None) -> str:
    if sport_key == "football":
        return "单场"
    if sport_key == "nba":
        return "单场"
    games = market.get("game_numbers") if market else None
    if games:
        return f"BO{5 if max(games) >= 5 else 3}"
    return "赛制待定"


def esports_game_numbers(markets: list[dict[str, Any]]) -> list[int]:
    games: set[int] = set()
    for market in markets:
        if str(market.get("status") or "").lower() != "active":
            continue
        match = re.search(
            r"\b(?:Game|Map)\s+(\d+)\s+Winner\b",
            str(market.get("name") or ""),
            re.IGNORECASE,
        )
        if match:
            games.add(int(match.group(1)))
    return sorted(games)


def fixture_status(fixture: dict[str, Any], start_ts: float, now: float) -> tuple[str, str]:
    raw_status = str(fixture.get("status") or "").lower()
    if raw_status == "live":
        return "live", "进行中"
    if raw_status == "ended":
        return "ended", "已结束"
    if start_ts <= now:
        return "starting", "已到开赛时间"
    return "upcoming", "待开赛"


def normalize_fixture(
    *,
    sport: dict[str, Any],
    competition: dict[str, str],
    fixture: dict[str, Any],
    detail: dict[str, Any],
    now: float,
) -> dict[str, Any] | None:
    start_ts = parse_ts(fixture.get("startTime"))
    teams = competitor_names(fixture)
    if not start_ts or len(teams) != 2:
        return None
    sport_key = str(sport.get("key") or "")
    markets = flatten_markets(detail)
    game_numbers = esports_game_numbers(markets) if sport_key not in {"football", "nba"} else []
    player_intel = extract_platform_player_intel(detail, teams, sport_key)
    team_market_intel = extract_team_market_intel(markets, teams, sport_key)
    player_counts = [len(player_intel["team_players"].get(team, [])) for team in teams]
    if sum(player_counts):
        ai_summary = (
            f"平台选手盘口识别：{teams[0]} {player_counts[0]} 人、{teams[1]} {player_counts[1]} 人；"
            "队伍与选手信息来自本场盘口结构，角色和正式首发待官方确认。"
        )
    elif sport_key in {"lol", "cs2", "dota2"}:
        ai_summary = "本场未提供可识别的电竞选手盘口，名单留空，不用旧画像补位。"
    else:
        ai_summary = "当前板块不把球员盘口当作首发阵容，阵容字段留空。"
    market_state, market_state_label = classify_market_state(markets, sport_key)
    winner = normalize_winner(markets, sport_key)
    status_key, status_label = fixture_status(fixture, start_ts, now)
    fixture_updated = parse_ts(fixture.get("updatedAt")) or 0.0
    market_updated = (winner or {}).get("updated_ts") or 0.0
    source_slug = str(fixture.get("slug") or fixture.get("id") or "")
    game_label = "1X2" if sport_key == "football" else "独赢"
    return {
        "id": f"stake:{source_slug}",
        "sport": sport_key,
        "sport_slug": str(sport.get("sport_slug") or ""),
        "sport_label": str(sport.get("label") or sport_key),
        "sport_short": str(sport.get("short") or sport.get("label") or sport_key),
        "league": competition.get("label") or competition.get("tournament") or "-",
        "league_source_name": competition.get("label") or competition.get("tournament") or "",
        "category": competition.get("category") or "",
        "tournament": competition.get("tournament") or "",
        "teams": teams,
        "name": str(fixture.get("name") or " vs ".join(teams)),
        "start_ts": int(start_ts),
        "start_at_utc": iso_utc(start_ts),
        "start_at_bj": bj_time(start_ts),
        "date_bj": bj_date(start_ts),
        "weekday_bj": bj_weekday(start_ts),
        "format": fixture_format(sport_key, {"game_numbers": game_numbers}),
        "status": status_label,
        "status_key": status_key,
        "fixture_status": str(fixture.get("status") or ""),
        "market_label": game_label,
        "market_state": market_state,
        "market_state_label": market_state_label,
        "winner_market": winner,
        "game_numbers": game_numbers,
        "player_intel": player_intel,
        "team_market_intel": team_market_intel,
        "ai_summary": ai_summary,
        "market_count": len(markets),
        "provider": str(fixture.get("provider") or ""),
        "fixture_slug": source_slug,
        "provider": str(fixture.get("provider") or ""),
        "ext_id": str(fixture.get("extId") or ""),
        "source_url": (
            f"https://odds-data.stake.com/fixtures/{urllib.parse.quote(source_slug)}"
        ),
        "fixture_updated_at": iso_utc(fixture_updated or None),
        "source_updated_at": iso_utc(max(fixture_updated, market_updated) or None),
        "source": "stake_odds_data",
        "source_tier": "B · 赛前跨市场参考",
        "fetched_at": iso_utc(now),
    }


def stake_match_url(row: dict[str, Any]) -> str:
    sport_paths = {
        "football": "soccer",
        "nba": "basketball",
        "lol": "league-of-legends",
        "cs2": "counter-strike",
        "dota2": "dota-2",
    }
    sport = sport_paths.get(str(row.get("sport") or ""), str(row.get("sport") or ""))
    return (
        f"https://stake.com/zh/sports/{sport}/{row.get('category')}/"
        f"{row.get('tournament')}/{row.get('fixture_slug')}"
    )


def lmt_referer(row: dict[str, Any]) -> str:
    return stake_match_url(row)


def summarize_lmt_intel(row: dict[str, Any], deep: dict[str, Any]) -> str:
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    home_form = ((home.get("form") or {}).get("form") or [])[:5]
    away_form = ((away.get("form") or {}).get("form") or [])[:5]
    home_rank = (home.get("league_position") or {}).get("position")
    away_rank = (away.get("league_position") or {}).get("position")
    home_inj = len(home.get("injuries") or [])
    away_inj = len(away.get("injuries") or [])
    lineup_note = []
    for side in (home, away):
        lineup = side.get("usual_lineup") or {}
        if lineup.get("players"):
            lineup_note.append(
                f"{side.get('name')} {lineup.get('formation') or '阵型未知'} "
                f"{side.get('lineup_status') == 'confirmed' and '本场首发' or '近场首发'}"
            )
    return (
        f"排名 {home.get('name') or row['teams'][0]} "
        f"{home_rank or '-'} vs {away.get('name') or row['teams'][1]} {away_rank or '-'}；"
        f"近5场 {'/'.join(home_form) or '-'} vs {'/'.join(away_form) or '-'}；"
        f"伤停 {home_inj}/{away_inj}；"
        + ("、".join(lineup_note) if lineup_note else "首发未公布")
    )


def enrich_lmt_rows(
    rows: list[dict[str, Any]],
    *,
    cache_path: Path,
    workers: int,
) -> dict[str, Any]:
    candidates = [
        row for row in rows
        if row.get("sport") in {"football", "nba"}
        and str(row.get("provider") or "") == "betradar"
        and stake_lmt.sr_match_id(row.get("ext_id"))
    ]
    diagnostics: dict[str, Any] = {
        "candidates": len(candidates),
        "enriched": 0,
        "errors": [],
    }
    if not candidates:
        return diagnostics
    client = stake_lmt.LMTClient(cache_path=cache_path, referer="https://stake.com/zh/sports")

    def fetch(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
        try:
            deep = stake_lmt.build_deep_match(
                client,
                stake_lmt.sr_match_id(row.get("ext_id")),
                referer=lmt_referer(row),
            )
            return row, deep, None
        except Exception as exc:  # noqa: BLE001 - source gaps stay explicit
            return row, None, f"{row.get('fixture_slug')}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        futures = [executor.submit(fetch, row) for row in candidates]
        for future in futures:
            row, deep, error = future.result()
            if error:
                diagnostics["errors"].append(error)
                continue
            if not deep or int((deep.get("coverage") or {}).get("lmtsupport") or 0) <= 0:
                continue
            row["lmt"] = deep
            row["ai_summary"] = summarize_lmt_intel(row, deep)
            row["intel_coverage"] = {
                "team": 2,
                "squad_players": len((deep.get("home") or {}).get("squad") or [])
                + len((deep.get("away") or {}).get("squad") or []),
                "injuries": len((deep.get("home") or {}).get("injuries") or [])
                + len((deep.get("away") or {}).get("injuries") or []),
                "lineups": sum(
                    1 for side in (deep.get("home") or {}, deep.get("away") or {})
                    if (side.get("usual_lineup") or {}).get("players")
                ),
            }
            diagnostics["enriched"] += 1
    diagnostics["error_count"] = len(diagnostics["errors"])
    diagnostics["errors"] = diagnostics["errors"][:20]
    return diagnostics


def _oddin_avg(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("avg")
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def summarize_oddin_intel(row: dict[str, Any], deep: dict[str, Any]) -> str:
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    home_form = "/".join(
        item.get("team_result") or "-"
        for item in (home.get("recent_matches") or [])[:5]
    ) or "-"
    away_form = "/".join(
        item.get("team_result") or "-"
        for item in (away.get("recent_matches") or [])[:5]
    ) or "-"
    home_rate = _oddin_avg(home.get("map_winrate"))
    away_rate = _oddin_avg(away.get("map_winrate"))
    home_players = len(home.get("players") or [])
    away_players = len(away.get("players") or [])
    tournament = deep.get("tournament") or {}
    rank_bits = []
    for team in (home, away):
        standings = [
            item
            for block in tournament.get("standings") or []
            if isinstance(block, dict)
            for item in block.get("standings") or []
            if (item.get("team") or {}).get("id") == team.get("id")
        ]
        if standings:
            rank_bits.append(f"{team.get('name')} #{standings[0].get('rank')}")
    rate_text = (
        f"对局胜率 {home_rate:.0f}% vs {away_rate:.0f}%；"
        if home_rate is not None and away_rate is not None
        else ""
    )
    rank_text = "；".join(rank_bits)
    h2h_count = len((deep.get("head_to_head") or {}).get("matches") or [])
    tournament_name = (tournament.get("metadata") or {}).get("tournament", {}).get("name") or row.get("league")
    return (
        f"{home.get('name') or row['teams'][0]} 近5场 {home_form}，"
        f"{away.get('name') or row['teams'][1]} {away_form}；"
        f"{rate_text}近期选手池 {home_players}+{away_players} 人；"
        f"{rank_text or tournament_name}；"
        f"近况交锋 {h2h_count} 场。"
    )


def enrich_oddin_rows(
    rows: list[dict[str, Any]],
    *,
    cache_path: Path,
    workers: int,
) -> dict[str, Any]:
    candidates = [
        row for row in rows
        if row.get("sport") in {"lol", "cs2", "dota2"}
        and str(row.get("provider") or "") == "oddin"
        and row.get("fixture_slug")
    ]
    diagnostics: dict[str, Any] = {
        "candidates": len(candidates),
        "enriched": 0,
        "metadata_fetched": 0,
        "errors": [],
    }
    if not candidates:
        return diagnostics

    def fetch_page(row: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any] | None, str | None]:
        page_url = stake_match_url(row)
        try:
            params = stake_oddin.fetch_widget_params(
                page_url=page_url,
                cache_path=cache_path,
            )
            return row, page_url, params, None
        except Exception as exc:  # noqa: BLE001 - source gap stays explicit
            return row, page_url, None, f"{row.get('fixture_slug')}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        page_results = list(executor.map(fetch_page, candidates))

    valid_pages: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    for row, page_url, params, error in page_results:
        if error or not params:
            diagnostics["errors"].append(error or f"{row.get('fixture_slug')}: missing widget")
            continue
        diagnostics["metadata_fetched"] += 1
        valid_pages.append((row, page_url, params))
    if not valid_pages:
        diagnostics["error_count"] = len(diagnostics["errors"])
        diagnostics["errors"] = diagnostics["errors"][:20]
        return diagnostics

    brand_token = str(valid_pages[0][2].get("brandToken") or "")
    client = stake_oddin.OddinClient(
        brand_token=brand_token,
        cache_path=cache_path,
        referer=valid_pages[0][1],
    )

    def fetch_deep(
        item: tuple[dict[str, Any], str, dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
        row, page_url, params = item
        try:
            deep = stake_oddin.build_deep_match(client, params, referer=page_url)
            return row, deep, None
        except Exception as exc:  # noqa: BLE001 - source gap stays explicit
            return row, None, f"{row.get('fixture_slug')}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 6))) as executor:
        for row, deep, error in executor.map(fetch_deep, valid_pages):
            if error:
                diagnostics["errors"].append(error)
                continue
            if not deep:
                continue
            row["oddin"] = deep
            row["ai_summary"] = summarize_oddin_intel(row, deep)
            row["intel_coverage"] = deep.get("coverage") or {}
            diagnostics["enriched"] += 1
    diagnostics["error_count"] = len(diagnostics["errors"])
    diagnostics["errors"] = diagnostics["errors"][:20]
    return diagnostics


def collect_snapshot(
    *,
    config: dict[str, Any],
    watchlist: dict[str, Any],
    base_url: str,
    api_key: str,
    now: float,
    horizon_hours: float,
    max_fixtures: int,
    workers: int,
    request_delay_ms: int,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    tournament_rows: list[tuple[dict[str, Any], dict[str, str], dict[str, Any]]] = []
    successful_fixture_lists = 0
    tournaments_seen = 0
    fixtures_seen = 0
    details_seen = 0
    start_floor = now - 10 * 60
    end_ceiling = now + horizon_hours * 3600

    for sport in config.get("sports") or []:
        if not isinstance(sport, dict) or not sport.get("key") or not sport.get("sport_slug"):
            warnings.append(f"忽略无效 sport 配置: {sport!r}")
            continue
        sport_slug = str(sport["sport_slug"])
        refs = tournament_refs_for_sport(
            config=config,
            sport=sport,
            watchlist=watchlist,
            base_url=base_url,
            api_key=api_key,
            errors=errors,
        )
        tournaments_seen += len(refs)
        per_sport: list[tuple[dict[str, Any], dict[str, str], dict[str, Any]]] = []
        for competition in refs:
            category = competition["category"]
            tournament = competition["tournament"]
            try:
                payload = api_json(
                    base_url,
                    f"sports/{sport_slug}/{category}/{tournament}/fixtures",
                    api_key=api_key,
                )
                successful_fixture_lists += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{sport['key']} {category}/{tournament} fixtures: {exc}")
                continue
            fixtures = payload.get("fixtures", []) if isinstance(payload, dict) else []
            fixtures_seen += len(fixtures)
            for fixture in fixtures:
                if not isinstance(fixture, dict) or fixture.get("enabled") is not True:
                    continue
                start = parse_ts(fixture.get("startTime"))
                if not start or start < start_floor or start > end_ceiling:
                    continue
                if str(fixture.get("status") or "").lower() == "ended":
                    continue
                per_sport.append((sport, competition, fixture))
        per_sport.sort(key=lambda row: parse_ts(row[2].get("startTime")) or 0.0)
        cap = int(sport.get("max_fixtures") or config.get("max_per_sport") or 50)
        tournament_rows.extend(per_sport[:max(0, cap)])

    tournament_rows.sort(key=lambda row: parse_ts(row[2].get("startTime")) or 0.0)
    tournament_rows = tournament_rows[:max(0, max_fixtures)]

    rows: list[dict[str, Any]] = []

    def fetch_detail(
        item: tuple[dict[str, Any], dict[str, str], dict[str, Any]]
    ) -> tuple[dict[str, Any], dict[str, str], dict[str, Any], dict[str, Any] | None, str | None]:
        sport, competition, fixture = item
        slug = str(fixture.get("slug") or "")
        if not slug:
            return sport, competition, fixture, None, "fixture missing slug"
        try:
            detail = api_json(
                base_url,
                f"fixtures/{urllib.parse.quote(slug)}",
                api_key=api_key,
            )
            return sport, competition, fixture, detail if isinstance(detail, dict) else {}, None
        except Exception as exc:  # noqa: BLE001
            return sport, competition, fixture, None, f"{slug}: {exc}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as executor:
        futures = []
        for index, item in enumerate(tournament_rows):
            if index and request_delay_ms > 0:
                time.sleep(request_delay_ms / 1000.0)
            futures.append(executor.submit(fetch_detail, item))
        for future in futures:
            sport, competition, fixture, detail, error = future.result()
            if error:
                errors.append(error)
            else:
                details_seen += 1
            row = normalize_fixture(
                sport=sport,
                competition=competition,
                fixture=fixture,
                detail=detail or {},
                now=now,
            )
            if row:
                if error:
                    row["detail_error"] = error
                rows.append(row)

    rows.sort(key=lambda row: (row["start_ts"], row["sport"], row["league"]))
    if not successful_fixture_lists:
        raise RuntimeError("no Stake fixture-list request succeeded; preserving previous page")
    if fixtures_seen == 0:
        raise RuntimeError("Stake returned zero fixtures across all configured competitions")
    if not rows:
        raise RuntimeError("no normalized future fixtures; preserving previous page")

    coverage: dict[str, dict[str, Any]] = {}
    for sport in config.get("sports") or []:
        key = str(sport.get("key") or "")
        sport_rows = [row for row in rows if row["sport"] == key]
        coverage[key] = {
            "label": str(sport.get("label") or key),
            "short": str(sport.get("short") or key),
            "fixtures": len(sport_rows),
            "valid_odds": sum(1 for row in sport_rows if row.get("winner_market")),
            "suspended": sum(1 for row in sport_rows if row.get("market_state") == "suspended"),
            "missing": sum(1 for row in sport_rows if row.get("market_state") == "missing"),
        }

    api_key_mode = "X-API-KEY configured" if api_key else "anonymous/public read"
    return {
        "schema_version": 1,
        "generated_at_utc": iso_utc(now),
        "generated_at_bj": dt.datetime.fromtimestamp(now, BJ).strftime("%Y-%m-%d %H:%M:%S"),
        "horizon_hours": horizon_hours,
        "window_start_utc": iso_utc(start_floor),
        "window_end_utc": iso_utc(end_ceiling),
        "source": {
            "name": "STAKE Sports Data API",
            "base_url": base_url,
            "docs_url": str((config.get("api") or {}).get("docs_url") or ""),
            "openapi_url": str((config.get("api") or {}).get("openapi_url") or ""),
            "access_mode": api_key_mode,
            "pricing_note": (
                "十进制赔率与去水概率是赛前市场共识参考，不是真实胜率、"
                "可成交价格或交易建议。"
            ),
        },
        "stats": {
            "fixtures": len(rows),
            "valid_odds": sum(1 for row in rows if row.get("winner_market")),
            "suspended": sum(1 for row in rows if row.get("market_state") == "suspended"),
            "missing": sum(1 for row in rows if row.get("market_state") == "missing"),
            "sports": sum(1 for item in coverage.values() if item["fixtures"]),
            "tournaments_seen": tournaments_seen,
            "fixtures_seen": fixtures_seen,
            "details_seen": details_seen,
        },
        "coverage": coverage,
        "fixtures": rows,
        "diagnostics": {
            "ok": not errors,
            "successful_fixture_lists": successful_fixture_lists,
            "request_delay_ms": request_delay_ms,
            "warnings": warnings[:20],
            "errors": errors[:30],
            "error_count": len(errors),
        },
    }


def favorite_text(row: dict[str, Any]) -> tuple[str, str]:
    winner = row.get("winner_market") or {}
    outcomes = winner.get("outcomes") or []
    if not outcomes:
        return "暂无有效赛前报价", "gap"
    top = max(outcomes, key=lambda item: parse_float(item.get("fair_probability"), 0.0))
    probability = parse_float(top.get("fair_probability"), 0.0)
    if probability >= 0.72:
        label = "强热门"
    elif probability >= 0.55:
        label = "优势方"
    else:
        label = "接近均势"
    return f"{top.get('name')} · {probability * 100:.1f}% · {label}", "ok"


def outcome_rows(row: dict[str, Any]) -> str:
    winner = row.get("winner_market") or {}
    outcomes = winner.get("outcomes") or []
    if not outcomes:
        return (
            '<div class="market-gap">'
            f'<strong>{esc(row.get("market_state_label") or "报价缺口")}</strong>'
            '<span>不沿用旧赔率，也不把 0 当价格。</span>'
            '</div>'
        )
    rendered = []
    for item in sorted(
        outcomes,
        key=lambda value: parse_float(value.get("fair_probability"), 0.0),
        reverse=True,
    ):
        fair = parse_float(item.get("fair_probability"), 0.0) * 100.0
        odds = parse_float(item.get("decimal_odds"), 0.0)
        rendered.append(
            '<div class="outcome">'
            f'<span class="team">{esc(item.get("name"))}</span>'
            f'<span class="prob">{fair:.1f}%</span>'
            f'<span class="odds">{odds:.2f}</span>'
            f'<i style="--p:{max(0.0, min(100.0, fair)):.1f}%"></i>'
            '</div>'
        )
    return "".join(rendered)


def player_metric_text(player: dict[str, Any]) -> str:
    projections = player.get("projections") or {}
    labels = []
    for metric in player.get("metrics") or []:
        projection = projections.get(metric) or {}
        line = projection.get("line")
        labels.append(f"{metric} {line:g}" if line else metric)
    return " / ".join(labels) or "参与"


def form_badges(form: list[Any]) -> str:
    labels = {"W": "胜", "D": "平", "L": "负"}
    return "".join(
        f'<i class="form-badge form-{esc(str(value).lower())}">{labels.get(str(value), esc(value))}</i>'
        for value in form[:10]
    )


def compact_date(value: Any) -> str:
    utc = str((value or {}).get("utc") or "")
    return utc[:10] if utc else "-"


def render_lmt_team(team: dict[str, Any]) -> str:
    position = team.get("league_position") or {}
    form = (team.get("form") or {}).get("form") or []
    streak = (team.get("form") or {}).get("streak") or {}
    manager = team.get("manager") or {}
    injuries = team.get("injuries") or []
    lineup = team.get("usual_lineup") or {}
    lineup_players = lineup.get("players") or []
    stats = team.get("season_stats") or {}
    key_stats = (
        ("场均进球", "goals_scored"),
        ("场均失球", "goals_conceded"),
        ("射正", "shots_on_goal"),
        ("角球", "corner_kicks"),
        ("控球率", "ball_possession"),
        ("黄牌", "yellow_cards"),
    )
    stat_html = "".join(
        f'<span><b>{esc(label)}</b>{parse_float((stats.get(key) or {}).get("average"), 0.0):.2f}</span>'
        for label, key in key_stats
        if isinstance(stats.get(key), dict)
    )
    injury_html = (
        '<div class="lmt-injuries">'
        + "".join(
            f'<span>{esc(item.get("player"))} · {esc(item.get("status"))}</span>'
            for item in injuries[:8]
        )
        + '</div>'
        if injuries
        else '<p class="lmt-empty">当前伤停列表为空。</p>'
    )
    lineup_html = (
        '<div class="lineup-list">'
        + "".join(
            f'<span><i>{esc(item.get("shirt_number"))}</i>{esc(item.get("name"))}'
            f'<em>{esc(item.get("position_abbr"))}</em></span>'
            for item in lineup_players
        )
        + '</div>'
        if lineup_players
        else '<p class="lmt-empty">本场及近场首发均不可用。</p>'
    )
    recent = "".join(
        f'<li><span>{esc(compact_date(item.get("date")))}</span>'
        f'<b class="res res-{esc(str(item.get("result") or "").lower())}">{esc(item.get("result"))}</b>'
        f'<em>{esc((item.get("opponent") or {}).get("name"))}</em>'
        f'<strong>{esc(item.get("score"))}</strong></li>'
        for item in (team.get("last_matches") or [])[:5]
    )
    scorers = "".join(
        f'<li><span>{esc(item.get("name"))}</span><b>{esc(item.get("goals"))} 球</b></li>'
        for item in (team.get("top_scorers") or [])[:5]
    )
    squad = "".join(
        f'<li><span>{esc(item.get("shirt_number"))}</span><b>{esc(item.get("name"))}</b>'
        f'<em>{esc(item.get("position"))}</em><small>{esc(item.get("nationality"))}</small></li>'
        for item in (team.get("squad") or [])
    )
    return f"""
<section class="lmt-team">
  <div class="lmt-team-head">
    <div><h4>{esc(team.get("name"))}</h4>
      <p>排名 {esc(position.get("position") or "-")} · {esc(int(position.get("wins") or 0))}胜
      {esc(int(position.get("draws") or 0))}平 {esc(int(position.get("losses") or 0))}负 ·
      {esc(int(position.get("points") or 0))} 分</p></div>
    <div class="form-line">{form_badges(form)}</div>
  </div>
  <p class="lmt-meta">状态：当前 {esc(streak.get("value") or 0)} 连
    {esc({"W": "胜", "D": "平", "L": "负"}.get(streak.get("type"), streak.get("type") or "-"))}
    · 主教练：{esc(manager.get("name") or "-")} · 伤停 {len(injuries)} 人</p>
  <div class="stat-strip">{stat_html}</div>
  <details class="lmt-sub"><summary>近 5 场战绩</summary><ul class="recent-list">{recent}</ul></details>
  <details class="lmt-sub" {"open" if lineup_players else ""}><summary>
    预计/已公布首发 · {esc(lineup.get("formation") or "阵型待定")}
    <em>{esc("本场官方" if team.get("lineup_status") == "confirmed" else "近场官方")}</em>
  </summary>{lineup_html}</details>
  <details class="lmt-sub"><summary>伤停名单 · {len(injuries)} 人</summary>{injury_html}</details>
  <div class="scorer-row"><div><h5>队内射手</h5><ul>{scorers or "<li>暂无数据</li>"}</ul></div>
    <div><h5>报名名单 · {len(team.get("squad") or [])} 人</h5>
      <details class="lmt-sub squad-detail"><summary>展开完整名单</summary><ul class="squad-list">{squad}</ul></details>
    </div>
  </div>
</section>"""


def render_lmt_panel(row: dict[str, Any]) -> str:
    deep = row.get("lmt") or {}
    if not deep:
        return ""
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    h2h = deep.get("head_to_head") or {}
    h2h_rows = "".join(
        f'<li><span>{esc(compact_date(item.get("date")))}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} '
        f'{esc((item.get("score") or {}).get("display"))}</b>'
        f'<em>{esc((item.get("away") or {}).get("name"))}</em></li>'
        for item in (h2h.get("matches") or [])[:5]
    )
    table = (deep.get("league") or {}).get("tables") or []
    table_html = ""
    if table:
        is_nba_table = any(
            item.get("win_pct") is not None
            for item in table[0].get("rows") or []
        )
        if is_nba_table:
            table_rows = "".join(
                f'<tr><td>{esc(item.get("position"))}</td><td>{esc((item.get("team") or {}).get("name"))}</td>'
                f'<td>{esc(item.get("played"))}</td><td>{esc(item.get("wins"))}</td>'
                f'<td>{esc(item.get("losses"))}</td><td>{oddin_rate(item.get("win_pct"))}</td>'
                f'<td>{esc(item.get("last_ten_wins"))}-{esc(item.get("last_ten_losses"))}</td>'
                f'<td>{esc(item.get("home_wins"))}-{esc(item.get("home_losses"))}</td>'
                f'<td>{esc(item.get("away_wins"))}-{esc(item.get("away_losses"))}</td></tr>'
                for item in table[0].get("rows") or []
            )
            table_html = (
                '<details class="lmt-sub league-detail"><summary>'
                f'{esc(table[0].get("name"))}排名 · 常规赛记录'
                '</summary><div class="table-scroll"><table class="lmt-table"><thead><tr>'
                '<th>#</th><th>队伍</th><th>赛</th><th>胜</th><th>负</th><th>胜率</th>'
                '<th>近10</th><th>主场</th><th>客场</th>'
                f'</tr></thead><tbody>{table_rows}</tbody></table></div></details>'
            )
        else:
            table_rows = "".join(
                f'<tr><td>{esc(item.get("position"))}</td><td>{esc((item.get("team") or {}).get("name"))}</td>'
                f'<td>{esc(item.get("played"))}</td><td>{esc(item.get("wins"))}</td>'
                f'<td>{esc(item.get("draws"))}</td><td>{esc(item.get("losses"))}</td>'
                f'<td>{esc(item.get("goal_diff"))}</td><td>{esc(item.get("points"))}</td></tr>'
                for item in table[0].get("rows") or []
            )
            table_html = (
                '<details class="lmt-sub league-detail"><summary>'
                f'{esc(table[0].get("name"))}积分榜 · 第 {esc(table[0].get("round"))}/{esc(table[0].get("max_rounds"))} 轮'
                '</summary><div class="table-scroll"><table class="lmt-table"><thead><tr>'
                '<th>#</th><th>队伍</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>净胜</th><th>分</th>'
                f'</tr></thead><tbody>{table_rows}</tbody></table></div></details>'
            )
    return f"""
<details class="deep-pack">
  <summary>完整赛前数据
    <em>排名 · 状态 · 近况 · 伤停 · 首发 · 名单 · H2H</em>
  </summary>
  <div class="h2h-summary">
    <b>{esc(home.get("name"))}</b>
    <span>近 {len(h2h.get("matches") or [])} 次：{esc(int(h2h.get("home_wins") or 0))} 胜
      {esc(int(h2h.get("draws") or 0))} 平 {esc(int(h2h.get("away_wins") or 0))} 负</span>
    <b>{esc(away.get("name"))}</b>
  </div>
  <div class="lmt-teams">{render_lmt_team(home)}{render_lmt_team(away)}</div>
  <details class="lmt-sub"><summary>历史交锋 · 最近 5 场</summary><ul class="h2h-list">{h2h_rows}</ul></details>
  {table_html}
</details>"""


def oddin_date(value: Any) -> str:
    raw = str(value or "")
    return raw[:10] if raw else "-"


def oddin_form(values: list[Any]) -> str:
    labels = {"W": "胜", "L": "负"}
    return "".join(
        f'<i class="form-badge form-{esc(str(value).lower())}">'
        f'{labels.get(str(value), esc(value))}</i>'
        for value in (values or [])[:8]
    )


def oddin_pct(value: Any, digits: int = 1) -> str:
    number = _oddin_avg(value)
    return "-" if number is None else f"{number:.{digits}f}%"


def oddin_number(value: Any, digits: int = 2) -> str:
    number = _oddin_avg(value)
    return "-" if number is None else f"{number:.{digits}f}"


def oddin_rate(value: Any, digits: int = 0) -> str:
    number = _oddin_avg(value)
    if number is None:
        return "-"
    if 0 < abs(number) <= 1:
        number *= 100
    return f"{number:.{digits}f}%"


def oddin_team_metrics(team: dict[str, Any], game: str) -> list[tuple[str, str]]:
    stats = team.get("metrics") or {}
    def grouped(name: str) -> dict[str, Any]:
        value = stats.get(name) or {}
        return value.get("all") if isinstance(value, dict) else value
    if game == "csgo":
        return [
            ("对局胜率", oddin_pct(team.get("map_winrate"))),
            ("回合胜率", oddin_pct(grouped("overallRoundWinrate"))),
            ("K/D", oddin_number(grouped("killsOverDeaths"), 2)),
            ("每回合伤害", oddin_number(grouped("damage"), 1)),
            ("爆头率", oddin_pct(grouped("headshotRate"))),
            ("首杀/回合", oddin_number(grouped("openingKills"), 3)),
        ]
    if game == "dota2":
        return [
            ("对局胜率", oddin_pct(team.get("map_winrate"))),
            ("K/D", oddin_number(grouped("killsOverDeaths"), 2)),
            ("击杀/分钟", oddin_number(grouped("kills"), 2)),
            ("经济/分钟", oddin_number(grouped("gold"), 0)),
            ("英雄伤害/分钟", oddin_number(grouped("heroDamage"), 0)),
            ("场均时长", oddin_number(grouped("duration"), 1)),
        ]
    return [
        ("对局胜率", oddin_pct(team.get("map_winrate"))),
        ("K/D", oddin_number(grouped("killsOverDeaths"), 2)),
        ("15 分经济差", oddin_number(grouped("goldDiffAt15mins"), 0)),
        ("场均小龙", oddin_number(grouped("dragonKills"), 2)),
        ("场均大龙", oddin_number(grouped("baronKills"), 2)),
        ("场均推塔", oddin_number(grouped("turretKills"), 2)),
    ]


def oddin_player_metrics(player: dict[str, Any], game: str) -> list[tuple[str, str]]:
    stats = player.get("metrics") or {}
    if game == "csgo":
        return [
            ("K/D", oddin_number(stats.get("killsOverDeaths"), 2)),
            ("ADR", oddin_number(stats.get("damage"), 1)),
            ("HS", oddin_pct(stats.get("headshotRate"))),
            ("首杀", oddin_number(stats.get("openingKills"), 3)),
            ("多杀", oddin_number(stats.get("multiKillRounds"), 3)),
            ("残局", oddin_number(stats.get("clutchRounds"), 3)),
        ]
    if game == "dota2":
        return [
            ("KDA", oddin_number(stats.get("killsDeathsAssists"), 2)),
            ("参团率", oddin_rate(stats.get("killParticipation"))),
            ("补刀/分", oddin_number(stats.get("creepScore"), 2)),
            ("英雄伤害", oddin_number(stats.get("heroDamage"), 0)),
        ]
    return [
        ("KDA", oddin_number(stats.get("killsDeathsAssists"), 2)),
        ("参团率", oddin_rate(stats.get("killParticipation"))),
        ("15 分经济差", oddin_number(stats.get("goldDiffAt15mins"), 0)),
        ("视野", oddin_number(stats.get("visionScore"), 1)),
        ("英雄伤害", oddin_number(stats.get("championDamage"), 0)),
    ]


def oddin_pool_html(team: dict[str, Any], game: str) -> str:
    items = [item for item in team.get("favorites") or [] if isinstance(item, dict)]
    map_items = [
        item for item in team.get("map_pool") or [] if isinstance(item, dict)
    ]
    if not items:
        if not map_items:
            return '<p class="lmt-empty">暂无池子数据。</p>'
    if game == "csgo" and map_items:
        rows = "".join(
            f'<tr><td>{esc(item.get("name"))}</td>'
            f'<td>{oddin_pct(item.get("win_rate"))}</td>'
            f'<td>{esc(int((item.get("picked") or {}).get("total") or 0))}</td>'
            f'<td>{esc(int((item.get("banned") or {}).get("total") or 0))}</td></tr>'
            for item in map_items[:12]
        )
        return (
            '<div class="table-scroll"><table class="lmt-table oddin-pool-table">'
            '<thead><tr><th>地图</th><th>胜率</th><th>选取</th><th>禁用</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
        )
    if game == "csgo":
        rows = "".join(
            f'<li><span>{esc(item.get("name"))}</span>'
            f'<b>{oddin_number((item.get("metrics") or {}).get("killsWithWeapon"), 0)}</b>'
            f'<em>爆头 {oddin_pct((item.get("metrics") or {}).get("headshotsWithWeapon"))}</em></li>'
            for item in items[:12]
        )
        return f'<ul class="oddin-pool-list"><li class="pool-head"><span>常用武器</span><b>击杀</b><em>爆头率</em></li>{rows}</ul>'
    rows = "".join(
        f'<li><span>{esc(item.get("name"))}</span>'
        f'<b>{oddin_rate((item.get("metrics") or {}).get("pickRate"))}</b>'
        f'<em>禁 {oddin_rate((item.get("metrics") or {}).get("banRate"))}</em></li>'
        for item in sorted(
            items,
            key=lambda value: float(
                ((value.get("metrics") or {}).get("pickRate") or {}).get("total") or 0
            ),
            reverse=True,
        )[:12]
    )
    label = "英雄池" if game == "dota2" else "英雄池"
    return f'<ul class="oddin-pool-list"><li class="pool-head"><span>{label}</span><b>选取</b><em>禁用</em></li>{rows}</ul>'


def oddin_player_html(player: dict[str, Any], game: str) -> str:
    metrics = "".join(
        f"<span><b>{esc(label)}</b>{esc(value)}</span>"
        for label, value in oddin_player_metrics(player, game)
    )
    full_stats = []
    for key, value in (player.get("metrics") or {}).items():
        if not isinstance(value, dict) or not value:
            continue
        avg = value.get("avg")
        percentile = value.get("percentile")
        if avg is None:
            continue
        full_stats.append(
            f'<span>{esc(key)} {float(avg):.3g}'
            + (f" · P{float(percentile):.0f}" if percentile is not None else "")
            + "</span>"
        )
    favourite = player.get("favorites") or []
    favourite_html = (
        '<div class="oddin-favourites">'
        + "".join(
            f'<span>{esc(item.get("name"))}'
            f' · 选 {oddin_rate((item.get("metrics") or {}).get("pickRate"))}'
            f' · 胜 {oddin_rate((item.get("metrics") or {}).get("winRate"))}</span>'
            for item in favourite[:6]
        )
        + "</div>"
        if favourite
        else ""
    )
    return f"""
<details class="oddin-player">
  <summary><b>{esc(player.get("nickname"))}</b><em>{esc(player.get("role") or player.get("real_name") or "")}</em></summary>
  <div class="oddin-player-metrics">{metrics}</div>
  <div class="oddin-stat-tags">{"".join(full_stats)}</div>
  {favourite_html}
</details>"""


def _legacy_render_oddin_team(team: dict[str, Any], game: str) -> str:
    recent = "".join(
        f'<li><span>{esc(oddin_date(item.get("start")))}</span>'
        f'<b class="res res-{esc(str(item.get("team_result") or "").lower())}">'
        f'{esc(item.get("team_result") or "-")}</b>'
        f'<em>{esc((item.get("home") or {}).get("name"))} '
        f'{esc(item.get("score"))} {(item.get("away") or {}).get("name")}</em></li>'
        for item in (team.get("recent_matches") or [])[:8]
    )
    metric_html = "".join(
        f"<span><b>{esc(label)}</b>{esc(value)}</span>"
        for label, value in oddin_team_metrics(team, game)
    )
    players = "".join(
        oddin_player_html(player, game)
        for player in (team.get("players") or [])
    )
    form = [
        item.get("team_result")
        for item in (team.get("recent_matches") or [])
        if item.get("team_result")
    ]
    pool_count = len(team.get("map_pool") or team.get("favorites") or [])
    return f"""
<section class="lmt-team oddin-team">
  <div class="lmt-team-head">
    <div><h4>{esc(team.get("name"))}</h4>
      <p>近三个月 · 最近 {len(team.get("recent_matches") or [])} 场 ·
      选手池 {len(team.get("players") or [])} 人</p></div>
    <div class="form-line">{oddin_form(form)}</div>
  </div>
  <div class="stat-strip">{metric_html}</div>
  <details class="lmt-sub"><summary>近期战绩</summary>
    <ul class="recent-list">{recent or "<li>暂无数据</li>"}</ul>
  </details>
  <details class="lmt-sub" open><summary>
    最近选手池与统计 · {len(team.get("players") or [])} 人
    <em>非本场首发声明</em>
  </summary>{players or '<p class="lmt-empty">暂无选手统计。</p>'}</details>
  <details class="lmt-sub"><summary>
    {esc("地图池" if game == "csgo" else "英雄池")} ·
    {pool_count} 项
  </summary>{oddin_pool_html(team, game)}</details>
</section>"""


def _legacy_render_oddin_tournament(tournament: dict[str, Any], game: str) -> str:
    if not tournament:
        return ""
    metadata = tournament.get("metadata") or {}
    tournament_info = metadata.get("tournament") or {}
    standings_rows = "".join(
        f'<tr><td>{esc(item.get("rank") or "-")}</td>'
        f'<td>{esc((item.get("team") or {}).get("name"))}</td>'
        f'<td>{esc(item.get("matches_won") or 0)}-{esc(item.get("matches_lost") or 0)}</td>'
        f'<td>{esc(item.get("maps_won") or 0)}-{esc(item.get("maps_lost") or 0)}</td>'
        f'<td>{esc(item.get("points") or 0)}</td></tr>'
        for block in tournament.get("standings") or []
        if isinstance(block, dict)
        for item in block.get("standings") or []
        if isinstance(item, dict)
    )
    standings_html = (
        '<div class="table-scroll"><table class="lmt-table">'
        '<thead><tr><th>#</th><th>队伍</th><th>系列赛</th><th>小局</th><th>分</th></tr></thead>'
        f'<tbody>{standings_rows}</tbody></table></div>'
        if standings_rows
        else '<p class="lmt-empty">当前赛事没有可用的积分榜数据。</p>'
    )
    matches = sorted(
        tournament.get("matches") or [],
        key=lambda item: str(item.get("start") or ""),
        reverse=True,
    )
    match_rows = "".join(
        f'<li><span>{esc(oddin_date(item.get("start")))}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} '
        f'{esc(item.get("score"))} {(item.get("away") or {}).get("name")}</b>'
        f'<em>{esc((item.get("winner") or {}).get("name") or "待赛")}</em></li>'
        for item in matches[:24]
    )
    pool_rows = "".join(
        f'<tr><td>{esc(((item.get("map") or item.get("hero") or item.get("champion") or {}).get("name")))}</td>'
        f'<td>{esc(item.get("picks") if item.get("picks") is not None else "-")}</td>'
        f'<td>{esc(item.get("bans") if item.get("bans") is not None else "-")}</td>'
        f'<td>{esc(item.get("wins") if item.get("wins") is not None else "-")}</td></tr>'
        for item in (tournament.get("stats") or {}).get("pools") or []
    )
    brackets = "".join(
        f'<li><span>{esc(item.get("block") or item.get("label"))}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} '
        f'{esc(item.get("home_score"))}-{esc(item.get("away_score"))} '
        f'{esc((item.get("away") or {}).get("name"))}</b></li>'
        for item in tournament.get("brackets") or []
    )
    return f"""
<details class="oddin-tournament">
  <summary>赛事数据 · {esc(tournament_info.get("name") or "赛事")}
    <em>{len(tournament.get("teams") or [])} 队 · {len(tournament.get("matches") or [])} 场</em>
  </summary>
  <div class="oddin-tournament-meta">
    <span>{esc(metadata.get("organizer") or "主办待定")}</span>
    <span>{esc(metadata.get("location") or "地点待定")}</span>
    <span>{esc(metadata.get("prize_pool") or "奖金待定")}</span>
    <span>{esc(oddin_date(tournament_info.get("startTimestamp")))} 至 {esc(oddin_date(tournament_info.get("endTimestamp")))}</span>
  </div>
  <details class="lmt-sub" open><summary>积分榜</summary>{standings_html}</details>
  <details class="lmt-sub"><summary>赛事赛程与结果 · {len(matches)} 场</summary>
    <ul class="oddin-tournament-matches">{match_rows or "<li>暂无赛程</li>"}</ul>
  </details>
  <details class="lmt-sub"><summary>赛事地图 / 英雄统计 · {len((tournament.get("stats") or {}).get("pools") or [])} 项</summary>
    <div class="table-scroll"><table class="lmt-table">
      <thead><tr><th>名称</th><th>选取</th><th>禁用</th><th>胜场</th></tr></thead>
      <tbody>{pool_rows or "<tr><td colspan=4>暂无数据</td></tr>"}</tbody>
    </table></div>
  </details>
  {f'<details class="lmt-sub"><summary>淘汰赛对阵</summary><ul class="h2h-list">{brackets}</ul></details>' if brackets else ''}
</details>"""


def _legacy_render_oddin_panel(row: dict[str, Any]) -> str:
    deep = row.get("oddin") or {}
    if not deep:
        return ""
    game = str(deep.get("game") or "")
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    h2h_data = (deep.get("head_to_head") or {}).get("matches") or []
    h2h = "".join(
        f'<li><span>{esc(oddin_date(item.get("start")))}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} '
        f'{esc(item.get("score"))} {(item.get("away") or {}).get("name")}</b>'
        f'<em>{esc((item.get("winner") or {}).get("name") or "")}</em></li>'
        for item in h2h_data[:8]
    )
    return f"""
<details class="deep-pack oddin-pack">
  <summary>完整电竞赛前数据
    <em>近三个月 · 队伍统计 · 选手池 · 地图/英雄池 · 赛事数据</em>
  </summary>
  <div class="lmt-teams">{render_oddin_team(home, game)}{render_oddin_team(away, game)}</div>
  <details class="lmt-sub"><summary>历史交锋 · {len(h2h_data)} 场</summary>
    <ul class="h2h-list">{h2h or "<li>暂无交锋数据</li>"}</ul>
  </details>
  {render_oddin_tournament(deep.get("tournament") or {}, game)}
</details>"""


def metric_avg(metrics: dict[str, Any], key: str, group: str = "") -> float | None:
    value = metrics.get(key)
    if group and isinstance(value, dict):
        value = value.get(group)
    if not isinstance(value, dict):
        return None
    raw = value.get("avg")
    return parse_float(raw, 0.0) if raw is not None else None


def metric_percentile(metrics: dict[str, Any], key: str, group: str = "") -> float | None:
    value = metrics.get(key)
    if group and isinstance(value, dict):
        value = value.get(group)
    if not isinstance(value, dict):
        return None
    raw = value.get("percentile")
    return parse_float(raw, 0.0) if raw is not None else None


def oddin_result_badge(value: Any) -> str:
    labels = {"W": "胜", "D": "平", "L": "负"}
    code = str(value or "")
    if not code:
        return ""
    return f'<i class="form-badge form-{esc(code.lower())}">{labels.get(code, esc(code))}</i>'


def oddin_recent(team: dict[str, Any]) -> str:
    return "".join(
        oddin_result_badge(item.get("team_result"))
        for item in (team.get("recent_matches") or [])[:5]
    )


def oddin_key_stats(game: str, team: dict[str, Any]) -> str:
    metrics = team.get("metrics") or {}
    if game == "csgo":
        selected = (
            ("回合胜率", metric_avg(metrics, "overallRoundWinrate", "all"), "%"),
            ("击杀/回合", metric_avg(metrics, "kills", "all"), ""),
            ("KD", metric_avg(metrics, "killsOverDeaths", "all"), ""),
            ("ADR", metric_avg(metrics, "damage", "all"), ""),
            ("爆头率", metric_avg(metrics, "headshotRate", "all"), "%"),
            ("首杀/回合", metric_avg(metrics, "openingKills", "all"), ""),
        )
    elif game == "dota2":
        selected = (
            ("击杀/分钟", metric_avg(metrics, "kills", "all"), ""),
            ("KD", metric_avg(metrics, "killsOverDeaths", "all"), ""),
            ("金币/分钟", metric_avg(metrics, "gold", "all"), ""),
            ("英雄伤害/分钟", metric_avg(metrics, "heroDamage", "all"), ""),
            ("肉山", metric_avg(metrics, "roshanKills", "all"), ""),
            ("一血率", metric_avg(metrics, "firstBlood", "all"), "%"),
        )
    else:
        selected = (
            ("击杀/分钟", metric_avg(metrics, "kills", "all"), ""),
            ("KD", metric_avg(metrics, "killsOverDeaths", "all"), ""),
            ("15分钟经济差", metric_avg(metrics, "goldDiffAt15mins", "all"), ""),
            ("小龙", metric_avg(metrics, "dragonKills", "all"), ""),
            ("大龙", metric_avg(metrics, "baronKills", "all"), ""),
            ("一血率", metric_avg(metrics, "firstBlood", "all"), "%"),
        )
    cells = []
    for label, value, suffix in selected:
        if value is None:
            continue
        decimals = 0 if suffix == "%" or abs(value) >= 10 else 2
        cells.append(
            f"<span><b>{esc(label)}</b>{value:.{decimals}f}{suffix}</span>"
        )
    return "".join(cells) or '<span><b>样本</b>暂无</span>'


def oddin_player_line(game: str, player: dict[str, Any]) -> str:
    metrics = player.get("metrics") or {}
    if game == "csgo":
        parts = (
            ("K/D/A", "kills", "deaths", "assists"),
            ("ADR", "damage", "", ""),
            ("HS", "headshotRate", "", ""),
            ("首杀", "openingKills", "", ""),
        )
    elif game == "dota2":
        parts = (
            ("KDA", "killsDeathsAssists", "", ""),
            ("参战", "killParticipation", "", ""),
            ("GPM", "gold", "", ""),
            ("伤害", "heroDamage", "", ""),
        )
    else:
        parts = (
            ("KDA", "killsDeathsAssists", "", ""),
            ("参战", "killParticipation", "", ""),
            ("经济", "gold", "", ""),
            ("补刀", "minionKills", "", ""),
        )
    labels = []
    for label, key, second, third in parts:
        if second:
            values = [
                metric_avg(metrics, item)
                for item in (key, second, third)
            ]
            if all(value is not None for value in values):
                labels.append(
                    f"{label} {values[0]:.2f}/{values[1]:.2f}/{values[2]:.2f}"
                )
        else:
            value = metric_avg(metrics, key)
            if value is not None:
                suffix = "%" if key in {"killParticipation", "headshotRate"} else ""
                labels.append(f"{label} {value:.2f}{suffix}")
    return " · ".join(labels)


def render_oddin_team(team: dict[str, Any], game: str) -> str:
    map_avg = (team.get("map_winrate") or {}).get("avg")
    sample = (team.get("map_winrate") or {}).get("sample_size")
    players = "".join(
        '<li class="oddin-player">'
        f'<div><b>{esc(player.get("nickname"))}</b>'
        f'<small>{esc(player.get("real_name") or player.get("role") or "")}</small></div>'
        f'<span>{esc(oddin_player_line(game, player) or "近期样本不足")}</span>'
        '</li>'
        for player in (team.get("players") or [])[:5]
    )
    recent = "".join(
        '<li>'
        f'<span>{esc(str(item.get("planned_start") or "")[:10])}</span>'
        f'{oddin_result_badge(item.get("team_result"))}'
        f'<em>{esc((item.get("away") or {}).get("name") if (item.get("home") or {}).get("id") == team.get("id") else (item.get("home") or {}).get("name"))}</em>'
        f'<strong>{esc(item.get("score") or "-")}</strong>'
        '</li>'
        for item in (team.get("recent_matches") or [])[:5]
    )
    pool_html = ""
    if game == "csgo":
        rows = []
        for item in team.get("map_pool") or []:
            win_rate = (item.get("win_rate") or {}).get("avg")
            pick_rate = (item.get("pick_rate") or {}).get("avg")
            ban_rate = (item.get("ban_rate") or {}).get("avg")
            rounds = item.get("rounds") or {}
            t_rate = ((rounds.get("terrorists") or {}).get("avg"))
            ct_rate = ((rounds.get("counterTerrorists") or {}).get("avg"))
            rows.append(
                "<tr>"
                f"<td>{esc(item.get('name'))}</td>"
                f"<td>{'-' if win_rate is None else f'{win_rate:.0f}%'}</td>"
                f"<td>{'-' if pick_rate is None else f'{pick_rate:.0f}%'}</td>"
                f"<td>{'-' if ban_rate is None else f'{ban_rate:.0f}%'}</td>"
                f"<td>{'-' if t_rate is None else f'{t_rate:.0f}%'}</td>"
                f"<td>{'-' if ct_rate is None else f'{ct_rate:.0f}%'}</td>"
                "</tr>"
            )
        empty_map = '<tr><td colspan="6">暂无样本</td></tr>'
        pool_html = (
            '<details class="lmt-sub"><summary>地图池 · 完整分图与阵营拆分</summary>'
            '<div class="table-scroll"><table class="lmt-table"><thead><tr>'
            '<th>地图</th><th>胜率</th><th>选用</th><th>禁用</th><th>T胜率</th><th>CT胜率</th>'
            f'</tr></thead><tbody>{"".join(rows) or empty_map}</tbody></table></div>'
            '</details>'
        )
        weapon_rows = []
        for item in team.get("favorites") or []:
            metrics = item.get("metrics") or {}
            kills = (metrics.get("killsWithWeapon") or {}).get("avg")
            headshots = (metrics.get("headshotsWithWeapon") or {}).get("avg")
            weapon_rows.append(
                f'<li><b>{esc(item.get("name"))}</b>'
                f'<span>{"-" if kills is None else f"击杀 {kills:.2f}"}</span>'
                f'<span>{("-" if headshots is None else f"爆头 {headshots:.2f}")}</span></li>'
            )
        if weapon_rows:
            pool_html += (
                '<details class="lmt-sub"><summary>常用武器 · 分项效率</summary>'
                f'<ul class="pool-list">{"".join(weapon_rows)}</ul></details>'
            )
    else:
        rows = []
        favorite_total = len(team.get("favorites") or [])
        for item in (team.get("favorites") or [])[:15]:
            metrics = item.get("metrics") or {}
            pick = (metrics.get("pickRate") or {}).get("avg")
            ban = (metrics.get("banRate") or {}).get("avg")
            win = (metrics.get("winRate") or {}).get("avg")
            rows.append(
                f'<li><b>{esc(item.get("name"))}</b>'
                f'<span>{("-" if pick is None else f"选 {pick * 100:.0f}%")}</span>'
                f'<span>{("-" if ban is None else f"禁 {ban * 100:.0f}%")}</span>'
                f'<span>{("-" if win is None else f"胜 {win * 100:.0f}%")}</span></li>'
            )
        pool_label = "英雄池" if game == "dota2" else "英雄池"
        pool_html = (
            f'<details class="lmt-sub"><summary>{pool_label} · 前 15 / 共 {favorite_total} 项</summary>'
            f'<ul class="pool-list">{"".join(rows) or "<li>暂无样本</li>"}</ul></details>'
        )
    return f"""
<section class="lmt-team oddin-team">
  <div class="lmt-team-head">
    <div><h4>{esc(team.get("name"))}</h4>
      <p>地图胜率 {esc("-" if map_avg is None else f"{map_avg:.0f}%")}
      · 样本 {esc(sample if sample is not None else "-")} 张</p></div>
    <div class="form-line">{oddin_recent(team)}</div>
  </div>
  <div class="stat-strip oddin-stat-strip">{oddin_key_stats(game, team)}</div>
  <details class="lmt-sub"><summary>近 5 场战绩</summary><ul class="recent-list">{recent}</ul></details>
  <details class="lmt-sub" open><summary>选手数据 · {len(team.get("players") or [])} 人</summary>
    <ul class="oddin-players">{players or "<li>暂无选手样本</li>"}</ul>
  </details>
  {pool_html}
</section>"""


def render_oddin_tournament(deep: dict[str, Any]) -> str:
    tournament = deep.get("tournament") or {}
    metadata = tournament.get("metadata") or {}
    meta = metadata.get("tournament") or {}
    stats = tournament.get("stats") or {}
    standings = tournament.get("standings") or []
    standing_rows = []
    for block in standings:
        for row in block.get("standings") or []:
            standing_rows.append(
                f'<tr><td>{esc(row.get("rank"))}</td>'
                f'<td>{esc((row.get("team") or {}).get("name"))}</td>'
                f'<td>{esc(int(row.get("matchesWon") or 0))}</td>'
                f'<td>{esc(int(row.get("matchesLost") or 0))}</td>'
                f'<td>{esc(int(row.get("mapsWon") or 0))}</td>'
                f'<td>{esc(int(row.get("mapsLost") or 0))}</td>'
                f'<td>{esc(int(row.get("points") or 0))}</td></tr>'
            )
    standings_html = (
        '<details class="lmt-sub"><summary>赛事积分榜</summary>'
        '<div class="table-scroll"><table class="lmt-table"><thead><tr>'
        '<th>#</th><th>队伍</th><th>胜</th><th>负</th><th>图胜</th><th>图负</th><th>分</th>'
        f'</tr></thead><tbody>{"".join(standing_rows)}</tbody></table></div></details>'
        if standing_rows
        else '<p class="lmt-empty">当前赛事未提供积分榜，不用推算排名补位。</p>'
    )
    game = str(deep.get("game") or "")
    pool_rows = []
    for item in stats.get("pools") or []:
        entity = item.get("map") or item.get("hero") or item.get("champion") or {}
        picks = item.get("picks")
        bans = item.get("bans")
        wins = item.get("wins")
        extra = ""
        if game == "csgo":
            t_winrate = item.get("terroristsWinrateInPercent")
            ct_winrate = item.get("counterTerroristsWinrateInPercent")
            t_text = "-" if t_winrate is None else f"{float(t_winrate):.0f}%"
            ct_text = "-" if ct_winrate is None else f"{float(ct_winrate):.0f}%"
            extra = (
                f'<td>{esc(t_text)}</td>'
                f'<td>{esc(ct_text)}</td>'
            )
        else:
            win_rate = (
                float(wins) / float(picks) * 100.0
                if wins is not None and picks
                else None
            )
            win_text = "-" if win_rate is None else f"{win_rate:.0f}%"
            extra = f'<td>{esc(win_text)}</td>'
        pool_rows.append(
            f'<tr><td>{esc(entity.get("name"))}</td>'
            f'<td>{esc("-" if picks is None else int(float(picks)))}</td>'
            f'<td>{esc("-" if bans is None else int(float(bans)))}</td>{extra}</tr>'
        )
    side_labels = {
        "terrorists": "T 方",
        "counter_terrorists": "CT 方",
        "radiant": "天辉",
        "dire": "夜魇",
        "blue": "蓝色方",
        "red": "红色方",
    }
    side_text = " · ".join(
        f"{side_labels.get(key, key)} {float(value):.1f}%"
        for key, value in (stats.get("side_winrates") or {}).items()
        if value is not None
    )
    pool_header = (
        "<th>T胜率</th><th>CT胜率</th>"
        if game == "csgo"
        else "<th>胜率</th>"
    )
    entity_label = "地图" if game == "csgo" else "英雄"
    pool_details = (
        f'<details class="lmt-sub"><summary>赛事{entity_label}池 · {len(pool_rows)} 项</summary>'
        '<div class="table-scroll"><table class="lmt-table"><thead><tr>'
        f'<th>{entity_label}</th><th>选</th><th>禁</th>{pool_header}'
        f'</tr></thead><tbody>{"".join(pool_rows)}</tbody></table></div></details>'
        if pool_rows
        else ""
    )
    leaders = []
    for label, collection in (("队伍", stats.get("best_teams") or []), ("选手", stats.get("best_players") or [])):
        for item in collection[:5]:
            subject = (
                (item.get("player") or {}).get("nickname")
                if label == "选手"
                else (item.get("team") or {}).get("name")
            )
            if not subject:
                continue
            leaders.append(
                f'<li><b>{esc(subject)}</b>'
                f'<span>{esc(item.get("metric"))}</span>'
                f'<strong>{esc(item.get("value"))}</strong></li>'
            )
    leaders_html = (
        f'<details class="lmt-sub"><summary>赛事领先数据</summary>'
        f'<ul class="leader-list">{"".join(leaders)}</ul></details>'
        if leaders
        else ""
    )
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    team_ids = {home.get("id"), away.get("id")}
    relevant_matches = [
        item for item in tournament.get("matches") or []
        if (item.get("home") or {}).get("id") in team_ids
        or (item.get("away") or {}).get("id") in team_ids
    ][:8]
    match_rows = "".join(
        f'<li><span>{esc(str(item.get("planned_start") or "")[:10])}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} vs {esc((item.get("away") or {}).get("name"))}</b>'
        f'<strong>{esc(item.get("score") or "-")}</strong></li>'
        for item in relevant_matches
    )
    schedule_html = (
        f'<details class="lmt-sub"><summary>本场队伍在赛事中的赛程</summary>'
        f'<ul class="match-list">{match_rows}</ul></details>'
        if match_rows
        else ""
    )
    return f"""
<details class="lmt-sub oddin-tournament"><summary>
  赛事数据 · {esc(meta.get("name") or "")}
  <em>{len(tournament.get("teams") or [])} 队 · {len(tournament.get("matches") or [])} 场</em>
</summary>
  <p class="lmt-meta">组织方 {esc(metadata.get("organizer") or "-")}
    · 地点 {esc(metadata.get("location") or "-")}
    · 奖金 {esc(metadata.get("prize_pool") or "-")}
    · {esc(side_text or "阵营胜率暂无")}</p>
  {schedule_html}
  {standings_html}
  {pool_details}
  {leaders_html}
</details>"""


def render_oddin_panel(row: dict[str, Any]) -> str:
    deep = row.get("oddin") or {}
    if not deep:
        return ""
    home = deep.get("home") or {}
    away = deep.get("away") or {}
    h2h = deep.get("head_to_head") or {}
    h2h_rows = "".join(
        '<li>'
        f'<span>{esc(str(item.get("planned_start") or "")[:10])}</span>'
        f'<b>{esc((item.get("home") or {}).get("name"))} '
        f'{esc(item.get("score") or "-")}</b>'
        f'<em>{esc((item.get("away") or {}).get("name"))}</em>'
        '</li>'
        for item in (h2h.get("matches") or [])[:5]
    )
    game = str(deep.get("game") or "")
    coverage = deep.get("coverage") or {}
    pool_count = (
        int(coverage.get("map_pool") or 0)
        if game == "csgo"
        else int(coverage.get("favorites") or 0)
    )
    return f"""
<details class="deep-pack oddin-pack">
  <summary>完整赛前数据
    <em>选手 {int(coverage.get("players") or 0)} 人 · 地图/英雄池 {pool_count} 项
      · 交锋 {int(coverage.get("h2h") or 0)} 场 · 赛事池 {int(coverage.get("pool_rows") or 0)} 项</em>
  </summary>
  <div class="h2h-summary">
    <b>{esc(home.get("name"))}</b>
    <span>H2H {esc(int(h2h.get("home_wins") or 0))} 胜 · {esc(int(h2h.get("away_wins") or 0))} 负</span>
    <b>{esc(away.get("name"))}</b>
  </div>
  <div class="lmt-teams">{render_oddin_team(home, game)}{render_oddin_team(away, game)}</div>
  <details class="lmt-sub"><summary>历史交锋 · 最近 {len(h2h.get("matches") or [])} 场</summary>
    <ul class="h2h-list">{h2h_rows or "<li>暂无可核验交锋</li>"}</ul>
  </details>
  {render_oddin_tournament(deep)}
</details>"""


def render_cards(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["date_bj"], []).append(row)
    blocks: list[str] = []
    for date, group in grouped.items():
        cards = []
        for row in group:
            detail_url = row.get("detail_url") or prematch_detail.filename_for(row)
            summary, state = favorite_text(row)
            updated = row.get("source_updated_at") or row.get("fixture_updated_at") or "-"
            player_intel = row.get("player_intel") or {}
            team_players = player_intel.get("team_players") or {}
            team_market_intel = row.get("team_market_intel") or {}
            intel_panels = []
            roster_count = 0
            for team_name in row.get("teams", []):
                roster = team_players.get(team_name) or []
                roster_count += len(roster)
                team_kills_line = parse_float(
                    (team_market_intel.get(team_name) or {}).get("kills_line"),
                    0.0,
                )
                team_metric = (
                    f"击杀基准 {team_kills_line:g} · {len(roster)} 人"
                    if team_kills_line
                    else f"{len(roster)} 人 · 盘口识别"
                )
                roster_html = (
                    '<ul class="roster">'
                    + "".join(
                        '<li>'
                        f'<b>{esc(item.get("name"))}</b>'
                        f'<span>槽 {esc(item.get("slot"))}</span>'
                        f'<em>{esc(player_metric_text(item))}</em>'
                        '</li>'
                        for item in roster
                    )
                    + '</ul>'
                    if roster
                    else '<p class="intel-empty">本场未发现该队的可识别选手盘口。</p>'
                )
                intel_panels.append(
                    '<div class="team-intel">'
                    f'<div class="team-intel-head"><strong>{esc(team_name)}</strong>'
                    f'<small>{esc(team_metric)}</small></div>'
                    '<div class="roster-title">平台可识别选手</div>'
                    f'{roster_html}'
                    '</div>'
                )
            unassigned = player_intel.get("unassigned") or []
            if unassigned:
                intel_panels.append(
                    '<div class="team-intel">'
                    '<div class="team-intel-head"><strong>其他盘口球员</strong>'
                    f'<small>{len(unassigned)} 人 · 队伍未绑定</small></div>'
                    '<div class="intel-tags">'
                    + "".join(
                        f'<span class="intel-tag">{esc(item.get("name"))}'
                        f'{" · " + esc(player_metric_text(item)) if item.get("metrics") else ""}</span>'
                        for item in unassigned
                    )
                    + '</div></div>'
                )
            ai_summary = row.get("ai_summary") or "暂无额外的选手或名单信息。"
            cards.append(
                f'<article class="event" data-sport="{esc(row["sport"])}" '
                f'data-search="{esc(" ".join([row["sport_label"], row["league"], *row["teams"], row["name"]]))}">'
                '<div class="event-top">'
                f'<div><span class="sport-badge s-{esc(row["sport"])}">{esc(row["sport_short"])}</span>'
                f'<span class="league">{esc(row["league"])}</span></div>'
                f'<time>{esc(row["start_at_bj"])}</time>'
                '</div>'
                '<div class="event-main">'
                f'<h3>{esc(row["teams"][0])}<span>vs</span>{esc(row["teams"][1])}</h3>'
                f'<div class="event-meta">{esc(row["format"])} · {esc(row["market_label"])} · '
                f'<span class="status {esc(row["status_key"])}">{esc(row["status"])}</span></div>'
                '</div>'
                f'<div class="consensus {state}">{esc(summary)}</div>'
                '<div class="market-head"><span>队伍</span><span>去水概率</span><span>十进制</span></div>'
                f'<div class="outcomes">{outcome_rows(row)}</div>'
                '<div class="ai-brief"><span>AI 研判</span>'
                f'<p>{esc(ai_summary)}</p></div>'
                '<details class="intel-pack">'
                '<summary>平台选手 / 名单情报'
                f'<em>{roster_count} 人已识别</em>'
                '</summary>'
                f'<div class="intel-grid">{"".join(intel_panels)}</div>'
                f'<p class="intel-disclaimer">{esc(player_intel.get("note") or "选手信息仅来自本场平台结构化字段。")}'
                ' 平台盘口字段不等于官方首发，未覆盖项不硬填。</p>'
                '</details>'
                f'{render_lmt_panel(row)}'
                f'{render_oddin_panel(row)}'
                '<div class="event-foot">'
                f'<span>市场数据更新 {esc(updated)}</span>'
                f'<span><a href="{esc(detail_url)}">完整数据页 ↗</a> · '
                '<a href="intel_prematch.json">数据审计 ↗</a></span>'
                '</div>'
                '</article>'
            )
        blocks.append(
            f'<section class="day" data-date="{esc(date)}">'
            f'<div class="day-head"><h2>{esc(date[5:])}</h2>'
            f'<span>{esc(bj_weekday(group[0]["start_ts"]))} · {len(group)} 场</span></div>'
            f'<div class="event-grid">{"".join(cards)}</div></section>'
        )
    return "".join(blocks)


def render_page(snapshot: dict[str, Any]) -> str:
    stats = snapshot.get("stats") or {}
    player_stats = snapshot.get("player_intel_stats") or {}
    coverage = snapshot.get("coverage") or {}
    fixtures = snapshot.get("fixtures") or []
    chips = ['<button class="chip active" data-sport="all">全部</button>']
    for key, item in coverage.items():
        if not item.get("fixtures"):
            continue
        chips.append(
            f'<button class="chip" data-sport="{esc(key)}">{esc(item.get("short") or key)}'
            f'<b>{int(item.get("fixtures") or 0)}</b></button>'
        )
    coverage_rows = "".join(
        '<div class="coverage-item">'
        f'<strong>{esc(item.get("label") or key)}</strong>'
        f'<span>{int(item.get("fixtures") or 0)} 场</span>'
        f'<small>有效报价 {int(item.get("valid_odds") or 0)} · 暂停 {int(item.get("suspended") or 0)} · 缺口 {int(item.get("missing") or 0)}</small>'
        '</div>'
        for key, item in coverage.items()
    )
    errors = (snapshot.get("diagnostics") or {}).get("errors") or []
    error_html = (
        '<div class="diagnostic"><h2>本轮数据缺口</h2><ul>'
        + "".join(f"<li>{esc(item)}</li>" for item in errors)
        + '</ul></div>'
    ) if errors else ""
    source = snapshot.get("source") or {}
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="AI 聚合 CS2、Dota2、英雄联盟、足球与 NBA 的赛前队伍、名单和市场共识情报">
<title>AI 赛前情报 · 多项目赛前洞察</title>
<style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--blue:#0071e3;--green:#248a3d;--orange:#b45309;--red:#c9342f}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{background:var(--bg)}}
body{{color:var(--ink);background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6}}
.wrap{{max-width:1180px;margin:0 auto;padding:30px 18px 64px}}
.hero{{padding:20px 0 24px}}
.eyebrow{{font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--blue);margin-bottom:8px}}
h1{{font-size:34px;line-height:1.12;letter-spacing:-.03em;margin-bottom:9px}}
.lead{{max-width:780px;color:var(--sub);font-size:14px}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}}
.meta span{{font-size:11.5px;color:var(--sub);background:rgba(255,255,255,.75);border:1px solid var(--line);padding:4px 10px;border-radius:999px}}
.metrics{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:4px 0 20px}}
.metric{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px;box-shadow:0 6px 24px rgba(0,0,0,.035)}}
.metric b{{display:block;font-size:26px;letter-spacing:-.03em;line-height:1.2}}
.metric span{{font-size:12px;color:var(--sub)}}
.coverage{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px;margin-bottom:18px}}
.coverage-item{{padding:8px 10px;border-right:1px solid var(--line);min-width:0}}
.coverage-item:last-child{{border-right:0}}
.coverage-item strong,.coverage-item span,.coverage-item small{{display:block}}
.coverage-item strong{{font-size:13px}}
.coverage-item span{{font-size:12px;color:var(--blue);font-weight:700}}
.coverage-item small{{font-size:10.5px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.toolbar{{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:9px;padding:12px 0;background:rgba(245,245,247,.92);backdrop-filter:saturate(180%) blur(18px);border-bottom:1px solid rgba(0,0,0,.06)}}
.chips{{display:flex;gap:7px;overflow:auto;scrollbar-width:none;flex:1}}
.chip{{appearance:none;border:1px solid var(--line);background:var(--card);color:var(--sub);border-radius:999px;padding:7px 12px;font:inherit;font-size:12px;font-weight:650;cursor:pointer;white-space:nowrap}}
.chip b{{margin-left:5px;font-size:10px;opacity:.72}}
.chip.active{{background:var(--ink);border-color:var(--ink);color:#fff}}
.search{{width:210px;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:8px 13px;font:inherit;font-size:12px;outline:none}}
.search:focus{{border-color:var(--blue);box-shadow:0 0 0 3px rgba(0,113,227,.1)}}
.day{{margin-top:24px}}
.day-head{{display:flex;align-items:baseline;gap:9px;margin-bottom:10px}}
.day-head h2{{font-size:17px}}
.day-head span{{font-size:12px;color:var(--sub)}}
.event-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.event{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:15px;box-shadow:0 5px 18px rgba(0,0,0,.03)}}
.event-top,.event-foot{{display:flex;justify-content:space-between;gap:8px;align-items:center}}
.event-top time{{font-size:11.5px;color:var(--sub);white-space:nowrap}}
.sport-badge{{display:inline-block;font-size:10px;font-weight:800;color:var(--blue);background:#eaf3ff;border-radius:7px;padding:2px 6px;margin-right:5px}}
.s-cs2{{color:#9a4f00;background:#fff0dd}} .s-dota2{{color:#7a3fb5;background:#f2eafd}} .s-football{{color:#15753a;background:#e8f7ed}} .s-nba{{color:#9e2d24;background:#fdecea}}
.league{{font-size:11.5px;color:var(--sub);font-weight:650}}
.event-main{{margin:14px 0 12px;min-height:57px}}
.event-main h3{{font-size:18px;line-height:1.3;letter-spacing:-.015em}}
.event-main h3 span{{font-size:11px;color:var(--sub);font-weight:500;margin:0 7px}}
.event-meta{{font-size:11px;color:var(--sub);margin-top:5px}}
.status{{font-weight:700}}
.status.live,.status.starting{{color:var(--orange)}} .status.upcoming{{color:var(--green)}}
.consensus{{font-size:11.5px;font-weight:700;background:#f5f5f7;border-radius:9px;padding:7px 9px;margin:10px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.consensus.ok{{color:#1f5c2b;background:#edf8f0}} .consensus.gap{{color:var(--sub)}}
.market-head{{display:grid;grid-template-columns:1fr 64px 50px;gap:6px;font-size:9.5px;color:var(--sub);font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin:8px 1px 3px}}
.market-head span:nth-child(2),.market-head span:nth-child(3){{text-align:right}}
.outcome{{position:relative;display:grid;grid-template-columns:1fr 64px 50px;gap:6px;align-items:center;font-size:12px;padding:7px 1px 6px;border-bottom:1px solid #f0f0f2;overflow:hidden}}
.outcome:last-child{{border-bottom:0}}
.outcome .team{{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;z-index:1}}
.outcome .prob,.outcome .odds{{text-align:right;font-variant-numeric:tabular-nums;z-index:1}}
.outcome .prob{{font-weight:750}} .outcome .odds{{color:var(--sub)}}
.outcome i{{position:absolute;left:0;bottom:0;height:2px;width:var(--p);background:linear-gradient(90deg,var(--blue),#64b5ff);border-radius:2px}}
.market-gap{{padding:14px 10px;border-radius:10px;background:#f5f5f7;color:var(--sub);font-size:11.5px}}
.market-gap strong{{display:block;color:var(--ink);font-size:12px}}
.event-foot{{margin-top:10px;font-size:9.5px;color:#86868b}}
.event-foot a{{color:var(--blue);text-decoration:none;font-weight:650}}
.ai-brief{{margin:10px 0 8px;padding:9px 10px;border-radius:10px;background:#f5f8ff;border:1px solid #e3edfb}}
.ai-brief span{{display:block;font-size:9px;font-weight:800;letter-spacing:.08em;color:var(--blue);text-transform:uppercase}}
.ai-brief p{{font-size:10.5px;line-height:1.55;color:#3a3a3c;margin-top:3px}}
.intel-pack{{border-top:1px solid var(--line);padding-top:8px;margin-top:7px}}
.intel-pack summary{{cursor:pointer;font-size:10.5px;font-weight:750;color:var(--ink);list-style:none;display:flex;justify-content:space-between;gap:8px}}
.intel-pack summary::-webkit-details-marker{{display:none}}
.intel-pack summary em{{font-style:normal;color:var(--sub);font-weight:500}}
.intel-grid{{display:grid;gap:7px;margin-top:8px}}
.team-intel{{background:#f8f8fa;border-radius:10px;padding:9px 10px}}
.team-intel-head{{display:flex;justify-content:space-between;gap:8px;align-items:baseline}}
.team-intel-head strong{{font-size:11.5px}}
.team-intel-head small{{font-size:9px;color:var(--sub)}}
.team-intel p{{font-size:10.5px;color:#515154;margin-top:3px}}
.intel-tags{{display:flex;gap:4px;flex-wrap:wrap;margin-top:5px}}
.intel-tag{{font-size:8.5px;background:#fff;border:1px solid var(--line);border-radius:999px;padding:1px 6px;color:#515154}}
.roster-title{{font-size:9px;color:var(--sub);font-weight:700;margin-top:8px}}
.roster{{list-style:none;display:grid;grid-template-columns:1fr;gap:3px;margin-top:3px}}
.roster li{{display:grid;grid-template-columns:minmax(0,1fr) 34px minmax(92px,auto);gap:6px;font-size:9.5px;align-items:center}}
.roster li b{{font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.roster li span{{font-style:normal;color:var(--sub);text-align:right}}
.roster li em{{font-style:normal;color:var(--sub);text-align:left;white-space:nowrap}}
.intel-empty{{font-size:9.5px;color:var(--sub);margin-top:3px}}
.intel-disclaimer{{font-size:8.5px;color:var(--sub);margin-top:7px}}
.deep-pack{{margin-top:10px;border-top:1px solid var(--line);padding-top:9px}}
.deep-pack>summary{{cursor:pointer;list-style:none;font-size:11px;font-weight:800;color:var(--ink)}}
.deep-pack>summary::-webkit-details-marker{{display:none}}
.deep-pack>summary em{{display:block;font-style:normal;font-size:9px;color:var(--sub);font-weight:500;margin-top:2px}}
.oddin-pack>summary{{color:#1f4f8f}}
.oddin-team .form-badge{{width:16px;height:16px}}
.oddin-player{{border-top:1px solid var(--line);padding:5px 0}}
.oddin-player:first-of-type{{border-top:0}}
.oddin-player>summary{{cursor:pointer;list-style:none;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;align-items:baseline}}
.oddin-player>summary::-webkit-details-marker{{display:none}}
.oddin-player>summary b{{font-size:10px}}
.oddin-player>summary em{{font-style:normal;font-size:8.5px;color:var(--sub);text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.oddin-player-metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:5px}}
.oddin-player-metrics span{{background:#fff;border:1px solid var(--line);border-radius:7px;padding:4px 5px;font-size:8.5px;color:var(--sub)}}
.oddin-player-metrics b{{display:block;color:var(--ink);font-size:8px}}
.oddin-stat-tags,.oddin-favourites{{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}}
.oddin-stat-tags span,.oddin-favourites span{{font-size:8px;background:#f2f5f9;color:#515154;border-radius:999px;padding:2px 5px}}
.oddin-pool-list{{list-style:none;margin-top:5px}}
.oddin-pool-list li{{display:grid;grid-template-columns:minmax(0,1fr) 46px 58px;gap:5px;padding:3px 0;border-bottom:1px solid var(--line);font-size:8.5px}}
.oddin-pool-list li:last-child{{border-bottom:0}}
.oddin-pool-list b,.oddin-pool-list em{{font-style:normal;text-align:right;color:var(--sub)}}
.oddin-pool-list .pool-head{{color:var(--sub);font-weight:700;border-bottom-color:#d8d8dc}}
.oddin-pool-table th:nth-child(n+2),.oddin-pool-table td:nth-child(n+2){{text-align:right}}
.oddin-tournament{{margin-top:9px;border-top:1px solid var(--line);padding-top:8px;font-size:9px}}
.oddin-tournament>summary{{cursor:pointer;list-style:none;font-weight:750}}
.oddin-tournament>summary::-webkit-details-marker{{display:none}}
.oddin-tournament>summary em{{display:block;font-style:normal;color:var(--sub);font-weight:400;margin-top:2px}}
.oddin-tournament-meta{{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}}
.oddin-tournament-meta span{{font-size:8px;background:#f2f5f9;border-radius:999px;padding:2px 6px;color:var(--sub)}}
.oddin-tournament-matches{{list-style:none;margin-top:5px;max-height:240px;overflow:auto}}
.oddin-tournament-matches li{{display:grid;grid-template-columns:48px minmax(0,1fr) 70px;gap:5px;padding:3px 0;border-bottom:1px solid var(--line);font-size:8.5px;align-items:center}}
.oddin-tournament-matches li:last-child{{border-bottom:0}}
.oddin-tournament-matches span,.oddin-tournament-matches em{{font-style:normal;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.oddin-live-state{{display:inline-block;font-size:8px;color:#1f4f8f;background:#eaf3ff;border-radius:999px;padding:1px 6px;margin-left:4px}}
.h2h-summary{{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;margin-top:9px;padding:8px 10px;background:#f5f5f7;border-radius:10px;font-size:10px}}
.h2h-summary span{{color:var(--sub);text-align:center}}
.h2h-summary b:last-child{{text-align:right}}
.lmt-teams{{display:grid;gap:8px;margin-top:8px}}
.lmt-team{{border:1px solid var(--line);border-radius:12px;padding:10px;background:#fbfbfc}}
.lmt-team-head{{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}}
.lmt-team-head h4{{font-size:12px}}
.lmt-team-head p,.lmt-meta{{font-size:9.5px;color:var(--sub);margin-top:2px}}
.form-line{{display:flex;gap:3px;flex-shrink:0}}
.form-badge{{display:grid;place-items:center;width:17px;height:17px;border-radius:5px;font-size:8px;font-style:normal;font-weight:800}}
.form-w{{background:#e2f4e6;color:#237a35}} .form-d{{background:#f0f0f2;color:#666}} .form-l{{background:#fde8e7;color:#b42318}}
.stat-strip{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}}
.stat-strip span{{background:#fff;border-radius:7px;padding:5px 6px;font-size:9px;color:var(--sub)}}
.stat-strip b{{display:block;color:var(--ink);font-size:9px}}
.lmt-sub{{margin-top:7px;font-size:9.5px}}
.lmt-sub>summary{{cursor:pointer;color:#515154;font-weight:650}}
.lmt-sub>summary em{{font-style:normal;color:var(--sub);font-weight:400;margin-left:5px}}
.recent-list,.h2h-list,.squad-list,.scorer-row ul{{list-style:none;margin-top:5px}}
.recent-list li{{display:grid;grid-template-columns:48px 19px minmax(0,1fr) auto;gap:5px;padding:4px 0;border-bottom:1px solid var(--line);align-items:center}}
.recent-list li:last-child,.h2h-list li:last-child{{border-bottom:0}}
.recent-list span,.recent-list em,.h2h-list span,.h2h-list em{{font-style:normal;color:var(--sub)}}
.res{{display:inline-grid;place-items:center;width:17px;height:17px;border-radius:4px;font-size:8px}}
.res-w{{background:#e2f4e6;color:#237a35}} .res-d{{background:#f0f0f2;color:#666}} .res-l{{background:#fde8e7;color:#b42318}}
.lineup-list{{display:grid;grid-template-columns:1fr 1fr;gap:3px 8px;margin-top:5px}}
.lineup-list span{{display:grid;grid-template-columns:20px minmax(0,1fr) 25px;gap:4px;font-size:9px;align-items:center}}
.lineup-list i,.lineup-list em{{font-style:normal;color:var(--sub)}} .lineup-list em{{text-align:right}}
.lmt-injuries{{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}}
.lmt-injuries span{{font-size:8.5px;background:#fff4e6;color:#92400e;border-radius:999px;padding:2px 6px}}
.lmt-empty{{font-size:9px;color:var(--sub);margin-top:5px}}
.scorer-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}}
.scorer-row h5{{font-size:9px;color:var(--sub);text-transform:uppercase;letter-spacing:.04em}}
.scorer-row li{{display:flex;justify-content:space-between;gap:5px;padding:2px 0;font-size:9px}}
.squad-detail .squad-list{{max-height:190px;overflow:auto;background:#fff;border-radius:7px;padding:5px}}
.squad-list li{{display:grid;grid-template-columns:20px minmax(0,1fr) 55px 50px;gap:4px;padding:2px 0;font-size:8.5px;align-items:center}}
.squad-list li span,.squad-list li em,.squad-list li small{{font-style:normal;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.h2h-list li{{display:grid;grid-template-columns:50px minmax(0,1fr) 45px;gap:6px;padding:4px 0;border-bottom:1px solid var(--line)}}
.h2h-list li b{{font-size:9px}} .h2h-list li em{{text-align:right}}
.table-scroll{{overflow:auto;margin-top:6px}}
.lmt-table{{width:100%;border-collapse:collapse;font-size:8.5px}}
.lmt-table th,.lmt-table td{{padding:3px 4px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
.lmt-table th:nth-child(2),.lmt-table td:nth-child(2){{text-align:left;width:100%}}
.oddin-stat-strip{{grid-template-columns:repeat(3,1fr)}}
.oddin-players{{list-style:none;margin-top:5px;display:grid;gap:4px}}
.oddin-player{{padding:6px 7px;border:1px solid var(--line);border-radius:8px;background:#fff}}
.oddin-player>div{{display:flex;justify-content:space-between;gap:8px;align-items:baseline}}
.oddin-player b{{font-size:9.5px}}
.oddin-player small,.oddin-player span{{font-size:8.5px;color:var(--sub)}}
.oddin-player>span{{display:block;margin-top:2px;line-height:1.45}}
.pool-list,.leader-list,.match-list{{list-style:none;margin-top:5px}}
.pool-list li,.leader-list li,.match-list li{{display:grid;gap:5px;padding:4px 0;border-bottom:1px solid var(--line);font-size:8.8px;align-items:center}}
.pool-list li{{grid-template-columns:minmax(0,1fr) auto auto auto}}
.leader-list li{{grid-template-columns:minmax(0,1fr) 100px auto}}
.match-list li{{grid-template-columns:50px minmax(0,1fr) auto}}
.pool-list li span,.leader-list li span,.match-list li span{{color:var(--sub)}}
.pool-list li:last-child,.leader-list li:last-child,.match-list li:last-child{{border-bottom:0}}
.oddin-tournament>summary em{{display:inline;margin-left:5px}}
.note{{margin-top:24px;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px;color:var(--sub);font-size:12px}}
.note strong{{color:var(--ink)}}
.diagnostic{{margin-top:12px;background:#fff8ed;border:1px solid #f2d7ac;border-radius:14px;padding:14px 16px;font-size:11.5px;color:#724b13}}
.diagnostic h2{{font-size:13px;margin-bottom:5px}} .diagnostic ul{{padding-left:18px}}
.empty{{display:none;padding:40px 10px;text-align:center;color:var(--sub);font-size:13px}}
footer{{margin-top:22px;padding-top:14px;border-top:1px solid var(--line);font-size:10.5px;color:var(--sub)}}
@media(max-width:980px){{.event-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.coverage{{grid-template-columns:repeat(3,minmax(0,1fr))}}.metrics{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}
@media(max-width:640px){{.wrap{{padding:20px 13px 48px}}h1{{font-size:29px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.coverage{{grid-template-columns:repeat(2,1fr)}}.coverage-item{{border-right:0;border-bottom:1px solid var(--line)}}.event-grid{{grid-template-columns:1fr}}.toolbar{{flex-wrap:wrap;top:-1px}}.search{{width:100%;order:2}}}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<div class="eyebrow">AI PREMATCH INTELLIGENCE</div>
<h1>AI 赛前情报</h1>
<p class="lead">自动汇总赛程、队伍近况、选手统计、地图 / 英雄池、赛事数据与赛前市场共识，回答“谁在打、状态和阵容结构怎样、市场如何定价”。电竞覆盖英雄联盟、CS2、Dota 2；传统体育首批接入足球热门联赛与 NBA。</p>
<div class="meta"><span>数据生成 {esc(snapshot.get("generated_at_bj"))}</span><span>未来 {esc(snapshot.get("horizon_hours"))} 小时</span><span>AI 聚合 · 多源交叉</span><span>只读 · 不参与自动交易</span></div>
</section>
<section class="metrics">
<div class="metric"><b>{int(stats.get("fixtures") or 0)}</b><span>窗口内比赛</span></div>
<div class="metric"><b>{int(stats.get("valid_odds") or 0)}</b><span>有效主市场报价</span></div>
<div class="metric"><b>{int(stats.get("deep_intel") or 0)}</b><span>完整赛前数据包</span></div>
<div class="metric"><b>{int(player_stats.get("identified_players") or 0)}</b><span>平台识别选手人次</span></div>
<div class="metric"><b>{int(stats.get("suspended") or 0)}</b><span>暂停/缺口</span></div>
</section>
<section class="coverage">{coverage_rows}</section>
<div class="toolbar">
<div class="chips">{"".join(chips)}</div>
<input class="search" id="search" type="search" placeholder="搜索队伍或联赛">
</div>
<div id="days">{render_cards(fixtures)}</div>
<div class="empty" id="empty">没有符合筛选条件的比赛。</div>
<section class="note"><strong>阅读口径</strong>：百分比由公开赛前市场报价换算并去水，只表示市场共识；“强热门”不等于稳赢。完整数据包中的选手、地图 / 英雄池和近期统计来自赛前组件的历史样本；最近选手池不等同于本场官方首发。角色、替补、临时换人和伤停以比赛官方名单为准；未覆盖项直接留空。不同来源的价格语义不混画，也不直接触发交易。</section>
{error_html}
<footer>AI 聚合赛程、队伍 / 选手 / 名单画像与赛前市场共识 · 采集时间 {esc(snapshot.get("generated_at_utc"))} UTC · 完整机器快照与底层溯源见 <a href="intel_prematch.json">数据审计文件</a> · 本页不展示账户或下注数据</footer>
</main>
<script>
(() => {{
  const cards = [...document.querySelectorAll('.event')];
  const chips = [...document.querySelectorAll('.chip')];
  const search = document.getElementById('search');
  const empty = document.getElementById('empty');
  let sport = 'all';
  function apply() {{
    const q = (search.value || '').trim().toLowerCase();
    let shown = 0;
    cards.forEach(card => {{
      const okSport = sport === 'all' || card.dataset.sport === sport;
      const okQuery = !q || (card.dataset.search || '').toLowerCase().includes(q);
      const show = okSport && okQuery;
      card.style.display = show ? '' : 'none';
      if (show) shown++;
    }});
    document.querySelectorAll('.day').forEach(day => {{
      const any = [...day.querySelectorAll('.event')].some(card => card.style.display !== 'none');
      day.style.display = any ? '' : 'none';
    }});
    empty.style.display = shown ? 'none' : 'block';
  }}
  chips.forEach(button => button.addEventListener('click', () => {{
    sport = button.dataset.sport;
    chips.forEach(item => item.classList.toggle('active', item === button));
    apply();
  }}));
  search.addEventListener('input', apply);
}})();
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--watchlist", default=str(DEFAULT_WATCHLIST))
    parser.add_argument("--base-url", default="", help="override Stake API base URL")
    parser.add_argument("--hours", type=float, default=0.0, help="override horizon hours")
    parser.add_argument("--max-fixtures", type=int, default=0, help="override global cap")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--oddin-workers", type=int, default=4)
    parser.add_argument("--lmt-workers", type=int, default=4)
    parser.add_argument("--no-oddin", action="store_true",
                        help="skip Stake/Oddin esports deep data enrichment")
    parser.add_argument("--no-lmt", action="store_true",
                        help="skip Stake/Sportradar LMT deep data enrichment")
    parser.add_argument("--oddin-cache",
                        default=str(ROOT / "runtime" / "stake_oddin_cache.json"))
    parser.add_argument("--lmt-cache",
                        default=str(ROOT / "runtime" / "stake_lmt_cache.json"))
    parser.add_argument("--request-delay-ms", type=int, default=-1)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--json-out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--detail-dir", default=str(DEFAULT_DETAIL_DIR))
    parser.add_argument("--no-details", action="store_true")
    parser.add_argument("--no-html", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(Path(args.config))
    watchlist = load_json(Path(args.watchlist))
    if not isinstance(config, dict) or not config.get("sports"):
        raise SystemExit(f"invalid Stake prematch config: {args.config}")
    if not isinstance(watchlist, dict):
        raise SystemExit(f"invalid watchlist: {args.watchlist}")
    api_cfg = config.get("api") or {}
    base_url = args.base_url or str(api_cfg.get("base_url") or "https://odds-data.stake.com")
    hours = args.hours if args.hours > 0 else parse_float(config.get("horizon_hours"), 72.0)
    max_fixtures = (
        args.max_fixtures
        if args.max_fixtures > 0
        else int(config.get("max_fixtures") or 160)
    )
    request_delay_ms = (
        args.request_delay_ms
        if args.request_delay_ms >= 0
        else int(config.get("request_delay_ms") or 350)
    )
    snapshot = collect_snapshot(
        config=config,
        watchlist=watchlist,
        base_url=base_url,
        api_key=os.environ.get("STAKE_ODDS_API_KEY", "").strip(),
        now=time.time(),
        horizon_hours=hours,
        max_fixtures=max_fixtures,
        workers=args.workers,
        request_delay_ms=request_delay_ms,
    )
    if not args.no_lmt:
        try:
            snapshot["diagnostics"]["lmt"] = enrich_lmt_rows(
                snapshot["fixtures"],
                cache_path=Path(args.lmt_cache),
                workers=args.lmt_workers,
            )
        except Exception as exc:  # noqa: BLE001 - optional enrichment is isolated
            snapshot["diagnostics"]["lmt"] = {
                "ok": False,
                "enriched": 0,
                "error_count": 1,
                "errors": [str(exc)],
            }
    if not args.no_oddin:
        try:
            snapshot["diagnostics"]["oddin"] = enrich_oddin_rows(
                snapshot["fixtures"],
                cache_path=Path(args.oddin_cache),
                workers=args.oddin_workers,
            )
        except Exception as exc:  # noqa: BLE001 - optional enrichment is isolated
            snapshot["diagnostics"]["oddin"] = {
                "ok": False,
                "enriched": 0,
                "error_count": 1,
                "errors": [str(exc)],
            }
    snapshot["stats"]["deep_intel"] = sum(
        1 for row in snapshot["fixtures"] if row.get("lmt") or row.get("oddin")
    )
    snapshot["player_intel_stats"] = {
        "fixtures_with_players": sum(
            1
            for row in snapshot["fixtures"]
            if sum(
                len(items)
                for items in ((row.get("player_intel") or {}).get("team_players") or {}).values()
            )
        ),
        "identified_players": sum(
            sum(
                len(items)
                for items in ((row.get("player_intel") or {}).get("team_players") or {}).values()
            )
            for row in snapshot["fixtures"]
        ),
    }
    if not args.no_details:
        detail_dir = Path(args.detail_dir)
        kept_details: set[str] = set()
        for row in snapshot["fixtures"]:
            row["detail_url"] = prematch_detail.write_detail(
                row,
                detail_dir,
                snapshot,
            )
            kept_details.update(
                {
                    str(row.get("detail_url") or ""),
                    str(row.get("detail_json_url") or ""),
                    str(row.get("detail_csv_url") or ""),
                }
            )
        snapshot["diagnostics"]["detail_pages"] = {
            "dir": str(detail_dir),
            "generated": sum(bool(row.get("detail_url")) for row in snapshot["fixtures"]),
            "removed_stale": prematch_detail.cleanup_stale(detail_dir, kept_details),
        }
    json_path = Path(args.json_out)
    atomic_write(json_path, json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    out_path = Path(args.out)
    if not args.no_html:
        atomic_write(out_path, render_page(snapshot))
    print(
        "[prematch] "
        f"fixtures={snapshot['stats']['fixtures']} "
        f"valid_odds={snapshot['stats']['valid_odds']} "
        f"sports={snapshot['stats']['sports']} "
        f"errors={snapshot['diagnostics']['error_count']} "
        f"page={out_path if not args.no_html else 'skipped'} "
        f"json={json_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
