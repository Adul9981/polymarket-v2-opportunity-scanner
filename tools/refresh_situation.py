#!/usr/bin/env python3
"""【比赛局势】栏实时刷新（按小局：局内实时、局末冻结 + 评分赛后回填）。

对"未结算且已生成小局节点"的比赛，逐小局处理：

  - 当前小局（最高局号、end 尚未生成，即进行中）：
      胜率 = 本小局切片 [本局起点 -> 现在] 重算 win_signal（近 5 分钟口径，
            样本不足回退整场累积）；
      评分 = fetch_ratings(mid, gi)（本小局 strict_game，不串局）；
      作用于 bp/mid 节点页。
  - 已结束小局（end 节点已生成）：
      胜率严格冻结（不再触碰）；
      评分在 end 节点生成后 RATINGS_BACKFILL_MIN 分钟内持续回填（虎扑评分赛后
      陆续上线，评分数一出来就补上），作用于 bp/mid/end 节点页；超时后全冻结。

只改 reports/ 本地 HTML，发布仍由 vps_publish 负责。

用法：
  python3 tools/refresh_situation.py --once            # 定时触发（每 60s）
  python3 tools/refresh_situation.py --interval 60     # 本地循环调试
  python3 tools/refresh_situation.py --once --match <id>  # 指定比赛跑一轮
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import time
from pathlib import Path

import danmu_intel
import render_node_page
import vps_intel_pipeline as vp

RATINGS_BACKFILL_MIN = 30  # 赛后评分回填窗口（分钟）；虎扑评分通常赛后数分钟内上线


def _node_state(mid: str, gi: int, phase: str) -> dict | None:
    """读小局节点状态文件（不存在/损坏返回 None）。"""
    p = vp.STATE_DIR / f"{mid}_g{gi}_{phase}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def game_start_iso(mid: str, gi: int) -> str | None:
    """本局起点：优先 mid 节点 slice_from（= 本局 g_start），退回 bp 节点（≈ g_start-15min）。"""
    for phase in ("mid", "bp"):
        st = _node_state(mid, gi, phase)
        if st and st.get("slice_from"):
            return str(st["slice_from"])
    return None


def _in_backfill(end_state: dict | None) -> bool:
    """end 节点生成后 RATINGS_BACKFILL_MIN 分钟内仍允许评分回填。"""
    if not end_state:
        return False
    try:
        gen = datetime.datetime.fromisoformat(
            str(end_state.get("generated_at") or "").replace("Z", "+00:00")
        )
        return (
            datetime.datetime.now(datetime.timezone.utc) - gen
        ).total_seconds() <= RATINGS_BACKFILL_MIN * 60
    except (ValueError, TypeError):
        return False


def _node_pages(mid: str, gi: int) -> dict[str, Path]:
    """该小局已生成且存在的节点页 {phase: path}（以状态文件 report 字段为准，不猜文件名）。"""
    out: dict[str, Path] = {}
    for phase in ("bp", "mid", "end"):
        st = _node_state(mid, gi, phase)
        if not st or not st.get("report_exists") or not st.get("report"):
            continue
        p = Path(str(st["report"]))
        if p.exists():
            out[phase] = p
    return out


def _replace_block(html: str, begin: str, end: str, new_block: str) -> str | None:
    """就地替换一对标记之间的内容；无标记返回 None（旧页无标记则跳过，不误写）。"""
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if not pat.search(html):
        return None
    return pat.sub(lambda _: new_block, html)


def _win_block(mid: str, gi: int, teams: list[str], files: list[Path], game: str | None = None) -> str | None:
    """本小局胜率块（[本局起点 -> 现在] 重算）；切片为 0/失败返回 None（保留旧值）。"""
    game_start = game_start_iso(mid, gi)
    if not game_start:
        return None
    slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
    tmp = vp.SLICE_DIR / f"{slug_id}_g{gi}_situation.jsonl"
    n = vp.slice_rows(game_start, files, tmp, "")
    if n <= 0:
        return None
    try:
        rows = [json.loads(ln) for ln in tmp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # 虎扑首发阵容动态折算选手表态（拿不到则降级静态 PLAYER_TEAM，danmu_intel 内部兜底）
        ws = danmu_intel.win_signal(rows, teams, game=game, player_teams=vp.fetch_lineup(mid))
    except Exception:  # noqa: BLE001
        return None
    return render_node_page.situation_win_block(ws, teams) if ws is not None else None


def _rat_block(mid: str, gi: int, teams: list[str]) -> str | None:
    """本小局评分块；无评分/拉取失败返回 None（不回写"暂无"，避免用空覆盖已有评分）。"""
    ratings = vp.fetch_ratings(mid, gi)
    if not ratings or not (ratings or {}).get("players"):
        return None
    return render_node_page.situation_ratings_block(ratings, teams)


def _refresh_pages(
    mid: str,
    gi: int,
    phases: tuple[str, ...],
    new_win: str | None = None,
    new_rat: str | None = None,
) -> int:
    """就地替换若干节点页的胜率/评分子块，返回实际更新的页面数。"""
    pages = _node_pages(mid, gi)
    updated = 0
    for phase in phases:
        p = pages.get(phase)
        if not p:
            continue
        try:
            html = p.read_text(encoding="utf-8")
        except OSError:
            continue
        orig = html
        if new_win is not None:
            html = _replace_block(
                html, render_node_page._WIN_BEGIN, render_node_page._WIN_END, new_win
            ) or html
        if new_rat is not None:
            html = _replace_block(
                html, render_node_page._RAT_BEGIN, render_node_page._RAT_END, new_rat
            ) or html
        if html == orig:
            continue
        try:
            p.write_text(html, encoding="utf-8")
            updated += 1
        except OSError:
            continue
    return updated


def refresh_match(m: dict, all_files: list[Path]) -> int:
    """刷新一场比赛各小局的节点页（当前局实时、已结束局评分回填），返回更新页面数。"""
    mid = m.get("id") or "-"
    teams = m["teams"]
    files = vp.league_files(m, all_files)
    if not files:
        return 0
    game = vp._match_game(m)
    updated = 0
    for gi in range(1, vp.MAX_GAME + 1):
        if not any(_node_state(mid, gi, ph) is not None for ph in ("bp", "mid", "end")):
            continue
        end_state = _node_state(mid, gi, "end")
        if end_state is not None:
            # 已结束：胜率冻结，评分仅在回填窗口内刷新
            if _in_backfill(end_state):
                new_rat = _rat_block(mid, gi, teams)
                if new_rat is not None:
                    updated += _refresh_pages(mid, gi, ("bp", "mid", "end"), new_rat=new_rat)
            continue
        # 进行中：胜率 + 评分都实时刷新（本局结束前）
        new_win = _win_block(mid, gi, teams, files, game)
        new_rat = _rat_block(mid, gi, teams)
        updated += _refresh_pages(mid, gi, ("bp", "mid"), new_win=new_win, new_rat=new_rat)
        break  # 只有一个小局在打，更高局号尚未生成
    return updated


def live_matches() -> list[dict]:
    """未结算且双队伍的比赛（与流水线口径一致）。"""
    if not vp.MATCHES.exists():
        return []
    try:
        data = json.loads(vp.MATCHES.read_text(encoding="utf-8"))
        matches = data.get("matches", []) if isinstance(data, dict) else data
    except (OSError, json.JSONDecodeError):
        return []
    return [m for m in matches if not m.get("closed") and m.get("teams") and len(m["teams"]) == 2]


def all_danmu_files() -> list[Path]:
    return sorted(p for game in vp.GAME_SLUGS for p in (vp.DANMU / game).glob("*/*.jsonl"))


def _run_once(match_filter: str | None) -> None:
    matches = live_matches()
    if match_filter:
        matches = [m for m in matches if (m.get("id") or "-") == match_filter]
    if not matches:
        return
    all_files = all_danmu_files()
    total = 0
    for m in matches:
        try:
            total += refresh_match(m, all_files)
        except Exception as e:  # noqa: BLE001
            print(f"[refresh] {m.get('id')}: skip ({e})", flush=True)
    if total:
        print(f"[refresh] updated {total} node page(s)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=0, help="循环间隔秒数（本地调试）")
    ap.add_argument("--match", default=None, help="只跑指定比赛 id")
    args = ap.parse_args()

    if args.interval and args.interval > 0:
        while True:
            _run_once(args.match)
            time.sleep(args.interval)
    else:
        _run_once(args.match)


if __name__ == "__main__":
    main()
