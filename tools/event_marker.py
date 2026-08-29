#!/usr/bin/env python3
"""Event marker tool v1: record match window markers for later data slicing.

打点程序第一版：轮询 Polymarket 公开赛事，为白名单比赛记录四个时间点：

    event_start  比赛开始
    game_start   每个小局开始（由 Game/Map Winner 子市场状态推断）
    game_end     每个小局结束（子市场 closed）
    event_end    整场结算（事件 closed 或整场胜者市场 closed）

产物：
    runtime/markers/YYYY-MM-DD.jsonl  一行一个点
    runtime/markers/state.json        去重状态（重启不重复打点）

安全：只读公开数据；不读私钥；不下单；不调用执行链。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKER_DIR = ROOT / "runtime" / "markers"
GAMMA = "https://gamma-api.polymarket.com"

MARKER_TYPES = ("event_start", "game_start", "game_end", "event_end")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def http_json(url: str, params: dict[str, Any] | None = None) -> Any:
    import urllib.parse
    import urllib.request

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "polymarket-event-marker/0.1"},
    )
    last_exc: Exception | None = None
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:  # noqa: S310 - fixed public API
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry public data reads
            last_exc = exc
    raise RuntimeError(f"公共数据接口请求失败: {last_exc}") from last_exc


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10_000_000_000:
            ts /= 1000
        return datetime.fromtimestamp(ts, timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def event_start_time(event: dict[str, Any]) -> datetime | None:
    # Gamma 语义：startTime = 真实开赛时间；startDate = 挂牌/创建时间。
    for key in ("startTime", "gameStartTime", "startDate", "start_date"):
        parsed = parse_time(event.get(key))
        if parsed:
            return parsed
    return None


def market_title(market: dict[str, Any], event: dict[str, Any]) -> str:
    return str(
        market.get("groupItemTitle")
        or market.get("question")
        or market.get("title")
        or event.get("title")
        or ""
    )


def game_index_from_market(market: dict[str, Any], event: dict[str, Any]) -> int | None:
    """Return game/map number for a sub-market like "Game 1 Winner", else None."""
    title = market_title(market, event)
    slug = str(market.get("slug") or "")
    haystack = f"{title} {slug}".lower()
    if "match" in haystack or "series" in haystack or "moneyline" in haystack:
        return None
    match = re.search(r"(?:game|map)\s*([1-9])", haystack)
    if match:
        return int(match.group(1))
    return None


def is_game_market(market: dict[str, Any], event: dict[str, Any]) -> bool:
    title = market_title(market, event).lower()
    if not title or any(bad in title for bad in ("match winner", "series winner", "moneyline")):
        return False
    return game_index_from_market(market, event) is not None


def is_series_market(market: dict[str, Any], event: dict[str, Any]) -> bool:
    title = market_title(market, event).lower()
    haystack = f"{title} {str(market.get('slug') or '')} {str(market.get('sportsMarketType') or '')}".lower()
    return "moneyline" in haystack or "match winner" in haystack or "series winner" in haystack


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = load_json(path)
            if isinstance(data.get("markers"), dict):
                return data
        except Exception:  # noqa: BLE001 - corrupt state resets safely
            pass
    return {"version": 1, "markers": {}}


def save_state(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)


def epoch_value(timestamp: float, unit: str) -> int:
    if unit == "ns":
        return int(timestamp * 1_000_000_000)
    if unit == "s":
        return int(timestamp)
    return int(timestamp * 1000)


def emit(
    markers: list[dict[str, Any]],
    state: dict[str, Any],
    event: dict[str, Any],
    market: dict[str, Any] | None,
    marker_type: str,
    now: datetime,
    unit: str,
    source: str,
    game_index: int | None = None,
) -> None:
    market_slug = str((market or {}).get("slug") or "")
    key = f"{event.get('slug')}|{market_slug}|{marker_type}"
    if key in state["markers"]:
        return
    ts_iso = now.isoformat()
    line = {
        "ts": epoch_value(now.timestamp(), unit),
        "ts_iso": ts_iso,
        "event_slug": str(event.get("slug") or ""),
        "event_title": str(event.get("title") or ""),
        "market_slug": market_slug,
        "market_title": market_title(market, event) if market else "",
        "marker_type": marker_type,
        "game_index": game_index,
        "source": source,
    }
    markers.append(line)
    state["markers"][key] = {"ts_iso": ts_iso}


def mark_event(
    event: dict[str, Any],
    now: datetime,
    state: dict[str, Any],
    markers: list[dict[str, Any]],
    unit: str,
    source: str,
) -> None:
    if not isinstance(event, dict) or not event.get("slug"):
        return
    closed = bool(event.get("closed"))
    start = event_start_time(event)

    if not closed and start is not None and now >= start:
        emit(markers, state, event, None, "event_start", now, unit, source)

    for market in event.get("markets") or []:
        if not isinstance(market, dict):
            continue
        if is_game_market(market, event):
            idx = game_index_from_market(market, event)
            m_closed = bool(market.get("closed"))
            if not m_closed and market.get("active") is not False:
                emit(markers, state, event, market, "game_start", now, unit, source, game_index=idx)
            if m_closed:
                emit(markers, state, event, market, "game_end", now, unit, source, game_index=idx)

    series_closed = any(
        isinstance(market, dict) and bool(market.get("closed"))
        for market in event.get("markets") or []
        if isinstance(market, dict) and is_series_market(market, event)
    )
    if closed or series_closed:
        emit(markers, state, event, None, "event_end", now, unit, source)


def fetch_event_by_slug(slug: str) -> dict[str, Any]:
    data = http_json(f"{GAMMA}/events/slug/{slug}")
    return data if isinstance(data, dict) else {}


def load_snapshots(path: Path) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Load offline replay file: {"snapshots": [{"simulated_now": iso, "events": [...]}]}."""
    data = load_json(path)
    raw_snapshots = data.get("snapshots") if isinstance(data, dict) else data
    if not isinstance(raw_snapshots, list):
        raise ValueError("--event-file 需要 {\"snapshots\": [{\"simulated_now\": iso, \"events\": [...]}]}")
    snapshots: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for snap in raw_snapshots:
        if not isinstance(snap, dict):
            continue
        events = snap.get("events")
        if not isinstance(events, list):
            continue
        snapshots.append((snap, [e for e in events if isinstance(e, dict)]))
    return snapshots


