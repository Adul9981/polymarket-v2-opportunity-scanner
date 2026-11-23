#!/usr/bin/env python3
"""Read-only Stake/Sportradar LMT Plus fixture feed client.

Stake embeds the Sportradar LMT Plus widget on supported match pages. The
widget license endpoint returns an encrypted JSON document. Decrypting it with
the public widget client id yields a short-lived Fishnet token used by the
fixture feed URLs. This module only performs public GET requests, never logs in,
and never touches betting or account endpoints.

Football standings use ``season_livetable``. NBA standings use
``season_dynamictable``; the latter contains overall, conference, and
division tables with basketball-specific record and streak columns.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from Crypto.Cipher import AES as _PycryptoAES
except ImportError:  # pragma: no cover - pycryptodome is in production requirements
    _PycryptoAES = None

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:  # pragma: no cover - production uses pycryptodome
    Cipher = algorithms = modes = None

CLIENT_ID = "7d2f8da584734cf9ab52112c1022d183"
WIDGET_BASE = "https://ws-cdn001.akamaized.net"
FEED_BASE = "https://lt-fn-cdn001.akamaized.net"
ORIGIN = "https://stake.com"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

FEED_TTL = {
    "match_info": 300,
    "stats_match_form": 600,
    "stats_match_head2head": 900,
    "stats_team_lastx": 900,
    "stats_team_versusrecent": 1800,
    "match_squads": 300,
    "stats_team_squad": 21600,
    "stats_season_injuries": 600,
    "season_livetable": 300,
    "season_dynamictable": 300,
    "stats_season_uniqueteamstats": 600,
    "stats_season_topgoals": 600,
}


class StakeLMTError(RuntimeError):
    """Raised when the public LMT data source cannot be read."""


def _request_json(url: str, *, referer: str, tries: int = 3, timeout: int = 25) -> Any:
    headers = {
        "Accept": "application/json",
        "Origin": ORIGIN,
        "Referer": referer or f"{ORIGIN}/",
        "User-Agent": USER_AGENT,
    }
    request = urllib.request.Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(max(1, tries)):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - bounded public GET retries
            last_error = exc
            if getattr(exc, "code", None) in (401, 403, 404, 451):
                break
            if attempt + 1 < tries:
                time.sleep(min(3.0, 0.5 * (2 ** attempt)))
    raise StakeLMTError(f"LMT request failed: {url}: {last_error}") from last_error


def _evp_bytes_to_key(password: bytes, salt: bytes, key_len: int = 32,
                      iv_len: int = 16) -> tuple[bytes, bytes]:
    """OpenSSL EVP_BytesToKey (MD5, one iteration) used by CryptoJS."""
    material = b""
    block = b""
    while len(material) < key_len + iv_len:
        block = hashlib.md5(block + password + salt).digest()
        material += block
    return material[:key_len], material[key_len:key_len + iv_len]


def decrypt_licensing(payload: dict[str, Any], client_id: str = CLIENT_ID) -> dict[str, Any]:
    encrypted = str(payload.get("text") or "")
    if not encrypted:
        raise StakeLMTError("licensing payload has no encrypted text")
    raw = base64.b64decode(encrypted)
    if not raw.startswith(b"Salted__") or len(raw) < 32:
        raise StakeLMTError("licensing payload has unexpected encryption format")
    salt = raw[8:16]
    ciphertext = raw[16:]
    key, iv = _evp_bytes_to_key(client_id.encode("utf-8"), salt)
    if _PycryptoAES is not None:
        padded = _PycryptoAES.new(key, _PycryptoAES.MODE_CBC, iv).decrypt(ciphertext)
    elif Cipher is not None:
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
    else:
        raise StakeLMTError("no AES backend available (install pycryptodome)")
    padding = padded[-1]
    if padding < 1 or padding > 16 or padded[-padding:] != bytes([padding]) * padding:
        raise StakeLMTError("licensing payload has invalid PKCS7 padding")
    try:
        decoded = json.loads(padded[:-padding].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StakeLMTError("licensing payload is not valid JSON") from exc
    if not isinstance(decoded, dict) or not decoded.get("fishnetToken"):
        raise StakeLMTError("licensing payload has no fishnetToken")
    return decoded


def get_license_token(*, referer: str = "", client_id: str = CLIENT_ID) -> dict[str, Any]:
    url = f"{WIDGET_BASE}/{client_id}/licensing"
    payload = _request_json(url, referer=referer)
    if not isinstance(payload, dict):
        raise StakeLMTError("licensing response is not an object")
    decoded = decrypt_licensing(payload, client_id)
    token = decoded.get("fishnetToken") or {}
    if not token.get("token") or int(token.get("expirationTs") or 0) <= int(time.time() * 1000):
        raise StakeLMTError("licensing token is missing or expired")
    return {
        "token": str(token["token"]),
        "origin": str(token.get("origin") or ORIGIN),
        "expiration_ts": int(token.get("expirationTs") or 0),
        "packages": decoded.get("packages") or [],
    }


def feed_url(path: str, token: str, *, client_alias: str = "common",
             language: str = "zh", timezone: str = "Etc:UTC") -> str:
    clean_path = path.lstrip("/")
    encoded_timezone = urllib.parse.quote(timezone, safe=":")
    return (
        f"{FEED_BASE}/{client_alias}/{urllib.parse.quote(language)}/"
        f"{encoded_timezone}/gismo/{clean_path}?T={token}"
    )


def feed_name(path: str) -> str:
    return path.split("/", 1)[0]


def load_cache(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


class LMTClient:
    """Cached, read-only client for Stake's public LMT feeds."""

    def __init__(self, *, cache_path: Path | None = None, referer: str = "",
                 language: str = "zh", timezone: str = "Etc:UTC"):
        self.cache_path = cache_path
        self.referer = referer
        self.language = language
        self.timezone = timezone
        self.cache = load_cache(cache_path) if cache_path else {}
        self._lock = threading.Lock()
        self.license = get_license_token(referer=referer)

    def get(self, path: str, *, client_alias: str = "common", ttl: int | None = None,
            force: bool = False) -> Any:
        key = f"{client_alias}:{path}"
        now = time.time()
        with self._lock:
            cached = self.cache.get("feeds", {}).get(key) or {}
        name = feed_name(path)
        max_age = FEED_TTL.get(name, 300) if ttl is None else ttl
        if not force and cached.get("data") is not None and now - float(cached.get("fetched_ts") or 0) < max_age:
            return cached["data"]
        url = feed_url(
            path,
            self.license["token"],
            client_alias=client_alias,
            language=self.language,
            timezone=self.timezone,
        )
        data = _request_json(url, referer=self.referer)
        if self.cache_path:
            with self._lock:
                self.cache.setdefault("feeds", {})[key] = {
                    "fetched_ts": now,
                    "data": data,
                }
                save_cache(self.cache_path, self.cache)
        return data


