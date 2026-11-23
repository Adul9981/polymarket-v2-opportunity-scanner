#!/usr/bin/env python3
"""赛前页历史数据拉取：两队交手（H2H）+ 各自近期战绩（规则层，只读）。

赛前节点页（S0）从 Codex 4 段改为「1 队伍交手情况 + 2 队伍比赛近况」两栏后，
这两栏是历史事实，由本工具从权威源拉取，供渲染层系统注入（AI 不写、不编）。

数据源（2026-11-22 定稿）：
  LoL : Riot getLeagues（发现当前 split leagueId）+ getSchedule
        （每场 teams[].result.outcome = win/loss + gameWins）。
        H2H = 同一联赛内两队同场；近况 = 各队该联赛近期场次（按 startTime 倒序）。
  CS2 : Liquipedia 队伍页「Recent Matches」（锦标赛级：名次 + 决赛比分）。
        H2H 无逐场直接源，复用本地 map_records.json + official_matches.json。

输出统一 JSON：
  {
    "game": "lol|cs2",
    "teams": ["A", "B"],
    "league": "...",
    "h2h": [{"date","team_a","team_b","winner","score"}],
    "recent": {"A": [{"date","opponent","result"}], "B": [...]},
    "source": "riot|liquipedia+local",
    "gaps": ["..."]
  }

用法：
  python3 tools/fetch_team_history.py --game lol --teams "T1,GEN" --league LCK
  python3 tools/fetch_team_history.py --game cs2 --teams "Spirit,MOUZ"
"""

from __future__ import annotations

import argparse
import gzip
import html as _html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"
API_KEY = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
API_BASE = "https://esports-api.lolesports.com/persisted/gw"
LIQUI_API = "https://liquipedia.net/counterstrike/api.php"
UA = "PolymarketIntelBot/1.0 (research; contact local)"


# --------------------------------------------------------------------------- helpers

def norm(s: str) -> str:
    """去非字母数字 + 小写，用于队伍名/联赛名宽松比对（DNS.C -> dnsc）。"""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_TEAM_ABBR_CACHE: dict[str, str] | None = None


def _team_abbr_map() -> dict[str, str]:
    """{norm(任意写法): abbr}，惰性加载 team_names.json（abbr/full/aliases 全映射）。"""
    global _TEAM_ABBR_CACHE
    if _TEAM_ABBR_CACHE is not None:
        return _TEAM_ABBR_CACHE
    m: dict[str, str] = {}
    try:
        d = json.loads((INTEL / "team_names.json").read_text(encoding="utf-8"))
        for t in d.get("teams", []):
            abbr = t.get("abbr")
            if not abbr:
                continue
            for cand in [t.get("abbr"), t.get("full")] + list(t.get("aliases", [])):
                if cand:
                    m.setdefault(norm(cand), abbr)
    except Exception:  # noqa: BLE001
        pass
    _TEAM_ABBR_CACHE = m
    return m


def canon_abbr(name: str) -> str:
    """任意写法（abbr/full/alias）-> 情报库规范 abbr（Riot team code 同源）。

    pipeline 传 matches.json 的 teams 全名（如 "Bilibili Gaming"），Riot code 是
    abbr（"BLG"），不归一化会匹配失败（2026-11-22 教训）。未登记队名原样返回。
    """
    return _team_abbr_map().get(norm(name), name)


def _at_or_after(ev_start: str, before: str) -> bool:
    """ev_start 是否不早于 before（即「本场自身或之后」，应从赛前历史排除）。

    before 为完整 ISO 时间戳（含时间）时精确比较；仅为日期时按天比较。
    赛前页只统计早于本场开赛的历史，避免把「本场自身」计入 H2H/近况
    （2026-11-22 教训：赛后视角拉 getSchedule 会把已结束的本场算进交手）。
    """
    if not before:
        return False
    if len(before) > 10:  # 含时间戳
        return (ev_start or "") >= before
    return (ev_start or "")[:10] >= before[:10]  # 仅日期


def riot_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"x-api-key": API_KEY, "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def liqui_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return json.loads(data.decode("utf-8"))


# --------------------------------------------------------------------------- LoL（Riot）

