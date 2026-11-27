"""独立「比赛局势」页回归（2026-11-01 固化）。

锁定：
- 数据层 build_situation_page：北京时区换算（含跨午夜）、CS2 小局封顶 3、地图名取自
  虎扑评分树 game.name、state（played/live/upcoming）回填、live_matches 过滤
  （未结算 + 双队）、标记剥离。
- 导航 add_site_nav：「比赛局势」入口在今日情报与历史情报库之间；kind/active/breadcrumb
  正确（面包屑无 title 后缀，避免 title_of 把 match_situation 误解析）。
- 发布 vps_publish：situation_live.json 属易变文件（镜像节流、nginx 仍每分钟最新）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import add_site_nav as N
import build_situation_page as B
import vps_publish as P


# ---------- 北京时区换算 ----------

def test_bj_time_utc_to_beijing():
    assert B._bj_time("2026-10-25T13:00:00Z") == "10-25 21:00"
    # 跨午夜：UTC 23:00 -> 北京次日 07:00（AGENTS 时间基准 25 的跨午夜场次）
    assert B._bj_time("2026-10-30T23:00:00Z") == "10-31 07:00"
    # 无时区后缀按 UTC 处理
    assert B._bj_time("2026-10-25T13:00:00") == "10-25 21:00"
    assert B._bj_time("") == ""


def test_strip_markers():
    html = (
        "<!-- SITUATION:WIN:BEGIN -->A<!-- SITUATION:WIN:END -->"
        "<!-- SITUATION:RATINGS:BEGIN -->B<!-- SITUATION:RATINGS:END -->"
    )
    out = B._strip_markers(html)
    assert "SITUATION" not in out
    assert out == "AB"


# ---------- 导航 ----------

def test_nav_situation_is_grouped_under_today():
    html = N.nav_html("../", "today")
    assert "今日情报" in html
    assert "比赛局势" in html
    assert 'href="today.html"' in html
    assert 'href="match_situation.html"' in html


def test_nav_root_pre_variant():
    assert 'href="intel/match_situation.html"' in N.nav_html("", "today")


def test_kind_and_active():
    assert N.kind_of("match_situation.html") == "situation"
    assert N.active_of("situation") == "situation"


def test_breadcrumb_situation_no_title():
    bc = N.breadcrumb_html("../", "situation", "", "match_situation.html")
    assert "比赛局势" in bc
    assert 'href="today.html"' in bc


# ---------- 发布易变文件 ----------

def test_volatile_situation_json():
    assert P.volatile_path("intel/situation_live.json") is True
    assert P.volatile_path("situation_live.json") is True
    assert P.volatile_path("intel/today.html") is False


# ---------- 数据层 build() ----------

def test_live_matches_filters(tmp_path, monkeypatch):
    mf = tmp_path / "matches_today.json"
    mf.write_text(
        json.dumps(
            {
                "matches": [
                    {"id": "a", "teams": ["X", "Y"], "closed": False},
                    {"id": "b", "teams": ["X", "Y"], "closed": True},
                    {"id": "c", "teams": ["X"], "closed": False},  # 单队，排除
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(B.vp, "MATCHES", mf)
    assert [m["id"] for m in B.live_matches()] == ["a"]


def test_build_shape_cs2(monkeypatch):
    fake_match = {
        "id": "cs2-hupu-123",
        "teams": ["G2", "Aurora"],
        "start_time": "2026-10-25T13:00:00Z",
        "league": "CS2",
    }
    map_names = {1: "炼狱小镇", 2: "死城之谜"}

    def fake_ratings(mid, gi):
        if gi in (1, 2):
            return {
                "players": [{"name": "woxic", "score": 9.3}],
                "game": {"num": gi, "name": map_names[gi]},
            }
        return None

    monkeypatch.setattr(B, "live_matches", lambda: [fake_match])
    monkeypatch.setattr(B, "_all_danmu_files", lambda: [])
    monkeypatch.setattr(B.vp, "_match_game", lambda m: "cs2")
    monkeypatch.setattr(B.vp, "format_of", lambda m: 3)
    monkeypatch.setattr(B.vp, "league_files", lambda m, files: [])
    monkeypatch.setattr(B.vp, "fetch_ratings", fake_ratings)
    monkeypatch.setattr(B.vp, "fetch_lineup", lambda mid: None)
    monkeypatch.setattr(B.vp, "game_end_iso", lambda mid, gi: "2026-10-25T13:40:00Z")
    monkeypatch.setattr(
        B.vp, "game_win_signal",
        lambda mid, gi, teams, files, game=None, lineup=None, end_iso="": None,
    )
    monkeypatch.setattr(B, "_win_html", lambda ws, ratings, teams: "<win>")
    monkeypatch.setattr(
        B, "_ratings_html", lambda r, teams: "R" if (r and r.get("players")) else ""
    )

    data = B.build()
    assert len(data["matches"]) == 1
    m = data["matches"][0]
    assert m["max_games"] == 3  # CS2 封顶 G1-G3
    assert m["live_gi"] == 2
    assert m["start_bj"] == "10-25 21:00"
    assert [g["map_name"] for g in m["games"]] == ["炼狱小镇", "死城之谜", ""]
    assert [g["state"] for g in m["games"]] == ["played", "live", "upcoming"]
    # 胜率按小局：每个 game 各带一块 win_html（不再有 match 级 win_html）
    assert [g["win_html"] for g in m["games"]] == ["<win>", "<win>", "<win>"]
    assert "win_html" not in m
    assert [g["ratings_html"] for g in m["games"]] == ["R", "R", ""]


def test_build_skips_unsupported_game(monkeypatch):
    # dota2/valorant 首版不做，直接跳过
    fake_match = {"id": "dota2-hupu-9", "teams": ["A", "B"], "start_time": "2026-10-25T13:00:00Z"}
    monkeypatch.setattr(B, "live_matches", lambda: [fake_match])
    monkeypatch.setattr(B, "_all_danmu_files", lambda: [])
    monkeypatch.setattr(B.vp, "_match_game", lambda m: "dota2")
    assert B.build()["matches"] == []


# ---------- 胜率三档规则（2026-11-01 用户定稿） ----------

def _ratings_home_away():
    return {
        "home": {"name": "G2", "team_id": 1},
        "away": {"name": "Aurora", "team_id": 2},
        "players": [
            {"name": "p1", "team_id": 1, "score": 9.0},
            {"name": "p2", "team_id": 1, "score": 8.0},
            {"name": "p3", "team_id": 2, "score": 7.0},
        ],
    }


def test_team_score_avgs_maps_home_away():
    # 2026-11-22 改：均分（总和/选手数）——G2 两人 (9.0+8.0)/2=8.5，Aurora 一人 7.0/1=7.0
    avgs = B.render_node_page._team_score_avgs(_ratings_home_away(), ["G2", "Aurora"])
    assert avgs == (8.5, 7.0)


def test_team_score_avgs_no_team_id_returns_none():
    # CS2 无 team_id，无法按队归属 -> None（回退 50:50）
    ratings = {"players": [{"name": "woxic", "score": 9.3}]}
    assert B.render_node_page._team_score_avgs(ratings, ["A", "B"]) is None
    assert B.render_node_page._team_score_avgs(None, ["A", "B"]) is None


def test_team_score_avgs_one_team_empty_returns_none():
    # 某队 0 名归属选手 -> None（回退 50/50，宁漏不误配）
    ratings = {
        "home": {"name": "G2", "team_id": 1},
        "away": {"name": "Aurora", "team_id": 2},
        "players": [
            {"name": "p1", "team_id": 1, "score": 9.0},
            {"name": "p2", "team_id": 1, "score": 8.0},
            # Aurora 无归属选手
        ],
    }
    assert B.render_node_page._team_score_avgs(ratings, ["G2", "Aurora"]) is None


def test_team_score_avgs_excludes_unassigned():
    # 空 team_id 的选手不得计入任何一队（宁可漏计不误配；曾把未归属塞进主队列/主队分）
    ratings = {
        "home": {"name": "G2", "team_id": 1},
        "away": {"name": "Aurora", "team_id": 2},
        "players": [
            {"name": "p1", "team_id": 1, "score": 9.0},
            {"name": "p2", "team_id": 2, "score": 7.0},
            {"name": "pX", "team_id": "", "score": 99.0},  # 未归属，不得计入任何一队
        ],
    }
    avgs = B.render_node_page._team_score_avgs(ratings, ["G2", "Aurora"])
    assert avgs == (9.0, 7.0)


def test_rating_cols_unassigned_goes_to_separate_group():
    # 部分队识别、部分空 team_id：空 team_id 必须单独标「未归属」，不混入主队列
    ratings = {
        "home": {"name": "The MongolZ", "team_id": 1},
        "away": {"name": "HEROIC", "team_id": 2},
        "players": [
            {"name": "bLitz", "team_id": 1, "score": 6.0},
            {"name": "nilo", "team_id": 2, "score": 10.0},
            {"name": "MartinezSa", "team_id": "", "score": 10.0},
        ],
    }
    html = B.render_node_page._rating_cols(ratings, ["The MongolZ", "HEROIC"])
    assert "未归属" in html
    # 未归属组排在两队列之后，MartinezSa 出现在「未归属」标签之后
    assert html.index("MartinezSa") > html.index("未归属")


def test_rating_cols_no_unassigned_group_when_all_attributed():
    ratings = {
        "home": {"name": "G2", "team_id": 1},
        "away": {"name": "Aurora", "team_id": 2},
        "players": [
            {"name": "p1", "team_id": 1, "score": 9.0},
            {"name": "p2", "team_id": 2, "score": 7.0},
        ],
    }
    html = B.render_node_page._rating_cols(ratings, ["G2", "Aurora"])
    assert "未归属" not in html


def test_rating_win_block_70_30():
    out = B.render_node_page._rating_win_block(["G2", "Aurora"], 17.0, 7.0)
    assert "70" in out and "30" in out
    assert "暂无显式胜负弹幕样本" in out
    # 外包 WIN 标记（与 situation_win_block 同构），供 refresh_situation 就地替换
    assert B.render_node_page._WIN_BEGIN in out and B.render_node_page._WIN_END in out


# ---------- 三档胜率块（render_node_page.situation_win_block_tiered，两页共用） ----------

def test_tiered_case3_danmu():
    ws = _ws(total=10, pct_a=60, pct_b=40)
    out = B.render_node_page.situation_win_block_tiered(ws, None, ["A", "B"])
    assert "60" in out and "40" in out  # 弹幕实际比例
    assert "暂无显式胜负弹幕样本" not in out


def test_tiered_case2_ratings():
    out = B.render_node_page.situation_win_block_tiered(_ws(), _ratings_home_away(), ["G2", "Aurora"])
    assert "70" in out and "30" in out
    assert "暂无显式胜负弹幕样本" in out


def test_tiered_case1_fifty():
    out = B.render_node_page.situation_win_block_tiered(_ws(), None, ["A", "B"])
    assert "暂无显式胜负弹幕样本" in out
    assert "50" in out


def _ws(total=0, pct_a=50, pct_b=50):
    return {"total": total, "pct_a": pct_a, "pct_b": pct_b, "sample_status": "insufficient"}


# ---------- 近 5 分钟不足改走评分均分（2026-11-22 用户规则） ----------

def _ratings_counted(counts: list[int]) -> dict:
    """G2 两人 8.0 分、Aurora 一人 9.0 分，评分人数可配。"""
    return {
        "home": {"name": "G2", "team_id": 1},
        "away": {"name": "Aurora", "team_id": 2},
        "players": [
            {"name": "p1", "team_id": 1, "score": 8.0, "count": counts[0]},
            {"name": "p2", "team_id": 1, "score": 8.0, "count": counts[1]},
            {"name": "p3", "team_id": 2, "score": 9.0, "count": counts[2]},
        ],
    }


def test_ratings_avg_count():
    assert B.render_node_page._ratings_avg_count(_ratings_counted([30, 30, 40])) == (30 + 30 + 40) / 3
    assert B.render_node_page._ratings_avg_count(None) is None
    # 未归属选手的评分人数不参与平均
    ratings = _ratings_counted([30, 30, 40])
    ratings["players"].append({"name": "pX", "team_id": "", "score": 9.0, "count": 10000})
    assert B.render_node_page._ratings_avg_count(ratings) == (30 + 30 + 40) / 3


def test_tiered_cumulative_insufficient_uses_rating_when_count_ok():
    # 近 5 分钟不足（basis=cumulative）+ 平均评分人数 >= 20 -> 改走评分均分 70/30
    ws = {"total": 8, "pct_a": 50, "pct_b": 50, "basis": "cumulative", "sample_status": "ready"}
    out = B.render_node_page.situation_win_block_tiered(ws, _ratings_counted([30, 30, 40]), ["G2", "Aurora"])
    assert "70" in out and "30" in out
    assert "近 5 分钟胜负弹幕样本不足" in out  # 新 reason，非「暂无显式胜负弹幕样本」


def test_tiered_cumulative_falls_back_when_count_low():
    # 平均评分人数 < 20 -> 评分不可靠，回退累积弹幕比例（不走 70/30）
    ws = {"total": 8, "pct_a": 60, "pct_b": 40, "basis": "cumulative", "sample_status": "ready"}
    out = B.render_node_page.situation_win_block_tiered(ws, _ratings_counted([5, 5, 5]), ["G2", "Aurora"])
    assert "60" in out and "40" in out
    assert "近 5 分钟胜负弹幕样本不足" not in out


def test_tiered_recent_uses_danmaku_not_rating():
    # basis=recent（近 5 分钟样本充足）-> 仍用弹幕比例，不改成评分（即使评分人数够）
    ws = {"total": 10, "pct_a": 60, "pct_b": 40, "basis": "recent", "sample_status": "ready"}
    out = B.render_node_page.situation_win_block_tiered(ws, _ratings_counted([30, 30, 40]), ["G2", "Aurora"])
    assert "60" in out and "40" in out
    assert "近 5 分钟胜负弹幕样本不足" not in out


def test_win_html_case3_danmu(monkeypatch):
    # 情况三：当前进行局有胜负弹幕 -> 现有规则
    monkeypatch.setattr(B.render_node_page, "situation_win_block", lambda ws, teams: "REALWIN")
    assert B._win_html(_ws(total=10, pct_a=60, pct_b=40), None, ["A", "B"]) == "REALWIN"


def test_win_html_case2_ratings():
    # 情况二：无胜负弹幕但有评分 -> 70/30
    out = B._win_html(_ws(), _ratings_home_away(), ["G2", "Aurora"])
    assert "70" in out and "30" in out
    assert "暂无显式胜负弹幕样本" in out


def test_win_html_case1_fifty(monkeypatch):
    # 情况一：无胜负弹幕也无评分 -> 50:50
    monkeypatch.setattr(B.render_node_page, "situation_win_block", lambda ws, teams: "FIFTY")
    assert B._win_html(_ws(), None, ["A", "B"]) == "FIFTY"


def test_win_html_none_ws_falls_back_to_fifty():
    # 非进行局（build 传 ws=None）-> 空信号 -> 回退评分/50:50，绝不走整场弹幕
    out = B._win_html(None, None, ["A", "B"])
    assert "暂无显式胜负弹幕样本" in out


def test_build_calls_game_win_signal_for_played_and_live(monkeypatch):
    # build() 对已结束局（封闭切片 end_iso）+ live 局（切到 now）都调 game_win_signal，
    # 待开打局不碰弹幕（2026-11-02 已结束局对齐情报页冻结口径，不再清弹幕只走评分）
    fake_match = {"id": "lol-hupu-1", "teams": ["G2", "Aurora"], "start_time": "2026-10-25T13:00:00Z"}
    calls = []

    def fake_ratings(mid, gi):
        return {"players": [{"name": "p", "team_id": 1, "score": 9.0}]} if gi in (1, 2) else None

    monkeypatch.setattr(B, "live_matches", lambda: [fake_match])
    monkeypatch.setattr(B, "_all_danmu_files", lambda: [])
    monkeypatch.setattr(B.vp, "_match_game", lambda m: "lol")
    monkeypatch.setattr(B.vp, "format_of", lambda m: 3)
    monkeypatch.setattr(B.vp, "league_files", lambda m, files: [])
    monkeypatch.setattr(B.vp, "fetch_ratings", fake_ratings)
    monkeypatch.setattr(B.vp, "fetch_lineup", lambda mid: None)
    monkeypatch.setattr(B.vp, "game_end_iso", lambda mid, gi: "2026-10-25T13:40:00Z")
    monkeypatch.setattr(B, "_ratings_html", lambda r, teams: "")

    def fake_game_win_signal(mid, gi, teams, files, game=None, lineup=None, end_iso=""):
        calls.append((gi, end_iso))
        return _ws()

    monkeypatch.setattr(B.vp, "game_win_signal", fake_game_win_signal)
    monkeypatch.setattr(B, "_win_html", lambda ws, ratings, teams: "W")
    B.build()
    # G1 played(封闭切片 end_iso 非空) / G2 live(切到 now) / G3 upcoming(不调)
    assert calls == [(1, "2026-10-25T13:40:00Z"), (2, "")]


def test_build_skips_finished_game_when_no_end_bound(monkeypatch):
    # 已结束局取不到结束上界（game_end_iso=None）时不碰弹幕，回退 ws=None -> 50:50，
    # 避免 open 切片把后续局弹幕混进来（2026-11-02 防串局）
    fake_match = {"id": "lol-hupu-1", "teams": ["G2", "Aurora"], "start_time": "2026-10-25T13:00:00Z"}
    calls = []

    def fake_ratings(mid, gi):
        return {"players": [{"name": "p", "team_id": 1, "score": 9.0}]} if gi in (1, 2) else None

    monkeypatch.setattr(B, "live_matches", lambda: [fake_match])
    monkeypatch.setattr(B, "_all_danmu_files", lambda: [])
    monkeypatch.setattr(B.vp, "_match_game", lambda m: "lol")
    monkeypatch.setattr(B.vp, "format_of", lambda m: 3)
    monkeypatch.setattr(B.vp, "league_files", lambda m, files: [])
    monkeypatch.setattr(B.vp, "fetch_ratings", fake_ratings)
    monkeypatch.setattr(B.vp, "fetch_lineup", lambda mid: None)
    monkeypatch.setattr(B.vp, "game_end_iso", lambda mid, gi: None)
    monkeypatch.setattr(B, "_ratings_html", lambda r, teams: "")

    def fake_game_win_signal(mid, gi, teams, files, game=None, lineup=None, end_iso=""):
        calls.append(gi)
        return _ws()

    monkeypatch.setattr(B.vp, "game_win_signal", fake_game_win_signal)
    monkeypatch.setattr(B, "_win_html", lambda ws, ratings, teams: "W")
    B.build()
    # G1 played 但无结束上界 -> 不调 game_win_signal；G2 live -> 调；G3 upcoming -> 不调
    assert calls == [2]
