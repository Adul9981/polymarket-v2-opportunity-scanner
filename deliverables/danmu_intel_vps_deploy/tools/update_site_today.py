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
    wl = Path(args.watchlist)
    if wl.exists():
        data = json.loads(wl.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("events", data.get("items", []))
        for e in items:
            d = str(e.get("startDate", e.get("start_date", e.get("date", ""))))[:10]
            slug = e.get("slug", "")
            m = re.search(r"-(\d{4}-\d{2}-\d{2})$", slug)
            if not d and m:
                d = m.group(1)
            if slug and (d == args.date or (m and m.group(1) <= args.date)):
                start = e.get("start_time") or e.get("startDate") or e.get("start_date") or ""
                title = e.get("title", e.get("name", "-"))
                lg = league_of(title)
                if lg == "LCS":
                    continue  # 用户指定：英雄联盟只看 LCK / LPL / LEC，不要 LCS
                rows.append(
                    {
                        "league": lg,
                        "title": title,
                        "slug": slug,
                        "date": d,
                        "time": fmt_time(start),
                        "status": e.get("time_status", ""),
                    }
                )
    mj = Path(args.matches_json)
    if mj.exists():
        md = json.loads(mj.read_text(encoding="utf-8"))
        for m in md.get("matches", []):
            if m.get("date") == args.date and m.get("event_slug"):
                rows.append(
                    {
                        "league": m.get("league", "-"),
                        "title": " vs ".join(m.get("teams", [])) or m.get("id"),
                        "slug": m["event_slug"],
                        "date": args.date,
                        "time": "",
                        "status": "",
                    }
                )
    rows.sort(key=lambda r: r["title"])

    out_json = Path("runtime/intel_today.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"date": args.date, "matches": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    leagues = sorted({r["league"] for r in rows if r["league"] != "-"})
    chips = '<button class="chip" aria-pressed="true" data-lg="all">全部</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-lg="{esc(l)}">{esc(l)}</button>' for l in leagues
    )
    body = f'<div class="chips">{chips}</div>'
    if rows:
        for r in rows:
            body += (
                f'<div class="row" data-league="{esc(r["league"])}"><span class="lg">{esc(r["league"])}</span>'
                f'<span class="tm">{esc(r["title"])}</span>'
                f'<span class="dt">{esc(r.get("date", ""))} {esc(r.get("time", ""))}</span>'
                f'<span class="st">{esc(r.get("status", ""))}</span></div>'
            )
    else:
        body = '<div class="row"><span class="tm">今日无已确认 Polymarket 电竞场次（空结果必须过自检，勿当无比赛）</span></div>'
    body += '<div class="note">关注联赛：LPL / LCK / LEC（英雄联盟）；比赛情报入口见「弹幕情报索引」——先看情报页，市场链接在情报页内。</div>'

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="今日比赛 · Polymarket 电竞白名单场次 · 弹幕情报库">
<title>今日比赛 · {args.date} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:26px 16px 60px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px}}
.row{{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px 2px;border-bottom:1px solid var(--line);font-size:13.5px}}
.row:last-child{{border-bottom:0}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.chip{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 13px;font-size:12px;font-weight:600;color:var(--sub);cursor:pointer}}
.chip[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
.lg{{font-size:11px;font-weight:700;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:2px 9px;flex:none}}
.tm{{font-weight:600}}
.dt{{color:var(--sub);font-size:12px;flex:none}}
.note{{color:var(--sub);font-size:12px;margin-top:10px}}
.st a{{color:var(--accent);text-decoration:none}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>今日比赛（自动生成）</h1>
<div class="sub">Polymarket 电竞白名单场次（近期扫描窗口）· {args.date} · 数据源：实时扫描 + 情报库 slug</div>
<div class="card">{body}</div>
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
        r.style.display = (lg === "all" || r.getAttribute("data-league") === lg) ? "" : "none";
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
