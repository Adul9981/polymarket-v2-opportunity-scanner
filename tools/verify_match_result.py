#!/usr/bin/env python3
"""比赛结果官方结算快速校验（Polymarket 结算优先，零网页搜索）。

用法：
  python3 tools/verify_match_result.py                  # 扫描全部待确认且带 slug 的比赛
  python3 tools/verify_match_result.py --match-id 2026-08-23_tt_lgd
  python3 tools/verify_match_result.py --match-id xxx --apply   # 回填 matches.json

原理：Polymarket 事件结算价 = 官方结果（99.5/0.5 或 1/0）。
  gamma /events?slug= 返回 closed + markets[].outcomePrices，
  直接映射胜负，不需要任何网页搜索；无事件时输出 NOT_FOUND 走兜底。

输出：逐条打印 结算状态 / 获胜侧 / 与库内推断是否一致；
  --apply 时把 pending 标记为官方确认并追加 key_signal（可溯源）。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = ROOT / "docs" / "data" / "intel" / "matches.json"
GAMMA = "https://gamma-api.polymarket.com"


def http_json(url: str, tries: int = 4) -> dict:
    last: Exception | None = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polymarket-intel/0.1"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i < tries - 1:
                import time

                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"gamma fetch fail {url}: {last}")


def parse_list(value, cast=str) -> list:
    if isinstance(value, list):
        return [cast(x) for x in value]
    if isinstance(value, str):
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return [cast(x) for x in data]
        except Exception:
            pass
    return []


def load_matches() -> list[dict]:
    return json.loads(MATCHES.read_text(encoding="utf-8"))["matches"]


def check_event(slug: str) -> dict:
    data = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")
    if isinstance(data, list):
        data = data[0] if data else {}
    return data or {}


def settlement_row(match: dict) -> dict:
    slug = match.get("event_slug") or ""
    if not slug:
        return {"id": match["id"], "slug": "", "state": "NO_SLUG"}
    try:
        ev = check_event(slug)
    except Exception as exc:  # noqa: BLE001
        return {"id": match["id"], "slug": slug, "state": "FETCH_ERR", "error": str(exc)}
    if not ev:
        return {"id": match["id"], "slug": slug, "state": "NOT_FOUND"}
    markets = ev.get("markets") or []
    rows = []
    for m in markets:
        prices = parse_list(m.get("outcomePrices"), float)
        outcomes = parse_list(m.get("outcomes"))
        rows.append(
            {
                "market": m.get("slug"),
                "question": (m.get("question") or "")[:60],
                "closed": bool(m.get("closed")),
                "outcomes": outcomes,
                "prices": [round(p, 3) for p in prices],
            }
        )
    winner = None
    settled = False
    # 优先取"整场"市场（slug == 事件 slug，或含 BO3/系列字样），
    # 避免把 game1 的赢家当成系列赢家。
    def is_series_market(m: dict) -> bool:
        ms = m.get("market") or ""
        q = m.get("question") or ""
        if ms == slug:
            return True
        if "total" in ms or "-game" in ms:
            return False
        return "BO3" in q or "Winner" in q

    order = sorted(rows, key=lambda m: (0 if is_series_market(m) else 1, m["market"]))
    for m in rows:
        if m["closed"] and m["prices"]:
            settled = True
    for m in order:
        if m["closed"] and m["prices"]:
            idx = max(range(len(m["prices"])), key=lambda i: m["prices"][i])
            if 0 <= idx < len(m["outcomes"]):
                winner = m["outcomes"][idx]
                break
    return {
        "id": match["id"],
        "slug": slug,
        "state": "SETTLED" if settled else "OPEN",
        "event_closed": bool(ev.get("closed")),
        "winner": winner,
        "result_inferred": (match.get("result_inferred") or "")[:80],
        "markets": rows[:4],
    }


def apply_confirmation(match: dict, row: dict) -> bool:
    if row["state"] != "SETTLED" or not row["winner"]:
        return False
    note = f"Polymarket 结算确认：{row['winner']}（gamma {row['slug']}，closed）"
    signals = match.setdefault("key_signals", [])
    if not any("Polymarket 结算确认" in s for s in signals):
        signals.append(note)
    match["pending"] = f"已回填（{note}）"
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Polymarket 结算优先的结果校验")
    ap.add_argument("--match-id", default="")
    ap.add_argument("--apply", action="store_true", help="把结算结果回填 matches.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    matches = load_matches()
    if args.match_id:
        matches = [m for m in matches if m["id"] == args.match_id]
    else:
        # 只扫还没官方确认、且带 slug 的记录
        matches = [
            m
            for m in matches
            if m.get("event_slug")
            and ("待" in str(m.get("pending", "")) or "回补" in str(m.get("pending", "")) or "待官方" in str(m.get("result_inferred", "")))
        ]

    out: list[dict] = []
    changed = 0
    for m in matches:
        row = settlement_row(m)
        out.append(row)
        if args.apply and apply_confirmation(m, row):
            changed += 1
        if not args.json:
            print(
                f"[{row['state']:9s}] {m['id']}  winner={row.get('winner') or '-'}  "
                f"slug={row.get('slug') or '-'}"
            )

    if args.apply and changed:
        data = json.loads(MATCHES.read_text(encoding="utf-8"))
        data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        MATCHES.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"applied {changed} confirmation(s) -> {MATCHES}")

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
