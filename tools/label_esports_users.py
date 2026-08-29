#!/usr/bin/env python3
"""Label esports users by on-chain behavior for a BO3 moneyline event.

Purpose
-------
Pilot: tag every user who traded a Polymarket esports BO3 event (Game 1 /
Game 2 / Match Winner) with behavior labels, persist into a long-lived SQLite
label library, and emit per-event JSON + markdown summaries.

Usage
-----
    python3 tools/label_esports_users.py label <event_slug> [--data-dir DIR] [--db PATH]
    python3 tools/label_esports_users.py enrich <event_slug> [--top N] [--db PATH]

`label` builds the per-event registry and tags. `enrich` pulls each user's
/activity history (up to 2000 rows) to compute history-based tags
(A_深水机器 / G_低历史 / first-activity).

Labels are behavioral inference (证据等级 3), not facts. Thresholds are pilot
constants and should be revisited after the one-week run.
"""

import argparse
import collections
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

UA = "Mozilla/5.0"
API = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

TH = 100.0          # per-leg dollar threshold for full-script tags
PRE_BIG = 3000.0    # pre-game big-buy threshold (winner side, single market)
DEEP_INPLAY = 0.20  # in-play "deep" price ceiling
H_DARK_COST = 300.0 # in-play deep cost threshold
DEEP_PRICE = 0.15   # deep-value price ceiling (history tag)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def curl(url, out=None):
    cmd = ["curl", "-sS", "--retry", "5", "--retry-all-errors",
           "--retry-delay", "2", "--max-time", "120", "-A", UA, url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"curl failed: {url} rc={r.returncode}")
    data = r.stdout
    if out:
        with open(out, "w") as f:
            f.write(data)
    return data


def http_json(url):
    return json.loads(curl(url))


