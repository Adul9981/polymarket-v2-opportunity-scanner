"""Offline regression checks for the cloud-side pattern decision refresh."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import update_pattern_decision_live as live  # noqa: E402
import publish_pattern_live_snapshot as publisher  # noqa: E402


def market(slug: str, question: str, sports_type: str) -> dict:
    return {
        "slug": slug,
        "question": question,
        "groupItemTitle": "Match Winner" if sports_type == "moneyline" else question,
        "sportsMarketType": sports_type,
        "closed": False,
        "outcomes": json.dumps(["Alpha", "Beta"]),
        "outcomePrices": json.dumps(["0.55", "0.45"]),
        "clobTokenIds": json.dumps(["11", "22"]),
        "gameStartTime": "2026-10-22 12:00:00+00",
    }


def test_target_games_keeps_series_and_game_winners_only():
    event = {
        "slug": "lol-alpha-beta-2026-10-22",
        "markets": [
            market("lol-alpha-beta-2026-10-22", "Alpha vs Beta Match Winner", "moneyline"),
            market("lol-alpha-beta-2026-10-22-game1", "Game 1 Winner", "child_moneyline"),
            market("lol-alpha-beta-2026-10-22-game2", "Game 2 Winner", "child_moneyline"),
            market("lol-alpha-beta-2026-10-22-total-games-2pt5", "Games Total O/U 2.5", "totals"),
        ],
    }
    series, games = live.target_games(event)
    assert series and series["slug"].endswith("lol-alpha-beta-2026-10-22")
    assert sorted(games) == [1, 2]


def test_target_games_keeps_settled_child_winners_but_not_other_closed_markets():
    settled = market("lol-alpha-beta-2026-10-22-game1", "Game 1 Winner", "child_moneyline")
    settled["closed"] = True
    prop = market("lol-alpha-beta-2026-10-22-game1-both-teams-slay-baron", "Baron?", "lol_both_teams_baron")
    prop["closed"] = True
    event = {
        "slug": "lol-alpha-beta-2026-10-22",
        "markets": [settled, prop],
    }
    _series, games = live.target_games(event)
    assert sorted(games) == [1]


def test_event_start_uses_market_event_start_time_without_listing_date():
    event = {
        "startDate": "2026-10-01T00:00:00Z",
        "markets": [{
            "gameStartTime": "",
            "eventStartTime": "2026-10-22T12:00:00Z",
            "startDate": "2026-10-01T00:00:00Z",
        }],
    }
    ts, source = live.event_start(event)
    assert ts == live.parse_ts("2026-10-22T12:00:00Z")
    assert source == "eventStartTime"


def test_active_game_treats_later_open_market_as_prematch():
    event = {
        "slug": "cs2-alpha-beta-2026-10-22",
        "title": "Counter-Strike: Alpha vs Beta (BO3) - IEM",
        "markets": [
            market("cs2-alpha-beta-2026-10-22", "Match Winner", "moneyline"),
            market("cs2-alpha-beta-2026-10-22-game1", "Map 1 Winner", "child_moneyline"),
            market("cs2-alpha-beta-2026-10-22-game2", "Map 2 Winner", "child_moneyline"),
        ],
    }
    series, games = live.target_games(event)
    assert series and sorted(games) == [1, 2]
    assert live.active_game_number(games) == 1

    games[1]["outcomePrices"] = json.dumps(["0.995", "0.005"])
    assert live.active_game_number(games) == 2


def test_watchlist_filter_uses_registered_leagues_and_worlds():
    watchlist = {
        "games": {
            "lol": {
                "include_keywords": ["League of Legends"],
                "league_keywords": ["LCK", "Worlds"],
            },
            "cs2": {
                "include_keywords": ["Counter-Strike"],
                "league_keywords": ["BLAST"],
            },
        }
    }
    assert live.watchlist_match({"title": "League of Legends: A vs B - Worlds Swiss", "slug": "x"}, watchlist) == "lol"
    assert live.watchlist_match({"title": "Counter-Strike: A vs B - BLAST Open", "slug": "x"}, watchlist) == "cs2"
    assert live.watchlist_match({"title": "Counter-Strike: A vs B - DACH Masters", "slug": "x"}, watchlist) is None


def test_live_window_keeps_future_space_for_candidate_path():
    floor = live.parse_ts("2026-10-22 12:00:00+00")
    now = floor + 20 * 60
    sides = {
        0: [(floor + index * 60, 0.55 + index * 0.002) for index in range(21)],
        1: [(floor + index * 60, 0.45 - index * 0.002) for index in range(21)],
    }
    event = {"slug": "lol-alpha-beta-2026-10-22", "title": "League of Legends: Alpha vs Beta (BO3) - LCK"}
    winner = market("lol-alpha-beta-2026-10-22-game1", "Game 1 Winner", "child_moneyline")
    payload = live.market_payload(
        event=event,
        sport="lol",
        level="game",
        game=1,
        market=winner,
        sides=sides,
        floor=floor,
        now=now,
        phase="live",
    )
    assert payload is not None
    assert payload["status"] == "盘面进行中"
    assert 35 <= payload["observed_max"] <= 75
    assert payload["last_ts"] == now


def test_prematch_can_use_current_outcome_price_without_fake_history():
    floor = live.parse_ts("2026-10-22 12:00:00+00")
    now = floor - 3600
    winner = market("lol-alpha-beta-2026-10-22", "Alpha vs Beta Match Winner", "moneyline")
    floor_floor = floor
    event = {"slug": "lol-alpha-beta-2026-10-22", "title": "League of Legends: Alpha vs Beta (BO3) - LCK"}
    payload = live.market_payload(
        event=event,
        sport="lol",
        level="series",
        game=None,
        market=winner,
        sides={0: [(now, 0.55)], 1: [(now, 0.45)]},
        floor=floor_floor,
        now=now,
        phase="prematch",
    )
    assert payload is not None
    assert payload["status"] == "赛前待走势"
    assert all(len(path) == 1 for path in payload["paths"].values())


def test_watchlist_time_window_drives_future_scan_range():
    watchlist = {"time_window": {"recent_started_days": 1.5, "upcoming_days": 2}}
    assert live.time_window_days(watchlist) == (1.5, 2.0)
    assert live.time_window_days({}) == (2.0, 2.0)


def test_stake_market_flattening_and_devig_probability():
    winner = {
        "id": "winner-1",
        "name": "Match Winner - Twoway",
        "status": "active",
        "updatedAt": 1_792_633_237_312,
        "outcomes": [
            {"name": "Aurora Gaming", "odds": 1.22, "active": True},
            {"name": "The MongolZ", "odds": 3.8, "active": True},
        ],
    }
    groups = [
        {"name": "main", "markets": [[winner]]},
        {"name": "winner", "markets": [[winner]]},
        {"name": "maps", "markets": [[
            {
                "id": "map-1",
                "name": "Map 1 Winner - Twoway",
                "status": "active",
                "outcomes": [{"odds": 1.4}, {"odds": 2.8}],
            }
        ]]},
    ]
    markets = live.stake_markets({"groups": groups})
    assert len(markets) == 2
    parsed = live.stake_match_winner(markets)
    assert parsed is not None
    assert [item["name"] for item in parsed["outcomes"]] == ["Aurora Gaming", "The MongolZ"]
    assert abs(sum(item["fair_probability"] for item in parsed["outcomes"]) - 1.0) < 1e-6
    assert live.stake_game_numbers(markets) == [1]


def test_schedule_links_to_matching_polymarket_match():
    schedule = {
        "sport": "lol",
        "teams": ["Anyone's Legend", "Karmine Corp"],
        "start_ts": 1_792_785_600,
    }
    match = {
        "slug": "lol-al-kc-2026-10-23",
        "sport": "lol",
        "teams": ["Anyone's Legend", "Karmine Corp"],
        "start_ts": 1_792_785_900,
        "status": "赛前待走势",
    }
    assert live.stake_matches_polymarket(schedule, match) is True
    match["teams"] = ["Karmine Corp", "Anyone's Legend"]
    assert live.stake_matches_polymarket(schedule, match) is True
    match["teams"] = ["T1", "Gen.G"]
    assert live.stake_matches_polymarket(schedule, match) is False


def test_schedule_team_aliases_handle_short_abbreviations():
    base = {"sport": "lol", "start_ts": 1_792_792_800}
    pm = {"sport": "lol", "start_ts": 1_792_792_900, "teams": ["LOS", "T1"]}
    assert live.stake_matches_polymarket({**base, "teams": ["Los Grandes", "T1 Esports"]}, pm) is True


def test_merge_replaces_previous_cloud_matches_and_preserves_training():
    base = {
        "generated_at": "old",
        "training": [{"slug": "history-1", "s": "lol", "l": "game"}],
        "matches": [
            {"slug": "cloud-old", "status": "盘面进行中", "source": "live_polymarket_cloud", "date": "2026-10-21"},
            {"slug": "history-1", "status": "已结束", "date": "2026-10-01"},
        ],
        "stats": {"training_samples": 1, "training_matches": 1},
        "source_reports": ["history.json"],
    }
    live_match = {
        "slug": "cloud-new",
        "status": "盘面进行中",
        "source": "live_polymarket_cloud",
        "date": "2026-10-22",
        "markets": {"series": {}},
    }
    merged = live.merge_dataset(base, [live_match], {"built_matches": 1}, "live source")
    assert [item["slug"] for item in merged["matches"]] == ["cloud-new", "history-1"]
    assert merged["training"] == base["training"]
    assert merged["stats"]["live_matches"] == 1
    assert "live source" in merged["source_reports"]


def test_merge_adds_future_schedule_with_polymarket_coverage():
    base = {"generated_at": "old", "training": [{"slug": "history"}], "matches": [], "stats": {}}
    match = {
        "slug": "lol-alpha-beta-2026-10-23",
        "sport": "lol",
        "teams": ["Alpha", "Beta"],
        "start_ts": 1_792_800_000,
        "status": "赛前待走势",
        "source": "live_polymarket_cloud",
        "date": "2026-10-23",
        "markets": {"series": {}},
    }
    schedule = [{
        "sport": "lol",
        "teams": ["Alpha", "Beta"],
        "start_ts": 1_792_800_100,
        "status": "待开赛",
        "polymarket_slug": "",
    }]
    merged = live.merge_dataset(base, [match], {}, "live", schedule)
    assert merged["upcoming_schedule"][0]["polymarket_slug"] == "lol-alpha-beta-2026-10-23"
    assert merged["stats"]["upcoming_schedule"] == 1


def test_template_uses_explicit_prematch_prior():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "status==='赛前待走势'" in template
    assert "赛前等待走势" in template
    assert "points.length<2" in template
    assert "prematch?scoredPool.filter" in template
    assert "赛前先验 · 前 10% 片段" in template
    assert "未来赛程" in template
    assert "upcoming_schedule" in template
    assert "PM 待开盘" in template
    assert "Stake 十进制赔率与 Polymarket 0–1 价格不混画" in template


def test_template_charts_both_sides_and_projection_layers():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "双方价格路径 × 候选延续" in template
    assert "蓝实线＝" in template
    assert "橙实线＝" in template
    assert "50:50 · 中枢" in template
    assert "#ff9f0a" in template
    assert "function candidateChart" in template
    assert "同类历史分钟路径" in template
    assert "中位线与区间由同层真实分钟路径计算" in template
    assert "Draw both real series last" in template


def test_template_navigation_points_to_related_pattern_pages():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert 'href="pattern_structure_audit_2026-10-22.html">新版形态审计' in template
    assert 'href="pattern_library.html">形态总库' in template
    assert 'href="pattern_playbook.html">形态速查' in template
    assert 'href="pattern_taxonomy.html">形态分类' in template
    assert 'href="pattern_library.html#charts_lol">分类图表' in template
    assert 'href="pattern_frequency_index.html">频率排行' in template


def test_prematch_prior_uses_one_minute_history_without_mislabelling_current_data():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "function poolGranularity()" in template
    assert "currentMarket.status==='赛前待走势'&&currentMarket.granularity==='数据不足'" in template
    assert "t.gr===poolGranularity()" in template
    assert "历史 '+pool+'先验" in template
    assert "当前行情粒度" in template
    assert "历史匹配粒度" in template


def test_candidate_curves_are_complete_and_smoothed_for_wide_laptops():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "function smoothSvgPath" in template
    assert "Catmull-Rom" in template
    assert "全部原始点位参与平滑连接" in template
    assert "futureDistribution(records,invert,steps=180)" in template
    assert "const w=920,h=540" in template
    assert "@media(max-width:1360px){.candidate-workbench{grid-template-columns:1fr}" in template


def test_candidate_projections_use_the_matched_team_side_coordinate():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "futureDistribution(g.records,false)" in template
    assert "representativePaths(g.records,false,5)" in template
    assert "matched record's future is already in the current-side analog" in template
    assert "候选方向" in template
    assert "右半边把历史同类路径统一换算到“" in template
    assert "不是双方同时到 100c" in template


def test_side_toggle_is_not_a_user_direction_choice():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert 'id="sideToggle"' not in template
    assert "side-toggle" not in template
    assert "双方同时评估" in template
    assert "系统固定价格坐标" in template
    assert "不需要你切换观察侧" in template


def test_decision_workspace_ranks_current_structure_by_model_similarity_not_team_frequency():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "当前形态，与形态模型库做结构匹配" in template
    assert "队伍身份不进入主匹配排序" in template
    assert "队伍过去出现某种形态的次数不参与主排序" in template
    assert "function structureSimilarity" in template
    assert "sort((a,b)=>a.matchDistance-b.matchDistance||uniqueMatchMass(b.records)-uniqueMatchMass(a.records))" in template
    assert "structureSimilarity:structureSimilarity(matchDistance)" in template
    assert "Number(c.share||0)*clamp(Number(c.structureSimilarity||0),.05,1)" in template
    assert "结构相似度" in template
    assert "建议关注区间" in template


def test_match_picker_defaults_to_live_or_nearest_upcoming_and_can_return():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "function defaultMatchForList(list)" in template
    assert "function matchIsLiveFresh(match)" in template
    assert "matchIsLiveFresh(match)?'live':'stale'" in template
    assert "start>=now-6*60*60?'upcoming':'stale'" in template
    assert "matchStateKind(m)==='live'" in template
    assert "matchStateKind(m)==='upcoming'&&matchStartTs(m)>=now-900" in template
    assert "matchStateKind(m)==='stale'" in template
    assert "manualMatchSelection?previousSlug:null" in template
    assert 'id="jumpCurrentMatch"' in template
    assert "回到进行中 / 最近赛程" in template


def test_candidate_chart_uses_fixed_right_information_panel():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "const panelX=plotRight+12" in template
    assert "固定右侧信息栏" in template or "Fixed right-hand panel" in template
    assert "结构结论" in template
    assert "建议买入" in template
    assert "镜像终点" in template
    assert "右侧改为固定信息栏" in template


def test_cached_labels_are_refreshed_to_current_chinese_names():
    dataset = {
        "labels": {
            "A3_折价修复": {
                "title": "A3 折价修复",
                "family": "反转",
                "summary": "不是 B4 阴跌，而是 A3_折价修复。",
            }
        }
    }
    refreshed = live.normalise_display_labels(dataset)
    label = refreshed["labels"]["A3_折价修复"]
    assert label["title"] == "高位回撤修复"
    assert label["family"] == "反转结构"
    assert "A3" not in label["summary"]
    assert "B4" not in label["summary"]


def test_atomic_publish_is_readable_by_web_server(tmp_path):
    target = tmp_path / "decision.html"
    live.atomic_write(target, "<html>ok</html>")
    assert target.read_text(encoding="utf-8") == "<html>ok</html>"
    assert target.stat().st_mode & 0o777 == 0o644


def test_live_refresh_refuses_to_regress_the_training_corpus():
    live.validate_base_corpus(
        {"stats": {"training_matches": 3109, "training_samples": 35405}},
        {"stats": {"training_matches": 3109, "training_samples": 35405}},
    )
    try:
        live.validate_base_corpus(
            {"stats": {"training_matches": 365, "training_samples": 14754}},
            {"stats": {"training_matches": 3109, "training_samples": 35405}},
        )
    except RuntimeError as exc:
        assert "base corpus regressed" in str(exc)
    else:
        raise AssertionError("a stale base corpus must not overwrite the verified live page")


def test_live_snapshot_is_compact_and_contains_only_current_cloud_matches():
    dataset = {
        "generated_at": "2026-11-04T08:26:35+08:00",
        "generated_date": "2026-11-04",
        "live_refresh": {"fetched_at": "2026-11-04T00:26:12+00:00", "built_matches": 1},
        "matches": [
            {"slug": "live-1", "source": "live_polymarket_cloud", "status": "盘面进行中"},
            {"slug": "history-1", "source": "history", "status": "已结束"},
        ],
        "upcoming_schedule": [{"sport": "lol", "teams": ["Alpha", "Beta"]}],
        "stats": {"training_samples": 100, "training_matches": 10, "matches": 2, "live_matches": 1},
        "training": [{"large": "payload"} for _ in range(100)],
    }

    snapshot = live.compact_live_snapshot(dataset)

    assert snapshot["generated_at"] == dataset["generated_at"]
    assert snapshot["live_refresh"] == dataset["live_refresh"]
    assert [item["slug"] for item in snapshot["matches"]] == ["live-1"]
    assert snapshot["upcoming_schedule"] == dataset["upcoming_schedule"]
    assert snapshot["stats"]["live_matches"] == 1
    assert "training" not in snapshot


def test_template_refreshes_live_snapshot_without_reloading_the_ten_megabyte_page():
    template = (ROOT / "tools" / "pattern_decision_workspace.template.html").read_text(encoding="utf-8")
    assert "pattern_decision_live.json" in template
    assert "cache:'no-store'" in template
    assert "applyLiveSnapshot" in template
    assert "REFRESH_INTERVAL_MS=60000" in template
    assert "startRefreshLoop" in template
    assert "refreshCountdown" in template
    assert "刷新失败 · '" in template
    assert "setInterval(refreshLiveSnapshot,60000)" not in template


def test_publisher_rejects_stale_or_historical_snapshot_payloads():
    import datetime as dt

    payload = {
        "schema_version": 1,
        "generated_at": "2026-11-04T08:26:35+08:00",
        "matches": [{"slug": "live-1", "source": "live_polymarket_cloud"}],
    }
    now = dt.datetime(2026, 11, 4, 0, 30, tzinfo=dt.timezone.utc)
    assert publisher.validate_snapshot_data(payload, now=now)["matches"][0]["slug"] == "live-1"

    try:
        publisher.validate_snapshot_data({**payload, "generated_at": "2026-11-04T07:00:00+08:00"}, now=now)
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale snapshot must be rejected")

    try:
        publisher.validate_snapshot_data({**payload, "training": []}, now=now)
    except ValueError as exc:
        assert "training" in str(exc)
    else:
        raise AssertionError("training corpus must not enter the live snapshot")


def test_completed_games_keep_their_minute_path_instead_of_becoming_prematch():
    assert live.market_phase_for_target("live", "game", 1, current_game=3) == "live"
    assert live.market_phase_for_target("live", "game", 3, current_game=3) == "live"
    assert live.market_phase_for_target("live", "game", 4, current_game=3) == "prematch"


def test_history_fetch_is_limited_to_live_series_current_and_uncached_past_games():
    assert live.target_needs_history("live", "series", None, 3, False) is True
    assert live.target_needs_history("live", "game", 3, 3, False) is True
    assert live.target_needs_history("live", "game", 4, 3, False) is False
    assert live.target_needs_history("live", "game", 1, 3, True) is False
    assert live.target_needs_history("live", "game", 1, 3, False) is True
    assert live.target_needs_history("prematch", "series", None, 1, False) is True
    assert live.target_needs_history("prematch", "game", 1, 1, False) is False


def test_price_cache_keeps_minute_history_when_closed_market_only_returns_endpoints():
    cache = {"schema_version": 1, "points": {}}
    market_payload = market("lol-alpha-beta-2026-10-22-game1", "Game 1 Winner", "child_moneyline")
    start = live.parse_ts("2026-10-22 12:00:00+00")
    original = [(start + index * 60, 0.55 + index * 0.001) for index in range(50)]
    live.merge_market_history(
        cache,
        slug="lol-alpha-beta-2026-10-22",
        level="game",
        game=1,
        market=market_payload,
        fresh_sides={0: original},
    )

    merged = live.merge_market_history(
        cache,
        slug="lol-alpha-beta-2026-10-22",
        level="game",
        game=1,
        market=market_payload,
        fresh_sides={0: [(original[-1][0] - 60, original[-1][1]), original[-1]]},
    )

    assert len(merged[0]) == 50
    assert merged[0][0] == original[0]
    assert merged[0][-1] == original[-1]
    assert len(cache["points"]) == 1


def test_price_cache_updates_same_timestamp_with_fresh_price():
    start = live.parse_ts("2026-10-22 12:00:00+00")
    merged = live.merge_price_points(
        [(start, 0.50), (start + 60, 0.52)],
        [(start + 60, 0.54), (start + 120, 0.56)],
    )
    assert merged == [(start, 0.50), (start + 60, 0.54), (start + 120, 0.56)]


def test_http_fallback_uses_parallel_proxy_pool_after_cloudflare_451(monkeypatch):
    import urllib.error

    direct_calls = 0
    fanout_calls = 0

    def denied(*_args, **_kwargs):
        nonlocal direct_calls
        direct_calls += 1
        raise urllib.error.HTTPError("https://example.invalid", 451, "blocked", None, None)

    def fanout(*_args, **_kwargs):
        nonlocal fanout_calls
        fanout_calls += 1
        return {"ok": True}

    monkeypatch.setattr(live.urllib.request, "urlopen", denied)
    monkeypatch.setattr(live.pm_http, "get_json_fanout", fanout)

    assert live.http_json("https://example.invalid", tries=3) == {"ok": True}
    assert direct_calls == 1
    assert fanout_calls == 1


def test_event_hydration_uses_full_detail_with_settled_child_markets(monkeypatch):
    listed = {"slug": "lol-alpha-beta-2026-10-22", "markets": [{"slug": "series"}]}
    detailed = {
        "slug": "lol-alpha-beta-2026-10-22",
        "markets": market("series", "Match Winner", "moneyline") | {"slug": "series"},
    }
    detailed["markets"] = [
        detailed["markets"],
        market("game1", "Game 1 Winner", "child_moneyline") | {"slug": "game1"},
    ]
    monkeypatch.setattr(live, "http_json", lambda *_args, **_kwargs: [detailed])
    refreshed = live.hydrate_event(listed)
    assert len(refreshed["markets"]) == 2
