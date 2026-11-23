"""0 样本节点占位页回归（2026-10-26 固化）。

教训：CS2 弹幕源离线（0 样本）时，Codex 偶发 rc=0 但不落盘 → generate_game_node
每 5 分钟空转重试（MongolZ-MOUZ g1_bp/g1_end report missing rc=0 死循环）。
修复：n==0 的节点跳过 Codex/DeepSeek，直接落「样本不足」占位页（无样本不硬撑），
幂等走同一收尾（注入局势 + MD 镜像 + 状态 + 壳），死循环即止。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def test_insufficient_html_has_four_sections_and_no_made_up_signal():
    html = V._insufficient_node_html(["The MongolZ", "MOUZ"], "2026-10-26", 1, "bp")
    # 第 1/2/3/4 段编号齐全（第 2 段比赛局势以「系统注入」占位，待 _inject_situation 替换成真实胜率/评分）
    for no in ("1", "2", "3", "4"):
        assert f'<span class="no">{no}</span>' in html, f"缺第 {no} 段"
    assert "系统注入" in html  # 第 2 段是占位，供 _inject_situation 锚点注入
    # 无样本不硬撑：不出现任何锚点/灰信号/阵容实锤，只有「样本不足/今日无灰信号」
    assert "样本不足" in html
    assert "今日无灰信号" in html
    assert "今日无锚点" in html


def test_zero_sample_node_writes_placeholder_and_skips_codex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """slice_rows 返回 0 时：不调用 Codex/DeepSeek，直接写占位页 + 状态文件。"""
    state = tmp_path / "state"
    slices = tmp_path / "slices"
    reports = tmp_path / "reports"
    for d in (state, slices, reports):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "STATE_DIR", state)
    monkeypatch.setattr(V, "SLICE_DIR", slices)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "ROOT", tmp_path)

    monkeypatch.setattr(V, "slice_rows", lambda *a, **k: 0)
    monkeypatch.setattr(V, "fetch_lineup", lambda *a, **k: None)
    monkeypatch.setattr(V, "fetch_ratings", lambda *a, **k: None)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())
    monkeypatch.setattr(V, "_inject_situation", lambda *a, **k: None)
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)

    def _boom(*a, **k):
        raise AssertionError("0 样本节点禁止调用 AI 生成器")

    monkeypatch.setattr(V, "run_codex_report", _boom)
    monkeypatch.setattr(V, "fast_intel_node", _boom)

    mid = "cs2-hupu-1441778164564995447"
    V.generate_game_node(
        mid,
        ["The MongolZ", "MOUZ"],
        "2026-10-26",
        mid,
        1,
        "bp",
        __import__("datetime").datetime(2026, 10, 26, 8, 0, 0),
        [],
    )

    report = reports / "intel_danmu_The MongolZ-MOUZ_2026-10-26_g1_bp.html"
    assert report.exists(), "0 样本节点必须落占位页（否则继续 report missing 死循环）"
    assert "样本不足" in report.read_text(encoding="utf-8")
    assert (state / f"{mid}_g1_bp.json").exists(), "0 样本节点也必须写状态文件（幂等）"


class _NoSubprocess:
    """替换 subprocess 模块：danmu_intel 子进程在 0 样本下无需真实执行。"""

    def run(self, *args, **kwargs):
        return None
