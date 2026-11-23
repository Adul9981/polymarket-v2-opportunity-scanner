#!/usr/bin/env python3
"""拉取 Riot 官方 LoL 赛程，补 LCK CL / 非 Polymarket 场次进今日清单。

背景（2026-09-10 固化）：今日比赛清单与 vps 管线只读 Polymarket
market_scanner 输出（runtime/watchlist_events.json），LCK CL / LPL 等
"Polymarket 暂无市场"的官方场次会被系统性漏掉（教训：09-09 NS vs DNS 与
多场 LCK CL 从未自动进 matches_today，需要用户口播才补）。

本工具从 Riot getSchedule 拉 LCK CL / LCK / LPL / LEC / LCP 的
今日+明日官方场次，输出统一 JSON（与 watchlist_events 同构），供：
  - export_today_matches.py --official <本文件>  合并进 matches_today
  - update_site_today.py 展示官方场次行（不带 Polymarket 市场链接）

用法：
  python3 tools/fetch_official_lol_schedule.py [--date 2026-09-10]
      [--out runtime/official_lol_today.json]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
API_BASE = "https://esports-api.lolesports.com/persisted/gw"

# 与 fetch_official_game_data.py 保持一致；只纳入情报库覆盖的联赛。
LEAGUE_IDS = {
    "LCK CL": "98767991335774713",
    "LCK": "98767991310872058",
    "LPL": "98767991314006698",
    "LEC": "98767991302996019",
    "LCP": "113476371197627891",
}


def http_get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "x-api-key": API_KEY,
            "accept": "application/json",
            "user-agent": "polymarket-intel/fetch_official_lol_schedule",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def bj_date(start_iso: str | None) -> str:
    if not start_iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        return dt.astimezone(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
    except ValueError:
        return ""


def norm_code(raw: str) -> str:
    """队伍代码：去空格/小写、替换点；保留字母数字（DNS.C -> dnsc）。"""
    return re.sub(r"[^a-zA-Z0-9]", "", raw or "").lower()


def build_slug(codes: list[str], date: str) -> str:
    if len(codes) != 2:
        return ""
    return f"lol-{norm_code(codes[0])}-{norm_code(codes[1])}-{date}"


def fetch_league(name: str, league_id: str, target_dates: set[str]) -> list[dict]:
    url = f"{API_BASE}/getSchedule?hl=zh-CN&leagueId={league_id}"
    try:
        data = http_get(url)
    except Exception as e:  # noqa: BLE001
        print(f"[official-lol] {name} fetch failed: {e}")
        return []
    out: list[dict] = []
    for ev in data.get("data", {}).get("schedule", {}).get("events", []):
        m = ev.get("match") or {}
        teams = []
        codes: list[str] = []
        for t in m.get("teams", []):
            teams.append(t.get("name") or t.get("code") or "")
            codes.append(t.get("code") or t.get("name") or "")
        if len(teams) != 2 or not all(teams):
            continue
        start = ev.get("startTime") or ""
        d = bj_date(start)
        if d not in target_dates:
            continue
        state = str(ev.get("state") or "").lower()
        if state in ("unstarted", "inprogress", "completed"):
            status = {"unstarted": "未开始", "inprogress": "进行中", "completed": "已结束"}[state]
        else:
            status = "未开始"
        slug = build_slug(codes, d)
        out.append(
            {
                "title": f"LoL: {teams[0]} vs {teams[1]} - {name}",
                "slug": slug,
                "official_match_id": str(m.get("id") or ev.get("id") or ""),
                "teams": teams,
                "codes": codes,
                "league": name,
                "start_time": start,
                "end_time": "",
                "time_status": status,
                "watchlist_group": "LoL",
                "watchlist_key": "lol_official",
                "active": state == "inprogress",
                "closed": state == "completed",
                "market_count": 0,
                "winner_market_count": 0,
                "series_market_count": 0,
                "_official_source": "riot",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default="runtime/official_lol_today.json")
    args = ap.parse_args()
    d0 = datetime.date.fromisoformat(args.date)
    target = {args.date, (d0 + datetime.timedelta(days=1)).isoformat()}

    rows: list[dict] = []
    for name, lid in LEAGUE_IDS.items():
        rows.extend(fetch_league(name, lid, target))
    # 按 slug 去重（同一队伍组合同天可能出现多阶段，保留最早未结束项即可）
    seen: dict[str, dict] = {}
    for r in rows:
        cur = seen.get(r["slug"])
        if cur is None:
            seen[r["slug"]] = r
            continue
        if cur.get("closed") and not r.get("closed"):
            seen[r["slug"]] = r
    out_rows = list(seen.values())
    out_rows.sort(key=lambda r: r.get("start_time") or "")

    p = ROOT / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "date": args.date,
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "count": len(out_rows),
                "matches": out_rows,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"[official-lol] wrote {args.out}: {len(out_rows)} official LoL matches")
    for r in out_rows:
        print(" ", r["slug"], "|", r["league"], "|", r["time_status"], "|", r["start_time"], "|", " vs ".join(r["teams"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
