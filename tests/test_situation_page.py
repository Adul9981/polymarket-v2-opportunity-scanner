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

def test_nav_situation_between_today_and_history():
    # intel/ 子页变体（pre 非空 -> in_sub）：href 不带前缀
    html = N.nav_html("../", "today")
    assert "比赛局势" in html
    assert html.index("今日情报") < html.index("比赛局势") < html.index("历史情报库")
    # 站内链接（非外链），与 today/history 同目录
    assert 'href="match_situation.html"' in html


def test_nav_root_pre_variant():
    # 根目录页面（in_sub=False）指向 intel/match_situation.html
    assert 'href="intel/match_situation.html"' in N.nav_html("", "today")


def test_kind_and_active():
    assert N.kind_of("match_situation.html") == "situation"
    assert N.active_of("situation") == "situation"


def test_breadcrumb_situation_no_title():
    bc = N.breadcrumb_html("../", "situation", "", "match_situation.html", "")
    assert "比赛局势" in bc
    # 面包屑不得带 title 后缀（title_of 会把 match_situation 误解析成 "situation"）
    assert "› <b" not in bc


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
    monkeypatch.setattr(B, "_match_win_signal", lambda m, teams, files, game: None)
    monkeypatch.setattr(B, "_win_html", lambda ws, ratings, teams, use_danmu: "<win>")
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


def test_team_score_sums_maps_home_away():
    sums = B.render_node_page._team_score_sums(_ratings_home_away(), ["G2", "Aurora"])
    assert sums == (17.0, 7.0)


def test_team_score_sums_no_team_id_returns_none():
    # CS2 无 team_id，无法按队归属 -> None（回退 50:50）
    ratings = {"players": [{"name": "woxic", "score": 9.3}]}
    assert B.render_node_page._team_score_sums(ratings, ["A", "B"]) is None
    assert B.render_node_page._team_score_sums(None, ["A", "B"]) is None


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


def test_win_html_case3_danmu(monkeypatch):
    # 情况三：当前进行局有胜负弹幕 -> 现有规则
    monkeypatch.setattr(B.render_node_page, "situation_win_block", lambda ws, teams: "REALWIN")
    assert B._win_html(_ws(total=10, pct_a=60, pct_b=40), None, ["A", "B"], True) == "REALWIN"


def test_win_html_case2_ratings():
    # 情况二：无胜负弹幕但有评分 -> 70/30
    out = B._win_html(_ws(), _ratings_home_away(), ["G2", "Aurora"], False)
    assert "70" in out and "30" in out
    assert "暂无显式胜负弹幕样本" in out


def test_win_html_case1_fifty(monkeypatch):
    # 情况一：无胜负弹幕也无评分 -> 50:50
    monkeypatch.setattr(B.render_node_page, "situation_win_block", lambda ws, teams: "FIFTY")
    assert B._win_html(_ws(), None, ["A", "B"], False) == "FIFTY"


def test_win_html_danmu_only_applies_to_live_game():
    # 非进行局 use_danmu=False：即使 ws.total>0 也不走弹幕（回退评分/50:50）
    out = B._win_html(_ws(total=10, pct_a=60, pct_b=40), None, ["A", "B"], False)
    # 无评分 -> 50:50（situation_win_block 输出，含"暂无显式胜负弹幕样本"）
    assert "暂无显式胜负弹幕样本" in out


def test_build_win_html_per_game_use_danmu_flag(monkeypatch):
    # build() 只对最高已开打局传 use_danmu=True，其余局 False
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
    monkeypatch.setattr(B, "_match_win_signal", lambda m, teams, files, game: _ws())
    monkeypatch.setattr(B, "_ratings_html", lambda r, teams: "")

    def fake_win(ws, ratings, teams, use_danmu):
        calls.append(use_danmu)
        return "W"

    monkeypatch.setattr(B, "_win_html", fake_win)
    B.build()
    # G1 played / G2 live / G3 upcoming -> 只有 G2（live）use_danmu=True
    assert calls == [False, True, False]
