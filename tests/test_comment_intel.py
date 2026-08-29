"""Offline regression tests for the comment-intel slicing/keyword logic.

Keeps the pipeline's pre-match / in-play comment alerts deterministic:
window slicing, keyword flags, empty-series self-check and series-id mapping
must not regress without a test noticing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import comment_intel as ci

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def _comment(created_at: str, body: str, name: str = "anon") -> dict:
    return {
        "createdAt": created_at,
        "body": body,
        "profile": {"name": name},
    }


def test_window_slice_and_keyword_flags():
    """Comments inside the event window are counted and flagged; outside ignored."""
    event = {
        "slug": "lol-t1-dnf-2026-08-17",
        "title": "T1 vs DNS",
        "start_time": "2026-08-17T09:15:00+00:00",
        "end_time": "2026-08-17T15:15:00+00:00",
    }
    rows = [
        _comment("2026-08-17T07:00:00Z", "pre-window noise"),
        _comment("2026-08-17T10:30:00Z", "the official lineup has been announced, academy roster", "EurekaWTI"),
        _comment("2026-08-17T11:00:00Z", "more pauses to go! technical issue again", "LetItRide100"),
        _comment("2026-08-17T11:20:00Z", "match fixing", "EurekaWTI"),
        _comment("2026-08-17T16:00:00Z", "post-window noise"),
    ]
    info = ci.build_event_intel(event, {10311: (rows, 100)}, NOW, 90, 30)
    assert info is not None
    assert info["comment_count"] == 3
    assert info["keyword_hits"]["名单/阵容"] == 1
    assert info["keyword_hits"]["pause/延迟"] == 1
    assert info["keyword_hits"]["假赛/作弊"] == 1
    assert "名单/阵容" in info["alerts"]
    assert info["top_commenters"][0][0] == "EurekaWTI"
    assert len(info["samples"]) == 3


def test_phase_filtering():
    """Far-future and finished events are excluded from intel."""
    far_future = {
        "slug": "lol-x-y-2026-08-20",
        "title": "future",
        "start_time": "2026-08-20T09:00:00+00:00",
        "end_time": "2026-08-20T15:00:00+00:00",
    }
    finished = {
        "slug": "lol-a-b-2026-08-10",
        "title": "finished",
        "start_time": "2026-08-10T09:00:00+00:00",
        "end_time": "2026-08-10T15:00:00+00:00",
    }
    assert ci.build_event_intel(far_future, {10311: ([], 0)}, NOW, 90, 30) is None
    assert ci.build_event_intel(finished, {10311: ([], 0)}, NOW, 90, 30) is None


def test_empty_series_self_check():
    """An empty fetch with a non-zero series count must not read as 'no comments'."""
    event = {
        "slug": "lol-t1-dnf-2026-08-17",
        "title": "T1 vs DNS",
        "start_time": "2026-08-17T09:15:00+00:00",
        "end_time": "2026-08-17T15:15:00+00:00",
    }
    suspicious = ci.build_event_intel(event, {10311: ([], 9316)}, NOW, 90, 30)
    assert suspicious is not None
    assert "异常" in suspicious["note"] and "无评论" not in suspicious["note"]
    empty = ci.build_event_intel(event, {10311: ([], 0)}, NOW, 90, 30)
    assert empty is not None and empty["note"] == "series 无评论（可能游戏讨论量少）"


def test_series_id_prefix_mapping():
    assert ci.series_id_for_event("lol-t1-dnf-2026-08-17") == 10311
    assert ci.series_id_for_event("cs2-fut-mouz-2026-08-14") == 10310
    assert ci.series_id_for_event("dota2-ts8-aur1-2026-08-13") == 10309
