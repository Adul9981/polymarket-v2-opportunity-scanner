#!/usr/bin/env python3
"""Export today's esports matches from watchlist_events.json -> matches_today.json.

本地侧辅助：每日扫描后运行，把今日比赛清单（对阵/联赛/时间）同步到服务器，
供 vps_intel_pipeline.py 按比赛检测结束并产出情报。

用法：
  python3 tools/export_today_matches.py [--input runtime/watchlist_events.json]
      [--official runtime/official_lol_today.json]
      [--hupu data/hupu_esports_schedule.json] [--out runtime/matches_today.json]
      [--date 2026-08-24]

--official：并入 Riot 官方赛程（fetch_official_lol_schedule.py 产出），
解决 LCK CL / LPL 等 Polymarket 暂无市场的官方场次不进今日清单的问题
（2026-09-10 固化；教训：09-09 NS vs DNS 需用户口播才补登记）。
--hupu：并入虎扑场次（fetch_hupu_esports.py 产出）——CS2 全部 + LoL 中官方
Riot 未覆盖的场次（德玛西亚杯/亚运会/表演赛等）；官方已覆盖的 LCK/LPL/LEC/LCP
跳过避免重复（2026-10-12 用户定稿）。

写 --out 的同时镜像到 data/matches_today.json（vps_intel_pipeline 的规范输入），
本地跑情报生成无需手动复制；Mac 日常任务仍 scp runtime/matches_today.json，不受影响
（2026-10-13 修复 runtime/data 路径不一致）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def _team_key(teams: list[str]) -> tuple[str, ...]:
    """按队伍名归一化去重键（容忍 DK Challengers / Dplus KIA Challengers 等写法）。"""
    norm: dict[str, str] = {}
    tn = Path(__file__).resolve().parent.parent / "docs" / "data" / "intel" / "team_names.json"
    if tn.exists():
        try:
            for t in json.loads(tn.read_text(encoding="utf-8")).get("teams", []):
                for k in [t.get("abbr", ""), t.get("full", ""), *t.get("aliases", [])]:
                    norm[str(k).strip().lower()] = t.get("abbr") or str(k)
        except Exception:  # noqa: BLE001
            pass
    return tuple(sorted(norm.get(str(t).strip().lower(), str(t).strip().lower()) for t in teams))


def merge_official(rows: list[dict], out: list[dict]) -> list[dict]:
    """合并官方场次（按 id/slug 去重），官方 slug 优先保持可追溯。"""
    if not rows:
        return out
    known = {m.get("id") or m.get("slug") for m in out}
    known_teams = {_team_key(m.get("teams") or []) for m in out}
    for e in rows:
        teams = e.get("teams") or []
        if len(teams) != 2:
            continue
        slug = e.get("slug") or e.get("official_match_id") or ""
        if slug and slug in known:
            continue
        tkey = _team_key(teams)
        if tkey in known_teams:
            # 同一场已由 Polymarket 快照登记：保留原条目，只补官方比赛 id
            for m in out:
                if _team_key(m.get("teams") or []) == tkey:
                    m.setdefault("official_match_id", e.get("official_match_id", ""))
                    m["league"] = e.get("league", m.get("league", "LoL"))
                    break
            continue
        out.append(
            {
                "id": slug or e.get("official_match_id"),
                "slug": slug,
                "official_match_id": e.get("official_match_id", ""),
                "league": e.get("league", "LoL"),
                "teams": teams,
                "start_time": e.get("start_time") or "",
                "end_time": e.get("end_time") or "",
                "closed": bool(e.get("closed")),
                "_official": True,
            }
        )
        if slug:
            known.add(slug)
        known_teams.add(tkey)
    return out


_OFFICIAL_LOL_LEAGUE_KEYS = ("lck", "lpl", "lec", "lcp")
_TBD_MARKERS = ("待定", "tbd", "tba")


def _hupu_is_official_lol(tournament: str) -> bool:
    """虎扑 LoL 场次是否属于官方 Riot 已覆盖的联赛（LCK/LPL/LEC/LCP）。"""
    t = (tournament or "").lower()
    return any(k in t for k in _OFFICIAL_LOL_LEAGUE_KEYS)


def _is_tbd(team: str) -> bool:
    """是否 TBD/待定 占位（无真实队伍，跳过，避免生成空情报）。"""
    s = str(team or "").strip().lower()
    return s == "" or s in _TBD_MARKERS


def merge_hupu(rows: list[dict], out: list[dict]) -> list[dict]:
    """合并虎扑场次（2026-10-12 用户定稿：CS2 全部 + LoL 官方没覆盖的场次）。

    纳入范围：
      - CS2 全部（无官方赛程源、Polymarket 覆盖不全，虎扑是主要补全来源）；
      - LoL 中官方 Riot 没覆盖的场次（德玛西亚杯 / 亚运会英雄联盟 / 表演赛等），
        官方已覆盖的 LCK/LPL/LEC/LCP 跳过，避免与 official 重复。
    按队伍名去重（已在 out 里的跳过）；比赛 id 加游戏前缀（cs2- / lol-）——
    vps_intel_pipeline._match_game 按 id 首段判游戏，否则 hupu-... 会被当
    "未知联赛"混用所有弹幕（违反禁跨联赛混源红线）。
    """
    if not rows:
        return out
    known_teams = {_team_key(m.get("teams") or []) for m in out}
    for e in rows:
        league = str(e.get("league") or "").strip().upper()
        if league == "CS2":
            game = "cs2"
        elif league == "LOL":
            if _hupu_is_official_lol(e.get("tournament") or ""):
                continue
            game = "lol"
        else:
            continue
        teams = e.get("teams") or []
        if len(teams) != 2:
            continue
        if any(_is_tbd(t) for t in teams):
            continue
        tkey = _team_key(teams)
        if tkey in known_teams:
            continue
        hid = str(e.get("hupu_match_id") or e.get("match_id") or "").strip()
        if not hid:
            continue
        mid = f"{game}-hupu-{hid}"
        out.append(
            {
                "id": mid,
                "slug": mid,
                "official_match_id": "",
                "league": "CS2" if game == "cs2" else "LoL",
                "teams": teams,
                "start_time": e.get("start_iso") or "",
                "end_time": "",
                "closed": bool(str(e.get("status") or "").lower() == "completed"),
                "_hupu": True,
                "_hupu_tournament": e.get("tournament") or "",
                # 选手评分链路：虎扑评分 key + 两队 memberId（供 fetch_hupu_player_ratings 三级拉取）
                "hupu_score_out_biz_no": str((e.get("score_item_key") or {}).get("out_biz_no") or ""),
                "hupu_score_out_biz_type": str((e.get("score_item_key") or {}).get("out_biz_type") or ""),
                "hupu_member_ids": e.get("member_ids") or [],
            }
        )
        known_teams.add(tkey)
    return out


def parse_teams(title: str) -> list[str]:
    m = re.search(r":\s*([^(:\-]+?)\s+vs\s+([^(:\-]+)", title or "", re.I)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return []


def league_of(group: str) -> str:
    g = (group or "").lower()
    if "dota" in g:
        return "Dota2"
    if "cs" in g:
        return "CS2"
    if "lol" in g or "league" in g:
        return "LoL"
    return (group or "-").strip()


def refresh_official_cache(path: Path, date: str, max_age_sec: int = 600) -> None:
    """官方赛程缓存 >10 分钟即刷新（失败不阻塞，沿用旧快照）。"""
    try:
        if path.exists() and time.time() - path.stat().st_mtime < max_age_sec:
            return
        script = Path(__file__).resolve().parent / "fetch_official_lol_schedule.py"
        if not script.exists():
            return
        subprocess.run(
            [sys.executable, str(script), "--date", date, "--out", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except Exception:  # noqa: BLE001
        pass


def refresh_hupu_cache(path: Path, max_age_sec: int = 300) -> None:
    """虎扑赛程缓存 >5 分钟即刷新（失败不阻塞，沿用旧快照）。

    抓全量（LOL+CS2），与 update_site_today.py 共用同一缓存文件；
    本脚本取 CS2 + 官方未覆盖的 LoL（merge_hupu 内按 league/tournament 过滤）。
    """
    try:
        if path.exists() and time.time() - path.stat().st_mtime < max_age_sec:
            return
        script = Path(__file__).resolve().parent / "fetch_hupu_esports.py"
        if not script.exists():
            return
        subprocess.run(
            [sys.executable, str(script), "--out", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="runtime/watchlist_events.json")
    ap.add_argument("--official", default="runtime/official_lol_today.json")
    ap.add_argument("--hupu", default="data/hupu_esports_schedule.json")
    ap.add_argument("--out", default="runtime/matches_today.json")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    today = args.date or datetime.date.today().isoformat()
    official_path = Path(args.official)
    refresh_official_cache(official_path, today)

    out = []
    input_path = Path(args.input)
    if input_path.exists():
        data = json.loads(input_path.read_text(encoding="utf-8"))
        evs = data if isinstance(data, list) else data.get("events", data.get("matches", []))
        for e in evs:
            st = e.get("start_time") or ""
            active_pending = bool(e.get("active")) and not bool(e.get("closed"))
            # 当天开赛 或 活跃未关闭（跨日仍在进行/未结束，如北京时间凌晨开赛）
            if not st.startswith(today) and not active_pending:
                continue
            teams = parse_teams(e.get("title") or "")
            if len(teams) != 2:
                continue
            out.append(
                {
                    "id": e.get("slug") or e.get("id"),
                    "slug": e.get("slug") or e.get("id"),
                    "official_match_id": e.get("official_match_id", ""),
                    "league": league_of(e.get("watchlist_group")),
                    "teams": teams,
                    "start_time": st,
                    "end_time": e.get("end_time") or "",
                    "closed": bool(e.get("closed")),
                }
            )

    # 官方 Riot 赛程补漏（2026-09-10）：LCK CL 等非 Polymarket 场次
    if official_path.exists():
        official = json.loads(official_path.read_text(encoding="utf-8"))
        rows = official.get("matches", []) if isinstance(official, dict) else []
        # 只补今天（含北京时间凌晨场次由 date 归并）
        today_rows = [r for r in rows if (r.get("start_time") or "").startswith(today)]
        merge_official(today_rows, out)

    # 虎扑补漏（2026-10-12 用户定稿）：CS2 全部 + 官方未覆盖的 LoL（德玛西亚杯等）
    hupu_path = Path(args.hupu)
    refresh_hupu_cache(hupu_path)
    if hupu_path.exists():
        hupu = json.loads(hupu_path.read_text(encoding="utf-8"))
        hrows = hupu.get("matches", []) if isinstance(hupu, dict) else []
        # 只取今天（虎扑 date 字段 = 北京时间，与本地 today 一致）
        today_hupu = [r for r in hrows if r.get("date") == today]
        merge_hupu(today_hupu, out)

    payload = {"date": today, "matches": out}
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    Path(args.out).write_text(text, encoding="utf-8")

    # 镜像到 pipeline 规范输入 data/matches_today.json（vps_intel_pipeline / vps_publish 读这里）。
    # 本地跑情报生成时无需手动复制；Mac 日常任务仍 scp runtime/matches_today.json 到服务器
    # data/，这里多写一份 data/ 副本对 Mac 无害（2026-10-13 修复 runtime/data 路径不一致）。
    canonical = Path(__file__).resolve().parent.parent / "data" / "matches_today.json"
    if canonical.resolve() != Path(args.out).resolve():
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(text, encoding="utf-8")

    print(f"wrote {args.out}: {len(out)} matches")
    for m in out:
        print(" ", m["id"], "|", m["league"], "|", " vs ".join(m["teams"]), "|", m["start_time"])


if __name__ == "__main__":
    main()
