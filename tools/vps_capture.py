#!/usr/bin/env python3
"""VPS 7x24 弹幕采集守护（临时过渡方案：VPS 只抓弹幕，本地做分析）。

职责：
1. 从 streamer_registry.json 读取直播间清单，自动生成 --room 参数；
2. 启动 run_danmu_session.py（多直播间采集 + 自动重连 + 聚合情报页）；
3. 跨天自动滚动：日期变化时优雅重启会话，弹幕按天落盘
   docs/data/danmu/<platform>/<date>_<source>.jsonl；
4. 子进程异常退出自动重启，配合 systemd 开机自启。

用法：
  python3 tools/vps_capture.py                # 常驻守护
  python3 tools/vps_capture.py --dry-run      # 只打印将抓取的直播间
  python3 tools/vps_capture.py --registry /opt/danmu-intel/knowledge/streamer_registry.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "knowledge" / "streamer_registry.json"


def load_rooms(registry: Path) -> list[dict]:
    data = json.loads(registry.read_text(encoding="utf-8"))
    rooms = []
    for s in data.get("streamers", []):
        if s.get("enabled") is False:
            continue  # 2026-08-26：国外源（twitch/kick）停用开关
        url = (s.get("live_url") or "").strip()
        sid = (s.get("id") or "").strip()
        if not sid or not url:
            continue
        status = s.get("capture_status") or ""
        rooms.append({**s, "verified": "待验证" not in status})
    if not rooms:
        raise SystemExit(f"[vps_capture] 注册表为空: {registry}")
    return rooms


def start_session(rooms: list[dict], session: str) -> subprocess.Popen:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "run_danmu_session.py"),
        "--session", session,
        "--title", "VPS 7x24 弹幕采集（本地分析过渡方案）",
    ]
    for r in rooms:
        cmd += ["--room", f"{r['id']}={r['live_url']}"]
    print(
        f"[vps_capture] {datetime.datetime.now():%F %T} 启动会话 {session}"
        f"（{len(rooms)} 个直播间）",
        flush=True,
    )
    return subprocess.Popen(cmd, env=os.environ.copy())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--poll-interval", type=int, default=5)
    ap.add_argument("--restart-delay", type=int, default=15)
    ap.add_argument("--crash-backoff", type=int, default=60)
    args = ap.parse_args()

    registry = Path(args.registry)
    rooms = load_rooms(registry)
    if args.dry_run:
        print(f"[vps_capture] 将抓取 {len(rooms)} 个直播间（{registry}）：")
        for r in rooms:
            mark = "已实测" if r["verified"] else "待验证"
            print(f"  - {r['id']:<22} {r['platform']:<6} {r['live_url']}  [{mark}]")
        return 0

    # run_danmu_session 用它启动各采集/监控子进程，确保与当前 venv 一致。
    os.environ["INTEL_PY"] = sys.executable

    consecutive_crashes = 0
    while True:
        today = datetime.date.today().isoformat()
        session = f"vps_{today}"
        proc = start_session(rooms, session)
        while True:
            time.sleep(args.poll_interval)
            if datetime.date.today().isoformat() != today:
                print("[vps_capture] 日期变化，滚动到新一天文件", flush=True)
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                consecutive_crashes = 0
                break
            if proc.poll() is not None:
                code = proc.returncode
                if code == 0:
                    print("[vps_capture] 会话正常退出", flush=True)
                else:
                    consecutive_crashes += 1
                    delay = args.crash_backoff if consecutive_crashes >= 3 else args.restart_delay
                    print(
                        f"[vps_capture] 会话异常退出 code={code}，"
                        f"{delay}s 后重启（连续 {consecutive_crashes} 次）",
                        flush=True,
                    )
                    time.sleep(delay)
                break
        if proc.poll() is not None and proc.returncode == 0:
            # 正常退出：交回给 systemd 决定是否拉起，避免空转。
            return 0
        time.sleep(args.restart_delay)


if __name__ == "__main__":
    raise SystemExit(main())
