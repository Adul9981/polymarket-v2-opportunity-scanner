"""【比赛局势】胜率/评分回归（2026-10-18 固化）。

锁定：
  1. 显式胜负弹幕计数归一化后两队相加恒为 100%；
  2. 样本不足（< 阈值）不硬算，pct=None + sample_status=insufficient；
  3. "某队输了/寄了"计给另一队（反向归属）；
  4. 俚语/玩梗（ok bro / gg）与无方向、双队同现的弹幕不计；
  5. 渲染层蓝=队1 / 红=队2，评分列按虎扑队名对齐。
"""

from __future__ import annotations

import danmu_intel
import render_node_page


def _rows(texts: list[str]) -> list[dict]:
    return [{"text": t} for t in texts]


# --------------------------------------------------------------------------- win_signal

def test_win_signal_sums_to_100():
    rows = _rows(["Alpha赢了"] * 6 + ["Beta拿下"] * 4)
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"])
    assert ws["sample_status"] == "ready"
    assert ws["pct_a"] + ws["pct_b"] == 100
    assert ws["pct_a"] == 60 and ws["pct_b"] == 40
    assert ws["total"] == 10


def test_win_signal_insufficient_threshold():
    rows = _rows(["Alpha赢了", "Beta拿下", "Alpha必胜"])
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"])
    assert ws["sample_status"] == "insufficient"
    assert ws["pct_a"] is None and ws["pct_b"] is None
    assert ws["total"] == 3


def test_lose_counts_opposite_team():
    rows = _rows(["Beta寄了", "Beta输了", "Beta被零封"])
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=3)
    assert ws["sample_status"] == "ready"
    # "Beta 寄了/输了" → 方向记给 Alpha
    assert ws["count_a"] == 3 and ws["count_b"] == 0
    assert ws["pct_a"] == 100 and ws["pct_b"] == 0


def test_slang_and_no_direction_not_counted():
    rows = _rows(["ok bro", "gg", "bro tax", "Alpha来了", "Alpha和Beta都赢了"])
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=0)
    assert ws["total"] == 0
    assert ws["count_a"] == 0 and ws["count_b"] == 0


def test_ambiguous_both_teams_skipped():
    rows = _rows(["Alpha和Beta都赢了"] * 5)
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=0)
    assert ws["total"] == 0


def test_win_signal_no_teams_returns_none():
    assert danmu_intel.win_signal(_rows(["Alpha赢了"]), []) is None
    assert danmu_intel.win_signal(_rows(["Alpha赢了"]), ["Alpha"]) is None


def test_champion_title_not_counted_as_win():
    # "DK冠军"是头衔不是胜负信号（教训 2026-10-18）
    ws = danmu_intel.win_signal(_rows(["DK冠军换个打野直接没了"]), ["DK", "DNS"], threshold=0)
    assert ws["total"] == 0


def test_taizou_is_lose_direction():
    # "把DK抬走" = DK 输，方向记给对手
    ws = danmu_intel.win_signal(_rows(["把DK抬走"] * 4), ["DK", "DNS"], threshold=4)
    assert ws["sample_status"] == "ready"
    assert ws["count_b"] == 4 and ws["count_a"] == 0
    assert ws["pct_b"] == 100


# --------------------------------------------------------------------------- 选手名 -> 队伍折算

def test_player_win_counts_to_team():
    # "Faker赢了"（T1 选手）记 T1；"Chovy拿下"（GEN 选手）记 GEN
    rows = _rows(["Faker赢了"] * 6 + ["Chovy拿下"] * 4)
    ws = danmu_intel.win_signal(rows, ["T1", "GEN"], game="lol")
    assert ws["sample_status"] == "ready"
    assert ws["count_a"] == 6 and ws["count_b"] == 4
    assert ws["pct_a"] == 60 and ws["pct_b"] == 40


def test_player_lose_counts_opponent():
    # "Chovy寄了"（GEN 选手输）→ 方向记给对手 T1
    ws = danmu_intel.win_signal(_rows(["Chovy寄了"] * 4), ["T1", "GEN"], threshold=4, game="lol")
    assert ws["sample_status"] == "ready"
    assert ws["count_a"] == 4 and ws["count_b"] == 0
    assert ws["pct_a"] == 100


