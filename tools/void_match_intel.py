#!/usr/bin/env python3
"""作废某场比赛的情报数据（2026-08-26 用户定稿：数据错误/混源即整场作废）。

用途：Aurora vs G2（cs2-aur1-g2-2026-08-26）因 LoL 弹幕混入 CS 板块，
全部情报作废。本脚本：
  1) 删除该场所有节点页（reports + site + git rm）；
  2) 删除比赛时间轴壳；
  3) matches.json 标记 intel_voided + 原因；
  4) 移除 teams.json 中该场沉淀标签；
  5) 写入 accumulated_matches 防再沉淀。

用法（服务器）：/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/void_match_intel.py <slug>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/danmu-intel/site_repo")
REPORTS = Path("/opt/danmu-intel/reports")


def main() -> int:
    if len(sys.argv) < 2:
        print("need slug")
        return 1
    slug = sys.argv[1]
    os.environ["GIT_SSH_COMMAND"] = (
        "ssh -i /root/.ssh/github_deploy -o StrictHostKeyChecking=accept-new"
    )
    # 1) 删除节点页（含 pre / g* / live / 整场）
    removed = []
    for base in (REPORTS, REPO / "intel"):
        for p in base.glob("intel_danmu_*2026-08-26*.html"):
            pass  # 用 slug 内文件更精确，下面按比赛时间轴壳/节点匹配
    # 按比赛对局关系删除：取该 slug 关联的 intel_danmu 页（通过 match 壳定位）
    shell = REPORTS / f"match_{slug}.html"
    match_pages: set[str] = set()
    if shell.exists():
        import re
        txt = shell.read_text(encoding="utf-8", errors="ignore")
        match_pages = set(re.findall(r'data-src="([^"]+)"', txt))
    for fname in match_pages:
        for base in (REPORTS, REPO / "intel"):
            p = base / fname
            if p.exists():
                try:
                    rel = p.relative_to(REPO)
                    subprocess.run(["git", "-C", str(REPO), "rm", "-q", str(rel)],
                                   capture_output=True, text=True)
                except ValueError:
                    pass
                p.unlink(missing_ok=True)
                md = p.with_suffix(".md")
                if md.exists():
                    try:
                        rel = md.relative_to(REPO)
                        subprocess.run(["git", "-C", str(REPO), "rm", "-q", str(rel)],
                                       capture_output=True, text=True)
                    except ValueError:
                        pass
                    md.unlink(missing_ok=True)
                removed.append(p.name)
    # 2) 删除时间轴壳
    for base in (REPORTS, REPO / "intel"):
        p = base / f"match_{slug}.html"
        if p.exists():
            try:
                rel = p.relative_to(REPO)
                subprocess.run(["git", "-C", str(REPO), "rm", "-q", str(rel)],
                               capture_output=True, text=True)
            except ValueError:
                pass
            p.unlink(missing_ok=True)
    # 3) matches.json 标记作废
    mj = Path("/opt/danmu-intel/docs/data/intel/matches.json")
    md = json.loads(mj.read_text(encoding="utf-8"))
    for m in md.get("matches", []):
        if (m.get("slug") or m.get("id")) == slug:
            m["intel_voided"] = True
            m["intel_voided_note"] = "LoL 弹幕混入 CS 板块（切片未按联赛过滤源），整场情报作废 2026-08-26"
    mj.write_text(json.dumps(md, ensure_ascii=False, indent=1), encoding="utf-8")
    # 4) teams.json 移除该场沉淀标签（含 "vs Aurora"/"vs G2" 且日期 2026-08-26）
    tj = Path("/opt/danmu-intel/docs/data/intel/teams.json")
    td = json.loads(tj.read_text(encoding="utf-8"))
    for t in td.get("teams", []):
        tags = (t.get("danmu") or {}).get("tags")
        if tags:
            t["danmu"]["tags"] = [
                x for x in tags
                if not ("2026-08-26 vs" in x and ("Aurora" in x or "G2" in x))
            ]
    tj.write_text(json.dumps(td, ensure_ascii=False, indent=1), encoding="utf-8")
    # 5) 防再沉淀
    mk = Path("/opt/danmu-intel/runtime/accumulated_matches.json")
    marker = json.loads(mk.read_text(encoding="utf-8"))
    acc = set(marker.get("accumulated", []))
    acc.add(slug)
    marker["accumulated"] = sorted(acc)
    mk.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, text=True)
    r = subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-m", f"作废 {slug} 情报（混源）"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"],
                       capture_output=True, text=True)
    print("voided:", slug, "| removed pages:", len(removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
