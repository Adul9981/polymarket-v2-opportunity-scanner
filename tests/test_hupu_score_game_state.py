"""hupu 实时比分驱动小局状态回归（2026-10-31 固化）。

教训：进行中的 hupu 场次无 Polymarket 小局市场，兜底路径用弹幕 GG 关键词
（detect_match_end_gg，含"夺冠/晋级/出局"赛事级闲谈）判系列结束，会在 G2 就被
误判"系列已结束"截断后续节点（Vitality vs MOUZ：09:07-09:16 连续误报，G2 节点
被卡约 13 分钟）。

修复：进行中的 hupu 场次，小局数 / 小局结束 / 系列结束全走官方比分
（scores 增量 + status/winner_member_id），弹幕 GG 仅作比分读不到时的兜底。
本测试锁定：比分可读时弹幕 GG 假阳性不生效；系列结束后不补不存在的局。
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


# ---------- _hupu_score_state 纯函数 ----------

def _write_hupu(tmp_path: Path, entries: list[dict]) -> Path:
    (tmp_path / "data").mkdir(exist_ok=True)
    sched = tmp_path / "data" / "hupu_esports_schedule.json"
    sched.write_text(json.dumps({"matches": entries}, ensure_ascii=False), encoding="utf-8")
    return sched


def test_hupu_score_state_in_progress(tmp_path, monkeypatch):
    # scores ["0","1"]，inProgress，winner 空 -> (1, False)
    _write_hupu(tmp_path, [{"hupu_match_id": "1441778164565002822", "scores": ["0", "1"],
                            "status": "inProgress", "winner_member_id": ""}])
    monkeypatch.setattr(V, "ROOT", tmp_path)
    m = {"_hupu": True, "id": "cs2-hupu-1441778164565002822"}
    assert V._hupu_score_state(m) == (1, False)


def test_hupu_score_state_completed(tmp_path, monkeypatch):
    # scores ["0","3"]，completed -> (3, True)
    _write_hupu(tmp_path, [{"hupu_match_id": "1441778164565002822", "scores": ["0", "3"],
                            "status": "completed", "winner_member_id": "123"}])
    monkeypatch.setattr(V, "ROOT", tmp_path)
    m = {"_hupu": True, "id": "cs2-hupu-1441778164565002822"}
    assert V._hupu_score_state(m) == (3, True)


def test_hupu_score_state_completed_by_winner_only(tmp_path, monkeypatch):
    # status 为空但 winner_member_id 非空 -> completed=True
    _write_hupu(tmp_path, [{"hupu_match_id": "1441778164565002822", "scores": ["2", "0"],
                            "status": "", "winner_member_id": "999"}])
    monkeypatch.setattr(V, "ROOT", tmp_path)
    m = {"_hupu": True, "id": "cs2-hupu-1441778164565002822"}
    assert V._hupu_score_state(m) == (2, True)


def test_hupu_score_state_dash_placeholder(tmp_path, monkeypatch):
    # "-" 占位符跳过，视为 0 局（未开赛）
    _write_hupu(tmp_path, [{"hupu_match_id": "1441778164565002822", "scores": ["-", "-"],
                            "status": "scheduled", "winner_member_id": ""}])
    monkeypatch.setattr(V, "ROOT", tmp_path)
    m = {"_hupu": True, "id": "cs2-hupu-1441778164565002822"}
    assert V._hupu_score_state(m) == (0, False)


def test_hupu_score_state_missing_or_non_hupu(tmp_path, monkeypatch):
    _write_hupu(tmp_path, [{"hupu_match_id": "other", "scores": ["2", "1"]}])
    monkeypatch.setattr(V, "ROOT", tmp_path)
    # 找不到场次 -> (None, False)
    assert V._hupu_score_state({"_hupu": True, "id": "cs2-hupu-missing"}) == (None, False)
    # 非 hupu 场次 -> (None, False)
    assert V._hupu_score_state({"_official": True, "id": "cs2-hupu-other"}) == (None, False)
    # 无比分字段 -> (None, False)
    _write_hupu(tmp_path, [{"hupu_match_id": "1441778164565002822"}])
    assert V._hupu_score_state({"_hupu": True, "id": "cs2-hupu-1441778164565002822"}) == (None, False)


# ---------- process_match 兜底循环：比分驱动系列/小局结束 ----------

PAST = datetime.datetime(2026, 10, 30, 5, 0, tzinfo=datetime.timezone.utc)


class _NoSubprocess:
    def run(self, *args, **kwargs):
        return None


def _match(hupu_id: str = "1441778164565002822", closed: bool = False) -> dict:
    return {
        "id": f"cs2-hupu-{hupu_id}",
        "teams": ["Vitality", "MOUZ"],
        "start_time": "2026-10-30T00:00:00+00:00",  # 已过去
        "league": "CS2",
        "format": None,  # format_of 默认 5
        "_hupu": True,
        "closed": closed,
    }


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, match: dict,
         hupu_entry: dict) -> list:
    state = tmp_path / "state"
    reports = tmp_path / "reports"
    slices = tmp_path / "slices"
    for d in (state, reports, slices):
        d.mkdir(parents=True, exist_ok=True)
    _write_hupu(tmp_path, [hupu_entry])

    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "STATE_DIR", state)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "SLICE_DIR", slices)
    monkeypatch.setattr(V, "_TEAM_ROWS", [])

    monkeypatch.setattr(V, "league_files", lambda m, files: [])
    monkeypatch.setattr(V, "verify_end", lambda teams, files: "未确认（进行中）：窗口内无数据")
    monkeypatch.setattr(V, "read_game_status", lambda slug: {})
    monkeypatch.setattr(V, "fetch_game_markets", lambda slug: {})
    monkeypatch.setattr(V, "detect_game_end_gg", lambda files, since: False)
    # 关键：即使弹幕 GG 判"系列结束"，比分可读时也不得截断
    monkeypatch.setattr(V, "detect_match_end_gg", lambda files, since: True)
    monkeypatch.setattr(V, "bp_slice_from", lambda g_start, start_dt: "2026-10-30T00:00:00+00:00")
    monkeypatch.setattr(V, "anchor_next_game", lambda mid, gi, now_utc: PAST)
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())

    captured: list = []

    def fake_game_node(mid, teams, date, slug_id, gi, gphase, slice_from, files,
                       end_basis="", **kw):
        captured.append((gi, gphase, end_basis))

    monkeypatch.setattr(V, "generate_game_node", fake_game_node)
    V.process_match(match, [])
    return captured


def test_inprogress_hupu_not_stopped_by_danmaku_gg(tmp_path, monkeypatch):
    """进行中 0:1：弹幕 GG 假阳性不生效，G2 bp/mid 必须生成，G2 end 不出。"""
    captured = _run(
        tmp_path, monkeypatch, _match(),
        {"hupu_match_id": "1441778164565002822", "scores": ["0", "1"],
         "status": "inProgress", "winner_member_id": ""},
    )
    assert (1, "end", "hupu") in captured  # G1 结束依据官方比分
    assert (2, "bp", "") in captured
    assert (2, "mid", "") in captured
    assert not any(gi == 2 and ph == "end" for gi, ph, _ in captured)
    assert not any(gi >= 3 for gi, _, _ in captured)


def test_inprogress_hupu_bo3_game3_still_generates(tmp_path, monkeypatch):
    """进行中 1:1（BO3 决胜局）：G3 bp/mid 生成，不出 G4。"""
    captured = _run(
        tmp_path, monkeypatch, _match(),
        {"hupu_match_id": "1441778164565002822", "scores": ["1", "1"],
         "status": "inProgress", "winner_member_id": ""},
    )
    assert (1, "end", "hupu") in captured
    assert (2, "end", "hupu") in captured
    assert (3, "bp", "") in captured
    assert (3, "mid", "") in captured
    assert not any(gi >= 4 for gi, _, _ in captured)


def test_hupu_completed_series_stops_at_played(tmp_path, monkeypatch):
    """系列已结束（0:3，status completed，但 closed 字段滞后未置）：只出 G1-G3，禁补 G4/G5。"""
    captured = _run(
        tmp_path, monkeypatch, _match(closed=False),
        {"hupu_match_id": "1441778164565002822", "scores": ["0", "3"],
         "status": "completed", "winner_member_id": "888"},
    )
    for gi in (1, 2, 3):
        assert (gi, "end", "hupu") in captured
    assert not any(gi >= 4 for gi, _, _ in captured)
