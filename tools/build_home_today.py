#!/usr/bin/env python3
"""Update homepage "#today" block with today's key LoL matches.

读取 runtime/intel_today.json（update_site_today.py 产出），提取今日
LPL / LCK / LEC 未开始 + 进行中的比赛（按时间升序取前 5），生成首页
"今日比赛"区块（关键 LoL 摘要 + 情报详情），并保留完整赛程入口。
"""

from __future__ import annotations

import datetime
import html
import json
import re
from pathlib import Path

from match_status import match_status

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / ".danmu_intel_site" / "index.html"
TODAY_JSON = ROOT / "runtime" / "intel_today.json"
MATCHES_JSON = ROOT / "docs" / "data" / "intel" / "matches.json"

# 2026-08-27：首页今日区块覆盖所有联赛（含 CS2），并显示已结束状态
ALL_LEAGUES = ("LPL", "LCK", "LEC", "CS2", "LCK CL", "LCP", "LoL")


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def short_title(title: str) -> str:
    m = re.search(r":\s*(.+?)\s*-\s*", title or "")
    return (m.group(1).strip() if m else title).strip()


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default=".danmu_intel_site",
                    help="site repo dir（VPS 上传 site_repo）")
    args = ap.parse_args()
    site_dir = Path(args.site_dir)
    home = ROOT / site_dir / "index.html"
    if not TODAY_JSON.exists():
        print("no runtime/intel_today.json (run update_site_today.py first)")
        return
    data = json.loads(TODAY_JSON.read_text(encoding="utf-8"))
    rows = data.get("matches", [])
    date = data.get("date", "")

    # 状态：upcoming / live / ended（与 update_site_today 一致）
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

    def parse_dt(iso: str):
        if not iso:
            return None
        try:
            return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(
                datetime.timezone(datetime.timedelta(hours=8))
            )
        except ValueError:
            return None

    def status_of(r: dict) -> str:
        return match_status(
            r.get("start_raw", ""), r.get("end_raw", ""), r.get("status", ""),
            r.get("title", ""), r.get("date", ""), now, ROOT / site_dir / "intel",
        )

    focus = [r for r in rows if r.get("league") in ALL_LEAGUES]
    focus.sort(key=lambda r: parse_dt(r.get("start_raw")) or datetime.datetime.max.replace(
        tzinfo=datetime.timezone.utc))
    focus = focus[:8]

    mrows = ""
    if focus:
        for r in focus:
            st = status_of(r)
            badge = {"upcoming": "未开始", "live": "进行中", "ended": "已结束"}.get(st, st)
            mrows += (
                f'<div class="mrow" style="cursor:default"><span class="lg">{esc(r["league"])}</span>'
                f'<span class="tm">{esc(short_title(r["title"]))}</span>'
                f'<span class="st">{esc(r.get("time", ""))} · {badge}</span></div>'
            )
    else:
        mrows = '<div class="mrow" style="cursor:default"><span class="lg">-</span><span class="tm">今日暂无已确认场次</span><span class="st"></span></div>'
    mrows += '<a class="mrow" href="intel/today.html"><span class="lg">全部</span><span class="tm">今日完整赛程与情报</span><span class="st">情报 →</span></a>'

    # 情报详情：今天已产出情报的比赛
    detail_rows = ""
    if MATCHES_JSON.exists():
        md = json.loads(MATCHES_JSON.read_text(encoding="utf-8")).get("matches", [])
        site_intel = ROOT / site_dir / "intel"
        for m in md:
            teams = m.get("teams", [])
            if len(teams) != 2 or m.get("date") != date:
                continue
            link = ""
            for rep in m.get("reports", []) or []:
                name = str(rep).rsplit("/", 1)[-1]
                if (site_intel / name).exists():
                    link = f'<a class="st" href="intel/{esc(name)}" style="color:var(--accent);text-decoration:none;font-weight:600">情报 →</a>'
                    break
            if not link:
                continue
            detail_rows += (
                f'<a class="mrow" href="intel/{esc(name)}"><span class="lg">{esc(m.get("league", "-"))}</span>'
                f'<span class="tm">{esc(" vs ".join(teams))}</span><span class="st">查看 →</span></a>'
            )
    if not detail_rows:
        detail_rows = '<div class="mrow" style="cursor:default"><span class="lg">情报</span><span class="tm" style="color:var(--sub)">今日暂无已产出情报（比赛结束后自动生成）</span><span class="st"></span></div>'

    block = (
        f'<section class="block" id="today">'
        f'<h2>今日比赛</h2>'
        f'<p class="sub">今日比赛（LCK / LPL / LEC / CS2）· 完整赛程与详情见自动页</p>'
        f'<div class="card"><div class="mrows">{mrows}</div></div>'
        f'<div class="card"><div class="mrows">{detail_rows}</div></div>'
        f"</section>"
    )

    text = home.read_text(encoding="utf-8")
    new, n = re.subn(
        r'<section class="block" id="today">.*?</section>',
        lambda _m: block,
        text,
        count=1,
        flags=re.S,
    )
    if not n:
        print("homepage #today block not found")
        return
    home.write_text(new, encoding="utf-8")
    print(f"updated homepage #today ({len(focus)} matches, date={date})")


if __name__ == "__main__":
    main()
