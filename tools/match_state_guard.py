#!/usr/bin/env python3
"""Match result declaration guard (结果判定门禁 · 2026-08-25).

防止"把进行中/刚开赛/弹幕情绪误判为已结束"——任何复盘页/结果结论
在落库或发布前必须过本门禁。对应教训：
  - FNC-NAVI G1：英文弹幕反讽（"FNC ARE BACK"/"HOLY FNC"）被当庆祝，
    误判 FNC 1-0（实际 NAVI 1-0）→ 反讽识别 + 结构源优先；
  - GX-G2 与 CS2：刚开赛被弹幕闲聊词误判"已结束" → 时间门槛；
  - 比分机器滞后：结构源时间戳早于弹幕结束信号 → 降级"待确认"。

判定规则（全部通过才允许 declared=ended）：
  1. 时间门槛：now < start_utc + MIN_ELAPSED → not_started / too_early，
     禁止输出"已结束"；
  2. 结构源优先：只有 scorebot / official / standings 确认才可 ended；
     仅弹幕证据 → pending_official；
  3. 比分源滞后：scorebot 时间戳早于弹幕结束信号 → lag=True，结果降级；
  4. 反讽识别：英文弹幕命中反讽模式 → 该证据不作胜者判定；
  5. 时区安全：全部用 UTC epoch 比较，展示层才转北京时间。

Usage:
  python3 tools/match_state_guard.py --teams "GX,G2" \
      --start "2026-08-25T17:00:00+00:00" --now "2026-08-25T18:40:00+00:00" \
      --scorebot "2026-08-25T18:07:10+00:00:G2 1-0 GX" \
      --danmaku "2026-08-25T18:08:11+00:00:gg G2 win"
"""

from __future__ import annotations

import argparse
import datetime
import re
from dataclasses import dataclass, field

MIN_ELAPSED_MINUTES = 30  # 比赛开始至少 30 分钟才允许判定结束
LAG_TOLERANCE_MINUTES = 5  # 比分源比弹幕结束信号晚 5 分钟内视为正常，不构成滞后

# 英文 Twitch 弹幕反讽/玩梗模式（命中即不作胜者证据）
IRONIC_PATTERNS = [
    r"\b(?:ARE BACK|IS BACK)\b",
    r"\bHOLY [A-Z]",
    r"\bplaying well\.\.? mhm\b",
    r"\bWINS AGAIN\b",
    r"\b(?:LO|LUL|KEKW|OMEGALUL|xdd)\s*$",
    r"\b(?:GOAT|WASHED|FRAUD)\b",
    r"\?{2,}",
    # 英文俚语 vs 战队名歧义（KT-BRO G1 教训：OKBRO/bro tax 等是聊天梗，
    # 不是 BRO 战队信号）
    r"\b(?:OK ?BRO|bro tax|BROLIEVERS|BROOOO+|ok bro)\b",
]
IRONIC_RE = re.compile("|".join(IRONIC_PATTERNS), re.IGNORECASE)
# BO3 系列终结比分（2-0 / 0-2 / 2-1 / 1-2）；1-0 / 1-1 只是局末不是系列终局
SERIES_FINAL_RE = re.compile(r"\b(?:2-\d|\d-2)\b")


