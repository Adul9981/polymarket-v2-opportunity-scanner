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


def test_game_num_cs2_uses_bonum_not_order():
    # CS2 节点带 infoJson.boNum（权威小局号）；hupu 返回倒序（最新地图在前），
    # 必须读 boNum 而非 index+1，否则 G1/G2 地图反（2026-11-02 教训）
    node = {"name": "炼狱小镇", "bizType": "common_sports_second", "infoJson": {"boNum": ["2"]}}
    assert F._game_num_of(node, 0) == 2  # index=0 但 boNum=2（倒序场景）


def test_game_num_cs2_falls_back_to_map_order():
    # boNum 缺失才回退地图顺序 index+1（第 1 张图 = 第 1 局）
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


def test_role_suffix_filtered_cs2():
    # CS2 通用评分把"解说"放在昵称后（后缀，如"DANK1NG解说"），此前只判前缀导致漏过滤
    #（2026-11-02 NaVi-Falcons G2 混入 4 个解说 + 1 个队服节点）
    for name in ("DANK1NG解说", "玩机器解说", "259解说", "马西西解说"):
        assert F._is_real_player(name) is False, name


def test_merch_nodes_filtered_cs2():
    # 周边商品节点（队服/队徽/周边/应援）不是选手，一律过滤
    for name in ("Falcons中国队服", "NaVi队徽", "周边", "应援物"):
        assert F._is_real_player(name) is False, name


def test_multi_hero_bundle_filtered():
    # 多英雄捆绑（如"卡西奥佩娅/魔腾/李青"）不是单名选手
    assert F._is_real_player("卡西奥佩娅/魔腾/李青") is False


def test_empty_and_blank_filtered():
    assert F._is_real_player("") is False
    assert F._is_real_player("   ") is False
    assert F._is_real_player(None) is False


# ---------- CS2 阵容归属回填（2026-11-02 固化） ----------

def test_canon_team_normalizes_cs2_team_names():
    # 虎扑/平台对同一队有不同写法，必须归一到一个规范 id 才能与阵容表 key 对齐
    for name, want in (
        ("FURIA", "furia"),
        ("DENDELE", "dendele"),
        ("NaVi", "navi"),
        ("Liquid", "tl"),
        ("The MongolZ", "mglz"),
        ("Vitality", "vit"),
        ("Aurora", "aurora"),
        ("BETBOOM", "betboom"),
        ("TYLOO", "tyloo"),
        ("PARIVISION", "prv"),
        ("B8", "b8"),
        ("HEROIC", "heroic"),
        ("Heroic", "heroic"),
        ("TheMongolz", "mglz"),  # 无空格变体（虎扑常用）必须也能归一
    ):
        assert F._canon_team(name) == want, name


def test_load_roster_maps_player_names_to_team_ids():
    roster = F._load_roster()
    # 阵容表由 tools/fetch_cs2_rosters.py 生成；选手名按小写匹配
    assert roster.get("zywoo") == "vit"
    assert roster.get("donk") == "spirit"
    assert roster.get("yuurih") == "furia"
    assert roster.get("rdnzao") == "dendele"
    assert roster.get("jame") == "prv"
    assert roster.get("fl1t") == "prv"
    # 教练不得混入（sidde 是 FURIA 教练，已被 role 过滤）
    assert "sidde" not in roster


def test_attribute_cs2_players_splits_into_two_teams():
    home = {"name": "FURIA", "team_id": "T-FURIA"}
    away = {"name": "DENDELE", "team_id": "T-DENDELE"}
    players = [
        {"name": "molodoy", "team_id": "", "team": ""},
        {"name": "rdnzao", "team_id": "", "team": ""},
        {"name": "yuurih", "team_id": "", "team": ""},
        {"name": "maxxkor", "team_id": "", "team": ""},
    ]
    F._attribute_cs2_players(players, home, away)
    by_name = {p["name"]: p for p in players}
    assert by_name["molodoy"]["team_id"] == "T-FURIA"
    assert by_name["molodoy"]["team"] == "FURIA"
    assert by_name["rdnzao"]["team_id"] == "T-DENDELE"
    assert by_name["rdnzao"]["team"] == "DENDELE"
    assert by_name["yuurih"]["team"] == "FURIA"
    assert by_name["maxxkor"]["team"] == "DENDELE"


