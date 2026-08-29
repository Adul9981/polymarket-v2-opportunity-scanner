#!/usr/bin/env python3
"""Lottery machine backtest: layer-1 deep-lottery ladders + layer-2 rebound confirmation.

Reads 1-minute price series (snapshot JSONL or backtest JSON) and simulates:
  Layer 1 (deep lottery): resting buys at 8c/6c/4c/2c when price dips below 10c.
  Layer 2 (rebound confirmation): add-on buy once a bounce from the deep zone is
  confirmed, with an immediate 50/70/85 take-profit ladder and half-cost stop.

Rule source: docs/task/PROJECT_PROGRESS.md section 10, 环节 4 (彩票机器).
"""

import argparse
import glob
import json
import os
from datetime import datetime, timezone

# Layer-1 ladder: ladder price -> fixed USD amount (环节 4: 每档 $5-10).
L1_LADDER = [(0.08, 5.0), (0.06, 6.0), (0.04, 8.0), (0.02, 10.0)]
L1_COST_FULL = sum(a for _, a in L1_LADDER)

# Layer-2 confirmation: fixed $15 add-on, take profit by cost basis, $1.5 lottery.
L2_AMOUNT = 15.0
L2_SELL_PLAN = [(0.50, 6.0), (0.70, 4.5), (0.85, 3.0)]  # (price, cost_basis_usd)
L2_LOTTERY_COST = 1.5

DEEP_ZONE = 0.10  # price below this = deep-lottery zone
NEED_HIGH_BEFORE = 0.25  # series must have traded >= this before the dip


def ts_to_epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def load_series(path):
    pts = []
    if path.endswith(".jsonl"):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                pts.append((ts_to_epoch(d["timestamp"]), d["price"]))
    else:
        with open(path) as fh:
            d = json.load(fh)
        pts = [(x["t"], x["p"]) for x in d.get("points", [])]
    pts.sort()
    return pts


def find_deep_phases(prices, need_high_before=NEED_HIGH_BEFORE, deep_zone=DEEP_ZONE):
    """Return list of (start, end) index ranges inside the deep zone, each preceded by >=25c."""
    phases = []
    in_phase = False
    start = None
    has_high = False
    n = len(prices)
    for i, p in enumerate(prices):
        if not has_high and p >= need_high_before:
            has_high = True
        if p < deep_zone:
            if not in_phase:
                in_phase = True
                start = i
        else:
            if in_phase:
                if has_high:
                    phases.append((start, i - 1))
                in_phase = False
                start = None
    if in_phase and has_high:
        phases.append((start, n - 1))
    return phases


def first_trigger(prices, phase, mode):
    """Scan from the deep-phase low onward; the rebound can exit the deep zone."""
    lo, hi = phase
    low = min(prices[lo : hi + 1])
    for i in range(lo + 1, len(prices)):
        a, b = prices[i - 1], prices[i]
        if mode == "single_15":
            if a < DEEP_ZONE and b - a >= 0.15:
                return i, b
        elif mode == "single_10":
            if a < DEEP_ZONE and b - a >= 0.10:
                return i, b
        elif mode == "cum_15":
            if prices[i] >= low + 0.15:
                return i, prices[i]
    return None, None


def simulate_layer2(prices, entry_idx, entry):
    """Confirm position: $15 at entry, 50/70/85 TP ladder + lottery, half-cost stop."""
    shares = L2_AMOUNT / entry
    stop_price = entry / 2.0
    stopped = False
    stop_fill = None
    proceeds = 0.0
    touched = {}
    tier_prices = [t[0] for t in L2_SELL_PLAN]
    for j in range(entry_idx + 1, len(prices)):
        p = prices[j]
        if p <= stop_price:
            stopped = True
            stop_fill = p
            break
        for price, cost in L2_SELL_PLAN:
            if price not in touched and p >= price:
                touched[price] = True
                proceeds += (cost / entry) * price
    if stopped:
        # stop the remaining un-sold cost basis (all not yet tier-sold)
        sold_cost = sum(c for price, c in L2_SELL_PLAN if price in touched)
        remaining_cost = L2_AMOUNT - sold_cost - L2_LOTTERY_COST
        proceeds += (remaining_cost / entry) * stop_fill
    # lottery: value at series end
    end_price = prices[-1]
    lottery_value = (L2_LOTTERY_COST / entry) * end_price
    proceeds += lottery_value
    max_after = max(prices[entry_idx + 1 :]) if entry_idx + 1 < len(prices) else entry
    return {
        "entry": round(entry, 3),
        "touched_tiers": sorted(touched),
        "stopped": stopped,
        "max_after": round(max_after, 3),
        "end": round(end_price, 3),
        "proceeds": round(proceeds, 2),
        "pnl": round(proceeds - L2_AMOUNT, 2),
        "roi": round((proceeds - L2_AMOUNT) / L2_AMOUNT * 100, 1),
    }


