#!/usr/bin/env python3
"""Read-only Stake/Oddin esports widget client.

Stake embeds an Oddin match widget for CS2, Dota 2, and League of Legends.
The public match page exposes short-lived widget parameters (including a brand
token), and the widget reads its rich pre-match data from Oddin's GraphQL API.
This module only performs public GET/POST reads and never handles accounts,
wallet credentials, or betting actions.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ORIGIN = "https://stake.com"
WIDGET_ORIGIN = "https://disir.oddin.gg"
GRAPHQL_URL = "https://api-disir.oddin.gg/main/disir/query"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
)
PAGE_USER_AGENT = "curl/8.7.1"

GAME_ROOTS = {
    "csgo": {
        "team": "csgoTeamsHistoricalStatistics",
        "tournament": "csgoTournamentInfo",
        "stats": "csgoTournamentStatistics",
    },
    "dota2": {
        "team": "dota2TeamsHistoricalStatistics",
        "tournament": "dota2TournamentInfo",
        "stats": "dota2TournamentStatistics",
    },
    "lol": {
        "team": "lolTeamsHistoricalStatistics",
        "tournament": "lolTournamentInfo",
        "stats": "lolTournamentStatistics",
    },
}

WIDGET_RE = re.compile(
    r"https://disir\.oddin\.gg/(?P<game>csgo|dota2|lol)/match\?"
    r"(?P<query>[^\"'<>\\\s]+)"
)
_PAGE_CACHE_LOCK = threading.Lock()

MATCH_FIELDS = """
  id
  plannedStartTimestamp
  startTimestamp
  endTimestamp
  tournament { id name }
  homeTeam { id name iconPath }
  homeScore
  awayTeam { id name iconPath }
  awayScore
  winTeam { id name }
  isClosed
  bestOfType
  maps { id order startTimestamp endTimestamp isClosed }