def first_doc_data(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return None
    docs = payload.get("doc") or []
    if not docs or not isinstance(docs[0], dict):
        return None
    doc = docs[0]
    if doc.get("event") == "exception":
        return None
    return doc.get("data")


def sr_match_id(ext_id: Any) -> str:
    match = re.search(r"(?:sr:match:|^)(\d+)$", str(ext_id or "").strip())
    return match.group(1) if match else ""


def _time_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    ts = int(value.get("uts") or 0)
    return {
        "uts": ts,
        "utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds") if ts else "",
        "date": str(value.get("date") or ""),
        "time": str(value.get("time") or ""),
    }


def _team_ref(team: Any) -> dict[str, Any]:
    if not isinstance(team, dict):
        return {}
    country = team.get("countrycode") or {}
    return {
        "id": team.get("_id"),
        "uid": team.get("uid"),
        "name": team.get("name") or team.get("mediumname") or "",
        "abbr": team.get("abbr") or "",
        "country": country.get("name") or "",
        "country_code": country.get("a2") or "",
    }


def _match_score(match: dict[str, Any]) -> dict[str, Any]:
    result = match.get("result") or {}
    periods = match.get("periods") or {}
    final = periods.get("ft") or {}
    return {
        "home": result.get("home", final.get("home")),
        "away": result.get("away", final.get("away")),
        "winner": result.get("winner"),
        "period": result.get("period") or "",
        "display": (
            f"{result.get('home')}:{result.get('away')}"
            if result.get("home") is not None and result.get("away") is not None
            else ""
        ),
    }


