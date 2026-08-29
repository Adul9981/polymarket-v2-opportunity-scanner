#!/usr/bin/env python3
"""Export today's esports matches from watchlist_events.json -> matches_today.json.

本地侧辅助：每日扫描后运行，把今日比赛清单（对阵/联赛/时间）同步到服务器，
供 vps_intel_pipeline.py 按比赛检测结束并产出情报。

用法：
  python3 tools/export_today_matches.py [--input runtime/watchlist_events.json]
      [--out runtime/matches_today.json] [--date 2026-08-24]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path


def parse_teams(title: str) -> list[str]:
    m = re.search(r":\s*([^(:\-]+?)\s+vs\s+([^(:\-]+)", title or "", re.I)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return []


def league_of(group: str) -> str:
    g = (group or "").lower()
    if "dota" in g:
        return "Dota2"
    if "cs" in g:
        return "CS2"
    if "lol" in g or "league" in g:
        return "LoL"
    return (group or "-").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runtime/watchlist_events.json")
    ap.add_argument("--out", default="runtime/matches_today.json")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    evs = data if isinstance(data, list) else data.get("events", data.get("matches", []))
    today = args.date or datetime.date.today().isoformat()

    out = []
    for e in evs:
        st = e.get("start_time") or ""
        active_pending = bool(e.get("active")) and not bool(e.get("closed"))
        # 当天开赛 或 活跃未关闭（跨日仍在进行/未结束，如北京时间凌晨开赛）
        if not st.startswith(today) and not active_pending:
            continue
        teams = parse_teams(e.get("title") or "")
        if len(teams) != 2:
            continue
        out.append(
            {
                "id": e.get("slug") or e.get("id"),
                "league": league_of(e.get("watchlist_group")),
                "teams": teams,
                "start_time": st,
                "end_time": e.get("end_time") or "",
                "closed": bool(e.get("closed")),
            }
        )

    Path(args.out).write_text(
        json.dumps({"date": today, "matches": out}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {args.out}: {len(out)} matches")
    for m in out:
        print(" ", m["id"], "|", m["league"], "|", " vs ".join(m["teams"]), "|", m["start_time"])


if __name__ == "__main__":
    main()
