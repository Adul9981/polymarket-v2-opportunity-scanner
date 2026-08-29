"""意见聚类采样回归（2026-08-26 固化）。

教训：整场 10,952 条弹幕只取前 500 条，结论停在系列前期（"FearX 胜算大"），
与最终赛果矛盾；--even 全时段均匀采样后结论覆盖全场。
"""

from __future__ import annotations

import json

from opinion_cluster import load_samples


def _make_slice(path, n: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for i in range(n):
            row = {
                "unixtime": 1787643000 + i * 10,
                "message": f"弹幕样本 {i}",
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_load_samples_first_cap(tmp_path) -> None:
    p = tmp_path / "s.jsonl"
    _make_slice(p, 1000)
    out = load_samples(p, cap=100)
    assert len(out) == 100
    assert out[0]["ts"] == 1787643000  # 只取前段


def test_load_samples_even_covers_full_window(tmp_path) -> None:
    p = tmp_path / "s.jsonl"
    _make_slice(p, 1000)
    out = load_samples(p, cap=100, even=True)
    assert len(out) == 100
    ts = [int(x["ts"]) for x in out]
    # 首尾都被覆盖，且大致均匀递增
    assert ts[0] == 1787643000
    assert ts[-1] >= 1787643000 + 990 * 10  # 覆盖到接近末尾（均匀采样末桶）
    assert all(ts[i] < ts[i + 1] for i in range(len(ts) - 1))
    assert ts[50] - ts[0] > 3000  # 中点落在全窗口中部（前截断时仅 500），而非前段
