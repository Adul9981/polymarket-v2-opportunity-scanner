#!/usr/bin/env python3
"""Build a filterable HTML atlas for the complete odds-shape library.

The atlas keeps the formal named patterns and the data-driven clusters as two
separate views. Every chart is derived from settled historical price paths;
no hand-drawn illustrative shape is presented as observed data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "reports" / "pattern_decision_data.json"
DEFAULT_CLUSTERS = ROOT / "reports" / "pattern_clusters_2026-11-08.json"
DEFAULT_PATH_INDEX = ROOT / "reports" / "pattern_atlas_full_paths.json"
DEFAULT_OUT = ROOT / "reports" / "pattern_atlas.html"
SNAPSHOT_ROOT = ROOT / "docs" / "data" / "snapshots"
PATH_INDEX_VERSION = 1
PATH_CURVE_POINTS = 81

sys.path.insert(0, str(ROOT / "tools"))

SPORTS = (("lol", "LoL"), ("cs2", "CS2"), ("dota2", "Dota2"))
SPORT_LABELS = dict(SPORTS)
LEVELS = (("series", "整场"), ("game", "小局"))
LEVEL_LABELS = dict(LEVELS)
FAMILY_ORDER = ("反转结构", "确立结构", "压制结构", "坠落结构", "拉锯结构")
FAMILY_COLORS = {
    "反转结构": "#0a7c66",
    "确立结构": "#0a6ed1",
    "压制结构": "#7c5cff",
    "坠落结构": "#d14f4f",
    "拉锯结构": "#c17c00",
}
GRID = tuple(range(0, 101, 2))


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def quantile(values: Iterable[float], q: float) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def interpolate(points: list[list[float]], x: float) -> float:
    if not points:
        return 0.0
    if x <= points[0][0]:
        return clamp(points[0][1])
    if x >= points[-1][0]:
        return clamp(points[-1][1])
    for left, right in zip(points, points[1:]):
        if left[0] <= x <= right[0]:
            span = right[0] - left[0]
            if span <= 1e-9:
                return clamp(right[1])
            ratio = (x - left[0]) / span
            return clamp(left[1] + (right[1] - left[1]) * ratio)
    return clamp(points[-1][1])


def normalized_path(raw: Iterable[Iterable[float]], initial: float | None = None) -> list[list[float]]:
    points = []
    for pair in raw:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        try:
            x, y = float(pair[0]), float(pair[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            points.append([x, clamp(y)])
    if not points:
        return []
    points.sort(key=lambda item: item[0])
    if initial is not None:
        points.insert(0, [0.0, clamp(initial * 100.0)])
    start, end = points[0][0], points[-1][0]
    span = max(1e-9, end - start)
    return [[clamp((x - start) / span * 100.0), y] for x, y in points]


def aggregate_curves(paths: list[list[list[float]]]) -> dict[str, Any] | None:
    if not paths:
        return None
    line: list[list[float]] = []
    band: list[list[float]] = []
    for x in GRID:
        values = [interpolate(path, x) for path in paths]
        line.append([x, round(statistics.median(values), 2)])
        band.append([x, round(quantile(values, 0.25), 2), round(quantile(values, 0.75), 2)])
    return {"n": len(paths), "line": line, "band": band}


def mirror_curve(curve: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the complementary side of an observation-side price curve."""
    if not curve:
        return None
    return {
        "n": int(curve.get("n") or 0),
        "line": [[x, round(100.0 - y, 2)] for x, y in curve.get("line") or []],
        "band": [
            [x, round(100.0 - high, 2), round(100.0 - low, 2)]
            for x, low, high in curve.get("band") or []
        ],
    }


def _dataset_signature(dataset: dict[str, Any]) -> dict[str, Any]:
    stats = dataset.get("stats") or {}
    return {
        "version": PATH_INDEX_VERSION,
        "dataset_generated_at": dataset.get("generated_at") or "",
        "training_matches": int(stats.get("training_matches") or 0),
        "training_samples": int(stats.get("training_samples") or 0),
        "snapshot_scan": stats.get("snapshot_training_scan") or {},
    }