def ts_str(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_event(slug, data_dir):
    ev = http_json(f"{GAMMA}/events?slug={slug}")
    if not ev:
        raise RuntimeError(f"event not found: {slug}")
    curl(f"{GAMMA}/events?slug={slug}", os.path.join(data_dir, "event.json"))
    return ev[0]


def pick_markets(event):
    """Return game1/game2/match moneyline markets (child_moneyline/moneyline)."""
    slug = event["slug"]
    base = [slug, f"{slug}-game1", f"{slug}-game2", f"{slug}-game3"]
    out = {}
    for m in event["markets"]:
        if m.get("sportsMarketType") not in ("moneyline", "child_moneyline"):
            continue
        if m["slug"] not in base:
            continue
        key = {"-game1": "g1", "-game2": "g2", "-game3": "g3"}.get(
            m["slug"][len(slug):], "match")
        out[key] = m
    return out


def fetch_trades(cond_id, data_dir, name, game_start_ts):
    """Paginate /trades with 6h windows (offset cap ~10k per window)."""
    out = os.path.join(data_dir, f"{name}_trades.json")
    if os.path.exists(out):
        with open(out) as f:
            return json.load(f)
    rows = []
    w0 = game_start_ts - 3 * 86400
    w1 = game_start_ts + 1 * 86400
    ws = w0
    while ws < w1:
        we = ws + 21600
        off = 0
        while True:
            page = http_json(
                f"{API}/trades?market={cond_id}&takerOnly=false&limit=1000"
                f"&offset={off}&start={ws}&end={we}")
            rows.extend(page)
            if len(page) < 1000:
                break
            off += 1000
            if off > 30000:
                break
        ws = we
    with open(out, "w") as f:
        json.dump(rows, f, ensure_ascii=False)
    return rows


def fetch_prices(token_id, data_dir, name, t0, t1):
    out = os.path.join(data_dir, f"prices_{name}_1m.json")
    if not os.path.exists(out):
        curl(f"{CLOB}/prices-history?market={token_id}&interval=1d&fidelity=1"
             f"&startTs={t0}&endTs={t1}", out)
    with open(out) as f:
        return json.load(f)["history"]


def decision_time(prices, winner_token_price_history, fallback):
    """First time the winner-side price stays >=0.95 forever after (suffix min)."""
    n = len(prices)
    if n == 0:
        return fallback
    suf = [0.0] * n
    suf[-1] = prices[-1]["p"]
    for i in range(n - 2, -1, -1):
        suf[i] = min(prices[i]["p"], suf[i + 1])
    for i, h in enumerate(prices):
        if h["p"] >= 0.95 and suf[i] >= 0.95:
            return h["t"]
    return fallback


def windows(ts, game_start, decision):
    if ts < game_start:
        return "pre"
    if ts < decision:
        return "inplay"
    return "post"


def build_event_labels(event, data_dir):
    slug = event["slug"]
    gs_raw = event["markets"][0].get("gameStartTime") or event.get("startTime")
    game_start = int(datetime.fromisoformat(gs_raw.replace("Z", "+00:00")).timestamp())
    markets = pick_markets(event)
    if not {"g1", "g2", "match"} <= set(markets):
        raise RuntimeError(f"missing moneyline markets for {slug}: {sorted(markets)}")

    # decision times
    decisions = {}
    toks = {}
    for key in ("g1", "g2", "match"):
        m = markets[key]
        outcomes = json.loads(m["outcomes"])
        prices = json.loads(m["outcomePrices"])
        winner = outcomes[prices.index("1")]
        toks[key] = {"cond": m["conditionId"], "tokens": json.loads(m["clobTokenIds"]),
                     "winner": winner, "outcomes": outcomes}
        t0 = int(datetime.fromisoformat(event["startDate"].replace("Z", "+00:00")).timestamp())
        t1 = int(datetime.fromisoformat(event["endDate"].replace("Z", "+00:00")).timestamp())
        wtok = toks[key]["tokens"][prices.index("1")]
        ph = fetch_prices(wtok, data_dir, f"{key}_winner", t0, t1)
        fallback = int(datetime.strptime(m["closedTime"].split("+")[0].strip(),
                                         "%Y-%m-%d %H:%M:%S").timestamp())
        decisions[key] = decision_time(ph, None, fallback)

    # trades
    all_trades = {}
    for key in ("g1", "g2", "match"):
        all_trades[key] = fetch_trades(toks[key]["cond"], data_dir, key, game_start)

    # per-address aggregation
    stats = collections.defaultdict(lambda: collections.defaultdict(
        lambda: {"buy_sh": 0.0, "buy_cost": 0.0, "sell_sh": 0.0, "sell_val": 0.0,
                 "n_buy": 0, "n_sell": 0, "pre": 0.0, "inplay": 0.0, "post": 0.0,
                 "win_cost": 0.0, "win_sh": 0.0, "deep_inplay": 0.0,
                 "maxp": 0.0, "minp": 9.0, "wins": 0}))
    names = {}
    for key, rows in all_trades.items():
        for t in rows:
            a = t["proxyWallet"]
            names[a] = t.get("name") or names.get(a, "")
            asset = t["asset"]
            is_winner = (asset == toks[key]["tokens"][toks[key]["outcomes"].index(toks[key]["winner"])])
            w = windows(t["timestamp"], game_start, decisions[key])
            s = stats[a][key]
            if t["side"] == "BUY":
                s["buy_sh"] += t["size"]; s["buy_cost"] += t["size"] * t["price"]
                s["n_buy"] += 1
                if is_winner:
                    s["wins"] += 1
                    s[w] += t["size"] * t["price"]
                    s["win_cost"] += t["size"] * t["price"]
                    s["win_sh"] += t["size"]
                    if w == "inplay" and t["price"] <= DEEP_INPLAY:
                        s["deep_inplay"] += t["size"] * t["price"]
                    s["maxp"] = max(s["maxp"], t["price"]); s["minp"] = min(s["minp"], t["price"])
            else:
                s["sell_sh"] += t["size"]; s["sell_val"] += t["size"] * t["price"]
                s["n_sell"] += 1

    # tags
    accounts = []
    for a, by in stats.items():
        tags = set()
        def loser_cost(key):
            out = toks[key]["outcomes"]
            winner = toks[key]["winner"]
            loser_tok = toks[key]["tokens"][1 - out.index(winner)]
            return sum(t["size"] * t["price"] for t in all_trades[key]
                       if t["proxyWallet"] == a and t["side"] == "BUY" and t["asset"] == loser_tok)
        def sides(key):
            return set(t["asset"] for t in all_trades[key]
                       if t["proxyWallet"] == a and t["side"] == "BUY")
        # full script: winner-side buy pre-decision on all three
        if (by["g1"]["pre"] + by["g1"]["inplay"] >= TH and
                by["g2"]["pre"] + by["g2"]["inplay"] >= TH and
                by["match"]["pre"] + by["match"]["inplay"] >= TH):
            tags.add("B_全剧本")
            if by["g1"]["pre"] >= TH and by["g2"]["pre"] >= TH and by["match"]["pre"] >= TH:
                tags.add("B1_赛前三腿")
        tot = sum(by[k]["buy_cost"] for k in ("g1", "g2", "match"))
        both_mkts = sum(1 for k in ("g1", "g2", "match") if len(sides(k)) == 2)
        if both_mkts >= 2 and sum(1 for k in ("g1", "g2", "match") if by[k]["n_buy"] > 0) == 3 and tot < 150:
            tags.add("C_尘埃簇")
        # post-decision flow
        if by["g2"]["post"] >= 500 and by["g2"]["maxp"] >= 0.98:
            tags.add("D_盘后流")
        # panic seller: pre-game big buy + in-play deep sell
        g2s = by["g2"]
        if g2s["pre"] + g2s["inplay"] >= 500 and g2s["sell_sh"] > 0:
            avg_buy = (g2s["win_cost"] / g2s["win_sh"]) if g2s["win_sh"] else 9.0
            deep_sell = sum(t["size"] for t in all_trades["g2"]
                            if t["proxyWallet"] == a and t["side"] == "SELL"
                            and t["timestamp"] >= game_start and t["timestamp"] < decisions["g2"]
                            and t["price"] <= 0.2)
            if deep_sell >= 500 and avg_buy >= 0.30:
                tags.add("E_恐慌割肉")
        # both sides actively (winner side and loser side both >= TH)
        if by["g2"]["win_cost"] >= TH and loser_cost("g2") >= TH:
            tags.add("F_活跃双向")
        # in-play deep large
        if g2s["deep_inplay"] >= H_DARK_COST:
            tags.add("H_局中深水")
        # pre-game big
        if max(by[k]["pre"] for k in ("g1", "g2", "match")) >= PRE_BIG:
            tags.add("I_赛前大额")
        total_cost = sum(by[k]["buy_cost"] for k in ("g1", "g2", "match"))
        total_sh = sum(by[k]["buy_sh"] for k in ("g1", "g2", "match"))
        total_sell_sh = sum(by[k]["sell_sh"] for k in ("g1", "g2", "match"))
        total_sell_val = sum(by[k]["sell_val"] for k in ("g1", "g2", "match"))
        net = total_sh - total_sell_sh
        est = total_sell_val + max(net, 0) - total_cost
        accounts.append({
            "address": a, "name": names.get(a, ""), "tags": sorted(tags),
            "total_cost": round(total_cost, 2), "total_shares": round(total_sh, 2),
            "net_shares": round(net, 2), "est_pnl": round(est, 2),
            "g1": by["g1"], "g2": by["g2"], "match": by["match"]})

    accounts.sort(key=lambda r: -r["est_pnl"])
    tag_counts = collections.Counter(t for r in accounts for t in r["tags"])
    report = {
        "event_slug": slug, "title": event["title"], "game_start": ts_str(game_start),
        "decisions": {k: ts_str(v) for k, v in decisions.items()},
        "tag_counts": dict(tag_counts), "n_accounts": len(accounts),
        "accounts": accounts, "processed_at": now_iso()}
    with open(os.path.join(data_dir, "labels_report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    return report


def write_summary(report, data_dir):
    lines = [f"# 打标报告：{report['title']}", "",
             f"- slug: `{report['event_slug']}`　处理时间：{report['processed_at']}",
             f"- 开赛：{report['game_start']}　定局：G1 {report['decisions']['g1']} / "
             f"G2 {report['decisions']['g2']} / 整场 {report['decisions']['match']}",
             f"- 涉及账户：{report['n_accounts']}", "",
             "## 标签统计", "", "| 标签 | 数量 |", "| --- | --- |"]
    for t, c in sorted(report["tag_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {c} |")
    lines += ["", "## 估计盈亏 Top 20", "",
              "| 地址 | 用户名 | 总成本 | 净持仓 | 估盈亏 | 标签 |", "| --- | --- | --- | --- | --- | --- |"]
    for r in report["accounts"][:20]:
        lines.append(f"| {r['address']} | {r['name'][:18] or '—'} | ${r['total_cost']:,.0f} | "
                     f"{r['net_shares']:,.0f} | ${r['est_pnl']:,.0f} | {'; '.join(r['tags'])} |")
    lines.append("")
    with open(os.path.join(data_dir, "labels_summary.md"), "w") as f:
        f.write("\n".join(lines))


def upsert(db_path, report):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS events(
      slug TEXT PRIMARY KEY, title TEXT, game_start TEXT, decisions TEXT, processed_at TEXT);
    CREATE TABLE IF NOT EXISTS users(
      address TEXT PRIMARY KEY, name TEXT, first_seen TEXT, last_seen TEXT,
      n_events INTEGER DEFAULT 0, tags TEXT, enriched INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS event_labels(
      event_slug TEXT, address TEXT, tags TEXT, stats TEXT,
      PRIMARY KEY(event_slug, address));
    """)
    now = report["processed_at"]
    con.execute("INSERT OR REPLACE INTO events VALUES (?,?,?,?,?)",
                (report["event_slug"], report["title"], report["game_start"],
                 json.dumps(report["decisions"]), now))
    for r in report["accounts"]:
        con.execute("INSERT OR REPLACE INTO event_labels VALUES (?,?,?,?)",
                    (report["event_slug"], r["address"], json.dumps(r["tags"]),
                     json.dumps({k: r[k] for k in ("total_cost", "total_shares", "net_shares", "est_pnl")})))
        row = con.execute("SELECT first_seen,last_seen,enriched FROM users WHERE address=?",
                          (r["address"],)).fetchone()
        if row:
            con.execute("UPDATE users SET name=?, first_seen=?, last_seen=? WHERE address=?",
                        (r["name"], min(row[0], report["game_start"]),
                         max(row[1], report["processed_at"]), r["address"]))
        else:
            con.execute("INSERT INTO users VALUES (?,?,?,?,?,?,0)",
                        (r["address"], r["name"], report["game_start"], now, 0, "{}"))
    # rebuild n_events and tag counts from event_labels (idempotent)
    for (addr,) in con.execute("SELECT DISTINCT address FROM event_labels"):
        n_ev = con.execute("SELECT COUNT(*) FROM event_labels WHERE address=?", (addr,)).fetchone()[0]
        tagc = collections.Counter()
        for (t,) in con.execute("SELECT tags FROM event_labels WHERE address=?", (addr,)):
            tagc.update(json.loads(t))
        con.execute("UPDATE users SET n_events=?, tags=? WHERE address=?",
                    (n_ev, json.dumps(dict(tagc)), addr))
    con.commit()
    con.close()


def enrich(db_path, slug, top):
    data_dir = os.path.join(os.path.dirname(db_path), "..", "events", slug)
    report_path = os.path.join(data_dir, "labels_report.json")
    if not os.path.exists(report_path):
        raise RuntimeError(f"run label first: {report_path}")
    report = json.load(open(report_path))
    act_dir = os.path.join(data_dir, "activity")
    os.makedirs(act_dir, exist_ok=True)
    con = sqlite3.connect(db_path)
    for r in report["accounts"][:top]:
        a = r["address"]
        out = os.path.join(act_dir, f"{a}.json")
        if not os.path.exists(out):
            rows = []
            for off in (0, 500, 1000, 1500):
                page = http_json(f"{API}/activity?user={a}&start=1&limit=500&offset={off}")
                rows.extend(page)
                if len(page) < 500:
                    break
            with open(out, "w") as f:
                json.dump(rows, f, ensure_ascii=False)
        acts = json.load(open(out))
        trades = [x for x in acts if x["type"] == "TRADE" and x.get("price") is not None]
        deep = [x for x in trades if x["side"] == "BUY" and x["price"] <= DEEP_PRICE]
        deep_usd = sum((x.get("usdcSize") or x["size"] * x["price"]) for x in deep)
        first = min((x["timestamp"] for x in acts), default=None)
        row = con.execute("SELECT tags, first_seen FROM users WHERE address=?", (a,)).fetchone()
        tags = dict(json.loads(row[0])) if row else {}
        if len(deep) >= 100 or deep_usd >= 10000:
            tags["A_深水机器"] = tags.get("A_深水机器", 0) + 1
        if len(acts) < 1000:
            tags["G_低历史"] = tags.get("G_低历史", 0) + 1
        first_seen = row[1] if row else None
        if first and (not first_seen or ts_str(first) < first_seen):
            first_seen = ts_str(first)
        con.execute("UPDATE users SET tags=?, enriched=1, first_seen=? WHERE address=?",
                    (json.dumps(tags), first_seen, a))
        print(f"enriched {a} rows={len(acts)} deepN={len(deep)} deepUSD={deep_usd:.0f}")
    con.commit()
    con.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("label")
    p1.add_argument("slug")
    p1.add_argument("--data-dir", default=None)
    p1.add_argument("--db", default="docs/forensics/data/accounts/esports_user_labels.db")
    p2 = sub.add_parser("enrich")
    p2.add_argument("slug")
    p2.add_argument("--top", type=int, default=30)
    p2.add_argument("--db", default="docs/forensics/data/accounts/esports_user_labels.db")
    args = ap.parse_args()

    if args.cmd == "label":
        data_dir = args.data_dir or os.path.join("docs/forensics/data", args.slug)
        os.makedirs(data_dir, exist_ok=True)
        event = fetch_event(args.slug, data_dir)
        report = build_event_labels(event, data_dir)
        write_summary(report, data_dir)
        upsert(args.db, report)
        print(f"{args.slug}: {report['n_accounts']} accounts, "
              f"tags={report['tag_counts']}")
    else:
        enrich(args.db, args.slug, args.top)


if __name__ == "__main__":
    main()
