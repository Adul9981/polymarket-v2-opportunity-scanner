#!/usr/bin/env python3
"""Inject the first-party analytics loader into every site page (idempotent).

The loader posts to /intel/api/track. It stores a namespaced visitor ID in
localStorage and a tab-scoped session ID in sessionStorage. Only aggregate
anonymous events are retained by tools/analytics_service.py.
"""

from __future__ import annotations

import re
from pathlib import Path

SITE = Path(".danmu_intel_site")
VERSION = "20261109c"

OLD_TRACK_RE = re.compile(
    r"\n?<script>.*?danmu-intel-api\.vercel\.app/api/track.*?</script>\n?",
    re.S,
)
ANALYTICS_SCRIPT_RE = re.compile(
    r'\n?<script\b[^>]*\bsrc=["\'][^"\']*analytics\.js(?:\?v=[^"\']*)?["\'][^>]*></script>\n?',
    re.I,
)
CONFIG_SCRIPT_RE = re.compile(
    r'\n?<script\b[^>]*\bsrc=["\'][^"\']*analytics-config\.js(?:\?v=[^"\']*)?["\'][^>]*></script>\n?',
    re.I,
)


def asset_path(page: Path, site: Path) -> str:
    rel = page.relative_to(site)
    depth = max(len(rel.parts) - 1, 0)
    if depth == 0:
        return "intel/analytics.js"
    if depth == 1 and rel.parts[0] == "intel":
        return "analytics.js"
    return "../" * depth + "intel/analytics.js"


def inject_file(page: Path, site: Path = SITE) -> bool:
    if page.name.startswith("._"):
        return False
    try:
        text = page.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"[add-stats-track] skip non-utf8 file: {page}")
        return False
    if "</body>" not in text:
        return False

    clean = OLD_TRACK_RE.sub("", text)
    clean = CONFIG_SCRIPT_RE.sub("", clean)
    clean = ANALYTICS_SCRIPT_RE.sub("", clean)
    src = asset_path(page, site)
    config_src = src.replace("analytics.js", "analytics-config.js")
    snippet = (
        f'<script src="{config_src}?v={VERSION}" defer></script>'
        f'<script src="{src}?v={VERSION}" defer></script>'
    )
    updated = clean.replace("</body>", snippet + "</body>", 1)
    if updated == text:
        return False
    page.write_text(updated, encoding="utf-8")
    return True


def inject_all(site_dir: Path = SITE) -> int:
    site_dir = Path(site_dir)
    return sum(1 for page in site_dir.rglob("*.html") if inject_file(page, site_dir))


def main() -> None:
    print(f"injected analytics loader into {inject_all()} pages")


if __name__ == "__main__":
    main()
