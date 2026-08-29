#!/usr/bin/env python3
"""应急：彻底下架 KT vs BRO G3 全部节点（bp/mid/end），并重建时间轴。

用法（服务器）：/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/cleanup_g3.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/danmu-intel/site_repo")
REPORTS = Path("/opt/danmu-intel/reports")
MID = "lol-kt-bro2-2026-08-26"
TEAMS = ["KT Rolster", "HANJIN BRION"]
DATE = "2026-08-26"


def main() -> int:
    os.environ["GIT_SSH_COMMAND"] = (
        "ssh -i /root/.ssh/github_deploy -o StrictHostKeyChecking=accept-new"
    )
    names = [
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_bp.html",
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_bp.md",
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_mid.html",
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_mid.md",
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_end.html",
        f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g3_end.md",
    ]
    for n in names:
        for base in (REPORTS, REPO / "intel"):
            p = base / n
            if p.exists():
                subprocess.run(["git", "-C", str(REPO), "rm", "-q", str(p.relative_to(REPO))],
                               capture_output=True, text=True)
                p.unlink(missing_ok=True)
                print("removed:", n, flush=True)
    subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, text=True)
    r = subprocess.run(
        ["git", "-C", str(REPO), "commit", "-q", "-m", "下架 G3 全部节点"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"], capture_output=True, text=True)
        print("committed+pushed", flush=True)
    else:
        print("commit skipped:", r.stderr[:120], flush=True)

    sys.path.insert(0, "/opt/danmu-intel/tools")
    from vps_intel_pipeline import build_timeline_shell  # noqa: E402
    print(build_timeline_shell(MID, TEAMS, "LCK CL", DATE, max_games=5), flush=True)
    shell = (REPORTS / f"match_{MID}.html").read_text(encoding="utf-8")
    print("real links:", re.findall(r'data-src="([^"]*)"', shell), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
