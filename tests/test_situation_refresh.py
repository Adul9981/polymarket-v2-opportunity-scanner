"""【比赛局势】实时刷新回归（2026-10-18 固化，按小局：局内实时、局末冻结 + 评分赛后回填）。

锁定：
  1. 胜率子块/评分子块各自带 BEGIN/END 标记，供 refresh_situation 就地替换；
  2. _replace_block 幂等 + 无标记返回 None（不误写旧页）；
  3. fetch_ratings 走本小局（fetch_player_ratings 以 (obn, obt, gi, strict_game=True) 调用）；
  4. _in_backfill：end 节点生成后 30 分钟内允许评分回填，超时全冻结；
  5. _rat_block：无评分/空 players 返回 None（不回写"暂无"覆盖已有评分）；
  6. game_start_iso 优先 mid 节点 slice_from（= 本局 g_start）。
"""

from __future__ import annotations

import datetime

import danmu_intel
import fetch_hupu_player_ratings
import refresh_situation
import render_node_page
import vps_intel_pipeline as vp


def _rows(texts: list[str]) -> list[dict]:
    return [{"text": t} for t in texts]


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


# --------------------------------------------------------------------------- markers

def test_win_block_has_markers():
    teams = ["Alpha", "Beta"]
    ws = danmu_intel.win_signal(_rows(["Alpha赢了"] * 10), teams)
    block = render_node_page.situation_win_block(ws, teams)
    assert render_node_page._WIN_BEGIN in block and render_node_page._WIN_END in block


def test_ratings_block_has_markers():
    block = render_node_page.situation_ratings_block(_ratings(), ["WBG", "LNG"])
    assert render_node_page._RAT_BEGIN in block and render_node_page._RAT_END in block


# --------------------------------------------------------------------------- _replace_block

def test_replace_block_idempotent():
    new = render_node_page._WIN_BEGIN + "NEW" + render_node_page._WIN_END
    html = f"<div>{render_node_page._WIN_BEGIN}OLD{render_node_page._WIN_END}</div>"
    once = refresh_situation._replace_block(
        html, render_node_page._WIN_BEGIN, render_node_page._WIN_END, new
    )
    assert once == f"<div>{new}</div>"
    twice = refresh_situation._replace_block(
        once, render_node_page._WIN_BEGIN, render_node_page._WIN_END, new
    )
    assert twice == once


def test_replace_block_missing_marker_returns_none():
    assert (
        refresh_situation._replace_block(
            "<div>x</div>", render_node_page._WIN_BEGIN, render_node_page._WIN_END, "Y"
        )
        is None
    )


# --------------------------------------------------------------------------- fetch_ratings 本小局

def test_fetch_ratings_uses_per_game():
    captured: dict = {}
    orig_load = vp.load_match
    orig_fetch = fetch_hupu_player_ratings.fetch_player_ratings

    vp.load_match = lambda mid: {"hupu_score_out_biz_no": "3817", "hupu_score_out_biz_type": "lol_match"}

    def fake(obn, obt, *a, **kw):
        captured["args"] = (obn, obt)
        captured["extra"] = (a, kw)
        return {"players": [], "game": {"num": 3}}

    fetch_hupu_player_ratings.fetch_player_ratings = fake
    try:
        result = vp.fetch_ratings("lol-123", 3)
    finally:
        vp.load_match = orig_load
        fetch_hupu_player_ratings.fetch_player_ratings = orig_fetch

    assert captured["args"] == ("3817", "lol_match")
    assert captured["extra"] == ((3,), {"strict_game": True})  # 本小局 strict，防串局
    assert result == {"players": [], "game": {"num": 3}}


# --------------------------------------------------------------------------- 评分回填窗口

def _end_state(minutes_ago: float) -> dict:
    gen = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes_ago)
    return {"generated_at": gen.isoformat(timespec="seconds")}


def test_in_backfill_recent_true():
    assert refresh_situation._in_backfill(_end_state(10)) is True


def test_in_backfill_expired_false():
    assert refresh_situation._in_backfill(_end_state(40)) is False


def test_in_backfill_missing_generated_at_false():
    assert refresh_situation._in_backfill({}) is False


# --------------------------------------------------------------------------- _rat_block（空评分不回写）

def test_rat_block_empty_players_returns_none():
    orig = vp.fetch_ratings
    vp.fetch_ratings = lambda mid, gi: {"players": [], "game": {"num": gi}}
    try:
        assert refresh_situation._rat_block("m1", 1, ["Alpha", "Beta"]) is None
    finally:
        vp.fetch_ratings = orig


def test_rat_block_nonempty_returns_block():
    orig = vp.fetch_ratings
    vp.fetch_ratings = lambda mid, gi: _ratings()
    try:
        block = refresh_situation._rat_block("m1", 3, ["WBG", "LNG"])
    finally:
        vp.fetch_ratings = orig
    assert block is not None
    assert render_node_page._RAT_BEGIN in block and render_node_page._RAT_END in block


# --------------------------------------------------------------------------- _win_block 三档

def test_win_block_tiered_uses_ratings_when_no_danmu(tmp_path, monkeypatch):
    """节点页胜率三档：无弹幕但有本小局评分 -> 70/30（不再是 50/50）。"""
    monkeypatch.setattr(refresh_situation, "game_start_iso", lambda mid, gi: "2026-10-18T07:00:00+00:00")
    monkeypatch.setattr(vp, "SLICE_DIR", tmp_path)

    def fake_slice(start, files, out, end):
        out.write_text("", encoding="utf-8")
        return 0

    monkeypatch.setattr(vp, "slice_rows", fake_slice)
    monkeypatch.setattr(vp, "fetch_lineup", lambda mid: None)
    monkeypatch.setattr(
        danmu_intel,
        "win_signal",
        lambda rows, teams, game=None, player_teams=None: {"total": 0, "pct_a": 50, "pct_b": 50},
    )
    ratings = {
        "home": {"name": "LNG", "team_id": "9"},
        "away": {"name": "WBG", "team_id": "11"},
        "players": [
            {"name": "Elk", "score": 9.0, "team_id": "11"},
            {"name": "Nia", "score": 3.0, "team_id": "9"},
        ],
    }
    block = refresh_situation._win_block("m1", 3, ["WBG", "LNG"], [], "lol", ratings)
    assert block is not None
    assert "70" in block and "30" in block
    assert render_node_page._WIN_BEGIN in block and render_node_page._WIN_END in block


# --------------------------------------------------------------------------- game_start

def test_game_start_prefers_mid_slice_from():
    orig = refresh_situation._node_state

    def fake(mid, gi, phase):
        return {"bp": {"slice_from": "2026-10-18T07:00:00+00:00"},
                "mid": {"slice_from": "2026-10-18T07:15:00+00:00"}}.get(phase)

    refresh_situation._node_state = fake
    try:
        assert refresh_situation.game_start_iso("x", 1) == "2026-10-18T07:15:00+00:00"
    finally:
        refresh_situation._node_state = orig
