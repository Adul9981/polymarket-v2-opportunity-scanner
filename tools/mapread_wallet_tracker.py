#!/usr/bin/env python3
"""Mapread wallet tracker - ingest mapread.gg public JSON APIs into the forensics library.

Chain: 交易者拆解数据采集链（只读 forensics）。绝不读私钥、绝不下单。

Why
---
mapread.gg maintains per-game "smart money" wallet pools (ranked by 180-day
resolved-market performance) and exposes three public JSON endpoints. This tool
turns that into a reusable project data source:

  * board   - live flow board per game segment (which markets top wallets traded)
  * market  - wallet-level activity + 180d profiles for one market (condition_id)
  * watch   - scan recent activity and flag our forensics watchlist wallets

All raw JSON is archived under docs/forensics/data/mapread/ (append-only,
timestamped filenames, 只增不改). Nothing here places orders or reads keys.

Usage
-----
    python3 tools/mapread_wallet_tracker.py board [--segment all|lol|cs2|dota2|valorant] [--out DIR]
    python3 tools/mapread_wallet_tracker.py market --condition-id 0x... --segment lol [--out DIR]
    python3 tools/mapread_wallet_tracker.py watch [--segment all] [--max-markets N] [--out DIR]

Endpoints
---------
    GET /api/v1a/market-flow?segment_id={seg}&surface=board
    GET /api/v1a/market-flow/wallet-activity?condition_id={id}&segment_id={seg}
    GET /api/v1a/market-flow/wallet-profiles?condition_id={id}&segment_id={seg}

Underlying source: Polymarket Goldsky subgraph (wallet_live_order_fills).
"""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone

ROOT = "/Users/ad/Documents/polymarket"
DEFAULT_OUT = os.path.join(ROOT, "docs/forensics/data/mapread")
BASE = "https://mapread.gg"
UA = "Mozilla/5.0"

SEGMENTS = {
    "lol": "LoL",
    "cs2": "CS2",
    "dota2": "Dota2",
    "valorant": "Valorant",
}

