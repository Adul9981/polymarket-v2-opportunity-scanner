"""Regression checks for the global search page and index."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import add_site_nav  # noqa: E402
import build_site_search as search  # noqa: E402


def _fixture_site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    intel = site / "intel"
    intel.mkdir(parents=True)
    for name in (
        "match_cs2-alpha-beta-2026-11-27.html",
        "intel_danmu_Alpha-Beta_2026-11-27_g1_mid.html",
        "intel_profile_team_alpha.html",
        "pattern_decision_workspace.html",
        "pattern_atlas.html",
        "intel_profiles_index.html",
        "intel_gray_verification_stats.html",
        "today.html",
        "history.html",
        "intel_prematch.html",
        "match_situation.html",
        "market_links.html",
    ):
        (intel / name).write_text(f"<html><body><h1>{name}</h1></body></html>", encoding="utf-8")
    matches = tmp_path / "matches.json"
    matches.write_text(
        json.dumps({
            "matches": [{
                "slug": "cs2-alpha-beta-2026-11-27",
                "teams": ["Alpha", "Beta"],
                "league": "CS2",
                "date": "2026-11-27",
                "result_inferred": "Alpha 2:0 Beta",
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return site


def test_build_search_creates_searchable_site(tmp_path, monkeypatch) -> None:
    site = _fixture_site(tmp_path)
    monkeypatch.setattr(search, "MATCHES_JSON", tmp_path / "matches.json")

    counts = search.build_all(site)

    assert counts == {"entries": counts["entries"], "search": 1}
    assert counts["entries"] >= 6
    search_html = (site / "intel" / "search.html").read_text(encoding="utf-8")
    index = json.loads((site / "intel" / "search_index.json").read_text(encoding="utf-8"))
    assert "搜索情报库" in search_html
    assert "search_index.json" in search_html
    assert any(row["title"] == "Alpha vs Beta" and row["type"] == "比赛" for row in index["entries"])


def test_new_hubs_receive_unified_navigation(tmp_path, monkeypatch) -> None:
    site = _fixture_site(tmp_path)
    monkeypatch.setattr(search, "MATCHES_JSON", tmp_path / "matches.json")
    search.build_all(site)

    assert add_site_nav.inject_all(site) >= 1
    text = (site / "intel" / "search.html").read_text(encoding="utf-8")
    assert text.count('<nav aria-label="弹幕情报库主导航"') == 1
    assert "形态决策台" in text
    assert "搜索" in text
    assert add_site_nav.kind_of("search.html") == "search"
