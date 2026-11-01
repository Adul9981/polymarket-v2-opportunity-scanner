"""_inject_situation 占位符替换回归（2026-10-26 固化）。

锁定本次修复的两个错误：
  1. 幂等判断曾用 `if "比赛局势" in html: return`——占位符标题
     「比赛局势（系统注入，本段不写）」也含"比赛局势"，导致 codex 节点页
     从未真正注入、页面空占位符（教训：Liquid-Legacy 等 42 个节点页空栏）；
  2. 注入是"插入到第 3 段前"而非"替换占位符 <section>"，会残留占位符与重复块。
"""

from __future__ import annotations

import json
from pathlib import Path

import render_node_page
import vps_intel_pipeline as vp


def _placeholder(slot_div: str = '<div class="system-slot" id="match-situation" data-system-inject="match-situation">') -> str:
    return (
        '<div class="container">\n'
        '  <section class="card">\n'
        '    <h2><span class="no">1</span>BP 锚点与选人情报</h2>\n'
        '    <div>bp 内容</div>\n'
        '  </section>\n'
        '  <section class="card">\n'
        '    <h2><span class="no">2</span>比赛局势（系统注入，本段不写）</h2>\n'
        f'    {slot_div}\n'
        '      <strong>系统注入区</strong>\n'
        '      <span>本段由规则层填充。</span>\n'
        '    </div>\n'
        '  </section>\n'
        '  <section class="card">\n'
        '    <h2><span class="no">3</span>方向性情报板</h2>\n'
        '    <div>方向内容</div>\n'
        '  </section>\n'
        '</div>\n'
    )


def _write_intel(tmp_path: Path) -> Path:
    p = tmp_path / "intel.json"
    stats = {
        "win_signal": {
            "sample_status": "ready",
            "team_a": "Alpha",
            "team_b": "Beta",
            "pct_a": 60,
            "pct_b": 40,
            "total": 10,
            "threshold": 10,
            "basis": "recent",
            "window_seconds": 300,
        }
    }
    p.write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    return p


def _inject(tmp_path: Path, html: str) -> Path:
    report = tmp_path / "report.html"
    report.write_text(html, encoding="utf-8")
    vp._inject_situation(report, _write_intel(tmp_path), None, ["Alpha", "Beta"])
    return report


def test_placeholder_replaced_with_real_card(tmp_path):
    report = _inject(tmp_path, _placeholder())
    html = report.read_text(encoding="utf-8")
    assert "系统注入" not in html                 # 占位符已替换
    assert "比赛局势" in html                      # 真实卡片标题在
    assert render_node_page._WIN_BEGIN in html    # 胜率子块标记在
    assert "方向性情报板" in html                  # 第 3 段未受影响


def test_placeholder_variant_bare_slot(tmp_path):
    # 无 data-system-inject 属性的漂移变体（g2 页实测）也要能替换
    report = _inject(tmp_path, _placeholder('<div class="system-slot">'))
    html = report.read_text(encoding="utf-8")
    assert "系统注入" not in html
    assert render_node_page._WIN_BEGIN in html


def test_no_duplicate_section(tmp_path):
    report = _inject(tmp_path, _placeholder())
    html = report.read_text(encoding="utf-8")
    assert html.count("比赛局势") == 1            # 替换而非插入，无重复标题
    assert html.count("<section") == 2           # 占位符 section 被 div 替换，剩 1/3 两段


def test_idempotent_second_call_noop(tmp_path):
    report = _inject(tmp_path, _placeholder())
    html1 = report.read_text(encoding="utf-8")
    vp._inject_situation(report, _write_intel(tmp_path), None, ["Alpha", "Beta"])
    html2 = report.read_text(encoding="utf-8")
    assert html1 == html2                        # 已注入后再次调用不改变


def test_no_placeholder_skipped(tmp_path):
    html = '<div class="card"><h2><span class="no">2</span>比赛局势</h2></div>'
    report = tmp_path / "report.html"
    report.write_text(html, encoding="utf-8")
    vp._inject_situation(report, _write_intel(tmp_path), None, ["Alpha", "Beta"])
    assert report.read_text(encoding="utf-8") == html  # 无占位符，原样不动
