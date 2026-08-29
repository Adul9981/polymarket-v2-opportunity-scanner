#!/usr/bin/env python3
"""Slice raw danmaku JSONL by MATCH dimension (a BO series with optional games).

Processing unit = MATCH (one series, e.g. WBG vs LNG BO3).
A match may contain multiple games (小局); switching G1 -> G2 keeps the SAME
match bucket, only the game label changes. Raw per-stream JSONL is never
modified; slices are derived views under docs/data/danmu/slices/<match_id>/.

Usage:
  python3 tools/slice_danmu_by_match.py --manifest docs/data/danmu/slices/manifest.json
  python3 tools/slice_danmu_by_match.py --manifest ... --out-dir docs/data/danmu/slices

Manifest schema (docs/data/danmu/slices/manifest.json):
{
  "matches": [
    {
      "id": "2026-08-19_wbg_lng",
      "teams": ["WBG", "LNG"],
      "league": "LPL",
      "streams": [
        {"file": "docs/data/danmu/huya/2026-08-19_official_660000.jsonl",
         "source": "official_660000"}
      ],
      "window": {"start": "2026-08-19T15:12:00+08:00", "end": "2026-08-19T16:40:00+08:00"},
      "games": [
        {"game_no": 1, "window": {"start": "...", "end": "..."}},
        {"game_no": 2, "window": {"start": "...", "end": "..."}}
      ]
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_ts(value) -> float | None:
    """Normalize row timestamp to epoch seconds (huya numeric ts / soop unixtime)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("+0800", "+08:00")
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def row_ts(row: dict) -> float | None:
    if row.get("unixtime"):
        return float(row["unixtime"])
    return parse_ts(row.get("ts"))


def load_rows(file: str):
    rows = []
    with open(file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def window_ts(window: dict) -> tuple[float, float]:
    return parse_ts(window["start"]), parse_ts(window["end"])


def slice_rows(rows, start_ts: float, end_ts: float):
    out = []
    for r in rows:
        ts = row_ts(r)
        if ts is None:
            continue
        if start_ts <= ts <= end_ts:
            out.append((ts, r))
    out.sort(key=lambda x: x[0])
    return [r for _, r in out]


def summarize(rows) -> dict:
    times = sorted(t for r in rows if (t := row_ts(r)) is not None)
    users = len({r.get("uid") or r.get("user_id") for r in rows})
    # intra-window gaps > 10 min = capture discontinuity
    gaps = []
    if times:
        for i in range(1, len(times)):
            d = times[i] - times[i - 1]
            if d > 600:
                gaps.append({
                    "from": datetime.fromtimestamp(times[i - 1]).strftime("%Y-%m-%d %H:%M:%S"),
                    "to": datetime.fromtimestamp(times[i]).strftime("%Y-%m-%d %H:%M:%S"),
                    "gap_min": round(d / 60, 1),
                })
    sources = Counter(r.get("source") or r.get("platform") or "unknown" for r in rows)
    return {
        "count": len(rows),
        "active_users": users,
        "window": {
            "start": datetime.fromtimestamp(times[0]).strftime("%Y-%m-%d %H:%M:%S") if times else None,
            "end": datetime.fromtimestamp(times[-1]).strftime("%Y-%m-%d %H:%M:%S") if times else None,
        },
        "sources": dict(sources),
        "gaps_over_10min": gaps,
    }


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Slice danmaku JSONL by match dimension")
    ap.add_argument("--manifest", required=True, help="match manifest JSON path")
    ap.add_argument("--out-dir", default="docs/data/danmu/slices")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    out_root = root / args.out_dir
    out_root.mkdir(parents=True, exist_ok=True)

    index = {"schema_version": "1.0", "matches": []}
    index_path = out_root / "index.json"
    if index_path.exists():
        index = json.load(open(index_path, encoding="utf-8"))
        index.setdefault("matches", [])

    for m in manifest.get("matches", []):
        mid = m["id"]
        start_ts, end_ts = window_ts(m["window"])
        all_rows = []
        stream_brief = []
        for s in m.get("streams", []):
            fpath = root / s["file"]
            rows = load_rows(fpath)
            hit = slice_rows(rows, start_ts, end_ts)
            all_rows.extend(hit)
            stream_brief.append({"source": s.get("source"), "count": len(hit)})
        all_rows.sort(key=lambda r: row_ts(r) or 0)

        mdir = out_root / mid
        write_jsonl(mdir / "all.jsonl", all_rows)

        games_summary = []
        for g in m.get("games", []):
            gs, ge = window_ts(g["window"])
            g_rows = slice_rows(all_rows, gs, ge)
            write_jsonl(mdir / f"game_{g['game_no']}.jsonl", g_rows)
            games_summary.append({"game_no": g["game_no"], **summarize(g_rows)})

        summary = {
            "id": mid,
            "teams": m.get("teams", []),
            "league": m.get("league", ""),
            "streams": stream_brief,
            "all": summarize(all_rows),
            "games": games_summary,
        }
        with open(mdir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)

        # upsert index entry
        index["matches"] = [x for x in index["matches"] if x.get("id") != mid]
        index["matches"].append({
            "id": mid,
            "teams": m.get("teams", []),
            "league": m.get("league", ""),
            "window": m["window"],
            "count": len(all_rows),
            "games": len(m.get("games", [])),
            "dir": str(mdir.relative_to(root)),
        })
        print(f"[slice] {mid}: {len(all_rows)} 条（games={len(m.get('games', []))}）")

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"[done] index: {index_path}")


if __name__ == "__main__":
    main()