# 联赛名 -> getLeagues 的 name 归一键。用户/情报库口径 -> Riot name。
LEAGUE_ALIAS = {
    "lckcl": "lckchallengers",
    "lck_cl": "lckchallengers",
    "lpl": "lpl",
    "lec": "lec",
    "lcp": "lcp",
    "lck": "lck",
}


def lol_league_ids() -> dict[str, str]:
    """getLeagues -> {norm(name): id}（当前活跃赛季，随赛季切换自动更新）。"""
    out: dict[str, str] = {}
    try:
        d = riot_get(f"{API_BASE}/getLeagues?hl=en-US")
        for l in d.get("data", {}).get("leagues", []):
            name = l.get("name") or ""
            out[norm(name)] = str(l.get("id"))
    except Exception:  # noqa: BLE001
        pass
    return out


def lol_league_id(league: str, ids: dict[str, str]) -> str | None:
    # 只做精确匹配（+ alias）。粗粒度（如 "LoL"）不精确匹配，交给 fetch_lol 反查兜底，
    # 避免前缀匹配把 "LoL" 误配到 "LoL Italian Tournament" 等（2026-11-22 教训）。
    key = LEAGUE_ALIAS.get(norm(league), norm(league))
    return ids.get(key)


# 反查优先顺序（league 参数无法精确匹配时，按此顺序遍历 getSchedule 找两队）。
PRIORITY_LEAGUE_KEYS = [
    "lck", "lckchallengers", "lpl", "lec", "lcp", "lcs",
    "worlds", "msi", "firststand", "kespacup", "esportsworldcup",
    "ltanorth", "ltasouth", "ltacrossconference", "pcs", "vcs",
    "emeamasters", "nacl", "cblol", "ljl", "tcl", "lla",
]


def _fetch_lol_lid(teams: list[str], league: str, lid: str, before: str | None = None) -> dict:
    """按 leagueId 拉 getSchedule 并过滤出 H2H + 近况（排除本场自身及之后）。"""
    ta, tb = norm(teams[0]), norm(teams[1])
    h2h: list[dict] = []
    recent: dict[str, list[dict]] = {teams[0]: [], teams[1]: []}
    try:
        d = riot_get(f"{API_BASE}/getSchedule?hl=en-US&leagueId={lid}")
        events = d.get("data", {}).get("schedule", {}).get("events", [])
    except Exception as e:  # noqa: BLE001
        return {"h2h": h2h, "recent": recent, "gaps": [f"getSchedule 失败：{e}"]}

    for ev in events:
        if _at_or_after(ev.get("startTime") or "", before or ""):
            continue  # 本场自身 / 未来场次，不算赛前历史
        m = ev.get("match") or {}
        mt = m.get("teams", [])
        if len(mt) != 2:
            continue
        codes = [t.get("code") or t.get("name") or "" for t in mt]
        outs = [str(t.get("result", {}).get("outcome") or "") for t in mt]
        wins = [int(t.get("result", {}).get("gameWins") or 0) for t in mt]
        date = (ev.get("startTime") or "")[:10]
        nc = [norm(c) for c in codes]
        if ta in nc and tb in nc:
            ia, ib = nc.index(ta), nc.index(tb)
            winner = codes[ia] if outs[ia] == "win" else (codes[ib] if outs[ib] == "win" else "")
            h2h.append({
                "date": date, "team_a": codes[ia], "team_b": codes[ib],
                "winner": winner, "score": f"{wins[ia]}:{wins[ib]}",
            })
        for team, tn in [(teams[0], ta), (teams[1], tb)]:
            if tn in nc:
                i = nc.index(tn)
                j = 1 - i
                result = "win" if outs[i] == "win" else ("loss" if outs[i] == "loss" else "?")
                recent[team].append({"date": date, "opponent": codes[j], "result": result})

    h2h.sort(key=lambda x: x["date"], reverse=True)
    for t in recent:
        recent[t].sort(key=lambda x: x["date"], reverse=True)
    return {"h2h": h2h, "recent": recent}


