#!/usr/bin/env python3
"""Pre-match / in-play comment intel for the task-2 scan pipeline.

Intel-collection chain (read-only; fully isolated from execution).

Input: the scanner's watchlist event JSON (runtime/watchlist_events.json).
For every whitelisted esports event that is upcoming within --pre-minutes or
currently in play, this tool:
  1. fetches the sport-series comments (LoL=10311 / CS2=10310 / DOTA=10309,
     with a gamma fallback for other games);
  2. slices the event window [start-90min, end+30min];
  3. flags 名单/暂停/回滚/假赛/50-50 keyword hits and top commenters;
  4. writes runtime/comment_intel.json + a markdown report and prints alerts.

Rules: knowledge/COMMENT_ANALYSIS_RULES.md (S1-S3: keyword hits are auxiliary
reference markers, never standalone signals; alerts are for pre-match rosters
and in-play pause/rollback/fix chatter only).

Usage:
  python3 tools/comment_intel.py --events-json runtime/watchlist_events.json
  python3 tools/comment_intel.py --events-json ... --report reports/comment_intel_2026-08-17.md
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/Users/ad/Documents/polymarket")
sys.path.insert(0, str(ROOT / "tools"))
from fetch_series_comments import (  # noqa: E402
    GAMMA,
    SERIES,
    fetch_comments_since,
    http_json,
)

DEFAULT_EVENTS_JSON = ROOT / "runtime" / "watchlist_events.json"
GAME_PREFIX_SERIES = {name: sid for name, (sid, _slug) in SERIES.items()}
ALERT_LABELS = ("名单/阵容", "pause/延迟", "chronobreak/回滚", "假赛/作弊", "规则/50-50")


def series_id_for_event(slug: str) -> int | None:
    """Prefix-map known games; fall back to gamma event market series."""
    for prefix, sid in GAME_PREFIX_SERIES.items():
        if slug.startswith(prefix):
            return sid
    try:
        events = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
        if events:
            for m in events[0].get("markets") or []:
                for s in m.get("series") or []:
                    if s.get("id"):
                        return int(s["id"])
    except Exception:  # noqa: BLE001 - best-effort fallback
        return None
    return None


def _phase(start: datetime, end: datetime | None, now: datetime) -> str:
    if start > now:
        return "pre_match"
    if end is None or end >= now:
        return "in_play"
    return "finished"


def _slice_window(
    rows: list[dict[str, Any]],
    start: datetime,
    end: datetime | None,
    pre_min: int,
    post_min: int,
) -> list[dict[str, Any]]:
    lo = start - timedelta(minutes=pre_min)
    hi = (end + timedelta(minutes=post_min)) if end else (datetime.now(timezone.utc) + timedelta(minutes=post_min))
    return [
        c
        for c in rows
        if lo <= datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00")) <= hi
    ]


def _flatten(body: str, limit: int = 150) -> str:
    return " ".join(body.split())[:limit]


def build_event_intel(
    event: dict[str, Any],
    series_cache: dict[int, tuple[list[dict[str, Any]], int | None]],
    now: datetime,
    pre_min: int,
    post_min: int,
) -> dict[str, Any] | None:
    slug = str(event.get("slug") or "")
    start_s = event.get("start_time")
    end_s = event.get("end_time")
    if not slug or not start_s:
        return None
    start = datetime.fromisoformat(start_s)
    end = datetime.fromisoformat(end_s) if end_s else None
    phase = _phase(start, end, now)
    if phase == "finished":
        return None
    if phase == "pre_match" and start > now + timedelta(minutes=pre_min):
        return None
    if phase == "in_play" and start < now - timedelta(hours=6):
        return None
    sid = series_id_for_event(slug)
    if sid is None:
        return {
            "slug": slug,
            "title": str(event.get("title") or ""),
            "start_time": start_s,
            "phase": phase,
            "series_id": None,
            "comment_count": 0,
            "keyword_hits": {},
            "top_commenters": [],
            "alerts": [],
            "samples": [],
            "note": "未知游戏系列，跳过评论情报",
        }
    rows, series_count = series_cache.get(sid, ([], None))
    win = _slice_window(rows, start, end, pre_min, post_min)
    hits: dict[str, int] = {}
    authors: dict[str, int] = {}
    samples: list[dict[str, str]] = []
    for c in win:
        body = c.get("body", "")
        for label, kws in (
            ("名单/阵容", ("roster", "lineup", "academy", "challengers", "sub", "benched")),
            ("pause/延迟", ("pause", "delay", "technical", "lag", "slow", "restart", "stuck")),
            ("chronobreak/回滚", ("chronobreak", "rollback", "glitch", "rewind", "reverse")),
            ("假赛/作弊", ("fix", "scam", "shady", "cheat", "rigged", "match fixing")),
            ("规则/50-50", ("50-50", "cancel", "postpone", "resolve", "settle", "rule")),
        ):
            if any(k in body.lower() for k in kws):
                hits[label] = hits.get(label, 0) + 1
                if len(samples) < 3:
                    samples.append(
                        {
                            "time": c.get("createdAt", ""),
                            "author": (c.get("profile") or {}).get("name") or "?",
                            "body": _flatten(body),
                        }
                    )
        name = (c.get("profile") or {}).get("name") or "?"
        authors[name] = authors.get(name, 0) + 1
    alerts = [label for label in ALERT_LABELS if hits.get(label)]
    note = None
    if not rows and series_count is not None and series_count > 0:
        note = f"series 有 {series_count} 条评论但本次抓取为空（工具/接口异常待查）"
    elif not rows:
        note = "series 无评论（可能游戏讨论量少）"
    return {
        "slug": slug,
        "title": str(event.get("title") or ""),
        "start_time": start_s,
        "phase": phase,
        "series_id": sid,
        "comment_count": len(win),
        "keyword_hits": hits,
        "top_commenters": sorted(authors.items(), key=lambda x: -x[1])[:5],
        "alerts": alerts,
        "samples": samples,
        "note": note,
    }


def write_report(path: Path, events: list[dict[str, Any]], generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 评论区情报（赛前 / 赛中提示）",
        "",
        f"生成时间：{generated_at}",
        "",
        "说明：关键词命中是辅助参考标记（名单/暂停/回滚/假赛/50-50），",
        "不构成独立信号；升级为信号需按 COMMENT_ANALYSIS_RULES.md S1-S3 判定。",
        "",
        "## 提示",
        "",
    ]
    alerted = [e for e in events if e.get("alerts")]
    if not alerted:
        lines.append("暂无关键词提示。")
    for e in alerted:
        lines.append(
            f"- **{e['title']}**（{e['phase']}）命中 "
            f"{', '.join(f'{k}×{v}' for k, v in e['keyword_hits'].items())}"
        )
        for s in e["samples"]:
            lines.append(f"  - {s['time'][:16]} @{s['author']}: {s['body']}")
    lines.extend(["", "## 全部窗口", "", "| 比赛 | 阶段 | 评论数 | 关键词 | 活跃评论者 |", "| --- | --- | --- | --- | --- |"])
    for e in events:
        hits = "、".join(f"{k}×{v}" for k, v in e["keyword_hits"].items()) or "-"
        top = ", ".join(a for a, _ in e["top_commenters"][:3]) or "-"
        lines.append(
            f"| {e['title']} | {e['phase']} | {e['comment_count']} | {hits} | {top} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="赛前/赛中评论区情报（只读）")
    parser.add_argument("--events-json", default=str(DEFAULT_EVENTS_JSON))
    parser.add_argument("--report", default="")
    parser.add_argument("--pre-minutes", type=int, default=90, help="赛前抓取窗口（开赛前 N 分钟内）")
    parser.add_argument("--post-minutes", type=int, default=30, help="赛后保留窗口")
    parser.add_argument("--max-in-play-hours", type=int, default=6)
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    events_path = Path(args.events_json)
    if not events_path.exists():
        print(f"[comment-intel] 未找到 {events_path}（先运行扫描）", file=sys.stderr)
        return 2
    data = json.loads(events_path.read_text(encoding="utf-8"))
    events = data.get("events") or []
    if not events:
        print("[comment-intel] 扫描事件列表为空，跳过评论情报")
        return 0
    now = datetime.now(timezone.utc)
    targets: list[dict[str, Any]] = []
    for e in events:
        try:
            start = datetime.fromisoformat(e.get("start_time"))
        except (TypeError, ValueError):
            continue
        end_s = e.get("end_time")
        end = datetime.fromisoformat(end_s) if end_s else None
        phase = _phase(start, end, now)
        if phase == "finished":
            continue
        if phase == "pre_match" and start > now + timedelta(minutes=args.pre_minutes):
            continue
        if phase == "in_play" and start < now - timedelta(hours=args.max_in_play_hours):
            continue
        targets.append(e)
    if not targets:
        print("[comment-intel] 当前无赛前/进行中白名单比赛，跳过评论情报")
        return 0

    series_cache: dict[int, tuple[list[dict[str, Any]], int | None]] = {}
    out_events: list[dict[str, Any]] = []
    for e in targets:
        slug = str(e.get("slug") or "")
        sid = series_id_for_event(slug)
        if sid is not None and sid not in series_cache:
            since = min(
                datetime.fromisoformat(x.get("start_time"))
                for x in targets
                if x.get("start_time")
            ) - timedelta(hours=2)
            try:
                count = None
                try:
                    count_resp = http_json(f"{GAMMA}/series/{sid}/comments/count")
                    count = int(count_resp.get("count") or 0)
                except Exception:  # noqa: BLE001
                    count = None
                rows = fetch_comments_since(sid, since, max_pages=args.max_pages)
                series_cache[sid] = (rows, count)
            except Exception as exc:  # noqa: BLE001
                print(f"[comment-intel] series {sid} 抓取失败: {exc}", file=sys.stderr)
                series_cache[sid] = ([], None)
        info = build_event_intel(e, series_cache, now, args.pre_minutes, args.post_minutes)
        if info:
            out_events.append(info)

    generated_at = now.isoformat()
    payload = {
        "generated_at": generated_at,
        "events_json": str(events_path),
        "window": {
            "pre_minutes": args.pre_minutes,
            "post_minutes": args.post_minutes,
            "max_in_play_hours": args.max_in_play_hours,
        },
        "events": out_events,
    }
    out_path = ROOT / "runtime" / "comment_intel.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    report_path = (
        Path(args.report)
        if args.report
        else ROOT / "reports" / f"comment_intel_{now:%Y-%m-%d}.md"
    )
    write_report(report_path, out_events, generated_at)
    for e in out_events:
        if e.get("alerts"):
            print(
                f"⚠ {e['title']}（{e['phase']}）评论 {e['comment_count']} 条，"
                f"命中 {', '.join(e['alerts'])}"
            )
            for s in e["samples"]:
                print(f"   {s['time'][:16]} @{s['author']}: {s['body']}")
        elif not args.quiet:
            print(f"· {e['title']}（{e['phase']}）评论 {e['comment_count']} 条（无关键词命中）")
    print(f"[comment-intel] 报告: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
