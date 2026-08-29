#!/usr/bin/env python3
"""Sigma-p mispricing scanner for Polymarket neg-risk groups (read-only).

Implements SCANNER_SPEC.md two-level design, hardened with findings from the
e46m3 dissection (2026-08-12):

  * Level 1 (coarse): mark-price SigmaP from Gamma outcomePrices, grouped by
    negRiskMarketID so multi-group events never aggregate into fake extremes.
  * Level 2 (deep): CLOB order books. Executable cost is computed by walking
    the ask ladder per leg (mark prices are NOT executable), depth-aware,
    with quality flags (stale book / degenerate ask / YES+NO consistency),
    subgroup view for liquid subsets, and a rebate-adjusted net edge.

Read-only: no orders, no private keys. Outputs:
  runtime/forensics/scan_YYYY-MM-DD.jsonl   (one row per group, per spec)
  reports/sigma_p_scan_<ts>.json            (level-1 summary)
  reports/sigma_p_deep_<ts>.json            (level-2 summary)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

ROOT = "/Users/ad/Documents/polymarket"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# e46m3 dissection calibration (STRATEGY_LIBRARY.md / data/e46m3/stats.json)
DEFAULT_COARSE_THRESHOLD = 0.02      # |mark SigmaP - 1| entry threshold
DEFAULT_FEE_RATE = 0.05              # Polymarket taker fee rate (weather/sports 0.05, politics 0.04, geopolitics 0)
DEFAULT_GAS_USD = 0.05               # per-cycle gas for 7-leg buy + Convert on Polygon
DEFAULT_TAKER_REBATE = 0.0           # share of fees returned to taker (tiered program; 0 = conservative)
DEFAULT_SAFETY = 0.001               # small extra margin per X (0.1%)
DEFAULT_X = 1.0                      # shares per leg in level-2 math
MIN_LEGS = 5                         # groups below this are skipped
DEFAULT_MIN_LIQ = 25.0               # group liquidity floor for discovery


def taker_fee(price: float, shares: float, fee_rate: float) -> float:
    """Polymarket fee formula: C * feeRate * p * (1 - p)."""
    if price is None or price <= 0 or price >= 1:
        return 0.0
    return shares * fee_rate * price * (1.0 - price)


def http_json(url: str, retries: int = 4, timeout: int = 20) -> dict | list:
    """GET a JSON endpoint with bounded retry/backoff."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), ssl.SSLError):
                # Local proxy/MITM with self-signed cert: fall back to
                # unverified context (public read-only APIs only).
                try:
                    ctx = ssl._create_unverified_context()
                    req = urllib.request.Request(url, headers=UA)
                    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                        return json.loads(r.read().decode("utf-8"))
                except Exception as e2:
                    last = e2
                    time.sleep(0.8 * (attempt + 1))
                    continue
        except Exception as e:  # network / parse errors
            last = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url} ({last})")


def parse_prices(market: dict) -> list[str]:
    v = market.get("outcomePrices") or []
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            return []
    return v