def fetch_lol(teams: list[str], league: str, before: str | None = None) -> dict:
    teams = [canon_abbr(t) for t in teams]
    ids = lol_league_ids()
    lid = lol_league_id(league, ids)
    gaps: list[str] = []
    used_league = league
    if not lid:
        # 反查兜底：按优先顺序遍历联赛，找同时含两队的联赛。
        ta, tb = norm(teams[0]), norm(teams[1])
        ordered = sorted(
            ids.items(),
            key=lambda kv: (PRIORITY_LEAGUE_KEYS.index(kv[0]) if kv[0] in PRIORITY_LEAGUE_KEYS else 999, kv[0]),
        )
        for name, cid in ordered:
            if name in ("tftesports",):
                continue
            try:
                d = riot_get(f"{API_BASE}/getSchedule?hl=en-US&leagueId={cid}")
                codes = set()
                for ev in d.get("data", {}).get("schedule", {}).get("events", []):
                    for t in (ev.get("match") or {}).get("teams", []):
                        codes.add(norm(t.get("code") or t.get("name") or ""))
                if ta in codes and tb in codes:
                    lid, used_league = cid, name
                    break
            except Exception:  # noqa: BLE001
                continue
    if not lid:
        return {
            "game": "lol", "teams": teams, "league": league,
            "h2h": [], "recent": {teams[0]: [], teams[1]: []},
            "source": "riot",
            "gaps": [f"getLeagues 反查未找到包含 {teams[0]}/{teams[1]} 的当前联赛"],
        }
    r = _fetch_lol_lid(teams, used_league, lid, before)
    return {
        "game": "lol", "teams": teams, "league": league,
        "h2h": r["h2h"], "recent": r["recent"], "source": "riot",
        "gaps": gaps + r.get("gaps", []),
        "league_id": lid, "league_resolved": used_league,
    }


# --------------------------------------------------------------------------- CS2（Liquipedia + 本地）

def _clean_cell(x: str) -> str:
    """Liquipedia 表单元格清洗：HTML 实体反转义 + 去 non-breaking space（&#160;）。"""
    return _html.unescape(x or "").replace("\xa0", " ").strip()


