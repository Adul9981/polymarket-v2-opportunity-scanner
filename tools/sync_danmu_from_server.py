#!/usr/bin/env python3
"""从线上采集服务器同步弹幕数据到本地（rsync 增量）。

配置：config/danmu_sync.json（host/user/remote_base/local_base）。
用法：
  python3 tools/sync_danmu_from_server.py            # 按配置同步
  python3 tools/sync_danmu_from_server.py --host 1.2.3.4 --dry-run

设计：服务器只负责"在场"，本脚本只把原始 JSONL + 健康状态拉回本地，
分析层完全不变。host 未配置时静默退出（方便挂定时任务）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "danmu_sync.json"


def load_config() -> dict:
    if not CONFIG.exists():
        print(f"[sync] 缺少配置文件 {CONFIG}", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def rsync(args: list[str]) -> int:
    cmd = ["rsync", "-avz", "--timeout=30", "--partial"]
    cmd += args
    print("[sync] " + " ".join(cmd), flush=True)
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description="从服务器同步弹幕数据（rsync 增量）")
    ap.add_argument("--host", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    host = args.host or cfg.get("host") or ""
    if not host:
        print("[sync] host 未配置（config/danmu_sync.json），跳过。", flush=True)
        return 0

    user = cfg.get("user", "root")
    remote = cfg["remote_base"]
    local = ROOT / cfg["local_base"]
    extra = ["-n"] if args.dry_run else []
    code = 0

    for sub in ("huya", "soop"):
        code |= rsync(extra + [f"{user}@{host}:{remote}/{sub}/", f"{local}/{sub}/"])

    if cfg.get("sync_sessions"):
        remote_s = cfg.get("remote_sessions", "/opt/danmu/runtime/danmu_sessions/server")
        local_s = ROOT / cfg.get("local_sessions", "runtime/danmu_sessions/server")
        code |= rsync(extra + [f"{user}@{host}:{remote_s}/", f"{local_s}/"])

    print("[sync] 完成。" if not args.dry_run else "[sync] 预演完成（未写入）。", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