def test_attribute_cs2_unknown_player_stays_unattributed():
    # 认不清的选手（不在阵容表 / 未登记队）保持空，展示层标"未归属"，宁可漏计不误配
    home = {"name": "FURIA", "team_id": "T-FURIA"}
    away = {"name": "DENDELE", "team_id": "T-DENDELE"}
    players = [
        {"name": "NobodyInRoster", "team_id": "", "team": ""},
        {"name": "molodoy", "team_id": "", "team": ""},
    ]
    F._attribute_cs2_players(players, home, away)
    by_name = {p["name"]: p for p in players}
    assert by_name["NobodyInRoster"]["team_id"] == ""
    assert by_name["NobodyInRoster"]["team"] == ""
    assert by_name["molodoy"]["team"] == "FURIA"


def test_attribute_cs2_skips_players_with_existing_team():
    # 已有 team_id 的选手（LoL 或已回填）不被覆盖
    home = {"name": "FURIA", "team_id": "T-FURIA"}
    away = {"name": "DENDELE", "team_id": "T-DENDELE"}
    players = [{"name": "yuurih", "team_id": "OTHER", "team": "OtherTeam"}]
    F._attribute_cs2_players(players, home, away)
    assert players[0]["team_id"] == "OTHER"


# ---------- CS2 选手昵称别名（2026-11-03 固化，虎扑昵称 vs Liquipedia 阵容名不一致） ----------

def test_canon_player_name_applies_alias():
    # 虎扑评分树昵称与 Liquipedia 阵容名不一致时，别名映射回规范名
    assert F._canon_player_name("MartinezSa") == "martinez"
    assert F._canon_player_name("Techno") == "techno4k"
    # 无别名时原样小写
    assert F._canon_player_name("nilo") == "nilo"
    assert F._canon_player_name("") == ""


def test_attribute_cs2_players_uses_alias_for_heroic_mongolz():
    # HEROIC 的 MartinezSa（虎扑）与 The MongolZ 的 Techno（虎扑）必须靠别名回填归属，
    # 否则空 team_id 会被展示层错塞进主队列（教训：2026-11-03 mglz-hero 页面）
    home = {"name": "The MongolZ", "team_id": "T-MGLZ"}
    away = {"name": "HEROIC", "team_id": "T-HEROIC"}
    players = [
        {"name": "MartinezSa", "team_id": "", "team": ""},
        {"name": "Techno", "team_id": "", "team": ""},
        {"name": "nilo", "team_id": "", "team": ""},
    ]
    F._attribute_cs2_players(players, home, away)
    by_name = {p["name"]: p for p in players}
    assert by_name["MartinezSa"]["team_id"] == "T-HEROIC"
    assert by_name["MartinezSa"]["team"] == "HEROIC"
    assert by_name["Techno"]["team_id"] == "T-MGLZ"
    assert by_name["Techno"]["team"] == "The MongolZ"
    assert by_name["nilo"]["team_id"] == "T-HEROIC"


# ---------- 系列比分 fetch_match_score（2026-11-02 固化） ----------

def test_fetch_match_score_reads_home_away(monkeypatch):
    # match 层 infoJson 带 homeTeamScore/awayTeamScore（系列总分），读出 home/away
    monkeypatch.setattr(F, "_self_node", lambda *a, **k: {
        "homeTeamName": ["FURIA"], "awayTeamName": ["DENDELE"],
        "homeTeamScore": ["2"], "awayTeamScore": ["0"],
    })
    assert F.fetch_match_score("36210", "common_sports_first") == {
        "home_name": "FURIA", "away_name": "DENDELE", "home": "2", "away": "0",
    }


def test_fetch_match_score_none_when_no_scores(monkeypatch):
    # 未开赛/无比分字段 -> None（前端不显示比分栏）
    monkeypatch.setattr(F, "_self_node", lambda *a, **k: {"homeTeamName": ["A"], "awayTeamName": ["B"]})
    assert F.fetch_match_score("x", "lol_match") is None
