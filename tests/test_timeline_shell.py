"""时间轴壳 aria-pressed 回归（2026-10-25 固化）。

锁定 bug：`build_timeline_shell` 曾把 `aria-pressed="true"` 设在 `views` 第 0 项
（`i == 0`），而第 0 项排序后恒是 G1·BP后 的占位（无 data-src，disabled），导致
回填场（只有"系列复盘"、无小局节点）时唯一可点按钮拿不到 aria-pressed，
iframe 空载 -> 用户看到"内容为空"（教训：TES-AL 10-25 回填后页面空白）。
修复后 aria-pressed 落在首个"有 data-src"的节点上。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


@pytest.fixture()
def reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """临时 REPORTS 目录，隔离真实 reports/。"""
    monkeypatch.setattr(V, "REPORTS", tmp_path)
    return tmp_path


def _shell(reports: Path, mid: str) -> str:
    return (reports / f"match_{mid}.html").read_text(encoding="utf-8")


def test_series_review_only_autoloads(reports: Path):
    """只有整场复盘、无小局节点时，系列复盘按钮必须 aria-pressed=true（自动加载）。"""
    mid = "lol-hupu-1693138568019968"
    (reports / "intel_danmu_TES-AL_2026-10-25.html").write_text("<p>系列复盘</p>", encoding="utf-8")
    V.build_timeline_shell(mid, ["TES", "AL"], "LoL 其他", "2026-10-25", max_games=5)
    html = _shell(reports, mid)
    assert 'data-src="intel_danmu_TES-AL_2026-10-25.html" aria-pressed="true"' in html
    # 占位按钮不得带 aria-pressed（disabled，无 data-src）
    assert 'disabled style="opacity:.5' in html


def test_first_game_node_autoloads(reports: Path):
    """有 G1 BP 节点时，首个可用节点（G1 BP）拿 aria-pressed，而非更后面的系列复盘。"""
    mid = "lol-hupu-1693138568019968"
    (reports / "intel_danmu_TES-AL_2026-10-25_g1_bp.html").write_text("<p>G1 BP</p>", encoding="utf-8")
    (reports / "intel_danmu_TES-AL_2026-10-25.html").write_text("<p>系列复盘</p>", encoding="utf-8")
    V.build_timeline_shell(mid, ["TES", "AL"], "LoL 其他", "2026-10-25", max_games=5)
    html = _shell(reports, mid)
    assert 'data-src="intel_danmu_TES-AL_2026-10-25_g1_bp.html" aria-pressed="true"' in html
    assert 'data-src="intel_danmu_TES-AL_2026-10-25.html" aria-pressed="true"' not in html


def test_empty_match_marks_no_danmaku_source(reports: Path):
    """无任何节点文件时，壳必须显式标注「本场暂无弹幕情报」，不得再用
    9 个「此节点暂未采集数据」占位按钮。
    （教训 2026-10-25：BETBOOM vs Nemiga / Vitality vs The MongolZ 19:00 国际
    CS2 场次 KICK 源故障 + 中文解说未覆盖，0 弹幕；旧占位语义含糊，且旧早退
    让陈旧占位壳残留在线。）"""
    mid = "cs2-hupu-1441778164564995314"
    out = V.build_timeline_shell(mid, ["BETBOOM", "Nemiga"], "CS2", "2026-10-25", max_games=3)
    assert out.exists()
    html = _shell(reports, mid)
    assert "本场暂无弹幕情报" in html
    assert "无可用弹幕源" in html
    assert "此节点暂未采集数据" not in html
    assert '<iframe id="view"' not in html
