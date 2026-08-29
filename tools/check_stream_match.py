#!/usr/bin/env python3
"""直播内容匹配校验（2026-08-26 用户定稿，切赛识别主信号）。

三信号：时间窗预匹配 + 弹幕内容队伍提及校验 + 主播行为画像加权。
用于切片/分析前判定某直播源某时段是否在播目标比赛；不匹配 -> 标"疑似切赛"。

用法：
  python3 tools/check_stream_match.py --match lol-drxc-foxy-2026-08-25 \
      --input <jsonl> [--streamer 硕硕]
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "docs" / "data" / "intel" / "team_names.json"
PROFILES = ROOT / "docs" / "data" / "intel" / "streamer_profiles.json"


def load_team_keywords() -> tuple[dict[str, set[str]], dict[str, str]]:
    """(队伍->关键词集, 归一关键词->队伍id)。"""
    kw: dict[str, set[str]] = {}
    norm_map: dict[str, str] = {}
    if not REG.exists():
        return kw, norm_map
    try:
        for t in json.loads(REG.read_text(encoding="utf-8")).get("teams", []):
            keys = {t["abbr"], t["full"], *t.get("aliases", [])}
            norm = set()
            for k in keys:
                v = str(k).strip()
                if len(v) >= 2:
                    norm.add(v)
                    norm_map.setdefault(re.sub(r"[.\s]", "", v).lower(), t["id"])
            kw[t["id"]] = norm
    except Exception:  # noqa: BLE001
        pass
    return kw, norm_map


def _hit(keyword: str, low_text: str, norm_text: str) -> bool:
    """ASCII 词边界匹配；韩文/中文子串匹配；2 字母缩写不参与内容判定（防误命中）。"""
    kw = keyword.lower()
    if re.search(r"[a-z0-9]", kw):
        if len(kw) <= 2:
            return False
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", low_text))
    return kw in norm_text


def match_info(slug: str) -> dict:
    """从 matches.json / settlements 取比赛信息（teams/start/end）。"""
    for p in (ROOT / "docs" / "data" / "intel" / "matches.json", ROOT / "runtime" / "settlements.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            rows = d.get("matches", []) if "matches" in d else list(d.get("settlements", {}).values())
            for m in rows:
                if str(m.get("id") or m.get("slug") or "") == slug or str(m.get("slug") or "") == slug:
                    return m
        except Exception:  # noqa: BLE001
            continue
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True)
    ap.add_argument("--input", required=True, help="弹幕 jsonl（text/message 字段）")
    ap.add_argument("--streamer", default="")
    ap.add_argument("--start", default="", help="比赛开始 ISO（缺省读 matches.json）")
    ap.add_argument("--end", default="", help="比赛结束 ISO")
    args = ap.parse_args()

    info = match_info(args.match)
    teams = info.get("teams") or []
    start_raw = args.start or info.get("start_time") or info.get("startDate") or ""
    end_raw = args.end or info.get("end_time") or ""
    if len(teams) != 2:
        print(json.dumps({"error": f"未找到比赛 {args.match} 的队伍信息"}, ensure_ascii=False))
        return 2

    kw, norm_map = load_team_keywords()

    def norm_team(t: str) -> str:
        v = re.sub(r"[.\s]", "", str(t).lower())
        if v in norm_map:
            return norm_map[v]
        return v

    ta, tb = norm_team(teams[0]), norm_team(teams[1])
    match_hits = {ta: 0, tb: 0}
    other_hits: dict[str, int] = {}
    n = 0
    t0 = t1 = None
    try:
        with open(args.input, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = str(r.get("text") or r.get("message") or "")
                ts = r.get("unixtime") or r.get("ts") or ""
                try:
                    ts_f = float(ts) if isinstance(ts, (int, float)) else float(ts)
                except (ValueError, TypeError):
                    ts_f = 0
                if ts_f:
                    t0 = ts_f if t0 is None else min(t0, ts_f)
                    t1 = ts_f if t1 is None else max(t1, ts_f)
                if not text:
                    continue
                n += 1
                low = text.lower()
                norm = re.sub(r"[.\s]", "", low)
                # 每条弹幕只归一次类：先判本场（含家族队别名重叠），再判其他队
                hit_match = any(
                    any(_hit(k, low, norm) for k in kw.get(tid, set()))
                    for tid in (ta, tb)
                )
                if hit_match:
                    match_hits[ta] += 1
                    continue
                for tid, keys in kw.items():
                    if tid in (ta, tb):
                        continue
                    if any(_hit(k, low, norm) for k in keys):
                        other_hits[tid] = other_hits.get(tid, 0) + 1
    except OSError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 2

    mh = match_hits[ta] + match_hits[tb]
    oh = sum(other_hits.values())
    total = mh + oh
    ratio = mh / total if total else 0.0

    # 时间窗
    window_ok = True
    if start_raw and t0:
        try:
            st = datetime.datetime.fromisoformat(str(start_raw).replace("Z", "+00:00")).timestamp()
            if t1 and t1 < st - 3600:
                window_ok = False
        except ValueError:
            pass

    # 主播画像加权
    follow_rate = None
    if args.streamer and PROFILES.exists():
        try:
            for p in json.loads(PROFILES.read_text(encoding="utf-8")).get("profiles", []):
                if p.get("streamer") == args.streamer and p.get("follow_rate") is not None:
                    follow_rate = float(p["follow_rate"])
                    break
        except Exception:  # noqa: BLE001
            pass

    if n == 0:
        verdict, note = "empty", "该时段无弹幕样本"
    elif total < 5:
        verdict, note = "pending", f"队伍提及稀疏（{total} 条），待核"
        if follow_rate is not None and follow_rate >= 0.8:
            verdict, note = "matched_lowconf", f"提及稀疏但主播跟随率高({follow_rate:.2f})，低置信并入·待核"
    elif ratio >= 0.5:
        verdict, note = "matched", f"本场队伍提及占比 {ratio:.0%}（{mh}/{total}）"
    else:
        top_other = max(other_hits.items(), key=lambda kv: kv[1]) if other_hits else ("", 0)
        verdict, note = "mismatch", (
            f"本场队伍占比仅 {ratio:.0%}（{mh}/{total}），疑似指向其他场次"
            f"（最高其他队 {top_other[0]}: {top_other[1]} 条）"
        )

    out = {
        "match": args.match,
        "teams": teams,
        "streamer": args.streamer or "",
        "rows": n,
        "window_ok": window_ok,
        "match_mentions": mh,
        "other_mentions": oh,
        "ratio": round(ratio, 3),
        "follow_rate": follow_rate,
        "verdict": verdict,
        "note": note,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
