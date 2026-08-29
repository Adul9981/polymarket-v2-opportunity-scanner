#!/usr/bin/env python3
"""Fetch and slice Polymarket series comments into the intel knowledge base.

Intel-collection chain (read-only; fully isolated from execution).

Why series-level: esports comments are attached to the sport "Series" entity,
not to individual events. GET /events/{id} returns commentCount=0 for esports
while the Series holds thousands of comments. Rules: knowledge/COMMENT_ANALYSIS_RULES.md.

Subcommands:
  fetch  Paginate GET /comments/keyset (Series) until --since is covered; save
         raw JSON under docs/data/snapshots/comments_batch/.
  slice  For each event slug, slice fetched raw comments into the event window
         [startTime-10min, endDate+30min] under docs/data/snapshots/<slug>/comments/
         and print a keyword-flagged summary (pause/chronobreak/fix/roster/50-50...).

Known series ids:
  lol  = 10311 (league-of-legends)   cs2 = 10310 (counter-strike)
  dota = 10309 (dota-2)

Usage:
  python3 tools/fetch_series_comments.py fetch --series lol --days 5
  python3 tools/fetch_series_comments.py slice --series lol --events \
      lol-t1-dnf-2026-08-17,lol-drxc-hle-2026-08-17
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/Users/ad/Documents/polymarket")
SNAPSHOT_ROOT = ROOT / "docs" / "data" / "snapshots"
BATCH_ROOT = SNAPSHOT_ROOT / "comments_batch"
GAMMA = "https://gamma-api.polymarket.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
SERIES = {
    "lol": (10311, "league-of-legends"),
    "cs2": (10310, "counter-strike"),
    "dota": (10309, "dota-2"),
}

KEYWORDS = {
    "pause/延迟": ("pause", "delay", "technical", "lag", "slow", "restart", "stuck"),
    "chronobreak/回滚": ("chronobreak", "rollback", "glitch", "rewind", "reverse"),
    "假赛/作弊": ("fix", "scam", "shady", "cheat", "rigged", "match fixing"),
    "名单/阵容": ("roster", "lineup", "academy", "challengers", "sub", "benched"),
    "规则/50-50": ("50-50", "cancel", "postpone", "resolve", "settle", "rule"),
}


def http_json(url: str, tries: int = 4) -> Any:
    last: Exception | None = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001 - network retry loop
            last = exc
            time.sleep(1.5)
    raise RuntimeError(f"GET {url} failed after {tries} tries: {last}")


def resolve_series(name: str) -> tuple[int, str]:
    if name in SERIES:
        return SERIES[name]
    if name.isdigit():
        return int(name), f"series-{name}"
    raise SystemExit(f"未知系列：{name}（可选 {', '.join(SERIES)} 或 series id）")


def fetch_comments_since(
    sid: int, since: datetime, max_pages: int = 60
) -> list[dict[str, Any]]:
    """Paginate /comments/keyset (Series) until `since` is covered."""
    since_s = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor: str | None = None
    rows: list[dict[str, Any]] = []
    pages = 0
    while pages < max_pages:
        q: dict[str, Any] = {
            "parent_entity_type": "Series",
            "parent_entity_id": sid,
            "limit": 100,
            "order": "createdAt",
            "ascending": "false",
        }
        if cursor:
            q["after_cursor"] = cursor
        url = f"{GAMMA}/comments/keyset?{urllib.parse.urlencode(q)}"
        data = http_json(url)
        page = data.get("comments") or []
        rows.extend(page)
        pages += 1
        if not page:
            break
        oldest = page[-1].get("createdAt", "")
        cursor = data.get("next_cursor")
        if oldest < since_s or not cursor:
            break
    rows.sort(key=lambda c: c.get("createdAt", ""))
    return rows


def cmd_fetch(args: argparse.Namespace) -> int:
    sid, sslug = resolve_series(args.series)
    since = (
        datetime.now(timezone.utc) - timedelta(days=args.days)
        if args.days
        else datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    )
    rows = fetch_comments_since(sid, since, max_pages=args.max_pages)
    pages = max(1, (len(rows) + 99) // 100)
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)
    out = BATCH_ROOT / f"{sslug}_comments_raw.json"
    payload = {
        "series_id": sid,
        "series_slug": sslug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "since": since.isoformat(),
        "pages": pages,
        "comments": rows,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"series {sslug} (id={sid}): {len(rows)} 条评论，{pages} 页 -> {out}")
    return 0


def _flag(body: str) -> list[str]:
    b = body.lower()
    hits = []
    for label, kws in KEYWORDS.items():
        if any(k in b for k in kws):
            hits.append(label)
    return hits


def cmd_slice(args: argparse.Namespace) -> int:
    sid, sslug = resolve_series(args.series)
    raw_path = Path(args.raw) if args.raw else BATCH_ROOT / f"{sslug}_comments_raw.json"
    if not raw_path.exists():
        raise SystemExit(f"未找到原始评论文件：{raw_path}（先运行 fetch）")
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = payload["comments"]
    total = 0
    for slug in args.events.split(","):
        slug = slug.strip()
        if not slug:
            continue
        ev = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
        if not ev:
            print(f"[skip] {slug}: 事件不存在")
            continue
        e = ev[0]
        start = datetime.fromisoformat(e["startTime"].replace("Z", "+00:00")) - timedelta(minutes=10)
        end = datetime.fromisoformat(e["endDate"].replace("Z", "+00:00")) + timedelta(minutes=30)
        win = [
            c
            for c in rows
            if start <= datetime.fromisoformat(c["createdAt"].replace("Z", "+00:00")) <= end
        ]
        if not win:
            print(f"[empty] {slug}: 窗口 {start:%m-%d %H:%M}~{end:%m-%d %H:%M} 无评论")
            continue
        out_dir = SNAPSHOT_ROOT / slug / "comments"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "comments_raw.json").write_text(
            json.dumps(win, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        total += len(win)
        flags: dict[str, int] = {}
        authors: dict[str, int] = {}
        for c in win:
            for f in _flag(c.get("body", "")):
                flags[f] = flags.get(f, 0) + 1
            name = (c.get("profile") or {}).get("name") or "?"
            authors[name] = authors.get(name, 0) + 1
        top = sorted(authors.items(), key=lambda x: -x[1])[:5]
        print(
            f"[ok] {slug}（{e['title'][:36]}）: {len(win)} 条评论 "
            f"| 关键词 {flags if flags else '无'} | 活跃 {top}"
        )
        (out_dir / "README.md").write_text(
            f"# 评论切片 {slug}\n\n窗口：{start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M} (UTC)\n"
            f"评论数：{len(win)}\n关键词命中：{flags}\n活跃评论者：{top}\n"
            f"来源：{raw_path.name}\n",
            encoding="utf-8",
        )
    print(f"共切片 {total} 条评论 -> {SNAPSHOT_ROOT}/<slug>/comments/")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Polymarket series 评论批量抓取/切片（只读）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="抓取 series 评论")
    f.add_argument("--series", required=True, help="lol / cs2 / dota 或 series id")
    f.add_argument("--days", type=int, default=None, help="回溯天数（与 --since 二选一）")
    f.add_argument("--since", default=None, help="起始 UTC ISO8601，如 2026-08-13T00:00:00Z")
    f.add_argument("--max-pages", type=int, default=60, help="安全翻页上限")
    f.set_defaults(func=cmd_fetch)
    s = sub.add_parser("slice", help="按比赛窗口切片")
    s.add_argument("--series", required=True, help="lol / cs2 / dota 或 series id")
    s.add_argument("--events", required=True, help="逗号分隔的比赛 slug")
    s.add_argument("--raw", default=None, help="原始评论文件（默认 comments_batch 内）")
    s.set_defaults(func=cmd_slice)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
