#!/usr/bin/env python3
"""Add favicon <link> to every site HTML page (idempotent).

在 .danmu_intel_site/ 下所有 HTML 的 <head> 后插入 favicon 引用，
相对路径按页面目录深度计算；已含 rel="icon" 的页面跳过。
"""

from __future__ import annotations

import re
from pathlib import Path

SITE = Path(".danmu_intel_site")


def favicon_href(p: Path, site: Path) -> str:
    rel = p.relative_to(site)
    depth = len(rel.parts) - 1
    return "../" * depth + "favicon.svg"


def inject_all(site: Path = SITE) -> int:
    changed = 0
    for p in site.rglob("*.html"):
        text = p.read_text(encoding="utf-8")
        if 'rel="icon"' in text:
            continue
        m = re.search(r"<head>", text, re.I)
        if not m:
            continue
        link = f'<link rel="icon" type="image/svg+xml" href="{favicon_href(p, site)}">'
        pos = m.end()
        text = text[:pos] + "\n" + link + text[pos:]
        p.write_text(text, encoding="utf-8")
        changed += 1
    return changed


def main() -> None:
    changed = inject_all()
    print(f"updated {changed} pages")


if __name__ == "__main__":
    main()
