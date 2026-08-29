#!/usr/bin/env python3
"""队伍情报库自动沉淀闭环（2026-08-26 用户定稿）。

每场比赛结算（matches.json result_inferred）后，自动把该场各节点弹幕统计
合并进 teams.json + TEAM_PROFILES.md，实现"每场 -> 队伍画像"闭环。

用法：
  python3 tools/accumulate_team_intel.py --root /opt/danmu-intel
  python3 tools/accumulate_team_intel.py --root /Users/ad/Documents/polymarket --match lol-kt-bro2-2026-08-26 --stats
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load(root: Path, rel: str):
    p = root / rel
    if not p.exists():
        return {} if rel.endswith(".json") else ""
    if rel.endswith(".json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return p.read_text(encoding="utf-8")


def save(root: Path, rel: str, data) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def team_id(team_names: dict, name: str) -> str:
    low = name.lower()
    for t in team_names.get("teams", []):
        if low in {str(t.get("abbr", "")).lower(), str(t.get("full", "")).lower()}:
            return str(t["id"])
        for a in t.get("aliases", []):
            if low == str(a).lower():
                return str(t["id"])
    return re.sub(r"[^a-z0-9]", "", low)


def aggregate_match(root: Path, slug: str, teams: list[str], date: str) -> dict:
    """汇总该场所有节点 intel JSON 的弹幕统计（本场弹幕来源）。"""
    out = {}
    for f in sorted((root / "runtime" / "vps_intel").glob(f"{slug}_g*_intel.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        meta = d.get("meta", {})
        for t, v in (d.get("teams") or {}).items():
            acc = out.setdefault(t, {"mentions": 0, "pos": 0, "neg": 0, "nodes": 0})
            acc["mentions"] += int(v.get("mentions", 0))
            acc["pos"] += int(v.get("pos", 0))
            acc["neg"] += int(v.get("neg", 0))
            acc["nodes"] += 1
    return out


def stats_from_lib(root: Path) -> dict:
    """跨场兑现率统计（灰信号/BP 锚点）。"""
    gray = load(root, "docs/data/intel/gray_signals.json").get("records", [])
    g = {"confirmed": 0, "refuted": 0, "partial": 0, "pending": 0}
    for r in gray:
        st = str(r.get("verification") or r.get("status") or "")
        if st in g:
            g[st] += 1
    gtot = g["confirmed"] + g["refuted"]
    bp = load(root, "docs/data/intel/bp_signals.json").get("records", [])
    b = {"hit": 0, "miss": 0}
    for r in bp:
        v = str(r.get("verdict") or "")
        if any(k in v for k in ("应验", "命中", "兑现", "hit", "yes")):
            b["hit"] += 1
        elif any(k in v for k in ("未应验", "未命中", "未兑现", "miss", "no")):
            b["miss"] += 1
    btot = b["hit"] + b["miss"]
    return {
        "gray": {"count": len(gray), **g, "rate": round(g["confirmed"] / gtot, 3) if gtot else None},
        "bp": {"count": len(bp), **b, "rate": round(b["hit"] / btot, 3) if btot else None},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/Users/ad/Documents/polymarket")
    ap.add_argument("--match", default="")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)

    if args.stats:
        print(json.dumps(stats_from_lib(root), ensure_ascii=False, indent=1))
        return 0

    matches = load(root, "docs/data/intel/matches.json").get("matches", [])
    team_names = load(root, "docs/data/intel/team_names.json")
    teams_lib = load(root, "docs/data/intel/teams.json")
    by_id = {t["id"]: t for t in teams_lib.get("teams", [])}
    marker = load(root, "runtime/accumulated_matches.json")
    done = set(marker.get("accumulated", [])) if isinstance(marker, dict) else set()
    profiles = load(root, "knowledge/TEAM_PROFILES.md")
    today = "2026-08-26"

    changed = []
    for m in matches:
        slug = m.get("slug") or m.get("id") or ""
        result = m.get("result_inferred") or ""
        teams = m.get("teams") or []
        if args.match and slug != args.match:
            continue
        if not result or len(teams) != 2 or slug in done:
            continue
        stats = aggregate_match(root, slug, teams, m.get("date", ""))
        if not stats:
            continue
        # 队伍命名兜底：team_names 缺失时，按已有画像条目名做包含匹配
        # （教训 2026-08-26：Aurora 未登记 -> 误建 "auroragaming" 假条目）
        lib_names = {str(t.get("name", "")).lower(): t["id"] for t in by_id.values()}
        sections = []
        for t in teams:
            tid = team_id(team_names, t)
            low_name = t.lower()
            if tid not in by_id:
                for nm, nm_id in lib_names.items():
                    if low_name in nm or nm in low_name:
                        tid = nm_id
                        break
            acc = stats.get(t, {})
            entry = by_id.setdefault(
                tid,
                {"id": tid, "name": t, "league": m.get("league", ""), "danmu": {}, "market": {}, "updated": today},
            )
            danmu = entry.setdefault("danmu", {})
            danmu["mentions_total"] = danmu.get("mentions_total", 0) + int(acc.get("mentions", 0))
            tag = f"{m.get('date','')} vs {teams[1] if t==teams[0] else teams[0]}：{result[:30]}"
            tags = danmu.setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
            danmu.setdefault("samples", [])
            entry["updated"] = today
            sections.append(
                f"### {t}（{tid}）\n\n```text\n{m.get('date','')} 系列：{result}\n"
                f"本场弹幕统计：提及 {acc.get('mentions',0)}（正 {acc.get('pos',0)} / 负 {acc.get('neg',0)}），"
                f"{acc.get('nodes',0)} 个节点\n来源：本场弹幕 + 结算仲裁\n```\n"
            )
        profiles += "\n## 自动沉淀 · " + str(m.get("date", "")) + "\n\n" + "\n".join(sections)
        done.add(slug)
        changed.append(slug)

    if changed:
        teams_lib["updated_at"] = today
        save(root, "docs/data/intel/teams.json", teams_lib)
        save(root, "knowledge/TEAM_PROFILES.md", profiles)
        save(root, "runtime/accumulated_matches.json", {"accumulated": sorted(done)})
        print("accumulated:", changed)
    else:
        print("nothing to accumulate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
