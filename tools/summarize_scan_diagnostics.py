#!/usr/bin/env python3
"""Summarize task 2 live scan outputs in Chinese."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize opportunity scan diagnostics.")
    parser.add_argument(
        "--candidates",
        default="runtime/opportunity_candidates_live_task2.json",
        help="Path to opportunity_candidates JSON.",
    )
    parser.add_argument(
        "--events",
        default="runtime/watchlist_events_live_task2.json",
        help="Path to watchlist_events JSON.",
    )
    args = parser.parse_args()

    candidates_payload = load_json(Path(args.candidates))
    events_payload = load_json(Path(args.events))
    diagnostics = candidates_payload.get("diagnostics") or events_payload.get("diagnostics") or {}
    candidates = candidates_payload.get("candidates") or []
    events = events_payload.get("events") or []

    print("任务 2 live 扫描摘要")
    print("")
    print(f"- 候选机会：{len(candidates)}")
    print(f"- Watchlist 赛事：{len(events)}")

    if diagnostics:
        print(f"- 抓取事件：{diagnostics.get('fetched_events', '-')}")
        print(f"- 电竞标签抓取：{diagnostics.get('esports_tag_fetched', '-')}")
        print(f"- 标题过滤后：{diagnostics.get('after_title_filter', '-')}")
        print(f"- 时间窗口内：{diagnostics.get('within_time_window', '-')}")
        print(f"- Watchlist 匹配：{diagnostics.get('watchlist_matches', '-')}")
        print(f"- 最终赛事：{diagnostics.get('final_events', '-')}")
        print(f"- 标题过滤词：{diagnostics.get('title_filter') or '-'}")
        samples = diagnostics.get("sample_after_title_filter") or diagnostics.get("sample_fetched_events") or []
        if samples:
            print("")
            print("事件样本：")
            for sample in samples[:5]:
                print(
                    f"- {sample.get('start_time') or '-'} | "
                    f"{sample.get('title') or '-'} | {sample.get('slug') or '-'}"
                )
    else:
        print("- 诊断块：缺失")
        print("- 判断：这是旧版扫描产物，需要重新运行 live scan 才能定位空结果原因。")

    if candidates:
        print("")
        print("候选预览：")
        for idx, item in enumerate(candidates[:5], start=1):
            phenomena = ", ".join(item.get("phenomenon_tags") or [])
            strategy = item.get("recommended_strategy") or item.get("pattern") or "-"
            title = item.get("event_title") or "-"
            score = item.get("opportunity_score", "-")
            print(f"{idx}. {title} | {phenomena or '-'} -> {strategy} | score {score}")
    elif diagnostics:
        fetched = int(diagnostics.get("fetched_events") or 0)
        esports_fetched = int(diagnostics.get("esports_tag_fetched") or 0)
        matches = int(diagnostics.get("watchlist_matches") or 0)
        final_events = int(diagnostics.get("final_events") or 0)
        if fetched == 0:
            print("- 初步判断：active events 源头没有返回事件，可能需要补充其他事件源。")
        elif esports_fetched == 0:
            print("- 初步判断：电竞标签（Esports tag）抓取为 0，疑似标签接口失败或 tag_id 失效，"
                  "结果不可信，勿当作“今日无比赛”。")
        elif matches == 0:
            print("- 初步判断：有电竞事件但 watchlist 关键词 0 命中，疑似白名单缺失联赛关键词，"
                  "需要核对 config/market_watchlist.json，勿当作“今日无比赛”。")
        elif final_events == 0:
            print("- 初步判断：watchlist 有匹配，但时间窗口过滤后为空，需要调整时间窗口或赛事状态判断。")
        else:
            print("- 初步判断：赛事已进池，但价格形态没有触发 S1/S2 候选。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
