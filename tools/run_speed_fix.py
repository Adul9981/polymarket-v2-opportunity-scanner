#!/usr/bin/env python3
"""服务器端速览卡批量修复入口（2026-08-26）。
避免在 ssh 命令行内拼复杂引号/&&（审批解析会失败）：
  scp tools/run_speed_fix.py root@SERVER:/opt/danmu-intel/tools/
  ssh root@SERVER '/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/run_speed_fix.py --dir reports [--check]'
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/opt/danmu-intel/reports")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    cmd = ["/opt/danmu-intel/tools/speedcard_consistency.py", "--dir", args.dir]
    if args.check:
        cmd.append("--check")
    else:
        cmd.append("--fix")
    r = subprocess.run(cmd, cwd="/opt/danmu-intel")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
