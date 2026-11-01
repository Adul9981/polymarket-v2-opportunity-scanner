#!/usr/bin/env python3
"""Inject the unified danmu nav into the pattern decision workspace.

The `pattern-decision-live` timer rewrites `pattern_decision_workspace.html`
every 5 minutes with only its own internal nav (no return path to the danmu
intel site). This script runs right after that regeneration (systemd
ExecStartPost) and re-adds the unified nav, so the workspace always carries the
return path to 首页 / 今日情报 / 历史情报库 / 形态决策台.

Run on the VPS only (paths below are VPS deployment paths).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from add_site_nav import inject_file  # noqa: E402

TARGETS: list[tuple[Path, str]] = [
    (Path("/opt/danmu-intel/site_repo"), "intel/pattern_decision_workspace.html"),
    (Path("/var/www/danmu-pulse"), "intel/pattern_decision_workspace.html"),
]


def main() -> int:
    changed = 0
    for root, rel in TARGETS:
        p = root / rel
        if not p.exists():
            print(f"[inject-pattern-nav] skip missing {p}")
            continue
        if inject_file(p, root):
            changed += 1
            print(f"[inject-pattern-nav] injected nav into {p}")
    print(f"[inject-pattern-nav] done ({changed} changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
