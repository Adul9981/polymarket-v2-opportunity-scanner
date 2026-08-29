"""Site framework regression: unified nav / breadcrumb / favicon on every page.

锁定 SITE_FRAMEWORK_STANDARD.md：每页恰好 1 个导航、1 条面包屑（非首页）、
1 个 favicon 引用、无 ../intel/ 错误链接；注入脚本幂等。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".danmu_intel_site"


def _pages():
    return [p for p in SITE.rglob("*.html")]


def _key(p: Path) -> str:
    return str(p.relative_to(SITE))


def test_every_page_has_exactly_one_nav() -> None:
    bad = []
    for p in _pages():
        n = len(re.findall(r"<nav[^>]*>", p.read_text(encoding="utf-8")))
        if n != 1:
            bad.append(f"{p.name}: nav={n}")
    assert not bad, bad[:10]


def test_nav_links_have_complete_inline_style() -> None:
    """导航链接必须完整内联样式（text-decoration:none + 固定字号/字重），
    禁止继承各页面 CSS 导致下划线/字号/加粗不统一（教训 2026-08-25）。"""
    bad = []
    for p in _pages():
        t = p.read_text(encoding="utf-8")
        for m in re.finditer(r'<nav[^>]*>.*?</nav>', t, re.S):
            nav = m.group(0)
            for a in re.findall(r'<a href="[^"]*"[^>]*>', nav):
                is_brand = "margin-right:auto" in a
                want_size = "font-size:14px" if is_brand else "font-size:13px"
                if "text-decoration:none" not in a or want_size not in a:
                    bad.append(f"{p.name}: {a[:70]}")
    assert not bad, bad[:8]


def test_every_page_has_breadcrumb_except_home() -> None:
    bad = []
    for p in _pages():
        if p.name in ("index.html", "404.html"):
            continue
        n = p.read_text(encoding="utf-8").count("首页</a> ›")
        if n != 1:
            bad.append(f"{p.name}: crumb={n}")
    assert not bad, bad[:10]


def test_every_page_has_favicon() -> None:
    bad = []
    for p in _pages():
        if 'rel="icon"' not in p.read_text(encoding="utf-8"):
            bad.append(p.name)
    assert not bad, bad[:10]


def test_body_top_padding_unified() -> None:
    """导航上方留白 + 基础排版统一：body 必须 padding-top:0 且 SF Pro 字体栈
    （参照今日比赛页观感，教训 2026-08-25）。"""
    bad = []
    for p in _pages():
        m = re.search(r"<body[^>]*>", p.read_text(encoding="utf-8"))
        if not m or "padding-top:0" not in m.group(0) or "SF Pro Text" not in m.group(0):
            bad.append(p.name)
    assert not bad, bad[:10]


def test_no_stale_intel_links() -> None:
    bad = []
    for p in (SITE / "intel").glob("*.html"):
        if 'href="../intel/' in p.read_text(encoding="utf-8"):
            bad.append(p.name)
    assert not bad, bad[:10]


def test_paywall_tier_boundary() -> None:
    """免费/付费边界（2026-08-25）：赛后复盘/壳/画像/灰信号/痕迹免费；
    实时/赛前节点（_pre/_live/_BP_/G1/G2）付费锁定。"""
    def has_pw(name: str) -> bool:
        p = SITE / "intel" / name
        return p.exists() and "danmu_member_v1" in p.read_text(encoding="utf-8")

    free_pages = [
        "match_2026-08-22_we_lgd.html",
        "intel_danmu_WE-LGD_2026-08-22.html",
        "intel_profile_team_t1.html",
        "intel_gray_signals_stats.html",
        "verification_traces.html",
    ]
    pro_pages = [
        "intel_danmu_QUAZAR-Nemiga_2026-08-24_live_0109.html",
    ]
    for f in free_pages:
        assert not has_pw(f), f"{f} 应为免费"
    for f in pro_pages:
        assert has_pw(f), f"{f} 应为付费"


def test_page_key_legacy_league_prefix_sorted() -> None:
    """旧文件名（LEC-FNC-NAVI_G1）剥联赛前缀 + 队伍排序后，
    与结算名单（顺序相反）映射到同一 key（2026-08-26 修复）。
    教训：该页已结束却仍被付费墙锁定。"""
    from add_paywall import _norm_team, page_key

    assert page_key("intel_danmu_LEC-FNC-NAVI_G1_2026-08-24.html") == "2026-08-24|fnc-navi"
    # 结算名单是 Natus Vincere vs Fnatic（顺序相反），归一后 key 相同
    teams = ["Natus Vincere", "Fnatic"]
    key = f"2026-08-24|{'-'.join(sorted([_norm_team(teams[0]), _norm_team(teams[1])]))}"
    assert key == "2026-08-24|fnc-navi"
    assert page_key("intel_danmu_KC-SHFT_BP_2026-08-24.html") == "2026-08-24|kc-shft"


def test_nav_injection_is_idempotent() -> None:
    import subprocess
    import sys

    # 先规范化一次（吸收历史残留），再验证后续运行不产生变化
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "add_site_nav.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    first = {_key(p): p.read_text(encoding="utf-8") for p in _pages()}
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "add_site_nav.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    changed = [_key(p) for p in _pages() if p.read_text(encoding="utf-8") != first.get(_key(p))]
    assert not changed, f"nav injection not idempotent: {changed[:5]}"


def test_embed_script_at_most_once() -> None:
    """嵌入模式脚本每页最多 1 份（教训 2026-08-25：重复注入叠加成多份）。"""
    bad = []
    for p in _pages():
        n = p.read_text(encoding="utf-8").count('location.search.indexOf("embed=1")')
        if n > 1:
            bad.append(f"{p.name}: embed={n}")
    assert not bad, bad[:10]


def test_case_page_follows_standard() -> None:
    """案例公告页必须符合 CASE_STANDARD.md 五段结构（2026-08-25 固化）。"""
    p = SITE / "intel" / "case_gx_g2_2026-08-24.html"
    t = p.read_text(encoding="utf-8")
    for section in ("情报库提示", "赔率变化", "灰信号汇总", "双方临场", "纪律声明"):
        assert section in t, f"案例页缺标准章节: {section}"
    assert (ROOT / "tools" / "templates" / "case_page_template.html").exists(), "缺案例页模板"
    assert (ROOT / "docs" / "task" / "CASE_STANDARD.md").exists(), "缺案例标准文档"