def _team_result(match: dict[str, Any], team_uid: int) -> str:
    result = _match_score(match)
    if result["winner"] not in {"home", "away"}:
        return ""
    home_uid = int(((match.get("teams") or {}).get("home") or {}).get("uid") or 0)
    if team_uid == home_uid:
        return "W" if result["winner"] == "home" else "L"
    return "W" if result["winner"] == "away" else "L"


def _compact_match(match: dict[str, Any], team_uid: int) -> dict[str, Any]:
    teams = match.get("teams") or {}
    home = _team_ref(teams.get("home"))
    away = _team_ref(teams.get("away"))
    team_home = int(home.get("uid") or 0) == team_uid
    opponent = away if team_home else home
    score = _match_score(match)
    team_score = score["home"] if team_home else score["away"]
    opponent_score = score["away"] if team_home else score["home"]
    return {
        "id": match.get("_id"),
        "date": _time_record(match.get("time")),
        "competition_id": match.get("_utid") or match.get("_tid"),
        "round": (match.get("roundname") or {}).get("name") or match.get("round"),
        "home_away": "home" if team_home else "away",
        "opponent": opponent,
        "team_score": team_score,
        "opponent_score": opponent_score,
        "result": _team_result(match, team_uid) or "D",
        "score": (
            f"{team_score}:{opponent_score}"
            if team_score is not None and opponent_score is not None
            else ""
        ),
        "comment": match.get("comment") or "",
    }


