#!/usr/bin/env python3
"""Build the teams/players/leagues profile quick-reference page.

Scans site intel/ for intel_profile_team_*.html / _player_* / _league_* and
emits <site>/intel/profiles.html grouped by type.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def label(name: str) -> str:
    return name.replace("_", " ").title()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default=".danmu_intel_site")
    args = ap.parse_args()
    intel = Path(args.site_dir) / "intel"

    groups = [
        ("队伍画像", "team"),
        ("选手画像", "player"),
        ("联赛画像", "league"),
    ]
    sections = ""
    total = 0
    for title, kind in groups:
        files = sorted(intel.glob(f"intel_profile_{kind}_*.html"))
        if not files:
            continue
        total += len(files)
        rows = "".join(
            f'<div class="row"><span class="tm">{esc(label(f.name[len("intel_profile_" + kind + "_"):-5]))}</span>'
            f'<span class="st"><a href="{esc(f.name)}">画像 →</a></span></div>'
            for f in files
        )
        sections += f'<div class="card"><h2>{title}（{len(files)}）</h2>{rows}</div>'

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="队伍 / 选手 / 联赛画像速查 · 弹幕情报库">
<title>画像速查 · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 56px}}
.wrap{{max-width:880px;margin:0 auto}}
h1{{font-size:23px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 18px;margin-bottom:14px}}
.card h2{{font-size:14px;font-weight:800;margin-bottom:6px}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:7px 2px;border-bottom:1px solid var(--line);font-size:13px}}
.row:last-child{{border-bottom:0}}
.st a{{color:var(--accent);text-decoration:none;font-weight:600}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>画像速查</h1>
<div class="sub">队伍 / 选手 / 联赛画像 · 跨场长期资产 · 共 {total} 个</div>
{sections or '<div class="card">暂无画像</div>'}
<footer>弹幕情报库 · 画像速查 · 2026-08-24</footer>
</div></body></html>"""
    out = intel / "profiles.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({total} profiles)")


if __name__ == "__main__":
    main()
