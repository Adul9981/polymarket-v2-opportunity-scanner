#!/usr/bin/env python3
"""Fetch per-game Hupu player ratings (选手评分) for a match.

逆向自虎扑"通用评分" H5（bbs-genericscore-opg），以赛程接口返回的
scoreItemKey {outBizNo, outBizType}（lol_match）为入口，三级下钻：
  match (lol_match) -> games (lol_bo, 第1局/第2局/...) -> players (lol_item)
每名选手带 scoreAvg（分）+ scorePersonCount（评分人数）+ infoJson.teamId（归属队）。

只读公开接口、无鉴权，复用 fetch_hupu_esports.py 的 iPhone Safari UA/header。

用法：
  python3 tools/fetch_hupu_player_ratings.py --out-biz-no 3817 --game 3 \
      --out runtime/hupu_ratings/lng-wbg_g3.json
  # 不指定 --game 时取最新一局；不指定 --out 时打印到 stdout
"""

from __future__ import annotations

import argparse
import datetime
import json
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://games.mobileapi.hupu.com/1/8.0.99"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 "
        "Safari/604.1"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://offline-download.hupu.com/online/prod/310016/detail.html",
}

DEFAULT_OUT = None  # 默认打印 stdout，由调用方决定落盘


def _get(path: str, params: dict, timeout: int = 20) -> dict:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API_BASE}{path}?{qs}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _ij(info: dict, key: str):
    """infoJson 的值为单元素 list（如 homeTeamId:["9"]），取首个；缺失返回 None。"""
    v = (info or {}).get(key)
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _self_node(out_biz_type: str, out_biz_no: str, timeout: int = 20) -> dict:
    """match 节点：detail.infoJson 含 home/away 队名与 teamId。"""
    payload = _get(
        "/bplcommentapi/bpl/score_tree/getSelfByBizKey",
        {"outBizType": out_biz_type, "outBizNo": out_biz_no},
        timeout,
    )
    data = payload.get("data") or {}
    return (data.get("detail") or {}).get("infoJson") or {}


def _child_nodes(out_biz_type: str, out_biz_no: str, page_size: int = 50, timeout: int = 20) -> list[dict]:
    """当前节点的子节点列表（match 下为 lol_bo 各小局；lol_bo 下为 lol_item 各选手）。"""
    payload = _get(
        "/bplcommentapi/bpl/score_tree/getCurAndSubNodeByBizKey",
        {"outBizType": out_biz_type, "outBizNo": out_biz_no, "relation": "CHILD", "page": 1, "pageSize": page_size},
        timeout,
    )
    data = payload.get("data") or {}
    page = data.get("pageResult") or {}
    return page.get("data") or []


def _game_num_of(node: dict) -> int | None:
    """从 lol_bo 节点名"第N局"或 boNum 提取小局号。"""
    name = str((node or {}).get("name") or "")
    import re as _re
    m = _re.search(r"第\s*(\d+)\s*局", name)
    if m:
        return int(m.group(1))
    bo = _ij((node or {}).get("infoJson") or {}, "boNum")
    try:
        return int(bo)
    except (TypeError, ValueError):
        return None


