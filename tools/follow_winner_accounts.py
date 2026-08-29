#!/usr/bin/env python3
"""Long-term tracking of winning/profitable esports accounts (read-only).

Pulls recent public trades for curated "quality" accounts (deep-water
machines from the fake-match forensics review), enriches them with market
info, and appends to a rolling JSONL for long-term study and follow-up.

2026-08-16: user request — study their strategies AND the markets/patterns
they trade; keep following them long-term. Their buying is a mispricing
signal that helps filter "bad odds that are genuinely bad" vs "bad odds
that are mispriced".

Read-only: never places orders, never touches private keys.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_API = "https://data-api.polymarket.com"
REGISTRY = ROOT / "docs" / "forensics" / "data" / "lol-gx-vit-2026-08-14" / "address_registry.csv"
TRACK_DIR = ROOT / "docs" / "forensics" / "data" / "accounts"
TRACK_FILE = TRACK_DIR / "followed_trades.jsonl"
SUMMARY_DIR = ROOT / "runtime"


def http_json(url: str, tries: int = 5) -> Any:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (polymarket-account-follow/0.1)"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:  # noqa: S310 - fixed public API
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retry public data reads
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"data-api 请求失败: {last}")


def load_followed_accounts(limit: int = 12) -> list[dict[str, str]]:
    """Top profitable deep-water accounts from the forensics registry."""
    if not REGISTRY.exists():
        return []
    accounts: list[dict[str, str]] = []
    with REGISTRY.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tags = str(row.get("tags") or "")
            if any(k in tags for k in ("尘埃", "E10", "E11", "E12")):
                continue
            try:
                est = float(row.get("est") or 0)
            except ValueError:
                est = 0.0
            if "A_深水机器" not in tags and "I_赛前大额" not in tags and est < 3000:
                continue
            accounts.append(
                {
                    "address": str(row.get("address") or "").strip(),
                    "name": str(row.get("name") or "").strip(),
                    "tags": tags,
                    "est": str(round(est, 2)),
                }
            )
    accounts.sort(key=lambda a: float(a["est"]), reverse=True)
    return accounts[:limit]


def fetch_trades(addr: str, since_ts: int) -> list[dict[str, Any]]:
    """Fetch recent trades for one account, newest-first, up to 1000 rows."""
    out: list[dict[str, Any]] = []
    offset = 0
    while offset < 1000:
        url = (
            f"{DATA_API}/trades?user={addr}&takerOnly=false&limit=500"
            f"&start=1&offset={offset}"
        )
        rows = http_json(url)
        if not isinstance(rows, list) or not rows:
            break
        new = 0
        for row in rows:
            ts = int(row.get("timestamp") or 0)
            if ts < since_ts:
                continue
            out.append(row)
            new += 1
        if new == 0 or len(rows) < 500:
            break
        offset += 500
        time.sleep(0.4)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Track profitable accounts' public trades.")
    parser.add_argument("--hours", type=int, default=24, help="Look-back window in hours.")
    parser.add_argument("--limit", type=int, default=12, help="Max accounts to follow.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    since_ts = int(since.timestamp())
    accounts = load_followed_accounts(args.limit)
    if not accounts:
        print("没有可用账户清单（缺少 address_registry.csv）")
        return 1

    TRACK_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    if TRACK_FILE.exists():
        for line in TRACK_FILE.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(str(json.loads(line).get("transactionHash") or ""))
            except json.JSONDecodeError:
                continue

    appended: list[dict[str, Any]] = []
    per_market: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"buys": [], "sells": [], "accounts": set()}
    )
    now = datetime.now(timezone.utc)
    for acc in accounts:
        addr = acc["address"]
        if not addr:
            continue
        try:
            trades = fetch_trades(addr, since_ts)
        except Exception as exc:  # noqa: BLE001
            print(f"[follow] {acc['name']} 拉取失败: {exc}")
            continue
        new_rows = 0
        for row in trades:
            tx = str(row.get("transactionHash") or "")
            if not tx or tx in seen:
                continue
            seen.add(tx)
            ts = int(row.get("timestamp") or 0)
            usd = 0.0
            try:
                usd = round(float(row.get("price") or 0) * float(row.get("size") or 0), 2)
            except (TypeError, ValueError):
                pass
            enriched = {
                "account": acc["name"],
                "address": addr,
                "tags": acc["tags"],
                "ts_utc": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
                "event_slug": row.get("eventSlug"),
                "title": row.get("title"),
                "market_slug": row.get("slug"),
                "outcome": row.get("outcome"),
                "side": row.get("side"),
                "price": row.get("price"),
                "size": row.get("size"),
                "usd_est": usd,
                "condition_id": row.get("conditionId"),
                "transaction_hash": tx,
            }
            appended.append(enriched)
            key = str(row.get("eventSlug") or row.get("slug") or row.get("conditionId") or "?")
            bucket = per_market[key]
            bucket["accounts"].add(acc["name"])
            (bucket["buys"] if str(row.get("side")) == "BUY" else bucket["sells"]).append(
                {
                    "account": acc["name"],
                    "outcome": row.get("outcome"),
                    "price": row.get("price"),
                    "size": row.get("size"),
                    "usd": usd,
                    "ts_utc": enriched["ts_utc"],
                }
            )
            new_rows += 1
        print(f"[follow] {acc['name']}: +{new_rows} 条新成交")
        time.sleep(0.5)

    if appended:
        with TRACK_FILE.open("a", encoding="utf-8") as f:
            for row in appended:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "lookback_hours": args.hours,
        "followed_accounts": len(accounts),
        "new_trades": len(appended),
        "markets": [],
    }
    for key, bucket in sorted(per_market.items(), key=lambda kv: -len(kv[1]["buys"])):
        buys = sorted(bucket["buys"], key=lambda x: x["ts_utc"])
        sells = sorted(bucket["sells"], key=lambda x: x["ts_utc"])
        total_shares = sum(float(b["size"]) for b in buys)
        summary["markets"].append(
            {
                "market": key,
                "accounts": sorted(bucket["accounts"]),
                "buy_count": len(buys),
                "buy_usd": round(sum(float(b["usd"] or 0) for b in buys), 2),
                "avg_buy_price": round(
                    sum(float(b["price"]) * float(b["size"]) for b in buys) / max(1, total_shares),
                    4,
                )
                if buys
                else None,
                "sell_count": len(sells),
                "sell_usd": round(sum(float(s["usd"] or 0) for s in sells), 2),
                "sample": (buys + sells)[:6],
            }
        )

    out_path = SUMMARY_DIR / f"winner_account_watch_{now:%Y-%m-%d}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== 赢家账户跟随摘要（{args.hours}h，新成交 {len(appended)} 条）===")
    for m in summary["markets"]:
        print(
            f"- {m['market']}: {m['accounts']} | 买 {m['buy_count']} 笔 ${m['buy_usd']}"
            f"（均价 {m['avg_buy_price']}）| 卖 {m['sell_count']} 笔 ${m['sell_usd']}"
        )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
