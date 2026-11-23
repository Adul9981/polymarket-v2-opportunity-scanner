"""比赛局势注入锚点回归（2026-10-29 固化）。

教训：_inject_situation 原锚点是标题里的「比赛局势（系统注入」，但 Codex 常把
标题里的「（系统注入」丢掉（只输出「比赛局势」），占位正文/注释却仍含「系统注入」
（「系统注入占位：…」/「<!-- 系统注入：… -->」）→ 锚点找不到 → 注入静默跳过 →
已结束比赛的比赛局势栏永久空占位（教训：MKOI-T1 2-0，节点页只显示占位文本）。
修复：锚点改为「系统注入」（占位各格式都含它；注入后真实卡片不含它，天然幂等）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def _prime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    report = tmp_path / "report.html"
    intel_json = tmp_path / "intel.json"
    intel_json.write_text("{}", encoding="utf-8")
    called: list = []

    def fake_card(*a, **k):
        called.append(1)
        return "SITUATION_CARD"

    monkeypatch.setattr(V.render_node_page, "situation_card", fake_card)
    return report, intel_json, called


def test_inject_anchors_on_body_system_inject(tmp_path, monkeypatch):
    """Codex 丢掉标题「（系统注入」，仅正文含「系统注入占位」→ 仍应注入。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<section class="card" aria-labelledby="section-2">'
        '<h2 id="section-2"><span class="no">2</span>比赛局势</h2>'
        '<!-- SITUATION:WIN:BEGIN -->'
        '<div class="system-slot">系统注入占位：两队胜率（弹幕口径·非结论）与虎扑队员评分。AI 不撰写本段。</div>'
        '<!-- SITUATION:WIN:END -->'
        '</section>'
        '<section><h2>3 方向性情报板</h2></section>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["Movistar KOI", "T1"])
    html = report.read_text(encoding="utf-8")
    assert called, "占位含「系统注入」时必须触发注入"
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html, "占位段应被整体替换，不残留「系统注入」"


def test_inject_anchors_on_comment_form(tmp_path, monkeypatch):
    """另一种占位：标题「比赛局势」+「<!-- 系统注入：… -->」注释 → 仍应注入。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<section class="section system-slot" aria-labelledby="section-2">'
        '<h2 id="section-2"><span class="no">2</span>比赛局势</h2>'
        '<!-- 系统注入：两队胜率与虎扑队员评分由规则层注入，本页不生成内容。 -->'
        '</section>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html


def test_inject_anchors_on_old_title(tmp_path, monkeypatch):
    """旧格式：标题「比赛局势（系统注入，本段不写）」→ 仍应注入（向后兼容）。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<section class="card"><h2>2 比赛局势（系统注入，本段不写）</h2></section>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html


def test_inject_anchors_on_article_container(tmp_path, monkeypatch):
    """占位容器用 <article> 而非 <section>（MOUZ-9z/T1-CTBC 教训）→ 仍应注入。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<article class="card"><h2><span class="no">2</span>比赛局势</h2>'
        '<div class="system" id="situation-system">系统注入位：本段仅承载规则层两队胜率…AI 不补写本段。</div>'
        '</article>'
        '<article class="card"><h2><span class="no">3</span>方向性情报板</h2></article>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html
    assert "方向性情报板" in html, "第 3 段不应被误删"


def test_inject_anchors_on_div_card_container(tmp_path, monkeypatch):
    """占位容器用 <div class="card"> 而非 <section>/<article>（KC vs MKOI 教训）→ 仍应注入。

    2026-11-01 修冻结：此前只认 section/article，LoL codex 页漂移成 div.card 后注入静默
    跳过 → 无 WIN/RAT 标记 → refresh_situation 更新不了 → 卡片冻结。
    """
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<div class="card">\n'
        '  <h2><span class="no">2</span>比赛局势</h2>\n'
        '  <p class="note">系统注入：规则层胜率 + 虎扑评分；本段不参与弹幕方向判断。</p>\n'
        '</div>\n'
        '<div class="card"><h2><span class="no">3</span>方向性情报板</h2></div>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["Karmine Corp", "Movistar KOI"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html, "div.card 占位段应被整体替换，不残留「系统注入」"
    assert "方向性情报板" in html, "第 3 段不应被误删"


def test_inject_div_card_with_nested_divs(tmp_path, monkeypatch):
    """div.card 占位含嵌套子 div（winrow/barfill 等）时，匹配闭标签必须按深度计数，
    不能把内层 </div> 当卡片结尾（否则截断卡片、残留孤儿 </div>）。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<div class="card" id="situation-card">\n'
        '  <h2><span class="no">2</span>比赛局势</h2>\n'
        '  <div class="winrow"><div class="winteam">Karmine Corp</div></div>\n'
        '  <p class="note">系统注入：规则层胜率 + 虎扑评分；本段不参与弹幕方向判断。</p>\n'
        '</div>\n'
        '<div class="card"><h2><span class="no">3</span>方向性情报板</h2></div>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["Karmine Corp", "Movistar KOI"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html
    assert "系统注入" not in html
    assert "winrow" not in html, "整个占位卡（含嵌套子 div）应被替换掉，不残留孤儿片段"
    assert "方向性情报板" in html, "第 3 段不应被误删"


