"""Homepage match rows must stay actionable and point at the right intel page."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_home_today as home  # noqa: E402


def test_home_match_row_uses_linked_prematch_detail() -> None:
    row = {"_prematch_href": "intel_prematch_detail_cs2_fixture-1.html"}
    assert home.detail_href(row) == "intel/intel_prematch_detail_cs2_fixture-1.html"


def test_home_match_row_falls_back_to_today_page() -> None:
    assert home.detail_href({"title": "A vs B"}) == "intel/today.html"


def test_home_match_row_does_not_double_prefix_intel() -> None:
    assert home.detail_href({"_prematch_href": "intel/today.html"}) == "intel/today.html"
