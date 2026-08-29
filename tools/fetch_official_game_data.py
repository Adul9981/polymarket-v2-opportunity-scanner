#!/usr/bin/env python3
"""Fetch official LoL esports lineup / result data from Riot APIs.

Sources:
  - schedule/details: https://esports-api.lolesports.com/persisted/gw
  - live window:      https://feed.lolesports.com/livestats/v1/window/<gameId>

Usage:
  python3 tools/fetch_official_game_data.py --league lck --date 2026-08-27 --teams NS,BFX
  python3 tools/fetch_official_game_data.py --match-id 117030752644841577
  python3 tools/fetch_official_game_data.py --game-id 117030752644841578

Notes:
  - The API key below is the public one used by lolesports.com frontend
    (verified 2026-08-27 via npm lck-analytics@0.4.0). Refresh from the
    website's JS bundle if it stops working.
  - "选手×英雄" here is official game data, NOT danmaku mentions.
  - window endpoint returns data once the game is live; empty during draft.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
API_BASE = "https://esports-api.lolesports.com/persisted/gw"
FEED_BASE = "https://feed.lolesports.com/livestats/v1"

LEAGUE_IDS = {
    "lck": "98767991310872058",
    "lck_cl": "98767991335774713",
    "lpl": "98767991314006698",
    "lec": "98767991302996019",
    "lcs": "98767991299243165",
    "lcp": "113476371197627891",
}

# English champion id -> Chinese name (common + new champs seen in 2026).
CHAMP_ZH = {
    "Ahri": "阿狸", "Ambessa": "安蓓萨（狼母）", "Bard": "巴德",
    "Caitlyn": "女警", "Camille": "青钢影", "Ezreal": "EZ",
    "Galio": "加里奥", "JarvanIV": "皇子", "Jayce": "杰斯",
    "Jhin": "烬", "Karma": "扇子妈", "LeeSin": "盲僧",
    "Locke": "洛克", "Lulu": "璐璐", "Nocturne": "梦魇（NOC）",
    "Orianna": "发条", "Rumble": "兰博", "Shen": "慎",
    "Vi": "蔚", "Yunara": "芸阿娜",
}


def http_get(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get(path: str, params: dict) -> dict:
    from urllib.parse import urlencode
    url = f"{API_BASE}/{path}?{urlencode(params)}"
    return http_get(url, {
        "x-api-key": API_KEY,
        "accept": "application/json",
        "user-agent": "polymarket-intel/fetch_official_game_data",
    })


def find_matches(league: str, date: str | None = None, teams: list[str] | None = None) -> list[dict]:
    data = api_get("getSchedule", {"hl": "zh-CN", "leagueId": LEAGUE_IDS[league]})
    out = []
    for ev in data.get("data", {}).get("schedule", {}).get("events", []):
        m = ev.get("match") or {}
        codes = [t.get("code", "") for t in m.get("teams", [])]
        if date and not ev.get("startTime", "").startswith(f"{date}T"):
            continue
        if teams and not set(teams) <= set(codes):
            continue
        out.append(ev)
    return out


def get_games(match_id: str) -> list[dict]:
    data = api_get("getEventDetails", {"hl": "zh-CN", "id": match_id})
    event = data.get("data", {}).get("event") or {}
    return (event.get("match") or {}).get("games", []) or []


def get_window(game_id: str) -> dict:
    req = urllib.request.Request(
        f"{FEED_BASE}/window/{game_id}",
        headers={"accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    # 2026-08-27：BP/选人阶段该接口返回 204 无内容（实测 G3 BP 阶段），
    # 属正常"开局后才有阵容"，不是错误——明确提示等待开局
    if not raw.strip():
        return {"game_id": game_id, "draft_phase": True,
                "error": "BP/选人阶段 window 无数据（HTTP 204），开局后 1 分钟再拉"}
    return json.loads(raw)


def zh(champ_id: str) -> str:
    return CHAMP_ZH.get(champ_id, champ_id)


def dump_lineup(game_id: str) -> dict | None:
    try:
        data = get_window(game_id)
    except Exception as e:
        return {"game_id": game_id, "error": str(e)}
    md = data.get("gameMetadata")
    if not md:
        return {"game_id": game_id, "error": "no game data (draft phase or unavailable)"}
    rows = []
    for side in ("blueTeamMetadata", "redTeamMetadata"):
        side_md = md.get(side, {})
        team = side_md.get("esportsTeamId", "?")
        for p in side_md.get("participantMetadata", []):
            rows.append({
                "side": "蓝" if side.startswith("blue") else "红",
                "team_id": team,
                "player": p.get("summonerName"),
                "champion_en": p.get("championId"),
                "champion_zh": zh(p.get("championId") or ""),
            })
    return {"game_id": game_id, "lineup": rows}


def print_lineup(rec: dict) -> None:
    if rec.get("error"):
        print(f"  ! {rec['game_id']}: {rec['error']}")
        return
    print(f"  gameId {rec['game_id']}:")
    for r in rec["lineup"]:
        print(f"    [{r['side']}] {r['player']:<22} -> {r['champion_zh']} ({r['champion_en']})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch official LoL lineup data from Riot APIs")
    ap.add_argument("--league", default="lck", choices=sorted(LEAGUE_IDS))
    ap.add_argument("--date", help="match start date, e.g. 2026-08-27")
    ap.add_argument("--teams", help="comma-separated team codes, e.g. NS,BFX")
    ap.add_argument("--match-id", help="official match id (from getSchedule)")
    ap.add_argument("--game-id", help="single game id (window endpoint)")
    args = ap.parse_args()

    if args.game_id:
        print_lineup(dump_lineup(args.game_id))
        return 0

    if args.match_id:
        match_id = args.match_id
    else:
        matches = find_matches(args.league, args.date,
                               [t.strip() for t in (args.teams or "").split(",") if t.strip()])
        if not matches:
            print("no matching match found; adjust --league/--date/--teams")
            return 1
        for ev in matches:
            m = ev.get("match") or {}
            codes = "/".join(t.get("code", "?") for t in m.get("teams", []))
            print(f"match: {ev.get('startTime')} {codes} ({ev.get('state')}) id={m.get('id')}")
        match_id = matches[-1]["match"]["id"]

    games = get_games(match_id)
    for g in games:
        print(f"game {g.get('number')}: {g.get('state')} id={g.get('id')}")
        if g.get("state") == "completed":
            print_lineup(dump_lineup(g["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
