#!/usr/bin/env python3
"""Rebuild match timeline shells for 2026-08-28 finished matches in the pub dir."""
import json
import sys
from pathlib import Path

PROJECT = Path("/Users/ad/Documents/polymarket")
PUB_INTEL = Path("/private/tmp/danmu-intel-pub/intel")

sys.path.insert(0, str(PROJECT / "tools"))
import vps_intel_pipeline as pipe  # noqa: E402

pipe.ROOT = PROJECT
pipe.REPORTS = PUB_INTEL
pipe._TEAM_ROWS = None  # force reload from local team_names.json


def max_games_for(league: str) -> int:
    if league.startswith("CS2") or league.startswith("LEC"):
        return 3
    if "LCK" in league or "LPL" in league:
        return 5
    return 5


def main() -> int:
    data = json.loads((PROJECT / "docs" / "data" / "intel" / "matches.json").read_text(encoding="utf-8"))
    for m in data["matches"]:
        slug = m.get("slug", "")
        if "2026-08-28" not in slug:
            continue
        if m.get("status") != "已结束":
            continue
        event_slug = m.get("event_slug") or slug
        teams = m.get("teams") or []
        if len(teams) != 2:
            print(f"skip {slug}: teams={teams}")
            continue
        out = pipe.build_timeline_shell(
            event_slug, teams, m.get("league", "-"), "2026-08-28",
            max_games=max_games_for(m.get("league", "")),
        )
        print(f"shell: {out.name} ({m.get('league')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
