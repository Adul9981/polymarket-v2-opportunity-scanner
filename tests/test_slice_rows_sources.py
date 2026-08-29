"""切片时间戳兼容回归（2026-08-26 固化）。

教训：虎牙弹幕行 ts 是数值 unix 时间戳（如 1787726666.02），
slice_rows 曾只按 ISO 字符串解析，导致虎牙中文弹幕整行被静默丢弃——
今天 KT vs BRO 节点切片只剩 Twitch/Kick 英文源，内容质量骤降。
"""

from __future__ import annotations

import json
import time

import vps_intel_pipeline as V


def _write(path, rows) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_slice_rows_keeps_huya_numeric_ts(tmp_path) -> None:
    now = time.time()
    huya = tmp_path / "huya.jsonl"
    twitch = tmp_path / "twitch.jsonl"
    _write(huya, [
        {"ts": now - 60, "text": "虎牙样本1", "source": "huya_we957"},
        {"ts": now - 3600, "text": "窗口外", "source": "huya_we957"},
    ])
    _write(twitch, [
        {"ts": now - 120, "text": "twitch sample", "source": "twitch_caedrel"},
    ])
    out = tmp_path / "slice.jsonl"
    n = V.slice_rows(
        __import__("datetime").datetime.fromtimestamp(now - 300).isoformat(),
        [huya, twitch],
        out,
        __import__("datetime").datetime.fromtimestamp(now + 60).isoformat(),
    )
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    texts = [r.get("text") for r in rows]
    assert "虎牙样本1" in texts, "虎牙数值时间戳行被丢弃"
    assert "twitch sample" in texts
    assert "窗口外" not in texts
    assert n == 2
