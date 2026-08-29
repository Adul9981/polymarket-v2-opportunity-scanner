#!/usr/bin/env python3
"""Rebuild all match timeline shells in REPORTS (server side).

在导航/壳模板升级后运行，按现有壳提取对阵与日期，用最新
build_timeline_shell 重建（幂等，无节点文件则跳过）。

用法：
  python3 tools/rebuild_shells.py [--reports DIR]
  python3 tools/rebuild_shells.py --legacy-site <site_intel_dir>
    # 兼容本地遗留"两级选择"壳：site_repo 里有、REPORTS 没有的 match_*.html，
    # 用统一时间轴壳重建（教训 2026-08-25：遗留壳节点按钮 __none__/同一份）。
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=None)
    ap.add_argument("--legacy-site", default=None)
    args = ap.parse_args()
    root = Path("/opt/danmu-intel")
    reports = Path(args.reports) if args.reports else root / "reports"
    spec = importlib.util.spec_from_file_location(
        "vps_intel_pipeline", root / "tools" / "vps_intel_pipeline.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["vps_intel_pipeline"] = m
    spec.loader.exec_module(m)

    def rebuild(shell: Path) -> bool:
        mid = shell.name[len("match_") : -len(".html")]
        text = shell.read_text(encoding="utf-8")
        h1 = re.search(r"<h1>(.*?) vs (.*?)</h1>", text)
        sub = re.search(r'<div class="sub">([^·]*) · ([0-9-]+) ·', text)
        if not h1 or not sub:
            return False
        a, b = h1.group(1).strip(), h1.group(2).strip()
        league, date = sub.group(1).strip(), sub.group(2).strip()
        out = m.build_timeline_shell(mid, [a, b], league, date)
        if not out.exists():
            print(f"skip {mid}: 无节点文件（保留原壳）", flush=True)
            return False
        views = len(re.findall(r'class="nbtn"', out.read_text(encoding="utf-8")))
        print(f"rebuild {mid} views={views}", flush=True)
        return True

    n = 0
    for shell in sorted(reports.glob("match_*.html")):
        if rebuild(shell):
            n += 1
    if args.legacy_site:
        for shell in sorted(Path(args.legacy_site).glob("match_*.html")):
            if (reports / shell.name).exists():
                continue
            if rebuild(shell):
                n += 1
    print(f"total shells rebuilt: {n}", flush=True)


if __name__ == "__main__":
    main()
