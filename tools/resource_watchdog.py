#!/usr/bin/env python3
"""服务器资源预警（2026-08-26 建立）：内存 / 磁盘 / 情报中间产物监控。

每 5 分钟运行一次（systemd timer），写入 runtime/health.json；
超阈值时推送 Telegram（经 Vercel /api/alert 复用 bot），60 分钟内不重复告警。

阈值（可调）：
  内存可用 < 600MB 或使用率 > 82%
  磁盘使用率 > 80%
  intel_slices > 800MB（中间产物未及时清理）
"""

from __future__ import annotations

import datetime
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path("/opt/danmu-intel")
HEALTH = ROOT / "runtime" / "health.json"
ALERT_LOG = ROOT / "logs" / "resource_watch.log"
ALERT_URL = "https://danmu-intel-api.vercel.app/api/alert"

MEM_FREE_MIN_MB = 600
MEM_USED_MAX = 82.0
DISK_USED_MAX = 80.0
SLICES_MAX_MB = 800.0
ALERT_COOLDOWN_S = 3600


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def parse_size(text: str) -> float:
    """'768M'/'1.2G' -> MB"""
    try:
        v = float(text[:-1])
        if text.endswith("G"):
            return v * 1024
        return v
    except Exception:  # noqa: BLE001
        return 0.0


def send_alert(text: str) -> None:
    try:
        body = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            ALERT_URL, data=body, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:  # noqa: BLE001
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ALERT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%F %T} 推送失败: {e}\n")


def main() -> int:
    mem = sh(["free", "-m"])
    mem_used_pct = 0.0
    mem_free_mb = 0.0
    for line in mem.splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            total = float(parts[1])
            used = float(parts[2])
            avail = float(parts[6]) if len(parts) > 6 else total - used
            mem_used_pct = used / total * 100
            mem_free_mb = avail
            break

    df = sh(["df", "-k", "/"])
    disk_used_pct = 0.0
    for line in df.splitlines():
        if line.startswith("/dev"):
            parts = line.split()
            disk_used_pct = float(parts[4].rstrip("%"))
            break

    slices_mb = parse_size(sh(["du", "-sm", str(ROOT / "data" / "intel_slices")]).split()[0]) if (ROOT / "data" / "intel_slices").exists() else 0.0
    raw_mb = parse_size(sh(["du", "-sm", str(ROOT / "docs" / "data" / "danmu")]).split()[0]) if (ROOT / "docs" / "data" / "danmu").exists() else 0.0

    warnings: list[str] = []
    if mem_free_mb < MEM_FREE_MIN_MB:
        warnings.append(f"内存可用 {mem_free_mb:.0f}MB < {MEM_FREE_MIN_MB}MB")
    if mem_used_pct > MEM_USED_MAX:
        warnings.append(f"内存使用 {mem_used_pct:.0f}% > {MEM_USED_MAX}%")
    if disk_used_pct > DISK_USED_MAX:
        warnings.append(f"磁盘使用 {disk_used_pct:.0f}% > {DISK_USED_MAX}%")
    if slices_mb > SLICES_MAX_MB:
        warnings.append(f"intel_slices {slices_mb:.0f}MB > {SLICES_MAX_MB}MB（建议跑 cleanup_intel_artifacts.py）")

    status = "ok" if not warnings else "warning"
    health = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "mem_used_pct": round(mem_used_pct, 1),
        "mem_free_mb": round(mem_free_mb),
        "disk_used_pct": round(disk_used_pct, 1),
        "intel_slices_mb": round(slices_mb, 1),
        "raw_danmu_mb": round(raw_mb, 1),
        "warnings": warnings,
    }
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")

    if warnings:
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        last = 0.0
        if ALERT_LOG.exists():
            try:
                last = float(ALERT_LOG.read_text(encoding="utf-8").strip().splitlines()[-1].split("|")[0])
            except Exception:  # noqa: BLE001
                last = 0.0
        if time.time() - last > ALERT_COOLDOWN_S:
            text = f"云服务器资源预警（{datetime.datetime.now():%m-%d %H:%M}）\n" + "\n".join(warnings)
            send_alert(text)
            with ALERT_LOG.open("a", encoding="utf-8") as f:
                f.write(f"{time.time():.0f}|{datetime.datetime.now():%F %T}|{'；'.join(warnings)}\n")
    print(json.dumps(health, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
