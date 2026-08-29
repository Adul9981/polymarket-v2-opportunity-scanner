#!/usr/bin/env python3
"""Verify whether a danmaku window really signals a match END (防误判).

2026-08-19 教训：零散弹幕（"A队两图晋级了""魔术队赢FUT不意外"）可能是
预测/玩梗，不是结果。本工具对"候选结束时刻"做多信号打分：
  1) 结束语密度（GG/恭喜/拿下/2-0/2:1 等，末段连续分钟内的条数与用户数）
  2) 流量骤降（结束后的分钟密度 vs 峰值密度，<10% 才算）
  3) 比分/图数陈述核对（显式"X 2:0 Y"式陈述数量）
分数 <3 一律输出"未确认（进行中）"，不当作结果。

Usage:
  python3 tools/verify_match_end.py --input docs/data/danmu/huya/xxx.jsonl \
      --end "2026-08-19T23:30:00+08:00" --teams "Astralis,G2"
"""

from __future__ import annotations

import argparse
import datetime
import json
from collections import Counter
from pathlib import Path


END_KW = ["gg", "恭喜", "拿下", "结束了", "2:0", "2-0", "2:1", "2-1", "晋级了", "出局了", "夺冠了", "收下比赛", "结束比赛"]
PREDICT_KW = ["要赢", "必", "不意外", "就离谱", "该赢", "有说法", "感觉", "看好", "应该", "了吧", "吗", "?"]


def parse_ts(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.datetime.fromisoformat(str(value).replace("+0800", "+08:00")).timestamp()
    except ValueError:
        return None


def row_ts(row: dict) -> float | None:
    if row.get("unixtime"):
        return float(row["unixtime"])
    return parse_ts(row.get("ts"))


def load_rows(paths: list[str]) -> list[dict]:
    rows = []
    for p in paths:
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True)
    ap.add_argument("--end", required=True, help="候选结束时刻（本地 ISO）")
    ap.add_argument("--teams", default="", help="对阵，如 Astralis,G2")
    ap.add_argument("--window-min", type=int, default=15, help="回溯窗口（分钟）")
    ap.add_argument("--drop-min", type=int, default=5, help="流量骤降观察分钟数")
    args = ap.parse_args()

    end_ts = parse_ts(args.end)
    if end_ts is None:
        print("ERR: 无法解析 --end")
        return
    rows = [r for r in load_rows(args.input) if (t := row_ts(r)) is not None]
    rows = [r for r in rows if row_ts(r) <= end_ts + args.drop_min * 60]
    rows.sort(key=row_ts)
    if not rows:
        print("未确认（进行中）：窗口内无数据")
        return

    start_ts = end_ts - args.window_min * 60
    window = [r for r in rows if row_ts(r) >= start_ts]
    last2 = [r for r in window if row_ts(r) >= end_ts - 120]
    teams = [t.strip().lower() for t in args.teams.split(",") if t.strip()]

    end_hits = []
    for r in last2:
        t = (r.get("text") or "").strip()
        if not t:
            continue
        low = t.lower()
        if any(k in low for k in END_KW) and not any(p in t for p in PREDICT_KW):
            end_hits.append((r.get("nick") or r.get("user_id") or "?", t))

    score = 0
    detail = []
    if len(end_hits) >= 10:
        score += 1
        detail.append(f"结束语 ≥10 条（实际 {len(end_hits)}）")
    users = len({n for n, _ in end_hits})
    if users >= 5:
        score += 1
        detail.append(f"共识用户 ≥5 人（实际 {users}）")

    # 流量骤降：结束后的密度 vs 窗口峰值
    minute_count = Counter(int(row_ts(r) // 60) for r in window)
    peak = max(minute_count.values()) if minute_count else 0
    tail_ts = end_ts + args.drop_min * 60
    tail = [r for r in rows if end_ts < row_ts(r) <= tail_ts]
    tail_min = max((tail_ts - end_ts) / 60, 1)
    tail_density = len(tail) / tail_min
    if peak > 0 and tail_density < peak * 0.1:
        score += 1
        detail.append(f"流量骤降（峰值 {peak}/分 → 结束后续 {tail_density:.0f}/分）")

    # 显式比分陈述（"X 2:0 Y"式）在末段的数量
    score_claims = [r for r in last2 if any(f"{t} 2:0" in (r.get("text") or "").lower() or f"{t} 2-0" in (r.get("text") or "").lower() for t in teams)]
    if len(score_claims) >= 5:
        score += 1
        detail.append(f"显式比分陈述 ≥5 条（实际 {len(score_claims)}）")

    verdict = "确认结束" if score >= 3 else ("需人工确认" if score >= 2 else "未确认（进行中）")
    print(f"评分 {score}/4 | 判定：{verdict}")
    for d in detail:
        print("  +", d)
    if end_hits:
        print("结束语样本（前 5）:")
        for n, t in end_hits[:5]:
            print("  ", n[:10], "|", t[:60])


if __name__ == "__main__":
    main()
