#!/usr/bin/env python3
"""Migrate legacy 2-level danmaku data to the 3-level game-scoped layout.

Legacy layout (before migration):
    docs/data/danmu/<platform>/<date>_<source>.jsonl
New layout (after migration):
    docs/data/danmu/<game>/<platform>/<date>_<source>.jsonl

`game` is resolved from the source id embedded in the filename via
streamer_game.game_of() (registry first, keyword fallback), which is the exact
same logic the collection layer (vps_capture.py / run_danmu_session.py) uses,
so migrated paths match where new data will be written.

Idempotent:
  - files already inside a <game>/<platform>/ tree are untouched;
  - a target that already exists is skipped (no overwrite).

Safe by default: dry-run prints the plan; pass --apply to actually move.

Usage:
  python3 tools/migrate_danmu_games.py                 # dry-run (local ROOT)
  python3 tools/migrate_danmu_games.py --apply         # migrate for real
  python3 tools/migrate_danmu_games.py --root /opt/danmu-intel --apply
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("DANMU_INTEL_ROOT", "/opt/danmu-intel"))
DANMU = ROOT / "docs" / "data" / "danmu"

GAMES = ("lol", "cs2", "dota2")

# Load game_of from the sibling streamer_game module (same dir as this script).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from streamer_game import game_of
except ImportError:  # pragma: no cover - fallback if module is absent
    def game_of(source_id: str, registry=None) -> str:  # type: ignore[misc]
        sid = (source_id or "").lower()
        if any(k in sid for k in ("csboy", "cs2", "blast", "ewc", "iem",
                                   "major", "eslcs", "gaules", "esportsworldcup")):
            return "cs2"
        if any(k in sid for k in ("dota", "ti2026", "ti_", "ti-", "maybeee")):
            return "dota2"
        return "lol"


_FN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(.+)$")


def parse_filename(name: str) -> tuple[str, str]:
    """Return (date, source) from a ``<date>_<source>.jsonl`` filename.

    Falls back to splitting on the first underscore for any name that does not
    start with an ISO date (should not happen for this dataset).
    """
    stem = name[:-6] if name.endswith(".jsonl") else name
    m = _FN.match(stem)
    if m:
        return m.group(1), m.group(2)
    if "_" in stem:
        return tuple(stem.split("_", 1))  # type: ignore[return-value]
    return "", stem


def plan(root: Path) -> list[tuple[Path, Path, str, str]]:
    """Return [(src, dst, platform, game)] for every 2-level file to move."""
    moves: list[tuple[Path, Path, str, str]] = []
    if not DANMU.exists():
        return moves
    for platform_dir in sorted(DANMU.iterdir()):
        if not platform_dir.is_dir() or platform_dir.name in GAMES:
            continue  # already a game dir -> not legacy
        for f in sorted(platform_dir.glob("*.jsonl")):
            date, source = parse_filename(f.name)
            game = game_of(source)
            dst = DANMU / game / platform_dir.name / f.name
            moves.append((f, dst, platform_dir.name, game))
    return moves


def main() -> int:
    ap = argparse.ArgumentParser(description="迁移旧弹幕目录到 game 分层结构")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--apply", action="store_true",
                    help="真正移动文件（默认只 dry-run）")
    args = ap.parse_args()

    root = Path(args.root)
    danmu = root / "docs" / "data" / "danmu"
    if not danmu.exists():
        print(f"[migrate] 无弹幕目录 {danmu}，跳过。")
        return 0

    moves = plan(root)
    if not moves:
        print(f"[migrate] {danmu} 下没有需要迁移的旧两级文件（或已迁移完）。")
        return 0

    by_game: Counter[str] = Counter()
    by_platform: Counter[str] = Counter()
    skipped_existing = 0
    for src, dst, platform, game in moves:
        if dst.exists():
            skipped_existing += 1
            print(f"  [skip 已存在] {dst.relative_to(danmu)}")
            continue
        by_game[game] += 1
        by_platform[platform] += 1
        if args.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"  [move] {src.relative_to(danmu)} -> {dst.relative_to(danmu)}")
        else:
            print(f"  [dry]  {src.relative_to(danmu)} -> {dst.relative_to(danmu)}")

    total = sum(by_game.values())
    print()
    print(f"[migrate] 计划迁移 {total} 个文件"
          + ("（dry-run 未实际移动，加 --apply 执行）" if not args.apply else "（已移动）"))
    print(f"  按 game:  {dict(by_game)}")
    print(f"  按平台:  {dict(by_platform)}")
    if skipped_existing:
        print(f"  跳过已存在: {skipped_existing} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
