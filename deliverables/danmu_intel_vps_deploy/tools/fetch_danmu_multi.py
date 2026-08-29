#!/usr/bin/env python3
"""Concurrent live-danmaku capture for multiple rooms (Huya + SOOP).

Each room runs the platform collector in its own subprocess; every process
writes to its own JSONL under docs/data/danmu/<platform>/. Rooms are given as
live page URLs; the platform is auto-detected (huya.com / sooplive.com).

Usage:
  /tmp/intel-whisper-venv/bin/python tools/fetch_danmu_multi.py \
      --rooms "https://www.huya.com/323444,https://play.sooplive.com/afchall/296450537" \
      --seconds 3600

--seconds 0 (default) means until Ctrl-C; Ctrl-C stops all children.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = "/tmp/intel-whisper-venv/bin/python"


def platform_of(url: str) -> str:
    if "huya.com" in url:
        return "huya"
    if "sooplive.com" in url:
        return "soop"
    raise ValueError(f"unsupported platform: {url}")


def output_path(url: str) -> Path:
    date = datetime.now().strftime("%Y-%m-%d")
    plat = platform_of(url)
    tag = url.rstrip("/").split("/")[-1]
    return ROOT / "docs" / "data" / "danmu" / plat / f"{date}_{tag}.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="multi-room live danmaku capture")
    ap.add_argument("--rooms", required=True, help="comma-separated live page URLs")
    ap.add_argument("--seconds", type=int, default=0, help="0 = until Ctrl-C")
    args = ap.parse_args()

    urls = [u.strip() for u in args.rooms.split(",") if u.strip()]
    procs: list[tuple[subprocess.Popen, str, Path]] = []
    for url in urls:
        plat = platform_of(url)
        script = ROOT / "tools" / ("fetch_huya_danmu.py" if plat == "huya" else "fetch_soop_danmu.py")
        out = output_path(url)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [PY, str(script), "--url", url]
        if args.seconds:
            cmd += ["--seconds", str(args.seconds)]
        cmd += ["--out", str(out)]
        env = dict(os.environ)
        env.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
        p = subprocess.Popen(cmd, env=env)
        procs.append((p, url, out))
        print(f"[multi] started {url} -> {out} (pid {p.pid})", flush=True)

    def stop(_sig, _frm):
        print("[multi] stopping all collectors", flush=True)
        for p, _, _ in procs:
            try:
                p.terminate()
            except ProcessLookupError:
                pass
        sys.exit(130)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    t0 = time.time()
    while procs:
        time.sleep(5)
        if args.seconds and time.time() - t0 >= args.seconds:
            for p, _, _ in procs:
                try:
                    p.terminate()
                except ProcessLookupError:
                    pass
            break
        procs = [x for x in procs if x[0].poll() is None]
        for p, url, out in procs:
            print(f"[multi] alive: {url} ({out.name})", flush=True)

    for p, url, out in procs:
        p.wait(timeout=10)
        print(f"[multi] exited: {url} -> {out}", flush=True)
    print("[multi] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
