#!/usr/bin/env python3
"""Publish danmaku intel pages to the danmu-intel site + regenerate index.

Syncs reports/intel_danmu_*.html, intel_profile_*.html and intel_gray_*.html
into <site>/intel/, then regenerates <site>/intel/index.html (auto index
grouped by date) and git add/commit/push.

Usage:
  python3 tools/publish_intel_pages.py [--site-dir .danmu_intel_site] [--push]
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from add_site_nav import inject_all  # noqa: E402
import add_favicon  # noqa: E402


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def guess_league(name: str) -> str:
    if "lol" in name or "LPL" in name or "LCK" in name or "LEC" in name:
        return "LoL"
    if "cs2" in name or "CS" in name:
        return "CS2"
    if "dota" in name:
        return "Dota2"
    return "-"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default="reports")
    ap.add_argument("--site-dir", default=".danmu_intel_site")
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()

    site = Path(args.site_dir)
    intel_dir = site / "intel"
    intel_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for pattern in ("intel_danmu_*.html", "intel_soop_*.html", "intel_profile_*.html", "intel_gray_*.html"):
        for f in Path(args.reports).glob(pattern):
            shutil.copy2(f, intel_dir / f.name)
            copied.append(f.name)

    match_files = sorted(intel_dir.glob("intel_danmu_*.html"), reverse=True)
    shell_files = sorted(intel_dir.glob("match_*.html"))
    profile_files = sorted(intel_dir.glob("intel_profile_*.html"))
    gray_files = sorted(intel_dir.glob("intel_gray_*.html"))

    by_date: dict[str, list[str]] = {}
    for f in match_files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
        date = m.group(1) if m else "未知日期"
        by_date.setdefault(date, []).append(f.name)

    rows = ""
    for date in sorted(by_date, reverse=True):
        rows += f'<h3 style="margin:14px 0 6px;font-size:13px;color:#6e6e73">{date}</h3>'
        for name in sorted(by_date[date]):
            label = re.sub(r"intel_danmu_|_\d{4}-\d{2}-\d{2}\.html", " ", name).replace("-", " vs ").strip()
            rows += (
                f'<div class="row"><span class="lg">{esc(guess_league(name))}</span>'
                f'<span class="tm">{esc(label)}</span>'
                f'<span class="st"><a href="{esc(name)}">情报页 →</a></span></div>'
            )
    if not rows:
        rows = '<div class="row"><span class="tm">暂无情报页（等比赛输出）</span></div>'

    shells = "".join(
        f'<div class="row"><span class="lg">详情</span>'
        f'<span class="tm">{esc(s.name.replace("match_", "").replace(".html", ""))}</span>'
        f'<span class="st"><a href="{esc(s.name)}">时间轴壳 →</a></span></div>'
        for s in shell_files
    )
    if not shells:
        shells = '<div class="row"><span class="tm">暂无详情壳</span></div>'

    profiles = "".join(
        f'<div class="row"><span class="tm">{esc(p.name.replace("intel_profile_", "").replace(".html", ""))}</span>'
        f'<span class="st"><a href="{esc(p.name)}">画像 →</a></span></div>'
        for p in profile_files[:20]
    )
    gray = "".join(
        f'<div class="row"><span class="tm">{esc(g.name.replace(".html", ""))}</span>'
        f'<span class="st"><a href="{esc(g.name)}">统计 →</a></span></div>'
        for g in gray_files
    )

    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<title>弹幕情报索引（自动生成）· Danmu Intel</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:26px 16px 60px}}
.wrap{{max-width:880px;margin:0 auto}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:14px}}
.row{{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:8px 2px;border-bottom:1px solid var(--line);font-size:13px}}
.row:last-child{{border-bottom:0}}
.lg{{font-size:11px;font-weight:700;color:var(--accent);background:#e8f1fd;border-radius:999px;padding:2px 8px;flex:none}}
.tm{{font-weight:600}}
.st a{{color:var(--accent);text-decoration:none}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>弹幕情报索引</h1>
<div class="sub">自动生成 · 比赛情报页 + 画像页 + 灰信号统计 · 最新在前</div>
<div class="card">{rows}</div>
<div class="card"><h3 style="font-size:14px;margin-bottom:6px">比赛详情（时间轴壳）</h3>{shells}</div>
<div class="card"><h3 style="font-size:14px;margin-bottom:6px">队伍 / 选手画像</h3>{profiles or '<div class="row"><span class="tm">暂无画像页</span></div>'}</div>
<div class="card"><h3 style="font-size:14px;margin-bottom:6px">灰信号统计</h3>{gray or '<div class="row"><span class="tm">暂无统计页</span></div>'}</div>
<footer>弹幕情报库 · 自动索引 · 2026-08-23</footer>
</div></body></html>"""

    (intel_dir / "index.html").write_text(page, encoding="utf-8")
    print(f"synced {len(copied)} pages; index rows {len(match_files)} match / {len(profile_files)} profile / {len(gray_files)} gray")

    # 注入与 git 解耦：nav/favicon 注入总是执行（2026-08-26 修复：
    # 此前只在 --push 时注入，导致不带 --push 的同步页面缺导航/图标）
    injected = inject_all(site)
    fav_injected = add_favicon.inject_all(site)
    print(f"nav injected into {injected} pages; favicon into {fav_injected} pages")

    if args.push:
        subprocess.run(["git", "-C", str(site), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(site), "commit", "-m", "sync danmaku intel pages + auto index", "-q"], check=True)
        subprocess.run(["git", "-C", str(site), "push", "-q"], check=True)
        print("pushed to danmu-intel")


if __name__ == "__main__":
    main()
