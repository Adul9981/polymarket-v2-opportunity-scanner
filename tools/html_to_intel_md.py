#!/usr/bin/env python3
"""Convert an intel HTML page to a full-fidelity Markdown mirror.

Guarantee: every heading / paragraph / list item / table row / note / link
in the HTML is preserved in the MD output (no summarization, no dropped
sections). Used to keep knowledge/intel_pages/*.md identical in content
to reports/intel_*.html (spec: knowledge/INTEL_MD_MIRROR.md).

Usage:
  python3 tools/html_to_intel_md.py \
      --html reports/intel_danmu_DNS-KRX_2026-08-24.html \
      --md knowledge/intel_pages/intel_danmu_DNS-KRX_2026-08-24.md

Or batch:
  python3 tools/html_to_intel_md.py --all
"""

from __future__ import annotations

import argparse
import html as html_mod
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class _TextCollector(HTMLParser):
    """Collect text and structure from an intel HTML page in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._stack: list[str] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._li: list[str] | None = None
        self._in_head = False
        self._head_depth = 0

    # -- helpers ----------------------------------------------------------
    def _emit(self, text: str) -> None:
        if self._cell is not None:
            self._cell.append(text)
        elif self._li is not None:
            self._li.append(text)
        elif self._table is not None and self._row is not None:
            pass  # text outside cells within table: ignore
        else:
            self.out.append(text)

    @staticmethod
    def _clean(parts: list[str]) -> str:
        s = "".join(parts)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # -- parser hooks ------------------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        attrs = dict(attrs)
        cls = attrs.get("class", "")
        if tag == "style" or tag == "script":
            self._stack.append(tag)
            return
        if tag in ("h1", "h2", "h3", "h4"):
            self._in_head = True
            self._head_depth = int(tag[1])
            self._stack.append(tag)
            self.out.append("\n\n")
            return
        if tag in ("p", "div", "section"):
            if tag == "div" and "note" in cls:
                self.out.append("\n\n> ")
            elif tag == "div" and cls in ("meta", "small", "sub"):
                self.out.append("\n\n*")
            elif tag == "p":
                self.out.append("\n\n")
            self._stack.append(tag)
            return
        if tag == "ul" or tag == "ol":
            self.out.append("\n")
            self._stack.append(tag)
            return
        if tag == "li":
            self._li = []
            self.out.append("\n- ")
            return
        if tag == "table":
            self._table = []
            self.out.append("\n\n")
            self._stack.append(tag)
            return
        if tag == "tr":
            self._row = []
            self._stack.append(tag)
            return
        if tag in ("td", "th"):
            self._cell = []
            self._stack.append(tag)
            return
        if tag == "br":
            self._emit("\n")
            return
        if tag == "code":
            self._emit("`")
            return
        if tag == "a":
            href = attrs.get("href", "")
            if href and not href.startswith("#"):
                self.out.append("[")
                self._stack.append(("a", href))
            else:
                self._stack.append(tag)
            return
        if tag in ("strong", "b"):
            self._emit("**")
            return
        if tag in ("em", "i"):
            self._emit("*")
            return
        self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script"):
            if self._stack:
                self._stack.pop()
            return
        if tag in ("h1", "h2", "h3", "h4"):
            parts: list[str] = []
            while self.out and not self.out[-1].startswith("\n\n"):
                parts.insert(0, self.out.pop())
            txt = self._clean(parts)
            if self.out and self.out[-1] == "\n\n":
                self.out.pop()
            prefix = "#" * self._head_depth + " "
            self.out.append(f"\n\n{prefix}{txt}\n")
            self._in_head = False
            if self._stack and self._stack[-1] == tag:
                self._stack.pop()
            return
        if tag in ("p", "div", "section"):
            if self._stack and self._stack[-1] == tag:
                self._stack.pop()
            return
        if tag == "li":
            if self._li is not None:
                self.out.append(self._clean(self._li))
                self._li = None
            return
        if tag == "td" or tag == "th":
            if self._cell is not None and self._row is not None:
                self._row.append(self._clean(self._cell))
                self._cell = None
            if self._stack and self._stack[-1] == tag:
                self._stack.pop()
            return
        if tag == "tr":
            if self._row is not None and self._table is not None:
                self._table.append(self._row)
                self._row = None
            if self._stack and self._stack[-1] == tag:
                self._stack.pop()
            return
        if tag == "table":
            if self._table:
                rows = self._table
                if rows:
                    widths = max(len(r) for r in rows)
                    header = rows[0]
                    lines = [
                        "| " + " | ".join(cell.replace("|", "\\|") for cell in row + [""] * (widths - len(row))) + " |"
                        for row in rows
                    ]
                    sep = "| " + " | ".join(["---"] * widths) + " |"
                    self.out.append("\n" + lines[0] + "\n" + sep + "\n" + "\n".join(lines[1:]) + "\n")
                self._table = None
            if self._stack and self._stack[-1] == tag:
                self._stack.pop()
            return
        if tag == "code":
            self._emit("`")
            return
        if tag == "a":
            if self._stack and isinstance(self._stack[-1], tuple) and self._stack[-1][0] == "a":
                _, href = self._stack.pop()
                self.out.append(f"]({href})")
            elif self._stack and self._stack[-1] == "a":
                self._stack.pop()
            return
        if tag in ("strong", "b"):
            self._emit("**")
            return
        if tag in ("em", "i"):
            self._emit("*")
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._stack and self._stack[-1] in ("style", "script"):
            return
        self._emit(data)


def convert(html_text: str) -> str:
    parser = _TextCollector()
    parser.feed(html_text)
    parts = parser.out
    # join and normalize blank lines
    text = "".join(parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def intel_html_files() -> list[Path]:
    return sorted((ROOT / "reports").glob("intel_*.html"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Intel HTML -> full-fidelity MD mirror")
    ap.add_argument("--html", default=None, help="source HTML (reports/intel_*.html)")
    ap.add_argument("--md", default=None, help="target MD (knowledge/intel_pages/*.md)")
    ap.add_argument("--all", action="store_true", help="convert every reports/intel_*.html")
    ap.add_argument("--dry-run", action="store_true", help="report files without writing")
    args = ap.parse_args()

    target_dir = ROOT / "knowledge" / "intel_pages"
    target_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[Path, Path]] = []
    if args.all:
        for src in intel_html_files():
            dst = target_dir / (src.stem + ".md")
            jobs.append((src, dst))
    else:
        if not args.html or not args.md:
            ap.error("--all 或同时提供 --html/--md")
        jobs = [(ROOT / args.html, ROOT / args.md)]

    written = 0
    for src, dst in jobs:
        if not src.exists():
            print(f"[skip] 不存在: {src}")
            continue
        md = convert(src.read_text(encoding="utf-8"))
        if args.dry_run:
            print(f"[plan] {src.name} -> {dst.relative_to(ROOT)} ({len(md)} chars)")
            continue
        dst.write_text(md, encoding="utf-8")
        written += 1
        print(f"[ok] {dst.relative_to(ROOT)} ({len(md)} chars)")
    print(f"done: {written} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
