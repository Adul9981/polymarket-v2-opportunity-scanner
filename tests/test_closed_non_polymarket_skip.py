"""已结束非 Polymarket 场次跳过判定回归（2026-10-25 固化）。

教训：001b298 引入"closed 且 hupu/official 直接 return"后，场次 closed 常早于 Codex
逐个跑完节点（4-5 分钟/个），导致 g1_end/g2_bp 等后半程节点永久缺失
（如 cs2-hupu-1441778164564995316 只剩 pre/g1_bp/g1_mid 三页）。
修复：跳过判定收窄为"从未生成过任何小局节点"；已开始生成的场次继续跑完剩余节点。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def _state(tmp_path: Path) -> Path:
    d = tmp_path / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_closed_hupu_with_started_nodes_is_not_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """已生成过小局节点（g1_bp/g1_mid）的 closed hupu 场次必须继续，不截断后半程。"""
    state = _state(tmp_path)
    monkeypatch.setattr(V, "STATE_DIR", state)
    (state / "cs2-hupu-1441778164564995316_g1_bp.json").write_text("{}", encoding="utf-8")
    (state / "cs2-hupu-1441778164564995316_g1_mid.json").write_text("{}", encoding="utf-8")

    m = {"closed": True, "_hupu": True, "id": "cs2-hupu-1441778164564995316"}
    assert V._closed_non_polymarket_skip(m, m["id"]) is False


def test_closed_hupu_without_nodes_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """从未生成节点的 closed hupu 场次仍跳过（保留 10-16 防误切片红线）。"""
    state = _state(tmp_path)
    monkeypatch.setattr(V, "STATE_DIR", state)

    assert V._closed_non_polymarket_skip({"closed": True, "_hupu": True, "id": "x"}, "x") is True
    assert V._closed_non_polymarket_skip({"closed": True, "_official": True, "id": "x"}, "x") is True


def test_not_closed_or_not_non_polymarket_never_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """未 closed、或非 hupu/official 的场次不进入跳过逻辑。"""
    state = _state(tmp_path)
    monkeypatch.setattr(V, "STATE_DIR", state)

    assert V._closed_non_polymarket_skip({"closed": False, "_hupu": True, "id": "x"}, "x") is False
    assert V._closed_non_polymarket_skip({"closed": True, "id": "x"}, "x") is False
    assert V._closed_non_polymarket_skip({"closed": False, "id": "x"}, "x") is False


def test_hupu_total_games_from_official_score(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """closed hupu 场次从官方比分推导实际局数（2:0 -> 2），防止补不存在的 G3+。"""
    (tmp_path / "data").mkdir()
    sched = tmp_path / "data" / "hupu_esports_schedule.json"
    sched.write_text(
        '{"matches": ['
        '{"hupu_match_id": "1441778164564995316", "scores": ["2", "0"]},'
        '{"hupu_match_id": "other", "scores": ["2", "1"]}'
        ']}',
        encoding="utf-8",
    )
    monkeypatch.setattr(V, "ROOT", tmp_path)

    m = {"id": "cs2-hupu-1441778164564995316", "_hupu": True}
    assert V._hupu_total_games(m) == 2
    # 非 hupu / 找不到 / 比分为空 -> None
    assert V._hupu_total_games({"id": "cs2-hupu-1441778164564995316"}) is None
    assert V._hupu_total_games({"id": "cs2-hupu-missing", "_hupu": True}) is None

