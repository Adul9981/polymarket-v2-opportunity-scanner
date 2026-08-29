#!/usr/bin/env python3
"""锁定已下架节点：G1/G2/G3 全部相位写状态文件（流水线跳过），并清理残留报告。

用法（服务器）：/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/lock_removed_nodes.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/danmu-intel/site_repo")
REPORTS = Path("/opt/danmu-intel/reports")
STATE = Path("/opt/danmu-intel/runtime/vps_intel")
MID = "lol-kt-bro2-2026-08-26"
TEAMS = ["KT Rolster", "HANJIN BRION"]
DATE = "2026-08-26"


def main() -> int:
    os_env = {
        **__import__("os").environ,
        "GIT_SSH_COMMAND": "ssh -i /root/.ssh/github_deploy -o StrictHostKeyChecking=accept-new",
    }
    for gi in (1, 2, 3):
        for gp in ("bp", "mid", "end"):
            st = STATE / f"{MID}_g{gi}_{gp}.json"
            st.write_text(
                json.dumps(
                    {
                        "match": MID, "game": gi, "phase": gp,
                        "slice_rows": 0,
                        "report": f"/opt/danmu-intel/reports/intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g{gi}_{gp}.html",
                        "report_exists": False, "codex_rc": 0,
                        "source": "disabled_by_user",
                        "generated_at": "2026-08-26T11:55:00+00:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            # 删除任何残留报告（reports + site）
            for base in (REPORTS, REPO / "intel"):
                p = base / f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g{gi}_{gp}.html"
                if p.exists():
                    try:
                        rel = p.relative_to(REPO)
                        subprocess.run(
                            ["git", "-C", str(REPO), "rm", "-q", str(rel)],
                            capture_output=True, text=True, env=os_env,
                        )
                    except ValueError:
                        pass
                    p.unlink(missing_ok=True)
                md = p.with_suffix(".md")
                if md.exists():
                    try:
                        rel = md.relative_to(REPO)
                        subprocess.run(
                            ["git", "-C", str(REPO), "rm", "-q", str(rel)],
                            capture_output=True, text=True, env=os_env,
                        )
                    except ValueError:
                        pass
                    md.unlink(missing_ok=True)
            print(f"locked G{gi} {gp}", flush=True)
    subprocess.run(["git", "-C", str(REPO), "add", "-A"], capture_output=True, text=True, env=os_env)
    r = subprocess.run(
        ["git", "-C", str(REPO), "commit", "-q", "-m", "锁定 G1-G3 节点防流水线重生成"],
        capture_output=True, text=True, env=os_env,
    )
    if r.returncode == 0:
        subprocess.run(["git", "-C", str(REPO), "push", "-q", "origin", "main"], capture_output=True, text=True, env=os_env)
        print("committed+pushed", flush=True)

    sys.path.insert(0, "/opt/danmu-intel/tools")
    from vps_intel_pipeline import build_timeline_shell  # noqa: E402
    print(build_timeline_shell(MID, TEAMS, "LCK CL", DATE, max_games=5), flush=True)
    shell = (REPORTS / f"match_{MID}.html").read_text(encoding="utf-8")
    print("real links:", re.findall(r'data-src="([^"]*)"', shell), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
