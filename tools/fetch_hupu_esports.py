#!/usr/bin/env python3
"""Fetch Hupu's public esports schedule API -> normalized schedule cache.

虎扑「热门比赛 / 赛程」公共接口（从 hupu.com 首页赛程 H5 逆向得到，2026-09-08
实测可用，LOL/CS2 均返回实时比分与状态）：

    GET https://match-api.hupu.com/1/8.2.10/matchallapi/bff/standard/\
getScheduleListByTagForH5?businessType=common&datasource=navigation&businessId=lol|cs2

本脚本只做“事实层快照 + 归一化缓存”，不写任何比赛情报、不改 matches_today.json；
消费方（今日比赛页等）自行决定如何展示/合并。

用法：
  python3 tools/fetch_hupu_esports.py                    # 抓 LOL + CS2 -> data/hupu_esports_schedule.json
  python3 tools/fetch_hupu_esports.py --business lol     # 只抓 LOL
  python3 tools/fetch_hupu_esports.py --out /tmp/hupu.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "hupu_esports_schedule.json"

API = (
    "https://match-api.hupu.com/1/8.2.10/matchallapi/bff/standard/"
    "getScheduleListByTagForH5"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 "
        "Safari/604.1"
    ),
    "Accept": "application/json, text/plain, */*",
}

# 虎扑 businessId -> 我们展示用一级分类（AGENTS：一级=游戏）
BUSINESSES = {
    "lol": {"league": "LoL", "label": "英雄联盟赛程"},
    "cs2": {"league": "CS2", "label": "CS2赛程"},
}

STATUS_MAP = {
    "COMPLETED": "completed",
    "INPROGRESS": "inProgress",
    "NOTSTARTED": "notStarted",
}


def _fetch(business: str, timeout: int = 20) -> list[dict]:
    qs = urllib.parse.urlencode(
        {
            "businessType": "common",
            "datasource": "navigation",
            "businessId": business,
        }
    )
    req = urllib.request.Request(f"{API}?{qs}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not payload.get("success"):
        raise RuntimeError(
            f"hupu {business} api not success: "
            f"{payload.get('errorCode')} {payload.get('errorMsg')}"
        )
    return payload.get("result", {}).get("dayGameData", []) or []


def _iso_of_ms(ms: str | int | None) -> str:
    if ms in (None, ""):
        return ""
    try:
        dt = datetime.datetime.fromtimestamp(int(ms) / 1000, tz=datetime.timezone.utc)
        return dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, TypeError, OSError):
        return ""


def _bj_parts(ms: str | int | None) -> tuple[str, str]:
    """返回北京时间 (date, HH:MM)。"""
    iso = _iso_of_ms(ms)
    if not iso:
        return "", ""
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(
            datetime.timezone(datetime.timedelta(hours=8))
        )
        return dt.date().isoformat(), dt.strftime("%H:%M")
    except ValueError:
        return "", ""


def normalize_match(raw: dict, business: str) -> dict | None:
    """把虎扑单场记录归一化为我们通用字段（仅对团队对抗型比赛）。"""
    if raw.get("matchType") != "against":
        return None
    against = raw.get("againstInfo") or {}
    members = against.get("memberInfos") or []
    if len(members) != 2:
        return None
    status_raw = str(raw.get("matchStatus") or "").upper()
    status = STATUS_MAP.get(status_raw, status_raw.lower() or "")
    mid = str(raw.get("matchId") or "")
    if not mid:
        return None
    start_iso = _iso_of_ms(raw.get("matchStartTimeStamp"))
    date, hhmm = _bj_parts(raw.get("matchStartTimeStamp"))
    teams = [str(m.get("memberName") or "").strip() for m in members]
    scores = [
        str(m.get("memberBaseScore") or "-").strip()
        for m in members
    ]
    if not all(teams):
        return None
    score_key = raw.get("scoreItemKey") or {}
    return {
        "source": "hupu",
        "business_id": business,
        "league": BUSINESSES[business]["league"],
        "hupu_match_id": mid,
        "match_id": f"hupu-{business}-{mid}",
        "match_name": str(raw.get("matchName") or "").strip(),
        "tournament": str(
            raw.get("matchIntroduction") or raw.get("matchName") or ""
        ).strip(),
        "teams": teams,
        "scores": scores,
        "winner_member_id": str(against.get("winnerMemberId") or ""),
        "status": status,
        "status_label": str(raw.get("matchStatusDesc") or "").strip(),
        "start_iso": start_iso,
        "start_time_cst": f"{date} {hhmm}:00" if date else "",
        "date": date,
        "live_room_link": str(raw.get("liveRoomLink") or ""),
        "score_count_text": str(raw.get("scoreCountText") or "").strip(),
        # 选手评分链路所需：match 评分 key + 两队 memberId（供 getSelfByBizKey 等三级拉取）
        "score_item_key": {
            "out_biz_no": str(score_key.get("outBizNo") or ""),
            "out_biz_type": str(score_key.get("outBizType") or ""),
        },
        "member_ids": [
            {"name": str(m.get("memberName") or "").strip(), "member_id": str(m.get("memberId") or "")}
            for m in members
        ],
    }


def fetch_schedule(business_ids: list[str], timeout: int = 20) -> list[dict]:
    out: list[dict] = []
    for b in business_ids:
        if b not in BUSINESSES:
            continue
        for day in _fetch(b, timeout=timeout):
            for raw in day.get("matchData", []) or []:
                item = normalize_match(raw, b)
                if item is not None:
                    out.append(item)
    return out


def refresh_cache(
    business_ids: list[str] | None = None,
    out_path: Path = DEFAULT_OUT,
    timeout: int = 20,
) -> Path:
    """抓最新虎扑赛程并覆盖缓存文件。网络失败时保留旧缓存并抛错。"""
    ids = business_ids or list(BUSINESSES)
    matches = fetch_schedule(ids, timeout=timeout)
    now = datetime.datetime.now(datetime.timezone.utc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "source": "hupu match-api",
                "businesses": ids,
                "fetched_at_utc": now.isoformat(timespec="seconds").replace(
                    "+00:00", "Z"
                ),
                "fetched_at_cst": now.astimezone(
                    datetime.timezone(datetime.timedelta(hours=8))
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "matches": matches,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--business",
        default=",".join(BUSINESSES),
        help="逗号分隔的 businessId，默认 lol,cs2",
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--timeout", type=int, default=20)
    args = ap.parse_args()

    ids = [b.strip().lower() for b in args.business.split(",") if b.strip()]
    t0 = time.time()
    path = refresh_cache(ids, Path(args.out), timeout=args.timeout)
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = data.get("matches", [])
    print(
        f"[hupu] wrote {path} in {time.time()-t0:.1f}s: "
        f"{len(matches)} matches"
    )
    for m in matches:
        print(
            " ",
            m["league"],
            m["date"],
            m["status"],
            m["start_time_cst"],
            " vs ".join(m["teams"]),
            m.get("tournament"),
        )


if __name__ == "__main__":
    main()
