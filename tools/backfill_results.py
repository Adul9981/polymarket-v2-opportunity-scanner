#!/usr/bin/env python3
"""Auto-backfill match results from Polymarket settlement (local daily).

比赛结束后，从 Polymarket 事件市场读取"系列赢家"结算，回填 matches.json
result_inferred，供历史库/今日页显示（用户对实时性要求不高但需要结果）。
覆盖 matches.json 已有场次 + 服务器产出的场次（watchlist 有 slug）。

用法：python3 tools/backfill_results.py [--date YYYY-MM-DD]
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
MATCHES = ROOT / "docs" / "data" / "intel" / "matches.json"
WATCHLIST = ROOT / "runtime" / "watchlist_events.json"


def _get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 danmu-intel"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def _parse(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v


def league_of(title: str) -> str:
    t = (title or "").lower()
    if "counter-strike" in t or t.startswith("cs"):
        return "CS2"
    if "dota 2:" in t:
        return "Dota2"
    if "lol:" in t:
        for lg in ("LCK CL", "LPL", "LCK", "LEC", "LCP"):
            if lg.lower() in t:
                return lg
        return "LoL"
    return "-"


def settled_winner(slug: str, teams: list[str]) -> str | None:
    """从 gamma 事件找系列赢家市场，返回赢家队伍名（结算价 1 的一侧）。"""
    try:
        evs = _get(f"https://gamma-api.polymarket.com/events?slug={slug}")
    except Exception:  # noqa: BLE001
        return None
    if not evs:
        return None
    t_low = {t.lower().strip() for t in teams}
    for mk in evs[0].get("markets", []):
        q = mk.get("question", "") or ""
        outcomes = _parse(mk.get("outcomes") or [])
        prices = _parse(mk.get("outcomePrices") or [])
        if "Game " in q or "Handicap" in q or "First Blood" in q or not outcomes or not prices:
            continue
        if len(outcomes) == 2 and {o.lower().strip() for o in outcomes} == t_low:
            try:
                winner_idx = 0 if float(prices[0]) >= 0.99 else (1 if float(prices[1]) >= 0.99 else None)
            except (ValueError, TypeError):
                winner_idx = None
            if winner_idx is not None:
                return outcomes[winner_idx]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    today = args.date or datetime.date.today().isoformat()

    matches = json.loads(MATCHES.read_text(encoding="utf-8"))
    ml = matches.get("matches", [])
    by_id = {m.get("id"): m for m in ml}
    updated = []

    # 候选：watchlist 中的比赛（含服务器产出，有 slug）
    cands = []
    if WATCHLIST.exists():
        wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
        evs = wl if isinstance(wl, list) else wl.get("events", wl.get("matches", []))
        for e in evs:
            slug = e.get("slug", "")
            title = e.get("title", "")
            if not slug:
                continue
            mm = re.search(r":\s*(.+?)\s+vs\s+(.+?)\s*(?:\(|\-|$)", title, re.I)
            if not mm:
                continue
            cands.append((slug, [mm.group(1).strip(), mm.group(2).strip()], e.get("start_time", "")[:10]))
    if not cands:
        print("no watchlist candidates")
        return

    for slug, teams, date in cands:
        if date and args.date and date != args.date:
            continue
        mid = f"{slug}"
        m = by_id.get(mid)
        if m and m.get("result_inferred"):
            continue
        winner = settled_winner(slug, teams)
        if not winner:
            continue
        result = f"{winner} 胜（Polymarket 结算）"
        if m:
            m["result_inferred"] = result
        else:
            by_id[mid] = {"id": mid, "slug": slug, "date": date, "teams": teams,
                          "league": league_of(m.get("title", "")), "result_inferred": result}
        updated.append((mid, winner))
        time.sleep(0.4)  # 温和限速

    if updated:
        matches["matches"] = list(by_id.values())
        matches["updated_at"] = today
        MATCHES.write_text(json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backfilled {len(updated)} results: {[w for _, w in updated]}")


if __name__ == "__main__":
    main()
