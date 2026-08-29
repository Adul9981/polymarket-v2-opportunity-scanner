#!/usr/bin/env python3
"""Definitive price-morphology census across all snapshot matches (read-only).

For every usable pinned two-sided price series:
  - extract match-window features (open, max dip, max rise, timing of dip/peak,
    first move, swing count, duration);
  - assign a morphology label on a rule grid:
      WIN:  W1直通 / W2回踩 / W3深V   x  开局(高/中/低)   x  转折时点(早/中/晚)
      LOSE: L1冲高回落 / L2阴跌 / L3快崩  x  开局(高/中/低)  x  转折时点(早/中/晚)
  - census: how many distinct morphologies exist, with counts, defining stats
    and representative real examples.
  - cross-check: prototype count by greedy correlation clustering of
    time-normalized paths (WIN and LOSE separately).

Output: console report + reports/morphology_census_2026-08-22.json.
"""

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensics_price_path_analysis as fpa
import path_morphology_live as pml


def bucket3(x):
    if x < 0.33:
        return "早"
    if x < 0.67:
        return "中"
    return "晚"


def open_bucket(p):
    if p >= 0.60:
        return "高开"
    if p >= 0.40:
        return "中开"
    return "低开"


def first_move_after(arr, j, win_min=10):
    for x in arr[j + 1:min(j + 1 + win_min, len(arr))]:
        if x[1] - arr[j][1] >= 0.10:
            return "up"
        if arr[j][1] - x[1] >= 0.10:
            return "down"
    return "flat"


def resample(arr, n=20, t0=None, t1=None):
    t0 = arr[0][0] if t0 is None else t0
    t1 = arr[-1][0] if t1 is None else t1
    if t1 <= t0:
        return [arr[-1][1]] * n
    out = []
    for i in range(n):
        target = t0 + (t1 - t0) * (i / (n - 1))
        out.append(min(arr, key=lambda x: abs(x[0] - target))[1])
    return out


def greedy_prototypes(series, thr):
    """Greedy farthest-point clustering by correlation on resampled paths."""
    import math

    protos = []
    for v in series:
        best = None
        best_r = -2
        for p in protos:
            m = len(v)
            mv = sum(v) / m
            mp = sum(p) / m
            num = sum((v[i] - mv) * (p[i] - mp) for i in range(m))
            d1 = math.sqrt(sum((v[i] - mv) ** 2 for i in range(m)))
            d2 = math.sqrt(sum((p[i] - mp) ** 2 for i in range(m)))
            r = num / (d1 * d2) if d1 * d2 > 0 else 0
            if r > best_r:
                best_r = r
                best = p
        if best is None or best_r < thr:
            protos.append(v)
    return len(protos)


