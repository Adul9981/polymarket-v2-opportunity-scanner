"""Regression tests for task-2 scan reliability (locked 2026-08-16).

These tests guard the failure modes that once made the scanner report
"no whitelisted matches" while LCK/LPL/LEC/EWC/TI matches were live:

1. event_start_time() must read the real match time from market-level
   gameStartTime, not fall back to event.startDate (listing time).
2. Esports events must be fetched via the Esports tag (config
   esports.tag_id), not by paging the global feed by listing time.
3. The watchlist must include every league the project tracks
   (LCK/LPL/LCP/LEC/KeSPA Cup / IEM/BLAST/EWC / TI/ESL One), otherwise
   fetched matches get silently filtered out.
4. The pipeline empty-result sanity check must turn silent failures into
   loud warnings instead of a valid "no signal" conclusion.

Project-wide rule: any new capability (auto-trading or otherwise) must
keep this suite green; scan reliability is highest priority.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

import market_scanner as ms
import task2_pipeline as tp

ROOT = Path(__file__).resolve().parents[1]


def load_config(name: str) -> dict:
    with (ROOT / "config" / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def test_event_start_time_prefers_market_game_start_time():
    """Listing time (startDate) must never be treated as match time."""
    event = {
        "title": "LoL: Gen.G vs KT Rolster (BO3) - LCK Round 3-4 Legend Group",
        "startDate": "2026-08-14T20:40:25Z",  # listing time
        "markets": [
            {"gameStartTime": "2026-08-19 08:00:00+00"},
            {"gameStartTime": "2026-08-19 09:00:00+00"},
        ],
    }
    start = ms.event_start_time(event)
    assert start is not None
    assert start.replace(tzinfo=None) == datetime(2026, 8, 19, 8, 0)


def test_event_start_time_falls_back_to_listing_time_without_markets():
    event = {"title": "season prop", "startDate": "2026-08-11T21:44:54Z"}
    start = ms.event_start_time(event)
    assert start is not None
    assert start.replace(tzinfo=None) == datetime(2026, 8, 11, 21, 44, 54)


def test_watchlist_esports_tag_fetch_is_enabled():
    """Esports tag fetch must stay enabled in the watchlist config."""
    cfg = load_config("market_watchlist.json")
    esports = cfg.get("esports") or {}
    assert esports.get("enabled") is True
    assert str(esports.get("tag_id")) == "64"


@pytest.mark.parametrize(
    "title",
    [
        "LoL: Gen.G vs KT Rolster (BO3) - LCK Round 3-4 Legend Group",
        "LoL: Team WE vs LGD Gaming (BO3) - LPL Group Ascend",
        "LoL: Team Secret Whales vs CTBC Flying Oyster (BO5) - LCP Group Stage",
        "LoL: G2 Esports vs Fnatic (BO3) - LEC Regular Season",
        "LoL: T1 vs DN SOOPers (BO5) - KeSPA Cup Playoffs",
        "Counter-Strike: Astralis vs NIP (BO3) - Esports World Cup Group B",
        "Dota 2: Team Spirit vs Team Resilience (BO3) - The International Elimination Round",
    ],
)
def test_watchlist_matches_tracked_leagues(title: str):
    """Every tracked league must survive watchlist filtering."""
    cfg = load_config("market_watchlist.json")
    ok, _group = ms.watchlist_match({"title": title, "slug": "x"}, cfg)
    assert ok, f"watchlist missed tracked league title: {title}"


def test_watchlist_rejects_unlisted_leagues():
    cfg = load_config("market_watchlist.json")
    ok, _group = ms.watchlist_match(
        {"title": "Counter-Strike: Keyd vs Imperial (BO3) - BetBoom Storm Playoffs", "slug": "x"},
        cfg,
    )
    assert not ok


def test_scan_sanity_warns_when_esports_tag_fetch_empty():
    diag = {
        "fetched_events": 1600,
        "esports_tag_enabled": True,
        "esports_tag_fetched": 0,
        "watchlist_matches": 1,
        "final_events": 0,
        "candidate_count": 0,
    }
    assert tp.scan_sanity(diag)


def test_scan_sanity_warns_when_watchlist_zero_but_esports_fetched():
    diag = {
        "fetched_events": 2300,
        "esports_tag_enabled": True,
        "esports_tag_fetched": 730,
        "watchlist_matches": 0,
        "final_events": 0,
        "candidate_count": 0,
    }
    assert tp.scan_sanity(diag)


def test_scan_sanity_passes_healthy_run():
    diag = {
        "fetched_events": 2300,
        "esports_tag_enabled": True,
        "esports_tag_fetched": 730,
        "watchlist_matches": 75,
        "final_events": 24,
        "candidate_count": 15,
    }
    assert tp.scan_sanity(diag) == []
