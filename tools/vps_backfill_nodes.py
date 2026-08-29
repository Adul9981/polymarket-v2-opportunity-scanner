#!/usr/bin/env python3
"""Backfill pre/live node pages for finished matches missing nodes.

背景：流水线串行导致部分比赛只产出赛后复盘（无赛前/局中节点）。
本脚本对指定/扫描出的"有 full 但无节点"比赛，用整场弹幕按时间窗回补
赛前(_pre)与局中(_live_<HHMM>)节点页（标注"赛后回补"），并重建时间轴壳。

用法：
  python3 tools/vps_backfill_nodes.py --match lol-gx-g2-2026-08-24
  python3 tools/vps_backfill_nodes.py --all-ended
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
from pathlib import Path

import vps_intel_pipeline as V

STATE = V.STATE_DIR


def backfill(mid: str, teams: list[str], league: str, date: str, start_iso: str, end_iso: str) -> None:
    slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
    files = sorted(V.DANMU.glob("*/*.jsonl"))
    pre = V.REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_pre.html"
    if not pre.exists():
        pre_slice = V.SLICE_DIR / f"{slug_id}_pre.jsonl"
        start_dt = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        V.slice_rows((start_dt - datetime.timedelta(minutes=90)).isoformat(), files, pre_slice)
        pre_intel = STATE / f"{slug_id}_pre_intel.json"
        subprocess.run([str(V.PY), str(V.ROOT / "tools" / "danmu_intel.py"),
                        "--input", str(pre_slice), "--out", str(pre_intel)], timeout=180, check=False)
        print(f"[backfill] {mid}: generating pre...", flush=True)
        V.run_codex_report(slug_id, teams, date, pre_intel, pre_slice, pre=True)
        print(f"[backfill] {mid}: pre done exists={pre.exists()}", flush=True)
        V.build_timeline_shell(mid, teams, league, date)  # 节点生成即进壳（有即可见）

    # 局中按时间窗分 3 段，回补前 2 段
    start_dt = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = datetime.datetime.fromisoformat(end_iso.replace("Z", "+00:00")) if end_iso else start_dt + datetime.timedelta(hours=2)
    total = (end_dt - start_dt).total_seconds()
    for i, frac in enumerate((0.15, 0.45), 1):
        win_start = start_dt + datetime.timedelta(seconds=total * frac)
        stamp = win_start.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime("%H%M")
        live = V.REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_live_{stamp}.html"
        if live.exists():
            continue
        live_slice = V.SLICE_DIR / f"{slug_id}_live_{stamp}.jsonl"
        V.slice_rows((win_start - datetime.timedelta(minutes=20)).isoformat(), files, live_slice)
        live_intel = STATE / f"{slug_id}_live_{stamp}_intel.json"
        subprocess.run([str(V.PY), str(V.ROOT / "tools" / "danmu_intel.py"),
                        "--input", str(live_slice), "--out", str(live_intel)], timeout=180, check=False)
        print(f"[backfill] {mid}: generating live {stamp}...", flush=True)
        V.run_codex_report(slug_id, teams, date, live_intel, live_slice, live=True, stamp=stamp)
        print(f"[backfill] {mid}: live {stamp} done exists={live.exists()}", flush=True)
        V.build_timeline_shell(mid, teams, league, date)  # 节点生成即进壳

    V.build_timeline_shell(mid, teams, league, date)
    print(f"[backfill] {mid}: shell rebuilt", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", default="")
    ap.add_argument("--all-ended", action="store_true")
    args = ap.parse_args()

    matches = json.loads(V.MATCHES.read_text(encoding="utf-8")).get("matches", [])
    if args.match:
        matches = [m for m in matches if m.get("id") == args.match]
    for m in matches:
        mid = m.get("id") or ""
        st = STATE / f"{mid}.json"
        if not st.exists() or (args.match and m.get("id") != args.match):
            continue
        teams = m.get("teams", [])
        if len(teams) != 2:
            continue
        backfill(mid, teams, m.get("league", "-"), (m.get("start_time") or "")[:10],
                 m.get("start_time", ""), m.get("end_time", ""))


if __name__ == "__main__":
    main()
