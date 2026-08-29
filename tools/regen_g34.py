#!/usr/bin/env python3
"""应急：生成 KT vs BRO G3 局末 + G4 BP（Codex 全量，用户标准格式）。

用法（服务器）：/opt/danmu-intel/.venv/bin/python /opt/danmu-intel/tools/regen_g34.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt/danmu-intel/tools")

from vps_intel_pipeline import (  # noqa: E402
    DANMU,
    REPORTS,
    SLICE_DIR,
    STATE_DIR,
    league_files,
    run_codex_report,
    slice_rows,
    write_md_mirror,
)

MID = "lol-kt-bro2-2026-08-26"
TEAMS = ["KT Rolster", "HANJIN BRION"]
DATE = "2026-08-26"


def main() -> int:
    allf = sorted(DANMU.glob("*/*.jsonl"))
    files = league_files({"id": MID}, allf)
    # G4 BP 优先（当前局），再补 G3 局末
    nodes = [
        (4, "bp", "2026-08-26T10:45:00+00:00", "2026-08-26T11:20:00+00:00", ""),
        (3, "end", "2026-08-26T10:20:00+00:00", "2026-08-26T10:58:00+00:00", "est"),
    ]
    for gi, gp, frm, to, eb in nodes:
        rep = REPORTS / f"intel_danmu_{TEAMS[0]}-{TEAMS[1]}_{DATE}_g{gi}_{gp}.html"
        st = STATE_DIR / f"{MID}_g{gi}_{gp}.json"
        sf = SLICE_DIR / f"{MID}_g{gi}_{gp}.jsonl"
        for p in (rep, st, sf):
            try:
                p.unlink()
            except OSError:
                pass
        n = slice_rows(frm, files, sf, to)
        ij = STATE_DIR / f"{MID}_g{gi}_{gp}_intel.json"
        subprocess.run(
            ["/opt/danmu-intel/.venv/bin/python", "/opt/danmu-intel/tools/danmu_intel.py",
             "--input", str(sf), "--out", str(ij)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        t0 = time.time()
        rc, so, se = run_codex_report(
            MID, TEAMS, DATE, ij, sf, game=gi, gphase=gp, end_basis=eb,
        )
        ok = rep.exists()
        print(
            f"G{gi} {gp}: slice={n} elapsed={time.time()-t0:.0f}s rc={rc} "
            f"exists={ok} bytes={rep.stat().st_size if ok else 0}",
            flush=True,
        )
        if ok:
            write_md_mirror(rep)
            st.write_text(
                '{"match":"%s","game":%d,"phase":"%s","slice_rows":%d,'
                '"report":"%s","report_exists":true,"codex_rc":%d,'
                '"source":"codex_full","generated_at":"2026-08-26T11:00:00+00:00"}'
                % (MID, gi, gp, n, rep, rc),
                encoding="utf-8",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