def main():
    records, _ = fpa.load_records(
        "docs/data/snapshots/*", "docs/forensics/data/lol-*",
        "runtime/observe_*.jsonl", "runtime/bar_monitor_state/*__window.jsonl",
    )
    print(f"可用双侧序列: {len(records)}")

    census = Counter()
    meta = defaultdict(list)
    win_paths, lose_paths = [], []

    for r in records:
        arr = r["pts"]
        act = pml.activation_ts(arr)
        pin = arr[-1][0]
        if pin - act < 5 * 60:
            act = arr[0][0]
        seg = [x for x in arr if x[0] >= act]
        o = seg[0][1]
        fin = seg[-1][1]
        lo = min(seg, key=lambda x: x[1])
        hi = max(seg, key=lambda x: x[1])
        dur = (pin - act) / 60
        dip = o - lo[1]
        rise = hi[1] - o
        dip_frac = (lo[0] - act) / (pin - act) if pin > act else 1
        rise_frac = (hi[0] - act) / (pin - act) if pin > act else 1
        drop10 = next(((x[0] - act) / (pin - act) for x in seg if x[1] <= 0.10), None)
        fm = first_move_after(arr, 0)  # first move from match start
        ob = open_bucket(o)

        if fin >= 0.95:
            base = "W1直通" if dip < 0.08 else ("W2回踩" if dip < 0.20 else "W3深V")
            tp = bucket3(dip_frac)
            code = f"{base}|{ob}|低点{tp}"
            win_paths.append(resample(seg, 20, act, pin))
        elif fin <= 0.05:
            if rise >= 0.15:
                base = "L1冲高回落"
                tp = bucket3(rise_frac)
            else:
                fast = drop10 is not None and drop10 * dur <= 10
                if fast:
                    base = "L3快崩"
                    tp = "早"
                else:
                    base = "L2阴跌"
                    tp = bucket3(drop10) if drop10 is not None else "晚"
            code = f"{base}|{ob}|{tp}"
            lose_paths.append(resample(seg, 20, act, pin))
        else:
            code = "S7横盘/截断"

        census[code] += 1
        meta[code].append(
            {
                "slug": r["slug"], "market": r["market"], "side": r["side"],
                "game": r["game"], "open": round(o, 3), "final": round(fin, 2),
                "max_dip": round(dip, 3), "dip_frac": round(dip_frac, 2),
                "max_rise": round(rise, 3), "rise_frac": round(rise_frac, 2),
                "dur_min": round(dur), "first": fm, "path": code,
            }
        )

    print("\n=== 基础形态（6 型）===")
    base = Counter()
    for code, n in census.items():
        base[code.split("|")[0]] += n
    for k in ("W1直通", "W2回踩", "W3深V", "L1冲高回落", "L2阴跌", "L3快崩", "S7横盘/截断"):
        if base[k]:
            print(f"  {k}: {base[k]}")

    print("\n=== 细分形态普查（终局 x 开局 x 转折时点，全部有样本的格子）===")
    print(f"有样本的细分形态数: {len(census)}")
    print(f"样本 >= 8 的细分形态数: {sum(1 for v in census.values() if v >= 8)}")
    print(f"样本 >= 15 的细分形态数: {sum(1 for v in census.values() if v >= 15)}")
    print("\n按样本量排序（Top 25）:")
    for code, n in census.most_common(25):
        print(f"  {code:22s} n={n}")

    print("\n=== 主要形态（n>=8）特征与代表案例 ===")
    for code, n in census.most_common():
        if n < 8:
            continue
        rows = meta[code]
        o = sorted(x["open"] for x in rows)[len(rows) // 2]
        dp = sorted(x["max_dip"] for x in rows)[len(rows) // 2]
        dr = sorted(x["max_rise"] for x in rows)[len(rows) // 2]
        du = sorted(x["dur_min"] for x in rows)[len(rows) // 2]
        ex = rows[0]
        print(f"  {code:22s} n={n:3d} | 开局中位 {o:.2f} 回撤中位 {dp:.2f} 回升中位 {dr:.2f} "
              f"时长 {du}min | 例: {ex['slug']} {ex['market']} {ex['side']} (open {ex['open']})")

    print("\n=== 交叉校验：时间归一化路径的原型数（相关系数阈值）===")
    for thr in (0.95, 0.90, 0.85):
        pw = greedy_prototypes(win_paths, thr)
        pl = greedy_prototypes(lose_paths, thr)
        print(f"  阈值 {thr}: 赢家侧原型 {pw} / 输家侧原型 {pl}（合计 {pw + pl}）")

    out = {
        "n_series": len(records),
        "census": dict(census.most_common()),
        "base": dict(base),
        "meta": {k: v for k, v in meta.items()},
        "n_distinct": len(census),
        "n_distinct_ge8": sum(1 for v in census.values() if v >= 8),
        "n_distinct_ge15": sum(1 for v in census.values() if v >= 15),
    }
    with open("reports/morphology_census_2026-08-22.json", "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("\nJSON: reports/morphology_census_2026-08-22.json")


if __name__ == "__main__":
    main()