def parse_ts(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class Verdict:
    status: str  # not_started | too_early | live | ended | pending_official
    reasons: list[str] = field(default_factory=list)
    structure_confirmed: bool = False
    scorebot_lag: bool = False
    sarcasm_flags: list[str] = field(default_factory=list)

    @property
    def can_declare_ended(self) -> bool:
        return self.status == "ended" and self.structure_confirmed and not self.sarcasm_flags


def guard(
    start: datetime.datetime,
    now: datetime.datetime,
    scorebot_lines: list[tuple[datetime.datetime, str]] | None = None,
    danmaku_end_signals: list[tuple[datetime.datetime, str]] | None = None,
    standings_final: bool = False,
) -> Verdict:
    scorebot_lines = scorebot_lines or []
    danmaku_end_signals = danmaku_end_signals or []

    if now < start:
        return Verdict("not_started", reasons=["当前时间早于开赛时间（UTC 比较）"])

    elapsed = (now - start).total_seconds() / 60
    if elapsed < MIN_ELAPSED_MINUTES:
        return Verdict(
            "too_early",
            reasons=[
                f"比赛开始仅 {elapsed:.0f} 分钟，未达 {MIN_ELAPSED_MINUTES} 分钟门槛；"
                "禁止判定已结束（教训：GX-G2 刚开赛被误判结束）"
            ],
        )

    # 比分源滞后检测：结构源时间戳显著早于弹幕结束信号（> 容差）
    lag = False
    if scorebot_lines and danmaku_end_signals:
        last_structure_ts = max(ts for ts, _ in scorebot_lines)
        last_danmaku_ts = max(ts for ts, _ in danmaku_end_signals)
        lag = (last_structure_ts + datetime.timedelta(minutes=LAG_TOLERANCE_MINUTES)) < last_danmaku_ts

    # 结构源（比分机器/官方/积分榜）是否确认"系列最终结果"
    series_final_lines = [text for _, text in scorebot_lines if SERIES_FINAL_RE.search(text)]
    structure_confirm = bool(series_final_lines) or standings_final
    if not structure_confirm:
        reasons = [
            "无结构源确认系列终局（需 2-0/2-1 类终局比分或官方积分榜）；"
            "1-0/1-1 仅为局末，或仅弹幕证据 → 只能标'待官方确认'，"
            "禁止单凭弹幕情绪定胜负（教训：FNC-NAVI G1）"
        ]
        if lag:
            reasons.append("比分源显著早于弹幕结束信号（>5 分钟）→ 比分源滞后")
        return Verdict(
            "pending_official",
            reasons=reasons,
            scorebot_lag=lag,
        )

    # 反讽识别：命中即该证据不可作胜者判定
    sarcasm_flags = []
    for ts, text in danmaku_end_signals:
        if IRONIC_RE.search(text):
            sarcasm_flags.append(f"{ts.isoformat(timespec='seconds')}: {text[:60]}")

    status = "ended"
    reasons = [f"结构源确认系列终局（{len(series_final_lines)} 条终局比分行/积分榜）"]
    if lag:
        status = "pending_official"
        reasons.append("比分源时间戳早于弹幕结束信号 → 比分源滞后，降级'待官方确认'")
    if sarcasm_flags:
        status = "pending_official"
        reasons.append(f"弹幕命中反讽模式 {len(sarcasm_flags)} 条，不可作胜者证据")

    return Verdict(
        status=status,
        reasons=reasons,
        structure_confirmed=structure_confirm,
        scorebot_lag=lag,
        sarcasm_flags=sarcasm_flags[:5],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="结果判定门禁")
    ap.add_argument("--start", required=True, help="开赛时间（UTC ISO，如 2026-08-25T17:00:00+00:00）")
    ap.add_argument("--now", required=True, help="当前时间（UTC ISO）")
    ap.add_argument("--scorebot", action="append", default=[], help="TS:文本（比分机器/官方确认行，可重复）")
    ap.add_argument("--danmaku", action="append", default=[], help="TS:文本（弹幕结束信号，可重复）")
    ap.add_argument("--standings-final", action="store_true", help="官方积分榜已确认该场结果")
    args = ap.parse_args()

    scorebot = []
    for item in args.scorebot:
        ts, _, text = item.partition(":")
        scorebot.append((parse_ts(ts), text))
    danmaku = []
    for item in args.danmaku:
        ts, _, text = item.partition(":")
        danmaku.append((parse_ts(ts), text))

    v = guard(parse_ts(args.start), parse_ts(args.now), scorebot, danmaku, args.standings_final)
    print(f"status: {v.status}")
    print(f"can_declare_ended: {v.can_declare_ended}")
    for r in v.reasons:
        print(f"  - {r}")
    for s in v.sarcasm_flags:
        print(f"  [反讽] {s}")
    return 0 if v.can_declare_ended else 1


if __name__ == "__main__":
    raise SystemExit(main())
