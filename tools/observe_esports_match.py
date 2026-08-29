#!/usr/bin/env python3
"""Read-only live observer for an esports match's market prices.

Discovery-chain tool (read-only; never places orders).

Polls gamma event outcome prices (game1/game2/moneyline + score) every
--interval seconds and appends samples to runtime/observe_<slug>.jsonl.
Prints a line when a side moves more than --alert-move within one poll,
and when TH-like underdog crosses below --alert-floor (potential "送局" move).

Usage:
  python3 tools/observe_esports_match.py --slug lol-navi-th-2026-08-17
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("/Users/ad/Documents/polymarket")
GAMMA = "https://gamma-api.polymarket.com"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:  # noqa: BLE001
            return []
    return value or []


def http_json(url: str, tries: int = 4) -> Any:
    last: Exception | None = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5)
    raise RuntimeError(f"GET {url} failed: {last}")


def main() -> int:
    parser = argparse.ArgumentParser(description="只读比赛赔率观察（监控用，不下单）")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--max-minutes", type=int, default=120)
    parser.add_argument("--alert-move", type=float, default=0.10)
    parser.add_argument("--alert-floor", type=float, default=0.12)
    args = parser.parse_args()

    out = ROOT / "runtime" / f"observe_{args.slug}.jsonl"
    deadline = time.time() + args.max_minutes * 60
    prev: dict[str, float] = {}
    while time.time() < deadline:
        try:
            ev = http_json(f"{GAMMA}/events?slug={args.slug}")[0]
            prices: dict[str, dict[str, float]] = {}
            for m in ev.get("markets") or []:
                slug = str(m.get("slug") or "")
                if slug not in (
                    f"{args.slug}",
                    f"{args.slug}-game1",
                    f"{args.slug}-game2",
                    f"{args.slug}-total-games-2pt5",
                ):
                    continue
                outs = parse_list(m.get("outcomes"))
                ps = parse_list(m.get("outcomePrices"))
                try:
                    prices[slug] = {
                        str(outs[i]): float(ps[i]) for i in range(min(len(outs), len(ps)))
                    }
                except (TypeError, ValueError):
                    continue
            now = datetime.now(timezone.utc).isoformat()
            sample = {
                "ts": now,
                "score": ev.get("score"),
                "game1": prices.get(f"{args.slug}-game1"),
                "game2": prices.get(f"{args.slug}-game2"),
                "moneyline": prices.get(args.slug),
                "total_games": prices.get(f"{args.slug}-total-games-2pt5"),
            }
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            g2 = sample["game2"] or {}
            ml = sample["moneyline"] or {}
            side0 = list(g2.keys())[0] if g2 else "?"
            side1 = list(g2.keys())[1] if g2 and len(g2) > 1 else "?"
            v0 = g2.get(side0)
            v1 = g2.get(side1)
            line = (
                f"{now[11:19]} score={ev.get('score')} "
                f"G2 {side0}={v0} {side1}={v1} | ML={ml}"
            )
            if v0 is not None and side0 in prev:
                move = v0 - prev[side0]
                if abs(move) >= args.alert_move:
                    print(f"  >> 移动 {side0}: {prev[side0]:.3f} -> {v0:.3f} ({(move):+.3f})")
                if v0 <= args.alert_floor and prev[side0] > args.alert_floor:
                    print(f"  !! {side0} 跌破 {args.alert_floor:.2f}（深水/送局候选）")
            if v0 is not None:
                prev[side0] = v0
            print(line)
        except Exception as exc:  # noqa: BLE001
            print(f"[observe] poll error: {exc}")
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