def liqui_recent_matches(team: str) -> list[dict]:
    """队伍页 Recent Matches 表（锦标赛级）。返回 [{date, place, tournament, result, opponent}]。"""
    q = urllib.parse.urlencode({
        "action": "parse", "page": team, "prop": "text", "format": "json",
    })
    try:
        d = liqui_get(f"{LIQUI_API}?{q}")
        html = d.get("parse", {}).get("text", {})
        html = html.get("*", "") if isinstance(html, dict) else str(html)
    except Exception:  # noqa: BLE001
        return []
    i = html.find("Recent Matches")
    if i < 0:
        return []
    seg = html[i:i + 8000]
    rows: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S):
        cells = [re.sub(r"<[^>]+>", " ", c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        cells = [" ".join(c.split()) for c in cells]
        cells = [c for c in cells if c]
        if not cells or cells[0] == "Date":
            continue
        # 表头：Date | Place | Tier | Type | G. | Tournament | Result | Prize
        # 数据行 G. 列空占位不定，故最后 4 格固定为 Tournament/Result/Opponent/Prize，从后往前取。
        rec = {"date": cells[0] if cells else ""}
        if len(cells) >= 2:
            rec["place"] = _clean_cell(cells[1])
        if len(cells) >= 4:
            rec["tournament"] = _clean_cell(cells[-4])
            rec["result"] = _clean_cell(cells[-3])
            rec["opponent"] = _clean_cell(cells[-2])
        rows.append(rec)
    return rows


def cs2_local_h2h(teams: list[str], before: str | None = None) -> list[dict]:
    """复用本地 map_records.json 的同对阵记录（排除本场自身及之后）。"""
    ta, tb = norm(teams[0]), norm(teams[1])
    cutoff = (before or "")[:10]
    out: list[dict] = []
    # map_records.json：map 级
    try:
        d = json.loads((INTEL / "map_records.json").read_text(encoding="utf-8"))
        recs = d.get("records", d if isinstance(d, list) else [])
        for r in recs:
            a, b = norm(r.get("team_a")), norm(r.get("team_b"))
            if {a, b} != {ta, tb}:
                continue
            if cutoff and (r.get("date") or "") >= cutoff:
                continue  # 本场自身 / 之后，不算赛前历史
            out.append({
                "date": r.get("date", ""), "team_a": r.get("team_a"),
                "team_b": r.get("team_b"), "winner": r.get("winner"),
                "score": f"{r.get('score_a')}:{r.get('score_b')}",
                "map": r.get("map"), "source": r.get("source"),
            })
    except Exception:  # noqa: BLE001
        pass
    return out


def liqui_page_name(abbr: str) -> str:
    """情报库 abbr -> Liquipedia CS2 页面名（team_names.json 的 full 字段）。"""
    try:
        d = json.loads((INTEL / "team_names.json").read_text(encoding="utf-8"))
        want = norm(abbr)
        for t in d.get("teams", []):
            if norm(t.get("abbr")) == want or norm(t.get("full")) == want:
                return t.get("full") or abbr
            if want in [norm(a) for a in t.get("aliases", [])]:
                return t.get("full") or abbr
    except Exception:  # noqa: BLE001
        pass
    return abbr


def cs2_h2h_from_recent(teams: list[str], recent: dict) -> list[dict]:
    """从两队 Recent Matches 交叉提取 H2H（决赛级，place=1st 即赢方）。"""
    ta, tb = norm(teams[0]), norm(teams[1])
    out: list[dict] = []
    for t, opp in [(teams[0], teams[1]), (teams[1], teams[0])]:
        for r in recent.get(t, []):
            if norm(r.get("opponent")) == norm(opp):
                winner = t if (r.get("place") or "").lower() == "1st" else ""
                out.append({
                    "date": r.get("date", ""),
                    "team_a": t, "team_b": opp,
                    "tournament": r.get("tournament", ""),
                    "result": r.get("result", ""),
                    "place": r.get("place", ""),
                    "winner": winner,
                })
    # 去重（同一场决赛从双方各出现一次），按日期倒序
    seen: set = set()
    dedup: list[dict] = []
    for r in out:
        key = (r["date"], norm(r["team_a"]), norm(r["team_b"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    dedup.sort(key=lambda x: x["date"], reverse=True)
    return dedup


def fetch_cs2(teams: list[str], before: str | None = None) -> dict:
    teams = [canon_abbr(t) for t in teams]
    pages = [liqui_page_name(t) for t in teams]
    recent = {teams[0]: [], teams[1]: []}
    gaps: list[str] = []
    cutoff = (before or "")[:10]
    for t, p in zip(teams, pages):
        rows = liqui_recent_matches(p)
        if cutoff:
            rows = [r for r in rows if (r.get("date") or "") < cutoff]
        if not rows:
            gaps.append(f"{t}：Liquipedia Recent Matches 未取到（页面名 {p}）")
        recent[t] = rows
    h2h = cs2_h2h_from_recent(teams, recent)
    if not h2h:
        h2h = cs2_local_h2h(teams, before)
    if not h2h:
        gaps.append("两队无同对阵记录（Liquipedia 近期赛事 + 本地台账均无）")
    return {
        "game": "cs2", "teams": teams, "league": "CS2",
        "h2h": h2h, "recent": recent, "source": "liquipedia+local", "gaps": gaps,
    }


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="赛前页历史数据：H2H + 近况")
    ap.add_argument("--game", choices=["lol", "cs2"], required=True)
    ap.add_argument("--teams", required=True, help="A,B")
    ap.add_argument("--league", default="")
    ap.add_argument("--before", default="", help="本场开赛时间/日期，排除自身及之后")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    teams = [t.strip() for t in args.teams.split(",") if t.strip()]
    if len(teams) != 2:
        print("需要两个队伍 A,B", file=sys.stderr)
        return 1

    if args.game == "lol":
        if not args.league:
            print("lol 需提供 --league（如 LCK/LPL/LEC/LCP/LCK CL）", file=sys.stderr)
            return 1
        out = fetch_lol(teams, args.league, args.before or None)
    else:
        out = fetch_cs2(teams, args.before or None)

    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"written {args.out}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
