import json
import time
from pathlib import Path

import danmu_intel
import danmu_live_monitor


def row(text: str, source: str = "official_660000") -> dict:
    return {"ts": time.time(), "nick": "tester", "uid": 1, "text": text, "source": source}


def test_empty_capture_is_sample_insufficient():
    intel = danmu_intel.analyze([])
    assert intel["meta"]["total"] == 0
    assert intel["meta"]["sample_status"] == "insufficient"
    assert intel["gray_signals"]["count"] == 0


def test_gray_signal_ignores_ad_room_noise():
    intel = danmu_intel.analyze([row("接广告了"), row("小卖部开门")])
    assert intel["gray_signals"]["count"] == 0


def test_gray_signal_keeps_qualified_audience_doubt():
    intel = danmu_intel.analyze([row("这波像在演"), row("观众说卡盘了")])
    assert intel["gray_signals"]["count"] == 2


def test_today_team_aliases_are_covered():
    intel = danmu_intel.analyze(
        [row("WBG这波很强"), row("LNG落后了"), row("GEN打得稳"), row("KT这波送了")]
    )
    assert {"WBG", "LNG", "GEN", "KT"}.issubset(intel["teams"])


def test_dota_ti2026_aliases_and_situation_are_covered():
    intel = danmu_intel.analyze(
        [
            row("Iron Wing这波守高"),
            row("雪碧拿盾准备上高地"),
            row("bzm没买活"),
            row("拉尔和崩溃这波配合很强"),
        ]
    )
    assert {"Iron Wing", "Spirit"}.issubset(intel["teams"])
    assert {"bzm", "Larl", "Collapse"}.issubset(intel["players"])
    assert intel["situation"]["count"] == 3


def test_dota_generic_child_word_does_not_match_cs_player():
    intel = danmu_intel.analyze([row("我的兄弟小孩想夺冠有点难")])
    assert "m0NESY" not in intel["players"]


def test_short_team_code_does_not_match_inside_word():
    intel = danmu_intel.analyze([row("this is a big mistake")])
    assert "IG" not in intel["teams"]


def test_multi_input_loader_adds_source_and_skips_partial_line(tmp_path: Path):
    path = tmp_path / "2026-08-19_mile_149361.jsonl"
    path.write_text(json.dumps({"ts": 1, "nick": "n", "text": "GEN强"}) + "\n{", encoding="utf-8")
    rows = danmu_live_monitor.load_rows([path])
    assert len(rows) == 1
    assert rows[0]["source"] == "mile_149361"


def test_soop_rows_are_normalized_to_text_nick(tmp_path: Path):
    path = tmp_path / "2026-08-24_soop_afchall.jsonl"
    path.write_text(
        json.dumps({"ts": "2026-08-24T13:03:31+0800", "nickname": "봉준성태", "message": "아 정글러야?"})
        + "\n",
        encoding="utf-8",
    )
    rows = danmu_live_monitor.load_rows([path])
    assert len(rows) == 1
    assert rows[0]["text"] == "아 정글러야?"
    assert rows[0]["nick"] == "봉준성태"
    assert rows[0]["source"] == "soop_afchall"
    # analyze_deep must not crash on SOOP-shaped rows
    deep = danmu_intel.analyze_deep(rows)
    assert "gray" in deep or "themes" in deep


def test_empty_health_page_warns_instead_of_claiming_no_signal():
    html = danmu_live_monitor.render_page(
        danmu_intel.analyze([]),
        danmu_intel.analyze_deep([]),
        "测试",
        "2026-08-19 15:00:00",
        [{"source": "remember_528222", "state": "live_waiting_danmaku", "message_count": 0}],
    )
    assert "样本不足" in html
    assert "不能输出“无信号”结论" in html
    assert "已开播·等待弹幕" in html