def test_inject_idempotent_when_no_placeholder(tmp_path, monkeypatch):
    """已注入页（无「系统注入」）→ 跳过，不再重复注入。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<section class="card"><h2>比赛局势</h2>'
        '<div>两队胜率（观众口径·非结论）</div></section>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    assert not called, "无「系统注入」占位时禁止重复注入"


def test_inject_ignores_system_inject_css_false_positive(tmp_path, monkeypatch):
    """「系统注入」只出现在 <head> 的 CSS .system-slot::before content，body 占位是空
    <div class="system-slot" data-system-inject=…>（2026-11-01 LOS-LYON 空卡教训）→ 必须仍注入。

    旧锚点 html.find("系统注入") 命中 <head> 里的 CSS，找不到外层 <section> 静默跳过。
    """
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<html><head><style>'
        '.system-slot::before{content:"系统注入区（本段不写）"}'
        '</style></head><body>'
        '<section class="card" id="situation">'
        '<h2><span class="no">2</span>比赛局势</h2>'
        '<div class="system-slot" data-system-inject="G2-match-state" aria-live="polite"></div>'
        '</section>'
        '<section class="card"><h2><span class="no">3</span>方向性情报板</h2></section>'
        '</body></html>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["LOS", "LYON"])
    html = report.read_text(encoding="utf-8")
    assert called, "CSS content 假阳性不得阻止注入"
    assert "SITUATION_CARD" in html
    assert "方向性情报板" in html, "第 3 段不应被误删"


def test_inject_data_system_injected_empty_div(tmp_path, monkeypatch):
    """body 占位为 <div class="system-slot" data-system-injected="true"> 空注释
    （2026-11-01 KC-MKOI pre 教训）→ 应注入。"""
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<section class="card">'
        '<h2><span class="no">2</span>比赛局势</h2>'
        '<div class="system-slot" id="situation-slot" data-system-injected="true">'
        '<!-- SITUATION:SYSTEM:BEGIN --><!-- 本段由系统注入，AI 不写。 --><!-- SITUATION:SYSTEM:END -->'
        '</div>'
        '</section>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    html = report.read_text(encoding="utf-8")
    assert called
    assert "SITUATION_CARD" in html


def test_inject_skips_when_card_already_real(tmp_path, monkeypatch):
    """真实卡片（含 WIN/RATINGS 标记、无占位签名）→ 跳过，不重复注入。

    幂等判据 = 卡片容器内无占位签名（data-system-inject / class="system / 系统注入），
    而非「含 WIN/RATINGS 标记」——占位也可能被 codex 包上 WIN 标记（见上面的
    body_system_inject 用例），用标记判幂等会误跳过。
    """
    report, intel_json, called = _prime(tmp_path, monkeypatch)
    report.write_text(
        '<div class="card" id="situation-card">'
        '<h2><span class="no">2</span>比赛局势</h2>'
        '<!-- SITUATION:WIN:BEGIN --><div>胜率条</div><!-- SITUATION:WIN:END -->'
        '<!-- SITUATION:RATINGS:BEGIN --><div>评分</div><!-- SITUATION:RATINGS:END -->'
        '</div>',
        encoding="utf-8",
    )
    V._inject_situation(report, intel_json, None, ["A", "B"])
    assert not called, "真实卡片不含占位签名时禁止重复注入"