def test_cross_game_player_not_attributed():
    # Dota2 场（Iron Wing vs Spirit）：CS2 的 donk（也归 Spirit）不得折算进 Dota2 Spirit
    ws = danmu_intel.win_signal(_rows(["donk赢了"] * 5), ["Iron Wing", "Spirit"], threshold=0, game="dota2")
    assert ws["total"] == 0
    # 但 Dota2 的 Yatoro 应折算进 Spirit（team_b）
    ws2 = danmu_intel.win_signal(_rows(["Yatoro赢了"] * 5), ["Iron Wing", "Spirit"], threshold=0, game="dota2")
    assert ws2["count_b"] == 5 and ws2["count_a"] == 0


def test_player_both_teams_skipped():
    # "Faker打赢Chovy"同时提两队选手 → 归属歧义，不计
    ws = danmu_intel.win_signal(_rows(["Faker打赢Chovy"] * 5), ["T1", "GEN"], threshold=0, game="lol")
    assert ws["total"] == 0


def test_player_of_unrelated_team_not_counted():
    # Zywoo（Vitality）不在 T1 vs GEN 对阵里 → 不计
    ws = danmu_intel.win_signal(_rows(["Zywoo赢了"] * 5), ["T1", "GEN"], threshold=0, game="lol")
    assert ws["total"] == 0


def test_team_and_player_not_double_counted():
    # "T1 Faker赢了"同时命中队名与选手名 → 只计一次
    ws = danmu_intel.win_signal(_rows(["T1 Faker赢了"] * 6), ["T1", "GEN"], threshold=6, game="lol")
    assert ws["sample_status"] == "ready"
    assert ws["count_a"] == 6 and ws["count_b"] == 0


# --------------------------------------------------------------------------- 动态首发阵容（虎扑）选手折算

def test_dynamic_lineup_new_player_counts_to_team():
    # 虎扑阵容新增选手（静态 PLAYER_TEAM 未登记）也应折算进其所属队伍
    ws = danmu_intel.win_signal(_rows(["Burdol赢了"] * 6), ["T1", "HLE"], threshold=6,
                                game="lol", player_teams={"Burdol": "HLE"})
    assert ws["sample_status"] == "ready"
    assert ws["count_b"] == 6 and ws["count_a"] == 0
    assert ws["pct_b"] == 100


def test_dynamic_lineup_hupu_name_maps_to_alias():
    # 虎扑官方名 Gumayusi 反查到 PLAYERS["Guma"] 别名，昵称弹幕"姑妈赢了"也应计 T1
    ws = danmu_intel.win_signal(_rows(["姑妈赢了"] * 5 + ["Chovy拿下"] * 3), ["T1", "GEN"],
                                threshold=8, game="lol",
                                player_teams={"Gumayusi": "T1", "Chovy": "GEN"})
    assert ws["count_a"] == 5 and ws["count_b"] == 3


def test_dynamic_lineup_overrides_static_player_team():
    # 转会/换队：动态阵容 Chovy->HLE 覆盖静态 PLAYER_TEAM 的 Chovy->GEN
    ws = danmu_intel.win_signal(_rows(["Chovy赢了"] * 6), ["T1", "HLE"], threshold=6,
                                game="lol", player_teams={"Chovy": "HLE"})
    assert ws["count_b"] == 6 and ws["count_a"] == 0


def test_dynamic_lineup_empty_falls_back_to_static():
    # 阵容拉取失败/为空时，静态 PLAYER_TEAM（Faker->T1）仍生效
    for player_teams in (None, {}):
        ws = danmu_intel.win_signal(_rows(["Faker赢了"] * 6), ["T1", "GEN"], threshold=6,
                                    game="lol", player_teams=player_teams)
        assert ws["count_a"] == 6 and ws["count_b"] == 0


def test_dynamic_lineup_unknown_name_matches_official():
    # 阵容里 PLAYERS 未登记的选手，官方名本身即关键词
    ws = danmu_intel.win_signal(_rows(["Heng赢了"] * 6), ["T1", "HLE"], threshold=6,
                                game="lol", player_teams={"Heng": "HLE"})
    assert ws["count_b"] == 6 and ws["count_a"] == 0


def test_dynamic_lineup_full_team_name_canonicalizes():
    # 阵容队伍名用全称 "Team Spirit" 也应经 _canon_team 归一为 Spirit
    ws = danmu_intel.win_signal(_rows(["Yatoro赢了"] * 5), ["Iron Wing", "Spirit"], threshold=5,
                                game="dota2", player_teams={"Yatoro": "Team Spirit"})
    assert ws["count_b"] == 5 and ws["count_a"] == 0


