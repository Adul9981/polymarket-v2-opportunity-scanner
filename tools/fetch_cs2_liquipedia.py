#!/usr/bin/env python3
"""Fetch CS2 match facts (time, teams, maps, scores) from Liquipedia CS wiki.

Liquipedia Counter-Strike is a free, structured, community-maintained fact
source (closest CS2 analog to Riot's official LoL API). Match data lives in
event page wikitext as {{Match ...}} templates.

Usage:
  python3 tools/fetch_cs2_liquipedia.py --event "BLAST/Open/2026/Fall"
  python3 tools/fetch_cs2_liquipedia.py --event "BLAST/Open/2026/Fall" --date 2026-08-27
  python3 tools/fetch_cs2_liquipedia.py --search "BLAST Open"

Notes:
  - API requires gzip encoding + a User-Agent (else HTTP 406).
  - Parse the {{Match}} template: teams, exact start time (date + time + TZ),
    per-map T/CT scores, finished/skip status, HLTV match id, VOD links.
  - HLTV id can be used to deep-link roster / map veto on hltv.org (Cloudflare
    protected; use unofficial wrappers or manual check there).
"""

import argparse
import gzip
import io
import json
import re
import sys
import urllib.request
import urllib.parse
import datetime

API = "https://liquipedia.net/counterstrike/api.php"
UA = "PolymarketIntelBot/1.0 (research; contact local)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data


def api_get(params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    return json.loads(fetch(f"{API}?{q}").decode("utf-8"))


def page_wikitext(title: str) -> str:
    d = api_get({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "titles": title, "format": "json", "formatversion": "2",
    })
    pages = d.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        raise ValueError(f"page not found: {title}")
    return pages[0].get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")


def search_pages(query: str, limit: int = 8) -> list[str]:
    d = api_get({
        "action": "query", "list": "search", "srsearch": query,
        "format": "json", "formatversion": "2",
    })
    return [r["title"] for r in d.get("query", {}).get("search", [])[:limit]]


def extract_template(body: str, name: str, start: int = 0):
    """Extract {{Name ...}} template bodies, handling nested braces."""
    out = []
    i = body.find("{{" + name, start)
    while i != -1:
        j = body.find("{", i + 2)
        depth = 1
        k = i + 2
        while k < len(body) and depth:
            if body[k:k+2] == "{{":
                depth += 1
                k += 2
            elif body[k:k+2] == "}}":
                depth -= 1
                k += 2
            else:
                k += 1
        out.append(body[i+2:k-2])
        i = body.find("{{" + name, k)
    return out


def field(text: str, key: str) -> str:
    m = re.search(rf"\|\s*{key}\s*=", text)
    if not m:
        return ""
    i = m.end()
    depth = 0
    out = []
    while i < len(text):
        if text.startswith("{{", i):
            depth += 1
            out.append("{{")
            i += 2
            continue
        if text.startswith("}}", i):
            depth -= 1
            out.append("}}")
            i += 2
            continue
        if text[i] == "|" and depth == 0:
            break
        if text[i] == "\n" and depth == 0:
            break
        out.append(text[i])
        i += 1
    return "".join(out).strip()


def parse_match(block: str) -> dict:
    def team_of(v: str) -> str:
        m = re.search(r"TeamOpponent\|([^}|]*)", v)
        return m.group(1).strip() if m else v.strip()

    match = {
        "team1": team_of(field(block, "opponent1")),
        "team2": team_of(field(block, "opponent2")),
        "date_raw": field(block, "date"),
        "finished": field(block, "finished"),
        "hltv": field(block, "hltv"),
        "maps": [],
    }
    for mblock in extract_template(block, "Map"):
        if field(mblock, "finished") == "skip":
            continue
        match["maps"].append({
            "map": field(mblock, "map"),
            "t1t": field(mblock, "t1t"),
            "t1ct": field(mblock, "t1ct"),
            "t2t": field(mblock, "t2t"),
            "t2ct": field(mblock, "t2ct"),
        })
    return match


def parse_matches(wikitext: str) -> list[dict]:
    matches = []
    for block in extract_template(wikitext, "Match"):
        matches.append(parse_match(block))
    return matches


def norm_date(date_raw: str) -> str | None:
    m = re.search(r"(\w+ \d{1,2}, \d{4})", date_raw)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def map_score(x: dict) -> tuple[int, int] | None:
    try:
        t1 = int(x["t1t"]) + int(x["t1ct"])
        t2 = int(x["t2t"]) + int(x["t2ct"])
    except ValueError:
        return None
    if t1 == 0 and t2 == 0:
        return None
    return t1, t2


def to_cst(date_raw: str) -> str:
    m = re.search(r"(\w+ \d{1,2}, \d{4}) - (\d{2}:\d{2})", date_raw)
    if not m:
        return ""
    try:
        dt = datetime.datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %d, %Y %H:%M")
    except ValueError:
        return ""
    # Liquipedia CS shows CEST (UTC+2) for European events; CST = UTC+8.
    return (dt + datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M CST")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch CS2 match facts from Liquipedia")
    ap.add_argument("--event", help="Liquipedia event page title, e.g. BLAST/Open/2026/Fall")
    ap.add_argument("--search", help="search Liquipedia for event title")
    ap.add_argument("--date", help="filter matches by date, e.g. 2026-08-27")
    ap.add_argument("--teams", help="comma-separated team names to filter")
    args = ap.parse_args()

    if args.event:
        title = args.event
    elif args.search:
        hits = search_pages(args.search)
        if not hits:
            print("no event pages found")
            return 1
        print("candidate pages:", ", ".join(hits))
        title = hits[0]
    else:
        ap.error("provide --event or --search")

    try:
        wt = page_wikitext(title)
    except ValueError as e:
        print(f"error: {e}")
        return 1

    matches = parse_matches(wt)
    if args.teams:
        want = {t.strip().lower() for t in args.teams.split(",")}
        matches = [m for m in matches if m["team1"].lower() in want or m["team2"].lower() in want]
    if args.date:
        matches = [m for m in matches if norm_date(m["date_raw"]) == args.date]

    if not matches:
        print(f"no matches found for event={title} date={args.date} teams={args.teams}")
        return 0

    for m in matches:
        played = [s for s in (map_score(x) for x in m["maps"]) if s]
        decisive = [s for s in played if s[0] != s[1]]
        score1 = sum(1 for s in decisive if s[0] > s[1])
        score2 = len(decisive) - score1
        maps = " | ".join(
            f"{x['map']} {s[0]}:{s[1]}" if (s := map_score(x)) else x["map"]
            for x in m["maps"]
        )
        cst = to_cst(m["date_raw"])
        print(f"{m['date_raw']:<34} {cst:<22} {m['team1']} {score1} - {score2} {m['team2']}  finished={m['finished'] or '-'}  [{maps}]  hltv={m['hltv'] or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
