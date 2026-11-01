"""fetch_hupu_player_ratings 节点类型与小局号映射回归（2026-11-01 固化）。

教训：评分树节点类型硬编码 lol_bo/lol_item，导致 CS2（common_sports_second/
common_sports_third）整场选手评分采不到（页面显示"暂未获取到虎扑选手评分"）。
锁定：两类节点类型都识别；CS2 小局号按地图顺序映射（节点名是地图名，无"第N局"可解析）。
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import fetch_hupu_player_ratings as F


def test_game_types_include_both_lol_and_cs2():
    assert "lol_bo" in F._GAME_TYPES
    assert "common_sports_second" in F._GAME_TYPES
    assert "lol_item" in F._PLAYER_TYPES
    assert "common_sports_third" in F._PLAYER_TYPES


def test_game_num_lol_parses_di_n():
    assert F._game_num_of({"name": "第2局", "bizType": "lol_bo"}, 0) == 2


def test_game_num_lol_parses_bonum():
    assert F._game_num_of({"name": "x", "bizType": "lol_bo", "infoJson": {"boNum": ["3"]}}, 0) == 3


def test_game_num_cs2_uses_map_order():
    # CS2 节点名是地图名（如"炙热沙城Ⅱ"），无"第N局"；按顺序 index+1（第 1 张图=第 1 局）
    node = {"name": "炙热沙城Ⅱ", "bizType": "common_sports_second"}
    assert F._game_num_of(node, 0) == 1
    assert F._game_num_of(node, 1) == 2


# ---------- _is_real_player：非选手过滤（2026-11-01 固化） ----------

def test_real_player_names_pass():
    # 拉丁 ID 与中文选手名（无冒号、无角色前缀）都是真实选手
    for name in ("Canna", "Jojopyun", "kyeahoo", "喻文波", "TheShy", "Faker"):
        assert F._is_real_player(name) is True, name


def test_costreamer_commentator_filtered():
    # 二路流主播 / 官方解说（"角色：昵称"全角冒号格式，teamId 为空）不得当作选手
    for name in ("二路：米勒", "二路：楚钧艾克", "二路：Ning", "解说：MacT", "解说：PYL"):
        assert F._is_real_player(name) is False, name


def test_halfwidth_colon_role_filtered():
    # 半角冒号的"角色:昵称"同样过滤
    assert F._is_real_player("解说:MacT") is False


def test_bare_role_prefix_filtered():
    # 裸角色前缀（无冒号）也要过滤
    for name in ("教练", "替补", "二路", "解说"):
        assert F._is_real_player(name) is False, name


def test_multi_hero_bundle_filtered():
    # 多英雄捆绑（如"卡西奥佩娅/魔腾/李青"）不是单名选手
    assert F._is_real_player("卡西奥佩娅/魔腾/李青") is False


def test_empty_and_blank_filtered():
    assert F._is_real_player("") is False
    assert F._is_real_player("   ") is False
    assert F._is_real_player(None) is False
