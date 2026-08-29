#!/usr/bin/env python3
"""Record / verify an audience prediction into docs/data/intel/matches.json.

Structured predictions enable the closed-loop page to be generated without
parsing report HTML (pipeline v2).

Usage:
  python3 tools/record_prediction.py --match-id 2026-08-22_we_lgd \
      --text "资本告诉你1:1" --time "16:08" --category result --status hit
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_match(data: dict, match_id: str) -> dict | None:
    items = data.get("matches", []) if isinstance(data, dict) else data
    for m in items:
        if m.get("id") == match_id:
            return m
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--time", default="")
    ap.add_argument("--category", default="result", choices=["result", "bp", "odds", "gray"])
    ap.add_argument("--status", default="pending", choices=["pending", "hit", "miss"])
    ap.add_argument("--note", default="")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    args = ap.parse_args()

    path = Path(args.matches_json)
    data = load(path) if path.exists() else {"matches": []}
    match = find_match(data, args.match_id)
    if match is None:
        print(f"error: match {args.match_id} not found in {path}")
        raise SystemExit(1)
    match.setdefault("predictions", [])
    match["predictions"].append(
        {
            "text": args.text,
            "time": args.time,
            "category": args.category,
            "status": args.status,
            "note": args.note,
        }
    )
    save(path, data)
    print(f"recorded {args.match_id}: {args.text} [{args.status}]")


if __name__ == "__main__":
    main()
