"""Regression tests for the Stake pre-match intelligence adapter."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_stake_prematch_site",
    ROOT / "tools" / "build_stake_prematch_site.py",
)
assert SPEC and SPEC.loader
stake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stake)

DETAIL_SPEC = importlib.util.spec_from_file_location(
    "prematch_detail",
    ROOT / "tools" / "prematch_detail.py",
)
assert DETAIL_SPEC and DETAIL_SPEC.loader
prematch_detail = importlib.util.module_from_spec(DETAIL_SPEC)
DETAIL_SPEC.loader.exec_module(prematch_detail)


def two_way_market(status: str = "active", active: bool = True) -> dict:
    return {
        "groups": [{
            "name": "main",
            "markets": [[{
                "id": "winner-1",
                "name": "Match Winner - Twoway",
                "status": status,
                "specifiers": "variant=way:two|way=two",
                "updatedAt": 1_792_633_237_312,
                "outcomes": [
                    {"name": "Aurora", "odds": 1.25, "active": active},
                    {"name": "MongolZ", "odds": 4.0, "active": active},
                ],
            }]],
        }]
    }


def football_market() -> dict:
    return {
        "groups": [{
            "name": "main",
            "markets": [[{
                "id": "1x2-1",
                "name": "1x2",
                "status": "active",
                "specifiers": "",
                "updatedAt": 1_792_633_237_312,
                "outcomes": [
                    {"name": "Brentford", "odds": 2.1, "active": True},
                    {"name": "Draw", "odds": 3.5, "active": True},
                    {"name": "Everton", "odds": 3.2, "active": True},
                ],
            }]],
        }]
    }


def test_two_way_market_is_devigged() -> None:
    markets = stake.flatten_markets(two_way_market())
    winner = stake.normalize_winner(markets, "lol")
    assert winner is not None
    assert winner["market_type"] == "two_way"
    assert [item["name"] for item in winner["outcomes"]] == ["Aurora", "MongolZ"]
    assert abs(sum(item["fair_probability"] for item in winner["outcomes"]) - 1.0) < 1e-6
    assert winner["margin"] > 0


def test_football_three_way_market_keeps_draw() -> None:
    markets = stake.flatten_markets(football_market())
    winner = stake.normalize_winner(markets, "football")
    assert winner is not None
    assert winner["market_type"] == "three_way"
    assert [item["name"] for item in winner["outcomes"]] == ["Brentford", "Draw", "Everton"]
    assert abs(sum(item["fair_probability"] for item in winner["outcomes"]) - 1.0) < 1e-6


def test_suspended_market_is_a_gap_not_a_zero_price() -> None:
    payload = two_way_market(status="suspended", active=False)
    markets = stake.flatten_markets(payload)
    state, label = stake.classify_market_state(markets, "cs2")
    assert (state, label) == ("suspended", "盘口暂停")
    assert stake.normalize_winner(markets, "cs2") is None


def test_only_exact_full_match_winner_market_is_selected() -> None:
    payload = football_market()
    payload["groups"][0]["markets"][0].append({
        "id": "half-1x2",
        "name": "1st Half - 1x2",
        "status": "active",
        "specifiers": "",
        "outcomes": [
            {"name": "Brentford", "odds": 2.8, "active": True},
            {"name": "Draw", "odds": 2.2, "active": True},
            {"name": "Everton", "odds": 3.7, "active": True},
        ],
    })
    markets = stake.flatten_markets(payload)
    candidates = stake.winner_market_candidates(markets, "football")
    assert [market["id"] for market in candidates] == ["1x2-1"]


def test_competitor_names_prefer_explicit_fixture_competitors() -> None:
    fixture = {
        "name": "Sabah Masazir - Barcelona",
        "competitors": ["Sabah FC", "Barcelona"],
    }
    assert stake.competitor_names(fixture) == ["Sabah FC", "Barcelona"]


def test_fixture_normalization_and_html_preserve_data_provenance() -> None:
    fixture = {
        "id": "f1",
        "slug": "1795464000000-brentford-everton",
        "name": "Brentford - Everton",
        "startTime": 1_795_464_000_000,
        "status": "active",
        "updatedAt": 1_795_430_000_000,
        "provider": "betradar",
        "competitors": ["Brentford", "Everton"],
    }
    sport = {
        "key": "football",
        "label": "足球",
        "short": "足球",
    }
    row = stake.normalize_fixture(
        sport=sport,
        competition={"category": "england", "tournament": "premier-league", "label": "英超"},
        fixture=fixture,
        detail=football_market(),
        now=1_795_400_000,
    )
    assert row is not None
    assert row["league"] == "英超"
    assert row["market_state"] == "available"
    snapshot = {
        "generated_at_bj": "2026-11-23 20:00:00",
        "horizon_hours": 72,
        "generated_at_utc": "2026-11-23T12:00:00+00:00",
        "source": {
            "docs_url": "https://docs-odds-data.stake.com/",
        },
        "stats": {
            "fixtures": 1,
            "valid_odds": 1,
            "sports": 1,
            "suspended": 0,
        },
        "coverage": {
            "football": {
                "label": "足球",
                "short": "足球",
                "fixtures": 1,
                "valid_odds": 1,
                "suspended": 0,
                "missing": 0,
            },
        },
        "fixtures": [row],
        "diagnostics": {"errors": []},
    }
    page = stake.render_page(snapshot)
    assert "赛前情报" in page
    assert "Brentford" in page
    assert "去水概率" in page
    assert "公开赛前市场报价换算并去水" in page
    assert "AI 聚合" in page
    assert "数据审计文件" in page
    assert "Stake Sports Data API" not in page


def test_fixture_detail_failure_still_keeps_a_non_fabricated_market_gap() -> None:
    fixture = {
        "id": "f-gap",
        "slug": "fixture-gap",
        "name": "Alpha - Beta",
        "startTime": 1_795_464_000_000,
        "status": "active",
        "provider": "betradar",
        "competitors": ["Alpha", "Beta"],
    }
    row = stake.normalize_fixture(
        sport={"key": "football", "label": "足球", "short": "足球"},
        competition={"category": "england", "tournament": "premier-league", "label": "英超"},
        fixture=fixture,
        detail={},
        now=1_795_400_000,
    )
    assert row is not None
    assert row["market_state"] == "missing"
    assert row["winner_market"] is None


def test_render_gap_does_not_invent_probability() -> None:
    row = {
        "sport": "cs2",
        "sport_label": "CS2",
        "sport_short": "CS2",
        "league": "BLAST",
        "teams": ["Alpha", "Beta"],
        "name": "Alpha - Beta",
        "start_ts": 1_795_464_000,
        "start_at_bj": "11-25 08:00",
        "date_bj": "2026-11-25",
        "format": "BO3",
        "market_label": "独赢",
        "status": "待开赛",
        "status_key": "upcoming",
        "market_state": "suspended",
        "market_state_label": "盘口暂停",
        "winner_market": None,
        "source_updated_at": "2026-11-23T12:00:00+00:00",
        "source_url": "https://odds-data.stake.com/fixtures/example",
    }
    rendered = stake.outcome_rows(row)
    assert "盘口暂停" in rendered
    assert "不沿用旧赔率" in rendered
    assert "0.0%" not in rendered


def test_platform_player_duels_are_extracted_without_local_profiles() -> None:
    detail = {
        "groups": [{
            "name": "players",
            "markets": [
                [{
                    "id": "duel-1",
                    "name": "Map 1 - Duel of Player Kills Draw No Bet",
                    "specifiers": "map=1|slot=1",
                    "outcomes": [
                        {"name": "History", "active": True},
                        {"name": "Z4kr", "active": True},
                    ],
                }],
                [{
                    "id": "duel-2",
                    "name": "Map 1 - Duel of Player Kills Draw No Bet",
                    "specifiers": "map=1|slot=2",
                    "outcomes": [
                        {"name": "Starry", "active": True},
                        {"name": "Huasopeek", "active": True},
                    ],
                }],
                [{
                    "id": "starry-kills",
                    "name": "Map 1 - Starry Total Kills",
                    "specifiers": "map=1|slot=2|threshold=13.5",
                    "outcomes": [
                        {"name": "Under", "odds": 1.9, "active": True},
                        {"name": "Over", "odds": 1.9, "active": True},
                    ],
                }],
            ],
        }],
    }
    intel = stake.extract_platform_player_intel(
        detail,
        ["9z Team", "Lynn Vision"],
        "cs2",
    )
    assert intel["status"] == "partial"
    assert intel["team_players"]["9z Team"][0]["name"] == "History"
    assert intel["team_players"]["Lynn Vision"][0]["name"] == "Z4kr"
    starry = next(
        item for item in intel["team_players"]["9z Team"] if item["name"] == "Starry"
    )
    assert starry["metrics"] == ["击杀"]
    assert starry["projections"]["击杀"]["line"] == 13.5
    assert stake.player_metric_text(starry) == "击杀 13.5"
    assert "不等于官方首发" in intel["note"]


def test_non_esports_player_props_are_not_treated_as_a_lineup() -> None:
    intel = stake.extract_platform_player_intel({}, ["Team A", "Team B"], "football")
    assert intel["status"] == "not_applicable"
    assert intel["team_players"] == {"Team A": [], "Team B": []}


def test_team_kill_baseline_uses_the_most_balanced_line() -> None:
    markets = [
        {
            "name": "Match home Total Kills",
            "specifiers": "side=home|threshold=71.5",
            "outcomes": [
                {"name": "Under 71.5", "odds": 2.2, "active": True},
                {"name": "Over 71.5", "odds": 1.65, "active": True},
            ],
        },
        {
            "name": "Match home Total Kills",
            "specifiers": "side=home|threshold=73.5",
            "outcomes": [
                {"name": "Under 73.5", "odds": 1.9, "active": True},
                {"name": "Over 73.5", "odds": 1.9, "active": True},
            ],
        },
        {
            "name": "Match away Total Kills",
            "specifiers": "side=away|threshold=58.5",
            "outcomes": [
                {"name": "Under 58.5", "odds": 1.85, "active": True},
                {"name": "Over 58.5", "odds": 1.85, "active": True},
            ],
        },
    ]
    intel = stake.extract_team_market_intel(markets, ["Alpha", "Beta"], "dota2")
    assert intel["Alpha"]["kills_line"] == 73.5
    assert intel["Beta"]["kills_line"] == 58.5


def test_oddin_widget_parameters_are_extracted_from_stake_html() -> None:
    html = (
        '<iframe src="https://disir.oddin.gg/csgo/match?'
        'availableData=tournament&amp;availableData=teams'
        '&amp;awayTeamId=dGVhbS9hd2F5'
        '&amp;brandToken=public-token'
        '&amp;homeTeamId=dGVhbS9ob21l'
        '&amp;id=bWF0Y2gvbWF0Y2g6MQ%3D%3D'
        '&amp;lang=zh'
        '&amp;tournamentId=dG91cm5hbWVudDox'
        '&amp;timeframe=THREE_MONTHS"></iframe>'
    )
    params = stake.stake_oddin.extract_widget_params(html)
    assert params["game"] == "csgo"
    assert params["brandToken"] == "public-token"
    assert params["id"] == "bWF0Y2gvbWF0Y2g6MQ=="
    assert params["homeTeamId"] == "dGVhbS9ob21l"


def test_oddin_csgo_team_normalization_keeps_map_pool_and_players() -> None:
    team = {
        "team": {"id": "team-1", "name": "Alpha", "iconPath": ""},
        "overallMapWinrate": {"avg": 61.5, "percentile": 70, "total": 13, "sampleSize": 20},
        "mapWinrate": [{
            "map": {"name": "Mirage"},
            "statistics": {"avg": 66.7, "percentile": 75, "total": 6},
        }],
        "mapVote": {
            "picked": [{
                "map": {"name": "Mirage"},
                "statistics": {"avg": 50, "percentile": 60, "total": 4},
            }],
            "banned": [],
        },
        "playerStatistics": [{
            "player": {"id": "p1", "nickname": "ace"},
            "kills": {"avg": 0.75, "percentile": 70, "total": 100},
        }],
        "favouriteWeapons": [{
            "weapon": {"name": "AK-47"},
            "killsWithWeapon": {"avg": 20, "percentile": 60, "total": 100},
        }],
        "form": [],
    }
    normalized = stake.stake_oddin._team_package(team, "csgo")
    assert normalized["map_winrate"]["avg"] == 61.5
    assert normalized["map_pool"][0]["name"] == "Mirage"
    assert normalized["map_pool"][0]["pick_rate"]["avg"] == 50
    assert normalized["players"][0]["nickname"] == "ace"
    assert normalized["favorites"][0]["name"] == "AK-47"


def test_oddin_h2h_uses_team_ids_not_argument_order() -> None:
    payload = {
        "data": {
            "dota2TeamsHistoricalStatistics": {
                "teamStatistics": [
                    {"team": {"id": "home", "name": "Home"}, "players": [], "form": []},
                    {"team": {"id": "away", "name": "Away"}, "players": [], "form": []},
                ],
                "pastFiveEncounters": [{
                    "id": "m1",
                    "plannedStartTimestamp": "2026-11-01T00:00:00Z",
                    "homeTeam": {"id": "away", "name": "Away"},
                    "awayTeam": {"id": "home", "name": "Home"},
                    "homeScore": 2,
                    "awayScore": 1,
                    "winTeam": {"id": "away", "name": "Away"},
                    "isClosed": True,
                }],
            }
        }
    }
    teams = stake.stake_oddin._normalize_team_data("dota2", payload)
    assert [item["name"] for item in teams] == ["Home", "Away"]


def test_lmt_latest_lineup_uses_historical_side() -> None:
    class FakeClient:
        def get(self, path: str) -> dict:
            assert path == "match_squads/previous"
            return {
                "doc": [{
                    "data": {
                        "home": {
                            "startinglineup": {
                                "formation": "4-4-2",
                                "players": [{"playername": "Home Player"}],
                            }
                        },
                        "away": {
                            "startinglineup": {
                                "formation": "4-3-3",
                                "players": [{"playername": "Away Player"}],
                            }
                        },
                    }
                }]
            }

    lineup, status = stake.stake_lmt._latest_lineup(
        FakeClient(),
        {"home": {}, "away": {}},
        "home",
        [{"id": "previous", "home_away": "away", "date": {"utc": "2026-11-01"}}],
    )
    assert status == "latest_available"
    assert lineup["formation"] == "4-3-3"
    assert lineup["players"][0]["name"] == "Away Player"


def test_lmt_licensing_decrypts_public_payload() -> None:
    secret = {
        "fishnetToken": {"token": "token", "expirationTs": 9_999_999_999_999},
        "packages": ["football"],
    }
    raw_plain = json.dumps(secret, separators=(",", ":")).encode()
    salt = b"12345678"
    key, iv = stake.stake_lmt._evp_bytes_to_key(stake.stake_lmt.CLIENT_ID.encode(), salt)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw_plain) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    payload = {"text": base64.b64encode(b"Salted__" + salt + ciphertext).decode()}
    decoded = stake.stake_lmt.decrypt_licensing(payload)
    assert decoded == secret


def test_lmt_nba_dynamic_table_preserves_basketball_columns() -> None:
    tables = stake.stake_lmt._league_tables({
        "tables": [{
            "_id": "112268",
            "name": "美国职业篮球联赛",
            "currentround": None,
            "maxrounds": 0,
            "tablerows": [{
                "pos": 1,
                "team": {"uid": 3420, "name": "76人"},
                "total": 17,
                "winTotal": 14,
                "lossTotal": 3,
                "pctTotal": 0.824,
                "gb": "-",
                "streak": 5,
                "lastTenGamesWin": 8,
                "lastTenGamesLoss": 2,
                "winHome": 7,
                "lossHome": 2,
                "winAway": 7,
                "lossAway": 1,
            }],
        }],
    })
    row = tables[0]["rows"][0]
    assert row["position"] == 1
    assert row["played"] == 17
    assert row["wins"] == 14
    assert row["losses"] == 3
    assert row["win_pct"] == 0.824
    assert row["last_ten_wins"] == 8
    assert row["home_wins"] == 7


def test_visible_zero_and_oddin_panel_are_rendered_without_brand_label() -> None:
    assert stake.esc(0) == "0"
    deep = {
        "game": "dota2",
        "coverage": {
            "players": 10,
            "favorites": 30,
            "map_pool": 0,
            "h2h": 0,
            "pool_rows": 127,
        },
        "home": {
            "id": "h",
            "name": "Home",
            "map_winrate": {"avg": 55, "sample_size": 20},
            "metrics": {},
            "players": [],
            "favorites": [],
            "recent_matches": [],
        },
        "away": {
            "id": "a",
            "name": "Away",
            "map_winrate": {"avg": 50, "sample_size": 20},
            "metrics": {},
            "players": [],
            "favorites": [],
            "recent_matches": [],
        },
        "head_to_head": {"home_wins": 0, "away_wins": 0, "matches": []},
        "tournament": {
            "metadata": {"tournament": {"name": "Event"}},
            "teams": [],
            "matches": [],
            "standings": [],
            "stats": {"pools": []},
        },
    }
    html = stake.render_oddin_panel({"oddin": deep})
    assert "完整赛前数据" in html
    assert "选手 10 人" in html
    assert "H2H 0 胜 · 0 负" in html
    assert "Stake" not in html
    assert "Oddin" not in html


def test_oddin_favorites_are_not_truncated() -> None:
    favorites = [
        {
            "hero": {"id": f"h{i}", "name": f"Hero {i}"},
            "pickRate": {"avg": 0.1, "percentile": 50, "total": 2},
            "banRate": {"avg": 0.2, "percentile": 60, "total": 3},
        }
        for i in range(20)
    ]
    normalized = stake.stake_oddin._team_package(
        {
            "team": {"id": "t1", "name": "Alpha"},
            "mapWinrate": {"avg": 55, "percentile": 60, "total": 10, "sampleSize": 20},
            "favouriteHeroes": favorites,
            "players": [],
            "form": [],
        },
        "dota2",
    )
    assert len(normalized["favorites"]) == 20


def test_detail_page_exports_html_json_and_csv(tmp_path: Path) -> None:
    row = {
        "id": "stake:fixture-1",
        "fixture_slug": "fixture-1",
        "sport": "cs2",
        "sport_short": "CS2",
        "league": "BLAST",
        "teams": ["Alpha", "Beta"],
        "start_at_bj": "11-24 12:00",
        "format": "BO3",
        "status": "待开赛",
        "winner_market": None,
        "market_state_label": "盘口暂停",
        "intel_coverage": {
            "teams": 2,
            "players": 2,
            "recent_matches": 2,
            "h2h": 0,
            "map_pool": 2,
            "favorites": 2,
        },
        "oddin": {
            "game": "csgo",
            "home": {
                "id": "a",
                "name": "Alpha",
                "map_winrate": {"avg": 60, "sample_size": 5},
                "metrics": {"kills": {"all": {"avg": 0.7, "percentile": 60, "total": 100}}},
                "map_pool": [{"name": "Mirage", "win_rate": {"avg": 60, "total": 5}}],
                "favorites": [{"name": "AK-47", "metrics": {"killsWithWeapon": {"avg": 10}}}],
                "players": [{"nickname": "ace", "metrics": {}, "favorites": []}],
                "recent_matches": [],
            },
            "away": {
                "id": "b",
                "name": "Beta",
                "map_winrate": {"avg": 50, "sample_size": 5},
                "metrics": {},
                "map_pool": [],
                "favorites": [],
                "players": [{"nickname": "bravo", "metrics": {}, "favorites": []}],
                "recent_matches": [],
            },
            "head_to_head": {"matches": []},
            "tournament": {
                "metadata": {"tournament": {"name": "Event"}},
                "teams": [],
                "matches": [],
                "standings": [],
                "stats": {"pools": []},
            },
        },
    }
    snapshot = {"generated_at_bj": "2026-11-23 23:45:00"}
    name = prematch_detail.write_detail(row, tmp_path, snapshot)
    assert name.endswith(".html")
    assert row["detail_json_url"].endswith(".json")
    assert row["detail_csv_url"].endswith(".csv")
    html = (tmp_path / name).read_text(encoding="utf-8")
    assert "全部队伍统计" in html
    assert "完整地图池" in html
    assert "下载完整 JSON" in html
    assert "Stake" not in html
    csv_text = (tmp_path / row["detail_csv_url"]).read_text(encoding="utf-8")
    assert "section,team,player,entity,metric" in csv_text


def test_detail_formatters_keep_integer_samples_and_pending_scores() -> None:
    assert prematch_detail.num(20, 0) == "20"
    assert prematch_detail.num(10, 0) == "10"
    rendered = prematch_detail.match_rows([
        {
            "planned_start": "2026-11-24T00:00:00Z",
            "home": {"name": "Alpha"},
            "away": {"name": "Beta"},
            "home_score": None,
            "away_score": None,
        }
    ])
    assert "待赛" in rendered
    assert "None" not in rendered
