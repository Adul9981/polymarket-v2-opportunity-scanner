"""系列未结算时弹幕「确认结束」不得截断 G2+ 节点回归（2026-11-01 固化）。

教训：HLE-BLG（2026-10-31，BO3，BLG 2-0）是 Polymarket 场，弹幕 verify_end
在 G1 结束后就返回「确认结束」（软信号），旧路由 `if "确认结束" not in out or
is_non_pm` 直接把它送进整场终局分支，终局门禁发现小局未全结算后 return——这
68 分钟里 G2 bp/mid/end 一个都没生成，整场只剩 G1 + 终局复盘。

修复：终局门禁前移到路由前（_series_settled）——系列未在 game_status 结构上
结算（未 all_closed 且未已决）时，即使弹幕判「确认结束」也继续走小局节点路径
出 G2+ 节点；只有系列真正结算才走整场终局分支。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


# ---------- _series_settled 纯函数 ----------

def test_series_settled_bo1_always_true(monkeypatch):
    monkeypatch.setattr(V, "read_game_status", lambda slug: {})
    assert V._series_settled("x", 1) is True


def test_series_settled_bo3_all_closed(monkeypatch):
    gs = {
        1: {"closed": True, "winner": 0},
        2: {"closed": True, "winner": 1},
        3: {"closed": True, "winner": 0},
    }
    monkeypatch.setattr(V, "read_game_status", lambda slug: gs)
    assert V._series_settled("x", 3) is True


def test_series_settled_bo3_2_0_decided(monkeypatch):
    # 收官局市场不存在（只有 G1/G2 closed），但系列已 2-0 决出 -> 视为已结算
    gs = {1: {"closed": True, "winner": 1}, 2: {"closed": True, "winner": 1}}
    monkeypatch.setattr(V, "read_game_status", lambda slug: gs)
    assert V._series_settled("x", 3) is True


def test_series_settled_bo3_1_0_not_settled(monkeypatch):
    gs = {1: {"closed": True, "winner": 1}}
    monkeypatch.setattr(V, "read_game_status", lambda slug: gs)
    assert V._series_settled("x", 3) is False


def test_series_settled_bo3_1_1_not_settled(monkeypatch):
    gs = {1: {"closed": True, "winner": 0}, 2: {"closed": True, "winner": 1}}
    monkeypatch.setattr(V, "read_game_status", lambda slug: gs)
    assert V._series_settled("x", 3) is False


def test_series_settled_empty_not_settled(monkeypatch):
    monkeypatch.setattr(V, "read_game_status", lambda slug: {})
    assert V._series_settled("x", 3) is False


def test_series_settled_stale_none_not_settled(monkeypatch):
    # game_status 过期（read_game_status 返回 None）-> 视为未结算，不提前终局
    monkeypatch.setattr(V, "read_game_status", lambda slug: None)
    assert V._series_settled("x", 3) is False


# ---------- process_match 路由集成 ----------

def _match() -> dict:
    return {
        "id": "lol-teama-teamb-2026-11-01",
        "teams": ["TeamA", "TeamB"],
        "start_time": "2026-10-31T20:00:00+00:00",  # 已过去（≥30 分钟），触发结束检测
        "league": "LoL",
        "format": 3,  # BO3
    }


def _prime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, gstatus: dict):
    state = tmp_path / "state"
    reports = tmp_path / "reports"
    slices = tmp_path / "slices"
    for d in (state, reports, slices):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "STATE_DIR", state)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "SLICE_DIR", slices)
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "_TEAM_ROWS", [])

    monkeypatch.setattr(V, "league_files", lambda m, files: [])
    monkeypatch.setattr(V, "verify_end", lambda teams, files: "确认结束（弹幕多信号）")
    monkeypatch.setattr(V, "read_game_status", lambda slug: gstatus)
    monkeypatch.setattr(V, "slice_rows", lambda *a, **k: 100)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)

    report = reports / "intel_danmu_TeamA-TeamB_2026-10-31.html"

    def fake_codex(*a, **k):
        report.write_text("<html></html>", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(V, "run_codex_report", fake_codex)

    captured: list = []

    def fake_game_node(mid, teams, date, slug_id, gi, gphase, slice_from, files,
                       end_basis="", **kw):
        captured.append((gi, gphase))

    monkeypatch.setattr(V, "generate_game_node", fake_game_node)
    return state / "lol-teama-teamb-2026-11-01.json", captured


def test_confirm_end_but_not_settled_keeps_generating_nodes(tmp_path, monkeypatch):
    """弹幕判「确认结束」但 game_status 只有 G1（1-0，未结算）-> 走小局路径，
    不写终局状态，G1 结算节点仍会生成（而非被终局门禁 return 截断）。"""
    st, captured = _prime(
        monkeypatch, tmp_path,
        gstatus={1: {"closed": True, "winner": 1}},
    )
    V.process_match(_match(), [])
    assert not st.exists(), "系列未结算时禁止写终局状态（否则整场被 already done skip）"
    assert (1, "end") in captured, "应走小局节点路径，G1 结算节点正常生成"


def test_confirm_end_settled_finalizes(tmp_path, monkeypatch):
    """弹幕判「确认结束」且 game_status 2-0 已决 -> 走终局分支，写终局状态。"""
    st, _captured = _prime(
        monkeypatch, tmp_path,
        gstatus={1: {"closed": True, "winner": 1}, 2: {"closed": True, "winner": 1}},
    )
    V.process_match(_match(), [])
    assert st.exists(), "系列已结算时必须走终局分支写终局状态"


class _NoSubprocess:
    """替换 subprocess 模块：danmu_intel 子进程在本测试无需真实执行。"""

    def run(self, *args, **kwargs):
        return None
