#!/usr/bin/env python3
"""生成「比赛局势」实时数据 JSON（今日未结算场次 × 每局胜率 + 虎扑选手评分）。

规则层、只读（不下单、不读私钥、零 AI）：胜率三档（2026-11-01 用户定稿）——
①有胜负弹幕：win_signal（近 5 分钟、样本不足回退累积）；②无胜负弹幕但有选手评分
（能按队求和）：评分总和对比，大者 70% / 小者 30%；③无胜负弹幕也无评分：50:50 占位。
评分 = 虎扑通用评分（LoL lol_* / CS2 common_sports_*，按小局 strict_game，实时）。
产出单文件 data/situation_live.json，供静态页 match_situation.html 的 JS 轮询
原地更新（不整页刷新）。CS2 地图名取自虎扑评分树节点名（game.name）。

与情报页比赛局势栏（_inject_situation 注入 Codex 节点页）完全独立，不动现有情报页。

用法：
  python3 tools/build_situation_page.py --once
  python3 tools/build_situation_page.py --interval 60
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

OUT = vp.ROOT / "data" / "situation_live.json"


def _load_rows(files: list[Path]) -> list[dict]:
    """读弹幕 JSONL 并归一化（text/message、nick/nickname、ts→epoch），与 danmu_live_monitor 同口径。"""
    rows: list[dict] = []
    for inp in files:
        if not inp.exists():
            continue
        source = inp.stem.split("_", 1)[-1]
        for line in inp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "text" not in row and "message" in row:
                row["text"] = row["message"]
            if "nick" not in row and "nickname" in row:
                row["nick"] = row["nickname"]
            ts = row.get("ts")
            if isinstance(ts, str):
                try:
                    row["ts"] = datetime.datetime.fromisoformat(
                        ts.replace("+0800", "+08:00")
                    ).timestamp()
                except ValueError:
                    pass
            row.setdefault("source", source)
            rows.append(row)
    return sorted(rows, key=lambda row: str(row.get("ts", 0)))


def _strip_markers(html: str) -> str:
    """去掉 situation_*_block 的 BEGIN/END 注释标记（独立页不需要就地替换标记）。"""
    for marker in (
        render_node_page._WIN_BEGIN,
        render_node_page._WIN_END,
        render_node_page._RAT_BEGIN,
        render_node_page._RAT_END,
    ):
        html = html.replace(marker, "")
    return html


def _match_win_signal(m: dict, teams: list[str], files: list[Path], game: str | None) -> dict | None:
    """整场胜负弹幕信号（近 5 分钟、样本不足回退累积），每场算一次。"""
    rows = _load_rows(files)
    try:
        lineup = vp.fetch_lineup(str(m.get("id") or ""))
    except Exception:  # noqa: BLE001
        lineup = None
    return danmu_intel.win_signal(rows, teams, game=game, player_teams=lineup, window_seconds=300)


def _win_html(ws: dict | None, ratings: dict | None, teams: list[str], use_danmu: bool) -> str:
    """某局胜率块（三档，2026-11-01，按小局口径）；委托 render_node_page.situation_win_block_tiered。

    use_danmu 仅当前进行局为 True；非进行局先把弹幕信号清零（只走评分 70/30 或 50/50），
    避免把整场弹幕带进已结束/未开打的小局。
    """
    if ws is None:
        return ""
    if not use_danmu:
        ws = dict(ws)
        ws.update(total=0, count_a=0, count_b=0, pct_a=50, pct_b=50)
        ws.pop("basis", None)
    return _strip_markers(render_node_page.situation_win_block_tiered(ws, ratings, teams))


def _ratings_html(ratings: dict | None, teams: list[str]) -> str:
    """某局评分块；无评分返回空串（前端显示「评分未生成/待开打」）。"""
    if not ratings or not (ratings or {}).get("players"):
        return ""
    return _strip_markers(render_node_page.situation_ratings_block(ratings, teams))


def live_matches() -> list[dict]:
    """未结算且双队的场次（与 refresh_situation / 流水线同口径）。"""
    if not vp.MATCHES.exists():
        return []
    try:
        data = json.loads(vp.MATCHES.read_text(encoding="utf-8"))
        matches = data.get("matches", []) if isinstance(data, dict) else data
    except (OSError, json.JSONDecodeError):
        return []
    return [m for m in matches if not m.get("closed") and m.get("teams") and len(m["teams"]) == 2]


def _all_danmu_files() -> list[Path]:
    return sorted(p for game in vp.GAME_SLUGS for p in (vp.DANMU / game).glob("*/*.jsonl"))


def _bj_time(iso: str) -> str:
    """UTC ISO -> 北京时间「MM-DD HH:MM」展示串（页面统一北京时间，AGENTS 时间基准 25）。"""
    s = (iso or "").strip()
    if not s:
        return ""
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        bj = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
        return bj.strftime("%m-%d %H:%M")
    except ValueError:
        return s


def build() -> dict:
    """构建今日实时局势 JSON。空结果由调用方走自检，不硬报「无比赛」。"""
    matches_out: list[dict] = []
    all_files = _all_danmu_files()
    for m in live_matches():
        mid = str(m.get("id") or "")
        game = vp._match_game(m)
        if game not in ("lol", "cs2"):
            continue  # 首版只做英雄联盟 + CS2（dota2/valorant 预留）
        teams = m["teams"]
        files = vp.league_files(m, all_files)
        ws = _match_win_signal(m, teams, files, game)
        # LoL BO1/3/5 上限 5；CS2 BO1/3 上限 3（用户定稿 2026-11-01）
        max_games = min(vp.format_of(m), 3) if game == "cs2" else vp.format_of(m)
        games: list[dict] = []
        ratings_by_gi: dict[int, dict | None] = {}
        highest_rated = 0
        for gi in range(1, max_games + 1):
            ratings = vp.fetch_ratings(mid, gi)
            ratings_by_gi[gi] = ratings
            players = (ratings or {}).get("players") or []
            map_name = ""
            if players:
                g = (ratings or {}).get("game") or {}
                if game == "cs2":
                    map_name = str(g.get("name") or "")
                highest_rated = gi
            games.append(
                {
                    "gi": gi,
                    "map_name": map_name,
                    "state": "",  # 下方统一回填
                    "ratings_html": _ratings_html(ratings, teams),
                    "win_html": "",  # 下方统一回填（需先知道当前进行局）
                }
            )
        # 状态 + 胜率回填：有评分 = 已开打；最高已开打局 = 进行中（该局可用弹幕信号），
        # 其余 = 已结束 / 待开打（只用该局评分，无评分则 50:50）。
        live_gi = highest_rated if highest_rated > 0 else 0
        for g in games:
            gi = g["gi"]
            if highest_rated == 0 or gi > highest_rated:
                g["state"] = "upcoming"
            elif gi < highest_rated:
                g["state"] = "played"
            else:
                g["state"] = "live"
            g["win_html"] = _win_html(ws, ratings_by_gi.get(gi), teams, use_danmu=(gi == highest_rated))
        matches_out.append(
            {
                "id": mid,
                "game": game,
                "league": m.get("league") or "-",
                "teams": teams,
                "start_time": m.get("start_time") or "",
                "start_bj": _bj_time(m.get("start_time") or ""),
                "max_games": max_games,
                "live_gi": live_gi,
                "games": games,
            }
        )
    bj = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=8))
    )
    return {
        "updated_at": bj.strftime("%Y-%m-%d %H:%M:%S") + "（北京时间）",
        "updated_unix": int(time.time()),
        "matches": matches_out,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--once", action="store_true", help="跑一轮即退出")
    ap.add_argument("--interval", type=int, default=0, help="循环间隔秒数（本地调试）")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（默认 data/situation_live.json）")
    args = ap.parse_args()

    out = Path(args.out) if args.out else OUT

    def run() -> int:
        data = build()
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(out)
        n_matches = len(data["matches"])
        n_games = sum(len(m["games"]) for m in data["matches"])
        print(f"[situation] wrote {out} ({n_matches} matches, {n_games} games)", flush=True)
        if n_matches == 0:
            # 防错规则 1：0 场 ≠ 「今天没比赛」，先怀疑 matches_today.json 未更新/云扫未跑，
            # 不静默输出空结论。
            print(
                "[situation] WARN: 0 live matches. 核对云扫是否已更新 data/matches_today.json；"
                "若确有进行中比赛却为 0，先查扫描，勿直接报「无比赛」。",
                flush=True,
            )
        return n_matches

    if args.interval and args.interval > 0:
        while True:
            run()
            time.sleep(args.interval)
    else:
        run()


if __name__ == "__main__":
    main()
