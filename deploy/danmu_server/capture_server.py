#!/usr/bin/env python3
"""服务器端弹幕采集守护（只采集，不分析）。

与本地 run_danmu_session.py 保持同构：每个直播间独立采集器 + JSONL 落盘 +
健康状态 + 自动重启。区别：不带 HTML 情报监控（那是本地分析层的事），
文件名的日期固定用北京时间，避免服务器 UTC 时区造成命名错位。

用法（由 systemd 调用）：
  python3 capture_server.py --session server --room official_660000=https://www.huya.com/660000
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BEIJING = datetime.timezone(datetime.timedelta(hours=8))


def bj_now() -> datetime.datetime:
    return datetime.datetime.now(BEIJING)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def safe_source(value: str) -> str:
    source = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    if not source:
        raise ValueError("empty source id")
    return source


def parse_rooms(values: list[str]) -> list[tuple[str, str]]:
    rooms: list[tuple[str, str]] = []
    for value in values:
        for token in value.split():
            if "=" not in token:
                raise ValueError(f"--room must be SOURCE=URL: {token}")
            source, url = token.split("=", 1)
            rooms.append((safe_source(source), url.strip()))
    return rooms


def platform_of(url: str) -> str:
    if "sooplive.com" in url:
        return "soop"
    return "huya"


def start_collector(room: tuple[str, str], out: Path, status: Path, timeout: int, env: dict) -> subprocess.Popen:
    source, url = room
    plat = platform_of(url)
    cmd = [PY, str(ROOT / "tools" / (f"fetch_{plat}_danmu.py")), "--url", url, "--seconds", "0", "--out", str(out)]
    if plat == "huya":
        cmd += ["--status", str(status), "--source", source, "--first-message-timeout", str(timeout)]
    print(f"[capture] start {source} {url} -> {out}", flush=True)
    return subprocess.Popen(cmd, env=env)


def main() -> int:
    ap = argparse.ArgumentParser(description="服务器端弹幕采集守护（只采集）")
    ap.add_argument("--room", action="append", default=[], help="SOURCE=URL；可重复或空格分隔多个")
    ap.add_argument("--session", default="server")
    ap.add_argument("--first-message-timeout", type=int, default=120)
    ap.add_argument("--restart-delay", type=int, default=10)
    args = ap.parse_args()
    rooms = parse_rooms(args.room)
    if not rooms:
        print("no rooms configured (ROOMS env empty?)", flush=True)
        return 1

    session_dir = ROOT / "runtime" / "danmu_sessions" / args.session
    session_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

    collectors: dict[str, subprocess.Popen] = {}
    restart_counts: dict[str, int] = {}
    last_exits: dict[str, str] = {}

    def stop(_sig=None, _frame=None) -> None:
        print("[capture] stopping collectors", flush=True)
        for proc in collectors.values():
            if proc.poll() is None:
                proc.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    for source, url in rooms:
        date = bj_now().strftime("%Y-%m-%d")
        plat = platform_of(url)
        out = ROOT / "docs" / "data" / "danmu" / plat / f"{date}_{source}.jsonl"
        status = session_dir / f"{source}.status.json"
        collectors[source] = start_collector((source, url), out, status, args.first_message_timeout, env)
        restart_counts[source] = 0
        atomic_json(status, {"source": source, "url": url, "platform": plat, "state": "capturing", "heartbeat_at": bj_now().isoformat()})

    try:
        while True:
            time.sleep(5)
            for source, proc in list(collectors.items()):
                if proc.poll() is None:
                    continue
                restart_counts[source] += 1
                last_exits[source] = str(proc.returncode)
                print(f"[capture] {source} exited rc={proc.returncode}, restart in {args.restart_delay}s "
                      f"(count={restart_counts[source]})", flush=True)
                time.sleep(args.restart_delay)
                url = dict(rooms)[source]
                date = bj_now().strftime("%Y-%m-%d")
                plat = platform_of(url)
                out = ROOT / "docs" / "data" / "danmu" / plat / f"{date}_{source}.jsonl"
                status = session_dir / f"{source}.status.json"
                collectors[source] = start_collector((source, url), out, status, args.first_message_timeout, env)
            atomic_json(
                session_dir / "rooms.json",
                {
                    "session": args.session,
                    "updated_at": bj_now().isoformat(),
                    "rooms": [
                        {"source": s, "url": u, "restart_count": restart_counts.get(s, 0), "last_exit": last_exits.get(s)}
                        for s, u in rooms
                    ],
                },
            )
    except KeyboardInterrupt:
        stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
