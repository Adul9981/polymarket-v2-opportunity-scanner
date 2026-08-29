#!/usr/bin/env python3
"""S-F1 完整集定价套利只读扫描器 v0 (forensics_arb_scanner.py)

Read-only. 两级扫描负风险多选项市场，寻找完整集定价错位 (Σp != 1)：
  一级粗筛：gamma outcomePrices 标记价算 Σp，|Σp-1| > coarse_threshold
  二级精筛：命中后拉订单簿 ask，逐档加权算"可成交总成本"，判 pass/fail

只扫描"近期结算"市场（默认 48 小时内），自动过滤远期冠军盘。
只读公开数据；不创建订单、不签名、不碰私钥。

输出：
  runtime/forensics/scan_YYYY-MM-DD.jsonl   每组每轮审计日志（一行一个组）
  reports/forensics_arb_scan_YYYY-MM-DD.md  每日统计摘要

用法：
  python3 tools/forensics_arb_scanner.py
  python3 tools/forensics_arb_scanner.py --horizon-hours 24 --target-usd 100 --verbose
"""

import argparse
import datetime
import json
import os
import ssl
import sys
import time
import urllib.request
from collections import defaultdict

ROOT = "/Users/ad/Documents/polymarket"
CONFIG_PATH = os.path.join(ROOT, "config", "forensics_arb.json")
SCAN_DIR = os.path.join(ROOT, "runtime", "forensics")
REPORT_DIR = os.path.join(ROOT, "reports")

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def http_get_json(url, retries=5, timeout=60):
    ctx = ssl.create_default_context()
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def parse_ts(iso):
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None


def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    cfg.setdefault("coarse_threshold", 0.02)
    cfg.setdefault("friction", 0.02)
    cfg.setdefault("safety_margin", 0.01)
    cfg.setdefault("min_legs", 5)
    cfg.setdefault("min_subset_legs", 4)
    cfg.setdefault("shares_per_leg", 12.8)
    cfg.setdefault("horizon_hours", 48)
    cfg.setdefault("target_usd", 100)
    cfg.setdefault("sanity_sump_min", 0.7)
    cfg.setdefault("sanity_sump_max", 1.3)
    cfg.setdefault("max_groups_fine", 8)
    cfg.setdefault("request_delay_sec", 0.15)
    return cfg


def fetch_events(cfg):
    """拉取未关闭事件（按成交量排序 + 天气分类补充），最多 3000 条。"""
    events, seen = [], set()
    urls = [
        f"{GAMMA}/events?closed=false&limit=100&order=volume&ascending=false",
        f"{GAMMA}/events?closed=false&limit=100&category=weather",
    ]
    for base in urls:
        for offset in range(0, 1500, 100):
            url = f"{base}&offset={offset}"
            try:
                page = http_get_json(url)
            except Exception:
                break
            if not page:
                break
            for ev in page:
                if ev.get("id") not in seen:
                    seen.add(ev.get("id"))
                    events.append(ev)
            if len(page) < 100:
                break
            time.sleep(cfg["request_delay_sec"])
    return events


def build_groups(events):
    """按 negRiskMarketID 聚合成组；同一事件多个组、不同事件同组都兼容。"""
    groups = {}
    for ev in events:
        for m in ev.get("markets", []):
            nr = m.get("negRiskMarketID")
            if not nr:
                continue
            try:
                prices = m.get("outcomePrices")
                if isinstance(prices, str):
                    prices = json.loads(prices)
                tokens = m.get("clobTokenIds")
                if isinstance(tokens, str):
                    tokens = json.loads(tokens)
            except Exception:
                continue
            if not prices or not tokens:
                continue
            g = groups.setdefault(
                nr,
                {
                    "group": nr,
                    "event_title": ev.get("title", ""),
                    "event_slug": ev.get("slug", ""),
                    "end_date": ev.get("endDate", ""),
                    "category": ev.get("category", ""),
                    "legs": [],
                },
            )
            g["legs"].append(
                {
                    "question": m.get("question") or m.get("title") or "",
                    "yes_price": float(prices[0]),
                    "yes_token": str(tokens[0]),
                    "no_token": str(tokens[1]),
                }
            )
    return groups


def coarse_filter(groups, cfg, now_ts):
    """只保留近期结算、腿数达标、Σp 在合理区间外的组。返回候选列表。"""
    horizon_ts = now_ts + cfg["horizon_hours"] * 3600
    candidates = []
    for g in groups.values():
        if len(g["legs"]) < cfg["min_legs"]:
            continue
        end_ts = parse_ts(g["end_date"])
        if end_ts is None or end_ts > horizon_ts:
            continue
        sp = sum(leg["yes_price"] for leg in g["legs"])
        if not (cfg["sanity_sump_min"] <= sp <= cfg["sanity_sump_max"]):
            continue
        if abs(sp - 1) <= cfg["coarse_threshold"]:
            continue
        g["mark_sump"] = sp
        g["end_ts"] = end_ts
        g["side"] = "NO" if sp > 1 else "YES"
        candidates.append(g)
    candidates.sort(key=lambda g: abs(g["mark_sump"] - 1), reverse=True)
    return candidates


