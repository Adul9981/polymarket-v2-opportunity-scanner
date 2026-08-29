#!/usr/bin/env python3
"""Unified price-path analysis for esports winner markets (read-only).

Ingests every available 1/5-minute price series in the project:
  - docs/forensics/data/<slug>/prices_*_1m.json      (CLOB dict format)
  - docs/data/snapshots/<event>/*.jsonl               (snapshot JSONL format)
  - runtime/observe_*.jsonl                           (live observation, nested)
  - runtime/bar_monitor_state/*__window.jsonl         (bar monitor windows)

For each side of each winner market, after an entry in a price band we
classify the forward path until settlement (pin = price sticks at >=0.98 or
<=0.02): P1 straight-up / P2 pullback-up / P3 deep-V / P4 spike-crash /
P5 grind-zero / P6 fast-crash / P7 sideways. Console summary + JSON output.
This is the evidence behind docs/forensics/PRICE_PATH_PLAYBOOK.md.
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
from collections import Counter, defaultdict


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def parse_ts(v):
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return int(dt.datetime.fromisoformat(s).timestamp())


def detect_pin(pts, near_frac=0.8, min_near=3):
    """First index whose price is pinned and stays pinned to the end."""
    n = len(pts)
    for i, (_, p) in enumerate(pts):
        if p >= 0.98 or p <= 0.02:
            tail = pts[i:]
            near = sum(1 for _, q in tail if q >= 0.97 or q <= 0.03)
            if near >= max(min_near, int(len(tail) * near_frac)):
                return i
    return None


def norm_side(side):
    return re.sub(r"[^a-z0-9]", "", str(side).lower())


def game_type(slug):
    s = slug.lower()
    for g in ("lol", "cs2", "dota2", "val"):
        if g in s:
            return g
    return "other"


SKIP_MKT_TOKENS = (
    "handicap", "first-blood", "firstblood", "fb1_", "fb2_", "fb1-", "fb2-",
    "over", "under", "total", "ou_", "ou-", "kill", "dragon", "baron",
    "tower", "first-map", "first_tower",
)


def norm_market(market_slug, fname):
    mkt = (market_slug or "").lower()
    m = re.search(r"(game\d+|map\d+|moneyline|match|winner|series)", mkt)
    if m:
        return m.group(1).lower()
    m2 = re.match(r"^(game\d+|map\d+|moneyline|winner|fb\d+)_", fname)
    if m2:
        return m2.group(1).lower()
    m3 = re.search(r"-(game\d+|map\d+|moneyline)$", fname)
    if m3:
        return m3.group(1).lower()
    return "match"


def skip_market(market, fname, market_slug):
    hay = f"{market} {fname} {market_slug or ''}".lower()
    return any(tok in hay for tok in SKIP_MKT_TOKENS)


def classify(entry_p, fwd):
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
        if dip < 0.08:
            lab = "P1 straight-up"
        elif dip < 0.20:
            lab = "P2 pullback-up"
        else:
            lab = "P3 deep-V"
    elif final <= 0.05:
        if rise >= 0.15:
            lab = "P4 spike-crash"
        else:
            tt = None
            for k, x in enumerate(fwd):
                if x[1] <= 0.10:
                    tt = (x[0] - fwd[0][0]) / 60
                    break
            lab = "P6 fast-crash" if (tt is not None and tt <= 10) else "P5 grind-zero"
    else:
        lab = "P7 sideways"
    return lab, max_p, min_p, rise, dip, first, final


def find_entries(pts, lo, hi, gap_min=10, cap=15):
    out = []
    last = None
    for i, (t, p) in enumerate(pts):
        if lo <= p <= hi:
            if last is None or (t - last) >= gap_min * 60:
                out.append(i)
                last = t
                if len(out) >= cap:
                    break
    return out


def make_record(slug, market, side, pts, source, fname):
    pin = detect_pin(pts)
    if pin is None or pin < 5:
        return None  # partial / already-decided series are not usable
    arr = pts[: pin + 1]
    return {
        "slug": slug,
        "market": market,
        "side": side,
        "side_norm": norm_side(side),
        "game": game_type(slug),
        "source": source,
        "fname": fname,
        "pts": arr,
    }


def scan_snapshot_file(path):
    """Snapshot JSONL: {timestamp, price, market_slug?, side?} per line."""
    lines = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except Exception:
                continue
    if not lines:
        return []
    try:
        pts = sorted((parse_ts(x.get("timestamp", x.get("ts"))), float(x["price"])) for x in lines)
    except Exception:
        return []
    if len(pts) < 5:
        return []
    x0 = lines[0]
    market = norm_market(x0.get("market_slug"), os.path.basename(path))
    if skip_market(market, os.path.basename(path), x0.get("market_slug")):
        return []
    side = x0.get("side") or os.path.basename(path).split("__")[-1].replace(".jsonl", "").replace("_", " ")
    slug = x0.get("event_slug") or os.path.basename(os.path.dirname(path))
    rec = make_record(slug, market, side, pts, "snapshot", os.path.basename(path))
    return [rec] if rec else []


def scan_forensics(meta):
    """CLOB dict format in docs/forensics/data/<slug>/."""
    out = []
    for slug, (gs, dec, base) in meta.items():
        for name, mkey in (
            ("g1_winner_1m", "g1"),
            ("g2_winner_1m", "g2"),
            ("match_winner_1m", "match"),
        ):
            path = os.path.join(base, f"prices_{name}.json")
            if not os.path.exists(path):
                continue
            h = sorted(load_json(path)["history"], key=lambda x: x["t"])
            if not h:
                continue
            settle = dec.get(mkey)
            if isinstance(settle, str):
                settle = parse_ts(settle)
            if not gs or not settle:
                continue
            pts = [(x["t"], x["p"]) for x in h if gs - 3600 <= x["t"] <= settle + 120]
            if len(pts) < 5:
                continue
            rec = make_record(slug, "game1" if mkey == "g1" else ("game2" if mkey == "g2" else "match"),
                              "winner", pts, "forensics", name)
            if rec:
                out.append(rec)
                comp = {"pts": [(t, round(1 - p, 4)) for t, p in pts]}
                rec2 = make_record(slug, rec["market"], "loser", comp["pts"], "forensics", name)
                if rec2:
                    out.append(rec2)
    return out


def scan_observe(pattern):
    out = []
    for path in glob.glob(pattern):
        slug = os.path.basename(path).replace("observe_", "").replace(".jsonl", "")
        buckets = defaultdict(list)
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    x = json.loads(line)
                except Exception:
                    continue
                try:
                    ts = parse_ts(x.get("ts") or x.get("timestamp"))
                except Exception:
                    continue
                for mkt in ("game1", "game2", "moneyline"):
                    teams = x.get(mkt)
                    if not isinstance(teams, dict):
                        continue
                    for side, price in teams.items():
                        buckets[(mkt, side)].append((ts, float(price)))
        for (mkt, side), pts in buckets.items():
            pts = sorted(pts)
            if len(pts) < 5:
                continue
            rec = make_record(slug, mkt, side, pts, "observe", os.path.basename(path))
            if rec:
                out.append(rec)
    return out


def scan_bar_windows(pattern):
    out = []
    for path in glob.glob(pattern):
        base = os.path.basename(path).replace("__window.jsonl", "")
        parts = base.split("__")
        slug = parts[0]
        market = norm_market("", parts[1]) if len(parts) > 1 else "match"
        side = parts[2] if len(parts) > 2 else "unknown"
        if skip_market(market, os.path.basename(path), ""):
            continue
        pts = []
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    x = json.loads(line)
                    pts.append((parse_ts(x.get("timestamp", x.get("ts"))), float(x["price"])))
                except Exception:
                    continue
        pts = sorted(pts)
        if len(pts) < 5:
            continue
        rec = make_record(slug, market, side, pts, "bar_window", os.path.basename(path))
        if rec:
            out.append(rec)
    return out


def load_records(snapshots_glob, forensics_glob, observe_glob, bar_glob):
    """Load + dedup all usable price series from the four data roots."""
    # 1. snapshots (preferred source)
    records = []
    snapshot_slugs = set()
    for d in sorted(glob.glob(snapshots_glob)):
        if not os.path.isdir(d):
            continue
        slug = os.path.basename(d)
        for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            base = os.path.basename(f)
            if base in ("classification.jsonl", "validation.jsonl") or base.startswith("comments"):
                continue
            records.extend(scan_snapshot_file(f))
            snapshot_slugs.add(slug)

    # 2. forensics dict format only for slugs not covered by snapshots
    meta = {}
    for lp in glob.glob(os.path.join(forensics_glob, "labels_report.json")):
        d = load_json(lp)
        slug = d["event_slug"]
        if slug in snapshot_slugs:
            continue
        try:
            gs = parse_ts(d["game_start"])
        except Exception:
            gs = None
        dec = {}
        for k, v in d.get("decisions", {}).items():
            try:
                dec[k] = parse_ts(v)
            except Exception:
                dec[k] = v
        meta[slug] = (gs, dec, os.path.dirname(lp))
    records.extend(scan_forensics(meta))

    # 3. observe + bar windows (fallback; dedup later)
    records.extend(scan_observe(observe_glob))
    records.extend(scan_bar_windows(bar_glob))

    # 4. fill missing opposite side with complement (1 - p) so both sides
    #    of every market are represented even when only one side was captured
    by_market = defaultdict(list)
    for r in records:
        by_market[(r["slug"], r["market"])].append(r)
    extra = []
    single_side_markets = 0
    for (slug, market), rs in by_market.items():
        present = {r["side_norm"] for r in rs}
        if len(present) == 1:
            single_side_markets += 1
        for r in rs:
            comp_side = f"{r['side']}·反向"
            comp_norm = norm_side(r["side"]) + "_opp"
            if comp_norm in present:
                continue  # real file for the other side exists
            comp = dict(r)
            comp["pts"] = [(t, round(1 - p, 4)) for t, p in r["pts"]]
            comp["side"] = comp_side
            comp["side_norm"] = comp_norm
            comp["source"] = r["source"] + "+comp"
            extra.append(comp)
    records.extend(extra)

    # 5. dedup: same (slug, market, side_norm) -> keep longest
    best = {}
    for r in records:
        key = (r["slug"], r["market"], r["side_norm"])
        if key not in best or len(r["pts"]) > len(best[key]["pts"]):
            best[key] = r
    records = list(best.values())
    return records, single_side_markets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", default="docs/data/snapshots/*")
    ap.add_argument("--forensics", default="docs/forensics/data/lol-*")
    ap.add_argument("--observe", default="runtime/observe_*.jsonl")
    ap.add_argument("--bar-windows", default="runtime/bar_monitor_state/*__window.jsonl")
    ap.add_argument("--out", default="/tmp/path_analysis_all.json")
    args = ap.parse_args()

    records, single_side_markets = load_records(args.snapshots, args.forensics, args.observe, args.bar_windows)

    # analysis
    bands = {
        "0.20-0.40": (0.20, 0.40),
        "0.40-0.55": (0.40, 0.55),
        "0.55-0.65(60c)": (0.55, 0.65),
    }
    agg_all = {b: Counter() for b in bands}
    agg_game = {g: {b: Counter() for b in bands} for g in ("lol", "cs2", "dota2", "val", "other")}
    agg_mkt = {"game": {b: Counter() for b in bands}, "match": {b: Counter() for b in bands}}
    examples = {b: defaultdict(list) for b in bands}
    first_move = {b: Counter() for b in bands}
    touch = {b: Counter() for b in bands}
    series_rows = []

    for r in records:
        arr = r["pts"]
        o = sum(p for _, p in arr[:5]) / 5
        hi = max(p for _, p in arr)
        lo = min(p for _, p in arr)
        fin = arr[-1][1]
        if fin >= 0.95:
            sp = "P1" if (o - lo < 0.08) else ("P3" if (o - lo >= 0.20) else "P2")
        elif fin <= 0.05:
            drop_ts = next(((x[0] - arr[0][0]) / 60 for x in arr if x[1] <= 0.10), 999)
            sp = "P6" if drop_ts <= 10 else ("P4" if (hi - o >= 0.15) else "P5")
        else:
            sp = "P7"
        series_rows.append(
            {
                "slug": r["slug"], "market": r["market"], "side": r["side"],
                "game": r["game"], "open": round(o, 3), "high": round(hi, 3),
                "low": round(lo, 3), "final": round(fin, 2), "path": sp,
                "source": r["source"], "n": len(arr),
            }
        )
        for b, (blo, bhi) in bands.items():
            for j in find_entries(arr, blo, bhi):
                ep = arr[j][1]
                fwd = arr[j:]
                lab, mx, mn, rise, dip, first, final = classify(ep, fwd)
                agg_all[b][lab] += 1
                agg_game[r["game"]][b][lab] += 1
                mkt_type = "game" if re.match(r"^(game\d+|map\d+)$", r["market"]) else "match"
                agg_mkt[mkt_type][b][lab] += 1
                first_move[b][first] += 1
                touch[b]["n"] += 1
                touch[b]["hit_0.75+"] += 1 if mx >= 0.75 else 0
                touch[b]["hit_0.90+"] += 1 if mx >= 0.90 else 0
                touch[b]["dip_<0.40"] += 1 if mn < 0.40 else 0
                touch[b]["dip_<0.20"] += 1 if mn < 0.20 else 0
                if len(examples[b][lab]) < 4:
                    examples[b][lab].append(
                        {
                            "slug": r["slug"], "market": r["market"], "side": r["side"],
                            "entry": round(ep, 2),
                            "t": dt.datetime.utcfromtimestamp(arr[j][0]).strftime("%m-%d %H:%M"),
                            "max": round(mx, 3), "min": round(mn, 3), "first": first,
                            "final": round(final, 2), "game": r["game"],
                        }
                    )

    # 6. report
    print(f"=== usable series: {len(records)} (dedup) ===")
    print(f"    single-side markets complemented: {single_side_markets}")
    for g in ("lol", "cs2", "dota2", "val", "other"):
        n = sum(1 for s in series_rows if s["game"] == g)
        if n:
            print(f"  {g}: {n}")
    print()
    print("=== per-band counts (all games) ===")
    for b in bands:
        print(b, dict(agg_all[b]))
    print()
    print("=== first move after entry (per band, all games) ===")
    for b in bands:
        n = sum(first_move[b].values())
        print(
            b, {k: (f"{v} ({v / n * 100:.0f}%)" if n else "0") for k, v in first_move[b].items()},
            f"n={n}",
        )
    print()
    print("=== chance to lock profit / dip after entry (per band) ===")
    for b in bands:
        t = touch[b]
        n = t["n"]
        if not n:
            continue
        print(
            f"{b}: n={n} hit0.75+={t['hit_0.75+'] / n * 100:.0f}% "
            f"hit0.90+={t['hit_0.90+'] / n * 100:.0f}% "
            f"dip<0.40={t['dip_<0.40'] / n * 100:.0f}% "
            f"dip<0.20={t['dip_<0.20'] / n * 100:.0f}%"
        )
    print()
    print("=== per-band counts by game ===")
    for g in ("lol", "cs2", "dota2", "val"):
        for b in bands:
            if agg_game[g][b]:
                print(f"{g} {b}: {dict(agg_game[g][b])}")
    print()
    print("=== per-band counts by market type (小局 vs 整场) ===")
    for mt in ("game", "match"):
        for b in bands:
            if agg_mkt[mt][b]:
                print(f"{mt} {b}: {dict(agg_mkt[mt][b])}")
    print()
    print("=== series-level path counts ===")
    for g in ("lol", "cs2", "dota2", "val", "other"):
        c = Counter(s["path"] for s in series_rows if s["game"] == g)
        if c:
            print(g, dict(c))
    print()
    print("=== representative examples ===")
    for b in bands:
        for lab in agg_all[b]:
            print(f"-- [{b}] {lab}: {agg_all[b][lab]}")
            for e in examples[b][lab]:
                print(
                    f"   {e['slug']} {e['market']} {e['side']} @{e['entry']} {e['t']} "
                    f"first={e['first']} max={e['max']} min={e['min']} final={e['final']} [{e['game']}]"
                )

    with open(args.out, "w") as fh:
        json.dump(
            {
                "agg": {b: dict(c) for b, c in agg_all.items()},
                "agg_game": {g: {b: dict(c) for b, c in agg_game[g].items()} for g in agg_game},
                "agg_mkt": {mt: {b: dict(c) for b, c in agg_mkt[mt].items()} for mt in agg_mkt},
                "series": series_rows,
                "examples": {b: {k: v for k, v in ex.items()} for b, ex in examples.items()},
                "first_move": {b: dict(c) for b, c in first_move.items()},
                "touch": {b: dict(c) for b, c in touch.items()},
            },
            fh,
            ensure_ascii=False,
            indent=1,
        )


if __name__ == "__main__":
    main()
