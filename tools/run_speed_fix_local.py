#!/usr/bin/env python3
"""本地速览卡批量修复入口（2026-08-26，独立于 ssh 场景）。

用法：python3 tools/run_speed_fix_local.py --dir /path/to/reports [--check]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "speedcard_consistency.py"),
        "--dir", args.dir,
    ]
    if args.check:
        cmd.append("--check")
    else:
        cmd.append("--fix")
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
