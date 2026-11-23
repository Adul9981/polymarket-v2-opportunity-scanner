#!/usr/bin/env python3
"""Map a danmaku source id / streamer to its canonical game tag.

Games are canonical slugs: `lol` (英雄联盟) / `cs2` / `dota2`.
Classification is room-level (each streamer streams exactly one game), so it is
resolved from the streamer registry first, with a keyword fallback for ad-hoc
sources that are not registered.

Shared by run_danmu_session.py and vps_capture.py so game-scoping stays in one
place.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = ROOT / "knowledge" / "streamer_registry.json"

GAME_LABELS = {
    "lol": "英雄联盟",
    "cs2": "CS2",
    "dota2": "Dota2",
}

# Fallback hints used only when a source is not in the registry.
_CS2_HINTS = ("csboy", "cs2", "cs_", "cs-", "blast", "ewc", "iem", "major",
              "eslcs", "gaules", "esportsworldcup", "esportswc")
_DOTA2_HINTS = ("dota", "ti2026", "ti_", "ti-", "maybeee", "the_international")


def load_registry(path: Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_REGISTRY
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def game_of(source_id: str, registry: dict | None = None) -> str:
    """Return the canonical game slug for a source id.

    `registry` may be an already-loaded dict (avoids re-reading the file); if
    None it is loaded from the default registry path.
    """
    sid = (source_id or "").strip().lower()
    reg = registry if registry is not None else load_registry()
    for s in reg.get("streamers", []):
        if (s.get("id") or "").strip().lower() == sid:
            g = (s.get("game") or "").strip().lower()
            if g in GAME_LABELS:
                return g
    if any(k in sid for k in _CS2_HINTS):
        return "cs2"
    if any(k in sid for k in _DOTA2_HINTS):
        return "dota2"
    return "lol"


def game_of_url(url: str, registry: dict | None = None) -> str:
    """Resolve game from a live page URL (matches registry live_url first)."""
    url = (url or "").strip().rstrip("/")
    reg = registry if registry is not None else load_registry()
    for s in reg.get("streamers", []):
        if (s.get("live_url") or "").strip().rstrip("/") == url:
            g = (s.get("game") or "").strip().lower()
            if g in GAME_LABELS:
                return g
    return game_of(url.rstrip("/").split("/")[-1], reg)


def label(game: str) -> str:
    return GAME_LABELS.get(game, game)


if __name__ == "__main__":
    import sys
    for sid in sys.argv[1:]:
        print(f"{sid} -> {game_of(sid)}")
