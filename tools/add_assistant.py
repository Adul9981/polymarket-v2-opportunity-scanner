#!/usr/bin/env python3
"""Inject the shared help assistant stylesheet and script into site pages."""

from __future__ import annotations

import re
from pathlib import Path


SITE = Path(".danmu_intel_site")
VERSION = "20261124a"
CSS_RE = re.compile(
    r'\n?<link\b[^>]*\bhref=["\'][^"\']*assistant\.css(?:\?v=[^"\']*)?["\'][^>]*>\n?',
    re.I,
)
JS_RE = re.compile(
    r'\n?<script\b[^>]*\bsrc=["\'][^"\']*assistant\.js(?:\?v=[^"\']*)?["\'][^>]*></script>\n?',
    re.I,
)


def asset_path(page: Path, site: Path) -> tuple[str, str]:
    rel = page.relative_to(site)
    depth = max(len(rel.parts) - 1, 0)
    if depth == 0:
        base = "intel/"
    elif depth == 1 and rel.parts[0] == "intel":
        base = ""
    else:
        base = "../" * depth + "intel/"
    return f"{base}assistant.css", f"{base}assistant.js"


def inject_file(page: Path, site: Path = SITE) -> bool:
    if page.name.startswith("._"):
        return False
    try:
        text = page.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    clean = JS_RE.sub("", CSS_RE.sub("", text))
    if "</body>" not in clean:
        return False
    css, script = asset_path(page, site)
    snippet = (
        f'<link rel="stylesheet" href="{css}?v={VERSION}">'
        f'<script src="{script}?v={VERSION}" defer></script>'
    )
    updated = clean.replace("</body>", snippet + "</body>", 1)
    if updated == text:
        return False
    page.write_text(updated, encoding="utf-8")
    return True


def inject_all(site: Path = SITE) -> int:
    site = Path(site)
    return sum(1 for page in site.rglob("*.html") if inject_file(page, site))


def main() -> None:
    print(f"injected assistant into {inject_all()} pages")


if __name__ == "__main__":
    main()
