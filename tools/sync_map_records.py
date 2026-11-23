#!/usr/bin/env python3
"""CS2 队伍×地图战绩台账同步（2026-09-08 建立）。

目的：把"每场打了哪张图、谁赢、比分"从单场结果里结构化出来，累计成
队伍×地图的官方战绩，供队伍画像/地图战绩页/BP 情报引用。

输入（按可信度）：
  1. docs/data/intel/official/official_matches.json 中 game=cs2 且带 maps 的官方记录；
  2. docs/data/intel/matches.json 中 result_inferred 带官方标记
     （官方/HLTV/Liquipedia/BLAST/Polymarket 结算）且逐图比分可确认的场次。

可确认规则（宁可少、不可错）：
  - 官方逐图记录（含 maps[]）直接入；
  - 横扫 2:0/3:0/1:0：所打地图胜者 = 系列胜者；
  - 文本显式给出地图胜者（如 "Anubis 13:7 Aurora"、"G1 LVG 13:10 Dust2"）直接入；
  - 其余（如 2:1 无显式胜者的分数串）不入，等官方逐图源回填。

用法：
  python3 tools/sync_map_records.py                # 扫描并重写 map_records.json
  python3 tools/sync_map_records.py --print        # 只打印当前台账
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTEL = ROOT / "docs" / "data" / "intel"
OUT = INTEL / "map_records.json"
OFFICIAL = INTEL / "official" / "official_matches.json"
MATCHES = INTEL / "matches.json"
TEAM_NAMES = INTEL / "team_names.json"

# 地图英文 ID 与别名（按官方图池）
MAP_ALIASES: dict[str, list[str]] = {
    "anubis": ["anubis"],
    "ancient": ["ancient", "远古遗迹", "遗迹"],
    "cache": ["cache", "叉车", "核子危机?"],
    "dust2": ["dust2", "dust ii", "dust 2", "沙二", "沙漠2"],
    "inferno": ["inferno", "炼狱小镇·inferno", "小镇", "炼狱小镇"],
    "mirage": ["mirage", "米垃圾", "荒漠迷城"],
    "nuke": ["nuke", "核子危机", "核子"],
    "overpass": ["overpass", "死亡游乐园"],
    "train": ["train", "列车"],
    "vertigo": ["vertigo", "殒命大厦"],
    "mills": ["mills"],
    "thera": ["thera"],
    "basalt": ["basalt"],
}

_MAP_TOKEN = "|".join(
    sorted(
        {
            tok
            for toks in MAP_ALIASES.values()
            for tok in toks
            if tok.isascii()
        },
        key=len,
        reverse=True,
    )
)
# 英文 token 太长放正则前避免歧义（Cache/Cobblestone 等），直接内联。
_MAP_RE = re.compile(
    rf"(?<![a-z0-9])(?:{_MAP_TOKEN}|train|vertigo|mills|thera|basalt)(?![a-z0-9])",
    re.I,
)

OFFICIAL_MARK = re.compile(
    r"官方|Liquipedia|HLTV|BLAST|blast\.tv|Polymarket 结算|Polymarket结算|finished|战报",
    re.I,
)


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def norm_team(name: str) -> str:
    """队伍名 -> 规范 abbr（team_names 优先；未登记保留原名小写 key）。"""
    raw = str(name or "").strip()
    low = raw.lower()
    try:
        rows = load_json(TEAM_NAMES).get("teams", [])
    except Exception:  # noqa: BLE001
        rows = []
    best = None
    for t in rows:
        keys = [
            t.get("abbr", ""), t.get("full", ""), t.get("name", ""),
            t.get("id", ""), *t.get("aliases", []),
        ]
        for k in keys:
            if str(k).strip().lower() == low:
                best = t.get("abbr") or raw
                break
        if best:
            break
    return best or raw


def canon_map(token: str) -> str | None:
    low = token.lower().strip()
    for mid, toks in MAP_ALIASES.items():
        if low in [t.lower() for t in toks]:
            return mid
    # 无别名直接命中英文 token 的兜底
    return low if low.isascii() and re.fullmatch(r"[a-z0-9_\- ]+", low) else None


def map_wins_from_text(team_a: str, team_b: str, text: str,
                       series_winner: str | None) -> list[dict]:
    """从 result_inferred 中提取可确认的逐图记录。

    只接受三种可确认写法：
      a) 横扫（系列胜者 X:0，文本无显式胜者队）-> 每图胜者=系列胜者；
      b) "<胜者队> <score> <图>"（队名在分数前，如 "G1 LVG 13:10 Dust2"）；
      c) "<图> <score> <胜者队>"（队名在分数后，如 "Anubis 13:7 Aurora"）。
    2:1 且无显式胜者的分数串不解析（等官方逐图回填），防止把输图算成赢图。
    """
    if not OFFICIAL_MARK.search(text):
        return []
    if re.search(r"进行中|未结算|待官方|暂停", text, re.I):
        return []
    out: list[dict] = []
    esc_a, esc_b = re.escape(team_a), re.escape(team_b)
    # b) 队名 → 分数 → 图名
    p_b = re.compile(
        rf"(?i)(?:{esc_a}|{esc_b})\s+(\d{{1,2}})\s*[:：\-]\s*(\d{{1,2}})\s+(?:{_MAP_TOKEN})"
    )
    # c) 图名 → 分数 → 队名
    p_c = re.compile(
        rf"(?i)(?:{_MAP_TOKEN})\s+(\d{{1,2}})\s*[:：\-]\s*(\d{{1,2}})\s+(?:{esc_a}|{esc_b})"
    )
    explicit: dict[str, dict] = {}
    for mm in p_b.finditer(text):
        _mt = _MAP_RE.search(mm.group(0))
        map_id = canon_map(_mt.group(0)) if _mt else None
        if not map_id:
            continue
        # 队名已由分组识别
        who = re.search(rf"(?i)({esc_a}|{esc_b})", mm.group(0)).group(1)
        wa, wb = int(mm.group(1)), int(mm.group(2))
        if wa == wb:
            continue
        explicit[map_id] = {
            "map": map_id,
            "winner": who,
            "score_a": wa if who == team_a else wb,
            "score_b": wb if who == team_a else wa,
        }
    for mm in p_c.finditer(text):
        _mt = _MAP_RE.search(mm.group(0))
        map_id = canon_map(_mt.group(0)) if _mt else None
        if not map_id:
            continue
        who = re.search(rf"(?i)({esc_a}|{esc_b})", mm.group(0)).group(1)
        wa, wb = int(mm.group(1)), int(mm.group(2))
        if wa == wb:
            continue
        explicit.setdefault(map_id, {
            "map": map_id,
            "winner": who,
            "score_a": wa if who == team_a else wb,
            "score_b": wb if who == team_a else wa,
        })
    if explicit:
        return list(explicit.values())
    # a) 横扫：整场 X:0，文本未显式标单图胜者 -> 每图归系列胜者
    if not series_winner:
        return []
    if not re.search(rf"(?i){re.escape(series_winner)}\s+\d+[:：-]0", text):
        return []
    for mm in _MAP_RE.finditer(text):
        after = text[mm.end():]
        score = re.search(r"(\d{1,2})\s*[:：\-]\s*(\d{1,2})", after)
        if not score:
            continue
        map_id = canon_map(mm.group(0))
        if not map_id:
            continue
        wa, wb = int(score.group(1)), int(score.group(2))
        if wa == wb:
            continue
        out.append({
            "map": map_id,
            "winner": series_winner,
            "score_a": wa if series_winner == team_a else wb,
            "score_b": wb if series_winner == team_a else wa,
        })
    return out


def _series_winner_of(teams: list[str], result: str) -> str | None:
    for t in teams:
        if re.search(rf"(?i){re.escape(t)}\s+\d\s*[:：]\s*0", result):
            return t
    return None


def collect_records() -> list[dict]:
    recs: list[dict] = []
    # 1) official_matches.json（最高可信）
    try:
        off = load_json(OFFICIAL).get("matches", [])
    except Exception:  # noqa: BLE001
        off = []
    for m in off:
        if m.get("game") != "cs2" or not m.get("maps"):
            continue
        mid = m.get("match_id", "")
        date = (m.get("confirmed_ts") or "")[:10]
        # match_id 形如 2026-08-23_ewc_cs2_final_spirit_fut，尝试拆队伍
        tails = [x for x in mid.split("_") if x]
        for i in range(len(tails) - 1):
            if tails[i] == "cs2" and i + 2 <= len(tails) - 1:
                pass
        # 直接使用 maps 里的 winner，队伍名从 winner/loser 反推不可靠时用官方字段
        for mp in m["maps"]:
            if not mp.get("winner"):
                continue
            map_id = canon_map(str(mp.get("map", ""))) or str(mp.get("map", "")).lower()
            # 队伍：maps 记录内可能带 team 字段；没有则从结果串解析
            # 此处先只收能确定双方的（result 形如 "A 3:1 B"）
            rm = re.search(
                r"^([A-Za-z0-9_. ]+?)\s+\d+\s*[:：]\s*\d+\s+([A-Za-z0-9_. ]+)$",
                str(m.get("result", "")),
            )
            if not rm:
                continue
            a, b = rm.group(1).strip(), rm.group(2).strip()
            winner = norm_team(mp["winner"])
            wa, wb = (1, 0) if winner == norm_team(a) else (0, 1)
            # 比分还原
            sc = re.search(r"(\d{1,2})-(\d{1,2})", str(mp.get("score", "")))
            if sc:
                if winner == norm_team(a):
                    wa, wb = int(sc.group(1)), int(sc.group(2))
                else:
                    wb, wa = int(sc.group(1)), int(sc.group(2))
            recs.append({
                "match_id": mid,
                "date": date,
                "event": str(m.get("league", "")),
                "map": map_id,
                "team_a": norm_team(a),
                "team_b": norm_team(b),
                "score_a": wa,
                "score_b": wb,
                "winner": winner,
                "source": str(m.get("source", "official_matches.json")),
                "verified": True,
            })
    # 2) matches.json 台账（仅官方标记且能确认胜者的场次）
    try:
        mj = load_json(MATCHES).get("matches", [])
    except Exception:  # noqa: BLE001
        mj = []
    for m in mj:
        mid = str(m.get("id") or m.get("slug") or "")
        if not str(mid).startswith("cs2"):
            continue
        teams = m.get("teams") or []
        if len(teams) != 2:
            continue
        result = str(m.get("result_inferred") or "")
        if not result or not OFFICIAL_MARK.search(result):
            continue
        raw_a, raw_b = str(teams[0]).strip(), str(teams[1]).strip()
        a, b = norm_team(raw_a), norm_team(raw_b)
        winner_series = _series_winner_of([a, b], result)
        for mp in map_wins_from_text(raw_a, raw_b, result, winner_series):
            recs.append({
                "match_id": mid,
                "date": str(m.get("date", ""))[:10],
                "event": str(m.get("league", "")),
                "map": mp["map"],
                "team_a": norm_team(raw_a),
                "team_b": norm_team(raw_b),
                "score_a": mp["score_a"],
                "score_b": mp["score_b"],
                "winner": norm_team(mp["winner"]),
                "source": "matches.json result_inferred（官方标记）",
                "verified": True,
            })
    # 去重（match_id+map）
    seen: set[tuple[str, str]] = set()
    out = []
    for r in recs:
        k = (r["match_id"], r["map"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    out.sort(key=lambda r: (r.get("date", ""), r.get("match_id", ""), r.get("map", "")))
    return out


def aggregate(records: list[dict]) -> dict[str, dict[str, dict]]:
    stats: dict[str, dict[str, dict]] = {}
    for r in records:
        for side in (r["team_a"], r["team_b"]):
            st = stats.setdefault(side, {}).setdefault(r["map"], {
                "played": 0, "wins": 0, "losses": 0,
                "last_date": "", "recent": [],
            })
            st["played"] += 1
            if side == r["winner"]:
                st["wins"] += 1
            else:
                st["losses"] += 1
            d = r["date"]
            if d and d > st["last_date"]:
                st["last_date"] = d
            if d and d not in st["recent"]:
                st["recent"].append(d)
    for team in stats:
        for mp in stats[team]:
            st = stats[team][mp]
            st["recent"] = sorted(st["recent"], reverse=True)[:8]
            st["winrate"] = round(st["wins"] / st["played"], 4) if st["played"] else None
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="同步 CS2 队伍×地图官方战绩台账")
    ap.add_argument("--print", action="store_true", help="只打印不写盘")
    args = ap.parse_args()
    recs = collect_records()
    stats = aggregate(recs)
    doc = {
        "schema_version": "1.0",
        "description": (
            "CS2 队伍×地图官方战绩（2026-09-08 建立）：records=逐场逐图胜负（仅官方可确认），"
            "team_map_stats=按队伍×地图聚合（场次/胜/负/胜率/最近日期）。"
            "事实层只信官方/Liquipedia/HLTV/官方标记台账；弹幕强图口径仍在 maps.json 的 anchors。"
        ),
        "updated_at": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "records": recs,
        "team_map_stats": stats,
    }
    if args.print:
        print(json.dumps(doc, ensure_ascii=False, indent=1))
        return 0
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    n_map = len(recs)
    teams = sorted(stats)
    print(f"[map_records] wrote {OUT}: {n_map} map-records, {len(teams)} teams")
    for t in teams[:15]:
        maps = stats[t]
        parts = [
            f"{k} {v['wins']}W-{v['losses']}L ({round(v['wins']/v['played']*100) if v['played'] else 0}%)"
            for k, v in sorted(maps.items())
        ]
        print(f"  {t}: " + " · ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
