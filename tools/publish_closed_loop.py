#!/usr/bin/env python3
"""Build and optionally publish a closed-loop page to the danmu-intel site.

Usage:
  python3 tools/publish_closed_loop.py --match-id 2026-08-22_we_lgd --push

Builds intel/closed_loop_<match-id>.html in the site working copy, then
git add/commit/push when --push is given.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--report-rel", default="", help="relative link to the full intel page")
    ap.add_argument("--site-dir", default="/private/tmp/danmu-intel-site")
    ap.add_argument("--push", action="store_true", help="git add/commit/push after build")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    args = ap.parse_args()

    site = Path(args.site_dir)
    out = site / "intel" / f"closed_loop_{args.match_id}.html"
    cmd = [
        sys.executable,
        "tools/build_closed_loop.py",
        "--match-id",
        args.match_id,
        "--out",
        str(out),
        "--matches-json",
        args.matches_json,
    ]
    if args.report_rel:
        cmd += ["--report-rel", args.report_rel]
    subprocess.run(cmd, check=True)

    if args.push:
        subprocess.run(["git", "-C", str(site), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(site), "commit", "-m", f"closed loop {args.match_id}"],
            check=True,
        )
        subprocess.run(["git", "-C", str(site), "push"], check=True)
        print(f"pushed closed_loop_{args.match_id}")


if __name__ == "__main__":
    main()
