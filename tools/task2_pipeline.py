#!/usr/bin/env python3
"""Task 2 automation pipeline: scan -> action queue -> bar monitor wiring.

Implements the three-layer framework as a loop:

    layer 1 (trigger):   scheduled pass (--watch --interval, default 15 min)
    layer 2 (decision):  tools/market_scanner.py --live -> candidates + action queue
    layer 3 (output):    runtime/opportunity_candidates_live.json,
                         runtime/watchlist_events_live.json,
                         runtime/candidate_action_queue.json,
                         reports/opportunity_scan_*.md
    bar monitor hook:    for each actionable candidate, run a single-pass
                         tools/bar_monitor_runner.py to start in-match monitoring
                         (resting-order action queue; dry-run, no orders).

Safety:
- The pipeline only reads public data and runs dry-run monitors; it never places
  orders. Order placement stays with tools/grid_plan_runner.py after human
  confirmation (task 4 console).
- Single-market/daily caps are enforced by the scanner's risk gates and by
  config/risk_limits.json consumed by the bar monitor.

Usage:
    python3 tools/task2_pipeline.py --once
    python3 tools/task2_pipeline.py --watch --interval 900
    python3 tools/task2_pipeline.py --fixture-queue tests/fixtures/action_queue_sample.json \
        --fixture-history tests/fixtures/bar_s2_dip1.json \
        --fixture-book tests/fixtures/bar_book_mid44.json   # offline wiring test
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCANNER = ROOT / "tools" / "market_scanner.py"
BAR_RUNNER = ROOT / "tools" / "bar_monitor_runner.py"

STRATEGY_TO_BAR_KEY = {
    "S2_FAVORITE_DIP_GRID": "B_FAVORITE_DIP",
    "S1_REVERSAL_GRID": "A_DEEP_REVERSAL",
    "S1_OBSERVATION_MID_REVERSAL": "A_STANDARD_MID_REVERSAL",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_scan(args: argparse.Namespace) -> Path:
    """Run the scanner in live mode; returns the action queue path."""
    cmd = [
        sys.executable,
        str(SCANNER),
        "--live",
        "--live-limit",
        str(args.live_limit),
        "--live-pages",
        str(args.live_pages),
        "--output-json",
        str(args.scan_json),
        "--output-events",
        str(args.events_json),
        "--output-action-queue",
        str(args.queue_json),
        "--output-report",
        str(args.report),
    ]
    if args.scan_skip_book:
        cmd.append("--skip-book")
    subprocess.run(cmd, check=True)
    return Path(args.queue_json)


def events_summary(events_json: Path) -> dict[str, Any]:
    """Summarize watchlist events: live count + next upcoming match."""
    try:
        data = load_json(events_json)
        events = data.get("events") or []
    except Exception:  # noqa: BLE001
        return {"live_count": 0, "next_start_iso": None, "next_title": ""}
    now = datetime.now(timezone.utc)
    live = [e for e in events if e.get("time_status") in ("started_recently_or_live", "live")]
    upcoming = [
        e for e in events
        if (e.get("start_time") or "") > now.isoformat()
    ]
    upcoming.sort(key=lambda e: e.get("start_time") or "")
    nxt = upcoming[0] if upcoming else None
    return {
        "live_count": len(live),
        "watchlist_count": len(events),
        "next_start_iso": nxt.get("start_time") if nxt else None,
        "next_title": nxt.get("title") if nxt else "",
    }


def scan_sanity(diagnostics: dict[str, Any]) -> list[str]:
    """Empty-result sanity check.

    Distinguish "today really has no whitelisted matches" from "the scan
    silently failed". 2026-08-16 lesson: the scanner used to page the global
    event feed by listing time and read event.startDate as match time, so it
    reported "no matches" while LCK/LPL/LEC/EWC/TI matches were live. Any
    suspicious empty result must be surfaced loudly instead of being treated
    as a valid "no signal" conclusion.
    """
    warnings: list[str] = []
    fetched = int(diagnostics.get("fetched_events") or 0)
    esports_fetched = int(diagnostics.get("esports_tag_fetched") or 0)
    tag_enabled = bool(diagnostics.get("esports_tag_enabled"))
    matches = int(diagnostics.get("watchlist_matches") or 0)
    final_events = int(diagnostics.get("final_events") or 0)
    candidates = int(diagnostics.get("candidate_count") or 0)

    if fetched == 0:
        warnings.append("抓取事件为 0：事件源或网络异常，结果不可信，勿当作“今日无比赛”。")
        return warnings
    if tag_enabled and esports_fetched == 0:
        warnings.append("电竞标签抓取为 0：Esports 标签接口可能失败或 tag_id 失效，"
                        "结果不可信，勿当作“今日无比赛”。")
        return warnings
    if matches == 0:
        if esports_fetched > 0:
            warnings.append(f"抓到了 {esports_fetched} 个电竞事件但白名单 0 匹配："
                            "疑似白名单关键词缺失（如新联赛），需核对 config/market_watchlist.json，"
                            "勿当作“今日无比赛”。")
        else:
            warnings.append("白名单 0 匹配：需确认抓取集合是否覆盖窗口内赛事。")
    elif final_events == 0:
        warnings.append(f"白名单匹配 {matches} 场但最终赛事为 0：若确认近两天应有白名单比赛，"
                        "则时间窗口过滤可疑，需核对真实开赛时间（market 层 gameStartTime）是否被正确读取；"
                        "若确实无窗口内赛事，则属正常。")
    return warnings


def append_sanity_to_report(report_path: Path, diagnostics: dict[str, Any]) -> None:
    """Append the empty-result verdict to the scan report for future sessions."""
    warnings = scan_sanity(diagnostics)
    final_events = int(diagnostics.get("final_events") or 0)
    candidates = int(diagnostics.get("candidate_count") or 0)
    notes: list[str] = []
    if final_events > 0 and candidates == 0:
        notes.append(f"窗口内 {final_events} 场白名单赛事均未触发候选：属正常（无形态信号），"
                     "请对照赛事时间线确认场次是否齐全。")
    try:
        with report_path.open("a", encoding="utf-8") as f:
            f.write("\n## 空结果自检\n\n")
            if warnings:
                f.write(f"- 结论：扫描存在异常（{len(warnings)} 条告警），"
                        "不得当作“今日无比赛/无信号”。\n")
                for warn in warnings:
                    f.write(f"- ⚠ {warn}\n")
            else:
                f.write(f"- 结论：自检通过。窗口内白名单赛事 {final_events} 场、"
                        f"候选 {candidates} 个；“无候选/无赛事”结论可信。\n")
                for note in notes:
                    f.write(f"- 提示：{note}\n")
    except OSError:
        pass


def sleep_seconds(summary: dict[str, Any], interval: int) -> int:
    """Adaptive idle behavior: live matches -> normal interval; upcoming soon -> faster;
    no matches at all -> heartbeat once an hour."""
    if summary.get("live_count", 0) > 0:
        return max(60, interval)
    next_start = summary.get("next_start_iso")
    if next_start:
        try:
            delta = (datetime.fromisoformat(next_start) - datetime.now(timezone.utc)).total_seconds()
            if 0 < delta <= 15 * 60:
                return max(60, min(300, interval))
        except Exception:  # noqa: BLE001
            pass
        return max(60, interval)
    return 3600  # no whitelist matches in window: keep-alive once per hour


def bar_args_for_item(
    item: dict[str, Any], args: argparse.Namespace, offline: bool
) -> list[str] | None:
    strategy = str(item.get("recommended_strategy") or "")
    bar_key = STRATEGY_TO_BAR_KEY.get(strategy)
    if bar_key is None:
        print(f"  [pipeline] skip bar monitor for unsupported strategy: {strategy}")
        return None
    cmd = [
        sys.executable,
        str(BAR_RUNNER),
        "--slug",
        str(item.get("event_slug") or "offline"),
        "--outcome",
        str(item.get("outcome") or ""),
        "--strategy",
        bar_key,
        "--state-dir",
        str(args.bar_state_dir),
        "--action-file",
        str(args.bar_action_file),
        "--quiet",
    ]
    if offline:
        cmd.extend(
            [
                "--history-file",
                str(args.fixture_history),
                "--book-file",
                str(args.fixture_book),
            ]
        )
    return cmd


def monitor_actionable(queue_items: list[dict[str, Any]], args: argparse.Namespace, offline: bool) -> int:
    monitored = 0
    for item in queue_items:
        cmd = bar_args_for_item(item, args, offline)
        if cmd is None:
            continue
        try:
            subprocess.run(cmd, check=True)
            monitored += 1
            print(f"  [pipeline] bar monitor started for {item.get('event_slug')} "
                  f"({item.get('outcome')}, {item.get('action_recommendation')})")
        except subprocess.CalledProcessError as exc:
            print(f"  [pipeline] bar monitor failed for {item.get('event_slug')}: {exc}")
    return monitored


def one_pass(args: argparse.Namespace) -> dict[str, Any]:
    if args.fixture_queue:
        queue = load_json(Path(args.fixture_queue))
        items = queue.get("items") if isinstance(queue, dict) else queue
        if not isinstance(items, list):
            raise ValueError("--fixture-queue 需要 {\"items\": [...]}")
        queue_path = Path(args.fixture_queue)
        offline = True
    else:
        queue_path = run_scan(args)
        data = load_json(queue_path)
        items = data.get("items") or []
        scan_data = load_json(Path(args.scan_json))
        diagnostics = scan_data.get("diagnostics") or {}
        sanity_warnings = scan_sanity(diagnostics)
        for warn in sanity_warnings:
            print(f"[pipeline] ⚠ 空结果自检: {warn}")
        if int(diagnostics.get("final_events") or 0) > 0 and int(diagnostics.get("candidate_count") or 0) == 0:
            print("[pipeline] 提示: 窗口内白名单赛事均未触发候选（无形态信号），属正常；场次清单见赛事时间线。")
        append_sanity_to_report(Path(args.report), diagnostics)
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "follow_winner_accounts.py"),
                    "--hours",
                    "6",
                    "--limit",
                    "12",
                ],
                check=False,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001 - best-effort tracking
            print(f"[pipeline] winner-follow update failed: {exc}")
        if not args.no_comment_intel:
            comment_report = ROOT / "reports" / f"comment_intel_{datetime.now(timezone.utc):%Y-%m-%d}.md"
            try:
                ci = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "tools" / "comment_intel.py"),
                        "--events-json",
                        args.events_json,
                        "--report",
                        str(comment_report),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                for line in ci.stdout.splitlines():
                    print(f"[comment-intel] {line}")
                if ci.returncode != 0:
                    print(f"[pipeline] comment-intel 失败 rc={ci.returncode}: {ci.stderr[:300]}")
            except Exception as exc:  # noqa: BLE001 - best-effort comment intel
                print(f"[pipeline] comment-intel failed: {exc}")
        offline = False

    summary: dict[str, Any] = {"live_count": 0, "watchlist_count": 0, "next_start_iso": None, "next_title": ""}
    if not offline:
        summary = events_summary(Path(args.events_json))
    print(f"[pipeline] pass: {len(items)} actionable item(s) from {queue_path}")
    if not offline:
        if summary["live_count"]:
            print(f"[pipeline] 进行中白名单比赛 {summary['live_count']} 场（未触发候选属正常，继续盯）")
        elif summary["next_start_iso"]:
            print(f"[pipeline] 暂无进行中比赛；下一场：{summary['next_title']} @ {summary['next_start_iso']}")
        elif sanity_warnings:
            print("[pipeline] 空结果自检发现异常，不输出“暂无白名单比赛”结论；请先核对上面的告警。")
        else:
            print("[pipeline] 未来 2 天内暂无白名单比赛，进入每小时保活检查")
    monitored = monitor_actionable(items, args, offline)
    print(f"[pipeline] bar monitor pass: {monitored} market(s) monitored")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 2 automation pipeline (scan -> queue -> bar monitor)")
    parser.add_argument("--once", action="store_true", help="Run a single pass (default).")
    parser.add_argument("--watch", action="store_true", help="Keep looping every --interval seconds.")
    parser.add_argument("--interval", type=int, default=900, help="Loop interval seconds (default 900 = 15 min).")
    parser.add_argument("--live-limit", type=int, default=100)
    parser.add_argument("--live-pages", type=int, default=8)
    parser.add_argument("--scan-skip-book", action="store_true", help="Pass --skip-book to the scanner.")
    parser.add_argument("--scan-json", default=str(ROOT / "runtime" / "opportunity_candidates_live.json"))
    parser.add_argument("--events-json", default=str(ROOT / "runtime" / "watchlist_events.json"))
    parser.add_argument("--queue-json", default=str(ROOT / "runtime" / "candidate_action_queue.json"))
    parser.add_argument("--report", default="")
    parser.add_argument("--bar-state-dir", default=str(ROOT / "runtime" / "bar_monitor_state"))
    parser.add_argument("--bar-action-file", default=str(ROOT / "runtime" / "bar_monitor_actions.jsonl"))
    parser.add_argument("--fixture-queue", default="", help="Offline wiring test: action queue JSON.")
    parser.add_argument("--fixture-history", default="", help="Offline wiring test: bar history JSON.")
    parser.add_argument("--fixture-book", default="", help="Offline wiring test: bar book JSON.")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-item pipeline output.")
    parser.add_argument("--no-comment-intel", action="store_true", help="跳过评论区情报（赛前/赛中提示）。")
    args = parser.parse_args()

    if args.report:
        args.report = str(Path(args.report))
    else:
        args.report = str(ROOT / "reports" / f"opportunity_scan_{datetime.now(timezone.utc):%Y-%m-%d}.md")

    while True:
        try:
            summary = one_pass(args)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[pipeline] pass failed: {exc}")
            summary = {}
        if not args.watch:
            break
        time.sleep(sleep_seconds(summary, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
