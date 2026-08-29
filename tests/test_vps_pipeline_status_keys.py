"""小局状态键类型回归（2026-08-25 固化）。

教训：game_status.json 经 json.loads 后键是字符串（"1"/"2"），
流水线用 gstatus.get(gi)（int）永远取不到 -> 每局退回时间窗估算，
第 3 局结束节点被跳过、第 4 局节点错序。
"""

from __future__ import annotations

import datetime
import json

import vps_intel_pipeline as V


def test_read_game_status_normalizes_int_keys(tmp_path, monkeypatch) -> None:
    f = tmp_path / "game_status.json"
    f.write_text(
        json.dumps(
            {
                "generated_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "games": {
                    "lol-test-2026-08-25": {
                        "1": {"closed": False, "winner": 0},
                        "3": {"closed": False, "winner": None},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(V, "GAME_STATUS_FILE", f)
    gs = V.read_game_status("lol-test-2026-08-25")
    assert gs is not None
    assert 1 in gs and 3 in gs
    assert "1" not in gs
    assert gs[1]["winner"] == 0
    assert gs[3]["winner"] is None


def test_read_game_status_stale_returns_none(tmp_path, monkeypatch) -> None:
    f = tmp_path / "game_status.json"
    old = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=30
    )
    f.write_text(
        json.dumps(
            {
                "generated_at": old.isoformat(),
                "games": {"lol-test": {"1": {"closed": False, "winner": 0}}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(V, "GAME_STATUS_FILE", f)
    assert V.read_game_status("lol-test") is None
