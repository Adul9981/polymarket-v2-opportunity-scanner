"""系列已决不误生成 + 壳页跨午夜日期 glob 回归（2026-10-29 固化）。

两个 bug：
  B1 日期错位：跨午夜场次报告文件名日期（start_time 的 UTC 日期）与壳页日期
     （北京时间/结构化库 date 字段）差一天，壳页单一日期 glob 漏配 ->
     显示"本场暂无弹幕情报"（教训：MKOI-T1 报告 2026-10-28 / 壳 2026-10-29）。
  B2 G3 误生成：BO3 2-0 收官时 game_status 只有 G1/G2，缺失市场的小局走兜底
     时间窗误生成不存在的 G3 节点（教训：MKOI-T1 2-0 却生成 g3_bp/mid/end）。
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


# ---------- B2：_series_decided 纯函数 ----------

def test_series_decided_bo3_2_0():
    assert V._series_decided({1: {"winner": 1}, 2: {"winner": 1}}, 3) is True


def test_series_decided_bo3_1_1_not_decided():
    assert V._series_decided({1: {"winner": 0}, 2: {"winner": 1}}, 3) is False


def test_series_decided_bo5_3_0():
    gs = {1: {"winner": 1}, 2: {"winner": 1}, 3: {"winner": 1}}
    assert V._series_decided(gs, 5) is True


def test_series_decided_bo5_2_2_not_decided():
    gs = {1: {"winner": 0}, 2: {"winner": 1}, 3: {"winner": 0}, 4: {"winner": 1}}
    assert V._series_decided(gs, 5) is False


def test_series_decided_empty():
    assert V._series_decided({}, 3) is False


# ---------- B2：market 分支系列已决时停止推进 ----------

def _match() -> dict:
    return {
        "id": "lol-teama-teamb-2026-10-29",
        "teams": ["TeamA", "TeamB"],
        "start_time": "2026-10-28T20:05:00+00:00",  # 已过去（≥30 分钟）
        "league": "LoL",
        "format": 3,  # BO3
    }


def _prime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list:
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
    monkeypatch.setattr(V, "verify_end", lambda teams, files: "未确认（进行中）：窗口内无数据")
    monkeypatch.setattr(V, "slice_rows", lambda *a, **k: 100)
    monkeypatch.setattr(V, "subprocess", _NoSubprocess())
    monkeypatch.setattr(V, "build_timeline_shell", lambda *a, **k: None)
    # 系列已决：TeamB(1) 连下两局 2-0
    monkeypatch.setattr(
        V, "read_game_status",
        lambda slug: {1: {"closed": True, "winner": 1}, 2: {"closed": True, "winner": 1}},
    )

    captured: list = []

    def fake_game_node(mid, teams, date, slug_id, gi, gphase, slice_from, files,
                       end_basis="", **kw):
        captured.append((gi, gphase))

    monkeypatch.setattr(V, "generate_game_node", fake_game_node)
    return captured


def test_market_branch_stops_on_series_decided(tmp_path, monkeypatch):
    """BO3 2-0：只生成 g1_end/g2_end，不生成不存在的 g3 节点。"""
    captured = _prime(monkeypatch, tmp_path)
    V.process_match(_match(), [])
    assert (1, "end") in captured
    assert (2, "end") in captured
    assert not any(gi == 3 for gi, _ph in captured), "2-0 收官时禁止生成 G3 节点"


# ---------- B1：壳页跨午夜日期 glob ----------

def test_shell_glob_matches_report_prev_day_date(tmp_path, monkeypatch):
    """报告文件名日期比壳页日期早一天（跨午夜）时，壳页应找到节点而非"暂无"。"""
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "_TEAM_ROWS", [])

    (reports / "intel_danmu_TeamA-TeamB_2026-10-28_g1_end.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    out = V.build_timeline_shell(
        "lol-teama-teamb-2026-10-29", ["TeamA", "TeamB"], "LoL", "2026-10-29", 3
    )
    html = out.read_text(encoding="utf-8")
    assert "本场暂无弹幕情报" not in html
    assert 'data-src="intel_danmu_TeamA-TeamB_2026-10-28_g1_end.html"' in html


def test_shell_glob_ignores_far_outside_date(tmp_path, monkeypatch):
    """报告文件名日期远在窗口外（如跨月）时，壳页应显示"暂无"而非误配。"""
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(V, "REPORTS", reports)
    monkeypatch.setattr(V, "ROOT", tmp_path)
    monkeypatch.setattr(V, "_TEAM_ROWS", [])

    (reports / "intel_danmu_TeamA-TeamB_2026-10-20_g1_end.html").write_text(
        "<html></html>", encoding="utf-8"
    )
    out = V.build_timeline_shell(
        "lol-teama-teamb-2026-10-29", ["TeamA", "TeamB"], "LoL", "2026-10-29", 3
    )
    html = out.read_text(encoding="utf-8")
    assert "本场暂无弹幕情报" in html


class _NoSubprocess:
    def run(self, *args, **kwargs):
        return None
