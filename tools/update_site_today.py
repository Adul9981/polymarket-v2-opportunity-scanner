#!/usr/bin/env python3
"""Generate the danmu-intel site's auto "today matches" page.

Reads runtime/watchlist_events.json (latest live scan) and
docs/data/intel/matches.json (confirmed event_slug entries), writes
runtime/intel_today.json + <site>/intel/today.html with Polymarket market links.

Usage:
  python3 tools/update_site_today.py --date 2026-08-23
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import re
from datetime import datetime as dt_fmt, timedelta, timezone
from pathlib import Path

from match_status import match_status


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def fmt_time(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = dt_fmt.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso[:16]
    dt = dt.astimezone(timezone(timedelta(hours=8)))
    return dt.strftime("%m-%d %H:%M")


def bj_date_of(start_raw: str, slug: str = "") -> str:
    """开赛时间的北京时间日期（今日/明日一律按 +8 时区分桶）。

    教训 2026-08-26：页面曾按服务器 UTC 日期生成，北京时间 08-26 时
    页面仍显示 08-25；今日页的"今日"必须用北京时间。
    """
    if start_raw:
        try:
            dt = dt_fmt.fromisoformat(str(start_raw).replace("Z", "+00:00"))
            return dt.astimezone(timezone(timedelta(hours=8))).date().isoformat()
        except ValueError:
            pass
    m = re.search(r"-(\d{4}-\d{2}-\d{2})$", slug or "")
    if m:
        return m.group(1)
    return ""


def league_of(title: str) -> str:
    t = title.lower()
    if t.startswith("lol:"):
        for lg in ("LPL", "LCK", "LEC", "LCP", "LCS"):
            if lg.lower() in t:
                return lg
        return "LoL"
    if "dota 2:" in t or t.startswith("dota2"):
        return "Dota2"
    if t.startswith("counter-strike:"):
        return "CS2"
    if t.startswith("valorant:"):
        return "Valorant"
    return "-"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--watchlist", default="runtime/watchlist_events.json")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    ap.add_argument("--site-dir", default=".danmu_intel_site")
    args = ap.parse_args()

    rows: list[dict] = []
    rows_tomorrow: list[dict] = []
    tomorrow = (
        dt_fmt.fromisoformat(args.date).date() + timedelta(days=1)
    ).isoformat()
    # 作废场次排除（2026-08-26 固化，AGENTS 19 教训：Aurora-G2 混源整场作废，
    # 不得再出现在今日页/明日预告/统计）
    voided_slugs: set[str] = set()
    mj_v = Path(args.matches_json)
    if mj_v.exists():
        try:
            for _m in json.loads(mj_v.read_text(encoding="utf-8")).get("matches", []):
                if _m.get("intel_voided"):
                    voided_slugs.add(_m.get("slug") or _m.get("id") or "")
        except Exception:  # noqa: BLE001
            pass
    wl = Path(args.watchlist)
    if wl.exists():
        data = json.loads(wl.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("events", data.get("items", []))
        for e in items:
            slug = e.get("slug", "")
            if slug in voided_slugs:
                continue
            start = e.get("start_time") or e.get("startDate") or e.get("start_date") or ""
            d = bj_date_of(start, slug)
            # 只放「今天开赛」的场次；昨天跨日仍在进行的场次仅在实时未结束时保留
            # （教训：今日页曾混入 08-23/08-24 已结束旧比赛，违反"清清爽爽"原则）
            is_today = d == args.date
            end_raw = e.get("end_time", e.get("end_date", "")) or ""
            end_dt = None
            if end_raw:
                try:
                    end_dt = dt_fmt.fromisoformat(end_raw.replace("Z", "+00:00"))
                except ValueError:
                    end_dt = None
            still_live = (
                str(e.get("time_status", "")).lower()
                in ("started_recently_or_live", "live", "in_progress")
                and end_dt is not None
                and end_dt >= dt_fmt.now(datetime.timezone.utc)
            )
            if slug and (is_today or still_live):
                title = e.get("title", e.get("name", "-"))
                lg = league_of(title)
                if lg == "LCS":
                    continue  # 用户指定：英雄联盟只看 LCK / LPL / LEC，不要 LCS
                row = {
                    "league": lg,
                    "title": title,
                    "slug": slug,
                    "date": d,
                    "time": fmt_time(start),
                    "status": e.get("time_status", ""),
                    "start_raw": start,
                    "end_raw": e.get("end_time", e.get("end_date", "")),
                }
                rows.append(row)
            elif slug and d == tomorrow and str(e.get("time_status", "")).lower() in (
                "upcoming_within_window", "upcoming",
            ):
                title = e.get("title", e.get("name", "-"))
                lg = league_of(title)
                if lg == "LCS":
                    continue
                rows_tomorrow.append(
                    {
                        "league": lg,
                        "title": title,
                        "slug": slug,
                        "date": d,
                        "time": fmt_time(start),
                        "status": e.get("time_status", ""),
                        "start_raw": start,
                        "end_raw": e.get("end_time", e.get("end_date", "")),
                    }
                )
    mj = Path(args.matches_json)
    if mj.exists():
        md = json.loads(mj.read_text(encoding="utf-8"))
        for m in md.get("matches", []):
            if m.get("intel_voided"):
                continue  # 作废场次不进入今日页/明日预告（2026-08-26，AGENTS 19）
            if m.get("date") == args.date and m.get("event_slug"):
                slug = m.get("event_slug", "")
                if slug and slug in {r.get("slug", "") for r in rows}:
                    continue  # 已在 watchlist 中出现，避免重复行（教训 2026-08-26）
                rows.append(
                    {
                        "league": m.get("league", "-"),
                        "title": " vs ".join(m.get("teams", [])) or m.get("id"),
                        "slug": slug,
                        "date": args.date,
                        "time": "",
                        "status": "",
                        "start_raw": "",
                        "end_raw": "",
                    }
                )

    out_json = Path("runtime/intel_today.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"date": args.date, "matches": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def parse_dt(iso: str):
        if not iso:
            return None
        try:
            return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(
                timezone(timedelta(hours=8))
            )
        except ValueError:
            return None

    now = datetime.datetime.now(timezone(timedelta(hours=8)))
    site_dir = Path(args.site_dir)
    site_dir.mkdir(parents=True, exist_ok=True)

    def short_title(title: str) -> str:
        m = re.search(r":\s*(.+?)\s*-\s*", title or "")
        return (m.group(1).strip() if m else title).strip()

    def via_suffix() -> str:
        try:
            code = json.loads(
                Path("config/affiliate.json").read_text(encoding="utf-8")
            ).get("polymarket_via", "")
            return f"?via={code}" if code else ""
        except Exception:  # noqa: BLE001
            return ""

    def market_link(slug: str) -> str:
        if not slug:
            return ""
        return (
            f'<a class="b" href="https://polymarket.com/event/{esc(slug)}{via_suffix()}" '
            f'target="_blank" rel="noopener">市场 →</a>'
        )

    def status_of(r: dict) -> str:
        # 2026-08-27 固化：今日页状态优先采用 matches.json 权威状态
        # （教训：CS2 短队名 "9z" 等导致整场页匹配失败，MOUZ-9z 已结束
        # 却仍显示"未开始"；matches.json 由官方数据源回填，作为最高优先）。
        _, _m = match_info(r["title"], r.get("date", ""))
        if _m and _m.get("status") in ("已结束", "进行中", "未开始"):
            return {"已结束": "ended", "进行中": "live", "未开始": "upcoming"}[_m["status"]]
        return match_status(
            r.get("start_raw", ""), r.get("end_raw", ""), r.get("status", ""),
            r.get("title", ""), r.get("date", ""), now, site_dir / "intel",
        )

    # 结果与情报入口（按 teams 关联 matches.json）
    # 队伍名称归一化（2026-08-26 固化：统一用 team_names.json 的 abbr，
    # 避免 "KT Rolster" vs "KT"、"HANJIN BRION" vs "BRO" 匹配失败导致结果待回填）
    _abbr_map: dict[str, str] = {}
    _tn_path = Path("docs/data/intel/team_names.json")
    if _tn_path.exists():
        try:
            for _t in json.loads(_tn_path.read_text(encoding="utf-8")).get("teams", []):
                for _k in [_t.get("abbr", ""), _t.get("full", ""), *_t.get("aliases", [])]:
                    _abbr_map[str(_k).strip().lower()] = _t.get("abbr", str(_k))
        except Exception:  # noqa: BLE001
            pass

    def norm_team(name: str) -> str:
        return _abbr_map.get(str(name).strip().lower(), str(name).strip().lower())

    md_by_teams = {}
    md_list = []
    if mj.exists():
        md_list = json.loads(mj.read_text(encoding="utf-8")).get("matches", [])
        for m in md_list:
            teams = m.get("teams", [])
            if len(teams) == 2:
                md_by_teams[(m.get("date"), tuple(sorted(norm_team(t) for t in teams)))] = m

    def match_info(title: str, date: str) -> tuple[dict, dict | None]:
        mm = re.search(r":\s*(.+?)\s+vs\s+(.+?)\s*(?:\(|\-|$)", title or "", re.I)
        if not mm:
            return {}, None
        teams = tuple(sorted([norm_team(mm.group(1)), norm_team(mm.group(2))]))
        m = md_by_teams.get((date, teams))
        return {}, m

    def intel_link(m: dict | None, title: str, date: str, slug: str = "") -> str:
        if slug:
            shell = site_dir / "intel" / f"match_{slug}.html"
            if shell.exists():
                return f'<a class="b" href="{esc(shell.name)}">情报 →</a>'
        if not m:
            pass
        else:
            for rep in m.get("reports", []) or []:
                name = str(rep).rsplit("/", 1)[-1]
                if (site_dir / "intel" / name).exists():
                    return f'<a class="b" href="{esc(name)}">情报 →</a>'
        # 扫描站点目录：按对阵关键词匹配（服务器自动产出等均可命中）
        mm = re.search(r"(.+?)\s+vs\s+(.+?)\s*(?:\(|\-|$)", title or "", re.I)
        if not mm:
            return ""
        k1 = [w for w in re.split(r"\s+", re.sub(r"\(.*?\)", "", mm.group(1))) if len(w) > 2]
        k2 = [w for w in re.split(r"\s+", re.sub(r"\(.*?\)", "", mm.group(2))) if len(w) > 2]
        if not k1 or not k2:
            return ""
        matches = []
        for f in (site_dir / "intel").glob(f"intel_danmu_*{date}.html"):
            low = f.name.lower()
            if any(w.lower() in low for w in k1) and any(w.lower() in low for w in k2):
                matches.append(f.name)
        if not matches:
            return ""
        # 优先时间轴壳（match_*.html，支持节点切换）
        for f in (site_dir / "intel").glob(f"match_*{date}*.html"):
            low = f.name.lower()
            if any(w.lower() in low for w in k1) and any(w.lower() in low for w in k2):
                return f'<a class="b" href="{esc(f.name)}">情报 →</a>'
        # 优先整场页（非 _live），否则局中页
        matches.sort(key=lambda n: ("_live" in n, n))
        name = matches[0]
        return f'<a class="b" href="{esc(name)}">情报 →</a>'

    leagues = sorted({r["league"] for r in rows if r["league"] != "-"})
    chips = '<button class="chip" aria-pressed="true" data-lg="all">全部</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-lg="{esc(l)}">{esc(l)}</button>' for l in leagues
    )

    grouped = {"upcoming": [], "live": [], "ended": []}
    for r in rows:
        grouped[status_of(r)].append(r)
    def start_ts(r: dict) -> float:
        dt = parse_dt(r.get("start_raw"))
        return dt.timestamp() if dt else float("inf")

    grouped["upcoming"].sort(key=start_ts)
    grouped["live"].sort(key=start_ts)
    grouped["ended"].sort(key=lambda r: r.get("date", ""), reverse=True)

    def row_html(r: dict) -> str:
        _, m = match_info(r["title"], r.get("date", ""))
        result = (m or {}).get("result_inferred", "") if m else ""
        cls = status_of(r)
        # 开赛时间以 matches.json 官方登记为准（教训 2026-08-27：
        # watchlist 快照 22:00 vs Liquipedia 官方 22:30，页面曾显示错误时间）
        show_time = r.get("time", "") or r.get("date", "")
        if m and m.get("start_time"):
            show_time = fmt_time(m["start_time"]) or show_time
        badge = {
            "upcoming": '<span class="bd up">未开始</span>',
            "live": '<span class="bd live">进行中</span>',
            "ended": '<span class="bd end">已结束</span>',
        }[cls]
        link = intel_link(m, r["title"], r.get("date", ""), r.get("slug", ""))
        st = f'<span class="st">{badge}'
        if cls == "ended" and result:
            st += f'<span class="rs" title="{esc(result)}">{esc(result[:34])}</span>'
        elif cls == "ended":
            st += '<span class="rs">结果待回填</span>'
        st += market_link(r.get("slug", ""))  # 市场链接（带联盟后缀）
        if link:
            st += link
        st += "</span>"
        return (
            f'<div class="row {cls}" data-league="{esc(r["league"])}">'
            f'<span class="lg">{esc(r["league"])}</span>'
            f'<span class="tm">{esc(short_title(r["title"]))}</span>'
            f'<span class="dt">{esc(show_time)}</span>{st}</div>'
        )

    def group_html(key: str, label: str, items: list) -> str:
        if not items:
            return ""
        inner = "".join(row_html(r) for r in items)
        return f'<div class="grp" id="{key}"><h3>{label}</h3>{inner}</div>'

    sched = (
        f'<div class="chips">{chips}</div>'
        + group_html("upcoming", "未开始（重点关注）", grouped["upcoming"])
        + group_html("live", "进行中", grouped["live"])
        + group_html("ended", "已结束", grouped["ended"])
    )
    if not rows:
        sched = '<div class="row"><span class="tm">今日无已确认 Polymarket 电竞场次（空结果必须过自检，勿当无比赛）</span></div>'

    # 今日情报区：今天已产出情报的比赛（有情报页）
    detail_rows = ""
    today_md = [m for m in md_list if m.get("date") == args.date]
    for m in today_md:
        teams = m.get("teams", [])
        if len(teams) != 2:
            continue
        link = ""
        # 优先时间轴壳（2026-08-27：用户找不到局中入口——今日情报区曾直连
        # 赛前页，改为先进时间轴，可切换 BP/局中/局末节点）
        slug = m.get("event_slug") or m.get("slug") or ""
        if slug:
            shell = site_dir / "intel" / f"match_{slug}.html"
            if shell.exists():
                link = f'<a class="b" href="{esc(shell.name)}">情报 →</a>'
        for rep in m.get("reports", []) or []:
            name = str(rep).rsplit("/", 1)[-1]
            if (site_dir / "intel" / name).exists():
                link = link or f'<a class="b" href="{esc(name)}">情报页 →</a>'
                break
        if not link:
            continue
        result = m.get("result_inferred", "")
        detail_rows += (
            f'<div class="row"><span class="lg">{esc(m.get("league", "-"))}</span>'
            f'<span class="tm">{esc(" vs ".join(teams))}</span>'
            f'<span class="st">{link}</span></div>'
        )
    empty_detail = '<div class="row"><span class="tm">今日暂无已产出情报（比赛结束后自动生成）</span></div>'
    detail = (
        '<div class="card"><h2>今日情报</h2>'
        '<div class="sub">今日已产出情报的比赛（情报页完整复盘 / 局中快照）</div>'
        + (detail_rows or empty_detail) + '</div>'
    )

    tomorrow_rows = "".join(row_html(r) for r in rows_tomorrow)
    tomorrow_html = (
        f'<div class="card"><h2>明日预告</h2>'
        f'<div class="grp">{tomorrow_rows}</div>'
        f'<div class="note">明日重点比赛提前预告（以开赛当天自动页为准）</div></div>'
    ) if rows_tomorrow else ""
    body = f'<div class="card"><h2>赛程</h2>{sched}<div class="note">未开始 = 重点关注；进行中 = 可看实时情报；已结束 = 置灰 + 结果说明。关注联赛：LPL / LCK / LEC（英雄联盟）。</div></div>{tomorrow_html}{detail}'

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="今日比赛 · Polymarket 电竞白名单场次 · 弹幕情报库">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<title>今日比赛 · {args.date} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:26px 16px 60px}}
.wrap{{max-width:860px;margin:0 auto}}
nav{{position:sticky;top:0;z-index:10;background:rgba(245,245,247,.86);backdrop-filter:saturate(180%) blur(16px);border-bottom:1px solid var(--line);margin-bottom:22px}}
nav .inner{{display:flex;align-items:center;gap:16px;max-width:860px;margin:0 auto;padding:11px 16px;flex-wrap:wrap}}
nav a{{color:var(--sub);text-decoration:none;font-size:13px;font-weight:500}}
nav a:hover{{color:var(--accent)}}
nav .crumb{{color:var(--sub);font-size:12px}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px}}
.card h2{{font-size:16px;font-weight:800;margin-bottom:2px}}
.grp{{margin-top:10px}}
.grp h3{{font-size:12.5px;font-weight:700;color:var(--sub);margin:10px 0 2px}}
.row{{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px 2px;border-bottom:1px solid var(--line);font-size:13.5px}}
.row:last-child{{border-bottom:0}}
.row.ended{{opacity:.62}}
.row.ended .tm{{text-decoration:line-through}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.chip{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 13px;font-size:12px;font-weight:600;color:var(--sub);cursor:pointer}}
.chip[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
.lg{{font-size:11px;font-weight:700;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:2px 9px;flex:none}}
.tm{{font-weight:600}}
.dt{{color:var(--sub);font-size:12px;flex:none}}
.st{{display:flex;gap:8px;align-items:center;flex:none}}
.bd{{font-size:10.5px;font-weight:700;border-radius:999px;padding:2px 9px}}
.bd.up{{color:var(--accent);background:#e8f1fd}}
.bd.live{{color:#b45309;background:#fef3e2}}
.bd.end{{color:var(--sub);background:#f0f0f2}}
.rs{{color:var(--sub);font-size:11.5px;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.st .b{{color:var(--accent);text-decoration:none;font-size:12px;font-weight:600}}
.note{{color:var(--sub);font-size:12px;margin-top:10px}}
.st a{{color:var(--accent);text-decoration:none}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
@media(max-width:640px){{.row{{flex-wrap:wrap}} .dt{{order:3;width:100%}}}}
</style></head><body><div class="wrap">
<h1>今日比赛</h1>
<div class="sub">Polymarket 电竞白名单场次（近期扫描窗口）· {args.date} · 数据源：实时扫描 + 情报库 slug</div>
{body}
<footer>弹幕情报库 · 每日自动更新</footer>
<script>
(function () {{
  var chips = document.querySelectorAll(".chip");
  var rows = document.querySelectorAll(".row[data-league]");
  chips.forEach(function (c) {{
    c.addEventListener("click", function () {{
      chips.forEach(function (x) {{ x.setAttribute("aria-pressed", x === c ? "true" : "false"); }});
  var lg = c.getAttribute("data-lg");
  rows.forEach(function (r) {{
    var ok = (lg === "all" || r.getAttribute("data-league") === lg);
    r.style.display = ok ? "" : "none";
    var grp = r.closest(".grp");
    if (grp) {{
      var any = Array.prototype.some.call(grp.querySelectorAll(".row"), function (x) {{ return x.style.display !== "none"; }});
      grp.style.display = any ? "" : "none";
    }}
  }});
    }});
  }});
}})();
</script>
</div></body></html>"""

    site_dir = Path(args.site_dir)
    (site_dir / "intel").mkdir(parents=True, exist_ok=True)
    (site_dir / "intel" / "today.html").write_text(page, encoding="utf-8")
    print(f"wrote runtime/intel_today.json + {site_dir}/intel/today.html ({len(rows)} matches)")


if __name__ == "__main__":
    main()
