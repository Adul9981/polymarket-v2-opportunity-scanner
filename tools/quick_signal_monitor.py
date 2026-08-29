#!/usr/bin/env python3
"""One-minute lightweight signal monitor (read-only).

Polls every ~60s:
  1. all Esports-tagged events (tag_id from watchlist config),
  2. watchlist + time-window filter (real match time via market gameStartTime),
  3. current prices from Gamma outcomePrices (already in event payload),
  4. followed winner accounts' trades in the last N minutes.

Emits ALERT lines and writes runtime/quick_signal_latest.json + a rolling log.
Complements the 5-minute deep pipeline scan (books/liquidity/bar monitors).
Never places orders.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import market_scanner as ms  # noqa: E402
import follow_winner_accounts as fw  # noqa: E402

GAMMA = ms.GAMMA


def fetch_esports_events(watchlist: dict[str, Any], max_pages: int = 10) -> list[dict[str, Any]]:
    cfg = (watchlist or {}).get("esports") or {}
    tag_id = str(cfg.get("tag_id") or "64")
    events: list[dict[str, Any]] = []
    for page in range(max_pages):
        data = ms.http_json(
            f"{GAMMA}/events",
            {
                "tag_id": tag_id,
                "closed": "false",
                "archived": "false",
                "limit": 100,
                "offset": page * 100,
                "order": "startDate",
                "ascending": "false",
            },
        )
        if not isinstance(data, list) or not data:
            break
        events.extend(data)
        if len(data) < 100:
            break
    return events


def current_prices(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Winner/moneyline markets with current outcome prices from the payload."""
    out: list[dict[str, Any]] = []
    for m in event.get("markets") or []:
        if not isinstance(m, dict) or not ms.is_live_winner_market(m, event):
            continue
        try:
            outcomes = ms.parse_json_array(m.get("outcomes"))
            prices = ms.parse_json_array(m.get("outcomePrices"))
        except Exception:  # noqa: BLE001
            continue
        if len(outcomes) != len(prices):
            continue
        for o, p in zip(outcomes, prices):
            try:
                px = float(p)
            except (TypeError, ValueError):
                continue
            out.append(
                {
                    "market": str(m.get("groupItemTitle") or m.get("question") or ""),
                    "market_slug": str(m.get("slug") or ""),
                    "outcome": str(o),
                    "price": px,
                }
            )
    return out


def detect(events: list[dict[str, Any]], watchlist: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for ev in events:
        ok, group = ms.watchlist_match(ev, watchlist)
        if not ok:
            continue
        in_window, status = ms.event_time_status(ev, watchlist)
        if not in_window:
            continue
        prices = current_prices(ev)
        deep = [p for p in prices if 0.01 <= p["price"] <= 0.15]
        dips = [
            p
            for p in prices
            if 0.40 <= p["price"] <= 0.52 and any(x["market"] == p["market"] and x["price"] >= 0.60 for x in prices)
        ]
        ev_info = {
            "event": str(ev.get("title") or ""),
            "slug": str(ev.get("slug") or ""),
            "start": ms.event_start_time(ev).isoformat() if ms.event_start_time(ev) else None,
            "status": status,
            "group": (group or {}).get("name"),
            "deep": deep,
            "dips": dips,
        }
        alerts.append(ev_info)
    return alerts


def recent_winner_trades(minutes: int = 10) -> list[dict[str, Any]]:
    since_ts = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
    rows: list[dict[str, Any]] = []
    for acc in fw.load_followed_accounts(12):
        try:
            trades = fw.fetch_trades(acc["address"], since_ts)
        except Exception:  # noqa: BLE001
            continue
        for t in trades:
            if t.get("side") != "BUY":
                continue
            try:
                if float(t.get("price") or 1) > 0.75:
                    continue  # redemption/reward buys are not fresh entries
            except (TypeError, ValueError):
                continue
            slug = str(t.get("eventSlug") or "")
            if not slug:
                continue
            try:
                usd = round(float(t.get("price") or 0) * float(t.get("size") or 0), 2)
            except (TypeError, ValueError):
                usd = 0.0
            rows.append(
                {
                    "account": acc["name"],
                    "event": slug,
                    "title": str(t.get("title") or ""),
                    "outcome": str(t.get("outcome") or ""),
                    "price": t.get("price"),
                    "size": t.get("size"),
                    "usd": usd,
                    "ts": int(t.get("timestamp") or 0),
                }
            )
        time.sleep(0.3)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="One-minute lightweight signal monitor.")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--winner-minutes", type=int, default=10)
    args = parser.parse_args()

    watchlist = ms.load_json(ms.DEFAULT_WATCHLIST_CONFIG)
    log_path = ROOT / "runtime" / "logs" / "quick_signal.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        started = datetime.now(timezone.utc)
        try:
            events = fetch_esports_events(watchlist)
            snapshot = detect(events, watchlist)
            winners = recent_winner_trades(args.winner_minutes)

            payload = {
                "ts": started.isoformat(),
                "events_seen": len(events),
                "watchlist_snapshot": snapshot,
                "winner_buys_10m": winners,
            }
            (ROOT / "runtime" / "quick_signal_latest.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

            deep_events = [s for s in snapshot if s["deep"]]
            dip_events = [s for s in snapshot if s["dips"]]
            if deep_events:
                for s in deep_events:
                    line = f"[ALERT 深水] {s['event']} {s['status']} deep={s['deep']}"
                    print(line)
                    log_path.open("a", encoding="utf-8").write(f"{started.isoformat()} {line}\n")
            if dip_events:
                for s in dip_events:
                    line = f"[ALERT 回撤] {s['event']} {s['status']} dips={s['dips']}"
                    print(line)
                    log_path.open("a", encoding="utf-8").write(f"{started.isoformat()} {line}\n")
            if winners:
                for w in winners[:10]:
                    line = (
                        f"[WIN] {w['account']} 买 {w['outcome']} @ {w['price']} "
                        f"${w['usd']} | {w['title']}"
                    )
                    print(line)
                    log_path.open("a", encoding="utf-8").write(f"{started.isoformat()} {line}\n")
            print(
                f"[quick] {started.strftime('%H:%M:%S')} events={len(events)} "
                f"deep={len(deep_events)} dips={len(dip_events)} winner_buys={len(winners)}"
            )
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[quick] cycle failed: {exc}")
        if args.once:
            break
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        time.sleep(max(5, args.interval - elapsed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
