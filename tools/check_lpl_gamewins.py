#!/usr/bin/env python3
"""Print official gameWins for LPL matches on a date (read-only)."""
import json
import sys
import urllib.request
from urllib.parse import urlencode

API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
API_BASE = "https://esports-api.lolesports.com/persisted/gw"


def api_get(path: str, params: dict) -> dict:
    url = f"{API_BASE}/{path}?{urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "x-api-key": API_KEY,
        "accept": "application/json",
        "user-agent": "polymarket-intel/check_lpl_gamewins",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-08-28"
    data = api_get("getSchedule", {"hl": "zh-CN", "leagueId": "98767991314006698"})
    for ev in data.get("data", {}).get("schedule", {}).get("events", []):
        m = ev.get("match") or {}
        if not ev.get("startTime", "").startswith(f"{date}T"):
            continue
        codes = []
        wins = []
        for t in m.get("teams", []):
            codes.append(t.get("code", "?"))
            res = t.get("result") or {}
            wins.append(res.get("gameWins", 0))
        print(f"{ev.get('state')} | {'/'.join(codes)} | gameWins={'/'.join(map(str, wins))} | matchId={m.get('id')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
