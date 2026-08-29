"""Regression tests for match status resolution (防错 E1-E4).

锁定：未开始误判结束 / 已结束显示进行中 / 跨时区误判 / full 页权威信号。
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from match_status import match_status  # noqa: E402


def dt_bj(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s).replace(
        tzinfo=datetime.timezone(datetime.timedelta(hours=8))
    )


@pytest.fixture()
def intel_dir(tmp_path: Path) -> Path:
    d = tmp_path / "intel"
    d.mkdir()
    return d


NOW = dt_bj("2026-08-25T01:30:00")


def test_not_started_is_upcoming(intel_dir: Path) -> None:
    assert (
        match_status(
            "2026-08-25T08:00:00+00:00", "2026-08-25T14:00:00+00:00", "upcoming_within_window",
            "Kiwoom DRX Challengers vs BNK FearX Youth (BO5)", "2026-08-25", NOW, intel_dir,
        )
        == "upcoming"
    )


def test_past_end_is_ended(intel_dir: Path) -> None:
    assert (
        match_status(
            "2026-08-23T12:20:00+00:00", "2026-08-23T18:20:00+00:00", "started_recently_or_live",
            "Bilibili Gaming vs Anyone's Legend (BO3)", "2026-08-23", NOW, intel_dir,
        )
        == "ended"
    )


def test_closed_status_is_ended(intel_dir: Path) -> None:
    assert (
        match_status(
            "2026-08-24T08:00:00+00:00", "2026-08-25T02:00:00+00:00", "closed",
            "Team A vs Team B (BO3)", "2026-08-25", NOW, intel_dir,
        )
        == "ended"
    )


def test_full_intel_page_is_ended(intel_dir: Path) -> None:
    (intel_dir / "intel_danmu_Natus Vincere-Fnatic_2026-08-24.html").write_text("x")
    assert (
        match_status(
            "2026-08-24T15:00:00+00:00", "2026-08-24T21:00:00+00:00", "",
            "Natus Vincere vs Fnatic (BO3)", "2026-08-24", NOW, intel_dir,
        )
        == "ended"
    )


def test_cross_timezone_not_ended_when_just_started(intel_dir: Path) -> None:
    """UTC 日期 08-24、北京 08-25 凌晨刚开赛（end 未到）=> live，禁止误判 ended。"""
    assert (
        match_status(
            "2026-08-24T17:15:00+00:00", "2026-08-24T23:15:00+00:00", "started_recently_or_live",
            "GIANTX vs G2 Esports (BO3)", "2026-08-24", NOW, intel_dir,
        )
        == "live"
    )


def test_node_pages_do_not_mark_ended(intel_dir: Path) -> None:
    """教训 2026-08-26：BO5 进行中，只有节点页（_g1_bp 等）存在时禁止判"已结束"。"""
    for name in (
        "intel_danmu_KT Rolster-HANJIN BRION_2026-08-26_g1_bp.html",
        "intel_danmu_KT Rolster-HANJIN BRION_2026-08-26_g1_end.html",
        "intel_danmu_KT Rolster-HANJIN BRION_2026-08-26_pre.html",
    ):
        (intel_dir / name).write_text("x")
    mid_match = dt_bj("2026-08-26T18:00:00")  # 北京时间 18:00 = UTC 10:00，处于赛程窗口内
    assert (
        match_status(
            "2026-08-26T08:00:00+00:00", "2026-08-26T14:00:00+00:00", "started_recently_or_live",
            "KT Rolster vs HANJIN BRION (BO5)", "2026-08-26", mid_match, intel_dir,
        )
        == "live"
    )
    # 真正无后缀整场页才判 ended
    (intel_dir / "intel_danmu_KT Rolster-HANJIN BRION_2026-08-26.html").write_text("x")
    assert (
        match_status(
            "2026-08-26T08:00:00+00:00", "2026-08-26T14:00:00+00:00", "",
            "KT Rolster vs HANJIN BRION (BO5)", "2026-08-26", mid_match, intel_dir,
        )
        == "ended"
    )


def test_in_progress_is_live(intel_dir: Path) -> None:
    assert (
        match_status(
            "2026-08-24T17:15:00+00:00", "2026-08-25T03:15:00+00:00", "",
            "GIANTX vs G2 Esports (BO3)", "2026-08-24", NOW, intel_dir,
        )
        == "live"
    )