def walk_asks(book, need):
    """按 ask 逐档加权，凑够 need 份；返回 (cost, filled)。"""
    asks = book.get("asks", [])
    cost, filled = 0.0, 0.0
    for a in sorted(asks, key=lambda x: float(x["price"])):
        if filled >= need:
            break
        price = float(a["price"])
        size = float(a["size"])
        take = min(size, need - filled)
        cost += take * price
        filled += take
    return cost, filled


def fine_scan(g, cfg):
    """订单簿精筛（NO 侧支持子集转换）。

    NO 侧：Convert 只需提供任一子集 S（k 条腿 × X 份），兑付现金 (k-1)*X。
      因此取"NO ask 深度够 X 且成本最低"的 k 条腿（k >= min_legs），
      若 Σ成本 < (k-1)*X*(1-摩擦)-安全垫 则 pass。
    YES 侧：需完整集全部腿，成本 < X*(1-摩擦)-安全垫 才 pass。
    任何腿深度不足 X 时该腿不可用；可用腿数不足 min_legs 判 depth_insufficient。
    """
    n = len(g["legs"])
    x = cfg["shares_per_leg"]
    token_key = "no_token" if g["side"] == "NO" else "yes_token"
    leg_costs, available = [], []
    no_ask_sum = 0.0
    legs_with_ask = 0
    for leg in g["legs"]:
        url = f"{CLOB}/book?token_id={leg[token_key]}"
        try:
            book = http_get_json(url)
        except Exception:
            return {
                "ask_cost": None,
                "notional": None,
                "net_est": None,
                "depth_ok": False,
                "verdict": "fail",
                "notes": "book_error",
                "live_sump": None,
            }
        asks = book.get("asks", [])
        if asks:
            best_ask = min(float(a["price"]) for a in asks)
            no_ask_sum += 1 - best_ask if g["side"] == "NO" else best_ask
            legs_with_ask += 1
        cost, filled = walk_asks(book, x)
        if filled >= x * 0.999:
            available.append(cost)
        else:
            leg_costs.append((filled, cost))
        time.sleep(cfg["request_delay_sec"])

    if len(available) < cfg["min_subset_legs"]:
        return {
            "ask_cost": round(sum(available) + sum(c for _, c in leg_costs), 4),
            "notional": None,
            "net_est": None,
            "depth_ok": False,
            "verdict": "depth_insufficient",
            "notes": f"legs_available={len(available)}/{n} (need {cfg['min_subset_legs']})",
            "live_sump": round(no_ask_sum, 4) if legs_with_ask else None,
        }

    available.sort()
    if g["side"] == "NO":
        best = None
        total = 0.0
        best_fail = None
        for k, cost in enumerate(available, start=1):
            if k < cfg["min_subset_legs"]:
                total += cost
                continue
            total += cost
            notional = (k - 1) * x
            limit = notional * (1 - cfg["friction"]) - cfg["safety_margin"]
            if best_fail is None or total < best_fail[1]:
                best_fail = (k, total, notional)
            if total < limit:
                edge = notional - total
                if best is None or edge > best[2]:
                    best = (k, round(total, 4), round(edge, 4), round(notional, 4))
        if best:
            k, total, edge, notional = best
            return {
                "ask_cost": total,
                "notional": notional,
                "net_est": edge,
                "depth_ok": True,
                "verdict": "pass",
                "notes": f"subset_k={k}/{n}",
                "live_sump": round(no_ask_sum, 4) if legs_with_ask else None,
            }
        k, total, notional = best_fail
        return {
            "ask_cost": round(total, 4),
            "notional": round(notional, 4),
            "net_est": None,
            "depth_ok": True,
            "verdict": "fail",
            "notes": f"best_subset_k={k}/{n}",
            "live_sump": round(no_ask_sum, 4) if legs_with_ask else None,
        }

    # YES side: complete set needs all legs
    total_cost = sum(available) + sum(c for _, c in leg_costs)
    if len(available) == n:
        notional = x
        limit = notional * (1 - cfg["friction"]) - cfg["safety_margin"]
        if total_cost < limit:
            return {
                "ask_cost": round(total_cost, 4),
                "notional": notional,
                "net_est": round(notional - total_cost, 4),
                "depth_ok": True,
                "verdict": "pass",
                "notes": "",
                "live_sump": round(no_ask_sum, 4) if legs_with_ask else None,
            }
    if len(available) < n:
        verdict = "depth_insufficient"
    else:
        verdict = "fail"
    return {
        "ask_cost": round(total_cost, 4),
        "notional": x,
        "net_est": None,
        "depth_ok": len(available) == n,
        "verdict": verdict,
        "notes": f"legs_available={len(available)}/{n}",
        "live_sump": round(no_ask_sum, 4) if legs_with_ask else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon-hours", type=int, default=None)
    ap.add_argument("--target-usd", type=float, default=None)
    ap.add_argument("--slugs", type=str, default=None,
                    help="comma-separated event slugs to scan directly (skip full event fetch)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    if args.horizon_hours:
        cfg["horizon_hours"] = args.horizon_hours
    if args.target_usd:
        cfg["target_usd"] = args.target_usd

    now_ts = int(time.time())
    today = datetime.datetime.utcfromtimestamp(now_ts).strftime("%Y-%m-%d")
    os.makedirs(SCAN_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    print(f"[scan] {today} {datetime.datetime.utcfromtimestamp(now_ts).strftime('%H:%M:%S')}Z "
          f"horizon={cfg['horizon_hours']}h target=${cfg['target_usd']:.0f} "
          f"coarse_thr={cfg['coarse_threshold']} X={cfg['shares_per_leg']}sh "
          f"min_subset={cfg['min_subset_legs']}")

    if args.slugs:
        events = []
        for s in [x.strip() for x in args.slugs.split(",") if x.strip()]:
            try:
                evs = http_get_json(f"{GAMMA}/events?slug={s}")
            except Exception:
                continue
            if isinstance(evs, list):
                events.extend(evs)
            time.sleep(cfg["request_delay_sec"])
        print(f"[scan] watchlist slugs={len(args.slugs.split(','))} events={len(events)}")
    else:
        events = fetch_events(cfg)
        print(f"[scan] events={len(events)}")
    groups = build_groups(events)
    print(f"[scan] neg-risk groups={len(groups)}")

    candidates = coarse_filter(groups, cfg, now_ts)
    print(f"[scan] coarse candidates={len(candidates)} "
          f"(legs>={cfg['min_legs']}, settle<={cfg['horizon_hours']}h)")

    rows = []
    for i, g in enumerate(candidates):
        if i >= cfg["max_groups_fine"]:
            rows.append(
                {
                    "ts": now_ts,
                    "group": g["event_slug"] or g["group"],
                    "event_title": g["event_title"],
                    "n_legs": len(g["legs"]),
                    "end_date": g["end_date"],
                    "category": g["category"],
                    "mark_sump": round(g["mark_sump"], 4),
                    "side": g["side"],
                    "ask_cost": None,
                    "notional": None,
                    "net_est": None,
                    "depth_ok": None,
                    "verdict": "coarse_only",
                    "notes": "fine-scan cap reached",
                    "live_sump": None,
                }
            )
            continue
        res = fine_scan(g, cfg)
        row = {
            "ts": now_ts,
            "group": g["event_slug"] or g["group"],
            "event_title": g["event_title"],
            "n_legs": len(g["legs"]),
            "end_date": g["end_date"],
            "category": g["category"],
            "mark_sump": round(g["mark_sump"], 4),
            "side": g["side"],
            **res,
        }
        rows.append(row)
        hours = max(0, (g["end_ts"] - now_ts) / 3600)
        flag = "★" if row["verdict"] == "pass" else " "
        print(
            f"[scan] {flag} {row['verdict']:<18} Σp={row['mark_sump']:.4f} "
            f"side={row['side']:<3} n={row['n_legs']:>2} settle_in={hours:>5.1f}h "
            f"ask=${row['ask_cost'] if row['ask_cost'] is not None else '-':<8} "
            f"{row['event_title'][:48]}"
        )
        time.sleep(cfg["request_delay_sec"])

    jsonl_path = os.path.join(SCAN_DIR, f"scan_{today}.jsonl")
    with open(jsonl_path, "a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[scan] jsonl -> {jsonl_path}")

    report_path = os.path.join(REPORT_DIR, f"forensics_arb_scan_{today}.md")
    with open(report_path, "w") as f:
        f.write(f"# S-F1 扫描 {today}（{cfg['horizon_hours']}h 内结算市场）\n\n")
        f.write(f"- 事件数 {len(events)}，负风险组 {len(groups)}，粗筛候选 {len(candidates)}\n")
        f.write(f"- 阈值：|Σp−1|>{cfg['coarse_threshold']}；摩擦 {cfg['friction']}；"
                f"安全垫 {cfg['safety_margin']}；目标 ${cfg['target_usd']:.0f}\n\n")
        if rows:
            f.write("| 状态 | 组 | Σp | 侧 | 腿 | 结算剩余h | ask成本$ | 净估$ | 备注 |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for r in rows:
                hours = max(0, (parse_ts(r["end_date"]) - now_ts) / 3600) if r["end_date"] else None
                f.write(
                    f"| {r['verdict']} | {r['event_title'][:36]} | {r['mark_sump']:.4f} | "
                    f"{r['side']} | {r['n_legs']} | {hours:.1f} | "
                    f"{r['ask_cost'] if r['ask_cost'] is not None else '-'} | "
                    f"{r['net_est'] if r['net_est'] is not None else '-'} | {r['notes']} |\n"
                )
        f.write("\n纪律：标记价只做粗筛；pass 仅表示可成交成本达标，真实执行需走成熟度与风控。\n")
    print(f"[scan] report -> {report_path}")

    passes = [r for r in rows if r["verdict"] == "pass"]
    print(f"[scan] done. pass={len(passes)} fail={sum(1 for r in rows if r['verdict']=='fail')} "
          f"depth_insufficient={sum(1 for r in rows if r['verdict']=='depth_insufficient')}")


if __name__ == "__main__":
    sys.exit(main())
