#!/usr/bin/env python3
"""Full price-path taxonomy across every snapshot match (read-only).

For every usable 1/5-minute two-sided price series in the project:
  1. classify the full-match path shape (S1..S7);
  2. encode the swing sequence (U/D moves in cents) and count distinct
     price-change path types;
  3. for entry bands 0.20 and 0.40 (plus 0.20-0.40 / 0.55-0.65 context),
     compute the outcome distribution: win rate, payoff multiple, lock-profit
     window, loss depth, path mix, split by sport / market type / pre-game vs
     in-game / first move.

Output: console report + /tmp/price_path_taxonomy.json.
"""

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forensics_price_path_analysis as fpa


def keypoints(pts, thr=0.07, gap=5):
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        t, p = pts[i]
        tp = pts[i - 1][1]
        tn = pts[i + 1][1]
        if (p > tp and p >= tn) or (p < tp and p <= tn):
            if abs(p - out[-1][1]) >= thr and (t - out[-1][0]) / 60 >= gap:
                out.append((t, p))
    out.append(pts[-1])
    return out


def swing_seq(pts, thr=0.07, gap=5):
    kps = keypoints(pts, thr, gap)
    seq = []
    for i in range(1, len(kps)):
        p0 = kps[i - 1][1]
        p1 = kps[i][1]
        d = "U" if p1 > p0 else "D"
        mag = int(round(abs(p1 - p0) * 100))
        seq.append(f"{d}{mag}")
    return seq


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
    """First time the price deviates >=10c from its opening value."""
    o = arr[0][1]
    for t, p in arr:
        if abs(p - o) >= 0.10:
            return t
    return arr[-1][0]


