#!/usr/bin/env python3
"""多路直播间共振检测：判断某关键词/事件在几路弹幕中同时出现。

规则：单路=低置信；两路及以上同窗口命中=升置信（高）。
用法：
  python3 tools/route_resonance.py 蛇女 --date 2026-08-24 --routes shuoshuo_323444,official_660000
  python3 tools/route_resonance.py 明牌假赛 --date 2026-08-24 --routes shuoshuo_323444 --start 01:50 --end 02:00
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data" / "danmu" / "huya"
TZ = timezone(timedelta(hours=8))


def load_route(route: str, date: str) -> list[dict]:
    p = DATA / f"{date}_{route}.jsonl"
    rows = []
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def in_window(ts: float, start: str, end: str) -> bool:
    t = datetime.fromtimestamp(ts, TZ).strftime("%H:%M:%S")
    if end < start:  # 跨零点
        return t >= start or t <= end
    return start <= t <= end


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", help="共振关键词")
    ap.add_argument("--date", default=datetime.now(TZ).strftime("%Y-%m-%d"))
    ap.add_argument("--routes", required=True, help="逗号分隔的路源（如 shuoshuo_323444,official_660000）")
    ap.add_argument("--start", default="00:00:00")
    ap.add_argument("--end", default="23:59:59")
    args = ap.parse_args()
    kw = args.keyword.lower()
    total_hits = 0
    hits_by_route = {}
    for route in [r.strip() for r in args.routes.split(",") if r.strip()]:
        rows = load_route(route, args.date)
        hits = [
            r for r in rows
            if kw in str(r.get("text", "")).lower() and in_window(r["ts"], args.start, args.end)
        ]
        hits_by_route[route] = len(hits)
        total_hits += len(hits)
    active = {r: c for r, c in hits_by_route.items() if c > 0}
    level = "高（两路及以上共振）" if len(active) >= 2 else ("低（单路）" if len(active) == 1 else "无命中")
    print(f"关键词「{args.keyword}」 {args.date} {args.start}-{args.end}")
    for r, c in hits_by_route.items():
        print(f"  {r}: {c} 条")
    print(f"命中路数: {len(active)} · 共振等级: {level} · 合计 {total_hits} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
