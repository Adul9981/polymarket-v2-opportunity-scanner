#!/usr/bin/env python3
"""Fetch per-game Hupu player ratings (选手评分) for a match.

逆向自虎扑"通用评分" H5（bbs-genericscore-opg），以赛程接口返回的
scoreItemKey {outBizNo, outBizType} 为入口，三级下钻，兼容两类评分树：
  LoL：match (lol_match) -> games (lol_bo, 第1局/第2局/...) -> players (lol_item)
  CS2/综合体育：match (common_sports_first) -> maps (common_sports_second, 地图名)
    -> players (common_sports_third)
每名选手带 scoreAvg（分）+ scorePersonCount（评分人数）；LoL 选手另带
infoJson.teamId（归属队），CS2 通用评分不提供选手级归属队——本工具用
docs/data/intel/cs2_rosters.json（Liquipedia 静态阵容表）按选手名回填归属
（认得清归队，认不清留空、展示层标未归属），见 tools/fetch_cs2_rosters.py。

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
import re
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

# 两类评分树的小局/选手节点类型（2026-11-01 增补 CS2 common_sports 系列）。
_GAME_TYPES = ("lol_bo", "common_sports_second")
_PLAYER_TYPES = ("lol_item", "common_sports_third")

# 静态 CS2 阵容表路径（由 tools/fetch_cs2_rosters.py 生成，Liquipedia 唯一事实源）。
_ROSTER_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "intel" / "cs2_rosters.json"
_TEAM_NAMES_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "intel" / "team_names.json"

_roster_cache: dict[str, str] | None = None
_team_canon_cache: dict[str, str] | None = None


def _load_roster() -> dict[str, str]:
    """cs2_rosters.json -> {选手名小写: 规范队伍 id}（懒加载，一次性缓存）。"""
    global _roster_cache
    if _roster_cache is None:
        _roster_cache = {}
        try:
            data = json.loads(_ROSTER_PATH.read_text(encoding="utf-8"))
            for cid, t in (data.get("teams") or {}).items():
                for name in t.get("players") or []:
                    _roster_cache[str(name).lower()] = cid
        except Exception:  # noqa: BLE001
            pass
    return _roster_cache


def _team_canon_map() -> dict[str, str]:
    """team_names.json -> {abbr/full/alias/id 小写: 规范 id}（唯一权威，同 build_history_index）。"""
    global _team_canon_cache
    if _team_canon_cache is None:
        _team_canon_cache = {}
        try:
            data = json.loads(_TEAM_NAMES_PATH.read_text(encoding="utf-8"))
            for t in data.get("teams") or []:
                tid = t.get("id") or ""
                keys = [t.get("abbr"), t.get("full"), tid, *(t.get("aliases") or [])]
                for k in keys:
                    if k:
                        _team_canon_cache[str(k).lower()] = tid
        except Exception:  # noqa: BLE001
            pass
    return _team_canon_cache


def _canon_team(name: str) -> str:
    """队名 -> 规范 id；未登记回退原名（小写）。"""
    low = str(name).lower()
    return _team_canon_map().get(low, low)


# 虎扑评分树昵称 -> Liquipedia 阵容表规范名（小写）的显式对照。虎扑 CS2 评分树的选手
# 昵称与 Liquipedia 不一致（HEROIC 的 MartinezSa 在 Liquipedia 记为 Martinez、The MongolZ
# 的 Techno4K 被虎扑截成 Techno）。只做显式映射，不做模糊/子串匹配（宁可漏计不误配）；
# 新发现不一致先登记这里再跑回归。
_CS2_PLAYER_ALIASES = {
    "martinezsa": "martinez",
    "techno": "techno4k",
}


def _canon_player_name(name: str) -> str:
    """虎扑评分树昵称 -> 阵容表规范名（小写）；无别名时原样小写。"""
    low = str(name or "").strip().lower()
    return _CS2_PLAYER_ALIASES.get(low, low)


def _attribute_cs2_players(players: list[dict], home: dict, away: dict) -> None:
    """CS2 通用评分无选手级 teamId：按静态阵容表回填归属（原地修改）。

    规则：选手名小写 -> 阵容表规范队伍 id，与 home/away 队名规范化后的 id 比对；
    命中即回填该队 team_id/team，认不清（未登记/未在表）保持空 -> 展示层标未归属。
    宁可漏计不误配：只做确定性比对，不做模糊匹配。
    """
    if not players:
        return
    roster = _load_roster()
    home_canon = _canon_team(home.get("name", ""))
    away_canon = _canon_team(away.get("name", ""))
    for p in players:
        if p.get("team_id"):
            continue
        canon = roster.get(_canon_player_name(p.get("name", "")), "")
        if canon and canon == home_canon:
            p["team_id"] = home.get("team_id", "")
            p["team"] = home.get("name", "")
        elif canon and canon == away_canon:
            p["team_id"] = away.get("team_id", "")
            p["team"] = away.get("name", "")


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


def _game_num_of(node: dict, index: int = 0) -> int | None:
    """小局号：CS2（common_sports_second）优先读 infoJson.boNum（权威小局号），
    boNum 缺失才回退地图顺序 index+1；LoL 从节点名"第N局"/boNum 提取。

    注意（2026-11-02 教训）：虎扑 CS2 返回的地图节点是**倒序**（最新地图在前，
    实测炼狱小镇 boNum=2 在前、远古遗迹 boNum=1 在后），若按 index+1 推会把
    G1/G2 地图搞反（局势页 G1 显示成 G2 的地图）。故 CS2 必须读 boNum，不能靠列表顺序。
    """
    nd = node or {}
    if nd.get("bizType") == "common_sports_second":
        bo = _ij(nd.get("infoJson") or {}, "boNum")
        try:
            return int(bo)
        except (TypeError, ValueError):
            return index + 1
    name = str(nd.get("name") or "")
    m = re.search(r"第\s*(\d+)\s*局", name)
    if m:
        return int(m.group(1))
    bo = _ij(nd.get("infoJson") or {}, "boNum")
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


_ROLE_WORDS = ("教练", "替补", "二路", "解说")
_MERCH_WORDS = ("队服", "队徽", "周边", "应援")


def _is_real_player(name: str) -> bool:
    """是否真实选手名（用于过滤评分树里的非选手节点）。

    非选手节点的统一特征：角色标签——"角色：昵称"格式（全角/半角冒号，如"二路：米勒"、
    "解说：MacT"）或裸角色词（教练/替补/二路/解说，前缀如 LoL"解说：X"、后缀如
    CS2"DANK1NG解说"，一律按子串判）；另有周边商品节点（队服/队徽/周边/应援，如
    "Falcons中国队服"）与"多英雄捆绑"（如"卡西奥佩娅/魔腾/李青"）与空名。
    真实选手名不含冒号，也不包含角色/周边关键词（前缀后缀皆判，2026-11-02 修 CS2 漏过滤）。
    """
    name = str(name or "").strip()
    if not name:
        return False
    if "/" in name or "：" in name or ":" in name:
        return False
    for kw in _ROLE_WORDS + _MERCH_WORDS:
        if kw in name:
            return False
    return True


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
    game_nodes = [
        g.get("node") or {} for g in games if (g.get("node") or {}).get("bizType") in _GAME_TYPES
    ]
    if not game_nodes:
        return _empty(out_biz_no, out_biz_type, home, away)

    # 按小局号升序重排：虎扑 CS2 返回倒序（最新地图在前），不能靠列表顺序——
    # 否则 game_nodes[-1]（"最新一局"默认路径）会取到最早地图。用原始 index 作
    # CS2 boNum 缺失时的回退键（boNum 存在时 index 不参与）。
    game_nodes = [
        g for g, _ in sorted(
            ((g, _game_num_of(g, idx) or 0) for idx, g in enumerate(game_nodes)),
            key=lambda x: x[1],
        )
    ]

    target = None
    target_num = None
    if game_num is not None:
        for idx, g in enumerate(game_nodes):
            if _game_num_of(g, idx) == game_num:
                target = g
                target_num = game_num
                break
        if target is None and strict_game:
            return _empty(out_biz_no, out_biz_type, home, away)
    if target is None:
        # 默认取最新一局（列表末尾）；无小局号信息则取最后一个
        target = game_nodes[-1]
        target_num = _game_num_of(target, len(game_nodes) - 1)

    biz_id = str(target.get("bizId") or "")
    players_raw = _child_nodes(target.get("bizType") or "lol_bo", biz_id, timeout=timeout)
    team_of = {home["team_id"]: home["name"], away["team_id"]: away["name"]}

    is_cs2 = "common_sports" in out_biz_type

    players = []
    for p in players_raw:
        nd = p.get("node") or {}
        if nd.get("bizType") not in _PLAYER_TYPES:
            continue
        name = str(nd.get("name") or "").strip()
        # 过滤非选手节点（二路/解说/教练/替补/多英雄捆绑等），统一走 _is_real_player。
        if not _is_real_player(name):
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
    # CS2 通用评分选手级无 teamId：用静态阵容表按选手名回填归属（认不清保持空 -> 未归属）。
    if is_cs2:
        _attribute_cs2_players(players, home, away)

    return {
        "source": "hupu",
        "out_biz_no": out_biz_no,
        "out_biz_type": out_biz_type,
        "match_name": str(_ij(info, "selfName") or ""),
        "home": home,
        "away": away,
        "game": {"num": target_num, "name": str(target.get("name") or ""), "biz_id": biz_id},
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


def fetch_match_score(
    out_biz_no: str,
    out_biz_type: str = "lol_match",
    timeout: int = 20,
) -> dict | None:
    """拉系列总比分（地图/小局胜场数，如 CS2 2:0、LoL 2:1），只读 match 层 infoJson。

    虎扑评分树 match 层（common_sports_first / lol_match）的 infoJson 带
    homeTeamScore / awayTeamScore（系列总分，随每小局结束 +1）；地图/小局层
    （common_sports_second / lol_bo）不带比分，只有名字 + boNum。用于比赛局势页
    「当前比分」栏。返回 {"home_name","away_name","home","away"}（与 _self_node 的
    home/away 同序）；拿不到（无 key / 网络失败）返回 None。
    """
    try:
        info = _self_node(out_biz_type, out_biz_no, timeout)
    except Exception:  # noqa: BLE001
        return None
    home = _ij(info, "homeTeamScore")
    away = _ij(info, "awayTeamScore")
    if home is None and away is None:
        return None
    return {
        "home_name": str(_ij(info, "homeTeamName") or ""),
        "away_name": str(_ij(info, "awayTeamName") or ""),
        "home": str(home) if home is not None else "",
        "away": str(away) if away is not None else "",
    }


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
