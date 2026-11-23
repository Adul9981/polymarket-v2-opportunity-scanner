#!/usr/bin/env python3
"""Fetch CS2 active rosters from Liquipedia CS team pages -> docs/data/intel/cs2_rosters.json.

虎扑通用评分对 CS2（common_sports_third）不提供选手归属 teamId（LoL 的 lol_item 有），
故 CS2 选手在【比赛局势】评分栏无法分成两队。本工具从 Liquipedia CS（项目规则 24 的
P0 事实源，免费可脚本化）拉取每队 "Player Roster → Active" 阵容，落成静态选手→队伍表，
供 fetch_hupu_player_ratings 在评分结果里回填选手归属（认得清的归队，认不清标未归属）。

实现要点（为避免 Liquipedia 反爬限流，本工具刻意做到"一次请求"）：
- 用 action=query&titles=A|B|... 一次性拉全部队伍 wikitext（redirects=1 跟随重定向），
  而不是逐队 parse 请求；Liquipedia 对连发请求会 429 甚至封 IP。
- 解析 wikitext 的 ===Active=== 段，逐 {{Person|...}} 模板（平衡括号扫描，容忍
  joindate 里的嵌套 {{abbr|...}}），按 role 字段过滤：

  · 排除（非上场人员）：Coach / Interim Coach / Manager / Analyst / Director 等，
    以及 "On Loan"（租借出去，在别队打）。
  · 保留（本队可能上场）：role 为空的首发、Loan（租借入）、Trial、Stand-in、Bench 等。

  纪律：宁可漏计（少归一个选手 -> 页面显示"未归属"），不误配（把教练/租借出选手
  算进本队）。教练绝不会出现在虎扑评分里，但租借出的选手会出现在他实际效力队，
  故必须排除，避免同队误配。

队伍 key 用 docs/data/intel/team_names.json 的规范 id（唯一权威），页标题映射写在
TEAM_PAGES。转会后重跑本工具即可刷新；新队伍先登记 team_names.json + 本表。

用法：
  python3 tools/fetch_cs2_rosters.py --out docs/data/intel/cs2_rosters.json
  python3 tools/fetch_cs2_rosters.py --print        # 只打印不落盘
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://liquipedia.net/counterstrike/api.php"
UA = "PolymarketIntelBot/1.0 (research; contact local)"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "data" / "intel" / "cs2_rosters.json"

# team_names.json 规范 id -> Liquipedia CS 页面标题（新增队伍两边都要登记）。
# 标题用 Liquipedia 规范名（重定向会由 redirects=1 跟随，但规范名省一次解析）。
TEAM_PAGES = {
    "furia": "FURIA",
    "g2": "G2 Esports",
    "navi": "Natus Vincere",
    "spirit": "Team Spirit",
    "vit": "Team Vitality",
    "mouz": "MOUZ",
    "mglz": "The MongolZ",
    "tl": "Team Liquid",
    "fut": "FUT Esports",
    "aurora": "Aurora Gaming",
    "nemiga": "Nemiga Gaming",
    "9z": "9z Team",
    "legacy": "Legacy",
    "flc": "Team Falcons",
    "ic": "IC Esports",
    "lvg": "Lynn Vision Gaming",
    "m80": "M80",
    "pain": "PaiN Gaming",
    "dendele": "DENDELE CS",
    "faze": "FaZe Clan",
    "tyloo": "TYLOO",
    "betboom": "BetBoom Team",
    "prv": "PARIVISION",
    "b8": "B8",
    "heroic": "HEROIC",
}

# 非上场角色关键词（小写匹配）；"on loan"（租借出）单独处理。
NON_PLAYER_ROLES = (
    "coach", "manager", "analyst", "director", "ceo", "owner",
    "physio", "psycholog", "consultant", "founder", "board",
)

_PERSON_RE = re.compile(r"\{\{(?:Person|SquadPlayer)\|")


def _fetch(url: str, retries: int = 4) -> bytes:
    """带 UA + gzip 的抓取；Liquipedia 对连发请求会限流（HTTP 429），故指数退避重试。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Encoding": "gzip",
    })
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data
        except urllib.error.HTTPError as e:
            last = e
            if e.code != 429 or attempt == retries:
                raise
            time.sleep(2 ** (attempt + 1))  # 2, 4, 8, 16 s
    raise last  # pragma: no cover


