"""赛制识别三信号交叉校验回归（2026-08-25 固化）。

detect_format 从 Polymarket 市场字段解析 BO1/BO3/BO5：
  ou    Games Total O/U 市场（0.5/2.5/4.5）
  title 标题 (BO\\d+) 标注
  games 小局 Winner 市场最大局数（G4->BO5、G2->BO3、G1->BO1）
结论规则：多数一致；冲突时以 O/U 为准并标记 conflict。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".danmu_intel_site" / ".github" / "scripts" / "game_status_fetch.py"


def _load():
    spec = importlib.util.spec_from_file_location("game_status_fetch", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = _load()
detect_format = MOD.detect_format


def _mk(title: str, questions: list[str]):
    return title, [{"question": q} for q in questions]


def test_bo5_three_signals_agree() -> None:
    title, markets = _mk(
        "LoL: A vs B (BO5) - LCK Play-In",
        ["Games Total: O/U 4.5", "Game 1 Winner", "Game 4 Winner"],
    )
    fmt, sources, conflict = detect_format(title, markets)
    assert fmt == 5
    assert sources == {"ou": 5, "title": 5, "games": 5}
    assert conflict is False


def test_bo3_three_signals_agree() -> None:
    title, markets = _mk(
        "Counter-Strike: A vs B (BO3) - IEM Beijing",
        ["Games Total: O/U 2.5", "Map 1 Winner", "Map 2 Winner"],
    )
    fmt, sources, conflict = detect_format(title, markets)
    assert fmt == 3
    assert sources == {"ou": 3, "title": 3, "games": 3}
    assert conflict is False


def test_bo1_no_ou_market_title_and_games_agree() -> None:
    title, markets = _mk(
        "LoL: A vs B (BO1)",
        ["Game 1 Winner"],
    )
    fmt, sources, conflict = detect_format(title, markets)
    assert fmt == 1
    assert sources == {"ou": None, "title": 1, "games": 1}
    assert conflict is False


def test_conflict_ou_wins_and_flagged() -> None:
    title, markets = _mk(
        "LoL: A vs B (BO5) - LCK",
        ["Games Total: O/U 2.5"],
    )
    fmt, sources, conflict = detect_format(title, markets)
    assert fmt == 3  # O/U 市场优先于标题
    assert sources == {"ou": 3, "title": 5, "games": None}
    assert conflict is True


def test_title_only_fallback() -> None:
    title, markets = _mk("LoL: A vs B (BO3)", ["Game 1 Winner"])
    fmt, sources, conflict = detect_format(title, markets)
    assert fmt == 3
    assert sources == {"ou": None, "title": 3, "games": 1}
    assert conflict is True  # games=1 与 title=3 不一致 -> 显式标记待确认


def test_no_signal_defaults_to_5_flagged() -> None:
    fmt, sources, conflict = detect_format("LoL: A vs B", [])
    assert fmt == 5
    assert sources == {"ou": None, "title": None, "games": None}
    assert conflict is True