"""

STATISTICS = "{ avg percentile total }"

CSGO_TEAM_FIELDS = f"""
  team {{ id name iconPath }}
  mapVote {{
    picked {{ map {{ name shortcut }} statistics {STATISTICS} }}
    banned {{ map {{ name shortcut }} statistics {STATISTICS} }}
  }}
  mapWinrate {{ map {{ name shortcut }} statistics {STATISTICS} }}
  roundWinrate {{
    map {{ name shortcut }}
    statistics {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  }}
  overallMapWinrate {{ avg percentile total sampleSize }}
  overallRoundWinrate {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  pistolWinrate {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  pistolWinConversion {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  pistolLossConversion {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  kills {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  deaths {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  killsOverDeaths {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  assists {{ all {STATISTICS} terrorists {STATISTICS} counterTerrorists {STATISTICS} }}
  flashAssists {{ all {STATISTICS} }}
  damage {{ all {STATISTICS} }}
  headshotRate {{ all {STATISTICS} }}
  openingKills {{ all {STATISTICS} }}
  openingConversion {{ all {STATISTICS} }}
  openingDeathConversion {{ all {STATISTICS} }}
  awpKills {{ all {STATISTICS} }}
  eliminationWinrate {{ all {STATISTICS} }}
  objectiveWinrate {{ all {STATISTICS} }}
  utilityDamage {{ all {STATISTICS} }}
  firstToWin3Rounds {{ all {STATISTICS} }}
  firstToWin6Rounds {{ all {STATISTICS} }}
  firstToWin9Rounds {{ all {STATISTICS} }}
  firstToWin12Rounds {{ all {STATISTICS} }}
  roundsLost {{ all {STATISTICS} }}
  favouriteWeapons {{
    weapon {{ name }}
    killsWithWeapon {STATISTICS}
    headshotsWithWeapon {STATISTICS}
  }}
  playerStatistics {{
    player {{ id nickname realName shortcut iconPath }}
    kills {STATISTICS}
    deaths {STATISTICS}
    assists {STATISTICS}
    killsOverDeaths {STATISTICS}
    damage {STATISTICS}
    headshotRate {STATISTICS}
    flashAssists {STATISTICS}
    openingKills {STATISTICS}
    awpKills {STATISTICS}
    utilityDamage {STATISTICS}
    enemiesFlashed {STATISTICS}
    multiKillRounds {STATISTICS}
    clutchRounds {STATISTICS}
    lurkKills {STATISTICS}
    grenadesUsed {STATISTICS}
    favouriteWeapons {{
      weapon {{ name }}
      killsWithWeapon {STATISTICS}
      headshotsWithWeapon {STATISTICS}
    }}
  }}
  form {{ {MATCH_FIELDS} }}
"""

DOTA2_TEAM_FIELDS = f"""
  team {{ id name iconPath }}
  mapWinrate {{ avg percentile total sampleSize }}
  kills {{ all {STATISTICS} }}
  killsOverDeaths {{ all {STATISTICS} }}
  gold {{ all {STATISTICS} }}
  xp {{ all {STATISTICS} }}
  heroDamage {{ all {STATISTICS} }}
  roshanKills {{ all {STATISTICS} }}
  towerKills {{ all {STATISTICS} }}
  barracksKills {{ all {STATISTICS} }}
  firstBlood {{ all {STATISTICS} }}
  firstTower {{ all {STATISTICS} }}
  firstRoshan {{ all {STATISTICS} }}
  firstBarracks {{ all {STATISTICS} }}
  first5Kills {{ all {STATISTICS} }}
  first10Kills {{ all {STATISTICS} }}
  first15Kills {{ all {STATISTICS} }}
  first20Kills {{ all {STATISTICS} }}
  duration {{ all {STATISTICS} }}
  favouriteHeroes {{
    hero {{ id name iconPath }}
    pickRate {STATISTICS}
    banRate {STATISTICS}
  }}
  players {{
    player {{ id nickname realName iconPath }}
    primaryRole
    killsDeathsAssists {STATISTICS}
    killParticipation {STATISTICS}
    gold {STATISTICS}
    xp {STATISTICS}
    creepScore {STATISTICS}
    denies {STATISTICS}
    heroDamage {STATISTICS}
    heroHealing {STATISTICS}
    buildingDamage {STATISTICS}
    wardsPlaced {STATISTICS}
    wardsDestroyed {STATISTICS}
    campsStacked {STATISTICS}
    stunDuration {STATISTICS}
    favouriteHeroes {{
      hero {{ id name iconPath }}
      pickRate {STATISTICS}
      winRate {STATISTICS}
    }}
  }}
  form {{ {MATCH_FIELDS} }}
"""

LOL_TEAM_FIELDS = f"""
  team {{ id name iconPath }}
  mapWinrate {{ avg percentile total sampleSize }}
  kills {{ all {STATISTICS} }}
  killsOverDeaths {{ all {STATISTICS} }}
  gold {{ all {STATISTICS} }}
  goldDiffAt15mins {{ all {STATISTICS} }}
  championDamage {{ all {STATISTICS} }}
  dragonKills {{ all {STATISTICS} }}
  baronKills {{ all {STATISTICS} }}
  heraldKills {{ all {STATISTICS} }}
  turretKills {{ all {STATISTICS} }}
  inhibitorKills {{ all {STATISTICS} }}
  firstBlood {{ all {STATISTICS} }}
  firstTurret {{ all {STATISTICS} }}
  firstDragon {{ all {STATISTICS} }}
  firstBaron {{ all {STATISTICS} }}
  firstInhibitor {{ all {STATISTICS} }}
  first5Kills {{ all {STATISTICS} }}
  first10Kills {{ all {STATISTICS} }}
  first15Kills {{ all {STATISTICS} }}
  duration {{ all {STATISTICS} }}
  favouriteChampions {{
    champion {{ id name iconPath }}
    pickRate {STATISTICS}
    banRate {STATISTICS}
  }}
  players {{
    player {{ id nickname realName iconPath }}
    primaryRole
    killsDeathsAssists {STATISTICS}
    killParticipation {STATISTICS}
    gold {STATISTICS}
    goldDiffAt15mins {STATISTICS}
    minionKills {STATISTICS}
    championDamage {STATISTICS}
    heals {STATISTICS}
    wardsPlaced {STATISTICS}
    wardsDestroyed {STATISTICS}
    visionScore {STATISTICS}
    crowdControlTime {STATISTICS}
    buildingDamage {STATISTICS}
    firstBlood {STATISTICS}
    favouriteChampions {{
      champion {{ id name iconPath }}
      pickRate {STATISTICS}
      winRate {STATISTICS}
    }}
  }}
  form {{ {MATCH_FIELDS} }}
"""

TEAM_FIELDS = {
    "csgo": CSGO_TEAM_FIELDS,
    "dota2": DOTA2_TEAM_FIELDS,
    "lol": LOL_TEAM_FIELDS,
}

TOURNAMENT_CORE_FIELDS = """
  id
  tournament { id name startTimestamp endTimestamp }
  organizer
  location
  prizePool
  isOffline
  isQualification
  teams {
    id
    team { id name iconPath }
    players { id nickname realName shortcut iconPath age }
  }
  matches {
    id
    plannedStartTimestamp
    startTimestamp
    endTimestamp
    homeTeam { id name }
    homeScore
    awayTeam { id name }
    awayScore
    winTeam { id name }
    isClosed
    bestOfType
    maps { id order isClosed }
  }
  standings {
    id
    name
    order
    standings {
      rank
      team { id name iconPath }
      points
      matchesWon
      matchesLost
      matchesDrawn
      mapsWon
      mapsLost
      mapDifference
      status
    }
  }
  brackets {
    id
    name
    order
    brackets {
      id
      label
      isRoot
      homeTeam { id name }
      homeScore
      awayTeam { id name }
      awayScore
      match { id }
    }
  }
"""

CSGO_STATS_FIELDS = """
  terroristsWinrateInPercent
  counterTerroristsWinrateInPercent
  bestTeams {
    highestKills { team { id name } value }
    highestKillsOverDeaths { team { id name } value }
    highestAwpKills { team { id name } value }
    highestPlantRate { team { id name } value }
    highestDefuseRate { team { id name } value }
  }
  bestPlayers {
    highestKills { player { id nickname } team { id name } value }
    highestKillsOverDeaths { player { id nickname } team { id name } value }
    highestDamage { player { id nickname } team { id name } value }
    highestFlashAssists { player { id nickname } team { id name } value }
    highestUtilityDamage { player { id nickname } team { id name } value }
    highestOpeningKills { player { id nickname } team { id name } value }
  }
  tournamentMapsStatistics {
    map { id name shortcut }
    picks
    bans
    terroristsWinrateInPercent
    counterTerroristsWinrateInPercent
  }
"""

DOTA2_STATS_FIELDS = """
  radiantWinrateInPercent
  direWinrateInPercent
  bestTeams {
    highestKills { team { id name } value }
    highestHeroDamage { team { id name } value }
    highestGold { team { id name } value }
    highestXp { team { id name } value }
    highestHeroHealing { team { id name } value }
  }
  bestPlayers {
    highestKillsDeathsAssists { player { id nickname } team { id name } hero { id name } value }
    highestHeroDamage { player { id nickname } team { id name } hero { id name } value }
    highestBuildingDamage { player { id nickname } team { id name } hero { id name } value }
    highestGold { player { id nickname } team { id name } hero { id name } value }
    highestXp { player { id nickname } team { id name } hero { id name } value }
  }
  tournamentHeroStatistics {
    hero { id name iconPath }
    bans
    picks
    wins
  }
"""

LOL_STATS_FIELDS = """
  blueWinrateInPercent
  redWinrateInPercent
  bestTeams {
    highestKills { team { id name } value }
    highestGold { team { id name } value }
    highestMinionKills { team { id name } value }
    highestChampionDamage { team { id name } value }
    highestHeals { team { id name } value }
  }
  bestPlayers {
    highestKillsDeathsAssists { player { id nickname } team { id name } champion { id name } value }
    highestGold { player { id nickname } team { id name } champion { id name } value }
    highestMinionKills { player { id nickname } team { id name } champion { id name } value }
    highestChampionDamage { player { id nickname } team { id name } champion { id name } value }
    highestBuildingDamage { player { id nickname } team { id name } champion { id name } value }
  }
  tournamentChampionStatistics {
    champion { id name iconPath }
    bans
    picks
    wins
  }
"""

TOURNAMENT_STATS_FIELDS = {
    "csgo": CSGO_STATS_FIELDS,
    "dota2": DOTA2_STATS_FIELDS,
    "lol": LOL_STATS_FIELDS,
}


class StakeOddinError(RuntimeError):
    """Raised when public Oddin widget data cannot be read."""


def _request(
    url: str,
    *,
    referer: str,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    user_agent: str = USER_AGENT,
    origin: str = ORIGIN,
    tries: int = 3,
    timeout: int = 30,
) -> bytes:
    request_headers = {
        "Accept": "application/json, text/html;q=0.9",
        "Origin": origin,
        "Referer": referer or f"{ORIGIN}/",
        "User-Agent": user_agent,
    }
    if headers:
        request_headers.update(headers)
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    last_error: Exception | None = None
    for attempt in range(max(1, tries)):
        try:
            request = urllib.request.Request(url, data=body, headers=request_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.read()
        except Exception as exc:  # noqa: BLE001 - bounded public read retries
            last_error = exc
            if getattr(exc, "code", None) in (401, 403, 404, 422, 451):
                break
            if attempt + 1 < tries:
                time.sleep(min(3.0, 0.5 * (2**attempt)))
    raise StakeOddinError(f"public widget request failed: {url}: {last_error}") from last_error


def load_cache(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(path: Path | None, data: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def extract_widget_params(page_html: str) -> dict[str, Any]:
    """Extract the first concrete Oddin match-widget configuration from HTML."""
    text = html.unescape(page_html)
    for match in WIDGET_RE.finditer(text):
        game = match.group("game")
        query_text = match.group("query").rstrip("\\")
        if "{" in query_text or "}" in query_text:
            continue
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit("?" + query_text).query,
            keep_blank_values=False,
        )
        params = {key: values[0] for key, values in query.items() if values}
        required = (
            "brandToken",
            "id",
            "homeTeamId",
            "awayTeamId",
            "tournamentId",
        )
        if all(params.get(key) for key in required):
            params["game"] = game
            return params
    raise StakeOddinError("Stake page has no concrete Oddin match widget parameters")


def _stat(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    out = {
        "avg": value.get("avg"),
        "percentile": value.get("percentile"),
        "total": value.get("total"),
    }
    if value.get("sampleSize") is not None:
        out["sample_size"] = value.get("sampleSize")
    return out


def _metric_map(data: Any, *, groups: bool = False) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key in {"team", "player", "players", "form"}:
            continue
        if isinstance(value, dict) and "avg" in value:
            out[key] = _stat(value)
        elif groups and isinstance(value, dict):
            grouped = {
                name: _stat(item)
                for name, item in value.items()
                if isinstance(item, dict) and "avg" in item
            }
            if grouped:
                out[key] = grouped
        elif key == "mapWinrate":
            out[key] = _stat(value)
    return {key: value for key, value in out.items() if value}


def _entity_favorites(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entity = item.get("weapon") or item.get("hero") or item.get("champion") or {}
        if not isinstance(entity, dict):
            continue
        metrics = {}
        for key, value in item.items():
            if key in {"weapon", "hero", "champion"}:
                continue
            stat = _stat(value)
            if stat:
                metrics[key] = stat
        out.append(
            {
                "id": entity.get("id"),
                "name": entity.get("name") or "",
                "icon": entity.get("iconPath") or "",
                "metrics": metrics,
            }
        )
    return out


def _csgo_map_pool(data: Any) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in data.get("mapWinrate") or []:
        if not isinstance(item, dict):
            continue
        map_data = item.get("map") or {}
        name = str(map_data.get("name") or "")
        if name:
            rows.setdefault(name, {"name": name})["win_rate"] = _stat(item.get("statistics"))
    vote = data.get("mapVote") or {}
    for key, field in (("picked", "pick_rate"), ("banned", "ban_rate")):
        for item in vote.get(key) or []:
            if not isinstance(item, dict):
                continue
            map_data = item.get("map") or {}
            name = str(map_data.get("name") or "")
            if name:
                rows.setdefault(name, {"name": name})[field] = _stat(item.get("statistics"))
    for item in data.get("roundWinrate") or []:
        if not isinstance(item, dict):
            continue
        map_data = item.get("map") or {}
        name = str(map_data.get("name") or "")
        if not name:
            continue
        stats = item.get("statistics") or {}
        rows.setdefault(name, {"name": name})["rounds"] = {
            key: _stat(value)
            for key, value in stats.items()
            if isinstance(value, dict) and "avg" in value
        }
    return list(rows.values())


def _player(player: Any) -> dict[str, Any]:
    if not isinstance(player, dict):
        return {}
    return {
        "id": player.get("id"),
        "nickname": player.get("nickname") or "",
        "real_name": player.get("realName") or "",
        "shortcut": player.get("shortcut") or "",
        "icon": player.get("iconPath") or "",
        "age": player.get("age"),
    }


def _match(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    home = value.get("homeTeam") or {}
    away = value.get("awayTeam") or {}
    winner = value.get("winTeam") or {}
    home_score = value.get("homeScore")
    away_score = value.get("awayScore")
    return {
        "id": value.get("id"),
        "planned_start": value.get("plannedStartTimestamp") or "",
        "start": value.get("startTimestamp") or "",
        "end": value.get("endTimestamp") or "",
        "tournament": ((value.get("tournament") or {}).get("name") or ""),
        "home": {"id": home.get("id"), "name": home.get("name") or ""},
        "away": {"id": away.get("id"), "name": away.get("name") or ""},
        "home_score": home_score,
        "away_score": away_score,
        "winner": {"id": winner.get("id"), "name": winner.get("name") or ""},
        "closed": bool(value.get("isClosed")),
        "best_of": value.get("bestOfType") or "",
        "maps": value.get("maps") or [],
        "score": (
            f"{home_score}:{away_score}"
            if home_score is not None and away_score is not None
            else ""
        ),
    }


def _team_package(data: Any, game: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    team = data.get("team") or {}
    if game == "csgo":
        player_rows = data.get("playerStatistics") or []
        favorite_field = "favouriteWeapons"
    else:
        player_rows = data.get("players") or []
        favorite_field = (
            "favouriteHeroes" if game == "dota2" else "favouriteChampions"
        )
    players = []
    for row in player_rows:
        if not isinstance(row, dict):
            continue
        player = _player(row.get("player"))
        if not player:
            continue
        player["role"] = row.get("primaryRole") or ""
        player["metrics"] = _metric_map(row)
        player["favorites"] = _entity_favorites(
            row.get(favorite_field.replace("favourite", "favourite"))
        )
        players.append(player)
    favorites = _entity_favorites(data.get(favorite_field))
    favorites.sort(
        key=lambda item: (
            -float(
                ((item.get("metrics") or {}).get("pickRate") or {}).get("avg")
                or ((item.get("metrics") or {}).get("killsWithWeapon") or {}).get("avg")
                or 0
            ),
            item.get("name") or "",
        )
    )
    return {
        "id": team.get("id"),
        "name": team.get("name") or "",
        "icon": team.get("iconPath") or "",
        "map_winrate": _stat(
            data.get("overallMapWinrate") if game == "csgo" else data.get("mapWinrate")
        ),
        "metrics": _metric_map(data, groups=True),
        "map_pool": _csgo_map_pool(data) if game == "csgo" else [],
        "favorites": favorites,
        "players": players,
        "recent_matches": [
            item for item in (_match(row) for row in data.get("form") or []) if item
        ][:10],
    }


def _team_result(match: dict[str, Any], team_id: Any) -> str:
    winner_id = (match.get("winner") or {}).get("id")
    home_id = (match.get("home") or {}).get("id")
    away_id = (match.get("away") or {}).get("id")
    if not winner_id or team_id not in {home_id, away_id}:
        return ""
    return "W" if winner_id == team_id else "L"


def _normalize_team_data(game: str, payload: Any) -> list[dict[str, Any]]:
    root = GAME_ROOTS[game]["team"]
    data = ((payload or {}).get("data") or {}).get(root) if isinstance(payload, dict) else {}
    rows = (data or {}).get("teamStatistics") or []
    return [_team_package(row, game) for row in rows if isinstance(row, dict)]


def _normalize_tournament_core(game: str, payload: Any) -> dict[str, Any]:
    root = GAME_ROOTS[game]["tournament"]
    data = ((payload or {}).get("data") or {}).get(root) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {}
    return {
        "metadata": {
            "tournament": data.get("tournament") or {},
            "organizer": data.get("organizer") or "",
            "location": data.get("location") or "",
            "prize_pool": data.get("prizePool") or "",
            "offline": data.get("isOffline"),
            "qualification": data.get("isQualification"),
        },
        "teams": [
            {
                "team": item.get("team") or {},
                "players": [_player(player) for player in item.get("players") or []],
            }
            for item in data.get("teams") or []
            if isinstance(item, dict)
        ],
        "matches": [
            item for item in (_match(row) for row in data.get("matches") or []) if item
        ],
        "standings": data.get("standings") or [],
        "brackets": data.get("brackets") or [],
    }


def _flatten_best(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows = []
    for metric, item in data.items():
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "metric": metric,
                "team": item.get("team") or {},
                "player": item.get("player") or {},
                "entity": item.get("hero") or item.get("champion") or {},
                "value": item.get("value"),
            }
        )
    return rows


def _normalize_tournament_stats(game: str, payload: Any) -> dict[str, Any]:
    root = GAME_ROOTS[game]["stats"]
    data = ((payload or {}).get("data") or {}).get(root) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {}
    if game == "csgo":
        side_winrates = {
            "terrorists": data.get("terroristsWinrateInPercent"),
            "counter_terrorists": data.get("counterTerroristsWinrateInPercent"),
        }
        pools = data.get("tournamentMapsStatistics") or []
    elif game == "dota2":
        side_winrates = {
            "radiant": data.get("radiantWinrateInPercent"),
            "dire": data.get("direWinrateInPercent"),
        }
        pools = data.get("tournamentHeroStatistics") or []
    else:
        side_winrates = {
            "blue": data.get("blueWinrateInPercent"),
            "red": data.get("redWinrateInPercent"),
        }
        pools = data.get("tournamentChampionStatistics") or []
    return {
        "side_winrates": {key: value for key, value in side_winrates.items() if value is not None},
        "best_teams": _flatten_best(data.get("bestTeams")),
        "best_players": _flatten_best(data.get("bestPlayers")),
        "pools": pools,
    }


def build_deep_match(
    client: "OddinClient",
    params: dict[str, Any],
    *,
    referer: str,
) -> dict[str, Any]:
    """Fetch and normalize one complete Oddin match package."""
    game = str(params.get("game") or "")
    if game not in GAME_ROOTS:
        raise StakeOddinError(f"unsupported Oddin game: {game}")
    home_id = str(params.get("homeTeamId") or "")
    away_id = str(params.get("awayTeamId") or "")
    tournament_id = str(params.get("tournamentId") or "")
    match_id = str(params.get("id") or "")
    if not all((home_id, away_id, tournament_id, match_id)):
        raise StakeOddinError("Oddin widget parameters are incomplete")

    roots = GAME_ROOTS[game]
    team_query = f"""
      query StakeOddinTeams($homeTeamId: ID!, $awayTeamId: ID!) {{
        {roots["team"]}(
          timeframe: THREE_MONTHS
          homeTeamId: $homeTeamId
          awayTeamId: $awayTeamId
        ) {{
          teamStatistics {{ {TEAM_FIELDS[game]} }}
          pastFiveEncounters {{ {MATCH_FIELDS} }}
        }}
      }}
    """
    tournament_query = f"""
      query StakeOddinTournament($tournamentId: ID!) {{
        {roots["tournament"]}(tournamentId: $tournamentId) {{
          {TOURNAMENT_CORE_FIELDS}
        }}
      }}
    """
    stats_query = f"""
      query StakeOddinTournamentStats($tournamentId: ID!) {{
        {roots["stats"]}(tournamentId: $tournamentId) {{
          {TOURNAMENT_STATS_FIELDS[game]}
        }}
      }}
    """
    team_payload = client.query(
        f"teams:{game}:{home_id}:{away_id}",
        team_query,
        {"homeTeamId": home_id, "awayTeamId": away_id},
        referer=referer,
    )
    tournament_payload = client.query(
        f"tournament:{game}:{tournament_id}",
        tournament_query,
        {"tournamentId": tournament_id},
        referer=referer,
    )
    stats_payload = client.query(
        f"tournament-stats:{game}:{tournament_id}",
        stats_query,
        {"tournamentId": tournament_id},
        referer=referer,
    )

    teams = _normalize_team_data(game, team_payload)
    if len(teams) < 2:
        raise StakeOddinError("Oddin returned incomplete team statistics")
    by_id = {str(team.get("id") or ""): team for team in teams}
    home = by_id.get(home_id, teams[0])
    away = by_id.get(away_id, teams[1])
    h2h_data = (
        ((team_payload or {}).get("data") or {}).get(roots["team"]) or {}
    ).get("pastFiveEncounters") or []
    h2h = [item for item in (_match(row) for row in h2h_data) if item][:5]
    for item in h2h:
        item["home_result"] = _team_result(item, home.get("id"))
        item["away_result"] = _team_result(item, away.get("id"))
    for team in (home, away):
        for item in team.get("recent_matches") or []:
            item["team_result"] = _team_result(item, team.get("id"))
    tournament = _normalize_tournament_core(game, tournament_payload)
    tournament["stats"] = _normalize_tournament_stats(game, stats_payload)

    tournament_rosters = {
        str((item.get("team") or {}).get("id") or ""): item.get("players") or []
        for item in tournament.get("teams") or []
        if isinstance(item, dict)
    }
    for team in (home, away):
        roster = tournament_rosters.get(str(team.get("id") or "")) or []
        if not roster:
            continue
        stats_players = team.get("players") or []
        by_id = {
            str(player.get("id") or ""): player
            for player in stats_players
            if player.get("id")
        }
        by_name = {
            str(player.get("nickname") or "").casefold(): player
            for player in stats_players
            if player.get("nickname")
        }
        merged = []
        used: set[str] = set()
        for player in roster:
            player_id = str(player.get("id") or "")
            name_key = str(player.get("nickname") or "").casefold()
            enriched = by_id.get(player_id) or by_name.get(name_key) or {}
            row = {**player, **enriched}
            row["metrics"] = enriched.get("metrics") or {}
            row["favorites"] = enriched.get("favorites") or []
            row["has_recent_stats"] = bool(row["metrics"])
            merged.append(row)
            if player_id:
                used.add(player_id)
            if name_key:
                used.add(name_key)
        for player in stats_players:
            if (
                str(player.get("id") or "") in used
                or str(player.get("nickname") or "").casefold() in used
            ):
                continue
            merged.append({**player, "has_recent_stats": True})
        team["players"] = merged[:10]

    home_wins = sum(1 for item in h2h if item.get("home_result") == "W")
    away_wins = sum(1 for item in h2h if item.get("away_result") == "W")
    coverage = {
        "teams": 2,
        "players": len(home.get("players") or []) + len(away.get("players") or []),
        "players_with_stats": sum(
            1
            for team in (home, away)
            for player in team.get("players") or []
            if player.get("has_recent_stats")
        ),
        "favorites": len(home.get("favorites") or []) + len(away.get("favorites") or []),
        "map_pool": len(home.get("map_pool") or []) + len(away.get("map_pool") or []),
        "recent_matches": len(home.get("recent_matches") or [])
        + len(away.get("recent_matches") or []),
        "h2h": len(h2h),
        "tournament_teams": len(tournament.get("teams") or []),
        "tournament_matches": len(tournament.get("matches") or []),
        "standings": sum(
            len(block.get("standings") or [])
            for block in tournament.get("standings") or []
            if isinstance(block, dict)
        ),
        "pool_rows": len((tournament.get("stats") or {}).get("pools") or []),
    }
    return {
        "game": game,
        "match_id": match_id,
        "tournament_id": tournament_id,
        "coverage": coverage,
        "home": home,
        "away": away,
        "head_to_head": {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "matches": h2h,
        },
        "tournament": tournament,
        "source": "stake_oddin_widget",
    }


class OddinClient:
    """Cached read-only client for Stake's public Oddin match widget."""

    def __init__(
        self,
        *,
        brand_token: str,
        locale: str = "zh",
        cache_path: Path | None = None,
        referer: str = "",
    ):
        self.brand_token = brand_token
        self.locale = locale
        self.cache_path = cache_path
        self.referer = referer
        self.cache = load_cache(cache_path)
        self._lock = threading.Lock()

    def query(
        self,
        key: str,
        query: str,
        variables: dict[str, Any],
        *,
        referer: str,
        ttl: int = 900,
        force: bool = False,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(
            (query + json.dumps(variables, sort_keys=True)).encode("utf-8")
        ).hexdigest()
        cache_key = f"{key}:{digest}"
        now = time.time()
        with self._lock:
            cached = (self.cache.get("queries") or {}).get(cache_key) or {}
        if (
            not force
            and isinstance(cached.get("data"), dict)
            and now - float(cached.get("fetched_ts") or 0) < ttl
        ):
            return cached["data"]
        raw = _request(
            GRAPHQL_URL,
            referer=referer,
            data={"query": query, "variables": variables},
            origin=WIDGET_ORIGIN,
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": self.brand_token,
                "X-Locale": self.locale,
            },
        )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StakeOddinError("Oddin returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise StakeOddinError("Oddin returned a non-object response")
        errors = payload.get("errors") or []
        if errors and not payload.get("data"):
            raise StakeOddinError(
                "Oddin GraphQL error: "
                + "; ".join(str(item.get("message") or item) for item in errors[:3])
            )
        with self._lock:
            self.cache.setdefault("queries", {})[cache_key] = {
                "fetched_ts": now,
                "data": payload,
            }
            save_cache(self.cache_path, self.cache)
        return payload


def fetch_widget_params(
    *,
    page_url: str,
    cache_path: Path | None = None,
    ttl: int = 1800,
    force: bool = False,
) -> dict[str, Any]:
    """Read a Stake match page and return its concrete Oddin widget parameters."""
    now = time.time()
    with _PAGE_CACHE_LOCK:
        cache = load_cache(cache_path)
        cached = (cache.get("pages") or {}).get(page_url) or {}
        if (
            not force
            and isinstance(cached.get("data"), dict)
            and now - float(cached.get("fetched_ts") or 0) < ttl
        ):
            return cached["data"]
    raw = _request(
        page_url,
        referer=page_url,
        user_agent=PAGE_USER_AGENT,
    )
    try:
        page_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StakeOddinError("Stake match page is not UTF-8") from exc
    params = extract_widget_params(page_text)
    if cache_path:
        # Re-read before merging: another worker may have written a different
        # page while this request was in flight.
        with _PAGE_CACHE_LOCK:
            current = load_cache(cache_path)
            current.setdefault("pages", {})[page_url] = {
                "fetched_ts": now,
                "data": params,
            }
            save_cache(cache_path, current)
    return params