def _empty(out_biz_no: str, out_biz_type: str, home: dict, away: dict) -> dict:
    return {
        "source": "hupu",
        "out_biz_no": out_biz_no,
        "out_biz_type": out_biz_type,
        "home": home,
        "away": away,
        "game": None,
        "players": [],
        "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def fetch_player_ratings(
    out_biz_no: str,
    out_biz_type: str = "lol_match",
    game_num: int | None = None,
    timeout: int = 20,
    strict_game: bool = False,
) -> dict:
    """三级拉取并归一化某场比赛（某小局）的选手评分。

    返回 None 语义由异常表达（网络失败抛 urllib.error）；空结果返回 players=[]。
    strict_game=True 且 game_num 给定时，若该局评分尚未生成（节点不存在）则返回空，
    不回退到最新一局——节点页按小局展示，禁止串局（混用上一局评分）。
    """
    info = _self_node(out_biz_type, out_biz_no, timeout)
    home = {"name": str(_ij(info, "homeTeamName") or ""), "team_id": str(_ij(info, "homeTeamId") or "")}
    away = {"name": str(_ij(info, "awayTeamName") or ""), "team_id": str(_ij(info, "awayTeamId") or "")}

    games = _child_nodes(out_biz_type, out_biz_no, timeout=timeout)
    game_nodes = [g.get("node") or {} for g in games if (g.get("node") or {}).get("bizType") == "lol_bo"]
    if not game_nodes:
        return _empty(out_biz_no, out_biz_type, home, away)

    target = None
    if game_num is not None:
        for g in game_nodes:
            if _game_num_of(g) == game_num:
                target = g
                break
        if target is None and strict_game:
            return _empty(out_biz_no, out_biz_type, home, away)
    if target is None:
        # 默认取最新一局（列表末尾）；无小局号信息则取最后一个
        target = game_nodes[-1]

    biz_id = str(target.get("bizId") or "")
    players_raw = _child_nodes(target.get("bizType") or "lol_bo", biz_id, timeout=timeout)
    team_of = {home["team_id"]: home["name"], away["team_id"]: away["name"]}
    players = []
    for p in players_raw:
        nd = p.get("node") or {}
        if nd.get("bizType") != "lol_item":
            continue
        name = str(nd.get("name") or "").strip()
        # 过滤非选手节点：教练/替补前缀、多英雄捆绑（如"卡西奥佩娅/魔腾/李青"），
        # 这些不是队员评分，混入会污染两列展示（2026-10-18 实测 BRO-LGD 发现）。
        if not name or "/" in name or name.startswith(("教练", "替补")):
            continue
        tid = str(_ij(nd.get("infoJson") or {}, "teamId") or "")
        players.append(
            {
                "name": name,
                "score": nd.get("scoreAvg"),
                "count": nd.get("scorePersonCount") or 0,
                "team_id": tid,
                "team": team_of.get(tid, ""),
            }
        )
    # 按评分人数降序（虎扑默认排序）
    players.sort(key=lambda p: -(p.get("count") or 0))

    return {
        "source": "hupu",
        "out_biz_no": out_biz_no,
        "out_biz_type": out_biz_type,
        "match_name": str(_ij(info, "selfName") or ""),
        "home": home,
        "away": away,
        "game": {"num": _game_num_of(target), "name": str(target.get("name") or ""), "biz_id": biz_id},
        "players": players,
        "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def fetch_lineup(
    out_biz_no: str,
    out_biz_type: str = "lol_match",
    game_num: int | None = None,
    timeout: int = 20,
) -> dict[str, str]:
    """返回某场比赛的首发阵容 {选手名: 队伍名}（复用评分树三级下钻，不依赖评分上线）。

    阵容在同一系列赛中基本固定，默认取最新一局 roster（比赛未开、无小局节点时返回空）；
    只保留有归属（team 非空）的选手，教练/替补/多英雄节点已由 fetch_player_ratings 过滤。
    网络失败抛 urllib.error（由调用方决定降级）。
    """
    r = fetch_player_ratings(out_biz_no, out_biz_type, game_num, timeout)
    lineup: dict[str, str] = {}
    for p in (r or {}).get("players") or []:
        name = str(p.get("name") or "").strip()
        team = str(p.get("team") or "").strip()
        if name and team:
            lineup[name] = team
    return lineup


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-biz-no", required=True, help="虎扑评分 match key 的 outBizNo（见赛程 scoreItemKey）")
    ap.add_argument("--out-biz-type", default="lol_match", help="评分节点类型，默认 lol_match")
    ap.add_argument("--game", type=int, default=None, help="目标小局号（默认取最新一局）")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（可选）")
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    result = fetch_player_ratings(args.out_biz_no, args.out_biz_type, args.game, args.timeout)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"[hupu_ratings] wrote {out} ({len(result['players'])} players, game {result.get('game')})")
    else:
        print(text)


if __name__ == "__main__":
    main()
