#!/usr/bin/env python3
"""Run a resilient multi-room danmaku intelligence session.

Each room gets an independent collector, JSONL file, health-status JSON and
automatic restart. One aggregate monitor continuously refreshes the HTML and
machine-readable intelligence outputs.

Example:
  /tmp/intel-whisper-venv/bin/python tools/run_danmu_session.py \
    --session lpl_lck_2026-08-19 \
    --title "LPL / LCK 多直播间弹幕情报" \
    --room official_660000=https://www.huya.com/660000 \
    --room mile_149361=https://www.huya.com/149361 \
    --room remember_528222=https://www.huya.com/rememberlol
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# VPS 部署时可经 INTEL_PY 指定 venv 解释器；本地默认路径保持不变。
PY = os.environ.get("INTEL_PY") or "/tmp/intel-whisper-venv/bin/python"


def platform_of(url: str) -> str:
    if "huya.com" in url:
        return "huya"
    if "sooplive.com" in url:
        return "soop"
    raise ValueError(f"unsupported platform: {url}")


def safe_source(value: str) -> str:
    source = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    if not source:
        raise ValueError("empty source id")
    return source


def parse_rooms(values: list[str]) -> list[tuple[str, str]]:
    rooms: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"--room must be SOURCE=URL: {value}")
        source, url = value.split("=", 1)
        rooms.append((safe_source(source), url.strip()))
    if not rooms:
        raise ValueError("at least one --room entry is required")
    sources = [source for source, _ in rooms]
    if len(sources) != len(set(sources)):
        raise ValueError("room source ids must be unique")
    return rooms


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_status(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="多直播间弹幕采集 + 情报监控")
    ap.add_argument("--room", action="append", default=[], help="SOURCE=URL；可重复")
    ap.add_argument("--session", default=None, help="稳定会话标识")
    ap.add_argument("--title", default="多直播间弹幕实时情报")
    ap.add_argument("--seconds", type=int, default=0, help="0 = 持续到 Ctrl-C")
    ap.add_argument("--monitor-interval", type=int, default=60)
    ap.add_argument("--first-message-timeout", type=int, default=120)
    ap.add_argument("--restart-delay", type=int, default=10)
    args = ap.parse_args()

    rooms = parse_rooms(args.room)
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    session = safe_source(args.session or f"danmu_{date}_{datetime.datetime.now():%H%M%S}")
    session_dir = ROOT / "runtime" / "danmu_sessions" / session
    report = ROOT / "reports" / f"intel_danmu_live_{session}.html"
    intel_json = session_dir / "intel.json"
    manifest_path = session_dir / "session.json"
    session_dir.mkdir(parents=True, exist_ok=True)

    room_defs: list[dict] = []
    for source, url in rooms:
        platform = platform_of(url)
        out = ROOT / "docs" / "data" / "danmu" / platform / f"{date}_{source}.jsonl"
        status = session_dir / f"{source}.status.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        room_defs.append(
            {"source": source, "url": url, "platform": platform, "out": out, "status": status}
        )

    env = dict(os.environ)
    env.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    collectors: dict[str, subprocess.Popen] = {}
    restart_counts = {item["source"]: 0 for item in room_defs}

    def start_collector(item: dict) -> subprocess.Popen:
        script = ROOT / "tools" / (
            "fetch_huya_danmu.py" if item["platform"] == "huya" else "fetch_soop_danmu.py"
        )
        cmd = [PY, str(script), "--url", item["url"]]
        if args.seconds:
            cmd += ["--seconds", str(args.seconds)]
        cmd += ["--out", str(item["out"])]
        if item["platform"] == "huya":
            cmd += [
                "--status", str(item["status"]),
                "--source", item["source"],
                "--first-message-timeout", str(args.first_message_timeout),
            ]
        process = subprocess.Popen(cmd, env=env)
        print(
            f"[multi] 已启动 {item['source']} {item['url']} -> {item['out']} (pid {process.pid})",
            flush=True,
        )
        return process

    for item in room_defs:
        collectors[item["source"]] = start_collector(item)

    monitor_cmd = [
        PY, str(ROOT / "tools" / "danmu_live_monitor.py"),
        "--html", str(report),
        "--json", str(intel_json),
        "--title", args.title,
        "--interval", str(args.monitor_interval),
    ]
    for item in room_defs:
        monitor_cmd += ["--input", str(item["out"])]
        if item["platform"] == "huya":
            monitor_cmd += ["--status", str(item["status"])]
    monitor = subprocess.Popen(monitor_cmd, env=env)
    print(f"[multi] 聚合情报页：{report} (pid {monitor.pid})", flush=True)

    stopping = False

    def stop(_sig=None, _frame=None):
        nonlocal stopping
        stopping = True
        print("[multi] 正在停止全部采集器与情报监控", flush=True)
        for process in [*collectors.values(), monitor]:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    started = time.time()
    try:
        while not stopping:
            if args.seconds and time.time() - started >= args.seconds:
                stop()
                break
            time.sleep(5)
            for item in room_defs:
                source = item["source"]
                process = collectors[source]
                if process.poll() is None:
                    continue
                if args.seconds and time.time() - started >= args.seconds:
                    continue
                restart_counts[source] += 1
                print(
                    f"[ALERT] {source} 采集器退出（code={process.returncode}），"
                    f"{args.restart_delay}s 后自动重启；完整性记为受影响",
                    flush=True,
                )
                time.sleep(args.restart_delay)
                collectors[source] = start_collector(item)
            if monitor.poll() is not None:
                print("[ALERT] 聚合情报监控退出，正在自动重启", flush=True)
                monitor = subprocess.Popen(monitor_cmd, env=env)

            statuses = []
            for item in room_defs:
                status = read_status(item["status"])
                status.setdefault("source", item["source"])
                status["restart_count"] = restart_counts[item["source"]]
                statuses.append(status)
            atomic_json(
                manifest_path,
                {
                    "schema_version": 1,
                    "session": session,
                    "title": args.title,
                    "state": "running",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "report": str(report.relative_to(ROOT)),
                    "intel_json": str(intel_json.relative_to(ROOT)),
                    "rooms": statuses,
                },
            )
    finally:
        stop()
        for process in [*collectors.values(), monitor]:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        payload = read_status(manifest_path)
        payload.update(
            state="stopped",
            updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        )
        atomic_json(manifest_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