def group_markets(event: dict, require_traded: bool = True) -> dict[str, list[dict]]:
    """Group event markets by negRiskMarketID (multi-group events stay apart).

    Markets with no real two-sided quotes (default 0.5 prices, no bid) would
    pollute SigmaP, so they are excluded unless require_traded=False. Note:
    gamma's `funded` flag is unreliable in list responses; lastTradePrice plus
    bestBid is the trustworthy signal.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in event.get("markets", []):
        if require_traded and (
            m.get("lastTradePrice") is None or m.get("bestBid") is None
        ):
            continue
        gid = m.get("negRiskMarketID") or ""
        prices = parse_prices(m)
        if not gid or not prices:
            continue
        try:
            float(prices[0])
        except (TypeError, ValueError):
            continue
        groups[gid].append(m)
    return groups


def level1_slug(slug: str) -> list[dict]:
    """Level-1 coarse scan for one event slug -> group rows."""
    url = f"{GAMMA}/events?slug={urllib.parse.quote(slug)}"
    event = http_json(url)[0]
    return _rows_from_event(event)


def _rows_from_event(
    event: dict, require_traded: bool = True, min_liq: float = DEFAULT_MIN_LIQ
) -> list[dict]:
    rows = []
    end_raw = event.get("endDate") or ""
    try:
        end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
    except Exception:
        end_dt = None
    if end_dt is not None and end_dt < datetime.now(timezone.utc):
        # Ended-but-unresolved events carry stale quotes (e.g. UN SG election
        # ended 2026-02-28 yet still listed): not tradeable, exclude.
        return rows
    for gid, markets in group_markets(event, require_traded).items():
        prices = [float(parse_prices(m)[0]) for m in markets if parse_prices(m)]
        if len(prices) < MIN_LEGS:
            continue
        sp = sum(prices)
        suspicious = sp > 2.5 or sp < 0.5
        liq = sum(
            float(m.get("liquidityNum") or 0) for m in markets
        )
        if liq < min_liq:
            continue
        rows.append(
            {
                "negRiskMarketID": gid,
                "sigmaP": round(sp, 4),
                "legs": len(prices),
                "title": event.get("title") or "",
                "slug": event.get("slug") or "",
                "category": event.get("category") or "",
                "endDate": event.get("endDate") or "",
                "suspicious": suspicious,
                "liquidity": round(liq, 2),
            }
        )
    return rows


def level1_discover(
    limit: int = 1000,
    order: str = "endDate",
    ascending: bool = True,
    filter_re: str | None = None,
    min_liq: float = DEFAULT_MIN_LIQ,
) -> list[dict]:
    """Discovery mode: level-1 straight from the events list (embedded markets).

    order=endDate+ascending surfaces soon-ending (live match / weather) groups;
    a regex filter targets esports / score / weather scenarios.
    """
    pat = re.compile(filter_re, re.IGNORECASE) if filter_re else None
    rows = []
    seen = 0
    offset = 0
    page = 100  # gamma caps page size at 100
    while seen < limit:
        url = (
            f"{GAMMA}/events?closed=false&limit={page}&offset={offset}"
            f"&order={order}&ascending={'true' if ascending else 'false'}"
        )
        try:
            events = http_json(url)
        except Exception:
            break  # API offset cap / transient failure: keep what we have
        if not events:
            break
        for ev in events:
            seen += 1
            if not ev.get("negRisk") or not ev.get("markets"):
                continue
            title = ev.get("title") or ""
            slug = ev.get("slug") or ""
            if pat and not (pat.search(title) or pat.search(slug)):
                continue
            rows.extend(_rows_from_event(ev, min_liq=min_liq))
        offset += page
    return rows


def cost_to_fill(asks: list[dict], amount: float) -> tuple[float, float]:
    """Walk the ask ladder; return (cost, filled)."""
    levels = sorted(
        [(float(a["price"]), float(a["size"])) for a in asks], key=lambda x: x[0]
    )
    cost, filled = 0.0, 0.0
    for price, size in levels:
        if filled >= amount - 1e-12:
            break
        take = min(amount - filled, size)
        cost += price * take
        filled += take
    return cost, filled


def quality_flags(book_yes: dict, book_no: dict, yes_ask: float, no_ask: float) -> list[str]:
    """Heuristics for quotes that should not be trusted."""
    flags = []
    try:
        ts_yes = float(book_yes.get("timestamp", 0))
    except (TypeError, ValueError):
        ts_yes = 0.0
    try:
        ts_no = float(book_no.get("timestamp", 0))
    except (TypeError, ValueError):
        ts_no = 0.0
    age = max(time.time() - ts_yes, time.time() - ts_no)
    if age > 300:
        flags.append(f"stale_book_{int(age)}s")
    if yes_ask >= 0.995 and no_ask >= 0.995:
        flags.append("degenerate_both_sides_0.995+")
    if 0 < no_ask < 0.5 and yes_ask >= 0.995:
        flags.append("degenerate_yes_wall")
    if 0 < yes_ask < 0.5 and no_ask >= 0.995:
        flags.append("degenerate_no_wall")
    return flags


def level2_group(
    slug: str,
    gid: str,
    markets: list[dict],
    x: float,
    event_end: str | None = None,
    convert_fee_bps: int = 0,
    fee_rate: float = DEFAULT_FEE_RATE,
    gas_usd: float = DEFAULT_GAS_USD,
    taker_rebate: float = DEFAULT_TAKER_REBATE,
) -> dict:
    """Level-2 deep scan: order-book executable cost for one group."""
    legs = []
    yes_asks, no_asks = [], []
    no_cost, yes_cost = 0.0, 0.0
    no_fee, yes_fee = 0.0, 0.0
    no_filled_min = None
    yes_filled_min = None
    n_no_ok, n_yes_ok = 0, 0
    no_cost_ok, yes_cost_ok = 0.0, 0.0
    mark_prices = []
    for m in markets:
        p = parse_prices(m)
        if p:
            try:
                mark_prices.append(float(p[0]))
            except (TypeError, ValueError):
                pass
        token_ids = m.get("clobTokenIds") or []
        if isinstance(token_ids, str):
            try:
                token_ids = json.loads(token_ids)
            except json.JSONDecodeError:
                token_ids = []
        if len(token_ids) < 2:
            continue
        yes_id, no_id = token_ids[0], token_ids[1]
        try:
            b_yes = http_json(f"{CLOB}/book?token_id={yes_id}")
        except Exception:
            b_yes = {"asks": [], "bids": [], "timestamp": 0}
        try:
            b_no = http_json(f"{CLOB}/book?token_id={no_id}")
        except Exception:
            b_no = {"asks": [], "bids": [], "timestamp": 0}
        y_ask = float(b_yes["asks"][0]["price"]) if b_yes.get("asks") else None
        n_ask = float(b_no["asks"][0]["price"]) if b_no.get("asks") else None
        y_cost, y_filled = cost_to_fill(b_yes.get("asks", []), x)
        n_cost, n_filled = cost_to_fill(b_no.get("asks", []), x)
        n_ok = n_ask is not None and n_filled >= x - 1e-9
        y_ok = y_ask is not None and y_filled >= x - 1e-9
        if n_ask is not None:
            no_cost += n_cost
            no_filled_min = n_filled if no_filled_min is None else min(no_filled_min, n_filled)
        if n_ok:
            n_no_ok += 1
            no_cost_ok += n_cost
            no_fee += taker_fee(n_cost / n_filled if n_filled > 0 else None, n_filled, fee_rate)
        if y_ask is not None:
            yes_cost += y_cost
            yes_filled_min = y_filled if yes_filled_min is None else min(yes_filled_min, y_filled)
        if y_ok:
            n_yes_ok += 1
            yes_cost_ok += y_cost
            yes_fee += taker_fee(y_cost / y_filled if y_filled > 0 else None, y_filled, fee_rate)
        flags = quality_flags(b_yes, b_no, y_ask or 1.0, n_ask or 1.0)
        if n_ask is None:
            flags.append("no_book_empty")
        if y_ask is None:
            flags.append("yes_book_empty")
        legs.append(
            {
                "title": m.get("groupItemTitle") or m.get("question") or "",
                "yes_ask": y_ask,
                "no_ask": n_ask,
                "yes_cost": round(y_cost, 6),
                "no_cost": round(n_cost, 6),
                "yes_filled": round(y_filled, 4),
                "no_filled": round(n_filled, 4),
                "no_ok": n_ok,
                "yes_ok": y_ok,
                "flags": flags,
            }
        )
        yes_asks.append(y_ask)
        no_asks.append(n_ask)

    n = len(legs)
    ask_sump = round(sum(a for a in yes_asks if a is not None), 4) if yes_asks else None
    # Convert payout is (n-1) * X * (1 - feeBips/10000) in V2 (fee can be
    # market-specific; verified 0 bps on NFL/NBA/MLB/EPL/UCL groups, 2026-08-15).
    no_theory = (n - 1) * x * (1 - convert_fee_bps / 10_000)
    # A full-set trade is only possible when EVERY leg is fillable at X.
    no_depth_ok = bool(n_no_ok == n)
    yes_depth_ok = bool(n_yes_ok == n)

    # Deterministic side: NO full-set -> Convert pays (n-1)X cash.
    # If some legs are missing, the set cannot be completed: mark cost as infeasible.
    no_exec_cost = no_cost if no_depth_ok else float("inf")
    no_gross = no_theory - no_exec_cost
    no_net = no_gross - no_fee - gas_usd - DEFAULT_SAFETY * x
    no_net_rebate = no_net + no_fee * taker_rebate
    # YES side: full YES set -> theoretical value X at settlement.
    yes_exec_cost = yes_cost if yes_depth_ok else float("inf")
    yes_gross = x - yes_exec_cost
    yes_net = yes_gross - yes_fee - gas_usd - DEFAULT_SAFETY * x
    yes_net_rebate = yes_net + yes_fee * taker_rebate

    # Subgroup view: SigmaP over legs whose NO side is actually fillable at X.
    fillable_yes = [a for a in yes_asks if a is not None]
    subgroup_p = None
    if fillable_yes and len(fillable_yes) >= MIN_LEGS:
        subgroup_p = round(sum(fillable_yes), 4)

    # Exhaustiveness / duration caveat: for SigmaP<1 (YES full-set) the edge is
    # only real when the leg set covers the whole outcome space. Politics-style
    # groups usually omit a "field" leg -> low SigmaP is residual probability,
    # not arbitrage. Long-dated YES passes are duration trades, not instant
    # Convert edges (e46m3's mode).
    field_hint = any(
        re.search(
            r"\b(other|another|field|someone else|none of the above|any other)\b",
            l["title"].lower(),
        )
        for l in legs
    )
    try:
        days_to_end = (
            datetime.fromisoformat((event_end or "").replace("Z", "+00:00"))
            - datetime.now(timezone.utc)
        ).days
    except Exception:
        days_to_end = None

    verdict_no = "pass" if (no_depth_ok and no_net_rebate > 0) else "fail"
    verdict_yes = "pass" if (yes_depth_ok and yes_net_rebate > 0) else "fail"
    notes = []
    if verdict_yes == "pass" and not field_hint and (days_to_end is None or days_to_end > 90):
        verdict_yes = "pass_long_dated"
        notes.append("YES set lacks a field/other leg; long-dated SigmaP<1 may be residual probability or duration value, not arbitrage.")
    if verdict_yes == "pass" and days_to_end is not None and days_to_end <= 90 and not field_hint:
        notes.append("short-dated YES pass: verify leg set is exhaustive before relying on it.")

    return {
        "ts": int(time.time()),
        "group": slug,
        "negRiskMarketID": gid,
        "n_legs": n,
        "ask_sump": ask_sump,
        "subgroup_sump_fillable": subgroup_p,
        "x": x,
        "mark_sump": round(sum(mark_prices), 4) if mark_prices else None,
        "mark_edge_per_x": round(sum(mark_prices) - 1, 4) if mark_prices else None,
        "exec_edge_per_x": round(no_theory - no_cost, 4) if no_depth_ok else None,
        "no_cost": round(no_cost, 6),
        "no_fee": round(no_fee, 6),
        "no_theory": round(no_theory, 6),
        "no_gross": round(no_gross, 6),
        "no_net": round(no_net, 6),
        "no_net_rebate": round(no_net_rebate, 6),
        "no_depth_ok": no_depth_ok,
        "no_fillable_min": round(no_filled_min, 4) if no_filled_min is not None else 0.0,
        "n_no_fillable": n_no_ok,
        "n_yes_fillable": n_yes_ok,
        "yes_cost": round(yes_cost, 6),
        "yes_fee": round(yes_fee, 6),
        "yes_gross": round(yes_gross, 6),
        "yes_net": round(yes_net, 6),
        "yes_net_rebate": round(yes_net_rebate, 6),
        "yes_depth_ok": yes_depth_ok,
        "yes_fillable_min": round(yes_filled_min, 4) if yes_filled_min is not None else 0.0,
        "side": "NO" if no_net_rebate > yes_net_rebate else "YES",
        "verdict": verdict_no if no_net_rebate >= yes_net_rebate else verdict_yes,
        "days_to_end": days_to_end,
        "exhaustive_hint": field_hint,
        "notes": "; ".join(notes),
        "legs": legs,
    }


def level2_slug(
    slug: str,
    x: float,
    convert_fee_bps: int = 0,
    fee_rate: float = DEFAULT_FEE_RATE,
    gas_usd: float = DEFAULT_GAS_USD,
    taker_rebate: float = DEFAULT_TAKER_REBATE,
) -> list[dict]:
    url = f"{GAMMA}/events?slug={urllib.parse.quote(slug)}"
    event = http_json(url)[0]
    out = []
    for gid, markets in group_markets(event).items():
        if len(markets) < MIN_LEGS:
            continue
        out.append(level2_group(slug, gid, markets, x, event.get("endDate"),
                                convert_fee_bps, fee_rate, gas_usd, taker_rebate))
    return out


def profile_slug(
    slug: str,
    xs: list[float],
    fee_rate: float = DEFAULT_FEE_RATE,
    gas_usd: float = DEFAULT_GAS_USD,
    taker_rebate: float = DEFAULT_TAKER_REBATE,
) -> dict:
    """NO-side depth profile: how executable edge decays as X grows."""
    event = http_json(f"{GAMMA}/events?slug={urllib.parse.quote(slug)}")[0]
    groups_ = group_markets(event)
    if not groups_:
        return {"group": slug, "error": "no tradable group"}
    gid = max(groups_, key=lambda g: len(groups_[g]))
    markets = groups_[gid]
    n = len(markets)
    theory_per = n - 1
    books = []
    for m in markets:
        ids = m.get("clobTokenIds") or []
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except json.JSONDecodeError:
                ids = []
        try:
            b = http_json(f"{CLOB}/book?token_id={ids[1]}")
        except Exception:
            b = {"asks": []}
        books.append(b.get("asks", []))
    depth = [sum(float(a["size"]) for a in asks) for asks in books]
    max_full = min(depth) if depth else 0.0
    rows = []
    for X in xs:
        if X > max_full + 1e-9:
            rows.append({"x": X, "cost": None})
            continue
        cost = 0.0
        fee = 0.0
        for asks in books:
            c, filled = cost_to_fill(asks, X)
            cost += c
            if filled > 0:
                fee += taker_fee(c / filled, filled, fee_rate)
        gross = theory_per * X - cost
        net = gross - fee - gas_usd - DEFAULT_SAFETY * X + fee * taker_rebate
        rows.append({
            "x": X,
            "cost": round(cost, 4),
            "fee": round(fee, 4),
            "gross": round(gross, 4),
            "net": round(net, 4),
            "gross_pct": round(gross / (theory_per * X) * 100, 3) if theory_per * X else None,
        })
    return {
        "group": slug,
        "n_legs": n,
        "no_theory_per_x": theory_per,
        "depth_min": round(min(depth), 1) if depth else 0.0,
        "depth_max": round(max(depth), 1) if depth else 0.0,
        "max_full_set_x": round(max_full, 1),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only SigmaP scanner")
    ap.add_argument("--slugs", help="comma-separated event slugs")
    ap.add_argument("--snapshot", default=None, help="reuse slugs from a prior summary JSON")
    ap.add_argument("--discover", action="store_true", help="scan recent neg-risk events")
    ap.add_argument("--deep", help="comma-separated slugs for level-2 order-book scan")
    ap.add_argument("--profile", help="comma-separated slugs for NO-side depth-profile scan")
    ap.add_argument("--threshold", type=float, default=DEFAULT_COARSE_THRESHOLD)
    ap.add_argument("--direction", choices=["gt", "lt", "both"], default="both",
                    help="gt: only SigmaP>1+threshold (buy NO full-set -> Convert); "
                         "lt: only SigmaP<1-threshold (buy YES full-set); both: |SigmaP-1|>threshold")
    ap.add_argument("--x", type=float, default=DEFAULT_X, help="shares per leg (level 2)")
    ap.add_argument("--limit", type=int, default=1000, help="discovery events limit")
    ap.add_argument("--min-liq", type=float, default=DEFAULT_MIN_LIQ,
                    help="minimum group liquidity (USD) for discovery rows")
    ap.add_argument("--convert-fee-bps", type=int, default=0,
                    help="NegRiskAdapter convert fee in bps (0 on major groups, 2026-08-15)")
    ap.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE,
                    help="taker fee rate (0.05 weather/sports, 0.04 politics/finance, 0 geopolitics)")
    ap.add_argument("--gas-usd", type=float, default=DEFAULT_GAS_USD,
                    help="per-cycle gas cost in USD")
    ap.add_argument("--taker-rebate", type=float, default=DEFAULT_TAKER_REBATE,
                    help="share of taker fee returned via rebate program (0 = conservative)")
    ap.add_argument("--order", choices=["volume", "endDate"], default="endDate")
    ap.add_argument("--ascending", action="store_true", default=True)
    ap.add_argument("--descending", action="store_true")
    ap.add_argument("--filter", help="regex over title/slug for discovery")
    ap.add_argument("--json", action="store_true", help="emit machine-readable summary")
    args = ap.parse_args()

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scan_dir = os.path.join(ROOT, "runtime", "forensics")
    os.makedirs(scan_dir, exist_ok=True)

    rows: list[dict] = []
    if args.slugs:
        slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
        for s in slugs:
            rows.extend(level1_slug(s))
    elif args.snapshot:
        snap = json.load(open(args.snapshot))
        slugs = [g["slug"] for g in snap.get("groups", [])]
        for s in slugs:
            try:
                rows.extend(level1_slug(s))
            except Exception as e:
                print(f"skip {s}: {e}", file=sys.stderr)
    elif args.discover:
        asc = not args.descending
        rows.extend(level1_discover(args.limit, args.order, asc, args.filter, args.min_liq))
    elif not (args.deep or args.profile):
        ap.error("need --slugs, --snapshot, --discover, --deep or --profile")

    hits = []
    for r in rows:
        if r.get("suspicious"):
            continue
        dev = r["sigmaP"] - 1
        if args.direction == "gt" and dev > args.threshold:
            hits.append(r)
        elif args.direction == "lt" and dev < -args.threshold:
            hits.append(r)
        elif args.direction == "both" and abs(dev) > args.threshold:
            hits.append(r)

    jsonl_path = os.path.join(scan_dir, f"scan_{day}.jsonl")
    if rows:
        with open(jsonl_path, "a") as f:
            for r in hits:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {
        "captured_at": ts,
        "note": "mark-price level-1 coarse scan (funded markets only); suspicious SigmaP artifacts flagged; level-2 order-book ask screening required before any action.",
        "threshold": args.threshold,
        "direction": args.direction,
        "groups": sorted(rows, key=lambda r: abs(r["sigmaP"] - 1), reverse=True) if rows else [],
        "hits": hits,
    }
    summary_path = os.path.join(ROOT, "reports", f"sigma_p_scan_{ts}.json")
    if rows:
        with open(summary_path, "w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
    else:
        summary_path = None

    deep_rows: list[dict] = []
    if args.deep:
        for s in [x.strip() for x in args.deep.split(",") if x.strip()]:
            try:
                deep_rows.extend(level2_slug(s, args.x, args.convert_fee_bps,
                                             args.fee_rate, args.gas_usd, args.taker_rebate))
            except Exception as e:
                print(f"deep skip {s}: {e}", file=sys.stderr)
        deep_path = os.path.join(ROOT, "reports", f"sigma_p_deep_{ts}.json")
        with open(deep_path, "w") as f:
            json.dump({"captured_at": ts, "x": args.x, "groups": deep_rows}, f, ensure_ascii=False, indent=1)

    profile_path = None
    if args.profile:
        prof_rows = []
        for sl in [x.strip() for x in args.profile.split(",") if x.strip()]:
            try:
                prof_rows.append(profile_slug(sl, [1, 2, 5, 10, 25, 50, 100, 200, 500],
                                              args.fee_rate, args.gas_usd, args.taker_rebate))
            except Exception as e:
                print(f"profile skip {sl}: {e}", file=sys.stderr)
        profile_path = os.path.join(ROOT, "reports", f"sigma_p_profile_{ts}.json")
        with open(profile_path, "w") as f:
            json.dump({"captured_at": ts, "groups": prof_rows}, f, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps({"summary": summary_path, "jsonl": jsonl_path if rows else None,
                          "deep": deep_path if deep_rows else None,
                          "profile": profile_path if prof_rows else None,
                          "hits": len(hits)}, ensure_ascii=False))
        return 0

    if rows:
        print(f"scanned {len(rows)} groups -> {len(hits)} hits (|SigmaP-1|>{args.threshold})")
        print(f"summary: {summary_path}")
    if deep_rows:
        print(f"deep:    {deep_path}")
        for g in deep_rows:
            ex = g["exec_edge_per_x"]
            ex_s = f"{ex:+.4f}/X" if ex is not None else "infeasible"
            print(
                f"  [{g['verdict']}] {g['group']} legs={g['n_legs']} "
                f"mark_edge={g['mark_edge_per_x']:+.4f}/X exec_edge={ex_s} "
                f"NO_fillable={g['n_no_fillable']}/{g['n_legs']} "
                f"NO_net(rebate)={g['no_net_rebate']:+.4f}/X "
                f"YES_net(rebate)={g['yes_net_rebate']:+.4f}/X"
            )
    if profile_path:
        print(f"profile: {profile_path}")
        for g in prof_rows:
            if "error" in g:
                print(f"  [{g['group']}] error: {g['error']}")
                continue
            print(f"  {g['group']} legs={g['n_legs']} NO_theory={g['no_theory_per_x']}/X "
                  f"depth_min={g['depth_min']} max_full_set_X={g['max_full_set_x']}")
            for r in g["rows"]:
                if r["cost"] is None:
                    print(f"    X={r['x']:>4}  >depth")
                else:
                    print(f"    X={r['x']:>4}  cost=${r['cost']:>10.2f}  gross=${r['gross']:>9.3f}  "
                          f"fee=${r['fee']:>7.3f}  net=${r['net']:>9.3f}  gross%={r['gross_pct']:>7.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
