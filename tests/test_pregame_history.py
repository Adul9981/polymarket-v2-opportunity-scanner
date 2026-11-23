"""赛前页历史数据 + 渲染回归（2026-11-22 固化）。

锁定：
  1. 联赛名精确匹配 + alias，粗粒度（"LoL"）不再误配到 LoL Italian Tournament（走反查兜底）；
  2. H2H 表渲染：行=时间、列=两队、单元格=胜负、表下各自交手胜率总结；
  3. 近况表：LoL 逐场胜负 + 胜率；CS2 锦标赛级（名次+决赛比分）显式标口径；
  4. 赛前页只保留两栏，不再出现 4 段标题（BP 锚点/比赛局势/方向性情报板/灰信号汇总）。
"""

from __future__ import annotations

import fetch_team_history as fth
import render_pregame as rp


# --------------------------------------------------------------------------- 联赛定位

def test_norm():
    assert fth.norm("DNS.C") == "dnsc"
    assert fth.norm("Team Spirit") == "teamspirit"


def test_clean_cell_unescape_nbsp():
    # Liquipedia place 字段常带 &#160;（non-breaking space），未反转义会在页面显示成字面实体
    assert fth._clean_cell("7th&#160;-&#160;8th") == "7th - 8th"
    assert fth._clean_cell("5th&#160;-&#160;8th") == "5th - 8th"
    assert fth._clean_cell("3 : 1") == "3 : 1"


def test_canon_abbr_maps_full_and_alias_to_abbr():
    # pipeline 传 matches.json 全名，须归一化到 Riot code / 情报库 abbr，否则 LoL 匹配失败
    assert fth.canon_abbr("Bilibili Gaming") == "BLG"
    assert fth.canon_abbr("FUT Esports") == "FUT"
    assert fth.canon_abbr("T1") == "T1"
    assert fth.canon_abbr("MOUZ") == "MOUZ"


def test_canon_abbr_unknown_returns_self():
    assert fth.canon_abbr("No Such Team XYZ") == "No Such Team XYZ"


def test_at_or_after_full_ts():
    # 完整时间戳：本场及之后排除，之前保留
    assert fth._at_or_after("2026-11-08T12:00:00Z", "2026-11-08T12:00:00Z") is True
    assert fth._at_or_after("2026-11-08T13:00:00Z", "2026-11-08T12:00:00Z") is True
    assert fth._at_or_after("2026-11-07T12:00:00Z", "2026-11-08T12:00:00Z") is False


def test_at_or_after_date_only():
    # 仅日期：当天及之后排除，前一天保留
    assert fth._at_or_after("2026-11-08T01:00:00Z", "2026-11-08") is True
    assert fth._at_or_after("2026-11-07T23:00:00Z", "2026-11-08") is False
    # 空 before 不排除
    assert fth._at_or_after("2026-11-08T12:00:00Z", "") is False


def test_lol_league_id_exact():
    ids = {"lck": "111", "lckchallengers": "222", "lpl": "333"}
    assert fth.lol_league_id("LCK", ids) == "111"
    assert fth.lol_league_id("lpl", ids) == "333"


def test_lol_league_id_alias():
    ids = {"lckchallengers": "222"}
    assert fth.lol_league_id("LCK CL", ids) == "222"


def test_lol_league_id_coarse_returns_none():
    # 2026-11-22 教训：前缀匹配曾把 "LoL" 误配到 "LoL Italian Tournament"
    ids = {"lck": "111", "lolitaliantournament": "999"}
    assert fth.lol_league_id("LoL", ids) is None


# --------------------------------------------------------------------------- H2H 表

def test_h2h_side_winner_attribution():
    assert rp._h2h_side({"winner": "T1"}, ["T1", "GEN"]) == (True, False)
    assert rp._h2h_side({"winner": "GEN"}, ["T1", "GEN"]) == (False, True)


def test_h2h_block_renders_table_and_summary():
    h2h = [
        {"date": "2026-08-16", "winner": "GEN", "score": "0:2"},
        {"date": "2026-07-31", "winner": "T1", "score": "2:0"},
    ]
    html = rp._h2h_block(h2h, ["T1", "GEN"], "lol")
    assert "时间" in html and "T1" in html and "GEN" in html
    assert "胜" in html and "负" in html
    assert "交手" in html and "50%" in html  # 各 1 胜 1 负


def test_h2h_block_empty():
    html = rp._h2h_block([], ["A", "B"], "lol")
    assert "暂无" in html


# --------------------------------------------------------------------------- 近况表

def test_recent_table_lol_win_loss_and_rate():
    rows = [
        {"date": "2026-09-12", "opponent": "HLE", "result": "loss"},
        {"date": "2026-09-06", "opponent": "DK", "result": "win"},
    ]
    html = rp._recent_table("T1", rows, "lol")
    assert "T1" in html and "HLE" in html and "DK" in html
    assert "50%" in html  # 1 胜 1 负


def test_recent_table_lol_empty():
    assert "样本不足" in rp._recent_table("T1", [], "lol")


def test_recent_table_cs2_tournament_level():
    rows = [{"date": "2026-09-06", "place": "1st", "tournament": "BLAST Open", "result": "3 : 1", "opponent": "MOUZ"}]
    html = rp._recent_table("Spirit", rows, "cs2")
    assert "BLAST Open" in html and "MOUZ" in html
    assert "锦标赛级" in html  # 口径显式标注


# --------------------------------------------------------------------------- 整页结构

def test_render_pregame_html_two_sections_no_4seg():
    hist = {
        "game": "lol",
        "h2h": [{"date": "2026-08-16", "winner": "GEN", "score": "0:2"}],
        "recent": {"T1": [], "GEN": []},
        "gaps": [],
    }
    html = rp.render_pregame_html(["T1", "GEN"], "2026-11-22", "LCK", "slug", hist)
    assert "队伍交手情况" in html
    assert "队伍比赛近况" in html
    for seg in ("方向性情报板", "灰信号汇总", "BP 锚点", "比赛局势"):
        assert seg not in html


def test_render_pregame_html_shows_gaps():
    hist = {"game": "lol", "h2h": [], "recent": {"A": [], "B": []}, "gaps": ["数据缺口 X"]}
    html = rp.render_pregame_html(["A", "B"], "2026-11-22", "LCK", "slug", hist)
    assert "数据缺口 X" in html