# --------------------------------------------------------------------------- 近窗口口径（2026-10-19，防"前期优势累积盖过末段被翻盘"）

def _rows_ts(pairs: list[tuple[str, float]]) -> list[dict]:
    """带时间戳的行（ts = now - ago 秒），用于近窗口口径测试。"""
    now = 1_000_000.0
    return [{"text": t, "ts": now - ago} for t, ago in pairs]


def test_recent_window_reflects_reversal():
    # 前 8 分钟 Alpha 优势 + 最后 2 分钟 Alpha 被翻盘 → 近窗口应判 Beta 占优（Alpha 输了）
    rows = _rows_ts(
        [("Alpha稳了", 540)] * 40 + [("Alpha拿下", 420)] * 40 + [("Alpha必胜", 360)] * 20
        + [("Alpha寄了", 90)] * 30 + [("Alpha输了", 60)] * 20 + [("Alpha被零封", 55)] * 10
    )
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=10)
    assert ws["sample_status"] == "ready"
    assert ws["basis"] == "recent"
    assert ws["pct_b"] > ws["pct_a"]  # 反转后 Beta 占优


def test_recent_window_insufficient_falls_back_cumulative():
    # 近 5 分钟样本 < 阈值 → 回退整场累积（basis=cumulative）
    rows = _rows_ts([("Alpha稳了", 540)] * 6 + [("Alpha寄了", 30)] * 3)
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=10)
    assert ws["basis"] == "cumulative"


def test_window_disabled_uses_cumulative():
    # window_seconds=0/None → 退化为整场累积（旧行为，供显式关闭用）
    rows = _rows_ts([("Alpha稳了", 540)] * 6 + [("Alpha寄了", 30)] * 4)
    ws = danmu_intel.win_signal(rows, ["Alpha", "Beta"], threshold=10, window_seconds=0)
    assert ws["basis"] == "cumulative"
    assert ws["count_a"] == 6 and ws["count_b"] == 4


def test_no_timestamp_uses_cumulative():
    # 行无时间戳（向后兼容，旧测试/调用方）→ 退化为整场累积
    ws = danmu_intel.win_signal(_rows(["Alpha赢了"] * 6 + ["Beta拿下"] * 4), ["Alpha", "Beta"])
    assert ws["basis"] == "cumulative"
    assert ws["pct_a"] == 60 and ws["pct_b"] == 40


# --------------------------------------------------------------------------- render

def _stats_ready() -> dict:
    return {
        "win_signal": {
            "team_a": "Alpha", "team_b": "Beta",
            "count_a": 60, "count_b": 40, "total": 100,
            "pct_a": 60, "pct_b": 40,
            "sample_status": "ready", "threshold": 10,
        }
    }


def _ratings() -> dict:
    return {
        "home": {"name": "LNG", "team_id": "9"},
        "away": {"name": "WBG", "team_id": "11"},
        "game": {"num": 3, "name": "第3局"},
        "fetched_at_utc": "2026-10-18T12:00:00Z",
        "players": [
            {"name": "Elk", "score": 6.9, "count": 1233, "team_id": "11", "team": "WBG"},
            {"name": "Nia", "score": 2.5, "count": 839, "team_id": "9", "team": "LNG"},
        ],
    }


def test_situation_ready_renders_blue_red():
    html = render_node_page._situation(_stats_ready(), _ratings(), ["Alpha", "Beta"])
    assert "两队胜率" in html
    assert "60%" in html and "40%" in html
    assert "#0071e3" in html and "#ff3b30" in html
    assert "两队相加恒为 100%" in html


def test_situation_insufficient_shows_note():
    stats = {"win_signal": {"total": 2, "pct_a": None, "pct_b": None,
                            "sample_status": "insufficient", "threshold": 10}}
    html = render_node_page._situation(stats, None, ["Alpha", "Beta"])
    assert "样本不足" in html
    assert "60%" not in html


def test_situation_no_ratings_shows_gap():
    html = render_node_page._situation(_stats_ready(), None, ["Alpha", "Beta"])
    assert "暂未获取到虎扑选手评分" in html


def test_rating_cols_align_blue_to_team1():
    html = render_node_page._rating_cols(_ratings(), ["WBG", "LNG"])
    # 队1 = WBG（虎扑客队）→ 蓝列在左；队2 = LNG（主队）→ 红列在右
    assert "color:#0071e3\">WBG" in html
    assert "color:#ff3b30\">LNG" in html
