"""league_files 目录兼容 + 日期收窄回归（2026-10-25 固化）。

教训：采集端仍写旧结构 danmu/<platform>/<file>.jsonl，读取端 2026-09-10
改成了 danmu/<game>/<platform>/<file>.jsonl，game 层目录从未存在 ->
all_files 扫出 0 文件 -> 所有比赛切片 0 字节。修复后 all_files 兼容两种结构；
同时 game 层迁移未落地导致 league_files 退回关键词拿到跨数月 ~260 个文件，
verify_end/slice_rows 每节点全量扫一遍，实时场次情报严重滞后 -> 加开赛日 ±1 天
日期收窄。
"""

from __future__ import annotations

from pathlib import Path

import vps_intel_pipeline as V


def _files(*names: str) -> list[Path]:
    return [Path(n) for n in names]


def test_file_date_prefix() -> None:
    assert V._file_date(Path("2026-10-25_huya_csboy_official.jsonl")) == "2026-10-25"
    assert V._file_date(Path("2026-08-24_huya_csboy_mo.jsonl")) == "2026-08-24"
    assert V._file_date(Path("no_date_huya_csboy.jsonl")) is None


def test_date_window_around_start() -> None:
    lo, hi = V._date_window({"start_time": "2026-10-25T13:00:00Z"})
    assert lo == "2026-10-24" and hi == "2026-10-26"
    assert V._date_window({"start_time": ""}) is None
    assert V._date_window({}) is None


def test_league_files_cs2_keyword_and_date_window() -> None:
    files = _files(
        "2026-10-25_huya_csboy_official.jsonl",
        "2026-10-25_huya_csboy_mo.jsonl",
        "2026-10-25_kick_eslcs.jsonl",
        "2026-10-24_huya_csboy_official.jsonl",   # 窗口下界（跨午夜兜底）
        "2026-08-24_huya_csboy_official.jsonl",   # 两个月前 -> 应收窄掉
        "2026-08-24_huya_lol_official.jsonl",     # 其他游戏 -> 关键词已排除
    )
    m = {"id": "cs2-hupu-1441778164564995315", "start_time": "2026-10-25T13:00:00Z"}
    out = V.league_files(m, files)
    names = {p.name for p in out}
    assert "2026-10-25_huya_csboy_official.jsonl" in names
    assert "2026-10-25_kick_eslcs.jsonl" in names
    assert "2026-10-24_huya_csboy_official.jsonl" in names
    assert "2026-08-24_huya_csboy_official.jsonl" not in names  # 日期收窄
    assert "2026-08-24_huya_lol_official.jsonl" not in names    # 跨联赛排除


def test_league_files_keeps_undated_files() -> None:
    # 无日期前缀的文件保守保留，避免丢数据
    files = _files(
        "2026-10-25_huya_csboy_official.jsonl",
        "undated_huya_csboy.jsonl",
    )
    m = {"id": "cs2-hupu-x", "start_time": "2026-10-25T13:00:00Z"}
    names = {p.name for p in V.league_files(m, files)}
    assert "undated_huya_csboy.jsonl" in names


def test_league_files_no_start_time_keeps_all() -> None:
    # 无 start_time -> 无法收窄，保持旧行为（全量），不静默丢数据
    files = _files(
        "2026-10-25_huya_csboy_official.jsonl",
        "2026-08-24_huya_csboy_official.jsonl",
    )
    m = {"id": "cs2-hupu-x", "start_time": ""}
    assert len(V.league_files(m, files)) == 2
