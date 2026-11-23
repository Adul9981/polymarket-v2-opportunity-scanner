"""Regression tests for standalone pre-match detail pages and exports."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "prematch_detail",
    ROOT / "tools" / "prematch_detail.py",
)
assert SPEC and SPEC.loader
detail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(detail)


def row(sport: str = "cs2") -> dict:
    team = {
        "id": sport,
        "name": "Alpha",
        "map_winrate": {"avg": 55.0, "sample_size": 20},
        "metrics": {
            "kills": {"all": {"avg": 0.7, "percentile": 75, "total": 100}},
        },
        "players": [{
            "id": "p1",
            "nickname": "ace",
            "real_name": "Ace Player",
            "role": "RIFLER",
            "metrics": {"damage": {"avg": 80, "percentile": 70, "total": 1000}},
            "favorites": [{
                "name": "AK-47",
                "metrics": {"killsWithWeapon": {"avg": 20, "total": 100}},
            }],
        }],
        "map_pool": [{
            "name": "Mirage",
            "win_rate": {"avg": 60, "total": 5},
            "pick_rate": {"avg": 40, "total": 2},
            "ban_rate": {"avg": 20, "total": 1},
            "rounds": {
                "terrorists": {"avg": 55},
                "counterTerrorists": {"avg": 65},
            },
        }],
        "favorites": [{
            "name": "AK-47",
            "metrics": {"killsWithWeapon": {"avg": 20, "total": 100}},
        }],
        "recent_matches": [],
    }
    return {
        "fixture_slug": "fixture-1",
        "sport": sport,
        "sport_short": sport,
        "sport_label": sport,
        "league": "Event",
        "teams": ["Alpha", "Beta"],
        "start_at_bj": "11-24 12:00",
        "format": "BO3",
        "status": "待开赛",
        "winner_market": {
            "outcomes": [
                {"name": "Alpha", "fair_probability": 0.6, "decimal_odds": 1.6},
                {"name": "Beta", "fair_probability": 0.4, "decimal_odds": 2.4},
            ]
        },
        "oddin": {
            "game": "csgo",
            "coverage": {
                "players": 2,
                "recent_matches": 0,
                "h2h": 0,
                "tournament_matches": 1,
                "pool_rows": 1,
            },
            "home": team,
            "away": {**team, "id": "away", "name": "Beta"},
            "head_to_head": {"matches": []},
            "tournament": {
                "metadata": {"tournament": {"name": "Event"}},
                "teams": [],
                "matches": [],
                "standings": [],
                "stats": {"pools": [], "best_teams": [], "best_players": []},
            },
        },
        "intel_coverage": {"players": 2},
    }


def test_detail_files_have_stable_names_and_exports(tmp_path: Path) -> None:
    item = row()
    snapshot = {"generated_at_bj": "2026-11-23 23:00:00"}
    html_name = detail.write_detail(item, tmp_path, snapshot)
    assert html_name == "intel_prematch_detail_cs2_fixture-1.html"
    assert item["detail_json_url"].endswith(".json")
    assert item["detail_csv_url"].endswith(".csv")
    assert (tmp_path / html_name).exists()
    assert (tmp_path / item["detail_json_url"]).exists()
    assert (tmp_path / item["detail_csv_url"]).exists()


def test_detail_page_contains_complete_team_player_and_market_sections() -> None:
    html = detail.render_page(
        row(),
        {"generated_at_bj": "2026-11-23 23:00:00"},
    )
    assert "全部队伍统计" in html
    assert "选手完整数据" in html
    assert "完整地图池" in html
    assert "赛前市场共识" in html
    assert "数据覆盖与缺口" in html
    assert "下载完整 JSON" in html
    assert "下载指标 CSV" in html
    assert "Stake" not in html
    assert "Oddin" not in html


def test_csv_export_flattens_grouped_metrics() -> None:
    csv_text = detail.render_csv(row())
    assert "team_metric" in csv_text
    assert "kills" in csv_text
    assert "all" in csv_text
    assert "player_metric" in csv_text
    assert "Mirage" in csv_text
