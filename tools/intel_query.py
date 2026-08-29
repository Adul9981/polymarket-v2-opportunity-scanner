#!/usr/bin/env python3
"""弹幕情报库检索工具（英雄×队伍×选手×比赛×锚点）。

用法：
  python3 tools/intel_query.py 杰斯            # 全库关键词检索
  python3 tools/intel_query.py --entity champion jayce
  python3 tools/intel_query.py --entity team kc
  python3 tools/intel_query.py --entity match 2026-08-24_kc_shft
  python3 tools/intel_query.py --anchor 蛇女     # 锚点/灰信号检索
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"


def load(name: str) -> dict:
    p = INTEL / f"{name}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def iter_entities() -> list[tuple[str, str, dict]]:
    """返回 (类型, id, 记录) 列表，供检索。"""
    out: list[tuple[str, str, dict]] = []
    for fname, key in [
        ("champions", "champions"),
        ("compositions", "compositions"),
        ("teams", "teams"),
        ("players", "players"),
        ("leagues", "leagues"),
        ("aliases", "aliases"),
        ("rosters", "teams"),
    ]:
        data = load(fname)
        for item in data.get(key, []):
            out.append((fname.rstrip("s"), item.get("id") or item.get("team_id") or "", item))
    matches = load("matches")
    for m in matches.get("matches", []):
        out.append(("match", m.get("id", ""), m))
    return out


def search(keyword: str) -> None:
    kw = keyword.lower()
    hits = 0
    for etype, eid, rec in iter_entities():
        blob = json.dumps(rec, ensure_ascii=False).lower()
        if kw in blob:
            hits += 1
            title = rec.get("name") or rec.get("result_inferred") or rec.get("alias") or eid
            print(f"[{etype}] {eid or title}: {str(title)[:70]}")
    if hits == 0:
        print("未命中（样本不足或关键词不同，尝试昵称/英文 ID）")


def show_entity(etype: str, eid: str) -> None:
    for t, i, rec in iter_entities():
        if t == etype and (i == eid or (rec.get("alias") or "").lower() == eid.lower()):
            print(json.dumps(rec, ensure_ascii=False, indent=1))
            return
    print("未找到该实体；可用类型: champion / composition / team / player / league / match / roster / alias")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", nargs="?", help="检索关键词（中文昵称/英雄名/队伍/选手/比赛ID）")
    ap.add_argument("--entity", nargs=2, metavar=("TYPE", "ID"), help="精确查看实体")
    ap.add_argument("--anchor", help="检索锚点/灰信号（如 '蛇女'）")
    args = ap.parse_args()
    if args.entity:
        show_entity(*args.entity)
        return 0
    kw = args.anchor or args.keyword
    if not kw:
        ap.print_help()
        return 1
    search(kw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