# Our forensics watchlist (address -> label). Sources:
# docs/forensics/KNOWLEDGE_BASE.md / cases/README.md / 2026-08-26 mapread 拆解卡。
WATCHLIST = {
    "0xdaef2be2a19ad331737d06545f85615b094554e9": "PEYZ-BIGGEST-FAN（全剧本/深水）",
    "0x0224bb9eb0a5c9fd261ac9123a72cbdd5748292a": "zb8（跨场赢家 Top15）",
    "0x38181f43e5802391522583a82d05893df3039797": "MissingJoy（全剧本）",
    "0x52ecea7b3159f09db589e4f4ee64872fd0bba6f3": "fkigedgjdgwbg（深水机器人/假赛高盈利）",
    "0xfe787d2da716d60e8acff57fb87eb13cd4d10319": "ferrariChampions（跨场赢家 Top1）",
    "0x893575c7d99542163c6b6e8a0fe5af0b6d217daa": "antec（赛前三腿全买）",
    "0x8a8685a792c184e5c2ee8c7d4d4baba7c2c94998": "BrotherObama（赛前大额）",
    "0xf201a19b43471261a3c1ba9247335d55270e527e": "0xF201A19b（全剧本/深水）",
    "0x48fe10cd940a030eb18348ad812e0c382a4cb2b6": "Iamnobody.Nobody（跨场赢家）",
    "0xb35f674af4603c9602dfbf39564087e94897cf4c": "calculate10（全剧本）",
    "0x5d7e054225d1c58de66249233bf34d8b96ba2ef7": "okokxd（全剧本）",
    "0xcf609d3256f0f37f0595e5dc64012fa3a8fea6f5": "cf609d32（对照样本，高换手亏损）",
    "0x6d20c35f65d9899b6d6b74f8466e824580f9a165": "djdjdjekekek（账户崩盘案例）",
    "0x4f1d5ae26fc31472966e951af3183308736d8de2": "e46m3（主目标）",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ts_stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def curl(url):
    cmd = ["curl", "-sS", "--retry", "4", "--retry-all-errors",
           "--retry-delay", "2", "--max-time", "60", "-A", UA, url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"curl failed: {url} rc={r.returncode}")
    return r.stdout


def http_json(url):
    return json.loads(curl(url))


def save_raw(obj, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}-{ts_stamp()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return path


def fmt_usd(v):
    return f"${v:,.0f}"


def summarize_board(seg, data):
    m = data.get("manifest", {})
    s = data.get("summary", {})
    scope = m.get("data_scope", {})
    dq = m.get("data_quality", {})
    signals = data.get("signals", [])
    top = sorted(signals, key=lambda x: x.get("total_flow_usd") or 0, reverse=True)[:5]
    lines = [
        f"[{SEGMENTS[seg]}] 池={scope.get('wallet_count', '-')} 钱包 | "
        f"信号={s.get('signals', 0)} | 免费样例={s.get('unlocked_free_samples', 0)} / "
        f"锁定={s.get('locked_current_like_rows', 0)} | 源行={dq.get('source_rows', 0)} | "
        f"最新={s.get('latest_activity_at', '-')}",
    ]
    for t in top:
        lines.append(
            f"   {t.get('event_label', '?')} [{t.get('market_type', '')}] "
            f"流={fmt_usd(t.get('total_flow_usd') or 0)} "
            f"方向={t.get('direction_outcome', '?')} "
            f"{fmt_usd(t.get('direction_buy_usd') or 0)}"
        )
    return lines


def cmd_board(args):
    segs = [args.segment] if args.segment != "all" else list(SEGMENTS)
    out_dir = args.out
    for seg in segs:
        url = f"{BASE}/api/v1a/market-flow?segment_id={seg}&surface=board"
        data = http_json(url)
        path = save_raw(data, out_dir, f"board-{seg}")
        print(f"board {seg} -> {path}")
        for line in summarize_board(seg, data):
            print(line)


def summarize_market(seg, activity, profiles):
    buys = {}
    buy_out = {}
    for w in activity.get("wallets", []):
        addr = w["wallet"]
        for a in w.get("actions", []):
            if a["side"] != "BUY":
                continue
            amt = a.get("amount_usd") or 0
            b = buys.setdefault(addr, {"usd": 0.0, "fills": 0})
            b["usd"] += amt
            b["fills"] += 1
            buy_out[a["outcome"]] = buy_out.get(a["outcome"], 0.0) + amt
    lines = [
        f"wallets={len(activity.get('wallets', []))} 买入按方向={ {k: fmt_usd(v) for k, v in buy_out.items()} }"
    ]
    hits = []
    for addr, b in sorted(buys.items(), key=lambda x: -x[1]["usd"])[:10]:
        tag = WATCHLIST.get(addr)
        hit = " ★WATCH" if tag else ""
        prof = (profiles.get("profiles") or {}).get(addr) if profiles else None
        pnl = f" | 180d PnL {fmt_usd(prof['observed_cash_flow_pnl_usd'])}" if prof else ""
        lines.append(f"   {addr[:12]}… {fmt_usd(b['usd'])} {b['fills']}笔{hit}{pnl}")
        if tag:
            hits.append({"wallet": addr, "label": tag, "buy_usd": b["usd"], "fills": b["fills"]})
    return lines, hits


def cmd_market(args):
    out_dir = args.out
    act = http_json(
        f"{BASE}/api/v1a/market-flow/wallet-activity?condition_id={args.condition_id}&segment_id={args.segment}"
    )
    act_path = save_raw(act, out_dir, f"wallet-activity-{args.condition_id[2:10]}")
    prof = None
    try:
        prof = http_json(
            f"{BASE}/api/v1a/market-flow/wallet-profiles?condition_id={args.condition_id}&segment_id={args.segment}"
        )
        prof_path = save_raw(prof, out_dir, f"wallet-profiles-{args.condition_id[2:10]}")
    except RuntimeError:
        prof_path = None
    print(f"market {args.condition_id} -> {act_path}" + (f" / {prof_path}" if prof_path else ""))
    lines, hits = summarize_market(args.segment, act, prof)
    for line in lines:
        print(line)
    if hits:
        print("WATCHLIST HITS:")
        for h in hits:
            print(f"   {h['wallet']} {h['label']} buy={fmt_usd(h['buy_usd'])}")


def cmd_watch(args):
    out_dir = args.out
    segs = [args.segment] if args.segment != "all" else list(SEGMENTS)
    markets = []
    for seg in segs:
        data = http_json(f"{BASE}/api/v1a/market-flow?segment_id={seg}&surface=board")
        save_raw(data, out_dir, f"board-{seg}")
        for s in data.get("signals", []):
            markets.append({
                "condition_id": s["condition_id"],
                "segment": seg,
                "event_label": s.get("event_label", "?"),
                "market_type": s.get("market_type", ""),
                "total_flow_usd": s.get("total_flow_usd") or 0,
            })
    markets.sort(key=lambda x: -x["total_flow_usd"])
    markets = markets[: args.max_markets]
    report = {"fetched_at": now_iso(), "markets": markets, "watchlist": {}}
    for m in markets:
        try:
            act = http_json(
                f"{BASE}/api/v1a/market-flow/wallet-activity?condition_id={m['condition_id']}&segment_id={m['segment']}"
            )
        except RuntimeError:
            continue
        found = []
        for w in act.get("wallets", []):
            tag = WATCHLIST.get(w["wallet"])
            if tag:
                usd = sum((a.get("amount_usd") or 0) for a in w.get("actions", []) if a["side"] == "BUY")
                found.append({"wallet": w["wallet"], "label": tag, "buy_usd": usd})
        if found:
            key = f"{m['segment']}:{m['condition_id']}"
            report["watchlist"][key] = {
                "event": m["event_label"],
                "market_type": m["market_type"],
                "total_flow_usd": m["total_flow_usd"],
                "hits": found,
            }
            save_raw(act, out_dir, f"watch-{m['segment']}-{m['condition_id'][2:10]}")
        time.sleep(0.25)
    path = save_raw(report, out_dir, "watch-report")
    print(f"watch -> {path}")
    print(f"扫描市场 {len(markets)} 个,命中名单:")
    if not report["watchlist"]:
        print("   (无)")
    for key, v in report["watchlist"].items():
        print(f"   {v['event']} [{v['market_type']}] 流={fmt_usd(v['total_flow_usd'])}")
        for h in v["hits"]:
            print(f"      {h['wallet']} {h['label']} buy={fmt_usd(h['buy_usd'])}")


def main():
    p = argparse.ArgumentParser(description="Mapread wallet tracker (read-only forensics)")
    sub = p.add_subparsers(dest="cmd", required=True)
    pb = sub.add_parser("board", help="fetch live flow board per segment")
    pb.add_argument("--segment", default="all", choices=["all", *SEGMENTS])
    pb.add_argument("--out", default=DEFAULT_OUT)
    pb.set_defaults(func=cmd_board)
    pm = sub.add_parser("market", help="fetch wallet-activity + profiles for one market")
    pm.add_argument("--condition-id", required=True)
    pm.add_argument("--segment", required=True, choices=list(SEGMENTS))
    pm.add_argument("--out", default=DEFAULT_OUT)
    pm.set_defaults(func=cmd_market)
    pw = sub.add_parser("watch", help="scan recent markets and flag watchlist wallets")
    pw.add_argument("--segment", default="all", choices=["all", *SEGMENTS])
    pw.add_argument("--max-markets", type=int, default=15)
    pw.add_argument("--out", default=DEFAULT_OUT)
    pw.set_defaults(func=cmd_watch)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
