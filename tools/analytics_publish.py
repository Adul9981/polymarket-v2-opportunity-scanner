#!/usr/bin/env python3
"""Small integration seam for shipping analytics assets with the site."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


ANALYTICS_ASSETS = (
    "analytics.html",
    "analytics.css",
    "analytics-config.js",
    "analytics.js",
    "analytics-page.js",
)
TUNNEL_RE = re.compile(r"https://[A-Za-z0-9.-]+\.trycloudflare\.com")


def resolve_api_origin(log_text: str) -> str:
    matches = TUNNEL_RE.findall(log_text or "")
    return matches[-1].rstrip("/") if matches else ""


def sync_api_config(root: Path, reports: Path) -> str:
    log_path = Path(root) / "logs" / "cloudflared-quick.err"
    config_path = Path(reports) / "analytics-config.js"
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        log_text = ""
    api_origin = resolve_api_origin(log_text)
    config_path.write_text(
        f"window.DANMU_ANALYTICS_API = {json.dumps(api_origin)};\n",
        encoding="utf-8",
    )
    return api_origin


def install_assets(reports: Path, target: Path) -> int:
    copied = 0
    for name in ANALYTICS_ASSETS:
        source = Path(reports) / name
        if source.exists():
            shutil.copy2(source, Path(target) / name)
            copied += 1
    return copied


def prepare_release(root: Path, reports: Path, target: Path) -> None:
    sync_api_config(root, reports)
    install_assets(reports, target)
