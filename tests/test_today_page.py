"""今日情报页规范回归（2026-08-25 锁定，头号防错对象）。

用户定调：今日情报页是"网站架构与显示"最典型的问题，绝对不能反复发生。
任何改动若静默破坏：统一导航 / 状态 / 明日预告 / 首页公告位置 /
详情壳嵌入模式 / 付费墙边界，都会在此测试中失败。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".danmu_intel_site"
TODAY_JSON = ROOT / "runtime" / "intel_today.json"


def test_today_page_has_exactly_one_unified_nav() -> None:
    p = SITE / "intel" / "today.html"
    t = p.read_text(encoding="utf-8")
    navs = re.findall(r"<nav[^>]*>", t)
    assert len(navs) == 1, f"today.html nav={len(navs)}"
    # 禁止生成器旧导航残留（class="inner" 是旧模板特征）
    assert 'class="inner"' not in t, "today.html 残留旧模板导航"
    # 统一导航必须有完整内联样式 + 当前页高亮
    assert 'color:#0071e3;font-weight:700;font-size:13px;text-decoration:none"' in t
    assert "弹幕情报库</a>" in t


def test_today_page_has_breadcrumb_and_embed_once() -> None:
    p = SITE / "intel" / "today.html"
    t = p.read_text(encoding="utf-8")
    assert t.count("首页</a> ›") == 1, "today.html 面包屑异常"
    assert t.count('location.search.indexOf("embed=1")') <= 1


def test_today_page_has_tomorrow_preview() -> None:
    p = SITE / "intel" / "today.html"
    t = p.read_text(encoding="utf-8")
    assert "明日预告" in t, "今日页缺少明日预告区块"


def test_intel_today_json_no_stale_matches() -> None:
    if not TODAY_JSON.exists():
        return
    d = json.loads(TODAY_JSON.read_text(encoding="utf-8"))
    today = d.get("date", "")
    stale = []
    for m in d.get("matches", []):
        md = m.get("date", "")
        if md and md < today and str(m.get("status", "")).lower() not in (
            "started_recently_or_live", "live", "in_progress",
        ):
            stale.append((md, m.get("slug")))
    assert not stale, f"今日页混入已结束旧比赛: {stale[:5]}"


def test_homepage_notice_is_before_hero() -> None:
    t = (SITE / "index.html").read_text(encoding="utf-8")
    i_notice = t.find('id="notice"')
    i_hero = t.find('class="hero"')
    assert i_notice != -1 and i_hero != -1
    assert i_notice < i_hero, "案例公告应位于首页顶部（hero 之前）"


def test_homepage_today_links_to_today_page() -> None:
    t = (SITE / "index.html").read_text(encoding="utf-8")
    assert 'href="intel/today.html"' in t
    assert 'id="today"' in t


def test_match_shells_use_embed_mode() -> None:
    bad = []
    for p in (SITE / "intel").glob("match_*.html"):
        t = p.read_text(encoding="utf-8")
        if "<iframe" not in t:
            continue  # 非时间轴壳（无 iframe）不检查
        if '?embed=1' not in t and '&embed=1' not in t:
            bad.append(p.name)
    assert not bad, f"详情壳未启用嵌入模式: {bad[:5]}"


def test_no_shell_has_broken_buttons() -> None:
    """时间轴壳按钮必须指向真实且互不重复的节点页。

    教训 2026-08-25：壳按队伍名硬拼文件名（BFX.Y vs BFXY）导致按钮
    `__none__` 或全部指向同一整场页——节点情报"同一份"假象。
    """
    bad = []
    for p in (SITE / "intel").glob("match_*.html"):
        t = p.read_text(encoding="utf-8")
        if 'class="nbtn"' not in t:
            continue
        btns = re.findall(r'class="nbtn" data-src="([^"]+)"', t)
        if not btns:
            continue
        if "__none__" in btns:
            bad.append(f"{p.name}: __none__")
        elif len(btns) != len(set(btns)):
            bad.append(f"{p.name}: 重复按钮")
    assert not bad, bad[:8]


def test_match_list_uses_unified_wording() -> None:
    """比赛列表/情报入口统一用词"情报"，禁止"多节点/复盘/详情"混用。"""
    today = (SITE / "intel" / "today.html").read_text(encoding="utf-8")
    assert "今日情报" in today
    assert "情报详情" not in today
    hist = (SITE / "intel" / "history.html").read_text(encoding="utf-8")
    assert ">情报</a>" in hist
    assert "多节点</a>" not in hist and "复盘</a>" not in hist


def test_history_lists_node_breakdown_or_none() -> None:
    """历史列表：有情报的比赛按小局/节点列明细，无情报的标"暂无"（高优先级 2026-08-25）。"""
    hist = (SITE / "intel" / "history.html").read_text(encoding="utf-8")
    assert "暂无" in hist, "历史列表应有'暂无'标记"
    assert "G1·情报" in hist or "赛前" in hist, "历史列表应展示小局/节点明细"
    # 已知有情报的比赛不应被标"暂无"
    rows = re.findall(r'<div class="row".*?</div>', hist, flags=re.S)
    for row in rows:
        for known in ("GIANTX vs G2 Esports", "Natus Vincere vs Fnatic", "BFX.Y vs HLE.C"):
            if known in row:
                assert "暂无" not in row, f"{known} 被误标暂无"
