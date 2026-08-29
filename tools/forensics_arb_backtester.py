#!/usr/bin/env python3
"""Backtester for S-F1 complete-set arbitrage (SigmaP mispricing).

Replays per-leg YES mark-price history for a neg-risk group and simulates the
NO-side arbitrage loop defined in ARB_SCANNER_EXEC_DESIGN.md section 3.3:

  * detect episodes where sum(YES mark) >= 1 + entry_threshold
  * one round per episode: buy NO for every leg at mark-derived price plus
    slippage, pay taker fees and gas
  * Convert the full NO combo -> cash (n-1)*X (convert fee configurable)
  * net per round = proceeds - total outlay  (realized immediately, no holding)

YES-side (SigmaP < 1) is reported as informational only: it requires holding
until settlement (long-dated), so it is not counted as realized P&L.

Fees follow SCANNER_SPEC v1.1: taker fee = C * feeRate * p * (1-p);
gas default $0.05/round; convert fee 0 bps (measured on-chain 2026-08-15);
taker rebate default 0 (conservative). Order-book history is unavailable, so
executable cost is approximated from mark prices plus slippage (documented
capability gap 3 in ARB_SCANNER_EXEC_DESIGN.md).

Outputs:
  reports/forensics_arb_backtest_<case>_<ts>.md   human-readable report
  reports/forensics_arb_backtest_<case>_<ts>.json summary
  runtime/forensics/backtest_<case>_<ts>.jsonl    one row per round
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = "/Users/ad/Documents/polymarket"

DEFAULT_ENTRY_THRESHOLD = 0.02   # |SigmaP - 1| entry threshold (level-1)
DEFAULT_FEE_RATE = 0.05          # weather/sports taker fee rate
DEFAULT_GAS_USD = 0.05           # per-round gas for buy + Convert on Polygon
DEFAULT_SLIP_BPS = 100           # mark -> ask premium on NO legs (1.0%)
DEFAULT_CONVERT_FEE_BPS = 0      # measured 0 bps on-chain 2026-08-15
DEFAULT_TAKER_REBATE = 0.0       # share of taker fees returned (0 = conservative)
DEFAULT_X = 10.0                 # shares per leg per round
DEFAULT_STEP_S = 60              # replay grid step
DEFAULT_MAX_STALE_S = 900        # a leg is missing if no sample within this
DEFAULT_BUDGET_USD = 50.0        # suggested-X math target

MIN_LEGS = 5
SUSPICIOUS_HIGH = 2.5
SUSPICIOUS_LOW = 0.5


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S") + "Z"


def taker_fee(price: float, shares: float, fee_rate: float) -> float:
    """Polymarket taker fee formula: C * feeRate * p * (1 - p)."""
    if price is None or price <= 0 or price >= 1:
        return 0.0
    return shares * fee_rate * price * (1.0 - price)


def load_series_map(path: str) -> tuple[dict[str, list[tuple[float, float]]], dict]:
    """Load per-leg YES price history from two supported formats.

    1. Case bundle (Villarreal-style): top-level dict with "hist" mapping
       token id -> [{"t": ..., "p": ...}, ...] plus optional "sump_at",
       "activity", "trades", "sump_grid", "yes_tokens".
    2. Hist dict: top-level dict mapping outcome label -> [{"t","p"}, ...].

    Returns (series_map, meta). Keys of series_map are human labels when
    available, otherwise raw keys.
    """
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read input {path}: {e}")

    if isinstance(raw, dict) and isinstance(raw.get("hist"), dict):
        hist = raw["hist"]
        labels: dict[str, str] = {}
        yes_tokens = raw.get("yes_tokens")
        if isinstance(yes_tokens, dict):
            for tk, info in yes_tokens.items():
                if isinstance(info, dict) and info.get("label"):
                    labels[str(tk)] = str(info["label"])
        series: dict[str, list[tuple[float, float]]] = {}
        for tk, pts in hist.items():
            if not isinstance(pts, list):
                continue
            label = labels.get(str(tk), str(tk))
            series[label] = [(float(p["t"]), float(p["p"])) for p in pts if isinstance(p, dict) and "t" in p and "p" in p]
        return series, raw

    if isinstance(raw, dict):
        series = {}
        for k, v in raw.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "t" in v[0] and "p" in v[0]:
                series[str(k)] = [(float(p["t"]), float(p["p"])) for p in v]
        if series:
            return series, {"_mode": "hist-dict", "path": path}

    raise SystemExit(f"unsupported price-history format: {path}")


def build_grid(
    series_map: dict[str, list[tuple[float, float]]],
    step_s: int,
    max_stale_s: float,
) -> list[tuple[float, dict[str, float]]]:
    """Uniform grid over the union time window; forward-fill each leg.

    A grid point is kept only if every leg has a sample no older than
    max_stale_s (no fake constant-SigmaP episodes on dead markets).
    """
    ts_min = min(s[0][0] for s in series_map.values())
    ts_max = max(s[-1][0] for s in series_map.values())
    if not (ts_min < ts_max):
        raise SystemExit("price history has no time span")
    grid_ts = []
    t = ts_min
    while t <= ts_max:
        grid_ts.append(t)
        t += step_s

    arrays = {k: sorted(s) for k, s in series_map.items()}
    tol = min(step_s, 60)
    rows: list[tuple[float, dict[str, float]]] = []
    for g in grid_ts:
        prices: dict[str, float] = {}
        ok = True
        for k, arr in arrays.items():
            best: tuple[float, float] | None = None
            for sample in arr:
                if sample[0] <= g + tol:
                    best = sample
                else:
                    break
            if best is None or (g - best[0]) > max_stale_s:
                ok = False
                break
            p = best[1]
            if not (0.0 < p < 1.0):
                ok = False
                break
            prices[k] = p
        if ok:
            rows.append((g, prices))
    return rows


def detect_episodes(
    rows: list[tuple[float, dict[str, float]]], entry_threshold: float
) -> list[tuple[int, int]]:
    """Contiguous windows where SigmaP >= 1 + threshold (one round each)."""
    episodes: list[tuple[int, int]] = []
    start: int | None = None
    for i, (_, prices) in enumerate(rows):
        sp = sum(prices.values())
        active = (1.0 + entry_threshold) <= sp < SUSPICIOUS_HIGH
        if active and start is None:
            start = i
        elif not active and start is not None:
            episodes.append((start, i - 1))
            start = None
    if start is not None:
        episodes.append((start, len(rows) - 1))
    return episodes


def simulate_round(
    prices: dict[str, float],
    x: float,
    fee_rate: float,
    gas_usd: float,
    slip_bps: int,
    convert_fee_bps: int,
    taker_rebate: float,
) -> dict:
    """Simulate one NO-side round: buy full NO combo, Convert to cash."""
    n = len(prices)
    sump = sum(prices.values())
    slip = slip_bps / 1e4
    legs = []
    cost = 0.0
    fees = 0.0
    for k, p in sorted(prices.items()):
        q = min(1.0, (1.0 - p) * (1.0 + slip))
        c = q * x
        f = taker_fee(q, x, fee_rate)
        cost += c
        fees += f
        legs.append(
            {
                "leg": k,
                "yes_mark": round(p, 4),
                "no_exec": round(q, 4),
                "cost": round(c, 4),
                "fee": round(f, 4),
            }
        )
    rebate = taker_rebate * fees
    convert_fee = (n - 1) * x * convert_fee_bps / 1e4
    proceeds = (n - 1) * x - convert_fee
    outlay = cost + fees + gas_usd
    net = proceeds - outlay + rebate
    gross_edge = (sump - 1.0) * x
    return {
        "n": n,
        "sump": round(sump, 4),
        "cost_no_legs": round(cost, 6),
        "taker_fees": round(fees, 6),
        "gas_usd": round(gas_usd, 4),
        "convert_fee": round(convert_fee, 4),
        "rebate": round(rebate, 4),
        "total_outlay": round(outlay, 6),
        "proceeds": round(proceeds, 4),
        "gross_edge": round(gross_edge, 4),
        "net": round(net, 6),
        "friction": round(gross_edge - net, 4),
        "net_per_x": round(net / x, 6),
        "roi_pct": round(100.0 * net / outlay, 4) if outlay else None,
        "legs": legs,
    }


def nearest_grid_ts(rows: list[tuple[float, dict[str, float]]], ts: float) -> float | None:
    best = None
    best_d = None
    for g, _ in rows:
        d = abs(g - ts)
        if best_d is None or d < best_d:
            best, best_d = g, d
    return best if best_d is not None and best_d <= 900 else None


def reality_check(
    meta: dict,
    rows: list[tuple[float, dict[str, float]]],
    entry_threshold: float,
) -> dict:
    """Cross-check simulation against actual e46m3 on-chain activity."""
    out: dict = {}
    sp_by_ts = {g: sum(p.values()) for g, p in rows}

    sump_at = meta.get("sump_at")
    if isinstance(sump_at, list) and sump_at:
        vals = [float(r["sump"]) for r in sump_at if isinstance(r, dict) and "sump" in r]
        if vals:
            out["sump_at_actual"] = {
                "count": len(vals),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "mean": round(sum(vals) / len(vals), 4),
            }

    activity = meta.get("activity")
    if isinstance(activity, list):
        convs = [a for a in activity if isinstance(a, dict) and a.get("type") == "CONVERSION"]
        if convs:
            ts = [float(a["timestamp"]) for a in convs]
            in_window = sum(1 for t in ts if any(abs(g - t) <= 900 for g in sp_by_ts))
            out["conversions_actual"] = {
                "count": len(convs),
                "count_in_backtest_window": in_window,
                "window": [utc(min(ts)), utc(max(ts))],
            }

    trades = meta.get("trades")
    if isinstance(trades, list):
        buys = sorted(
            [a for a in trades if isinstance(a, dict) and a.get("side") == "BUY"],
            key=lambda a: float(a["timestamp"]),
        )
        actual_rounds: list[list[dict]] = []
        cur: list[dict] = []
        for a in buys:
            if cur and float(a["timestamp"]) - float(cur[-1]["timestamp"]) > 60:
                actual_rounds.append(cur)
                cur = []
            cur.append(a)
        if cur:
            actual_rounds.append(cur)
        cal = []
        for r in actual_rounds:
            ts = sum(float(a["timestamp"]) for a in r) / len(r)
            notional = sum(float(a["size"]) * float(a["price"]) for a in r)
            shares = sum(float(a["size"]) for a in r)
            g = nearest_grid_ts(rows, ts)
            row = {
                "ts": utc(ts),
                "n_fills": len(r),
                "notional_usd": round(notional, 2),
                "shares": round(shares, 2),
                "avg_fill_price": round(notional / shares, 4) if shares else None,
                "sigmaP_at_grid": round(sp_by_ts[g], 4) if g in sp_by_ts else None,
            }
            cal.append(row)
        if cal:
            out["actual_buy_rounds"] = cal
    return out


def pct(v: float, total: float) -> str:
    return f"{100.0 * v / total:.2f}%" if total else "n/a"


def write_report(
    args: argparse.Namespace,
    labels: list[str],
    rows: list[tuple[float, dict[str, float]]],
    episodes: list[tuple[int, int]],
    rounds: list[dict],
    totals: dict,
    sp_stats: dict,
    yes_side: dict,
    reality: dict,
    sensitivity: list[dict],
    out_md: str,
) -> None:
    n = len(labels)
    lines: list[str] = []
    add = lines.append
    add("# S-F1 完整集套利回测报告")
    add("")
    add(f"- 数据源：`{args.input}`")
    add(f"- 窗口：{utc(rows[0][0])} ~ {utc(rows[-1][0])}（{len(rows)} 个采样点，步长 {args.step_s}s）")
    add(f"- 组内腿数：{n}")
    add("")
    add("## 参数")
    add("")
    add(f"| 参数 | 值 |")
    add("| --- | --- |")
    add(f"| 入场阈值 \|Σp−1\| | ≥ {args.entry_threshold} |")
    add(f"| 每腿份额 X | ${args.x:g} |")
    add(f"| 滑点假设 | {args.slip_bps} bps（标记价→NO 成交价） |")
    add(f"| taker 费率 | {args.fee_rate}（天气/体育档） |")
    add(f"| taker 返佣 | {args.taker_rebate:.0%} |")
    add(f"| Convert 费率 | {args.convert_fee_bps} bps |")
    add(f"| 每轮 gas | ${args.gas_usd:g} |")
    add("")
    add("## Σp 统计（全套 YES 标记价之和）")
    add("")
    add("| 指标 | 值 |")
    add("| --- | --- |")
    add(f"| min / max | {sp_stats['min']:.4f} / {sp_stats['max']:.4f} |")
    add(f"| mean / median | {sp_stats['mean']:.4f} / {sp_stats['median']:.4f} |")
    add(f"| Σp ≥ 1+{args.entry_threshold} 的时间占比 | {pct(sp_stats['time_above'], len(rows))} |")
    add(f"| Σp ≤ 1−{args.entry_threshold} 的时间占比（YES 侧，仅信息） | {pct(sp_stats['time_below'], len(rows))} |")
    add(f"| 独立错价窗口（NO 侧） | {len(episodes)} 个 |")
    add(f"| YES 侧理论边（最低 Σp） | {yes_side['min_sump']:.4f} → 理论 (1−Σp)X = {yes_side['edge_per_x']:.4f}×X（需持有到结算，不计入已实现） |")
    add("")
    if not rounds:
        add("## 结论：无触发窗口")
        add("")
        add(f"窗口内 Σp 全程未达到入场阈值 {1 + args.entry_threshold:.3f}（max Σp = {sp_stats['max']:.4f}）。")
        add("这是有完整 Σp 分布证据的'无机会'结论，不是数据缺失。")
        add("")
        add("## 建议")
        add("")
        add("1. 扩大回测窗口（更多历史价格）或降低阈值观察；")
        add("2. 跑只读扫描器（Step 1）收集未来两周的实时窗口频率。")
        add("")
    else:
        add("## 回测轮次（NO 侧：买全套 NO → Convert → 现金 (n−1)X）")
        add("")
        add(f"共 **{len(rounds)} 轮**；每轮按该错价窗口首个采样点入场，不重复触发。")
        add("")
        nets = [r["net"] for r in rounds]
        add("| 指标 | 值 |")
        add("| --- | --- |")
        add(f"| 单轮净利 mean / median | ${sum(nets)/len(nets):.4f} / ${sorted(nets)[len(nets)//2]:.4f} |")
        add(f"| 单轮净利 min / max | ${min(nets):.4f} / ${max(nets):.4f} |")
        add(f"| 累计净利 | ${totals['net']:.4f} |")
        add(f"| 累计毛利（Σp−1）×X | ${totals['gross_edge']:.4f} |")
        add(f"| 摩擦合计 | ${totals['friction']:.4f}（滑点+手续费+gas+convert） |")
        add(f"| 每轮平均投入 | ${totals['outlay']/len(rounds):.2f} |")
        add(f"| 投入资金 ROI | {totals['roi_pct']:.2f}%（按总投入） |")
        add(f"| 每 X 净利（net/X） | {totals['net']/(len(rounds)*args.x):.4f} |")
        add("")
        add("摩擦分解：")
        add("")
        add(f"- 滑点（标记价→NO 成交价 {args.slip_bps} bps）占比：{pct(totals['slip_cost'], totals['friction'])}")
        add(f"- taker 手续费占比：{pct(totals['taker_fees'], totals['friction'])}")
        add(f"- gas 占比：{pct(totals['gas'], totals['friction'])}")
        add(f"- Convert 费用占比：{pct(totals['convert_fee'], totals['friction'])}")
        add("")
        add("### 轮次明细（前 40 轮）")
        add("")
        add("| 入场时间 | Σp | 投入 | 毛利 | 净利 | net/X | ROI |")
        add("| --- | --- | --- | --- | --- | --- | --- |")
        for r in rounds[:40]:
            add(f"| {utc(r['ts'])} | {r['sump']:.4f} | ${r['total_outlay']:.2f} | ${r['gross_edge']:.2f} | ${r['net']:.2f} | ${r['net_per_x']:.4f} | {r['roi_pct']:.2f}% |")
        if len(rounds) > 40:
            add(f"| … 其余 {len(rounds)-40} 轮见 JSONL | | | | | | |")
        add("")
        add("## 结论")
        add("")
        if totals["net"] > 0:
            add("**回测口径净期望为正**（taker 全收费、无返佣、含滑点与 gas）。")
        else:
            add("**回测口径净期望不为正**：毛利被摩擦吃掉。需区分摩擦来源并验证 maker/返佣口径，或等待订单簿历史数据校准可成交成本。")
        add("")
        add("当前口径为最保守假设（taker 全收费、返佣 0）。敏感性：")
        add("")
        add(f"- taker 返佣 {args.taker_rebate:.0%}：净利 ${totals['net']:.4f}")
        add(f"- taker 返佣 100%（费用全返）：净利约 ${totals['net'] + totals['taker_fees']:.4f}")
        add(f"- maker 无 taker 费（价格仍含滑点）：净利约 ${totals['net'] + totals['taker_fees']:.4f}")
        add("")
        add("### 敏感性（滑点 × 返佣，累计净利）")
        add("")
        add("| 滑点 bps | 返佣 0% | 返佣 100% |")
        add("| --- | --- | --- |")
        for row in sensitivity:
            add(f"| {row['slip_bps']} | ${row['net_rebate0']:.4f} | ${row['net_rebate1']:.4f} |")
        add("")
    if reality:
        add("## 现实校验（e46m3 链上活动）")
        add("")
        if "sump_at_actual" in reality:
            a = reality["sump_at_actual"]
            add(f"- 实际 Convert 时点 Σp：{a['count']} 次，min {a['min']} / max {a['max']} / mean {a['mean']}")
        if "conversions_actual" in reality:
            a = reality["conversions_actual"]
            add(f"- 实际 CONVERSION 笔数：{a['count']}（回测窗口内 {a['count_in_backtest_window']} 笔）")
        if "actual_buy_rounds" in reality:
            add("- 实际 NO 买入轮次（按 60s 聚簇）：")
            add("")
            add("| 时间 | 笔数 | 名义金额 | 份额 | 均价 | 同点 Σp |")
            add("| --- | --- | --- | --- | --- | --- |")
            for r in reality["actual_buy_rounds"]:
                add(f"| {r['ts']} | {r['n_fills']} | ${r['notional_usd']} | {r['shares']:g} | {r['avg_fill_price']} | {r['sigmaP_at_grid']} |")
            add("")
        add("说明：实际成交含子集 Convert 与持仓/赎回，与回测'全套 NO 立即兑现'模型不完全同构，仅作校准参考。")
        add("")
    add("## 局限")
    add("")
    add("1. 无订单簿历史：NO 成交价用标记价 + 滑点近似，实际可成交成本以扫描器二级精筛（订单簿 ask）为准；")
    add("2. 每轮按窗口首个采样点入场，未模拟 30 秒级循环与单轮容量上限；")
    add("3. 未计做市/返佣（S-F2）与平台规则变化；")
    avg_outlay = totals["outlay"] / len(rounds) if rounds else 0.0
    add(f"4. 单轮 X=${args.x:g} 时，每轮投入约 ${avg_outlay:.0f}；")
    add("   $50 预算下建议 X ≈ $50 / (n−Σp) ≈ $" + (f"{50.0 / max((n - sp_stats['max']), 0.01):.1f}" if rounds else "n/a") + "（容量需用订单簿验证）。")
    add("")
    add(f"报告生成：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="case bundle JSON or per-leg price-history dict JSON")
    ap.add_argument("--x", type=float, default=DEFAULT_X, help="shares per leg per round")
    ap.add_argument("--entry", type=float, default=DEFAULT_ENTRY_THRESHOLD, dest="entry_threshold")
    ap.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE)
    ap.add_argument("--gas-usd", type=float, default=DEFAULT_GAS_USD)
    ap.add_argument("--slip-bps", type=int, default=DEFAULT_SLIP_BPS)
    ap.add_argument("--convert-fee-bps", type=int, default=DEFAULT_CONVERT_FEE_BPS)
    ap.add_argument("--taker-rebate", type=float, default=DEFAULT_TAKER_REBATE)
    ap.add_argument("--step-s", type=int, default=DEFAULT_STEP_S)
    ap.add_argument("--max-stale-s", type=float, default=DEFAULT_MAX_STALE_S)
    ap.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD)
    ap.add_argument("--activity", default=None, help="optional e46m3 activity JSON for reality check")
    ap.add_argument("--trades", default=None, help="optional e46m3 trades JSON for reality check")
    ap.add_argument("--out-dir", default=None, help="override output directory (default reports/)")
    args = ap.parse_args()

    series_map, meta = load_series_map(args.input)
    if len(series_map) < MIN_LEGS:
        print(f"skip: only {len(series_map)} legs (< {MIN_LEGS})", file=sys.stderr)
        return 2
    rows = build_grid(series_map, args.step_s, args.max_stale_s)
    if not rows:
        raise SystemExit("no valid grid rows: price history empty or all legs stale")

    labels = list(series_map.keys())
    sp_all = [sum(p.values()) for _, p in rows]
    sp_stats = {
        "min": min(sp_all),
        "max": max(sp_all),
        "mean": sum(sp_all) / len(sp_all),
        "median": sorted(sp_all)[len(sp_all) // 2],
        "time_above": sum(1 for s in sp_all if s >= 1 + args.entry_threshold),
        "time_below": sum(1 for s in sp_all if s <= 1 - args.entry_threshold),
    }
    yes_side = {
        "min_sump": min(sp_all),
        "edge_per_x": max(0.0, 1.0 - min(sp_all)),
    }

    episodes = detect_episodes(rows, args.entry_threshold)
    rounds: list[dict] = []
    totals = {
        "net": 0.0, "gross_edge": 0.0, "friction": 0.0, "outlay": 0.0,
        "taker_fees": 0.0, "gas": 0.0, "convert_fee": 0.0, "slip_cost": 0.0,
    }
    for start, end in episodes:
        ts, prices = rows[start]
        r = simulate_round(
            prices,
            args.x,
            args.fee_rate,
            args.gas_usd,
            args.slip_bps,
            args.convert_fee_bps,
            args.taker_rebate,
        )
        r["ts"] = ts
        r["state"] = "SIMULATED"
        r["side"] = "NO"
        rounds.append(r)
        totals["net"] += r["net"]
        totals["gross_edge"] += r["gross_edge"]
        totals["friction"] += r["friction"] if r["friction"] is not None else 0.0
        totals["outlay"] += r["total_outlay"]
        totals["taker_fees"] += r["taker_fees"]
        totals["gas"] += r["gas_usd"]
        totals["convert_fee"] += r["convert_fee"]
        slip = sum((l["no_exec"] - (1 - prices[l["leg"]])) * args.x for l in r["legs"])
        totals["slip_cost"] += slip
    totals["roi_pct"] = 100.0 * totals["net"] / totals["outlay"] if totals["outlay"] else None

    meta_check = dict(meta)
    if args.activity:
        try:
            with open(args.activity, encoding="utf-8") as f:
                meta_check["activity"] = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: cannot read --activity {args.activity}: {e}", file=sys.stderr)
    if args.trades:
        try:
            with open(args.trades, encoding="utf-8") as f:
                meta_check["trades"] = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: cannot read --trades {args.trades}: {e}", file=sys.stderr)
    reality = reality_check(meta_check, rows, args.entry_threshold)

    sensitivity = []
    if rounds:
        for slip in (0, 50, 100):
            row = {"slip_bps": slip}
            for rebate, key in ((0.0, "net_rebate0"), (1.0, "net_rebate1")):
                total = 0.0
                for start, _end in episodes:
                    _ts, prices = rows[start]
                    total += simulate_round(
                        prices, args.x, args.fee_rate, args.gas_usd,
                        slip, args.convert_fee_bps, rebate,
                    )["net"]
                row[key] = round(total, 4)
            sensitivity.append(row)

    base = os.path.splitext(os.path.basename(args.input))[0]
    ts_now = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = args.out_dir or os.path.join(ROOT, "reports")
    os.makedirs(out_dir, exist_ok=True)
    runtime_dir = os.path.join(ROOT, "runtime", "forensics")
    os.makedirs(runtime_dir, exist_ok=True)
    out_md = os.path.join(out_dir, f"forensics_arb_backtest_{base}_{ts_now}.md")
    out_json = os.path.join(out_dir, f"forensics_arb_backtest_{base}_{ts_now}.json")
    out_jsonl = os.path.join(runtime_dir, f"backtest_{base}_{ts_now}.jsonl")

    write_report(
        args, labels, rows, episodes, rounds, totals, sp_stats, yes_side,
        reality, sensitivity, out_md,
    )
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "input": args.input,
                "params": vars(args),
                "legs": len(labels),
                "window": [rows[0][0], rows[-1][0]],
                "sigmaP": sp_stats,
                "yes_side": yes_side,
                "episodes": len(episodes),
                "rounds": len(rounds),
                "totals": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in totals.items()},
                "verdict": "positive" if totals["net"] > 0 else ("no_episodes" if not rounds else "non_positive"),
                "reality_check": reality,
                "sensitivity": sensitivity,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in rounds:
            slim = {k: v for k, v in r.items() if k != "legs"}
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")

    verdict = "positive" if totals["net"] > 0 else ("no_episodes" if not rounds else "non_positive")
    print(f"input     : {args.input}")
    print(f"legs      : {len(labels)}  window: {utc(rows[0][0])} ~ {utc(rows[-1][0])} ({len(rows)} pts)")
    print(f"sigmaP    : min {sp_stats['min']:.4f}  max {sp_stats['max']:.4f}  mean {sp_stats['mean']:.4f}")
    print(f"episodes  : {len(episodes)}  rounds: {len(rounds)}")
    if rounds:
        print(f"net       : ${totals['net']:.4f}  gross ${totals['gross_edge']:.4f}  friction ${totals['friction']:.4f}")
        print(f"roi       : {totals['roi_pct']:.2f}%  verdict: {verdict}")
    else:
        print(f"verdict   : {verdict}  (max Σp {sp_stats['max']:.4f} < threshold {1+args.entry_threshold:.3f})")
    print(f"report    : {out_md}")
    print(f"summary   : {out_json}")
    print(f"rounds    : {out_jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
