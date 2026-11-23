"""节点页 BP 栏按游戏分口径回归（2026-11-21 固化）。

教训：BP 锚点栏历史上 LoL 硬编码「选人情报/阵容」，CS2 比赛没有选英雄环节、
只有地图禁选，导致 CS2 节点页出现无意义的「阵容」栏。
锁定：
- render_node_page._game_of：slug 首段 -> lol/cs2/dota2（默认 lol）。
- render_node_page._bp：cs2 渲染「地图禁选」、不渲染「阵容」；
  lol/dota2 渲染「阵容」、不渲染「地图禁选」。
- render()：cs2 标题「BP 锚点与地图禁选情报」，lol/dota2「BP 锚点与选人情报」。
- vps_intel_pipeline._node_json_schema：cs2 用 maps 字段，lol/dota2 用 lineup 字段。
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import render_node_page as R
import vps_intel_pipeline as V


def _anchor(**kw) -> dict:
    base = {"type": "正", "content": "弹幕锚点内容", "bp_note": "无战绩情报提及"}
    base.update(kw)
    return base


# ---------- _game_of 分类 ----------

def test_game_of_classification():
    assert R._game_of("cs2-hupu-1441778164564995316") == "cs2"
    assert R._game_of("cs2-iem-katowice-2026") == "cs2"
    assert R._game_of("dota2-ti-2026") == "dota2"
    assert R._game_of("ti-grand-final") == "dota2"
    assert R._game_of("lol-lck-kt-bro") == "lol"
    assert R._game_of("lck-kt-bro") == "lol"  # 无 lol 前缀默认 lol
    assert R._game_of("") == "lol"


# ---------- _bp 按游戏分口径 ----------

def test_bp_cs2_renders_map_veto_not_lineup():
    data = {"bp_anchors": [_anchor(maps="Inferno/Anubis 被禁，选 Mirage", lineup="阿狸")]}
    html = R._bp(data, game="cs2")
    assert "地图禁选" in html
    assert "阵容" not in html


def test_bp_lol_renders_lineup_not_map_veto():
    data = {"bp_anchors": [_anchor(lineup="VicLa 阿狸 / 打野 Vi", maps="Inferno")]}
    html = R._bp(data, game="lol")
    assert "阵容" in html
    assert "地图禁选" not in html


def test_bp_dota2_renders_lineup():
    data = {"bp_anchors": [_anchor(lineup="中单 Puck", maps="Inferno")]}
    html = R._bp(data, game="dota2")
    assert "阵容" in html
    assert "地图禁选" not in html


# ---------- render() 标题分口径 ----------

def test_render_cs2_title_map_veto():
    html = R.render({}, {}, teams=["A", "B"], date="2026-11-21", gi=1, gphase="bp",
                    slug_id="cs2-blast-2026")
    assert "BP 锚点与地图禁选情报" in html
    assert "BP 锚点与选人情报" not in html


def test_render_lol_title_lineup():
    html = R.render({}, {}, teams=["A", "B"], date="2026-11-21", gi=1, gphase="bp",
                    slug_id="lol-lck-kt-bro")
    assert "BP 锚点与选人情报" in html
    assert "BP 锚点与地图禁选情报" not in html


# ---------- 规则层 JSON schema 分口径 ----------

def test_node_json_schema_cs2_uses_maps():
    schema = V._node_json_schema("cs2")
    assert '"maps"' in schema
    assert '"lineup"' not in schema


def test_node_json_schema_lol_uses_lineup():
    schema = V._node_json_schema("lol")
    assert '"lineup"' in schema
    assert '"maps"' not in schema
