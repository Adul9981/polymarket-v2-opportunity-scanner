"""run_codex_report 兜底取回回归（2026-10-25 固化）。

教训：Codex 偶发自作主张把报告写到 runtime/pending_reports/（8-28 起就存在的
诱饵目录）而不是 prompt 指定的 reports/，导致 generate_game_node 判
"report missing rc=0"、节点页"生成但看不见"（线上壳误显示"本场暂无弹幕情报"）。
修复：run_codex_report 在 Codex 返回后，若 reports/ 无目标文件，则从
pending_reports/ 取回同名文件，使 node/pre/live 所有调用点 report.exists() 一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


class _FakeRun:
    """模拟 Codex 子进程：rc=0 但把文件写到了 pending_reports（没写 reports）。"""

    returncode = 0
    stdout = "ok"
    stderr = ""


def _report(tmp_path: Path, name: str) -> Path:
    return tmp_path / "reports" / name


def test_codex_writes_pending_reports_is_recovered(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Codex 写错到 pending_reports 时，run_codex_report 必须取回到 reports/。"""
    (tmp_path / "reports").mkdir()
    pending = tmp_path / "runtime" / "pending_reports"
    pending.mkdir(parents=True)
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "REPORTS", tmp_path / "reports")

    name = "intel_danmu_G2-Aurora_2026-10-25_g1_mid.html"
    (pending / name).write_text("<html>recovered</html>", encoding="utf-8")

    monkeypatch.setattr(V.subprocess, "run", lambda *a, **k: _FakeRun())

    rc, _so, _se = V.run_codex_report(
        "cs2-hupu-x", ["G2", "Aurora"], "2026-10-25",
        Path("x_intel.json"), Path("x_slice.jsonl"), game=1, gphase="mid",
    )

    target = _report(tmp_path, name)
    assert rc == 0
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "<html>recovered</html>"


def test_codex_writes_reports_directly_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Codex 正常写到 reports/ 时，兜底不覆盖、不破坏原文件。"""
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "REPORTS", tmp_path / "reports")

    name = "intel_danmu_G2-Aurora_2026-10-25_g1_mid.html"
    _report(tmp_path, name).write_text("<html>direct</html>", encoding="utf-8")

    monkeypatch.setattr(V.subprocess, "run", lambda *a, **k: _FakeRun())

    V.run_codex_report(
        "cs2-hupu-x", ["G2", "Aurora"], "2026-10-25",
        Path("x_intel.json"), Path("x_slice.jsonl"), game=1, gphase="mid",
    )

    assert _report(tmp_path, name).read_text(encoding="utf-8") == "<html>direct</html>"