def _team_key(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def _compact_full_path(points: list[list[float]]) -> list[list[float]]:
    """Keep the complete 0–100 timeline while bounding the embedded index size."""
    clean: list[list[float]] = []
    for pair in points:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        try:
            x, y = float(pair[0]), float(pair[1])
        except (TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            clean.append([clamp(x), clamp(y)])
    if not clean:
        return []
    clean.sort(key=lambda item: item[0])
    if len(clean) <= PATH_CURVE_POINTS:
        return [[round(x, 1), round(y, 1)] for x, y in clean]

    # Reuse the decision workspace simplifier: it keeps direction changes and
    # extrema instead of uniformly skipping through a reversal.
    import build_pattern_decision_site as decision_site

    simplified = decision_site.shape_downsample(
        [(x, y) for x, y in clean], PATH_CURVE_POINTS
    )
    out = [[round(x, 1), round(y, 1)] for x, y in simplified]
    if out[0][0] > 0:
        out.insert(0, [0.0, out[0][1]])
    if out[-1][0] < 100:
        out.append([100.0, out[-1][1]])
    return out


def build_full_path_index(
    dataset: dict[str, Any], index_path: Path = DEFAULT_PATH_INDEX,
) -> dict[str, Any]:
    """Index every labelled training market by its complete in-game path.

    ``training[].fut`` is intentionally compact: it starts at one observation
    checkpoint and records only the realised continuation. It must never be
    presented as a complete match. This index reconstructs the full 0–100
    in-game timeline from the local snapshot archive and reuses the same
    long-tail settlement trimming as the decision workspace.
    """
    signature = _dataset_signature(dataset)
    if index_path.exists():
        try:
            cached = json.loads(index_path.read_text(encoding="utf-8"))
            if cached.get("signature") == signature and isinstance(cached.get("markets"), dict):
                return cached
        except (OSError, json.JSONDecodeError):
            pass

    import build_pattern_decision_site as decision_site
    import build_pattern_library as pattern_library

    training = dataset.get("training") or []
    wanted: dict[str, set[str]] = defaultdict(set)
    for row in training:
        mid = str(row.get("mid") or "")
        slug = str(row.get("slug") or "")
        if mid and slug:
            wanted[slug].add(mid)

    markets: dict[str, dict[str, Any]] = {}
    missing_slugs: list[str] = []
    parse_errors = 0
    for slug in sorted(wanted):
        path = SNAPSHOT_ROOT / slug
        if not path.is_dir():
            missing_slugs.append(slug)
            continue
        try:
            parts = pattern_library.parse_snapshot_dir(str(path), slug)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            parse_errors += 1
            continue

        pending: list[tuple[str, int | None]] = []
        if parts.get("series"):
            pending.append(("series", None))
        pending.extend(("game", int(no)) for no in sorted((parts.get("games") or {}).keys()))
        for level, game in pending:
            mid = f"{slug}:{level}:{game or 0}"
            if mid not in wanted[slug]:
                continue
            try:
                raw, teams = decision_site.load_market_paths(parts, level, game)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                parse_errors += 1
                continue
            if not raw:
                continue
            start, end, window_source = decision_site.infer_window(slug, game, raw)
            if not (start and end and end > start):
                continue
            spacings = [decision_site.median_spacing(points) for points in raw.values() if len(points) > 1]
            spacing = statistics.median(spacings) if spacings else 0.0
            tolerance = max(300.0, spacing * 1.5)
            paths: dict[str, list[list[float]]] = {}
            side_meta: dict[str, dict[str, Any]] = {}
            for side in sorted(raw):
                points = sorted(raw[side])
                compact = _compact_full_path(decision_site.display_path(points, start, end))
                if not compact:
                    continue
                paths[str(side)] = compact
                side_meta[str(side)] = {
                    "team": teams.get(side, f"side-{side + 1}"),
                    "first_ts": points[0][0],
                    "last_ts": points[-1][0],
                    "raw_points": len(points),
                    "start_covered": points[0][0] <= start + tolerance,
                    "end_covered": points[-1][0] >= end - tolerance,
                }
            if not paths:
                continue
            markets[mid] = {
                "slug": slug,
                "sport": "cs2" if slug.startswith("cs2-") else ("dota2" if slug.startswith("dota2-") else "lol"),
                "level": level,
                "game": game,
                "start": start,
                "end": end,
                "window_source": window_source,
                "granularity": decision_site.input_granularity(list(raw.values())),
                "sides": {key: value["team"] for key, value in side_meta.items()},
                "side_meta": side_meta,
                "paths": paths,
            }

    granularity: dict[str, int] = defaultdict(int)
    endpoint_complete = 0
    minute_complete = 0
    two_sided = 0
    for market in markets.values():
        label = str(market.get("granularity") or "数据不足")
        granularity[label] += 1
        covered = all(
            meta.get("start_covered") and meta.get("end_covered")
            for meta in (market.get("side_meta") or {}).values()
        )
        if covered:
            endpoint_complete += 1
            if label == "1分钟级":
                minute_complete += 1
        if len(market.get("paths") or {}) >= 2:
            two_sided += 1

    payload = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "signature": signature,
        "markets": markets,
        "summary": {
            "markets": len(markets),
            "matches": len({value.get("slug") for value in markets.values()}),
            "endpoint_complete_markets": endpoint_complete,
            "one_minute_endpoint_complete_markets": minute_complete,
            "two_sided_markets": two_sided,
            "granularity_markets": dict(sorted(granularity.items())),
            "missing_slugs": len(missing_slugs),
            "parse_errors": parse_errors,
        },
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return payload


def canonical_rows(rows: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    """Pick one observation row per market, never one row per match slug.

    A BO3/BO5 can have separate series and map markets. Collapsing by slug
    erased those games. Within one market, two side observations may both carry
    the same label; keep one side so the same complete path is not double
    weighted. Prefer an outcome-labelled row when available.
    """
    by_market: dict[str, dict[str, Any]] = {}
    for row in rows:
        mid = str(row.get("mid") or "")
        if not mid:
            continue
        outcome = label in (row.get("ols") or [])
        stable_cut = abs(float(row.get("cut") or 50.0) - 50.0)
        score = (0 if outcome else 1, stable_cut, _team_key(row.get("team")))
        previous = by_market.get(mid)
        if previous is None or score < previous["_score"]:
            current = dict(row)
            current["_score"] = score
            by_market[mid] = current
    return list(by_market.values())


def table_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "matches": len({row["slug"] for row in rows}),
        "observations": len(rows),
        "sports": {key: len({row["slug"] for row in rows if row.get("s") == key}) for key, _ in SPORTS},
        "levels": {key: len({row["slug"] for row in rows if row.get("l") == key}) for key, _ in LEVELS},
        "combos": {},
    }
    for sport, _ in SPORTS:
        for level, _ in LEVELS:
            subset = [row for row in rows if row.get("s") == sport and row.get("l") == level]
            counts["combos"][f"{sport}|{level}"] = {
                "matches": len({row["slug"] for row in subset}),
                "observations": len(subset),
            }
    return counts


def oriented_market_paths(
    row: dict[str, Any], path_index: dict[str, Any]
) -> tuple[list[list[float]], list[list[float]], bool]:
    """Return observed side, real opponent side, and whether opponent is real."""
    market = (path_index.get("markets") or {}).get(str(row.get("mid") or "")) or {}
    paths = market.get("paths") or {}
    if not paths:
        return [], [], False
    team = _team_key(row.get("team"))
    side = next(
        (key for key, name in (market.get("sides") or {}).items() if _team_key(name) == team),
        "",
    )
    if not side:
        side = sorted(paths)[0]
    observed = normalized_path(paths.get(side) or [])
    if not observed:
        return [], [], False
    opponent_side = next((key for key in sorted(paths) if key != side), "")
    opponent = normalized_path(paths.get(opponent_side) or []) if opponent_side else []
    return observed, opponent, bool(opponent)


def aggregate_market_curves(rows: list[dict[str, Any]], path_index: dict[str, Any]) -> dict[str, Any] | None:
    observed_paths: list[list[list[float]]] = []
    opponent_paths: list[list[list[float]]] = []
    opponent_real = 0
    opponent_fallback = 0
    for row in rows:
        observed, opponent, real = oriented_market_paths(row, path_index)
        if not observed:
            continue
        observed_paths.append(observed)
        if real and opponent:
            opponent_paths.append(opponent)
            opponent_real += 1
        else:
            opponent_paths.append([[x, 100.0 - y] for x, y in observed])
            opponent_fallback += 1
    observed_curve = aggregate_curves(observed_paths)
    opponent_curve = aggregate_curves(opponent_paths)
    if not observed_curve:
        return None
    observed_curve.update({
        "path_basis": "complete_market",
        "opponent": opponent_curve,
        "opponent_real_n": opponent_real,
        "opponent_fallback_n": opponent_fallback,
    })
    return observed_curve


def pattern_records(dataset: dict[str, Any], path_index: dict[str, Any]) -> list[dict[str, Any]]:
    training = dataset.get("training") or []
    labels = dataset.get("labels") or {}
    inventory = {row.get("label"): row for row in dataset.get("pattern_inventory") or []}
    records = []
    for label, meta in labels.items():
        if label == "未知" or not isinstance(meta, dict):
            continue
        rows = [row for row in training if label in (row.get("labs") or [])]
        if not rows:
            continue
        selected = canonical_rows(rows, label)
        curves: dict[str, Any] = {}
        for sport in (None, *(key for key, _ in SPORTS)):
            for level in (None, *(key for key, _ in LEVELS)):
                subset = [
                    row for row in selected
                    if (sport is None or row.get("s") == sport)
                    and (level is None or row.get("l") == level)
                ]
                curve = aggregate_market_curves(subset, path_index)
                if curve:
                    curves[f"{sport or 'all'}|{level or 'all'}"] = curve
        counts = table_counts(rows)
        indexed = [
            market for mid, market in (path_index.get("markets") or {}).items()
            if mid in {str(row.get("mid") or "") for row in selected}
        ]
        complete = sum(
            1 for market in indexed
            if all(
                meta.get("start_covered") and meta.get("end_covered")
                for meta in (market.get("side_meta") or {}).values()
            )
        )
        inv = inventory.get(label, {})
        records.append({
            "label": label,
            "title": meta.get("title") or label,
            "family": meta.get("family") or "其他结构",
            "mark": meta.get("mark") or "形",
            "summary": meta.get("summary") or "",
            "trigger": meta.get("trigger") or "",
            "entry": meta.get("entry") or "",
            "exit": meta.get("exit") or "",
            "invalid": meta.get("invalid") or "",
            "visible_matches": int(inv.get("visible_matches") or 0),
            "outcome_matches": int(inv.get("outcome_matches") or 0),
            "counts": counts,
            "path_coverage": {
                "selected_markets": len(selected),
                "indexed_markets": len(indexed),
                "endpoint_complete_markets": complete,
            },
            "curves": curves,
        })
    family_rank = {name: idx for idx, name in enumerate(FAMILY_ORDER)}
    return sorted(records, key=lambda row: (family_rank.get(row["family"], 99), -row["counts"]["matches"], row["title"]))


def choose_representative_curve(
    match: dict[str, Any],
    scope: str,
    expected_start: float,
) -> tuple[list[list[float]], str, list[list[float]], str]:
    candidates: list[tuple[float, list[list[float]], str, list[list[float]], str]] = []
    for market in (match.get("markets") or {}).values():
        if market.get("level") != scope:
            continue
        raw_sides = market.get("sides") or []
        paths = sorted((market.get("paths") or {}).items(), key=lambda item: str(item[0]))
        side_names = (
            [raw_sides.get(key, f"side-{key}") for key in sorted(raw_sides)]
            if isinstance(raw_sides, dict)
            else list(raw_sides)
        )
        for index, (_, path) in enumerate(paths):
            normalized = normalized_path(path or [])
            if not normalized:
                continue
            target = expected_start * 100.0 if expected_start <= 1.0 else expected_start
            score = abs(normalized[0][1] - target)
            team = side_names[index] if index < len(side_names) else f"side-{index + 1}"
            opponent_curve: list[list[float]] = []
            opponent_team = ""
            if len(paths) > 1:
                opponent_index = 1 - index if index < 2 else 0
                opponent_curve = normalized_path(paths[opponent_index][1] or [])
                opponent_team = (
                    side_names[opponent_index]
                    if opponent_index < len(side_names)
                    else f"side-{opponent_index + 1}"
                )
            candidates.append((score, normalized, team, opponent_curve, opponent_team))
    if not candidates:
        return [], "", [], ""
    _, curve, team, opponent_curve, opponent_team = min(candidates, key=lambda item: item[0])
    return curve, team, opponent_curve, opponent_team


def cluster_records(
    dataset: dict[str, Any], cluster_data: dict[str, Any], path_index: dict[str, Any]
) -> list[dict[str, Any]]:
    label_meta = dataset.get("labels") or {}
    matches = {row.get("slug"): row for row in dataset.get("matches") or []}
    indexed_by_slug: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for mid, market in (path_index.get("markets") or {}).items():
        indexed_by_slug[str(market.get("slug") or "")][mid] = market
    groups = []
    for group in cluster_data.get("clusters") or []:
        sport = group.get("sport") or ""
        scope = group.get("scope") or ""
        rows = []
        for cluster_index, cluster in enumerate(group.get("clusters") or [], start=1):
            cluster_labels = sorted(
                (cluster.get("labels") or []),
                key=lambda row: (-int(row.get("count") or 0), str(row.get("label") or "")),
            )
            primary = cluster_labels[0] if cluster_labels else {}
            primary_label = str(primary.get("label") or "")
            meta = label_meta.get(primary_label) or {}
            representative = str(cluster.get("representative") or "")
            match = dict(matches.get(representative) or {})
            candidate_markets = dict(match.get("markets") or {})
            for mid, market in indexed_by_slug.get(representative, {}).items():
                candidate_markets.setdefault(mid, market)
            match["markets"] = candidate_markets
            curve, team, opponent_curve, opponent_team = choose_representative_curve(
                match, scope, float(cluster.get("pre") or 0.5)
            )
            opponent = (
                {"line": opponent_curve}
                if opponent_curve
                else mirror_curve({"line": curve, "band": [], "n": 1}) if curve else None
            )
            rows.append({
                "cluster_id": f"{sport}-{scope}-{cluster_index}",
                "name": cluster.get("name") or "未命名聚类",
                "size": int(cluster.get("size") or 0),
                "share": float(cluster.get("share") or 0),
                "pre": float(cluster.get("pre") or 0) * 100,
                "low": float(cluster.get("low") or 0) * 100,
                "high": float(cluster.get("high") or 0) * 100,
                "end": float(cluster.get("end") or 0) * 100,
                "drawdown": float(cluster.get("drawdown") or 0) * 100,
                "rebound": float(cluster.get("rebound") or 0) * 100,
                "labels": cluster_labels,
                "strategy": {
                    "primary_label": primary_label,
                    "primary_title": meta.get("title") or primary.get("display") or primary_label,
                    "cluster_signature": (
                        f"起点 {float(cluster.get('pre') or 0) * 100:.0f}c · "
                        f"低点 {float(cluster.get('low') or 0) * 100:.0f}c · "
                        f"回撤 {float(cluster.get('drawdown') or 0) * 100:.0f}c · "
                        f"反弹 {float(cluster.get('rebound') or 0) * 100:.0f}c"
                    ),
                    "trigger": meta.get("trigger") or "",
                    "entry": meta.get("entry") or "",
                    "exit": meta.get("exit") or "",
                    "invalid": meta.get("invalid") or "",
                    "basis": "执行条件借用该簇主标签；聚类负责结构归类，不代表独立胜率验证。",
                },
                "representative": representative,
                "representative_team": team,
                "representative_opponent": opponent_team,
                "curve": curve,
                "opponent": opponent,
            })
        groups.append({
            "sport": sport,
            "sport_label": SPORT_LABELS.get(sport, sport.upper()),
            "scope": scope,
            "level_label": LEVEL_LABELS.get(scope, scope),
            "matches": int(group.get("n") or 0),
            "clusters": rows,
        })
    return groups


def json_script(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def _legacy_render_html(data: dict[str, Any]) -> str:
    payload = json_script(data)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>赔率形态图谱</title>
<style>
:root{{--bg:#f5f5f7;--card:#fff;--text:#1d1d1f;--muted:#6e6e73;--line:#e5e5ea;--accent:#0a6ed1;--green:#0a7c66;--shadow:0 8px 28px rgba(0,0,0,.055)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}}a{{color:var(--accent);text-decoration:none}}button,input{{font:inherit}}button{{cursor:pointer}}.wrap{{max-width:1280px;margin:auto;padding:22px 20px 60px}}nav{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:18px}}nav a{{padding:7px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);color:#424245;font-size:13px}}nav .active{{background:#1d1d1f;color:#fff;border-color:#1d1d1f}}.hero{{background:linear-gradient(135deg,#fff 0%,#f7fbff 58%,#f0f8f5 100%);border:1px solid #e7eaf0;border-radius:24px;padding:34px 36px;box-shadow:var(--shadow)}}.eyebrow{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--green);font-weight:700}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.04;letter-spacing:-2.2px;margin:12px 0 13px;max-width:820px}}.hero p{{max-width:860px;color:#515154;line-height:1.75;margin:0;font-size:16px}}.metrics{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:24px}}.metric{{background:rgba(255,255,255,.86);border:1px solid rgba(0,0,0,.055);border-radius:16px;padding:14px 15px}}.metric b{{display:block;font-size:27px;letter-spacing:-.8px}}.metric span{{display:block;color:var(--muted);font-size:11px;margin-top:3px}}.toolbar{{position:sticky;top:10px;z-index:8;display:grid;grid-template-columns:1fr auto;gap:14px;margin:20px 0 14px;padding:14px;background:rgba(245,245,247,.9);backdrop-filter:blur(18px);border:1px solid rgba(0,0,0,.045);border-radius:18px}}.filters{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}.filter-group{{display:flex;gap:5px;background:#fff;padding:4px;border-radius:12px;border:1px solid var(--line)}}.filter-group button{{border:0;border-radius:9px;padding:7px 11px;background:transparent;color:#515154;font-size:12px}}.filter-group button.on{{background:#1d1d1f;color:#fff}}.search{{width:220px;border:1px solid var(--line);background:#fff;border-radius:12px;padding:10px 13px;outline:none}}.section-head{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:28px 2px 13px}}.section-head h2{{font-size:26px;letter-spacing:-.8px;margin:0}}.section-head p{{margin:5px 0 0;color:var(--muted);font-size:12px}}.section-head .count{{font-size:13px;color:#3a3a3c;background:#fff;border:1px solid var(--line);padding:8px 11px;border-radius:999px}}.families{{display:grid;grid-template-columns:repeat(auto-fit,minmax(195px,1fr));gap:8px;margin-bottom:14px}}.family{{display:flex;justify-content:space-between;padding:10px 12px;background:#fff;border:1px solid var(--line);border-radius:13px;font-size:12px}}.family i{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:7px}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}.card{{background:var(--card);border:1px solid rgba(0,0,0,.055);border-radius:20px;padding:17px;box-shadow:0 4px 18px rgba(0,0,0,.035);display:flex;flex-direction:column;min-width:0}}.card-top{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}.mark{{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:color-mix(in srgb,var(--fc) 12%,white);color:var(--fc);font-weight:800;font-size:17px;flex:none}}.card h3{{margin:0;font-size:18px;letter-spacing:-.35px}}.tech{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#8e8e93;font-size:9.5px;margin-top:4px}}.chip{{display:inline-flex;align-items:center;gap:5px;padding:5px 8px;border-radius:999px;background:#f5f5f7;color:#515154;font-size:10px;white-space:nowrap}}.chart{{height:154px;margin:11px 0 8px;border-radius:13px;background:linear-gradient(#fbfbfd,#f7f8fa);overflow:hidden}}.chart svg{{width:100%;height:100%;display:block}}.sample-line{{display:flex;justify-content:space-between;gap:8px;color:var(--muted);font-size:10px;margin-top:2px}}.split-counts{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:9px 0}}.split-counts div{{background:#f8f8fa;border-radius:10px;padding:8px 9px}}.split-counts span{{display:block;color:var(--muted);font-size:9px}}.split-counts b{{display:block;margin-top:2px;font-size:11.5px}}.desc{{font-size:12px;line-height:1.55;color:#515154;margin:4px 0 8px;min-height:56px}}details{{border-top:1px solid var(--line);padding-top:9px;margin-top:auto}}summary{{font-size:11px;color:#515154;cursor:pointer;font-weight:650}}.detail-grid{{display:grid;gap:6px;margin-top:8px}}.detail-row{{display:grid;grid-template-columns:52px 1fr;gap:8px;font-size:10.5px;line-height:1.5}}.detail-row span{{color:#8e8e93}}.detail-row b{{font-weight:500;color:#3a3a3c}}.cluster-groups{{display:grid;gap:16px}}.cluster-group{{background:#fff;border:1px solid rgba(0,0,0,.055);border-radius:20px;padding:18px;box-shadow:0 4px 18px rgba(0,0,0,.035)}}.cluster-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}}.cluster-head h3{{margin:0;font-size:18px}}.cluster-head p{{margin:3px 0 0;color:var(--muted);font-size:11px}}.cluster-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}.cluster-card{{border:1px solid var(--line);border-radius:15px;padding:12px;background:#fbfbfd}}.cluster-card h4{{font-size:13px;margin:0;line-height:1.35}}.cluster-card .mini{{height:88px;margin:8px -3px}}.cluster-metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:7px}}.cluster-metrics span{{font-size:9px;color:var(--muted)}}.cluster-metrics b{{display:block;font-size:10.5px;color:#3a3a3c;margin-top:1px}}.cluster-labels{{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}}.cluster-labels span{{font-size:8.5px;background:#fff;border:1px solid var(--line);border-radius:999px;padding:3px 5px;color:#5c5c61}}.note{{padding:12px 14px;border-radius:14px;background:#fff8e8;border:1px solid #f1ddb1;color:#725514;font-size:11.5px;line-height:1.65;margin:12px 0}}.empty{{grid-column:1/-1;padding:50px 20px;text-align:center;color:var(--muted);background:#fff;border-radius:18px;border:1px dashed #d7d7dc}}footer{{margin-top:28px;color:#8e8e93;font-size:10.5px;line-height:1.65}}@media(max-width:1000px){{.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.cluster-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.metrics{{grid-template-columns:repeat(3,minmax(0,1fr))}}}}@media(max-width:700px){{.wrap{{padding:14px 12px 40px}}.hero{{padding:25px 20px;border-radius:20px}}h1{{letter-spacing:-1.3px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.toolbar{{position:static;grid-template-columns:1fr}}.search{{width:100%}}.cards,.cluster-grid{{grid-template-columns:1fr}}.section-head{{align-items:flex-start}}.section-head .count{{white-space:nowrap}}}}
.chart-legend{{display:flex;align-items:center;flex-wrap:wrap;gap:12px;color:#6e6e73;font-size:9.5px;line-height:1.3;margin:-3px 1px 8px;min-height:14px}}.chart-legend span{{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}}.legend-line{{display:inline-block;width:17px;height:0;border-top:2px solid #0a6ed1}}.legend-line.opponent{{border-top:2px dashed #d88918}}.legend-line.band{{height:7px;border:0;border-radius:3px;background:rgba(10,110,209,.12)}}
</style>
</head>
<body>
<div class="wrap">
<nav><span class="active">形态图谱</span><a href="pattern_decision_workspace.html">形态决策台</a><a href="pattern_library.html">形态总库</a><a href="pattern_shapes_granularity.html">粒度对照</a></nav>
<header class="hero">
  <div class="eyebrow">PATTERN ATLAS · 2026-11-08</div>
  <h1>每一种赔率形态，都能看到它的历史结构。</h1>
  <p>先分比赛类型，再分整场与小局。下面的曲线来自已结算比赛的真实价格路径；同一条形态可以跨比赛类型出现，但不会跨层计算，也不把整场和小局混在一起。</p>
  <div class="metrics">
    <div class="metric"><b>{len(data['patterns'])}</b><span>正式命名形态</span></div>
    <div class="metric"><b>{len(data['families'])}</b><span>结构家族</span></div>
    <div class="metric"><b>{data['cluster_total']}</b><span>数据聚类（5 个比赛层级）</span></div>
    <div class="metric"><b>{data['stats']['training_matches']:,}</b><span>纳入训练的比赛</span></div>
    <div class="metric"><b>{data['stats']['training_samples']:,}</b><span>分钟观察点</span></div>
  </div>
</header>
<div class="toolbar">
  <div class="filters">
    <div class="filter-group" id="sportFilter"><button data-sport="all" class="on">全部比赛</button><button data-sport="lol">LoL</button><button data-sport="cs2">CS2</button><button data-sport="dota2">Dota2</button></div>
    <div class="filter-group" id="levelFilter"><button data-level="all" class="on">整场 + 小局</button><button data-level="series">仅整场</button><button data-level="game">仅小局</button></div>
  </div>
  <input class="search" id="search" placeholder="搜索形态名称或结构说明">
</div>
<div class="section-head"><div><h2>正式形态图谱</h2><p>同一比赛可命中多个形态，所以各形态场数不能相加成总库场数。</p></div><div class="count" id="visibleCount"></div></div>
<div class="families" id="families"></div>
<div class="cards" id="cards"></div>
<div class="section-head"><div><h2>数据聚类结果</h2><p>这是按比赛类型和整场/小局分别做聚类的研究视图，与正式命名不是一一对应。</p></div><div class="count">{data['cluster_total']} 簇 · {len(data['cluster_groups'])} 个比赛层级</div></div>
<div class="note">本次聚类覆盖 LoL 整场/小局、CS2 整场/小局、Dota2 整场共 5 个比赛层级；Dota2 当前没有足够的小局样本，因此不生成 Dota2 小局聚类，也不借用整场样本替代。</div>
<div class="cluster-groups" id="clusterGroups"></div>
<footer>口径：正式形态使用全库已结算训练记录；蓝线为观测方历史中位，橙虚线为对手方 100c 镜像，阴影为观测方 25%–75% 分位。聚类图为该簇代表比赛的真实双方 token 价格路径。历史结构只用于研究和观察，不构成胜率或投资建议。</footer>
</div>
<script id="atlas-data" type="application/json">{payload}</script>
<script>
const DATA=JSON.parse(document.getElementById('atlas-data').textContent);
const state={{sport:'all',level:'all',query:''}};
const SPORT={{lol:'LoL',cs2:'CS2',dota2:'Dota2'}},LEVEL={{series:'整场',game:'小局'}};
const FAMILY_COLORS={json_script(FAMILY_COLORS)};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const fmt=n=>Number(n||0).toLocaleString('zh-CN');
function curveFor(p){{
  const direct=`${{state.sport}}|${{state.level}}`;
  const sportAll=`${{state.sport}}|all`,allLevel=`all|${{state.level}}`;
  return p.curves[direct]||p.curves[state.sport==='all'&&state.level==='all'?'all|all':(state.sport!=='all'?sportAll:allLevel)]||p.curves['all|all']||null;
}}
function countFor(p){{
  if(state.sport==='all'&&state.level==='all')return p.counts.matches;
  if(state.sport==='all')return p.counts.levels[state.level];
  if(state.level==='all')return p.counts.sports[state.sport];
  return p.counts.combos[`${{state.sport}}|${{state.level}}`].matches;
}}
function chart(curve,compact=false){{
  const w=compact?260:360,h=compact?88:154,left=25,right=6,top=8,bottom=18;
  if(!curve)return '<div class="empty" style="padding:18px">当前筛选暂无路径</div>';
  const X=x=>left+(w-left-right)*x/100,Y=y=>top+(h-top-bottom)*(1-y/100);
  const line=curve.line.map((p,i)=>(i?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)).join(' ');
  const opponent=(curve.opponent&&curve.opponent.line)||curve.line.map(p=>[p[0],100-p[1]]);
  const opponentLine=opponent.map((p,i)=>(i?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)).join(' ');
  const upper=curve.band.map((p,i)=>(i?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[2]).toFixed(1)).join(' ');
  const lower=[...curve.band].reverse().map(p=>'L'+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)).join(' ');
  const grid=[0,25,50,75,100].map(y=>`<line x1="${{left}}" x2="${{w-right}}" y1="${{Y(y)}}" y2="${{Y(y)}}" stroke="${{y===50?'#b8b8bd':'#e3e5e9'}}" stroke-dasharray="${{y===50?'3 3':'0'}}"/><text x="2" y="${{Y(y)+3}}" font-size="8" fill="#9a9aa0">${{y}}c</text>`).join('');
  return `<svg viewBox="0 0 ${{w}} ${{h}}" aria-label="观测方与对手方历史价格路径">${{grid}}<path d="${{upper}} ${{lower}} Z" fill="rgba(10,110,209,.10)"/><path d="${{opponentLine}}" fill="none" stroke="#d88918" stroke-width="${{compact?1.5:1.8}}" stroke-dasharray="${{compact?'4 3':'5 4'}}" stroke-linecap="round" stroke-linejoin="round" opacity=".92"/><path d="${{line}}" fill="none" stroke="#0a6ed1" stroke-width="${{compact?2:2.6}}" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}}
function chartLegend(primary='观测方 · 历史中位',opponent='对手方 · 100c 镜像',showBand=true){{
  return `<span><i class="legend-line"></i>${{esc(primary)}}</span><span><i class="legend-line opponent"></i>${{esc(opponent)}}</span>${{showBand?'<span><i class="legend-line band"></i>25%–75% 区间</span>':''}}`;
}}
function familySummary(){{
  const counts={{}};for(const p of DATA.patterns)counts[p.family]=(counts[p.family]||0)+1;
  document.getElementById('families').innerHTML=DATA.families.map(f=>`<div class="family"><span><i style="background:${{FAMILY_COLORS[f]||'#666'}}"></i>${{esc(f)}}</span><b>${{counts[f]||0}} 种</b></div>`).join('');
}}
function renderCards(){{
  const q=state.query.trim().toLowerCase();
  const shown=DATA.patterns.filter(p=>{{
    const n=countFor(p);if(!n)return false;
    if(!q)return true;
    return [p.title,p.label,p.family,p.summary,p.trigger].join(' ').toLowerCase().includes(q);
  }});
  document.getElementById('visibleCount').textContent=`${{shown.length}} / ${{DATA.patterns.length}} 种有证据`;
  document.getElementById('cards').innerHTML=shown.map(p=>{{
    const curve=curveFor(p),count=countFor(p),fc=FAMILY_COLORS[p.family]||'#666';
    const sportText=DATA.sports.map(s=>`${{s.label}} ${{fmt(p.counts.sports[s.key])}}`).join(' · ');
    const levelText=`整场 ${{fmt(p.counts.levels.series)}} · 小局 ${{fmt(p.counts.levels.game)}}`;
    return `<article class="card" style="--fc:${{fc}}"><div class="card-top"><div class="mark">${{esc(p.mark)}}</div><span class="chip">${{esc(p.family)}}</span></div><h3>${{esc(p.title)}}</h3><div class="tech">${{esc(p.label)}}</div><div class="chart">${{chart(curve)}}</div><div class="chart-legend">${{chartLegend()}}</div><div class="sample-line"><span>当前筛选 ${{fmt(count)}} 场</span><span>曲线 ${{curve?curve.n:0}} 场去重</span></div><div class="split-counts"><div><span>比赛类型 · 去重场数</span><b>${{esc(sportText)}}</b></div><div><span>市场层级 · 去重场数</span><b>${{esc(levelText)}}</b></div></div><p class="desc">${{esc(p.summary)}}</p><details><summary>查看触发、买入与失效结构</summary><div class="detail-grid"><div class="detail-row"><span>触发</span><b>${{esc(p.trigger)}}</b></div><div class="detail-row"><span>买入</span><b>${{esc(p.entry)}}</b></div><div class="detail-row"><span>退出</span><b>${{esc(p.exit)}}</b></div><div class="detail-row"><span>失效</span><b>${{esc(p.invalid)}}</b></div></div></details></article>`;
  }}).join('')||'<div class="empty">当前筛选没有形态证据。</div>';
}}
function renderClusters(){{
  document.getElementById('clusterGroups').innerHTML=DATA.cluster_groups.map(g=>`<section class="cluster-group"><div class="cluster-head"><div><h3>${{esc(g.sport_label)}} · ${{esc(g.level_label)}}</h3><p>${{fmt(g.matches)}} 场参与聚类，拆成 ${{g.clusters.length}} 簇</p></div><span class="chip">单独计算，不跨层级</span></div><div class="cluster-grid">${{g.clusters.map(c=>`<article class="cluster-card"><h4>${{esc(c.name)}}</h4><div class="mini">${{chart({{line:c.curve,band:c.curve.map(p=>[p[0],p[1],p[1]]),opponent:c.opponent}},true)}}</div><div class="chart-legend">${{chartLegend(`观测方 · ${{c.representative_team||'代表侧'}}`,`对手方 · ${{c.representative_opponent||'另一侧'}}`,false)}}</div><div class="cluster-metrics"><span>样本<b>${{fmt(c.size)}} 场 · ${{(c.share*100).toFixed(1)}}%</b></span><span>起点 / 低点<b>${{c.pre.toFixed(0)}}c / ${{c.low.toFixed(0)}}c</b></span><span>回撤 / 反弹<b>${{c.drawdown.toFixed(0)}}c / ${{c.rebound.toFixed(0)}}c</b></span><span>终点<b>${{c.end.toFixed(0)}}c</b></span></div><div class="cluster-labels">${{(c.labels||[]).slice(0,3).map(x=>`<span>${{esc(x.display)}} · ${{x.count}}</span>`).join('')}}</div><div class="sample-line"><span>${{esc(c.representative)}}</span><span>${{esc(c.representative_team)}}</span></div></article>`).join('')}}</div></section>`).join('');
}}
function setButtons(id,key,value){{document.querySelectorAll(`#${{id}} button`).forEach(b=>b.classList.toggle('on',b.dataset[key]===value));}}
document.querySelectorAll('#sportFilter button').forEach(b=>b.onclick=()=>{{state.sport=b.dataset.sport;setButtons('sportFilter','sport',state.sport);renderCards()}});
document.querySelectorAll('#levelFilter button').forEach(b=>b.onclick=()=>{{state.level=b.dataset.level;setButtons('levelFilter','level',state.level);renderCards()}});
document.getElementById('search').oninput=e=>{{state.query=e.target.value;renderCards()}};
familySummary();renderCards();renderClusters();
</script>
</body>
</html>
"""


def render_html(data: dict[str, Any]) -> str:
    """Render the current atlas template with a compact JSON payload."""
    payload = json_script(data)
    template = (ROOT / "tools" / "pattern_atlas.template.html").read_text(encoding="utf-8")
    return (
        template.replace("__ATLAS_DATA__", payload)
        .replace("__FAMILY_COLORS__", json_script(FAMILY_COLORS))
    )


def build(
    dataset_path: Path,
    clusters_path: Path,
    out_path: Path,
    path_index_path: Path = DEFAULT_PATH_INDEX,
) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cluster_data = json.loads(clusters_path.read_text(encoding="utf-8"))
    path_index = build_full_path_index(dataset, path_index_path)
    patterns = pattern_records(dataset, path_index)
    families = [name for name in FAMILY_ORDER if any(row["family"] == name for row in patterns)]
    families.extend(sorted({row["family"] for row in patterns} - set(families)))
    cluster_groups = cluster_records(dataset, cluster_data, path_index)
    cluster_total = sum(len(group["clusters"]) for group in cluster_groups)
    # Make the two research layers navigable in both directions: a formal
    # pattern lists the empirical clusters it appears in, while each cluster
    # points back to its dominant formal label.
    for pattern in patterns:
        refs = []
        for group in cluster_groups:
            for cluster in group["clusters"]:
                match = next(
                    (row for row in cluster.get("labels") or [] if row.get("label") == pattern["label"]),
                    None,
                )
                if match:
                    refs.append({
                        "sport": group["sport"],
                        "sport_label": group["sport_label"],
                        "scope": group["scope"],
                        "level_label": group["level_label"],
                        "name": cluster["name"],
                        "cluster_id": cluster["cluster_id"],
                        "count": int(match.get("count") or 0),
                        "cluster_size": cluster["size"],
                        "share": cluster["share"],
                    })
        pattern["cluster_refs"] = sorted(
            refs,
            key=lambda row: (row["sport"], row["scope"], -row["count"]),
        )
    stats = dataset.get("stats") or {}
    path_summary = path_index.get("summary") or {}
    sport_coverage = {
        key: {
            "label": label,
            "pattern_count": sum(
                1 for pattern in patterns if int(pattern["counts"]["sports"].get(key) or 0) > 0
            ),
            "total": len(patterns),
            "missing": [
                {"label": pattern["label"], "title": pattern["title"]}
                for pattern in patterns
                if int(pattern["counts"]["sports"].get(key) or 0) == 0
            ],
        }
        for key, label in SPORTS
    }
    data = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "source_dataset": str(dataset_path.relative_to(ROOT)) if dataset_path.is_relative_to(ROOT) else str(dataset_path),
        "source_clusters": str(clusters_path.relative_to(ROOT)) if clusters_path.is_relative_to(ROOT) else str(clusters_path),
        "stats": {
            "training_matches": int(stats.get("training_matches") or 0),
            "training_samples": int(stats.get("training_samples") or 0),
            "snapshot_scan": stats.get("snapshot_training_scan") or {},
        },
        "path_coverage": path_summary,
        "sports": [{"key": key, "label": label} for key, label in SPORTS],
        "levels": [{"key": key, "label": label} for key, label in LEVELS],
        "patterns": patterns,
        "families": families,
        "cluster_groups": cluster_groups,
        "cluster_total": cluster_total,
        "sport_coverage": sport_coverage,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(data), encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the named-pattern and empirical-cluster atlas")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--clusters", default=str(DEFAULT_CLUSTERS))
    parser.add_argument("--path-index", default=str(DEFAULT_PATH_INDEX))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)
    data = build(
        Path(args.dataset), Path(args.clusters), Path(args.out), Path(args.path_index)
    )
    print(
        f"[pattern-atlas] {args.out} | patterns={len(data['patterns'])} "
        f"families={len(data['families'])} clusters={data['cluster_total']} "
        f"matches={data['stats']['training_matches']} observations={data['stats']['training_samples']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
