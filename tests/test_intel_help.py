"""Help page and assistant content must cover core user questions."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import add_assistant  # noqa: E402


def test_assistant_injection_is_responsive_and_idempotent(tmp_path: Path) -> None:
    page = tmp_path / "intel" / "today.html"
    page.parent.mkdir()
    page.write_text("<html><head></head><body><h1>ok</h1></body></html>", encoding="utf-8")
    assert add_assistant.inject_all(tmp_path) == 1
    first = page.read_text(encoding="utf-8")
    assert "assistant.css" in first
    assert "assistant.js" in first
    assert add_assistant.inject_all(tmp_path) == 0
    assert page.read_text(encoding="utf-8") == first


def test_help_page_covers_required_sections() -> None:
    text = (ROOT / "reports" / "intel_help.html").read_text(encoding="utf-8")
    for phrase in (
        "比赛基本情况",
        "幻觉的核心识别",
        "常见问题解答",
        "个人情况与联系",
        "今日比赛",
        "TG 更新频道",
        "@serene7mc",
        "@polymarket_ad",
    ):
        assert phrase in text
    assert "Stake" not in text


def test_assistant_assets_are_valid_and_have_no_raw_question_storage() -> None:
    js_path = ROOT / "reports" / "assistant.js"
    js = js_path.read_text(encoding="utf-8")
    subprocess.run(["node", "--check", str(js_path)], check=True)
    assert "localStorage" not in js
    assert "sessionStorage" not in js
    assert "di-assistant-panel" in js
    assert "幻觉的核心识别方法" in js


def test_assistant_css_has_mobile_and_desktop_breakpoints() -> None:
    css = (ROOT / "reports" / "assistant.css").read_text(encoding="utf-8")
    assert "@media(max-width:640px)" in css
    assert "100dvh" in css
    assert "safe-area-inset-bottom" in css
