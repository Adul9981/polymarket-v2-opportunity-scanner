#!/usr/bin/env python3
"""Fetch game/map winner market status for watchlist matches -> runtime/game_status.json.

本地侧：Polymarket gamma 在云服务器（首尔）被地区限制（HTTP 451），
因此由本机每 5 分钟拉取小局结算状态并推到服务器
（/opt/danmu-intel/data/game_status.json），供 vps_intel_pipeline 按小局出节点。

用法：
  python3 tools/fetch_game_status.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "runtime" / "watchlist_events.json"
OUT = ROOT / "runtime" / "game_status.json"


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 danmu-intel"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def fetch(slug: str) -> dict:
    """返回 {局数: {closed, prices, winner_idx}}；失败返回 {}。"""
    try:
        evs = _get(f"https://gamma-api.polymarket.com/events?slug={slug}")
    except Exception:  # noqa: BLE001
        return {}
    if not evs:
        return {}
    out: dict[int, dict] = {}
    for mk in evs[0].get("markets", []):
        q = mk.get("question", "") or ""
        mm = re.search(r"(?:Game|Map)\s*(\d+)\s*Winner", q, re.I)
        if not mm:
            continue
        gi = int(mm.group(1))
        raw = mk.get("outcomePrices")
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            prices = [float(p) for p in (raw or [])]
        except (ValueError, TypeError, json.JSONDecodeError):
            prices = []
        winner = None
        if len(prices) >= 2:
            if prices[0] >= 0.99:
                winner = 0
            elif prices[1] >= 0.99:
                winner = 1
        out[gi] = {"closed": bool(mk.get("closed")), "prices": prices, "winner": winner}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchlist", default=str(WATCHLIST))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    data = json.loads(Path(args.watchlist).read_text(encoding="utf-8"))
    evs = data if isinstance(data, list) else data.get("events", data.get("matches", []))
    games: dict[str, dict] = {}
    for e in evs:
        slug = e.get("slug") or e.get("id") or ""
        if not slug:
            continue
        gs = fetch(slug)
        if gs:
            games[slug] = gs
        time.sleep(0.3)

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "games": games,
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {args.out}: {len(games)} events with game markets", flush=True)


if __name__ == "__main__":
    main()
