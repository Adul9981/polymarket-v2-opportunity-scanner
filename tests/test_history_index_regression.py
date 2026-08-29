"""Regression tests locking the league-classification standard + history index integrity.

Guards AGENTS.md 防错规则 12 (intel linking) and the 2026-08-24 league
classification standard: allowed labels, no unknown labels, no pending results,
and every referenced page exists in the site.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SITE_INTEL = ROOT / ".danmu_intel_site" / "intel"
ALLOWED = {"LPL", "LCK", "LCK CL", "LEC", "LCP", "KeSPA Cup", "LoL 其他", "CS2", "Dota2", "Valorant"}

# 与 tools/build_history_index.py 保持单一来源（防错：索引键归一化口径一致，
# 避免别名/正则副本漂移——教训 2026-08-26：测试缺 bfxy/hlec/krxc 别名导致误报未关联）。
sys.path.insert(0, str(ROOT / "tools"))
from build_history_index import MATCH_FILE_RE, AGGREGATE_TEAMS, SPECIAL_FILES, norm_team  # noqa: E402

AGGREGATE = AGGREGATE_TEAMS


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads((ROOT / "docs/data/intel/match_index.json").read_text(encoding="utf-8"))


def test_league_labels_are_standard(index) -> None:
    for m in index["matches"]:
        assert m["league"] in ALLOWED, f"{m['date']} {m['teams']}: bad league {m['league']}"


def test_no_unknown_labels(index) -> None:
    bad = [m for m in index["matches"] if m["league"] in ("其他", "-")]
    assert not bad, f"unknown league labels: {bad}"


def test_no_pending_results(index) -> None:
    pend = [m for m in index["matches"] if not m.get("result")]
    assert not pend, f"results pending: {pend}"


def test_referenced_pages_exist(index) -> None:
    for m in index["matches"]:
        if m.get("report"):
            assert (SITE_INTEL / m["report"]).exists(), f"missing report {m['report']}"
        if m.get("detail"):
            assert (SITE_INTEL / m["detail"]).exists(), f"missing shell {m['detail']}"


def test_market_links_page_has_slugs() -> None:
    page = (SITE_INTEL / "market_links.html").read_text(encoding="utf-8")
    assert "polymarket.com/event/" in page


def test_suffixed_node_reports_are_visible(index) -> None:
    """防错规则 12：带 BP/G1/G2/full/S0 后缀的节点报告必须进历史库。

    2026-08-24 曾漏掉 KC-SHFT（4 个节点报告全带后缀）、T1-HLE（S0）、
    KC-GX（G1/full）；修复后这些场次必须出现在索引里。
    """
    rows = {(m["date"], frozenset(norm_team(t) for t in m["teams"])) for m in index["matches"]}
    expect = {
        ("2026-08-24", frozenset(norm_team(t) for t in ["KC", "SHFT"])),
        ("2026-08-23", frozenset(norm_team(t) for t in ["T1", "HLE"])),
        ("2026-08-18", frozenset(norm_team(t) for t in ["KC", "GX"])),
        # 特殊文件名（中文昵称）映射：CS-绿龙-Legacy = Spirit vs Legacy
        ("2026-08-23", frozenset(norm_team(t) for t in ["Spirit", "Legacy"])),
    }
    assert expect <= rows, f"历史库漏关联: {expect - rows}"


def test_every_match_page_is_linked(index) -> None:
    """防错规则 12：站点里每个可解析的单场情报页都必须有历史库条目。"""
    rows = {(m["date"], frozenset(norm_team(t) for t in m["teams"])) for m in index["matches"]}
    unlinked = []
    for f in SITE_INTEL.glob("intel_danmu_*.html"):
        if f.name in SPECIAL_FILES:
            continue  # 特殊文件由 SPECIAL_FILES 显式映射，跳过正则判定
        m = MATCH_FILE_RE.match(f.name)
        if not m:
            continue
        a, b, date = norm_team(m.group(1)), norm_team(m.group(2)), m.group(3)
        if a in AGGREGATE or b in AGGREGATE:
            continue
        if (date, frozenset((a, b))) not in rows:
            unlinked.append(f.name)
    assert not unlinked, f"情报页未关联历史库: {unlinked}"