def _api_get(params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    return json.loads(_fetch(f"{API}?{q}").decode("utf-8", "replace"))


def _all_wikitext() -> dict:
    """一次 action=query 拉全部队伍 wikitext -> {title: wikitext}。"""
    titles = "|".join(TEAM_PAGES.values())
    d = _api_get({
        "action": "query", "titles": titles, "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "redirects": "1",
        "format": "json", "formatversion": "2",
    })
    out = {}
    for p in (d.get("query") or {}).get("pages") or []:
        if p.get("missing"):
            continue
        revs = p.get("revisions") or []
        if not revs:
            continue
        content = (revs[0].get("slots") or {}).get("main", {}).get("content") or ""
        out[p["title"]] = content
    return out


def _person_bodies(seg: str) -> list[str]:
    """抽出 seg 内每个 {{Person|...}} / {{SquadPlayer|...}} 的参数字符串。

    用平衡括号扫描（而非 [^{}]*），容忍 joindate 里嵌套的 {{abbr|...}} / {{cite|...}}。
    """
    out = []
    for m in _PERSON_RE.finditer(seg):
        i = m.end()
        depth = 1
        while i < len(seg) and depth > 0:
            if seg[i:i + 2] == "{{":
                depth += 1
                i += 2
            elif seg[i:i + 2] == "}}":
                depth -= 1
                i += 2
            else:
                i += 1
        out.append(seg[m.end():i - 2])
    return out


def _field(body: str, key: str) -> str:
    """取 Person 模板顶层字段值（id / role / team 等）。值不含 | { }，正则足够。"""
    m = re.search(r"(?:^|\|)" + key + r"\s*=\s*([^|{}]*)", body)
    return m.group(1).strip() if m else ""


def _exclude_role(role: str) -> bool:
    r = role.lower()
    if not r:
        return False
    if any(k in r for k in NON_PLAYER_ROLES):
        return True
    if "on loan" in r:  # 租借出 -> 在别队打，不算本队
        return True
    return False


def active_roster(wikitext: str) -> list[str]:
    """从某队 wikitext 抽取 Active 段选手 ID（in-game 名，含大小写）。

    读到 ===Former=== 为止；逐 {{Person}} 解析，按 _exclude_role 排除教练/经理/
    租借出，保留首发 + 租借入 + 试训 + 替补。
    """
    start = wikitext.find("===Active===")
    if start < 0:
        return []
    end = wikitext.find("===Former===", start)
    seg = wikitext[start:end if end >= 0 else start + 60000]
    ids = []
    for body in _person_bodies(seg):
        pid = _field(body, "id")
        role = _field(body, "role")
        if not pid or _exclude_role(role):
            continue
        pid = re.split(r"\{\{", pid)[0].strip()
        if pid and pid not in ids:
            ids.append(pid)
    return ids


def _team_abbr(cid: str) -> str:
    """从 team_names.json 取规范 abbr；未登记则回退 key 本身。"""
    reg = ROOT / "docs" / "data" / "intel" / "team_names.json"
    try:
        for t in json.loads(reg.read_text(encoding="utf-8")).get("teams", []):
            if t.get("id") == cid:
                return t.get("abbr") or cid
    except Exception:  # noqa: BLE001
        pass
    return cid


def fetch_all() -> dict:
    wikitexts = _all_wikitext()
    teams = {}
    for cid, page in TEAM_PAGES.items():
        wt = wikitexts.get(page)
        players = active_roster(wt) if wt is not None else []
        ok = wt is not None and "===Active===" in wt
        teams[cid] = {
            "abbr": _team_abbr(cid),
            "liquipedia_page": page,
            "players": players,
            "ok": ok,
        }
    return {
        "source": "liquipedia_cs",
        "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds").replace("+00:00", "Z"),
        "teams": teams,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="输出 JSON 路径")
    ap.add_argument("--print", action="store_true", help="只打印结果，不落盘")
    args = ap.parse_args()

    data = fetch_all()
    text = json.dumps(data, ensure_ascii=False, indent=2)

    if args.print:
        print(text)
    else:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        n_ok = sum(1 for t in data["teams"].values() if t["ok"])
        n_players = sum(len(t["players"]) for t in data["teams"].values())
        print(f"[cs2_rosters] wrote {out}: {n_ok}/{len(data['teams'])} teams, {n_players} players")
        for cid, t in data["teams"].items():
            flag = "" if t["ok"] else "  <-- fetch failed"
            print(f"  {t['abbr']:10} {t['liquipedia_page']:22} {t['players']}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
