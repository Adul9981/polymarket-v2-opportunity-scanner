"""节点页标题区 CSS 钉死回归（2026-11-01 固化）。

教训：Codex 每个节点页独立生成，prompt 只写「系统字体栈」约束不住，h1 字号/字体族/字重
随模型漂移（KC-MKOI 同一场次各节点页 h1 为 26px / clamp(25..35px) / clamp(32..54px），
队名标题忽大忽小）。修复：_pin_header_css 后注入固定覆盖样式（!important）到 </head> 前，
使所有节点页标题区一致；幂等（canonical-header 标记）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import vps_intel_pipeline as V


def test_pin_overrides_drifting_h1(tmp_path):
    report = tmp_path / "r.html"
    report.write_text(
        "<html><head><style>"
        "body{font-family:-apple-system,'Microsoft YaHei',sans-serif}"
        "h1{font-size:clamp(32px,6vw,54px)}"
        "</style></head><body><h1>Karmine Corp vs Movistar KOI</h1></body></html>",
        encoding="utf-8",
    )
    V._pin_header_css(report)
    html = report.read_text(encoding="utf-8")
    assert "canonical-header" in html, "必须注入固定覆盖样式"
    assert html.count("canonical-header") == 1
    assert "font-size:24px !important" in html
    assert "font-weight:800 !important" in html
    # 覆盖样式必须在 </head> 前（后于 Codex 的 <style>，配合 !important 压过漂移）
    assert html.find("font-size:24px !important") < html.find("</head>")
    assert "<h1>Karmine Corp vs Movistar KOI</h1>" in html, "正文 h1 不得被改动"


def test_pin_idempotent(tmp_path):
    report = tmp_path / "r.html"
    report.write_text(
        "<html><head><style>h1{font-size:54px}</style></head><body><h1>X vs Y</h1></body></html>",
        encoding="utf-8",
    )
    V._pin_header_css(report)
    first = report.read_text(encoding="utf-8")
    V._pin_header_css(report)
    second = report.read_text(encoding="utf-8")
    assert first == second, "二次调用不得重复注入"


def test_pin_skips_when_already_pinned(tmp_path):
    report = tmp_path / "r.html"
    original = "<html><head><style>canonical-header h1{font-size:24px}</style></head><body><h1>X</h1></body></html>"
    report.write_text(original, encoding="utf-8")
    V._pin_header_css(report)
    assert report.read_text(encoding="utf-8") == original, "已注入页必须原样跳过"


def test_pin_bare_body_without_head(tmp_path):
    """无 </head> 的异常页：插到 <body 前，仍能生效，不抛异常。"""
    report = tmp_path / "r.html"
    report.write_text(
        "<!doctype html><body><h1>Karmine Corp vs Movistar KOI</h1></body>",
        encoding="utf-8",
    )
    V._pin_header_css(report)
    html = report.read_text(encoding="utf-8")
    assert "canonical-header" in html
    assert html.find("canonical-header") < html.find("<body"), "样式应插到 <body 前"
    assert "<h1>Karmine Corp vs Movistar KOI</h1>" in html
