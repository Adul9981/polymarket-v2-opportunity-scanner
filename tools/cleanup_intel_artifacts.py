#!/usr/bin/env python3
"""情报中间产物清理 + 核心情报库保护备份（2026-08-26 建立）。

原则：**核心价值 = docs/data/intel/*.json 结构化情报库**，永不清理、每日快照备份；
只清理可再生中间产物：intel_slices（每节点切片，完成即弃）、旧日志。

用法：
  python3 tools/cleanup_intel_artifacts.py --dry-run   # 只看会删什么
  python3 tools/cleanup_intel_artifacts.py             # 实际执行
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/opt/danmu-intel")
SLICES = ROOT / "data" / "intel_slices"
STATE = ROOT / "runtime" / "vps_intel"
LOGS = ROOT / "logs"
INTEL_LIB = ROOT / "docs" / "data" / "intel"
BACKUP = ROOT / "runtime" / "intel_lib_backup"
SLICE_MAX_AGE_DAYS = 2  # 切片保留天数（完成后只留 2 天兜底）


def series_done(mid: str) -> bool:
    return (STATE / f"{mid}.json").exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    freed = 0
    removed = 0
    if SLICES.exists():
        for f in sorted(SLICES.iterdir()):
            if not f.is_file():
                continue
            name = f.name
            # 从文件名提取比赛 id（去掉 _gN_bp/_live_XXXX 等后缀）
            import re
            m = re.match(r"(.+?)(?:_g\d+_(?:bp|mid|end)|_pre|_live(?:_\d{4})?|_full)?\.jsonl$", name)
            mid = m.group(1) if m else name[:-6]
            mtime = datetime.date.fromtimestamp(f.stat().st_mtime)
            age = (datetime.date.today() - mtime).days
            keep = (not series_done(mid)) and age <= SLICE_MAX_AGE_DAYS
            # 今天/明天比赛保留（进行中可能继续切片）
            keep = keep or name.startswith(today) or any(
                d in name for d in ("-2026-08-26", "-2026-08-27")
            )
            if not keep:
                size = f.stat().st_size
                if args.dry_run:
                    print(f"[dry-run] 删 {name} ({size/1e6:.1f}MB)")
                else:
                    f.unlink()
                    print(f"[clean] 删 {name} ({size/1e6:.1f}MB)")
                freed += size
                removed += 1

    # 核心情报库每日快照（保护沉淀，保留 7 天）
    if INTEL_LIB.exists():
        snap = BACKUP / today
        if not snap.exists():
            shutil.copytree(INTEL_LIB, snap)
            print(f"[backup] 结构化情报库快照 -> {snap}")
        # 清理 7 天前快照
        for old in sorted(BACKUP.iterdir()):
            if old.is_dir() and old.name < (datetime.date.today() - datetime.timedelta(days=7)).isoformat():
                shutil.rmtree(old, ignore_errors=True)
                print(f"[clean] 旧快照 {old}")

    # 日志轮转：保留最近 5 个
    for f in sorted(LOGS.glob("*.log*")):
        pass  # 暂不自动删应用日志，量很小（8M）

    print(f"结果: 删除 {removed} 个切片，释放 {freed/1e6:.1f}MB" + ("（dry-run 未实际删除）" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
