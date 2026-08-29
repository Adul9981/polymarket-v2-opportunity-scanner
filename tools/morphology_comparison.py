#!/usr/bin/env python3
"""Complete base-morphology comparison with REAL match minutes (read-only).

For every usable pinned series:
  - duration stats by game type (activation -> pin, in minutes);
  - per base morphology: median price at real minute checkpoints
    (0,5,10,...,60 min after activation), median time to max dip / max rise,
    median time to first touch of key levels;
  - fraction -> real-minute mapping per game type (25/50/75%).

Output: console report + reports/morphology_comparison_2026-08-22.json
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensics_price_path_analysis as fpa
import path_morphology_live as pml

BASES = ["W1直通", "W2回踩", "W3深V", "L1冲高回落", "L2阴跌", "L3快崩"]


def base_of(arr):
    o = sum(p for _, p in arr[:5]) / 5
    lo = min(p for _, p in arr)
    hi = max(p for _, p in arr)
    fin = arr[-1][1]
    if fin >= 0.95:
        if o - lo < 0.08:
            return "W1直通"
        if o - lo < 0.20:
            return "W2回踩"
        return "W3深V"
    if fin <= 0.05:
        drop_ts = next(((x[0] - arr[0][0]) / 60 for x in arr if x[1] <= 0.10), 999)
        if drop_ts <= 10:
            return "L3快崩"
        if hi - o >= 0.15:
            return "L1冲高回落"
        return "L2阴跌"
    return None


def price_at_minute(arr, minute, t0):
    target = t0 + minute * 60
    return min(arr, key=lambda x: abs(x[0] - target))[1] if arr else None


def time_to(arr, cond, t0):
    for t, p in arr:
        if cond(p):
            return (t - t0) / 60
    return None


def main():
    records, _ = fpa.load_records(
        "docs/data/snapshots/*", "docs/forensics/data/lol-*",
        "runtime/observe_*.jsonl", "runtime/bar_monitor_state/*__window.jsonl",
    )

    dur_by_game = defaultdict(list)
    minutes = list(range(0, 61, 5))
    per_base = {b: {m: [] for m in minutes} for b in BASES}
    timing = {b: {"dip_min": [], "rise_min": [], "t75": [], "t90": [], "t40": [], "t20": [], "t10": []}
              for b in BASES}
    count = Counter()

    for r in records:
        arr = r["pts"]
        b = base_of(arr)
        if not b:
            continue
        count[b] += 1
        act = pml.activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        seg = [x for x in arr if x[0] >= act]
        dur_min = (pin - act) / 60
        dur_by_game[r["game"]].append(dur_min)
        for m in minutes:
            per_base[b][m].append(price_at_minute(seg, m, act))
        lo = min(seg, key=lambda x: x[1])
        hi = max(seg, key=lambda x: x[1])
        timing[b]["dip_min"].append((lo[0] - act) / 60)
        timing[b]["rise_min"].append((hi[0] - act) / 60)
        timing[b]["t75"].append(time_to(seg, lambda p: p >= 0.75, act))
        timing[b]["t90"].append(time_to(seg, lambda p: p >= 0.90, act))
        timing[b]["t40"].append(time_to(seg, lambda p: p <= 0.40, act))
        timing[b]["t20"].append(time_to(seg, lambda p: p <= 0.20, act))
        timing[b]["t10"].append(time_to(seg, lambda p: p <= 0.10, act))

    def med(xs):
        v = [x for x in xs if x is not None]
        return round(sorted(v)[len(v) // 2], 1) if v else None

    print("=== 比赛时长（激活点→定局，分钟）===")
    print("游戏     n     中位    p25    p75")
    for g in ("lol", "cs2", "dota2", "val"):
        v = dur_by_game.get(g, [])
        if not v:
            continue
        sv = sorted(v)
        print(f"{g:6s} {len(v):5d} {sv[len(sv)//2]:6.1f} {sv[len(sv)//4]:6.1f} {sv[len(sv)*3//4]:6.1f}")

    print("\n=== 每形态：真实分钟价格中位数（第 0/5/10/15/20/25/30/35/40/45/50/55/60 分钟）===")
    print("形态      " + " ".join(f"{m:>4}" for m in minutes))
    for b in BASES:
        row = " ".join(f"{str(med(per_base[b][m])):>4}" for m in minutes)
        print(f"{b:8s} {row}")

    print("\n=== 每形态：关键转折时刻（分钟，中位）===")
    print("形态      低点时刻  高点时刻  首触0.75 首触0.90 | 首触0.40 首触0.20 首触0.10")
    for b in BASES:
        t = timing[b]
        print(f"{b:8s} {str(med(t['dip_min'])):>7} {str(med(t['rise_min'])):>7} "
              f"{str(med(t['t75'])):>7} {str(med(t['t90'])):>7} | "
              f"{str(med(t['t40'])):>7} {str(med(t['t20'])):>7} {str(med(t['t10'])):>7}")

    print("\n=== 赛程百分比 → 真实分钟（按 LoL 中位时长换算）===")
    sv = sorted(dur_by_game.get("lol", []))
    lol_med = sv[len(sv) // 2] if sv else None
    if lol_med:
        for f in (0.25, 0.5, 0.75):
            print(f"  {int(f * 100)}% 赛程 ≈ 第 {round(f * lol_med)} 分钟（LoL 中位 {round(lol_med)} 分钟）")

    out = {
        "dur_by_game": {g: {"n": len(v), "median": round(sorted(v)[len(v) // 2], 1),
                            "p25": round(sorted(v)[len(v) // 4], 1),
                            "p75": round(sorted(v)[len(v) * 3 // 4], 1)} for g, v in dur_by_game.items() if v},
        "per_base_minute_median": {b: {str(m): med(per_base[b][m]) for m in minutes} for b in BASES},
        "timing_minute_median": {b: {k: med(v) for k, v in timing[b].items()} for b in BASES},
        "count": dict(count),
        "lol_median_duration": lol_med,
    }
    with open("reports/morphology_comparison_2026-08-22.json", "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nJSON: reports/morphology_comparison_2026-08-22.json")


if __name__ == "__main__":
    main()
