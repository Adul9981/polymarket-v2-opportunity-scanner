#!/usr/bin/env python3
"""应急：重新生成 lol-kt-bro2-2026-08-26 G1 节点（BP/MID/END，BO5，虎牙源已修复）。

用法（服务器）：/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/regen_kt_nodes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/danmu-intel/tools")

from vps_intel_pipeline import (  # noqa: E402
    REPORTS,
    SLICE_DIR,
    STATE_DIR,
    fast_intel_node,
    slice_rows,
)

SLUG = "lol-kt-bro2-2026-08-26"
TEAMS = ["KT Rolster", "HANJIN BRION"]
DATE = "2026-08-26"
FILES = sorted(Path("/opt/danmu-intel/docs/data/danmu").glob("*/*.jsonl"))


def main() -> int:
    nodes = [
        (1, "bp", "2026-08-26T07:53:00+00:00", "2026-08-26T08:28:00+00:00", False),
        (1, "mid", "2026-08-26T08:08:00+00:00", "2026-08-26T08:40:00+00:00", False),
        (1, "end", "2026-08-26T08:30:00+00:00", "2026-08-26T09:05:00+00:00", True),
    ]
    for gi, gphase, frm, to, is_end in nodes:
        rep = REPORTS / f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g{gi}_{gphase}.html"
        st = STATE_DIR / f"{SLUG}_g{gi}_{gphase}.json"
        sf = SLICE_DIR / f"{SLUG}_g{gi}_{gphase}.jsonl"
        for p in (rep, st, sf):
            try:
                p.unlink()
            except OSError:
                pass
        n = slice_rows(frm, FILES, sf, to)
        ij = STATE_DIR / f"{SLUG}_g{gi}_{gphase}_intel.json"
        rc, so, se = fast_intel_node(
            SLUG, TEAMS, DATE, gi, gphase, ij, sf,
            end_basis="est" if is_end else "", max_games=5,
        )
        ok = rep.exists() and "</body>" in rep.read_text(encoding="utf-8", errors="ignore")
        print(f"G{gi} {gphase}: slice={n} rc={rc} complete={ok} {so} {se}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
