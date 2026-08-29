#!/usr/bin/env python3
"""Update homepage "#intel" stats block with live asset counts.

统计平台 / 直播间 / 比赛 / 选手 / 情报页 / 锚点信号等数据量，
写入 index.html 的 #intelStats 占位（每日流水线或手动运行）。
"""

from __future__ import annotations

import datetime
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / ".danmu_intel_site" / "index.html"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def count_json(path: Path, key: str | None = None) -> int:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        if key and isinstance(d, dict):
            d = d.get(key, [])
        if isinstance(d, list):
            return len(d)
        if isinstance(d, dict):
            return len(d.get("records", d.get("players", d.get("teams", []))))
    except (OSError, json.JSONDecodeError):
        pass
    return 0


def main() -> None:
    intel = ROOT / "docs" / "data" / "intel"
    registry = ROOT / "docs" / "data" / "danmu" / "streamer_registry.json"

    matches = count_json(intel / "matches.json", "matches")
    players = count_json(intel / "players.json", "players")
    teams = count_json(intel / "teams.json", "teams")
    bp = count_json(intel / "bp_signals.json", "records")
    md_count = len(list((ROOT / "knowledge" / "intel_pages").glob("*.md")))

    streamers = 0
    platforms: set[str] = set()
    if registry.exists():
        try:
            data = json.loads(registry.read_text(encoding="utf-8"))
            streamers = len(data.get("streamers", []))
            platforms = {s.get("platform", "") for s in data.get("streamers", []) if s.get("platform")}
        except (OSError, json.JSONDecodeError):
            pass

    stats = [
        (str(len(platforms)), "抓取平台（虎牙 / SOOP / Twitch / KICK）"),
        (str(streamers), "直播间实时采集"),
        (str(matches), "场比赛沉淀"),
        (f"{players} 选手 · {teams} 队伍", "画像资产"),
        (str(md_count), "情报页 / 画像文档"),
        (str(bp), "锚点信号（BP 战绩 / 正负锚）"),
    ]
    cards = "".join(
        f'<div class="stat"><div class="num">{esc(n)}</div><div class="lbl">{esc(l)}</div></div>'
        for n, l in stats
    )
    updated = datetime.date.today().isoformat()
    block = (
        f'{cards}'
        f'<div class="note" style="grid-column:1/-1;margin-top:2px">持续积累中：每场比赛结束自动新增情报页，'
        f'锚点应验 / 灰信号兑现公开可溯 · 数据更新至 {updated}</div>'
    )

    text = HOME.read_text(encoding="utf-8")
    new, n = __import__("re").subn(
        r'<div class="stats" id="intelStats">.*?</div>\s*<div class="links">',
        lambda _m: f'<div class="stats" id="intelStats">{block}</div><div class="links">',
        text,
        count=1,
        flags=__import__("re").S,
    )
    if not n:
        print("homepage #intelStats block not found")
        return
    HOME.write_text(new, encoding="utf-8")
    print(f"updated homepage intel stats ({len(platforms)} platforms, {streamers} streamers, {matches} matches, {md_count} docs)")


if __name__ == "__main__":
    main()
