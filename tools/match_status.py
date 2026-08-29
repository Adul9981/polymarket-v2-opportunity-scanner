#!/usr/bin/env python3
"""Match status resolution (shared by today page & homepage generators).

真实时间优先，禁止用扫描快照 time_status 直接定状态
（教训 2026-08-25：已结束比赛曾显示"进行中"，未开始比赛曾误判"已结束"）。
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path


def parse_dt(iso: str):
    if not iso:
        return None
    try:
        return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(
            datetime.timezone(datetime.timedelta(hours=8))
        )
    except ValueError:
        return None


def _team_kws(title: str) -> tuple[list[str], list[str]]:
    mm = re.search(r"(.+?)\s+vs\s+(.+?)\s*(?:\(|\-|$)", title or "", re.I)
    if not mm:
        return [], []
    k1 = [w for w in re.split(r"\s+", re.sub(r"\(.*?\)", "", mm.group(1))) if len(w) > 2]
    k2 = [w for w in re.split(r"\s+", re.sub(r"\(.*?\)", "", mm.group(2))) if len(w) > 2]
    return k1, k2


def has_full_intel(title: str, date: str, intel_dir: Path) -> bool:
    """该场已有完整情报页（服务器真实结束后产出）=> 已结束的权威信号。"""
    k1, k2 = _team_kws(title)
    if not k1 or not k2:
        return False
    # 教训 2026-08-26：节点页（_g1_bp/_g1_mid/_g1_end/_pre/_live 等）不是整场页，
    # 不能据此判"已结束"——KT vs BRO（BO5 进行中）曾被节点页误标已结束。
    # 2026-08-26 兼容两种命名：`..._2026-08-26.html`（流水线整场）与
    # `..._2026-08-26_full.html` / `..._full_2026-08-26.html`（本地整场）。
    node_re = re.compile(r"_(g\d+|bp|mid|end|pre|live|s\d)([_.]|$)", re.I)
    for f in intel_dir.glob(f"intel_danmu_*{date}*.html"):
        low = f.name.lower()
        if node_re.search(low):
            continue
        # 排除时间轴壳与"局"级页（_full 之前的 _gN 等）
        if re.search(r"_g\d+_", low):
            continue
        if any(w.lower() in low for w in k1) and any(w.lower() in low for w in k2):
            return True
    return False


def match_status(
    start_raw: str,
    end_raw: str,
    time_status: str,
    title: str,
    date: str,
    now: datetime.datetime,
    intel_dir: Path,
) -> str:
    """Return "upcoming" | "live" | "ended"."""
    st = (time_status or "").lower()
    start = parse_dt(start_raw)
    end = parse_dt(end_raw)
    if start and now < start:
        return "upcoming"
    if end and now >= end:
        return "ended"
    if st in ("closed", "ended", "final"):
        return "ended"
    if has_full_intel(title, date, intel_dir):
        return "ended"
    if start and now >= start:
        return "live"
    return "upcoming"
