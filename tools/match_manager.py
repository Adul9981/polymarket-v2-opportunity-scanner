#!/usr/bin/env python3
"""Match management records: per-match status cards (series progress + order flags).

Stores one JSON per event slug under runtime/match_management/<slug>.json.
Purpose: after each match / game window, record lightweight status markers so
past sessions can answer "which game did we reach, did we place orders, did the
market ever give us a chance?" without re-reading raw action logs.

Status enums:
  game_status   : not_started | live | finished
  order_status  : none | no_opportunity | planned | cancelled | placed |
                  filled | closed
                  - none          未关注/未操作
                  - no_opportunity 没给机会（无信号/未进入场区）
                  - planned        已生成待确认计划（dry-run）
                  - cancelled      计划已取消
                  - placed         已挂单（未成交）
                  - filled         已成交
                  - closed         挂单/仓位已结束

Usage:
  python3 tools/match_manager.py init --slug <slug> --title "..." --league LPL --bo 3
  python3 tools/match_manager.py record --slug <slug> --game 1 --game-status finished \
      --winner IG --order-status no_opportunity --note "..."
  python3 tools/match_manager.py series --slug <slug> --score "IG 2-0 LNG" --finished
  python3 tools/match_manager.py show --slug <slug>
  python3 tools/match_manager.py list
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "runtime" / "match_management"

GAME_STATUSES = ("not_started", "live", "finished")
ORDER_STATUSES = ("none", "no_opportunity", "planned", "cancelled", "placed", "filled", "closed")

ORDER_LABELS = {
    "none": "未关注",
    "no_opportunity": "没给机会",
    "planned": "计划待确认",
    "cancelled": "计划取消",
    "placed": "已挂单",
    "filled": "已成交",
    "closed": "已结束",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(slug: str) -> Path:
    return DIR / f"{slug}.json"


def _load(slug: str) -> dict:
    path = _path(slug)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save(slug: str, data: dict) -> Path:
    DIR.mkdir(parents=True, exist_ok=True)
    path = _path(slug)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def cmd_init(args: argparse.Namespace) -> int:
    slug = args.slug
    if _path(slug).exists():
        print(f"[match] 已存在 {slug}，如需覆盖请先删除再 init")
        return 1
    data = {
        "slug": slug,
        "title": args.title,
        "league": args.league,
        "bo": args.bo,
        "date": args.date,
        "series": {
            "games_played": 0,
            "series_score": "",
            "series_finished": False,
            "note": "",
        },
        "games": [],
        "last_updated": _now(),
    }
    path = _save(slug, data)
    print(f"[match] 已创建比赛记录：{path}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    data = _load(args.slug)
    if not data:
        print(f"[match] 记录不存在：{args.slug}；先 init")
        return 1
    if args.game_status not in GAME_STATUSES:
        print(f"[match] game-status 必须是 {GAME_STATUSES}")
        return 1
    if args.order_status and args.order_status not in ORDER_STATUSES:
        print(f"[match] order-status 必须是 {ORDER_STATUSES}")
        return 1
    game_no = args.game
    if game_no < 1 or game_no > int(data.get("bo", 3)):
        print(f"[match] game 必须在 1-{data.get('bo', 3)} 之间")
        return 1
    games = {int(g.get("game")): g for g in data.get("games", [])}
    entry = games.get(game_no, {"game": game_no})
    entry["game_status"] = args.game_status
    if args.winner:
        entry["winner"] = args.winner
    if args.order_status:
        entry["order_status"] = args.order_status
    if args.note:
        entry["note"] = args.note
    games[game_no] = entry
    data["games"] = [games[k] for k in sorted(games)]
    data["last_updated"] = _now()
    path = _save(args.slug, data)
    print(f"[match] 已更新 G{game_no}：{path}")
    return 0


def cmd_series(args: argparse.Namespace) -> int:
    data = _load(args.slug)
    if not data:
        print(f"[match] 记录不存在：{args.slug}；先 init")
        return 1
    data.setdefault("series", {})
    if args.games_played is not None:
        data["series"]["games_played"] = args.games_played
    if args.score:
        data["series"]["series_score"] = args.score
    if args.finished is not None:
        data["series"]["series_finished"] = args.finished
    if args.note:
        data["series"]["note"] = args.note
    data["last_updated"] = _now()
    path = _save(args.slug, data)
    print(f"[match] 已更新系列赛状态：{path}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    data = _load(args.slug)
    if not data:
        print(f"[match] 记录不存在：{args.slug}")
        return 1
    series = data.get("series", {})
    print(f"比赛: {data.get('title')} [{data.get('league')}] BO{data.get('bo')}")
    print(f"日期: {data.get('date')}")
    finished = series.get("series_finished")
    print(f"系列赛: 已打 {series.get('games_played')} 局 | 比分 {series.get('series_score') or '-'} | "
          f"{'已结束' if finished else '未结束/进行中'}")
    if series.get("note"):
        print(f"系列备注: {series['note']}")
    for g in data.get("games", []):
        gs = g.get("game_status", "?")
        os_ = g.get("order_status") or "none"
        label = ORDER_LABELS.get(os_, os_)
        print(f"  G{g.get('game')}: {gs} | 胜者 {g.get('winner') or '-'} | 挂单状态 {label}"
              + (f" | {g.get('note')}" if g.get("note") else ""))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not DIR.exists():
        print("[match] 暂无记录")
        return 0
    for path in sorted(DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        series = data.get("series", {})
        print(f"{data.get('slug')} | {data.get('title','?')} | "
              f"局数 {series.get('games_played')}/{data.get('bo')} | "
              f"{'已结束' if series.get('series_finished') else '进行中'} | "
              f"比分 {series.get('series_score') or '-'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="比赛管理状态卡")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="创建比赛记录")
    p_init.add_argument("--slug", required=True)
    p_init.add_argument("--title", required=True)
    p_init.add_argument("--league", default="")
    p_init.add_argument("--bo", type=int, default=3)
    p_init.add_argument("--date", default="")
    p_init.set_defaults(func=cmd_init)

    p_rec = sub.add_parser("record", help="记录单局状态")
    p_rec.add_argument("--slug", required=True)
    p_rec.add_argument("--game", type=int, required=True)
    p_rec.add_argument("--game-status", choices=GAME_STATUSES, required=True)
    p_rec.add_argument("--winner", default="")
    p_rec.add_argument("--order-status", choices=ORDER_STATUSES, default="")
    p_rec.add_argument("--note", default="")
    p_rec.set_defaults(func=cmd_record)

    p_ser = sub.add_parser("series", help="记录系列赛总览")
    p_ser.add_argument("--slug", required=True)
    p_ser.add_argument("--games-played", type=int)
    p_ser.add_argument("--score", default="")
    p_ser.add_argument("--finished", action="store_true", default=None)
    p_ser.add_argument("--note", default="")
    p_ser.set_defaults(func=cmd_series)

    p_show = sub.add_parser("show", help="查看比赛记录")
    p_show.add_argument("--slug", required=True)
    p_show.set_defaults(func=cmd_show)

    p_list = sub.add_parser("list", help="列出所有比赛")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
