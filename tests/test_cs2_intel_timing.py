"""CS2 node timing must not inherit the LoL BP-start gap."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import vps_intel_pipeline as pipeline  # noqa: E402


def test_cs2_bp_node_uses_map_start_not_lol_gap():
    match = {"league": "CS2"}
    assert pipeline.bp_gap_minutes(match) == 0
    assert pipeline.bp_node_wait_minutes(match) == 2


def test_lol_keeps_existing_bp_gap():
    match = {"league": "LoL"}
    assert pipeline.bp_gap_minutes(match) == 8
    assert pipeline.bp_node_wait_minutes(match) == 4


def test_cs2_bp_trigger_is_within_five_minutes_of_market_start():
    match = {"league": "CS2"}
    total_wait = pipeline.bp_gap_minutes(match) + pipeline.bp_node_wait_minutes(match)
    assert total_wait <= 5