def simulate_layer1(prices, phase):
    """Resting ladders inside the deep phase; value if held to post-low max vs. settlement."""
    lo, hi = phase
    seg_low = min(prices[lo : hi + 1])
    cost = 0.0
    shares = 0.0
    for price, amount in L1_LADDER:
        if seg_low <= price:
            cost += amount
            shares += amount / price
    avg = cost / shares if shares else 0.0
    phase_max = max(prices[lo:])
    end = prices[-1]
    value_at_max = shares * phase_max
    value_at_end = shares * end
    return {
        "cost": round(cost, 1),
        "filled_ladders": sum(1 for price, _ in L1_LADDER if seg_low <= price),
        "avg": round(avg, 3),
        "phase_max": round(phase_max, 3),
        "value_at_max": round(value_at_max, 1),
        "value_at_end": round(value_at_end, 1),
        "multiple_at_max": round(value_at_max / cost, 1) if cost else 0.0,
    }


def analyze(path, modes):
    pts = load_series(path)
    prices = [p for _, p in pts]
    name = os.path.relpath(path, "/Users/ad/Documents/polymarket")
    phases = find_deep_phases(prices)
    out = {"name": name, "n": len(prices), "deep_phases": len(phases), "triggers": {}}
    if phases:
        # Main phase = the one containing the series minimum (the real deep reversal).
        main = min(phases, key=lambda ph: min(prices[ph[0] : ph[1] + 1]))
        out["layer1"] = simulate_layer1(prices, main)
        for mode in modes:
            idx, entry = first_trigger(prices, main, mode)
            if idx is not None:
                out["triggers"][mode] = simulate_layer2(prices, idx, entry)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Explicit series paths; default: auto-discover snapshots + backtest JSONs.",
    )
    parser.add_argument(
        "--modes",
        nargs="*",
        default=["single_15", "single_10", "cum_15"],
        choices=["single_15", "single_10", "cum_15"],
    )
    args = parser.parse_args()

    if args.paths:
        paths = args.paths
    else:
        paths = sorted(glob.glob("/Users/ad/Documents/polymarket/docs/data/snapshots/*/*.jsonl"))
        paths += sorted(glob.glob("/Users/ad/Documents/polymarket/reports/*.json"))

    rows = []
    summary = {m: {"triggers": 0, "pnl": 0.0, "hits50": 0, "hits70": 0, "hits85": 0} for m in args.modes}
    n_deep_series = 0
    n_l1_positive = 0
    l1_multiples = []

    for path in paths:
        try:
            a = analyze(path, args.modes)
        except Exception:
            continue
        if not a["deep_phases"]:
            continue
        n_deep_series += 1
        l1 = a["layer1"]
        if l1["multiple_at_max"] > 1:
            n_l1_positive += 1
        l1_multiples.append(l1["multiple_at_max"])
        trig = " | ".join(
            f"{m}:{a['triggers'][m]['roi']}%" if m in a["triggers"] else f"{m}:-"
            for m in args.modes
        )
        rows.append(
            f"{a['name']:64s} deep={a['deep_phases']} l1_cost={l1['cost']:4.0f} "
            f"l1_maxx={l1['multiple_at_max']:5.1f} l1_end={l1['value_at_end']:6.1f} | {trig}"
        )
        for m in args.modes:
            t = a["triggers"].get(m)
            if t:
                s = summary[m]
                s["triggers"] += 1
                s["pnl"] += t["pnl"]
                s["hits50"] += 1 if 0.50 in t["touched_tiers"] else 0
                s["hits70"] += 1 if 0.70 in t["touched_tiers"] else 0
                s["hits85"] += 1 if 0.85 in t["touched_tiers"] else 0

    print(f"series with deep phases: {n_deep_series}")
    print(f"layer1 multiple>1 (held to phase max): {n_l1_positive}/{n_deep_series}")
    if l1_multiples:
        print(f"layer1 avg multiple at phase max: {sum(l1_multiples)/len(l1_multiples):.1f}x")
    for m in args.modes:
        s = summary[m]
        avg = s["pnl"] / s["triggers"] if s["triggers"] else 0.0
        print(
            f"layer2[{m}]: triggers={s['triggers']} avg_pnl={avg:+.1f} "
            f"hits 50/70/85 = {s['hits50']}/{s['hits70']}/{s['hits85']}"
        )
    print("--- per-series ---")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
