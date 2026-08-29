#!/usr/bin/env python3
"""VPS self-check: auto-detect and repair data-integrity issues.

机制（2026-08-25 建立，防重复错误）：
  1) 节点完整性：扫描"已产出完整复盘(full)但缺赛前/局中节点"的比赛，
     自动触发回补（vps_backfill_nodes，后台跑、防并发）；
  2) 状态一致性：full 存在但状态文件缺失的比赛 -> 重建状态（视为已结束）；
  3) 输出自检报告（runtime/vps_intel/self_check_report.json）。
由 vps-intel-pipeline.service 在每次流水线后运行。
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
from pathlib import Path

import vps_intel_pipeline as V


def has_nodes(teams: list[str], date: str, max_games: int = 3) -> bool:
    """节点完整性：赛前 + 每局 bp/mid/end + 整场（2026-08-27 升级：
    此前只查 pre/live，昨晚 FURIA/NAVI G3 缺节点未被检测）。"""
    stem = f"intel_danmu_{teams[0]}-{teams[1]}_{date}"
    if (V.REPORTS / f"{stem}_pre.html").exists() or bool(list(V.REPORTS.glob(f"{stem}_live_*.html"))):
        pass
    found = {"pre": (V.REPORTS / f"{stem}_pre.html").exists()}
    for gi in range(1, max_games + 1):
        for ph in ("bp", "mid", "end"):
            found[f"g{gi}_{ph}"] = (V.REPORTS / f"{stem}_g{gi}_{ph}.html").exists()
    # 兼容每局一页命名（_G1/_G2/...）与整场无后缀
    for gi in range(1, max_games + 1):
        found.setdefault(f"g{gi}_game", (V.REPORTS / f"{stem}_G{gi}.html").exists())
    found["full"] = (V.REPORTS / f"{stem}.html").exists() or (V.REPORTS / f"{stem}_full.html").exists()
    return found


def backfill_running() -> bool:
    out = subprocess.run(["pgrep", "-f", "vps_backfill_nodes"], capture_output=True, text=True).stdout
    return bool(out.strip())


def main() -> None:
    report = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "backfill_needed": [], "backfill_skipped": [], "state_repaired": [],
              "site_audit": [], "warnings": []}
    if not V.MATCHES.exists():
        print("[self_check] no matches_today.json")
        return
    matches = json.loads(V.MATCHES.read_text(encoding="utf-8")).get("matches", [])
    for m in matches:
        mid = m.get("id") or ""
        st = V.STATE_DIR / f"{mid}.json"
        teams = m.get("teams", [])
        if len(teams) != 2 or not st.exists():
            continue
        date = (m.get("start_time") or "")[:10]
        # 1) 节点完整性：已结束/有整场的比赛，节点必须齐全（赛前+各局 bp/mid/end）
        nodes = has_nodes(teams, date, V.format_of(m) if hasattr(V, "format_of") else 3)
        full_exists = nodes.pop("full", False)
        pre_exists = nodes.pop("pre", False)
        # 每局一页（_G1/_G2）已存在时，不再要求该局 bp/mid/end 三段式
        for gi in range(1, V.format_of(m) + 1 if hasattr(V, "format_of") else 4):
            if nodes.get(f"g{gi}_game"):
                for ph in ("bp", "mid", "end"):
                    nodes.pop(f"g{gi}_{ph}", None)
        missing = [k for k, v in nodes.items() if not v]
        ended = full_exists or st.exists()
        if ended and missing:
            report["warnings"].append(
                f"{mid}: 已结束但缺节点 {','.join(missing)}（含赛前={'Y' if pre_exists else 'N'}）"
            )
        if ended and (missing or not pre_exists):
            if backfill_running():
                report["backfill_skipped"].append(mid)
            elif not report["backfill_needed"]:  # 每轮只回补一场，防积压过载
                report["backfill_needed"].append(mid)
                subprocess.Popen(
                    [str(V.PY), str(V.ROOT / "tools" / "vps_backfill_nodes.py"), "--match", mid],
                    cwd=str(V.ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                report["backfill_skipped"].append(mid)
    # 2) 状态一致性：full 存在但状态文件缺失 -> 重建状态（已结束）
    for m in matches:
        mid = m.get("id") or ""
        st = V.STATE_DIR / f"{mid}.json"
        teams = m.get("teams", [])
        if len(teams) != 2 or st.exists():
            continue
        date = (m.get("start_time") or "")[:10]
        full = V.REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}.html"
        if full.exists():
            st.write_text(json.dumps({"match": mid, "verified": True,
                                      "note": "self_check 重建状态（full 已存在）",
                                      "generated_at": report["ts"]}, ensure_ascii=False, indent=2),
                          encoding="utf-8")
            report["state_repaired"].append(mid)
    # 3) 站点结构审计：发布通道（site_repo）每 5 分钟查一次，
    #    导航/今日页/付费墙异常即时可见（今日情报页 = 头号防错对象）
    repo = V.ROOT / "site_repo"
    if repo.exists():
        pro_re = re.compile(r"intel_danmu_.*_(pre|live|bp|g[1-9])(?:[_.].*)?\.html$", re.I)
        for p in repo.rglob("*.html"):
            rel = str(p.relative_to(repo))
            t = p.read_text(encoding="utf-8", errors="ignore")
            n = len(re.findall(r"<nav[^>]*>", t))
            if n != 1:
                report["site_audit"].append(f"{rel}: nav={n}")
            if rel == "intel/today.html" and 'class="inner"' in t:
                report["site_audit"].append(f"{rel}: 旧模板导航残留")
            if t.count('location.search.indexOf("embed=1")') > 1:
                report["site_audit"].append(f"{rel}: embed>1")
            if pro_re.search(p.name) and "danmu_member_v1" not in t:
                report["site_audit"].append(f"{rel}: 缺付费墙")
    V.STATE_DIR.mkdir(parents=True, exist_ok=True)
    (V.STATE_DIR / "self_check_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[self_check] backfill_needed={len(report['backfill_needed'])} "
          f"skipped={len(report['backfill_skipped'])} repaired={len(report['state_repaired'])} "
          f"site_issues={len(report['site_audit'])}")


if __name__ == "__main__":
    main()
