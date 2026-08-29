"""Regression tests for the result declaration guard (防重犯机制).

锁定 2026-08-25 全部教训：
  E1 刚开赛（<30 分钟）被弹幕误判"已结束"（GX-G2 / CS2 教训）→ too_early
  E2 仅弹幕情绪、无结构源 → pending_official，禁止定胜负（FNC-NAVI G1 教训）
  E3 英文弹幕反讽不可作胜者证据（"FNC ARE BACK / HOLY FNC"）→ sarcasm_flags
  E4 比分源滞后（结构源早于弹幕结束信号）→ 降级 pending_official
  E5 结构源确认 + 无反讽 → 允许 declared=ended（正常路径不误伤）
  E6 跨时区安全：UTC 比较，北京时间展示不参与判定
"""

from __future__ import annotations

import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from match_state_guard import guard, IRONIC_RE  # noqa: E402


def dt(iso: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(iso)


def test_e1_just_started_cannot_be_ended():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T17:20:00+00:00")  # 开赛仅 20 分钟
    danmaku = [(dt("2026-08-25T17:18:00+00:00"), "gg 结束了 拿下 2-0")]
    v = guard(start, now, danmaku_end_signals=danmaku, standings_final=True)
    assert v.status == "too_early"
    assert not v.can_declare_ended


def test_e2_danmaku_only_cannot_declare_winner():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T18:40:00+00:00")
    danmaku = [(dt("2026-08-25T18:38:00+00:00"), "gg G2 win")]
    v = guard(start, now, danmaku_end_signals=danmaku)  # 无结构源
    assert v.status == "pending_official"
    assert not v.can_declare_ended
    assert not v.structure_confirmed


def test_e3_sarcasm_flags_english_danmaku():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T18:40:00+00:00")
    danmaku = [
        (dt("2026-08-25T18:33:00+00:00"), "HOLY FNC"),
        (dt("2026-08-25T18:33:00+00:00"), "FNC ARE BACK"),
        (dt("2026-08-25T18:33:00+00:00"), "FNC is playing well.. mhm"),
    ]
    v = guard(start, now, danmaku_end_signals=danmaku, standings_final=True)
    assert v.sarcasm_flags
    assert v.status == "pending_official"
    assert not v.can_declare_ended


def test_e4_scorebot_lag_downgrades():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T18:40:00+00:00")
    scorebot = [(dt("2026-08-25T18:07:00+00:00"), "G2 1-0 GX")]  # 旧比分
    danmaku = [(dt("2026-08-25T18:38:00+00:00"), "gg GX win 1-1")]
    v = guard(start, now, scorebot_lines=scorebot, danmaku_end_signals=danmaku)
    assert v.scorebot_lag
    assert v.status == "pending_official"
    assert not v.can_declare_ended


def test_e5_clean_structure_confirmation_passes():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T18:40:00+00:00")
    scorebot = [(dt("2026-08-25T18:39:00+00:00"), "G2 1-2 GX")]  # 系列终局比分
    danmaku = [(dt("2026-08-25T18:39:30+00:00"), "gg")]
    v = guard(start, now, scorebot_lines=scorebot, danmaku_end_signals=danmaku)
    assert v.status == "ended"
    assert v.can_declare_ended


def test_e5b_game_level_score_1_1_is_not_series_final():
    start = dt("2026-08-25T17:00:00+00:00")
    now = dt("2026-08-25T18:40:00+00:00")
    scorebot = [(dt("2026-08-25T18:39:00+00:00"), "G2 1-1 GX")]  # 局末非终局
    danmaku = [(dt("2026-08-25T18:39:30+00:00"), "gg")]
    v = guard(start, now, scorebot_lines=scorebot, danmaku_end_signals=danmaku)
    assert v.status == "pending_official"
    assert not v.can_declare_ended


def test_e6_utc_comparison_not_bj_time():
    # 北京时间 01:00 开赛 = UTC 17:00；若误用北京时钟比较会差 8 小时
    start = dt("2026-08-25T17:00:00+00:00")  # 01:00 北京时间
    now_utc = dt("2026-08-25T17:20:00+00:00")  # 01:20 北京
    v = guard(start, now_utc)
    assert v.status == "too_early"
    # 同一天北京 01:20 对应 UTC 17:20，绝不允许按 UTC 日期 08-25 就判"已结束"


def test_sarcasm_regex_common_patterns():
    for text in ["FNC ARE BACK", "HOLY FNC", "FNC is playing well.. mhm", "NAVI WINS AGAIN"]:
        assert IRONIC_RE.search(text), text
