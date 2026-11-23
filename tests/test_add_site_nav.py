"""Regression checks for site navigation injection."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import add_site_nav  # noqa: E402


def test_inject_all_skips_macos_apple_double_files(tmp_path):
    page = tmp_path / "index.html"
    page.write_text("<html><body><h1>ok</h1></body></html>", encoding="utf-8")
    apple_double = tmp_path / "._index.html"
    apple_double.write_bytes(b"\x00\x05\x16\x07not-utf8")

    changed = add_site_nav.inject_all(tmp_path)

    assert changed == 1
    assert "<nav" in page.read_text(encoding="utf-8")
    assert apple_double.read_bytes() == b"\x00\x05\x16\x07not-utf8"


def test_inject_all_skips_any_non_utf8_html_without_aborting_other_pages(tmp_path):
    good = tmp_path / "good.html"
    good.write_text("<html><body>good</body></html>", encoding="utf-8")
    bad = tmp_path / "bad.html"
    bad.write_bytes(b"<html><body>\xb0 broken</body></html>")

    changed = add_site_nav.inject_all(tmp_path)

    assert changed == 1
    assert "<nav" in good.read_text(encoding="utf-8")
    assert bad.read_bytes().startswith(b"<html><body>\xb0")


def test_pattern_pages_get_current_page_nav_state():
    assert add_site_nav.kind_of("pattern_decision_workspace.html") == "pattern"
    assert add_site_nav.kind_of("pattern_atlas.html") == "pattern-atlas"
    assert add_site_nav.kind_of("intel_prematch.html") == "prematch"
    assert add_site_nav.kind_of("intel_help.html") == "help"
    assert add_site_nav.active_of("pattern") == "pattern"
    assert add_site_nav.active_of("pattern-atlas") == "pattern-atlas"
    assert add_site_nav.active_of("prematch") == "prematch"
    assert add_site_nav.active_of("help") == "help"

    pattern = add_site_nav.nav_html("", "pattern")
    atlas = add_site_nav.nav_html("", "pattern-atlas")
    assert 'aria-current="page"' in pattern
    assert "形态决策台" in pattern
    assert 'aria-current="page"' in atlas
    assert "形态图谱" in atlas
    assert "max-width:1280px" in atlas


def test_analytics_tab_is_linked_and_active():
    nav = add_site_nav.nav_html("", "analytics")
    assert "访问统计" in nav
    assert "intel/analytics.html" in nav
    assert add_site_nav.kind_of("analytics.html") == "analytics"
    assert add_site_nav.active_of("analytics") == "analytics"


def test_inject_file_supports_single_page_systemd_hooks_and_is_idempotent(tmp_path):
    intel = tmp_path / "intel"
    intel.mkdir()
    page = intel / "pattern_decision_workspace.html"
    page.write_text("<html><body><h1>workspace</h1></body></html>", encoding="utf-8")

    assert add_site_nav.inject_file(page, tmp_path) is True
    once = page.read_text(encoding="utf-8")
    assert "形态决策台" in once
    assert once.count('<nav aria-label="弹幕情报库主导航"') == 1
    assert add_site_nav.inject_file(page, tmp_path) is False
    assert page.read_text(encoding="utf-8") == once
