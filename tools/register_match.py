#!/usr/bin/env python3
"""比赛日程登记：往 docs/data/danmu/schedule.json 增改一条比赛窗口。

用法：
  python3 tools/register_match.py --match-id 2026-08-23_blg_al \
      --teams "BLG,AL" --start 19:00 --league LPL --streams official_660000 --status planned

切片/分析前查 schedule.json 确定时间窗与来源，保证弹幕↔比赛准确对应。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "docs" / "data" / "danmu" / "schedule.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="登记/更新一场比赛的时间窗")
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--date", default="")
    ap.add_argument("--teams", required=True, help="A,B")
    ap.add_argument("--start", required=True, help="北京时间 HH:MM")
    ap.add_argument("--league", default="")
    ap.add_argument("--streams", default="", help="来源逗号分隔")
    ap.add_argument("--status", default="planned", choices=["planned", "live", "done"])
    ap.add_argument("--result", default="")
    args = ap.parse_args()

    data = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    entry = {
        "match_id": args.match_id,
        "date": args.date or args.match_id[:10],
        "start_local": args.start,
        "league": args.league,
        "teams": [t.strip() for t in args.teams.split(",") if t.strip()],
        "streams": [s.strip() for s in args.streams.split(",") if s.strip()],
        "status": args.status,
        "result": args.result,
    }
    matches = data["matches"]
    for i, m in enumerate(matches):
        if m["match_id"] == args.match_id:
            matches[i] = entry
            break
    else:
        matches.append(entry)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    SCHEDULE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"registered {args.match_id} ({args.start}) status={args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
