"""BO1 终局补 end 回归（2026-10-28 固化）。

教训：T1-CFO / KC-BLG（2026-10-26，Worlds BO1）无 Polymarket 小局市场，
game_status.json 无条目 -> 小局 end 检测永远不触发 -> 终局时已生成的
g1_bp/g1_mid 缺 g1_end 节点（BO1 max_games=1 跳过 all_closed 门禁直接出 series）。
修复：终局路径（series 段前）对「有 bp/mid 无 end」的小局补发 end 节点，
切片用 mid 的 slice_from（= 本局起点），end_basis=settlement，幂等（有 end 状态即跳过）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def _match() -> dict:
    return {
        "id": "lol-t1-cfo-2026-10-26",
        "teams": ["T1", "CFO"],
        "start_time": "2026-10-26T16:00:00+00:00",  # 已过去（≥30 分钟前）
        "league": "LoL",
        "format": 1,  # BO1：跳过 all_closed 门禁，直接走到终局 series 段
    }


def _prime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mid_state: str | None,
    end_state: bool,
) -> tuple[Path, list]:
    """布置 process_match 走到终局段所需的全局，返回 (st_file, captured_calls)。"""
    state = tmp_path / "state"
    reports = tmp_path / "reports"
    slices = tmp_path / "slices"
    for d in (state, reports, slices):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "STATE_DIR", state)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "SLICE_DIR", slices)
    monkeypatch.setattr(V, "ROOT", tmp_path)

    monkeypatch.setattr(V, "league_files", lambda m, files: [])
    monkeypatch.setattr(V, "verify_end", lambda teams, files: "确认结束（弹幕多信号）")
    monkeypatch.setattr(V, "slice_rows", lambda *a, **k: 100)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)

    # 预置 g1_mid 状态（= 已生成过 mid 节点，其 slice_from 作为 end 切片起点）
    if mid_state:
        (state / "lol-t1-cfo-2026-10-26_g1_mid.json").write_text(
            json.dumps({"match": "lol-t1-cfo-2026-10-26", "slice_from": mid_state}),
            encoding="utf-8",
        )
    if end_state:
        (state / "lol-t1-cfo-2026-10-26_g1_end.json").write_text("{}", encoding="utf-8")

    report = reports / "intel_danmu_T1-CFO_2026-10-26.html"

    def fake_codex(*a, **k):
        report.write_text("<html></html>", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(V, "run_codex_report", fake_codex)

    captured: list = []

    def fake_game_node(mid, teams, date, slug_id, gi, gphase, slice_from, files,
                       end_basis="", **kw):
        captured.append((gi, gphase, end_basis))

    monkeypatch.setattr(V, "generate_game_node", fake_game_node)
    return state / "lol-t1-cfo-2026-10-26.json", captured


def test_bo1_terminal_backfills_missing_end(tmp_path, monkeypatch):
    """BO1 有 g1_mid 无 g1_end -> 终局补发 end 节点（end_basis=settlement）。"""
    st, captured = _prime(
        monkeypatch, tmp_path,
        mid_state="2026-10-26T17:13:00+00:00", end_state=False,
    )
    V.process_match(_match(), [])
    assert st.exists(), "series 复盘正常落盘后应写终局状态"
    assert (1, "end", "settlement") in captured, "缺 end 的 BO1 应在终局补发 end 节点"


def test_bo1_terminal_skips_existing_end(tmp_path, monkeypatch):
    """g1_end 已存在 -> 不重复补发（幂等）。"""
    st, captured = _prime(
        monkeypatch, tmp_path,
        mid_state="2026-10-26T17:13:00+00:00", end_state=True,
    )
    V.process_match(_match(), [])
    assert st.exists()
    assert not captured, "已有 end 状态时禁止重复补发 end 节点"


def test_bo1_terminal_no_mid_state_skips_backfill(tmp_path, monkeypatch):
    """既无 mid 也无 bp 状态 -> 无切片起点，静默跳过（不崩溃）。"""
    st, captured = _prime(monkeypatch, tmp_path, mid_state=None, end_state=False)
    V.process_match(_match(), [])
    assert st.exists()
    assert not captured, "无 mid/bp 状态时不应补发 end 节点"


class _NoSubprocess:
    """替换 subprocess 模块：danmu_intel 子进程在本测试无需真实执行。"""

    def run(self, *args, **kwargs):
        return None