def run_pass(
    events: list[dict[str, Any]],
    now: datetime,
    state: dict[str, Any],
    markers: list[dict[str, Any]],
    unit: str,
    source: str,
) -> None:
    for event in events:
        mark_event(event, now, state, markers, unit, source)


def list_scope_events(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Live mode: fetch active events, optionally filtered by watchlist or explicit slugs."""
    from market_scanner import list_live_events

    if args.event_slug:
        events: list[dict[str, Any]] = []
        for slug in [s.strip() for s in args.event_slug.split(",") if s.strip()]:
            event = fetch_event_by_slug(slug)
            if event:
                events.append(event)
        return events
    if args.no_watchlist:
        events, _diag = list_live_events(args.live_limit, args.live_pages, "", None)
        return events
    watchlist = load_json(ROOT / "config" / "market_watchlist.json")
    events, _diag = list_live_events(args.live_limit, args.live_pages, "", watchlist)
    return events


def append_lines(path: Path, lines: list[dict[str, Any]]) -> None:
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Event marker tool v1")
    parser.add_argument("--watch", action="store_true", help="Keep polling; default is one pass.")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval seconds in watch mode.")
    parser.add_argument("--event-slug", default="", help="Only these event slugs (comma separated).")
    parser.add_argument("--no-watchlist", action="store_true", help="Scan all active events, skip watchlist filter.")
    parser.add_argument("--live-limit", type=int, default=100, help="Events per page in live mode.")
    parser.add_argument("--live-pages", type=int, default=5, help="Pages to scan in live mode.")
    parser.add_argument("--marker-dir", default=str(DEFAULT_MARKER_DIR), help="Marker output directory.")
    parser.add_argument("--time-unit", choices=("ms", "s", "ns"), default="ms", help="Epoch unit in marker output.")
    parser.add_argument("--event-file", default="", help="Offline replay JSON file (no network).")
    parser.add_argument("--simulated-now", default="", help="Fixed now (ISO) for replay.")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-marker stdout.")
    args = parser.parse_args()

    marker_dir = Path(args.marker_dir)
    state_path = marker_dir / "state.json"
    state = load_state(state_path)

    if args.event_file:
        snapshots = load_snapshots(Path(args.event_file))
        for snap, events in snapshots:
            now = parse_time(snap.get("simulated_now") or args.simulated_now) or datetime.now(timezone.utc)
            markers: list[dict[str, Any]] = []
            run_pass(events, now, state, markers, args.time_unit, "event-file")
            append_lines(marker_dir / f"{now:%Y-%m-%d}.jsonl", markers)
            if not args.quiet:
                for m in markers:
                    print(json.dumps(m, ensure_ascii=False))
        save_state(state_path, state)
        return 0

    while True:
        try:
            now = datetime.now(timezone.utc)
            events = list_scope_events(args)
            tracked_slugs = {
                key.split("|")[0] for key in state["markers"] if key.split("|")[0]
            }
            for slug in tracked_slugs:
                event = fetch_event_by_slug(slug)
                if event:
                    events.append(event)
            markers: list[dict[str, Any]] = []
            run_pass(events, now, state, markers, args.time_unit, "gamma-poll")
            append_lines(marker_dir / f"{now:%Y-%m-%d}.jsonl", markers)
            if not args.quiet:
                for m in markers:
                    print(json.dumps(m, ensure_ascii=False))
            save_state(state_path, state)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[event_marker] pass failed: {exc}", file=sys.stderr)
        if not args.watch:
            break
        time.sleep(max(5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
