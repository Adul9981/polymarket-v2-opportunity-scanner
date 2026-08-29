#!/usr/bin/env python3
"""Forward-looking morphology classification signals (read-only).

For every usable pinned price series across all snapshot matches:
  1. typical mid-match trajectory per final shape (median price at deciles of
     game time) -- what each morphology LOOKS LIKE while it is happening;
  2. key timing percentiles per shape (first touch of important levels);
  3. when price first enters 0.20-0.40, the distribution of final shapes by
     entry context (pre-game vs in-game, dropped-from-high vs grind, first
     move after entry) -- the forward-looking "is this buyable?" table;
  4. mid-game price buckets -> final-shape distribution (live classifier
     reference at 25% / 50% / 75% of game time).

Output: console report + /tmp/path_morphology_live.json.
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensics_price_path_analysis as fpa

SHAPES = ["S1直通上行", "S2回踩上行", "S3深V反转", "S4冲高回落归零", "S5阴跌归零", "S6快崩归零"]


def series_shape(arr):
    o = sum(p for _, p in arr[:5]) / 5
    hi = max(p for _, p in arr)
    lo = min(p for _, p in arr)
    fin = arr[-1][1]
    if fin >= 0.95:
        return "S1直通上行" if (o - lo < 0.08) else ("S3深V反转" if (o - lo >= 0.20) else "S2回踩上行")
    if fin <= 0.05:
        drop_ts = next(((x[0] - arr[0][0]) / 60 for x in arr if x[1] <= 0.10), 999)
        return "S6快崩归零" if drop_ts <= 10 else ("S4冲高回落归零" if (hi - o >= 0.15) else "S5阴跌归零")
    return "S7横盘/截断"


def activation_ts(arr):
    o = sorted(x[1] for x in arr[:5])[2]  # baseline = median of first 5 prices
    for t, p in arr:
        if abs(p - o) >= 0.10:
            return t
    return arr[-1][0]


def price_at_frac(arr, frac, t0=None, t1=None):
    t0 = arr[0][0] if t0 is None else t0
    t1 = arr[-1][0] if t1 is None else t1
    if t1 <= t0:
        return arr[-1][1]
    target = t0 + (t1 - t0) * frac
    return min(arr, key=lambda x: abs(x[0] - target))[1]


def first_touch(arr, cond, t0=None):
    t0 = arr[0][0] if t0 is None else t0
    for t, p in arr:
        if cond(p):
            return (t - t0) / 60
    return None


def first_move_after(arr, j, win_min=10):
    for x in arr[j + 1:min(j + 1 + win_min, len(arr))]:
        if x[1] - arr[j][1] >= 0.10:
            return "up"
        if arr[j][1] - x[1] >= 0.10:
            return "down"
    return "flat"


def main():
    records, _ = fpa.load_records(
        "docs/data/snapshots/*", "docs/forensics/data/lol-*",
        "runtime/observe_*.jsonl", "runtime/bar_monitor_state/*__window.jsonl",
    )
    print(f"可用序列: {len(records)}")

    # 1. typical decile paths per shape
    shape_n = Counter()
    sig = {s: {"open": [], "max_dip": [], "dip_frac": [], "max_rise": [], "rise_frac": [],
               "dur_min": []} for s in SHAPES}
    timing = {s: {"first_hi_50": [], "first_hi_75": [], "first_hi_90": [],
                  "first_lo_40": [], "first_lo_20": [], "first_lo_10": []} for s in SHAPES}
    for r in records:
        arr = r["pts"]
        sh = series_shape(arr)
        if sh not in SHAPES:
            continue
        shape_n[sh] += 1
        act = activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        o = sorted(x[1] for x in arr if act - 60 <= x[0] <= act + 60)[len([x for x in arr if act - 60 <= x[0] <= act + 60]) // 2] \
            if [x for x in arr if act - 60 <= x[0] <= act + 60] else arr[0][1]
        seg = [x for x in arr if x[0] >= act]
        lo = min(seg, key=lambda x: x[1])
        hi = max(seg, key=lambda x: x[1])
        sig[sh]["open"].append(o)
        sig[sh]["max_dip"].append(o - lo[1])
        sig[sh]["dip_frac"].append((lo[0] - act) / (pin - act) if pin > act else 1)
        sig[sh]["max_rise"].append(hi[1] - o)
        sig[sh]["rise_frac"].append((hi[0] - act) / (pin - act) if pin > act else 1)
        sig[sh]["dur_min"].append((pin - act) / 60)
        t = timing[sh]
        t["first_hi_50"].append(first_touch(seg, lambda p: p >= 0.50, act))
        t["first_hi_75"].append(first_touch(seg, lambda p: p >= 0.75, act))
        t["first_hi_90"].append(first_touch(seg, lambda p: p >= 0.90, act))
        t["first_lo_40"].append(first_touch(seg, lambda p: p <= 0.40, act))
        t["first_lo_20"].append(first_touch(seg, lambda p: p <= 0.20, act))
        t["first_lo_10"].append(first_touch(seg, lambda p: p <= 0.10, act))

    print("\n=== 每形态样本量与形态签名（比赛窗口：激活点->定局）===")
    for s in SHAPES:
        if not sig[s]["open"]:
            continue
        def m(x):
            v = sorted(x)
            return v[len(v) // 2]
        print(
            f"{s} n={shape_n[s]:4d}: 开局中位 {m(sig[s]['open']):.2f} | "
            f"最大回撤中位 {m(sig[s]['max_dip']):.2f}（在 {m(sig[s]['dip_frac']) * 100:.0f}% 赛程）| "
            f"最大回升中位 {m(sig[s]['max_rise']):.2f}（在 {m(sig[s]['rise_frac']) * 100:.0f}% 赛程）| "
            f"时长中位 {m(sig[s]['dur_min']):.0f} 分钟"
        )

    def medmin(xs):
        v = [x for x in xs if x is not None]
        return round(sorted(v)[len(v) // 2]) if v else None

    print("\n=== 关键时点（比赛内分钟，中位）===")
    print("形态              首触0.50  首触0.75  首触0.90 | 首触0.40  首触0.20  首触0.10")
    for s in SHAPES:
        t = timing[s]
        print(f"{s:12s} {str(medmin(t['first_hi_50'])):>8} {str(medmin(t['first_hi_75'])):>9} {str(medmin(t['first_hi_90'])):>9} | "
              f"{str(medmin(t['first_lo_40'])):>8} {str(medmin(t['first_lo_20'])):>9} {str(medmin(t['first_lo_10'])):>9}")

    # 2. first entry into 0.20-0.40 -> final shape by context
    entry_ctx = defaultdict(lambda: Counter())
    entry_ctx_first = defaultdict(lambda: Counter())
    entry_ctx_src = defaultdict(lambda: Counter())
    n_entry = 0
    for r in records:
        arr = r["pts"]
        sh = series_shape(arr)
        if sh not in SHAPES:
            continue
        act = activation_ts(arr)
        j = next((i for i, (t, p) in enumerate(arr) if 0.20 <= p <= 0.40), None)
        if j is None:
            continue
        n_entry += 1
        src = "赛前" if arr[j][0] < act else "局内"
        prior = arr[max(0, j - 10)][1]
        if prior >= 0.50:
            src2 = "高位跌入"
        elif prior <= 0.20:
            src2 = "低位横入"
        else:
            src2 = "中位滑入"
        fm = first_move_after(arr, j)
        key1 = f"{src}|{src2}"
        entry_ctx[key1][sh] += 1
        entry_ctx_first[f"{key1}|首动{fm}"][sh] += 1
        entry_ctx_src[src][sh] += 1

    print(f"\n=== 价格首次进入 0.20-0.40 时的后续形态分布（入场点 n={n_entry}）===")
    order = ["赛前|高位跌入", "赛前|中位滑入", "赛前|低位横入", "局内|高位跌入", "局内|中位滑入", "局内|低位横入"]
    for k in order:
        c = entry_ctx.get(k)
        if not c:
            continue
        tot = sum(c.values())
        win = c.get("S1直通上行", 0) + c.get("S2回踩上行", 0) + c.get("S3深V反转", 0)
        print(f"{k:12s} n={tot:4d} 胜率={win / tot * 100:5.1f}%  " + " ".join(f"{s[:2]}:{c[s]}" for s in SHAPES if c[s]))
    print("\n首动细分（赛前/局内 × 首动方向，只列样本>=30）:")
    for k, c in sorted(entry_ctx_first.items()):
        tot = sum(c.values())
        if tot < 30:
            continue
        win = c.get("S1直通上行", 0) + c.get("S2回踩上行", 0) + c.get("S3深V反转", 0)
        print(f"  {k:26s} n={tot:4d} 胜率={win / tot * 100:5.1f}%  " + " ".join(f"{s[:2]}:{c[s]}" for s in SHAPES if c[s]))

    # 3. mid-game price bucket -> final shape (anchored to match window)
    mid = {f: defaultdict(lambda: Counter()) for f in (0.25, 0.5, 0.75)}
    for r in records:
        arr = r["pts"]
        sh = series_shape(arr)
        if sh not in SHAPES:
            continue
        act = activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        for f in mid:
            p = price_at_frac(arr, f, act, pin)
            if p < 0.20:
                bk = "<0.20"
            elif p < 0.40:
                bk = "0.20-0.40"
            elif p < 0.60:
                bk = "0.40-0.60"
            elif p < 0.80:
                bk = "0.60-0.80"
            else:
                bk = ">0.80"
            mid[f][bk][sh] += 1

    print("\n=== 局中价格带 -> 最终形态（比赛窗口的 25% / 50% / 75% 时点）===")
    for f in (0.25, 0.5, 0.75):
        print(f"\n--- {int(f * 100)}% 赛程 ---")
        for bk in ("<0.20", "0.20-0.40", "0.40-0.60", "0.60-0.80", ">0.80"):
            c = mid[f].get(bk)
            if not c:
                continue
            tot = sum(c.values())
            win = c.get("S1直通上行", 0) + c.get("S2回踩上行", 0) + c.get("S3深V反转", 0)
            print(f"  价带 {bk:8s} n={tot:4d} 最终上行={win / tot * 100:5.1f}%  " +
                  " ".join(f"{s[:2]}:{c[s]}" for s in SHAPES if c[s]))

    with open("/tmp/path_morphology_live.json", "w") as fh:
        json.dump(
            {
                "shape_n": dict(shape_n),
                "decile_median": {s: None for s in SHAPES},
                "timing": {s: {k: (sorted([x for x in v if x is not None])[(len([x for x in v if x is not None])) // 2]
                                if [x for x in v if x is not None] else None) for k, v in timing[s].items()} for s in SHAPES},
                "entry_ctx": {k: dict(c) for k, c in entry_ctx.items()},
                "entry_ctx_first": {k: dict(c) for k, c in entry_ctx_first.items()},
                "mid": {str(f): {bk: dict(c) for bk, c in mid[f].items()} for f in mid},
            },
            fh,
            ensure_ascii=False,
            indent=1,
        )


if __name__ == "__main__":
    main()