def _match_form(data: Any, side: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    team = ((data.get("teams") or {}).get(side) or {})
    return {
        "form": [str(item.get("type") or "") for item in team.get("form") or []],
        "streak": team.get("streak") or {},
    }


def _last_matches(data: Any, team_uid: int, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows = []
    for match in data.get("matches") or []:
        if not isinstance(match, dict):
            continue
        result = _match_score(match)
        if result["winner"] not in {"home", "away"}:
            continue
        rows.append(_compact_match(match, team_uid))
        if len(rows) >= limit:
            break
    return rows


def _h2h_matches(data: Any, home_uid: int, away_uid: int,
                 current_uts: int, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    rows = []
    for match in data.get("matches") or []:
        if not isinstance(match, dict):
            continue
        uts = int((match.get("time") or {}).get("uts") or 0)
        if current_uts and uts >= current_uts:
            continue
        teams = match.get("teams") or {}
        uids = {
            int((teams.get("home") or {}).get("uid") or 0),
            int((teams.get("away") or {}).get("uid") or 0),
        }
        if uids != {int(home_uid), int(away_uid)}:
            continue
        rows.append({
            "id": match.get("_id"),
            "date": _time_record(match.get("time")),
            "home": _team_ref(teams.get("home")),
            "away": _team_ref(teams.get("away")),
            "score": _match_score(match),
            "competition_id": match.get("_utid") or match.get("_tid"),
        })
        if len(rows) >= limit:
            break
    return rows


def _league_tables(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        tables = data.get("tables") or []
    elif isinstance(data, list):
        tables = data
    else:
        tables = []
    out = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        rows = []
        for item in table.get("tablerows") or []:
            team = _team_ref(item.get("team"))
            rows.append({
                "position": item.get("pos"),
                "team": team,
                "played": item.get("total"),
                "wins": item.get("winTotal"),
                "draws": item.get("drawTotal"),
                "losses": item.get("lossTotal"),
                "goals_for": item.get("goalsForTotal"),
                "goals_against": item.get("goalsAgainstTotal"),
                "goal_diff": item.get("goalDiffTotal"),
                "points": item.get("pointsTotal"),
                "win_pct": item.get("pctTotal"),
                "games_back": item.get("gb"),
                "streak": item.get("streak"),
                "last_ten_wins": item.get("lastTenGamesWin"),
                "last_ten_losses": item.get("lastTenGamesLoss"),
                "home_wins": item.get("winHome"),
                "home_losses": item.get("lossHome"),
                "away_wins": item.get("winAway"),
                "away_losses": item.get("lossAway"),
                "conference_wins": item.get("confWinTotal"),
                "conference_losses": item.get("confLossTotal"),
                "division_wins": item.get("divWinTotal"),
                "division_losses": item.get("divLossTotal"),
                "sort_position": item.get("sortPositionTotal"),
                "promotion": (item.get("promotion") or {}).get("name") or "",
            })
        out.append({
            "id": table.get("_id"),
            "name": table.get("name") or "",
            "round": table.get("currentround"),
            "max_rounds": table.get("maxrounds"),
            "rows": rows,
        })
    return out


def _select_table_row(tables: list[dict[str, Any]], team_uid: int) -> dict[str, Any] | None:
    for table in tables:
        for row in table.get("rows") or []:
            if int((row.get("team") or {}).get("uid") or 0) == int(team_uid):
                return row
    return None


def _team_season_stats(data: Any, team_uid: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    raw = (((data.get("stats") or {}).get("uniqueteams") or {}).get(str(team_uid)) or {})
    if not isinstance(raw, dict):
        return {}
    return {
        key: value
        for key, value in raw.items()
        if key != "uniqueteam"
    }


def _squad_players(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    out = []
    for player in data.get("players") or []:
        if not isinstance(player, dict):
            continue
        position = player.get("position") or {}
        nationality = player.get("nationality") or {}
        membersince = _time_record(player.get("membersince"))
        out.append({
            "id": player.get("_id"),
            "name": player.get("name") or "",
            "fullname": player.get("fullname") or "",
            "position": position.get("name") or "",
            "position_abbr": position.get("abbr") or "",
            "shirt_number": player.get("shirtnumber") or "",
            "nationality": nationality.get("name") or "",
            "age": (
                int((datetime.now(timezone.utc) - datetime.fromtimestamp(
                    int((player.get("birthdate") or {}).get("uts") or 0), timezone.utc
                )).days / 365.25)
                if int((player.get("birthdate") or {}).get("uts") or 0) > 0
                else None
            ),
            "height_cm": player.get("height"),
            "weight_kg": player.get("weight"),
            "preferred_foot": player.get("foot") or "",
            "market_value": player.get("marketvalue"),
            "member_since": membersince.get("utc") or "",
        })
    return sorted(out, key=lambda item: (
        item.get("position_abbr") or "Z",
        item.get("shirt_number") or "999",
        item.get("name") or "",
    ))


def _manager(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    manager = data.get("manager") or {}
    if manager:
        country = manager.get("nationality") or {}
        return {
            "id": manager.get("_id"),
            "name": manager.get("name") or "",
            "fullname": manager.get("fullname") or "",
            "nationality": country.get("name") or "",
            "birthdate": _time_record(manager.get("birthdate")),
        }
    managers = data.get("managers") or []
    if managers and isinstance(managers[0], dict):
        country = managers[0].get("nationality") or {}
        return {
            "id": managers[0].get("_id"),
            "name": managers[0].get("name") or "",
            "nationality": country.get("name") or "",
        }
    return {}


def _lineup(data: Any, side: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    team = data.get(side) or {}
    lineup = team.get("startinglineup") or {}
    players = lineup.get("players") or []
    return {
        "formation": lineup.get("formation") or "",
        "players": [
            {
                "id": player.get("playerid") or player.get("_id"),
                "name": player.get("playername") or player.get("name") or "",
                "position": player.get("name") or "",
                "position_abbr": player.get("pos") or player.get("matchpos") or "",
                "shirt_number": player.get("shirtnumber") or "",
            }
            for player in players
            if isinstance(player, dict)
        ],
    }


def _injuries(data: Any, team_uid: int) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        team = item.get("uniqueteam") or {}
        if int(team.get("_id") or 0) != int(team_uid):
            continue
        status = item.get("status") or {}
        player = item.get("player") or {}
        out.append({
            "player_id": item.get("_playerid"),
            "player": player.get("name") or "",
            "position": (player.get("position") or {}).get("name") or "",
            "status": status.get("name") or status.get("status") or "",
            "comment": status.get("comment") or "",
            "missing": bool(status.get("missing")),
            "doubtful": bool(status.get("doubtful")),
            "start": _time_record(status.get("start")),
            "end": _time_record(status.get("end")),
        })
    return out


def _top_scorers(data: Any, team_uid: int, limit: int = 10) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    out = []
    for item in data.get("players") or []:
        if not isinstance(item, dict):
            continue
        team_stats = (item.get("teams") or {}).get(str(team_uid))
        if not team_stats:
            continue
        player = item.get("player") or {}
        out.append({
            "player_id": item.get("playerid"),
            "name": player.get("name") or "",
            "position": (player.get("position") or {}).get("name") or "",
            "goals": team_stats.get("goals"),
            "matches": team_stats.get("matches"),
            "minutes": team_stats.get("minutes_played"),
            "first_goals": team_stats.get("first_goals"),
            "last_goals": team_stats.get("last_goals"),
        })
    return sorted(out, key=lambda item: (-int(item.get("goals") or 0), item.get("name") or ""))[:limit]


def _latest_lineup(
    client: "LMTClient",
    current_squads: Any,
    current_side: str,
    last_matches: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    current = _lineup(current_squads, current_side)
    if current.get("players"):
        return current, "confirmed"
    # The LMT widget displays the most recent official starting XI when the
    # current lineup has not yet been published.
    for match in last_matches[:3]:
        match_id = match.get("id")
        if not match_id:
            continue
        try:
            payload = client.get(f"match_squads/{match_id}")
            previous = first_doc_data(payload)
            source_side = str(match.get("home_away") or current_side)
            lineup = _lineup(previous, source_side)
            if lineup.get("players"):
                lineup["source_match_id"] = match_id
                lineup["source_date"] = match.get("date") or {}
                return lineup, "latest_available"
        except Exception:  # noqa: BLE001 - fallback remains explicit
            continue
    return {}, "missing"


def build_deep_match(
    client: "LMTClient",
    match_id: str,
    *,
    referer: str,
) -> dict[str, Any] | None:
    """Fetch and normalize one complete LMT match package."""
    match_info = first_doc_data(client.get(f"match_info/{match_id}"))
    match = (match_info or {}).get("match") or {}
    home = _team_ref((match.get("teams") or {}).get("home"))
    away = _team_ref((match.get("teams") or {}).get("away"))
    home_uid = int(home.get("uid") or 0)
    away_uid = int(away.get("uid") or 0)
    season_id = str(match.get("_seasonid") or "")
    if not home_uid or not away_uid or not season_id:
        return None

    form_data = first_doc_data(client.get(f"stats_match_form/{match_id}"))
    squads_data = first_doc_data(client.get(f"match_squads/{match_id}"))
    home_last_data = first_doc_data(client.get(f"stats_team_lastx/{home_uid}"))
    away_last_data = first_doc_data(client.get(f"stats_team_lastx/{away_uid}"))
    h2h_data = first_doc_data(client.get(f"stats_team_versusrecent/{home_uid}/{away_uid}"))
    home_squad_data = first_doc_data(client.get(f"stats_team_squad/{home_uid}"))
    away_squad_data = first_doc_data(client.get(f"stats_team_squad/{away_uid}"))
    table_data = first_doc_data(client.get(f"season_livetable/{season_id}"))
    if not (_league_tables(table_data)):
        # Basketball LMT uses season_dynamictable; season_livetable returns an
        # empty tables array for NBA seasons.
        dynamic_payload = first_doc_data(client.get(f"season_dynamictable/{season_id}"))
        dynamic_table = (
            dynamic_payload.get("season")
            if isinstance(dynamic_payload, dict) and dynamic_payload.get("season")
            else dynamic_payload
        )
        if _league_tables(dynamic_table):
            table_data = dynamic_table
    season_stats_data = first_doc_data(client.get(f"stats_season_uniqueteamstats/{season_id}"))
    injuries_data = first_doc_data(client.get(f"stats_season_injuries/{season_id}"))
    top_goals_data = first_doc_data(client.get(f"stats_season_topgoals/{season_id}"))

    tables = _league_tables(table_data)
    home_last = _last_matches(home_last_data, home_uid)
    away_last = _last_matches(away_last_data, away_uid)
    current_uts = int(((match.get("_dt") or {}).get("uts")) or 0)
    h2h = _h2h_matches(h2h_data, home_uid, away_uid, current_uts)
    home_lineup, home_lineup_status = _latest_lineup(client, squads_data, "home", home_last)
    away_lineup, away_lineup_status = _latest_lineup(client, squads_data, "away", away_last)

    home_package = {
        **home,
        "form": _match_form(form_data, "home"),
        "last_matches": home_last[:10],
        "league_position": _select_table_row(tables, home_uid),
        "season_stats": _team_season_stats(season_stats_data, home_uid),
        "squad": _squad_players(home_squad_data),
        "injuries": _injuries(injuries_data, home_uid),
        "top_scorers": _top_scorers(top_goals_data, home_uid, 5),
        "manager": _manager(squads_data.get("home") if isinstance(squads_data, dict) else None)
        or _manager(home_squad_data),
        "usual_lineup": home_lineup,
        "lineup_status": home_lineup_status,
    }
    away_package = {
        **away,
        "form": _match_form(form_data, "away"),
        "last_matches": away_last[:10],
        "league_position": _select_table_row(tables, away_uid),
        "season_stats": _team_season_stats(season_stats_data, away_uid),
        "squad": _squad_players(away_squad_data),
        "injuries": _injuries(injuries_data, away_uid),
        "top_scorers": _top_scorers(top_goals_data, away_uid, 5),
        "manager": _manager(squads_data.get("away") if isinstance(squads_data, dict) else None)
        or _manager(away_squad_data),
        "usual_lineup": away_lineup,
        "lineup_status": away_lineup_status,
    }
    home_wins = sum(1 for item in h2h if item["score"]["winner"] == "home")
    away_wins = sum(1 for item in h2h if item["score"]["winner"] == "away")
    draws = sum(1 for item in h2h if item["score"]["winner"] not in {"home", "away"})
    return {
        "match_id": match_id,
        "coverage": match.get("coverage") or {},
        "season_id": season_id,
        "round": match.get("round"),
        "round_name": (match.get("roundname") or {}).get("name"),
        "home": home_package,
        "away": away_package,
        "head_to_head": {
            "home_wins": home_wins,
            "draws": draws,
            "away_wins": away_wins,
            "matches": h2h[:10],
        },
        "league": {
            "tables": tables,
            "top_scorers": [
                item for item in (top_goals_data or {}).get("players", [])
                if isinstance(item, dict)
            ][:20],
        },
        "source": "stake_sportradar_lmt_plus",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--referer", default=f"{ORIGIN}/sports")
    parser.add_argument("--cache", default="")
    parser.add_argument("--path", default="")
    args = parser.parse_args()
    client = LMTClient(
        cache_path=Path(args.cache) if args.cache else None,
        referer=args.referer,
    )
    path = args.path or f"match_info/{args.match_id}"
    print(json.dumps(client.get(path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
