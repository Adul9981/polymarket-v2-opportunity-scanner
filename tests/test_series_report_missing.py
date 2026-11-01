"""series 复盘 report missing 回归（2026-10-26 固化）。

教训：HLE-IG（2026-10-25）整场复盘因 reports 目录属主错误（501，Codex 沙箱=受限
root 写不了）导致 HTML 落不了盘，但 process_match 的 series 段仍无条件写 st_file
（{mid}.json）-> 下一 tick 看到 st_file 存在 -> "already done, skip" -> 复盘永久缺失。
修复：series 段与 generate_game_node 同款保护——report 不存在时不写 st_file，
下轮重试而非永久跳过。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def _match() -> dict:
    return {
        "id": "lol-hle1-ig1-2026-10-25",
        "teams": ["HLE", "IG"],
        "start_time": "2026-10-25T17:00:00+00:00",  # 已过去（≥30 分钟前），触发结束检测
        "league": "LoL",
        "format": 1,  # BO1：跳过 all_closed 门禁，直接走到 series 段
    }


def _prime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write_report: bool) -> Path:
    """布置 process_match 走到 series 段所需的全局，返回 st_file 路径。"""
    state = tmp_path / "state"
    reports = tmp_path / "reports"
    slices = tmp_path / "slices"
    for d in (state, reports, slices):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "STATE_DIR", state)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "SLICE_DIR", slices)
    monkeypatch.setattr(V, "ROOT", tmp_path)

    # 让 process_match 一路走到 series 段
    monkeypatch.setattr(V, "league_files", lambda m, files: [])
    monkeypatch.setattr(V, "verify_end", lambda teams, files: "确认结束（弹幕多信号）")
    monkeypatch.setattr(V, "slice_rows", lambda *a, **k: 100)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)

    report = reports / "intel_danmu_HLE-IG_2026-10-25.html"

    def fake_codex(*a, **k):
        if write_report:
            report.write_text("<html></html>", encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(V, "run_codex_report", fake_codex)
    return state / "lol-hle1-ig1-2026-10-25.json"


def test_series_report_missing_does_not_write_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex 返回 rc=0 但不落盘 HTML -> 不写 st_file -> 下轮重试而非 skip。"""
    st = _prime(monkeypatch, tmp_path, write_report=False)
    V.process_match(_match(), [])
    assert not st.exists(), "series 复盘 HTML 未落盘时禁止写 st_file（否则永久 already done skip）"


def test_series_report_exists_writes_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Codex 正常落盘 HTML -> 写 st_file（正常终局路径）。"""
    st = _prime(monkeypatch, tmp_path, write_report=True)
    V.process_match(_match(), [])
    assert st.exists(), "series 复盘 HTML 已落盘时必须写 st_file 标记终局"


class _NoSubprocess:
    """替换 subprocess 模块：danmu_intel 子进程在本测试无需真实执行。"""

    def run(self, *args, **kwargs):
        return None