def classify_entry(entry_p, fwd):
    max_p = max(x[1] for x in fwd)
    min_p = min(x[1] for x in fwd)
    final = fwd[-1][1]
    rise = max_p - entry_p
    dip = entry_p - min_p
    first = "flat"
    for x in fwd[1:min(9, len(fwd))]:
        if x[1] - entry_p >= 0.10:
            first = "up"
            break
        if entry_p - x[1] >= 0.10:
            first = "down"
            break
    if final >= 0.95:
        lab = "P1直通" if dip < 0.08 else ("P2回踩上行" if dip < 0.20 else "P3深V反转")
    elif final <= 0.05:
        if rise >= 0.15:
            lab = "P4冲高回落归零"
        else:
            tt = next(((x[0] - fwd[0][0]) / 60 for x in fwd if x[1] <= 0.10), 999)
            lab = "P6快崩归零" if tt <= 10 else "P5阴跌归零"
    else:
        lab = "P7横盘/截断"
    return lab, max_p, min_p, rise, dip, first, final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/price_path_taxonomy.json")
    args = ap.parse_args()

    records, _ = fpa.load_records(
        "docs/data/snapshots/*", "docs/forensics/data/lol-*",
        "runtime/observe_*.jsonl", "runtime/bar_monitor_state/*__window.jsonl",
    )
    print(f"可用序列: {len(records)}")
    for g in ("lol", "cs2", "dota2", "val"):
        n = sum(1 for r in records if r["game"] == g)
        if n:
            print(f"  {g}: {n}")

    # ---- series-level taxonomy ----
    shape_cnt = Counter()
    seq_cnt = Counter()
    seq_dir_cnt = Counter()
    swing_n = Counter()
    series_rows = []
    for r in records:
        arr = r["pts"]
        sh = series_shape(arr)
        seq = swing_seq(arr)
        shape_cnt[sh] += 1
        seq_cnt[" ".join(seq)] += 1
        seq_dir_cnt[" ".join(s[0] for s in seq)] += 1
        swing_n[len(seq)] += 1
        series_rows.append(
            {
                "slug": r["slug"], "market": r["market"], "side": r["side"],
                "game": r["game"], "shape": sh, "seq": seq,
                "open": round(arr[0][1], 3), "final": round(arr[-1][1], 2),
            }
        )

    print("\n=== 系列级整场形态（710 条双侧序列）===")
    for k in ("S1直通上行", "S2回踩上行", "S3深V反转", "S4冲高回落归零", "S5阴跌归零", "S6快崩归零", "S7横盘/截断"):
        print(f"  {k}: {shape_cnt.get(k, 0)}")
    print(f"\n价格变化路径（带幅度摆动序列）种类数: {len(seq_cnt)}")
    print("Top 12:")
    for s, c in seq_cnt.most_common(12):
        print(f"  {s:24s} {c}")
    print(f"\n方向序列种类数: {len(seq_dir_cnt)}")
    for s, c in seq_dir_cnt.most_common(10):
        print(f"  {s:14s} {c}")
    print(f"\n摆动次数分布: {dict(sorted(swing_n.items()))}")

    # ---- entry analysis ----
    bands = {
        "0.20(±2c)": (0.18, 0.22),
        "0.40(±2c)": (0.38, 0.42),
        "0.20-0.40": (0.20, 0.40),
        "0.55-0.65": (0.55, 0.65),
    }
    stat = {b: {"n": 0, "win": 0, "lose": 0, "multi": [], "loss_ratio": [], "touch75": 0, "touch90": 0,
                "paths": Counter(), "by_sport": defaultdict(lambda: [0, 0]),
                "by_mkt": defaultdict(lambda: [0, 0]), "by_phase": defaultdict(lambda: [0, 0]),
                "by_first": defaultdict(lambda: [0, 0])} for b in bands}
    detail = {b: [] for b in bands}

    for r in records:
        arr = r["pts"]
        act = activation_ts(arr)
        for b, (blo, bhi) in bands.items():
            for j in fpa.find_entries(arr, blo, bhi):
                ep = arr[j][1]
                fwd = arr[j:]
                lab, mx, mn, rise, dip, first, final = classify_entry(ep, fwd)
                win = final >= 0.95
                s = stat[b]
                s["n"] += 1
                s["win" if win else "lose"] += 1
                s["paths"][lab] += 1
                s["touch75"] += 1 if mx >= 0.75 else 0
                s["touch90"] += 1 if mx >= 0.90 else 0
                if win:
                    s["multi"].append(final / ep)
                else:
                    s["loss_ratio"].append(mn / ep)
                s["by_sport"][r["game"]][0 if win else 1] += 1
                mkt_type = "game" if r["market"].startswith(("game", "map")) else "match"
                s["by_mkt"][mkt_type][0 if win else 1] += 1
                phase = "pre" if arr[j][0] < act else "ingame"
                s["by_phase"][phase][0 if win else 1] += 1
                s["by_first"][first][0 if win else 1] += 1
                detail[b].append(
                    {
                        "slug": r["slug"], "market": r["market"], "side": r["side"],
                        "game": r["game"], "entry": round(ep, 2), "win": win,
                        "path": lab, "max": round(mx, 3), "min": round(mn, 3),
                        "final": round(final, 2), "first": first, "phase": phase,
                        "multiple": round(final / ep, 2) if win else None,
                    }
                )

    def pct(a, b):
        return f"{a / b * 100:.1f}%" if b else "-"

    def med(xs):
        return round(sorted(xs)[len(xs) // 2], 2) if xs else None

    print("\n=== 买入位结果分布 ===")
    for b in bands:
        s = stat[b]
        if not s["n"]:
            continue
        n, w, l = s["n"], s["win"], s["lose"]
        print(f"\n[{b}] 入场点 n={n} | 最终上行 {pct(w, n)} | 归零 {pct(l, n)}")
        print(f"  赢家中位倍数 {med(s['multi'])}x | 输家最深回撤中位 {med(s['loss_ratio'])}（1=全亏）")
        print(f"  摸到过 0.75+ {pct(s['touch75'], n)} | 摸到过 0.90+ {pct(s['touch90'], n)}")
        print(f"  路径: {dict(s['paths'].most_common())}")
        for k, label in (("by_sport", "赛项"), ("by_mkt", "市场层"), ("by_phase", "阶段"), ("by_first", "首动")):
            parts = []
            for kk, (ww, ll) in sorted(s[k].items()):
                parts.append(f"{kk}:胜{ww}/负{ll}({pct(ww, ww + ll)})")
            print(f"  {label}: " + " | ".join(parts))

    with open(args.out, "w") as fh:
        json.dump(
            {
                "series": series_rows,
                "shape_cnt": dict(shape_cnt),
                "seq_cnt": dict(seq_cnt.most_common(100)),
                "seq_dir_cnt": dict(seq_dir_cnt.most_common(30)),
                "swing_n": dict(sorted(swing_n.items())),
                "entry_stat": {
                    b: {
                        "n": s["n"], "win": s["win"], "lose": s["lose"],
                        "median_multiple": med(s["multi"]),
                        "median_loss_ratio": med(s["loss_ratio"]),
                        "touch75": s["touch75"], "touch90": s["touch90"],
                        "paths": dict(s["paths"]),
                        "by_sport": {k: v for k, v in s["by_sport"].items()},
                        "by_mkt": {k: v for k, v in s["by_mkt"].items()},
                        "by_phase": {k: v for k, v in s["by_phase"].items()},
                        "by_first": {k: v for k, v in s["by_first"].items()},
                    }
                    for b, s in stat.items()
                },
                "entry_detail": detail,
            },
            fh,
            ensure_ascii=False,
            indent=1,
        )


if __name__ == "__main__":
    main()
