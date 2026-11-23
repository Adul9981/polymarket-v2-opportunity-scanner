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


_SITUATION_CARD_OPEN = '<div class="card"><h2><span class="no">2</span>比赛局势</h2>'
_SITPOLL_RE = re.compile(r"<script>.*?__sitPoll.*?</script>", re.DOTALL)


def _ensure_poll(html: str) -> tuple[str, bool]:
    """进行中页回填：给比赛局势卡补 #situation-card id + 注入/升级 60s 轮询脚本（幂等）。

    仅对进行中的 bp/mid 页调用（end 页冻结、不注入）。旧页（改前生成）卡无 id、无脚本，
    这里补上；新页已含则跳过（防重入守卫 + 幂等判断）。
    2026-10-31：已含旧版脚本（?sit= 版，无单调守卫）则就地升级为最新脚本。
    返回 (新 html, 是否改动)。
    """
    changed = False
    # 1) 旧页比赛局势卡无 id -> 补上（锚点由 intel_html.card 确定性产出，安全）
    if 'id="situation-card"' not in html and _SITUATION_CARD_OPEN in html:
        html = html.replace(
            _SITUATION_CARD_OPEN,
            '<div class="card" id="situation-card"><h2><span class="no">2</span>比赛局势</h2>',
            1,
        )
        changed = True
    # 2) 注入或升级轮询脚本
    script = render_node_page.situation_poll_script()
    if "__sitPoll" not in html:
        # 无脚本 -> 注入新脚本（须卡已有 id，否则轮询无目标）
        if 'id="situation-card"' in html:
            if "</body>" in html:
                html = html.replace("</body>", script + "</body>", 1)
            elif "</html>" in html:
                html = html.replace("</html>", script + "</html>", 1)
            else:
                html += script
            changed = True
    else:
        # 已有脚本 -> 若非最新版则就地替换（升级旧 ?sit= 版到单调守卫版）
        m = _SITPOLL_RE.search(html)
        if m and m.group(0) != script:
            html = html.replace(m.group(0), script, 1)
            changed = True
    return html, changed


def _win_block(
    mid: str,
    gi: int,
    teams: list[str],
    files: list[Path],
    game: str | None = None,
    ratings: dict | None = None,
) -> str | None:
    """本小局胜率块（[本局起点 -> 现在] 重算，三档，2026-11-01）；无法确定窗口返回 None（保留旧值）。

    无弹幕切片也照常算（win_signal 空行 -> total=0），让 tiered 回退到评分 70/30 或 50/50。
    与独立局势页共用 vp.game_win_signal（2026-11-02 统一"本小局切片"口径）。
    """
    ws = vp.game_win_signal(mid, gi, teams, files, game, lineup=vp.fetch_lineup(mid))
    if ws is None:
        return None
    return render_node_page.situation_win_block_tiered(ws, ratings, teams)


def _rat_block(
    mid: str, gi: int, teams: list[str], ratings: dict | None = None
) -> str | None:
    """本小局评分块；无评分/拉取失败返回 None（不回写"暂无"，避免用空覆盖已有评分）。"""
    if ratings is None:
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
    ensure_poll: bool = False,
) -> int:
    """就地替换若干节点页的胜率/评分子块，返回实际更新的页面数。

    ensure_poll=True 时（仅进行中 bp/mid）额外回填 #situation-card id + 60s 轮询脚本
    （幂等），让改前生成的旧页也获得实时刷新能力。
    """
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
        if ensure_poll:
            html, _ = _ensure_poll(html)
        if html == orig:
            continue
        try:
            p.write_text(html, encoding="utf-8")
            updated += 1
        except OSError:
            continue
    return updated


def refresh_match(m: dict, all_files: list[Path], force: bool = False) -> int:
    """刷新一场比赛各小局的节点页（当前局实时、已结束局评分回填），返回更新页面数。

    force=True 时忽略"已结束局评分回填窗口"，对已结束小局也强制重拉评分并重渲染
    （用于数据源修正后回填旧页，如阵容表补齐导致选手归属变化）。
    """
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
            # 已结束：胜率冻结，评分仅在回填窗口内刷新（force 则评分也强制刷新，胜率仍冻结）
            if force or _in_backfill(end_state):
                new_rat = _rat_block(mid, gi, teams)
                if new_rat is not None:
                    updated += _refresh_pages(mid, gi, ("bp", "mid", "end"), new_rat=new_rat)
            continue
        # 进行中：胜率 + 评分都实时刷新（本局结束前）；评分拉一次供胜率三档与评分块共用
        ratings = vp.fetch_ratings(mid, gi)
        new_win = _win_block(mid, gi, teams, files, game, ratings)
        new_rat = _rat_block(mid, gi, teams, ratings)
        updated += _refresh_pages(
            mid, gi, ("bp", "mid"), new_win=new_win, new_rat=new_rat, ensure_poll=True
        )
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


def _run_once(match_filter: str | None, force: bool = False) -> None:
    matches = live_matches()
    if match_filter:
        matches = [m for m in matches if (m.get("id") or "-") == match_filter]
    if not matches:
        return
    all_files = all_danmu_files()
    total = 0
    for m in matches:
        try:
            total += refresh_match(m, all_files, force=force)
        except Exception as e:  # noqa: BLE001
            print(f"[refresh] {m.get('id')}: skip ({e})", flush=True)
    if total:
        print(f"[refresh] updated {total} node page(s)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=0, help="循环间隔秒数（本地调试）")
    ap.add_argument("--match", default=None, help="只跑指定比赛 id")
    ap.add_argument("--force", action="store_true", help="忽略评分回填窗口，强制重拉已结束小局评分")
    args = ap.parse_args()

    if args.interval and args.interval > 0:
        while True:
            _run_once(args.match, force=args.force)
            time.sleep(args.interval)
    else:
        _run_once(args.match, force=args.force)


if __name__ == "__main__":
    main()
