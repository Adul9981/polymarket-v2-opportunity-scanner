"""虎扑跨午夜场次漏入今日清单回归（2026-10-30 固化）。

教训：BLG vs TES（中国内战，无 Polymarket 市场）仅靠虎扑补漏，但
export_today_matches 用 UTC 本地日期（VPS 是 UTC）比对虎扑北京日期，
跨午夜场次（23:00 UTC 开赛 = 北京次日 07:00）被漏出今日清单。
锁定：虎扑 date 过滤必须按北京时间换算，并带"北京昨天"窗口覆盖跨午夜，
不得把北京"明天"的未来场次也拉进来。
"""

from __future__ import annotations

import datetime

import export_today_matches as em


def _utc(*a: int) -> datetime.datetime:
    return datetime.datetime(*a, tzinfo=datetime.timezone.utc)


def test_hupu_window_cross_midnight_includes_beijing_next_day():
    # UTC 深夜 23:30（北京已是次日 07:30）→ 窗口须含北京"次日"
    win = em.hupu_date_window(_utc(2026, 10, 29, 23, 30, 0))
    assert "2026-10-30" in win  # BLG vs TES 的虎扑 date
    assert "2026-10-29" in win  # 北京昨天窗口兜底


def test_hupu_window_does_not_include_beijing_future():
    # 不得把北京"明天"的场次也拉进今日清单（防过度纳入未来场次）
    win = em.hupu_date_window(_utc(2026, 10, 29, 23, 30, 0))
    assert "2026-10-31" not in win


def test_hupu_window_beijing_midnight_spanning():
    # 北京本地跨午夜（UTC 16:00 = 北京 00:00）→ 北京日期已翻到次日，窗口含昨天覆盖进行中场次
    win = em.hupu_date_window(_utc(2026, 10, 30, 16, 0, 0))
    assert "2026-10-31" in win
    assert "2026-10-30" in win


def test_hupu_window_daytime_matches_utc_date():
    # 北京时间白天（UTC 08:00 = 北京 16:00），北京日期与 UTC 日期同一天
    win = em.hupu_date_window(_utc(2026, 10, 30, 8, 0, 0))
    assert "2026-10-30" in win
    assert "2026-10-29" in win


def test_merge_hupu_adds_cross_midnight_lol_match():
    # BLG-TES 复现场景：虎扑 date=北京次日，start_iso=UTC 前一天深夜
    rows = [
        {
            "league": "LOL",
            "tournament": "全球总决赛瑞士轮",  # 非 LCK/LPL/LEC/LCP，不被 _hupu_is_official_lol 跳过
            "teams": ["BLG", "TES"],
            "hupu_match_id": "123456",
            "date": "2026-10-30",
            "start_iso": "2026-10-29T23:00:00Z",
            "status": "live",
        }
    ]
    out = em.merge_hupu(rows, [])
    assert len(out) == 1
    m = out[0]
    assert m["id"] == "lol-hupu-123456"  # 游戏前缀防止混源
    assert m["closed"] is False


def test_hupu_window_utc_previous_day_start_enters():
    # G2 vs HLE 场景：UTC 10-31 00:30（北京 10-31 08:30），比赛 UTC 10-30 23:00 开赛
    # （北京 10-31 07:00），虎扑 date 字段 = 北京当天 10-31。
    win = em.hupu_date_window(_utc(2026, 10, 31, 0, 30, 0))
    assert "2026-10-31" in win  # 虎扑 date（北京当天）
    assert "2026-10-30" in win  # 北京昨天兜底，覆盖 UTC 昨天深夜开赛仍在进行的场次


def test_merge_hupu_attaches_score_key_to_existing_official_lol():
    # 官方 LoL 场次（KC vs MKOI）已在 out（Polymarket/official 源），虎扑赛程里也有同一场
    # （LEC 官方联赛，本会被 _hupu_is_official_lol 跳过新增）——必须按队伍名反查把虎扑
    # 评分 key 补挂到已有场次，让官方 LCK/LPL/LEC/LCP 场次也能出选手评分（2026-11-01 修）。
    existing = {
        "id": "lol-kc-mkoi-2026-10-31",
        "slug": "lol-kc-mkoi-2026-10-31",
        "league": "LoL",
        "teams": ["Karmine Corp", "Movistar KOI"],
        "start_time": "2026-10-31T17:00:00Z",
        "closed": False,
    }
    out = [existing]
    rows = [
        {
            "league": "LOL",
            "tournament": "LEC",  # 官方联赛，本会被跳过新增
            "teams": ["KC", "MKOI"],  # 别名写法，_team_key 归一化后与全名一致
            "hupu_match_id": "777777",
            "date": "2026-10-31",
            "start_iso": "2026-10-31T17:00:00Z",
            "status": "live",
            "score_item_key": {"out_biz_no": "SCORE_123", "out_biz_type": "1"},
            "member_ids": ["a", "b"],
        }
    ]
    out2 = em.merge_hupu(rows, out)
    assert len(out2) == 1  # 不新增行（同一场）
    assert out2[0]["hupu_score_out_biz_no"] == "SCORE_123"  # 评分 key 补挂到位
    assert out2[0]["hupu_score_out_biz_type"] == "1"
    assert out2[0]["hupu_member_ids"] == ["a", "b"]


def test_merge_hupu_does_not_overwrite_existing_score_key():
    # 已挂过评分 key 的场次不重复覆盖（幂等）
    existing = {
        "id": "lol-kc-mkoi-2026-10-31",
        "slug": "lol-kc-mkoi-2026-10-31",
        "league": "LoL",
        "teams": ["Karmine Corp", "Movistar KOI"],
        "start_time": "2026-10-31T17:00:00Z",
        "closed": False,
        "hupu_score_out_biz_no": "SCORE_OLD",
    }
    rows = [
        {
            "league": "LOL",
            "tournament": "LEC",
            "teams": ["KC", "MKOI"],
            "hupu_match_id": "777777",
            "date": "2026-10-31",
            "start_iso": "2026-10-31T17:00:00Z",
            "status": "live",
            "score_item_key": {"out_biz_no": "SCORE_NEW", "out_biz_type": "2"},
            "member_ids": ["x"],
        }
    ]
    out2 = em.merge_hupu(rows, [existing])
    assert len(out2) == 1
    assert out2[0]["hupu_score_out_biz_no"] == "SCORE_OLD"  # 不覆盖已有 key


def test_merge_hupu_utc_previous_day_start_enters():
    # G2 vs HLE 教训：start_iso 是 UTC（昨天深夜），date 是北京（今天），
    # merge_hupu 不得因 date/start_iso 日期错位拒绝该场；窗口判定由上层 hupu_date_window 负责。
    rows = [
        {
            "league": "LOL",
            "tournament": "全球总决赛瑞士轮",  # 非 LCK/LPL/LEC/LCP，不被官方覆盖跳过
            "teams": ["Hanwha Life Esports", "G2 Esports"],
            "hupu_match_id": "999999",
            "date": "2026-10-31",  # 北京当天
            "start_iso": "2026-10-30T23:00:00Z",  # UTC 昨天深夜
            "status": "live",
        }
    ]
    out = em.merge_hupu(rows, [])
    assert len(out) == 1
    assert out[0]["id"] == "lol-hupu-999999"
    assert out[0]["start_time"] == "2026-10-30T23:00:00Z"  # start_time 保留 UTC，date 仅作北京窗口判定
