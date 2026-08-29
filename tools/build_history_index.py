#!/usr/bin/env python3
"""Build the historical danmaku intel library page with league/team/date filters.

Scans site intel/ for match reports (intel_danmu_<A>-<B>_<date>.html) and
detail shells (match_<id>.html), merges matches.json metadata, and emits
docs/data/intel/match_index.json + <site>/intel/history.html.

Usage:
  python3 tools/build_history_index.py [--site-dir .danmu_intel_site]
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
from pathlib import Path


def via_suffix() -> str:
    try:
        aff = json.loads(Path("config/affiliate.json").read_text(encoding="utf-8"))
        code = aff.get("polymarket_via", "")
        return f"?via={code}" if code else ""
    except (OSError, json.JSONDecodeError):
        return ""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def normalize_league(text: str) -> str:
    """Normalize any league/title string into a clean, non-overlapping label."""
    t = str(text).lower().strip()
    if not t or t in ("-", "none"):
        return "-"
    if "dota" in t or "the international" in t or "ti2026" in t or t.startswith("ti "):
        return "Dota2"
    if "counter-strike" in t or t.startswith("cs2") or t.startswith("cs ") or t.startswith("cs-"):
        return "CS2"
    if "valorant" in t:
        return "Valorant"
    if "lol" in t or "league of legends" in t or "lpl" in t or "lck" in t or "lec" in t or "lcp" in t or "lcs" in t:
        if "challengers" in t or "lck cl" in t or "lck-cl" in t or "lckcl" in t:
            return "LCK CL"
        if "kespa" in t or "k cup" in t or "k杯" in t or "杯赛" in t or "凯斯帕" in t:
            return "KeSPA Cup"
        if "lck" in t:
            return "LCK"
        if "lpl" in t:
            return "LPL"
        if "lec" in t:
            return "LEC"
        if "lcp" in t:
            return "LCP"
        if "lcs" in t:
            return "LCS"
        return "LoL 其他"
    if "kespa" in t or "k杯" in t or "杯赛" in t:
        return "KeSPA Cup"
    return "-"


def league_of_title(title: str) -> str:
    m = re.search(r"<title>(.*?)</title>", title, re.S | re.I)
    text = m.group(1) if m else title
    return normalize_league(text[:300])


TEAM_LEAGUE = {
    "LPL": {"we", "al", "ig", "nip", "tt", "lgd", "blg", "jdg", "edg", "tes", "wbg", "lng"},
    "LCK": {"t1", "kt", "hle", "dk", "gen", "ns", "bro", "bfx", "fox1", "drx", "dns", "krx", "dnf"},
    "LCK CL": {"drxc", "hle1", "t1a", "dnsc", "ktc", "nsea", "t1a"},
    "LEC": {"navi", "th", "sk", "kc", "gx", "giantx", "shft", "mkoi", "vit", "fnc", "g2"},
    "KeSPA Cup": {"krx", "dnsc", "dnf"},
    "CS2": {"spirit", "fut", "furia", "legacy", "faze", "liquid", "fnatic", "mouz", "astralis",
            "fokus", "parivision", "bestia", "eyeballers", "ace", "van", "lone", "vae", "og",
            "nrg", "k27", "shu", "magic", "g2", "falcons",
            # IEM Beijing 2026 预选（2026-08-24 服务器产出，扩充防"-"）
            "acend", "phantom", "5star", "kaleido", "morningstar", "rare atom",
            "the huns", "not a squad", "100 thieves", "inox", "nuclear tigres",
            "spirit academy", "quazar", "nemiga", "baks", "color", "echo",
            "cybershoke", "eternal fire", "insiders", "esport academy copenhagen"},
}


def league_by_teams(a: str, b: str) -> str:
    for lg, names in TEAM_LEAGUE.items():
        if a.lower() in names or b.lower() in names:
            return lg
    return "-"


TEAM_ALIAS = {
    "fox": "bfx", "fox1": "bfx", "gx": "giantx", "shft": "shifters", "mkoi": "koi",
    "hle1": "hle", "t1a": "t1", "dnsc": "dns", "ktc": "kt", "nsea": "ns",
    "dkc": "dk", "bro2": "bro", "drxc": "drx", "genga": "gen",
    "juhua": "legacy", "movistar koi": "koi", "sk gaming": "sk",
    "natus vincere": "navi", "team herethics": "th", "karmine corp": "kc",
    "g2 esports": "g2", "krxc": "krx", "bfxy": "bfx", "hlec": "hle",
    "foxy": "fox", "fearx youth": "foxy",
}
AGGREGATE_TEAMS = {
    "cs", "r2", "ewc", "lec", "s2", "lpl", "lck", "dota2", "ti",
    "eve", "batch", "index", "alerts", "workflow", "day1", "day2",
}

# 队伍统一清单（2026-08-26 定稿，最高标准）：
# docs/data/intel/team_names.json 是唯一权威；所有别名/全称/缩写归一到这里。
TEAM_REG: dict[str, str] = {}
TEAM_CANON: dict[str, dict] = {}
_REG = Path(__file__).resolve().parents[1] / "docs" / "data" / "intel" / "team_names.json"
if _REG.exists():
    try:
        for _t in json.loads(_REG.read_text(encoding="utf-8")).get("teams", []):
            tid = _t["id"]
            TEAM_CANON[tid] = _t
            for _k in [_t["abbr"], _t["full"], *_t.get("aliases", [])]:
                TEAM_REG[str(_k).lower()] = tid
    except Exception:  # noqa: BLE001
        pass


def norm_team(t: str) -> str:
    low = str(t).lower()
    return TEAM_REG.get(low) or TEAM_ALIAS.get(low, low)


def canon_teams(teams: list[str]) -> list[str]:
    """展示用规范缩写（KRX.C / BFX.Y），无登记则原样。"""
    out = []
    for t in teams:
        tid = TEAM_REG.get(str(t).lower()) or TEAM_ALIAS.get(str(t).lower())
        if tid and tid in TEAM_CANON:
            out.append(TEAM_CANON[tid]["abbr"])
        else:
            out.append(t)
    return out


def node_label_of(name: str) -> tuple[str, tuple]:
    """从情报文件名后缀提取节点标签 + 排序键（与时间轴壳同一口径）。

    高优先级（2026-08-25 用户要求）：历史列表按小局/节点分门别类列清楚，
    无情报的比赛明确标"暂无"。
    """
    body = name[len("intel_danmu_"):]
    body = re.sub(r"_\d{4}-\d{2}-\d{2}(?:\.html)?$", "", body)
    pair = body.split("_", 1)[0]
    suffix = body[len(pair):]
    if suffix == "":
        return ("系列复盘", (99, 0))
    if suffix == "_pre":
        return ("赛前", (0, 0))
    m = re.match(r"_g(\d+)_(bp|mid|end)$", suffix)
    if m:
        gi, ph = int(m.group(1)), m.group(2)
        label = {"bp": "BP 后", "mid": "局中", "end": "结束"}[ph]
        order = {"bp": 1, "mid": 2, "end": 3}[ph]
        return (f"G{gi}·{label}", (gi, order))
    m = re.match(r"_G(\d+)$", suffix)
    if m:
        return (f"G{int(m.group(1))}·情报", (int(m.group(1)), 4))
    if suffix.startswith("_live"):
        return ("局中快照", (50, 0))
    if suffix == "_full":
        return ("整场复盘", (98, 0))
    if suffix == "_BP":
        return ("BP", (1, 0))
    return (suffix.lstrip("_"), (60, 0))


def key_teams(teams: list[str]) -> frozenset:
    """队伍集合键：别名归一（同时查带空格/不带空格形式）+ 去点/空格。

    教训 2026-08-25：G2 Esports 走别名得 g2、Natus Vincere 走别名得 navi，
    但先去空格再查别名会漏（g2esports 无别名）——两条路径结果不一致
    导致同一场比赛被误判"暂无"。
    """
    out = set()
    for t in teams:
        low = str(t).lower()
        stripped = re.sub(r"[.\s]", "", low)
        v = TEAM_REG.get(low) or TEAM_REG.get(stripped) or TEAM_ALIAS.get(low) or TEAM_ALIAS.get(stripped) or low
        out.add(re.sub(r"[.\s]", "", v).lower())
    return frozenset(out)


MATCH_FILE_RE = re.compile(
    # 支持联赛前缀命名（LCK-KT-BRO / LCKCL-KRXC-BFXY / LEC-FNC-NAVI / DOTA-BB-PV）
    r"intel_danmu_(?:[A-Za-z0-9\u4e00-\u9fff]+-)?([A-Za-z0-9\u4e00-\u9fff]+)-([A-Za-z0-9\u4e00-\u9fff]+)"
    r"(?:_[A-Za-z0-9]+)*_(\d{4}-\d{2}-\d{2})\.html"
)

# 文件名不符合标准 A-B_date 模式、但确实是单场比赛情报页的特殊映射。
# 值 = (队伍A, 队伍B, 比赛日期)。绿龙 = Spirit（EWC CS2，弹幕昵称）。
SPECIAL_FILES = {
    "intel_danmu_CS-绿龙-Legacy_2026-08-23.html": ("spirit", "legacy", "2026-08-23"),
    "intel_danmu_DOTA-IW-TS_2026-08-20.html": ("Iron Wing", "Team Spirit", "2026-08-20"),
    "intel_danmu_DOTA-BB-PV_2026-08-20.html": ("BoomBoys", "Team Vision", "2026-08-20"),
    "intel_danmu_CS-ASTRALIS-G2_2026-08-19.html": ("Astralis", "G2", "2026-08-19"),
    "intel_danmu_CS-MAGIC-FUT_2026-08-19.html": ("Magic", "FUT", "2026-08-19"),
}


def _meta_richness(m: dict) -> int:
    """情报完整性评分，用于同一场比赛多条元数据时挑最全的一条。"""
    score = 0
    if m.get("event_slug"):
        score += 4
    if m.get("games"):
        score += 2
    if m.get("predictions"):
        score += 2
    if m.get("danmu_count") is not None:
        score += 2
    if m.get("gray_signals_count") is not None:
        score += 1
    if m.get("key_signals"):
        score += 1
    return score


def _meta_candidates(meta: list, a: str, b: str, date: str) -> list:
    """匹配同一对队伍的结构化情报记录：优先同日，其次 ±1 天（时区偏移）。"""
    target = key_teams([a, b])
    scored = []
    for m in meta:
        teams = m.get("teams") or []
        if len(teams) != 2:
            continue
        if key_teams(teams) != target:
            continue
        md = m.get("date", "")
        if md == date:
            scored.append((0, _meta_richness(m), m))
            continue
        try:
            diff = abs((datetime.date.fromisoformat(date) - datetime.date.fromisoformat(md)).days)
        except ValueError:
            diff = 99
        if diff <= 1:
            scored.append((diff, _meta_richness(m), m))
    scored.sort(key=lambda x: (x[0], -x[1]))
    return [m for _, _, m in scored]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default=".danmu_intel_site")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    ap.add_argument("--out-index", default="docs/data/intel/match_index.json")
    args = ap.parse_args()

    site = Path(args.site_dir) / "intel"
    matches: dict[tuple[str, frozenset], dict] = {}

    mj = Path(args.matches_json)
    meta = {}
    meta_by_key: dict = {}
    meta_list: list = []
    if mj.exists():
        data = json.loads(mj.read_text(encoding="utf-8"))
        meta_list = data.get("matches", [])
        meta = {m.get("id"): m for m in data.get("matches", []) if m.get("id")}
        for m in meta_list:
            teams = m.get("teams", [])
            if len(teams) == 2:
                key = (m.get("date", ""), frozenset(norm_team(t) for t in teams))
                meta_by_key.setdefault(key, m)

    for f in site.glob("intel_danmu_*.html"):
        # 特殊文件（中文昵称等）优先匹配，避免前缀正则误解析（如 CS-绿龙-Legacy）
        special = SPECIAL_FILES.get(f.name)
        if special:
            a, b, date = special
        else:
            m = MATCH_FILE_RE.match(f.name)
            if not m:
                continue
            a, b, date = norm_team(m.group(1)), norm_team(m.group(2)), m.group(3)
        if a in AGGREGATE_TEAMS or b in AGGREGATE_TEAMS:
            continue  # aggregate pages (战报/汇总), not single matches
        key = (date, key_teams([a, b]))
        title = f.read_text(encoding="utf-8", errors="ignore")
        lg = league_of_title(title)
        metas = _meta_candidates(meta_list, a, b, date)
        mm = metas[0] if metas else {}
        teams = mm.get("teams") or [a, b]
        teams = canon_teams(teams)  # 统一清单：展示用规范缩写（KRX.C / BFX.Y）
        mm_league = normalize_league(mm.get("league", "-"))
        guess = league_by_teams(a, b)
        rec = matches.setdefault(
            key,
            {
                "date": date,
                "league": mm_league if mm_league != "-" else (lg if lg != "-" else guess),
                "teams": teams,
                "result": mm.get("result_inferred", ""),
                "report": f.name,
                "detail": "",
                "nodes": 0,
                "node_labels": [],
                "slug": mm.get("event_slug", ""),
            },
        )
        if not rec.get("slug"):
            rec["slug"] = mm.get("event_slug", "")
        rec["report"] = f.name
        rec["nodes"] += 1
        label, lkey = node_label_of(f.name)
        if not any(l == label for l, _ in rec["node_labels"]):
            rec["node_labels"].append((label, lkey))
        if not rec["result"]:
            rec["result"] = mm.get("result_inferred", "")
        if not rec["result"]:
            rec["result"] = "局中情报·结果待定（等整场复盘回填）"

    for shell in site.glob("match_*.html"):
        m = re.match(r"match_(\d{4}-\d{2}-\d{2})_([a-z0-9]+)_([a-z0-9]+)\.html", shell.name)
        if m:
            date = m.group(1)
            a, b = m.group(2), m.group(3)
            mm = {}
            # 遗留壳用 h1 的正式队名展示（文件名是缩写）
            h1m = re.search(r"<h1>(.*?) vs (.*?)</h1>", shell.read_text(encoding="utf-8", errors="ignore"))
            if h1m:
                a, b = h1m.group(1).strip(), h1m.group(2).strip()
        else:
            # 服务器产出壳：match_<slug>.html（slug 在 matches.json 有记录）
            mid = shell.name[6:-5]
            mm = meta.get(mid) or {}
            if not mm:
                # 2026-08-29：canonical 条目 id 为 lpl-tt-ig，壳按 event_slug
                # （lol-tt-ig1）命名——按 event_slug 匹配，保证历史页链接到
                # 时间轴壳（可切换节点）而非裸报告页。
                mm = next(
                    (m for m in meta_list if str(m.get("event_slug") or "") == mid),
                    {},
                )
            if not mm:
                continue
            date = mm.get("date") or mid[-10:]
            teams = mm.get("teams") or []
            if len(teams) != 2:
                continue
            a, b = norm_team(teams[0]), norm_team(teams[1])
        if a in AGGREGATE_TEAMS or b in AGGREGATE_TEAMS:
            continue
        key = (date, key_teams([a, b]))
        rec = matches.setdefault(
            key,
            {"date": date, "league": "-", "teams": [a, b], "result": "", "report": "", "detail": shell.name, "nodes": 0, "slug": ""},
        )
        if mm.get("teams"):
            rec["teams"] = canon_teams(mm["teams"])  # 统一清单：规范缩写展示
        rec["detail"] = shell.name
        mid = f"{date}_{a}_{b}"
        rec["nodes"] = len(list(site.glob(f"node_{mid}_g*.html")))
        if not mm:
            metas = _meta_candidates(meta_list, a, b, date)
            mm = metas[0] if metas else {}
        if not rec["result"]:
            rec["result"] = mm.get("result_inferred", "")
        if not rec["result"]:
            rec["result"] = "结果待定（未回填）"
        if rec["league"] == "-":
            rec["league"] = normalize_league(mm.get("league", "-"))
        if rec["league"] == "-":
            rec["league"] = league_by_teams(a, b)
        if not rec.get("slug"):
            rec["slug"] = mm.get("event_slug", "")

    # 壳节点明细：有壳的比赛以壳按钮为准（赛前 / G1… / 局中快照 / 系列复盘）
    for r in matches.values():
        if r.get("detail") and not r.get("node_labels"):
            shell = site / r["detail"]
            if shell.exists():
                t = shell.read_text(encoding="utf-8", errors="ignore")
                labels = re.findall(r'class="nbtn" data-src="[^"]+"[^>]*>\s*([^<]+)', t)
                r["node_labels"] = [
                    (l.strip(), (0, i)) for i, l in enumerate(labels) if l.strip()
                ]

    index = sorted(matches.values(), key=lambda r: r["date"], reverse=True)

    # 无情报的比赛（matches.json 有记录但无任何情报文件）-> 明确标"暂无"
    # （高优先级 2026-08-25：有情报的按小局/节点列清楚，无情报的写"暂无"）
    index_keys = {(r["date"], key_teams(r["teams"])) for r in index}
    for mm in meta.values():
        if mm.get("intel_voided"):
            continue  # 作废场次整行移除（2026-08-26 固化，AGENTS 19：Aurora-G2 混源作废）
        if not mm.get("teams") or len(mm["teams"]) != 2:
            continue
        lg = normalize_league(mm.get("league", "-"))
        if lg == "-":
            continue
        teams = mm["teams"]
        try:
            mdate = datetime.date.fromisoformat(mm.get("date", ""))
        except ValueError:
            mdate = None
        hit = any(
            key_teams(r["teams"]) == key_teams(teams)
            and (
                mdate is None
                or abs(
                    (datetime.date.fromisoformat(r["date"]) - mdate).days
                )
                <= 1
            )
            for r in index
        )
        if not hit:
            index.append({
                "date": mm.get("date", ""), "league": lg, "teams": teams,
                "result": mm.get("result_inferred", ""), "report": "", "detail": "",
                "nodes": 0, "node_labels": [], "slug": mm.get("event_slug", ""),
                "no_intel": True,
            })
    index.sort(key=lambda r: r["date"], reverse=True)
    today = datetime.date.today().isoformat()
    Path(args.out_index).write_text(
        json.dumps({"updated_at": today, "matches": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 市场链接页按北京时间分桶（教训 2026-08-26：UTC 日期会让北京次日时
    # "今日比赛"显示昨天；与今日页同一口径）
    bj_today = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).date()
    today = bj_today.isoformat()
    week_start = (bj_today - datetime.timedelta(days=6)).isoformat()
    market = [r for r in index if r.get("slug")]

    def market_rows(items, ended: bool = True) -> str:
        if not items:
            return '<div class="row"><span class="tm">暂无已确认市场链接，等每日扫描更新</span></div>'
        return "".join(
            f'<div class="row{" ended" if ended else " up"}"><span class="lg">{esc(r["league"])}</span>'
            f'<span class="tm">{esc(" vs ".join(r["teams"]))}</span>'
            f'<span class="dt">{esc(r["date"])}</span>'
            f'<span class="rs">{esc(r.get("result", "")[:24] or "待确认")}</span>'
            f'<span class="st"><a href="https://polymarket.com/event/{esc(r["slug"])}{via_suffix()}" target="_blank" rel="noopener">市场 →</a></span></div>'
            for r in items
        )

    # 本周未开始（重点）：来自最近一次 Polymarket 扫描
    wl = Path("runtime/watchlist_events.json")
    future = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    week_end = now_utc + datetime.timedelta(days=7)
    if wl.exists():
        try:
            wdata = json.loads(wl.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            wdata = {}
        evs = wdata if isinstance(wdata, list) else wdata.get("events", wdata.get("matches", []))
        for e in evs:
            slug = e.get("slug", "")
            st = e.get("start_time") or ""
            if not slug or not st:
                continue
            try:
                st_dt = datetime.datetime.fromisoformat(st.replace("Z", "+00:00"))
            except ValueError:
                continue
            if now_utc - datetime.timedelta(hours=2) <= st_dt <= week_end:
                title = e.get("title", "")
                mm = re.search(r":\s*(.+?)\s+vs\s+(.+?)\s*(?:\(|\-|$)", title, re.I)
                teams = [mm.group(1).strip(), mm.group(2).strip()] if mm else [title[:36]]
                lg = normalize_league(title)
                if lg == "LCS":
                    continue
                future.append(
                    {
                        "league": lg,
                        "teams": teams,
                        "date": st_dt.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime("%m-%d %H:%M"),
                        "result": "",
                        "slug": slug,
                    }
                )
    future.sort(key=lambda r: r["date"])
    future_rows = market_rows(future, ended=False) if future else (
        '<div class="row"><span class="tm">暂无未来 7 天已确认场次（等每日扫描更新）</span></div>'
    )
    today_rows = market_rows([r for r in market if r["date"] == today])
    week_rows = market_rows([r for r in market if week_start <= r["date"] < today])
    mpage = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="最新 Polymarket 市场链接：每日 + 本周 · 弹幕情报库">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<title>最新市场链接（每日 + 本周）· 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 56px}}
.wrap{{max-width:900px;margin:0 auto}}
nav{{position:sticky;top:0;z-index:10;background:rgba(245,245,247,.86);backdrop-filter:saturate(180%) blur(16px);border-bottom:1px solid var(--line);margin-bottom:22px}}
nav .inner{{display:flex;align-items:center;gap:16px;max-width:900px;margin:0 auto;padding:11px 16px;flex-wrap:wrap}}
nav a{{color:var(--sub);text-decoration:none;font-size:13px;font-weight:500}}
nav a:hover{{color:var(--accent)}}
h1{{font-size:23px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 18px;margin-bottom:14px}}
.card h2{{font-size:14px;font-weight:800;margin-bottom:6px}}
.row{{display:grid;grid-template-columns:70px 1fr 100px 110px auto;gap:10px;align-items:center;padding:9px 2px;border-bottom:1px solid var(--line);font-size:12.5px}}
.row:last-child{{border-bottom:0}}
.row.ended{{opacity:.6}}
.row.ended .tm{{text-decoration:line-through}}
.row.up .lg{{background:#e8f1fd}}
.row.up .dt{{font-weight:700;color:var(--accent)}}
.lg{{font-size:11px;font-weight:700;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:2px 8px;text-align:center}}
.dt,.rs{{color:var(--sub);font-size:11.5px}}
.rs{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.st a{{color:var(--accent);text-decoration:none;font-weight:600}}
.note{{color:var(--sub);font-size:12px;margin-top:10px}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
@media(max-width:680px){{.row{{grid-template-columns:60px 1fr auto}} .rs{{display:none}}}}
</style></head><body><div class="wrap">
<nav><div class="inner">
  <a href="../index.html" style="font-weight:700;color:var(--ink)">弹幕情报库</a>
  <a href="today.html">今日比赛</a>
  <a href="market_links.html" style="color:var(--accent);font-weight:700">市场链接</a>
  <a href="history.html">历史情报库</a>
  <a href="../subscribe.html">订阅</a>
</div></nav>
<h1>最新市场链接</h1>
<div class="sub">每日 + 本周最新（Polymarket 电竞）· 历史链接见<a href="history.html" style="color:var(--accent)">历史情报库</a></div>
<div class="card"><h2>本周未开始（重点关注）</h2>{future_rows}</div>
<div class="card"><h2>今日（{esc(today)}）</h2>{today_rows}</div>
<div class="card"><h2>本周已结束（{esc(week_start)} ~ {esc(today)}）</h2>{week_rows}</div>
<div class="note">市场链接在每场情报页内同样提供；每日流水线自动更新本页。</div>
<footer>弹幕情报库 · 最新市场链接 · {esc(today)}</footer>
</div></body></html>"""
    (site / "market_links.html").write_text(mpage, encoding="utf-8")
    print(f"wrote market_links.html ({len(market)} with slug)")

    from collections import Counter
    leagues = sorted({r["league"] for r in index if r["league"] != "-"})
    league_dist = Counter(r["league"] for r in index)
    n_total = len(index)
    n_result = sum(1 for r in index if r["result"])
    n_detail = sum(1 for r in index if r["detail"])
    n_nodes = sum(1 for r in index if r["nodes"])
    teams = sorted({t for r in index for t in r["teams"]})
    chips = '<button class="chip" aria-pressed="true" data-lg="all">全部</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-lg="{esc(l)}">{esc(l)}</button>' for l in leagues
    )
    stats = (
        f'<div class="stats">'
        f'<div class="stat"><div class="num">{n_total}</div><div class="lbl">历史场次</div></div>'
        f'<div class="stat"><div class="num">{len(leagues)}</div><div class="lbl">覆盖联赛</div></div>'
        f'<div class="stat"><div class="num">{n_result}/{n_total}</div><div class="lbl">结果已回填</div></div>'
        f'<div class="stat"><div class="num">{n_detail} 壳 · {n_nodes} 节点</div><div class="lbl">情报完整度</div></div>'
        f'</div>'
    )
    team_opts = '<option value="all">全部队伍</option>' + "".join(
        f'<option value="{esc(t.lower())}">{esc(t)}</option>' for t in teams
    )

    rows = ""
    for r in index:
        a, b = r["teams"][:2]
        # 统一描述词：每行一个"情报"入口（优先多节点壳，其次整场复盘）
        # 教训 2026-08-25：曾出现"多节点 / 复盘"两种描述，用户要求只有一种。
        btns = ""
        target = r["detail"] or r["report"]
        if target:
            btns += f'<a class="b" href="{esc(target)}">情报</a>'
        if r.get("no_intel"):
            node_line = '<div class="nd none">暂无</div>'
        elif r.get("node_labels"):
            labels = sorted(r["node_labels"], key=lambda x: x[1])
            node_line = '<div class="nd">' + " · ".join(esc(l) for l, _ in labels) + "</div>"
        elif r.get("nodes"):
            node_line = f'<div class="nd">{r["nodes"]} 节点</div>'
        else:
            node_line = ""
        rows += (
            f'<div class="row" data-lg="{esc(r["league"])}" data-team="{esc(a.lower())} {esc(b.lower())}" data-date="{esc(r["date"])}">'
            f'<span class="lg">{esc(r["league"])}</span>'
            f'<div class="main"><span class="tm">{esc(a)} vs {esc(b)}</span>{node_line}</div>'
            f'<span class="dt">{esc(r["date"])}</span>'
            f'<span class="rs" title="{esc(r["result"] or "待确认")}">{esc(r["result"] or "待确认")}</span>'
            f'<span class="st">{btns or "暂无情报"}</span></div>'
        )
    if not rows:
        rows = '<div class="row"><span class="tm">暂无历史情报</span></div>'

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="历史弹幕情报库：按联赛 / 队伍 / 日期检索已采集的比赛弹幕情报">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<title>历史弹幕情报库 · Danmu Intel</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 60px}}
.wrap{{max-width:980px;margin:0 auto}}
h1{{font-size:24px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:14px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px}}
.stat .num{{font-size:20px;font-weight:800;color:var(--accent)}}
.stat .lbl{{font-size:11.5px;color:var(--sub);margin-top:2px}}
.filters{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}}
.chip{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:6px 14px;font-size:12px;font-weight:600;color:var(--sub);cursor:pointer}}
.chip[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
select,input{{border:1px solid var(--line);background:var(--card);border-radius:10px;padding:7px 12px;font-size:12.5px;color:var(--ink);font-family:inherit}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:8px 16px}}
.row{{display:grid;grid-template-columns:74px 1fr 110px 160px auto;gap:12px;align-items:center;padding:11px 2px;border-bottom:1px solid var(--line);font-size:13px}}
.row:last-child{{border-bottom:0}}
.lg{{font-size:11px;font-weight:700;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:2px 9px;text-align:center}}
.tm{{font-weight:600}}
.main{{min-width:0}}
.nd{{font-size:11px;color:var(--sub);margin-top:2px}}
.nd.none{{color:#b0b0b6}}
.dt{{color:var(--sub);font-size:12px}}
.rs{{color:var(--sub);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.st{{display:flex;gap:8px;justify-content:flex-end;align-items:center}}
.st .b{{color:var(--accent);text-decoration:none;font-size:12px;font-weight:600}}
.st .n{{font-size:11px;color:var(--sub);background:#fafafa;border:1px solid var(--line);border-radius:999px;padding:2px 8px}}
.empty{{display:none;color:var(--sub);font-size:13px;text-align:center;padding:26px 0}}
.note{{color:var(--sub);font-size:12px;margin-top:10px}}
footer{{margin-top:18px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
@media (max-width:760px){{.row{{grid-template-columns:70px 1fr;row-gap:2px}} .dt,.rs{{grid-column:2}} .st{{grid-column:2;justify-content:flex-start}}}}
</style></head><body><div class="wrap">
<h1>历史弹幕情报库</h1>
<div class="sub">已采集比赛的弹幕情报存档 · 按联赛 / 队伍 / 日期筛选 · 共 {len(index)} 场</div>
{stats}
<div class="filters">
  {chips}
  <select id="team">{team_opts}</select>
  <input type="text" id="q" placeholder="搜索队伍 / 联赛 / 关键词…" style="min-width:200px">
  <input type="date" id="date" title="按日期筛选">
  <button class="chip" id="reset">重置</button>
</div>
<div class="card">{rows}</div>
<div class="empty" id="empty">没有匹配的情报，换个筛选条件试试</div>
<div class="note">每行一个「情报」入口；节点明细按 赛前 / 小局（BP后·局中·结束） / 局中快照 / 系列复盘 列出；无情报的比赛标「暂无」。新比赛实时采集后会自动入库。</div>
<footer>弹幕情报库 · 历史存档 · 2026-08-24</footer>
</div>
<script>
(function () {{
  var chips = document.querySelectorAll(".chip[data-lg]");
  var rows = document.querySelectorAll(".row");
  var team = document.getElementById("team");
  var q = document.getElementById("q");
  var date = document.getElementById("date");
  var reset = document.getElementById("reset");
  var empty = document.getElementById("empty");
  var lg = "all";
  function apply() {{
    var t = team.value, d = date.value, kw = q.value.trim().toLowerCase();
    var visible = 0;
    rows.forEach(function (r) {{
      var ok = (lg === "all" || r.getAttribute("data-lg") === lg)
        && (t === "all" || r.getAttribute("data-team").indexOf(t) >= 0)
        && (!d || r.getAttribute("data-date") === d)
        && (!kw || r.textContent.toLowerCase().indexOf(kw) >= 0);
      r.style.display = ok ? "" : "none";
      if (ok) visible++;
    }});
    empty.style.display = visible ? "none" : "block";
  }}
  chips.forEach(function (c) {{
    c.addEventListener("click", function () {{
      chips.forEach(function (x) {{ x.setAttribute("aria-pressed", x === c ? "true" : "false"); }});
      lg = c.getAttribute("data-lg"); apply();
    }});
  }});
  team.addEventListener("change", apply);
  q.addEventListener("input", apply);
  date.addEventListener("change", apply);
  reset.addEventListener("click", function () {{
    lg = "all"; team.value = "all"; date.value = ""; q.value = "";
    chips.forEach(function (x) {{ x.setAttribute("aria-pressed", x.getAttribute("data-lg") === "all" ? "true" : "false"); }});
    apply();
  }});
}})();
</script>
</body></html>"""

    out = site / "history.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(index)} matches)")


if __name__ == "__main__":
    main()
