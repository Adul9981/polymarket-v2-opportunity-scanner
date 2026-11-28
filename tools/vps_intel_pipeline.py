#!/usr/bin/env python3
"""VPS intel pipeline: match end detection -> slice -> rule intel -> Codex report.

服务器端：由 systemd timer 每 5 分钟触发（--once），读取 data/matches_today.json
（本地 export_today_matches.py 生成后同步），对每场"未完成"比赛：
  1) verify_match_end.py 弹幕多信号检测结束（确认/需人工确认均触发，结果标待确认）；
  2) 按比赛开始时间切片弹幕 -> danmu_intel.py 规则层情报 JSON；
  3) codex exec（DeepSeek）按 intel-report 技能 + 情报模板生成整场情报页 HTML；
  4) 状态写入 runtime/vps_intel/<match>.json（幂等，已完成跳过）。

用法：
  python3 tools/vps_intel_pipeline.py --once        # 定时触发（每 5 分钟）
  python3 tools/vps_intel_pipeline.py --match <id>  # 指定比赛跑一次
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import functools
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

import danmu_intel
import fetch_hupu_player_ratings
import render_node_page
import render_pregame

ROOT = Path(os.environ.get("DANMU_INTEL_ROOT", "/opt/danmu-intel"))
MATCHES = ROOT / "data" / "matches_today.json"
STATE_DIR = ROOT / "runtime" / "vps_intel"
SLICE_DIR = ROOT / "data" / "intel_slices"
REPORTS = ROOT / "reports"
DANMU = ROOT / "docs" / "data" / "danmu"
PY = os.environ.get("INTEL_PY", str(ROOT / ".venv" / "bin" / "python"))
CODEX = os.environ.get("CODEX", "/root/.local/bin/codex")
# AI 后端：codex（默认，VPS 现状）| deepseek（直连 DeepSeek API，本地无需 codex CLI）
AI_BACKEND = os.environ.get("DANMU_INTEL_AI", "codex")
MAX_MATCH_WORKERS = int(os.environ.get("INTEL_MAX_MATCH_WORKERS", "3"))  # 跨比赛并行度（③ 2026-10-18）
LIVE_INTERVAL_SEC = 1800  # 局中情报快照限频：30 分钟一份
GAME_BP_GAP_MIN = 8    # 开赛/上一局结束后到本小局 BP 的估计间隔（分钟）
GAME_NODE_BP_MIN = 4   # 小局 BP 后/开局节点：小局开始后 X 分钟（2026-08-26 由 12+8 提速）
GAME_BP_GAP_MIN_CS2 = 0     # CS2 market gameStartTime 已接近地图开始，不再加 LoL 式 BP 间隔
GAME_NODE_BP_MIN_CS2 = 2    # CS2 开赛后 2 分钟允许生成 G1 BP/开局节点
GAME_NODE_MID_MIN = 16  # 小局局中节点：小局开始后 X 分钟（由 22 提速）
GAME_NODE_BP_MAX_MIN = 20  # BP 后节点最晚窗口（错过则不再补发，避免"BP后"内容失真）
MAX_GAME = 5
GAME_STATUS_FILE = ROOT / "data" / "game_status.json"
GAME_STATUS_FRESH_SEC = 1200  # 本地推送的小局状态 20 分钟内视为新鲜


def _match_is_cs2(match: dict[str, Any]) -> bool:
    league = str((match or {}).get("league") or "").upper()
    game = str((match or {}).get("game") or (match or {}).get("sport") or "").lower()
    return league.startswith("CS2") or game == "cs2"


def bp_gap_minutes(match: dict[str, Any]) -> int:
    return GAME_BP_GAP_MIN_CS2 if _match_is_cs2(match) else GAME_BP_GAP_MIN


def bp_node_wait_minutes(match: dict[str, Any]) -> int:
    return GAME_NODE_BP_MIN_CS2 if _match_is_cs2(match) else GAME_NODE_BP_MIN

# 2026-08-29：时间轴壳匹配增强——队伍别名（team_names.json）与联赛前缀
# （LCK-/CS2-/LPL- 等文件名）支持。教训：BRO-BFX 全称节点页与短名 teams
# 无法匹配导致壳丢节点；整场复盘页带 LCK-/CS2- 前缀时无法入壳。
_TEAM_ROWS: list[dict] | None = None


def _team_rows() -> list[dict]:
    global _TEAM_ROWS
    if _TEAM_ROWS is None:
        try:
            d = json.loads((ROOT / "docs" / "data" / "intel" / "team_names.json").read_text(encoding="utf-8"))
            _TEAM_ROWS = d.get("teams", []) if isinstance(d, dict) else []
        except OSError:
            _TEAM_ROWS = []
    return _TEAM_ROWS


def _team_id(name: str) -> str:
    """队名 -> team_names.json 的 id（无法归一则返回去点空格小写，供模糊比较）。

    Polymarket outcomes 是全称（"Hanwha Life Esports"），teams 是缩写（"HLE"），
    统一归一到 id 后比较。队名唯一权威 = docs/data/intel/team_names.json。
    """
    n = re.sub(r"[.\s]", "", (name or "").lower())
    for row in _team_rows():
        for k in (row.get("abbr"), row.get("full"), *(row.get("aliases") or [])):
            if k and n == re.sub(r"[.\s]", "", str(k).lower()):
                return row.get("id") or n
    return n


def _winner_side(mk: dict | None, teams: list[str]) -> str | None:
    """小局结算 winner -> 'A'/'B'（teams[0]/teams[1]）。映射失败返回 None（不硬写结果）。

    红线：官方胜方无法唯一对齐到某队时不猜、返回 None，调用方降级为弹幕口径 + 待核对。
    """
    if not isinstance(mk, dict) or mk.get("winner") not in (0, 1):
        return None
    outcomes = mk.get("outcomes") or []
    if not isinstance(outcomes, list) or len(outcomes) < 2:
        return None
    wname = _team_id(str(outcomes[mk["winner"]] or ""))
    if not wname:
        return None
    for i, t in enumerate(teams[:2]):
        if _team_id(t) == wname:
            return "A" if i == 0 else "B"
    return None


GAME_EST_LEN_MIN = 35  # 无市场状态时的小局时长估计（LoL BO 系列）
GAME_MIN_LEN_MIN = 20  # gg 信号最早可信时间：开局 <20 分钟判"局末"一律算噪声（CS2 教训）
GAME_EST_LEN_MIN_CS2 = 55  # CS2 地图含加时可 40-60 分钟，时间窗估算更保守（10-16 OT 教训）
GG_END_KW = (
    "gg", "恭喜", "拿下", "结束了", "结束比赛", "下一把", "下把", "第二局", "第三局",
    "第四局", "第五局", "2:0", "2-0", "1:1", "1-1", "2:1", "2-1", "승리", "끝",
    "다음 경기", "next game", "game 2", "game 3",
)
MATCH_END_KW = (
    "晋级", "晋级了", "横扫", "夺冠", "出局", "3:0", "3-0", "3:1", "3-1",
    "3:2", "3-2", "series over", "sweep", "win the series",
)


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def format_of(m: dict) -> int:
    """系列赛格式（BO1/BO3/BO5）：从比赛元数据 format 或标题解析，默认 5。

    2026-08-25 用户要求：BO1/BO3/BO5 必须区分，决定节点框架上限，
    防止 BO3 结束后误生成不存在的 G4/G5 节点。
    """
    fmt = m.get("format")
    if isinstance(fmt, int) and fmt > 0:
        return min(fmt, MAX_GAME)
    if isinstance(fmt, str):
        mm = re.search(r"BO\s*(\d+)", fmt, re.I)
        if mm:
            return min(int(mm.group(1)), MAX_GAME)
    title = m.get("title") or ""
    mm = re.search(r"BO\s*(\d+)", title, re.I)
    if mm:
        return min(int(mm.group(1)), MAX_GAME)
    return MAX_GAME


def _series_decided(gstatus: dict, max_games: int) -> bool:
    """系列赛是否已决出胜负（某队已拿到半数以上胜场）。

    2026-10-29 固化：BO3 2-0 / BO5 3-0 收官时，后续小局市场不会存在，
    game_status 只有已结算的小局；若无此判定，流水线会在缺失市场的小局走
    兜底时间窗误生成不存在的 G3/G4 节点（教训：MKOI-T1 2-0 却生成 g3_bp/mid/end）。
    """
    wins: dict[int, int] = {}
    for mk in gstatus.values():
        w = mk.get("winner") if isinstance(mk, dict) else None
        if w is not None:
            wins[w] = wins.get(w, 0) + 1
    need = max_games // 2 + 1
    return any(c >= need for c in wins.values())


def _series_settled(slug_id: str, max_games: int) -> bool:
    """系列赛是否已在结构上结算（所有小局 closed 或某队已拿半数以上胜场）。

    2026-11-01 固化：process_match 的路由仲裁——弹幕 verify_end 的「确认结束」
    是软信号（G1 结束后就会误触发），必须用 game_status 的结构事实来仲裁；
    未结算时即使弹幕判结束，也必须继续走小局节点路径出 G2+ 节点
    （教训：HLE-BLG 2-0，弹幕在 G1 后就判「确认结束」把流水线卡进终局门禁的
    return，G2 bp/mid/end 全丢，整场只剩 G1 + 终局复盘）。
    BO1（max_games<=1）无系列结构，恒真（与旧门禁 max_games>1 才仲裁一致）。
    game_status 过期/缺失（read_game_status 返回 None）视为未结算，路由到小局
    路径兜底，不提前终局。
    """
    if max_games <= 1:
        return True
    gs_now = read_game_status(slug_id) or {}
    all_closed = all(
        bool((gs_now.get(i) or {}).get("closed"))
        or (gs_now.get(i) or {}).get("winner") is not None
        for i in range(1, max_games + 1)
    )
    return all_closed or _series_decided(gs_now, max_games)


def _closed_non_polymarket_skip(m: dict, mid: str) -> bool:
    """已结束的非 Polymarket 场次是否应跳过（避免误切片）。

    2026-10-16 固化：closed 的 hupu/官方场次无 Polymarket 小局市场，走兜底时间窗切片
    会把闲时/他场弹幕误切成该场节点（教训：C9-KC / FUR-MVK / Legacy-FURIA 被误生成
    G1 节点，Aurora-9z 弹幕混入 Legacy-FURIA）。
    2026-10-25 回归修复：原来无条件 return 会截断"生成到一半"的场次——场次 closed 常早于
    Codex 逐个跑完节点（4-5 分钟/个），导致 g1_end/g2_bp 等后半程节点永久缺失
    （如 cs2-hupu-1441778164564995316 只剩 pre/g1_bp/g1_mid）。修正：仅当该场从未开始
    生成过任何小局节点（无 {mid}_g*_*.json 状态）才跳过；已开始生成的场次继续跑完剩余
    节点（窗口已被真实开局/anchor_next_game 锚定，不会按 close 后的闲时弹幕误切片，
    与 001b298 之前的旧行为一致）。
    """
    if not (m.get("closed") and (m.get("_hupu") or m.get("_official"))):
        return False
    return not any(STATE_DIR.glob(f"{mid}_g*_*.json"))


def _hupu_total_games(m: dict) -> int | None:
    """从 data/hupu_esports_schedule.json 读该场官方比分，返回总局数（如 2:0 -> 2）。

    用于 closed 的 hupu 场次：无 Polymarket 小局市场，format_of 拿不到 BO 数（默认 5），
    兜底时间窗会按 max_games 生成不存在的 G3/G4/G5 节点（10-16 教训：2-0 场次被补假节点）。
    官方比分是唯一权威的"实际打了几局"信号；找不到或比分为空返回 None（退回 format_of）。
    """
    if not m.get("_hupu"):
        return None
    sched = ROOT / "data" / "hupu_esports_schedule.json"
    if not sched.exists():
        return None
    try:
        data = json.loads(sched.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    entries = data.get("matches", data) if isinstance(data, dict) else data
    mid = str(m.get("id") or "")
    hupu_id = mid.rsplit("-", 1)[-1] if "-" in mid else mid
    for e in entries:
        if str(e.get("hupu_match_id") or "") != hupu_id and str(e.get("match_id") or "") != mid:
            continue
        total = 0
        for s in e.get("scores") or []:
            try:
                total += int(s)
            except (ValueError, TypeError):
                pass
        return total if total > 0 else None
    return None


def _hupu_score_state(m: dict) -> tuple[int | None, bool]:
    """读 hupu 实时比分：返回 (已结束局数, 系列是否已结束)。

    进行中的 hupu 场次没有 Polymarket 小局市场，官方比分 scores（如 ["0","1"]）
    是唯一权威的"打到第几局 / 小局是否结束 / 系列是否结束"信号；弹幕 GG 兜底
    会在 G2 就被赛事级闲谈（夺冠/晋级/出局）误判系列结束（教训：Vitality vs MOUZ）。
    找不到场次/无比分字段返回 (None, False)，调用方退回弹幕兜底。
    """
    if not m.get("_hupu"):
        return None, False
    sched = ROOT / "data" / "hupu_esports_schedule.json"
    if not sched.exists():
        return None, False
    try:
        data = json.loads(sched.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None, False
    entries = data.get("matches", data) if isinstance(data, dict) else data
    mid = str(m.get("id") or "")
    hupu_id = mid.rsplit("-", 1)[-1] if "-" in mid else mid
    for e in entries:
        if str(e.get("hupu_match_id") or "") != hupu_id and str(e.get("match_id") or "") != mid:
            continue
        scores = e.get("scores")
        if not isinstance(scores, list) or not scores:
            return None, False
        played = 0
        for s in scores:
            try:
                played += int(s)
            except (ValueError, TypeError):
                pass  # "-" 等占位符跳过，与 _hupu_total_games 一致
        completed = (
            str(e.get("status") or "").lower() in ("completed", "finished", "closed")
            or bool(e.get("winner_member_id"))
        )
        return played, completed
    return None, False


def verify_end(teams: list[str], inputs: list[Path]) -> str:
    cmd = [str(PY), str(ROOT / "tools" / "verify_match_end.py"), "--end", now_iso()]
    for p in inputs:
        cmd += ["--input", str(p)]
    if teams:
        cmd += ["--teams", ",".join(teams)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.stdout or r.stderr or ""
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def slice_rows(start_iso: str, files: list[Path], out: Path, end_iso: str = "") -> int:
    try:
        # 2026-08-26 教训：此前 -1800（切片起点自动前移 30 分钟）会把
        # 开赛前等待期杂音混进节点切片（KT-BRO 07:27、Spirit 11:28 均因此混入
        # 赛前闲聊/其他联赛内容）——节点切片起点必须精确，不再前移。
        start_ts = datetime.datetime.fromisoformat(
            str(start_iso).replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        start_ts = 0
    end_ts = None
    if end_iso:
        try:
            end_ts = datetime.datetime.fromisoformat(str(end_iso).replace("Z", "+00:00")).timestamp()
        except ValueError:
            end_ts = None
    def _ts(r: dict):
        u = r.get("unixtime")
        if u is not None:
            return float(u)
        t = r.get("ts")
        if isinstance(t, (int, float)):
            return float(t)  # 虎牙：数值 unix 时间戳（教训 2026-08-26：曾被当 ISO 解析失败而整行丢弃）
        try:
            return datetime.datetime.fromisoformat(
                str(t).replace("+0800", "+08:00")
            ).timestamp()
        except Exception:  # noqa: BLE001
            return None

    rows = []
    for p in files:
        try:
            fh = open(p, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _ts(r)
                if ts and ts >= start_ts and (end_ts is None or ts <= end_ts):
                    rows.append(r)
    rows.sort(key=lambda x: _ts(x) or 0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def fetch_game_markets(slug: str) -> dict[int, dict]:
    """拉取该事件的小局赢家市场（Game/Map N Winner），返回 {局数: {closed, prices, winner_idx}}。

    小局结束的可靠信号：市场 closed 或某一侧 outcomePrice >= 0.99（Polymarket 结算）。
    """
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 danmu-intel"})
        evs = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception:  # noqa: BLE001
        return {}
    if not evs:
        return {}
    out: dict[int, dict] = {}
    for mk in evs[0].get("markets", []):
        q = mk.get("question", "") or ""
        mm = re.search(r"(?:Game|Map)\s*(\d+)\s*Winner", q, re.I)
        if not mm:
            continue
        gi = int(mm.group(1))
        raw = mk.get("outcomePrices")
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            prices = [float(p) for p in (raw or [])]
        except (ValueError, TypeError, json.JSONDecodeError):
            prices = []
        winner = None
        if len(prices) >= 2:
            if prices[0] >= 0.99:
                winner = 0
            elif prices[1] >= 0.99:
                winner = 1
        # 2026-10-31：官方结果回填——outcomes 全称队名数组（顺序与 prices 一致），
        # 供 winner=0/1 映射到具体队名（与 fetch_game_status.py 口径一致）。
        raw_out = mk.get("outcomes")
        try:
            if isinstance(raw_out, str):
                raw_out = json.loads(raw_out)
            outcomes = list(raw_out or [])
        except (ValueError, TypeError, json.JSONDecodeError):
            outcomes = []
        out[gi] = {
            "closed": bool(mk.get("closed")),
            "prices": prices,
            "winner": winner,
            "outcomes": outcomes,
        }
    return out


def read_game_status(slug: str) -> dict[int, dict] | None:
    """读取本地推送的小局结算状态（本机拉取，服务器直连 Polymarket 被 451 限制）。

    状态文件过期（>20 分钟）视为不可用，返回 None。
    键统一转 int（JSON 文件里键是字符串；教训 2026-08-25：get(1) 取不到 '1'
    导致每局都退回时间窗估算，第 3 局结束节点被跳过）。
    """
    try:
        d = json.loads(GAME_STATUS_FILE.read_text(encoding="utf-8"))
        gen = datetime.datetime.fromisoformat(
            str(d.get("generated_at", "")).replace("Z", "+00:00")
        )
        if (datetime.datetime.now(datetime.timezone.utc) - gen).total_seconds() > GAME_STATUS_FRESH_SEC:
            return None
        raw = d.get("games", {}).get(slug) or {}
        return {int(k): v for k, v in raw.items()}
    except Exception:  # noqa: BLE001
        return None


def _row_ts(r: dict) -> float | None:
    """弹幕行时间戳 -> epoch 秒（统一处理 unixtime / 数值 ts / ISO ts 三种来源）。

    虎牙写数值 unix ts（无 unixtime 字段），其他源可能写 unixtime 或 ISO ts。
    教训 2026-10-31：detect_game_end_gg / detect_match_end_gg 曾只按 ISO 解析
    ts，虎牙数值 ts 被 fromisoformat 抛异常整行丢弃，GG/系列结束兜底对虎牙恒 False。
    """
    u = r.get("unixtime")
    if u is not None:
        try:
            return float(u)
        except (TypeError, ValueError):
            return None
    t = r.get("ts")
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, str):
        try:
            return datetime.datetime.fromisoformat(
                t.replace("+0800", "+08:00")
            ).timestamp()
        except (ValueError, TypeError):
            return None
    return None


def detect_game_end_gg(files: list[Path], since: datetime.datetime) -> bool:
    """近 8 分钟弹幕 GG/局间关键词突发检测（兜底信号，非权威）。"""
    now = time.time()
    lo = max(since.timestamp(), now - 480)
    hits = 0
    for p in files:
        try:
            fh = open(p, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _row_ts(r)
                if ts is None or ts < lo:
                    continue
                msg = (r.get("message") or r.get("text") or "").lower()
                if any(k in msg for k in GG_END_KW):
                    hits += 1
                    if hits >= 8:
                        return True
    return False


def detect_match_end_gg(files: list[Path], since: datetime.datetime) -> bool:
    """近 10 分钟弹幕系列结束关键词检测（兜底：防止给已结束系列补 G4/G5 假节点）。"""
    now = time.time()
    lo = max(since.timestamp(), now - 600)
    hits = 0
    for p in files:
        try:
            fh = open(p, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _row_ts(r)
                if ts is None or ts < lo:
                    continue
                msg = (r.get("message") or r.get("text") or "").lower()
                if any(k in msg for k in MATCH_END_KW):
                    hits += 1
                    if hits >= 5:
                        return True
    return False


def load_match(mid: str) -> dict | None:
    """按 id/slug 从 data/matches_today.json 读一场比赛条目（评分/累积胜率共用）。"""
    try:
        if not MATCHES.exists():
            return None
        data = json.loads(MATCHES.read_text(encoding="utf-8"))
        matches = data.get("matches", []) if isinstance(data, dict) else data
        for mm in matches:
            if (mm.get("id") or mm.get("slug")) == mid:
                return mm
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] {mid}: load_match failed ({e})", flush=True)
    return None


def fetch_ratings(mid: str, gi: int) -> dict | None:
    """拉该场指定小局 gi 的虎扑选手评分（strict_game，防串局；失败/无 key 返回 None，不阻塞）。

    2026-10-18 口径定稿（按小局冻结）：节点页评分 = 本小局评分，生成后冻结；
    每小局各显示自己的评分，不随后续小局变化（G1 页永远显示 G1 的评分）。
    """
    mm = load_match(mid)
    if not mm:
        return None
    try:
        obn = str(mm.get("hupu_score_out_biz_no") or "").strip()
        if not obn:
            return None
        obt = str(mm.get("hupu_score_out_biz_type") or "").strip() or "lol_match"
        return fetch_hupu_player_ratings.fetch_player_ratings(obn, obt, gi, strict_game=True)
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] {mid}: ratings fetch skipped ({e})", flush=True)
    return None


def fetch_lineup(mid: str) -> dict[str, str] | None:
    """拉该场首发阵容 {选手名: 队伍名}（虎扑评分树最新一局 roster，比赛期间可用）。

    与 fetch_ratings 不同：不 strict_game（阵容同系列固定，取最新局即可），
    用于把选手表态折算进【比赛局势】胜率。失败/无 key 返回 None，调用方降级到
    静态 PLAYER_TEAM（danmu_intel 内部已有该兜底）。
    """
    mm = load_match(mid)
    if not mm:
        return None
    try:
        obn = str(mm.get("hupu_score_out_biz_no") or "").strip()
        if not obn:
            return None
        obt = str(mm.get("hupu_score_out_biz_type") or "").strip() or "lol_match"
        lineup = fetch_hupu_player_ratings.fetch_lineup(obn, obt)
        return lineup or None
    except Exception as e:  # noqa: BLE001
        print(f"[pipeline] {mid}: lineup fetch skipped ({e})", flush=True)
    return None


def game_start_iso(mid: str, gi: int) -> str | None:
    """本小局起点 ISO：优先 mid 节点 slice_from（= 本局 g_start），退回 bp 节点（≈ g_start-15min）。

    【比赛局势】"本小局切片"口径的唯一锚点（独立局势页 + 情报页比赛局势栏共用，2026-11-02 统一）。
    无状态文件（该局节点未生成 / 未开打）返回 None，调用方降级评分 70/30 或 50/50。
    """
    for phase in ("mid", "bp"):
        p = STATE_DIR / f"{mid}_g{gi}_{phase}.json"
        try:
            st = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if st.get("slice_from"):
            return str(st["slice_from"])
    return None


def game_win_signal(
    mid: str,
    gi: int,
    teams: list[str],
    files: list[Path],
    game: str | None = None,
    lineup: dict[str, str] | None = None,
    end_iso: str = "",
) -> dict | None:
    """本小局胜负弹幕信号：切片 [本局起点 -> 结束/现在] 重算 win_signal（近 5 分钟口径，样本不足回退本局累积）。

    独立局势页 + 情报页比赛局势栏统一用此口径（2026-11-02 以情报页"本小局切片"为准，
    弃用整场全量弹幕）。本局起点取 game_start_iso；无状态文件返回 None（调用方降级）。
    end_iso 为空 = 切到 now（进行中局）；已结束局传本局结束上界（game_end_iso），封闭切片。
    lineup 传虎扑首发阵容（可 None，danmu_intel 内部回退静态 PLAYER_TEAM）。
    """
    game_start = game_start_iso(mid, gi)
    if not game_start:
        return None
    slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
    tmp = SLICE_DIR / f"{slug_id}_g{gi}_situation.jsonl"
    try:
        slice_rows(game_start, files, tmp, end_iso)
        rows = [json.loads(ln) for ln in tmp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return danmu_intel.win_signal(rows, teams, game=game, player_teams=lineup)
    except Exception:  # noqa: BLE001
        return None


def game_end_iso(mid: str, gi: int) -> str | None:
    """本局结束上界 ISO：下一局起点（gi+1 的 mid/bp slice_from）优先，退回本局 end 节点 generated_at。

    已结束局「本小局切片」的封闭上界（2026-11-02 与情报页冻结口径对齐）：进行中局的切片
    切到 now，已结束局用此上界封闭，避免把后续局/局间弹幕混进本局胜率。下一局起点是
    稳定锚点（下一局节点生成后即固定，不随刷新滑动）；取不到返回 None（调用方降级评分/50:50）。
    """
    nxt = game_start_iso(mid, gi + 1)
    if nxt:
        return nxt
    p = STATE_DIR / f"{mid}_g{gi}_end.json"
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if st.get("generated_at"):
        return str(st["generated_at"])
    return None


_CANONICAL_HEADER_CSS = (
    "/* canonical-header (pipeline-pinned 2026-11-01): stop per-node Codex CSS drift */"
    "body{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','PingFang SC',"
    "'Microsoft YaHei',sans-serif !important;}"
    "h1{font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','PingFang SC',"
    "'Microsoft YaHei',sans-serif !important;font-size:24px !important;"
    "line-height:1.25 !important;font-weight:800 !important;letter-spacing:-.02em !important;}"
)


def _pin_header_css(report: Path) -> None:
    """钉死节点页头部 CSS（幂等）：Codex 每次独立生成，h1 字号/字体族/字重漂移。

    2026-11-01 KC-MKOI 教训：同一场比赛各节点页的 <h1>Karmine Corp vs Movistar KOI</h1>
    被 Codex 各自现编的 <style> 渲染成 26px / clamp(25..35px) / clamp(32..54px)，字体族也
    或 Helvetica Neue 或 Microsoft YaHei——prompt 只写了「系统字体栈」，约束不住。故生成后
    把固定覆盖样式注入 </head> 前，用 !important 压过 Codex 任意漂移，保证所有节点页标题区一致。
    """
    try:
        html = report.read_text(encoding="utf-8")
    except OSError as e:  # noqa: BLE001
        print(f"[pipeline] pin header css failed: {e}", flush=True)
        return
    if "canonical-header" in html:
        return  # 已注入，幂等
    tag = f"<style>{_CANONICAL_HEADER_CSS}</style>"
    idx = html.rfind("</head>")
    if idx < 0:
        # 无 </head>（异常/裸 body 页）：插到 <body 开标签前，浏览器仍会应用 <style>。
        b = html.find("<body")
        if b < 0:
            return
        html = html[:b] + tag + html[b:]
    else:
        html = html[:idx] + tag + html[idx:]
    report.write_text(html, encoding="utf-8")


def _inject_situation(report: Path, intel_json: Path, ratings: dict | None, teams: list[str], gphase: str = "") -> None:
    """codex 页后置注入【比赛局势】卡片（规则层块，幂等：卡片内无占位签名则跳过）。

    占位符是 codex 按 prompt 输出的「2 比赛局势（系统注入，本段不写）」卡片，结构随模型
    输出漂移：标题里「（系统注入」常被丢；占位正文/注释/CSS 也变（system-slot /
    system-placeholder / data-system-inject / 系统注入占位…）。故**不锚「系统注入」文本**
    （2026-11-01 教训：那串字会漂进 <head> 的 CSS `.system-slot::before { content:"系统注入…" }`，
    注入函数命中 CSS 后找不到外层 <section>，静默跳过 → 比赛局势卡空，LOS-LYON 等 9 页中招）。
    稳定锚点改用卡片标题「比赛局势」（body-only、占位卡与真实卡都有）。幂等改用**卡片容器内**
    是否仍含占位签名（data-system-inject / class="system / 系统注入）判定——真实卡片
    （situation_card 输出，含 WIN/RATINGS 标记）不含这些签名。这里按锚点定位外层卡片容器
    （`<section>` / `<article>` / `<div class="card">`）并**整体替换**成真实卡片
    （替换而非插入，避免残留占位符与重复块）。
    """
    try:
        html = report.read_text(encoding="utf-8")
        # 稳定锚点：卡片标题「比赛局势」（body-only，不受 CSS content 假阳性影响）。
        anchor = html.find("比赛局势")
        if anchor < 0:
            return  # 无该卡片（非本路径），跳过
        # 占位容器可能是 <section> / <article> / <div class="card">（Codex 输出漂移），
        # 取锚点前最近的这三种开标签及其对应闭标签，整体替换。
        # 教训：MOUZ-9z / T1-CTBC 用 <article>；2026-11-01 发现 LoL 场次（KC vs MKOI）
        # 漂移成 <div class="card">——此前只认 section/article，div 包裹的页注入静默跳过
        # -> 比赛局势卡无更新标记 -> refresh_situation 更新不了 -> 卡片冻结。
        open_tag = html.rfind("<section", 0, anchor)
        close_marker = "</section>"
        art_tag = html.rfind("<article", 0, anchor)
        if art_tag > open_tag:
            open_tag = art_tag
            close_marker = "</article>"
        card_tag = html.rfind('<div class="card"', 0, anchor)
        if card_tag > open_tag:
            open_tag = card_tag
            close_marker = "</div>"
        if open_tag < 0:
            return
        if close_marker == "</div>":
            # div 会嵌套（卡片内还有 winrow/barfill 等子 div），不能 find 第一个 </div>，
            # 否则「系统注入」若出现在卡片中段会把内层 div 闭标签当卡片结尾截断卡片。
            # 从 open_tag 起按 <div>/</div> 深度计数找匹配闭标签（2026-11-01 修冻结）。
            depth = 0
            pos = open_tag
            close_tag = -1
            while pos < len(html):
                nxt_open = html.find("<div", pos)
                nxt_close = html.find("</div>", pos)
                if nxt_close < 0:
                    break  # 不平衡，放弃本次注入
                if nxt_open != -1 and nxt_open < nxt_close:
                    depth += 1
                    pos = nxt_open + 1
                else:
                    depth -= 1
                    pos = nxt_close + len("</div>")
                    if depth == 0:
                        close_tag = pos
                        break
            if close_tag < 0:
                return
        else:
            close_tag = html.find(close_marker, anchor)
            if close_tag < 0:
                return
            close_tag += len(close_marker)
        # 幂等：只当卡片容器内仍有占位签名时才注入；真实卡片（situation_card 输出，
        # 含 WIN/RATINGS 标记、无这些签名）跳过。判据必须放在卡片容器内——「系统注入」
        # 会漂进 <head> 的 CSS .system-slot::before content，卡片外判据会被 CSS 假阳性
        # 骗到而漏注入（2026-11-01 LOS-LYON 等 9 页空卡教训）。
        card_seg = html[open_tag:close_tag]
        if not (
            "data-system-inject" in card_seg
            or 'class="system' in card_seg
            or "class='system" in card_seg
            or "系统注入" in card_seg
        ):
            return
        stats: dict = {}
        try:
            stats = json.loads(intel_json.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            stats = {}
        block = render_node_page.situation_card(stats, ratings, teams)
        # 进行中的 bp/mid 节点附加 60s 实时轮询脚本（绕过 GitHub Pages 10min 缓存）；end 冻结不注入。
        if gphase in ("bp", "mid"):
            block += render_node_page.situation_poll_script()
        html = html[:open_tag] + block + html[close_tag:]
        report.write_text(html, encoding="utf-8")
    except OSError as e:
        print(f"[pipeline] inject situation failed: {e}", flush=True)


def _insufficient_node_html(teams: list[str], date: str, gi: int, gphase: str, game: str = "lol") -> str:
    """0 样本节点占位页（无样本不硬撑，跳过 Codex/DeepSeek，避免 report missing 死循环）。

    教训 2026-10-26：CS2 弹幕源离线（0 样本）时，Codex 偶发 rc=0 但不落盘，
    导致 generate_game_node 每 5 分钟空转重试（MongolZ-MOUZ g1_bp/g1_end）。
    结构与 Codex 全量页一致：1 BP 锚点 → 2 比赛局势（_inject_situation 注入）→
    3 方向性情报板 → 4 灰信号汇总，各段写「样本不足 / 今日无信号」。
    BP 栏按 game 分口径（2026-11-21）：cs2=地图禁选，lol/dota2=选人。
    """
    gph = {"bp": "BP 后/开局", "mid": "局中", "end": "局末/局间"}.get(gphase, gphase)
    bp_title = "BP 锚点与地图禁选情报" if game == "cs2" else "BP 锚点与选人情报"
    bp_empty = "地图禁选" if game == "cs2" else "BP/阵容"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{teams[0]} vs {teams[1]} · G{gi} {gph} 弹幕情报快照 · {date}</title>
<style>
  :root {{ --bg:#f5f5f7; --card:#fff; --ink:#1d1d1f; --sub:#6e6e73; --line:#e5e5ea; --soft:#f1f2f5; --accent:#0071e3; --accent-soft:#eaf3ff; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; line-height:1.65; padding:24px 14px 56px; }}
  .wrap {{ max-width:920px; margin:0 auto; }}
  .hero {{ background:var(--card); border-radius:18px; padding:24px; box-shadow:0 1px 5px rgba(0,0,0,.05); }}
  .eyebrow {{ color:var(--accent); font-size:12px; font-weight:700; letter-spacing:.04em; }}
  h1 {{ font-size:24px; line-height:1.25; letter-spacing:-.02em; margin:7px 0 12px; }}
  .badges {{ display:flex; flex-wrap:wrap; gap:7px; }}
  .badge {{ display:inline-flex; align-items:center; min-height:25px; border-radius:999px; padding:3px 10px; background:var(--soft); color:var(--sub); font-size:11.5px; font-weight:650; }}
  .badge.primary {{ background:var(--accent); color:#fff; }}
  .card {{ background:var(--card); border-radius:18px; padding:22px 20px; margin-top:16px; box-shadow:0 1px 5px rgba(0,0,0,.05); }}
  h2 {{ font-size:18px; display:flex; align-items:center; gap:10px; margin-bottom:12px; }}
  h2 .no {{ display:inline-flex; align-items:center; justify-content:center; width:24px; height:24px; border-radius:50%; background:var(--accent); color:#fff; font-size:13px; font-weight:700; flex:none; }}
  .empty {{ color:var(--sub); font-size:14px; padding:6px 0; }}
  .note {{ color:var(--sub); font-size:12px; margin-top:8px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="eyebrow">弹幕情报 · 节点快照</div>
    <h1>{teams[0]} vs {teams[1]}</h1>
    <div class="badges"><span class="badge primary">G{gi} · {gph}</span><span class="badge">样本不足 · 无弹幕数据</span></div>
  </div>
  <div class="card">
    <h2><span class="no">1</span>{bp_title}（弹幕讨论 · 非确认）</h2>
    <p class="empty">样本不足 — 本节点窗口无弹幕数据，{bp_empty}情报无法确认（弹幕口径 · 待官方）。</p>
  </div>
  <section>
    <h2><span class="no">2</span>比赛局势（系统注入，本段不写）</h2>
    <p class="empty">系统注入占位：比赛局势（胜率 + 虎扑评分）。</p>
  </section>
  <div class="card">
    <h2><span class="no">3</span>方向性情报板（正锚 × 负锚 × 共识 × 灰信号条件预测）</h2>
    <p class="empty">样本不足 — 本节点窗口无弹幕数据，暂无方向性共识；今日无锚点、共识不足。</p>
  </div>
  <div class="card">
    <h2><span class="no">4</span>灰信号汇总（风险 · 观众质疑非结论）</h2>
    <p class="empty">今日无灰信号。</p>
  </div>
</div>
</body>
</html>"""


def generate_game_node(
    mid: str,
    teams: list[str],
    date: str,
    slug_id: str,
    gi: int,
    gphase: str,
    slice_from: datetime.datetime,
    files: list[Path],
    end_basis: str = "",
    slice_end: str = "",
    late: bool = False,
    max_games: int = MAX_GAME,
    winner_side: str | None = None,
) -> None:
    """生成一个小局节点（幂等，成功后写状态；失败不写，下轮重试）。"""
    st = STATE_DIR / f"{mid}_g{gi}_{gphase}.json"
    if st.exists():
        return
    slice_file = SLICE_DIR / f"{slug_id}_g{gi}_{gphase}.jsonl"
    n = slice_rows(slice_from.isoformat(), files, slice_file, slice_end)
    intel_json = STATE_DIR / f"{slug_id}_g{gi}_{gphase}_intel.json"
    lineup = fetch_lineup(mid)
    cmd = [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
           "--input", str(slice_file), "--out", str(intel_json),
           "--teams", ",".join(teams)]
    if lineup:
        lineup_file = STATE_DIR / f"{slug_id}_g{gi}_{gphase}_lineup.json"
        try:
            lineup_file.write_text(json.dumps(lineup, ensure_ascii=False), encoding="utf-8")
            cmd += ["--players", str(lineup_file)]
        except OSError:
            pass
    subprocess.run(cmd, timeout=180, check=False)
    # 2026-08-26 用户定稿：弃用快节点输出（未经验证、结构混乱），
    # 恢复 Codex 全量路径——时效可稍慢（数分钟），但信息准确、结构清晰（昨日标准）。
    # 2026-09-27 本地适配：DANMU_INTEL_AI=deepseek 时走 fast_intel_node 直连 DeepSeek，
    # 本地无 codex CLI 也能生成情报页；默认仍走 codex（VPS 现状不变）。
    # 2026-10-18【比赛局势】栏：胜率来自 intel_json 的 win_signal（--teams 已注入，本节点窗口口径），
    # 选手评分来自虎扑（fetch_ratings 按本小局 gi 拉取）；deepseek 路径由模板渲染直接输出，
    # codex 路径后置注入。生成后冻结，不随后续小局变化。
    ratings = fetch_ratings(mid, gi)
    # 2026-10-31：end 页官方结果回填——小局官方结算（Polymarket Game N Winner）后，
    # 把胜方写入 intel_json.official_result，供渲染层把胜率条改成 100:0（结果展示）。
    # winner_side 无法对齐时（None）不写，保持弹幕口径 + 待核对（红线不猜）。
    if gphase == "end" and winner_side in ("A", "B"):
        try:
            _d = json.loads(intel_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _d = {}
        _d["official_result"] = {"winner_side": winner_side, "source": "polymarket"}
        intel_json.write_text(json.dumps(_d, ensure_ascii=False), encoding="utf-8")
    report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_g{gi}_{gphase}.html"
    if n == 0:
        # 0 样本节点：Codex/DeepSeek 在 0 样本时偶发 rc=0 但不落盘 → report missing 死循环
        # （教训 2026-10-26 MongolZ-MOUZ g1_bp/g1_end 反复空转）。直接落「样本不足」占位页，
        # 符合「无样本不硬撑」，幂等走同一收尾（注入局势 + MD 镜像 + 状态 + 壳）。
        source = "insufficient"
        rc = 0
        so = se = ""
        _gtype = (slug_id or "").split("-")[0].lower()
        _gtype = "cs2" if _gtype.startswith("cs") else ("dota2" if (_gtype.startswith("dota") or _gtype.startswith("ti")) else "lol")
        report.write_text(_insufficient_node_html(teams, date, gi, gphase, _gtype), encoding="utf-8")
        print(f"[pipeline] {mid}: G{gi} {gphase} slice 0 rows → 样本不足占位页（跳过 Codex）", flush=True)
    elif AI_BACKEND == "deepseek":
        source = "deepseek"
        print(f"[pipeline] {mid}: G{gi} {gphase} slice {n} rows, generating (DeepSeek)...", flush=True)
        rc, so, se = fast_intel_node(
            slug_id, teams, date, gi, gphase, intel_json, slice_file,
            end_basis=end_basis, late=late, max_games=max_games, ratings=ratings,
        )
    else:
        source = "codex"
        print(f"[pipeline] {mid}: G{gi} {gphase} slice {n} rows, generating (Codex 全量)...", flush=True)
        rc, so, se = run_codex_report(
            slug_id, teams, date, intel_json, slice_file,
            game=gi, gphase=gphase, end_basis=end_basis, late=late,
        )
    if not report.exists():
        print(f"[pipeline] {mid}: G{gi} {gphase} report missing rc={rc}（下轮重试）", flush=True)
        return
    # 标题区 CSS 钉死（幂等）：codex 路径在 run_codex_report 里已钉，这里覆盖
    # insufficient / deepseek 路径，保证所有节点页标题一致。
    _pin_header_css(report)
    # codex/占位路径：【比赛局势】栏为规则层块，后置注入（不依赖 AI 文本）；
    # deepseek 路径由模板直接渲染，无需注入。
    if source in ("codex", "insufficient"):
        _inject_situation(report, intel_json, ratings, teams, gphase=gphase)
    write_md_mirror(report)  # HTML + MD 双格式（2026-08-26 定稿）
    st.write_text(
        json.dumps(
            {
                "match": mid,
                "game": gi,
                "phase": gphase,
                "slice_rows": n,
                "slice_from": slice_from.isoformat(),
                "report": str(report),
                "report_exists": report.exists(),
                "codex_rc": rc,
                "source": source,
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[pipeline] {mid}: G{gi} {gphase} done rc={rc} exists={report.exists()}", flush=True)
    build_timeline_shell(mid, teams, "-", date, max_games=max_games)


def run_nodes_parallel(tasks: list) -> None:
    """并行生成互不依赖的节点（2026-08-26 及时性 C：BP 与局中可同时生成）。"""
    if len(tasks) <= 1:
        for t in tasks:
            t()
        return
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(t) for t in tasks]
        for f in futs:
            f.result()


def anchor_next_game(mid: str, gi: int, now_utc: datetime.datetime) -> datetime.datetime:
    """下一局锚点 = 本局结束节点状态文件的生成时间（固定，避免每轮滑动）。

    教训 2026-08-25：G1 结束后用 now_utc 作下一局锚点，每 5 分钟滑动一次，
    G2 的 BP 窗口永远追不上，导致只有 G1 出节点、G2+ 全部缺失。
    """
    try:
        st = STATE_DIR / f"{mid}_g{gi}_end.json"
        return datetime.datetime.fromisoformat(
            json.loads(st.read_text(encoding="utf-8"))["generated_at"].replace("Z", "+00:00")
        )
    except Exception:  # noqa: BLE001
        return now_utc


def run_codex_report(
    slug_id: str,
    teams: list[str],
    date: str,
    intel_json: Path,
    slice_file: Path,
    live: bool = False,
    pre: bool = False,
    game: int = 0,
    gphase: str = "",
    end_basis: str = "",
    late: bool = False,
    stamp: str = "",
    result_note: str = "",
) -> tuple[int, str, str]:
    if pre:
        suffix = "_pre"
    elif game:
        suffix = f"_g{game}_{gphase}"
    elif live:
        ts = stamp or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%H%M")
        suffix = f"_live_{ts}"
    else:
        suffix = ""
    report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}{suffix}.html"
    if pre:
        phase = (
            f"比赛 {teams[0]} vs {teams[1]}（{date}，slug={slug_id}）尚未开赛（赛前窗口），"
            f"节点=S0｜赛前｜PRE-MATCH。请生成「赛前弹幕情报页」：标注「赛前·未开赛」；内容聚焦赛前共识/队伍状态/"
            f"历史对阵/盘口讨论/预期，禁用比分类结论"
        )
    elif game:
        glabel = {
            "bp": "BP 后/开局（EARLY-GAME）",
            "mid": "局中（MID-GAME）",
            "end": "局末/局间（GAME-REVIEW）",
        }.get(gphase, gphase)
        end_note = ""
        if gphase == "end":
            if end_basis == "market":
                end_note = (
                    f"第 {game} 小局已结束（Polymarket Game {game} Winner 市场结算确认，结果待官方核对）。"
                )
            elif end_basis == "gg":
                end_note = f"第 {game} 小局已结束（弹幕 GG/局间信号，结果待官方核对）。"
            elif end_basis == "settlement":
                end_note = (
                    f"第 {game} 小局已结束（整场 Polymarket 结算确认，终局补发，结果待官方核对）。"
                )
            elif end_basis == "hupu":
                end_note = f"第 {game} 小局已结束（虎扑官方比分确认，结果待官方核对）。"
            else:
                end_note = (
                    f"第 {game} 小局按时间窗估计已结束（局末·待结算校准），结果待官方核对。"
                )
        phase = (
            f"比赛 {teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行第 {game} 小局，"
            f"节点=G{game}｜{glabel}。{end_note}生成「局中弹幕情报快照（G{game}）」，"
            f"页面显著标注「局中·非终局，结果待定」，进度以弹幕口径为准；"
            f"内容聚焦本小局：BP/阵容、灰信号、方向性共识（正锚×负锚×群体共识）；"
            f"无样本写「样本不足」，不硬造。"
        )
        if late and gphase == "bp":
            phase += (
                "（补发节点：本页因流水线延迟在窗口后生成，"
                "切片已限定为 BP/开局时段，内容以该时段弹幕为准，页面标注「补发」）"
            )
    elif live:
        phase = (
            f"比赛 {teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行中，请生成"
            f"节点=局中｜IN-GAME（时间点快照）。生成「局中弹幕情报快照」，页面显著标注「局中·非终局，结果待定」，进度以弹幕口径为准"
        )
    else:
        phase = (
            f"比赛 {teams[0]} vs {teams[1]}（{date}，slug={slug_id}）已结束（弹幕多信号确认，"
            f"结果待官方核对），节点=FINAL｜系列复盘｜SERIES-REVIEW。请生成「整场弹幕情报页」"
        )
        if result_note:
            phase += f"（本场已确认结果：{result_note}，来源「Polymarket 结算」，供方向板/灰信号校准）"
    # 2026-11-21：BP 栏按游戏分口径——LoL/Dota2 选人（lineup），CS2 只有选图（maps）。
    gtype = (slug_id or "").split("-")[0].lower()
    gtype = "cs2" if gtype.startswith("cs") else ("dota2" if (gtype.startswith("dota") or gtype.startswith("ti")) else "lol")
    bp_title = "1 BP 锚点与地图禁选情报" if gtype == "cs2" else "1 BP 锚点与选人情报"
    bp_item6 = (
        "6) BP 锚点（第 1 段）：地图禁选/队伍×地图为「弹幕口径·待官方」，BP 后战绩情报"
        "（无则写「无战绩情报提及」），禁止把弹幕讨论当实际选图"
        if gtype == "cs2" else
        "6) BP 锚点（第 1 段）：阵容（英雄+选手）为「弹幕口径·待官方」，BP 后战绩情报"
        "（无则写「无战绩情报提及」），禁止把弹幕讨论当实际选人"
    )
    prompt = (
        f"{phase}。\n"
        f"【时间显示规范（2026-08-27 用户定稿，最高）】页面所有时间（数据窗口、"
        f"弹幕样本时间戳、节点时刻）一律用北京时间展示（UTC+8）；弹幕原始时间戳"
        f"换算后展示北京时间（如 16:08 而不是 08:08），UTC 仅作括号备注；"
        f"禁止直接展示 UTC 时间。\n"
        f"请按以下流程生成情报页：\n"
        f"1) 先完整阅读技能文件 /root/.codex/skills/intel-report/SKILL.md 与模板 "
        f"knowledge/INTEL_HTML_TEMPLATE.md、knowledge/LIVE_INTEL_SCHEMA.md；\n"
        f"2) 读取规则层情报 JSON {intel_json}（其中 narrative 字段含观众共识/情绪走势/转折点，"
        f"作为第 3 段方向性情报板群体共识的叙事主线；neutral_salvage 字段为规则层判中性、"
        f"待二次判定情绪的弹幕候选）与弹幕切片 {slice_file}；\n"
        f"3) 页面结构只保留 4 段（2026-10-24 用户定稿，其余栏不生成，禁止多写），"
        f"每段用 <h2><span class=\"no\">N</span>标题</h2> 编号，编号连续、禁止合并/省略："
        f"{bp_title}（弹幕讨论·非确认）→ 2 比赛局势（系统注入，本段不写）→ "
        f"3 方向性情报板（正锚×负锚×共识×灰信号条件预测）→ 4 灰信号汇总（风险·观众质疑非结论）；\n"
        f"4) 方向板（第 3 段）：正锚点（看好谁赢，含对象/依据/时间/验证）、负锚点（看衰谁输）、"
        f"群体共识（+分歧+样本量，由 narrative 提炼）、灰信号条件预测（若兑现指向哪边）；"
        f"无锚点写「今日无锚点」，无共识写「共识不足」，无灰信号写「今日无灰信号」；\n"
        f"5) 灰信号（第 4 段）：每条写明「观众质疑，非结论」+ 指向对象 + 风险等级，"
        f"只作风险标注与盘口对照，禁止写成实锤；无则写「今日无灰信号」；\n"
        f"{bp_item6}；\n"
        f"7) 【情报来源分层·最高纪律（2026-08-26 用户定稿）】每条结论必须带证据来源标签"
        f"（本场弹幕 / 前局弹幕 / 历史画像 / 盘口 / 推测·待验证），核心情报必须来自本场弹幕，"
        f"严禁无中生有；仅简单推断、无数据支撑的不写；推测必须显式标注「推测·待验证」并与事实分离；"
        f"历史画像引用须带时间；缺源（如 SOOP 离线）显式标注为缺口，禁止用历史画像冒充本场数据。\n"
        f"【中性弹幕二次判定】对 neutral_salvage 候选（规则层判中性）逐条判定："
        f"发现真实情绪（如 666=夸赞、'这把拉了'=失误）纳入方向板并标注「模型二次判定」，"
        f"纯聊天/表情/无情绪的不写，禁止硬套情绪。\n"
        f"8) 生成 SAP/Apple 风格（浅底 #f5f5f7、白卡片、单一强调色、系统字体栈）紧凑清爽完整 HTML，"
        f"必须用 Write 工具写入绝对路径 {report}（含 </body></html>）；"
        f"禁止写入 runtime/pending_reports/ 或任何其他目录，禁止改文件名或加 .codex/.final 等后缀。"
    )
    env = dict(os.environ)
    env["PATH"] = env.get("PATH", "") + ":/root/.local/bin"
    try:
        r = subprocess.run(
            [CODEX, "exec", "--skip-git-repo-check", prompt],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            # 2026-08-25 教训：DeepSeek 高峰期单节点生成曾连续 2 次在 600s
            # 超时（G3 end / G4 mid）；放宽到 900s，宁可慢不可丢节点
            timeout=900,
        )
        # 兜底（2026-10-25 根治）：Codex 偶发自作主张把报告写到 runtime/pending_reports/
        # （8-28 起就存在的诱饵目录），导致流水线 report missing。此处从 pending 取回，
        # 使 node/pre/live 所有调用点 report.exists() 一致成立。
        if not report.exists():
            pending = ROOT / "runtime" / "pending_reports" / report.name
            if pending.exists():
                shutil.copyfile(pending, report)
                print(f"[pipeline] recovered {report.name} from pending_reports", flush=True)
        if report.exists():
            _pin_header_css(report)  # 标题区 CSS 钉死（Codex 漂移，见 _pin_header_css）
        return r.returncode, r.stdout[-500:], r.stderr[-500:]
    except subprocess.TimeoutExpired:
        return 124, "timeout", "timeout 600s"


def deepseek_key() -> str:
    """DeepSeek API Key：优先环境变量，其次 codex 配置（experimental_bearer_token）。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        cfg = Path.home() / ".codex" / "config.toml"
        if cfg.exists():
            m = re.search(
                r'experimental_bearer_token\s*=\s*"([^"]+)"',
                cfg.read_text(encoding="utf-8"),
            )
            if m:
                tok = m.group(1).strip()
                # 跳过占位符（如 PROXY_xxx）：不是真实 API key，继续回退到本地 txt
                if tok and not tok.startswith("PROXY_"):
                    return tok
    except Exception:  # noqa: BLE001
        pass
    # 本地回退（2026-09-27 本地适配）：从 ~/Deepseek API key.txt 读；服务器上无此文件，无影响
    try:
        f = Path.home() / "Deepseek API key.txt"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("sk-"):
                    return line
    except Exception:  # noqa: BLE001
        pass
    return ""


GAME_SLUGS = ("lol", "cs2", "dota2")


def _match_game(m: dict) -> str | None:
    """从比赛 id 首段推断游戏类型（lol/cs2/dota2）；无法判断返回 None。"""
    slug = str(m.get("id") or "").strip().lower()
    first = slug.split("-")[0]
    if first.startswith("cs"):
        return "cs2"
    if first.startswith("dota") or first.startswith("ti"):
        return "dota2"
    if first.startswith("lol"):
        return "lol"
    return None


def _game_of_file(p: Path) -> str | None:
    """新目录 danmu/<game>/<platform>/<file> 下的文件返回其 game，否则 None。"""
    g = p.parent.parent.name
    return g if g in GAME_SLUGS else None


def _file_date(p: Path) -> str | None:
    """从文件名提取采集日期（YYYY-MM-DD 前缀）；无前缀返回 None。"""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})_", p.name)
    return m.group(1) if m else None


def _date_window(m: dict) -> tuple[str, str] | None:
    """比赛开赛日 ±1 天（覆盖跨午夜赛程），用于把弹幕文件扫描收窄到当日。"""
    st = m.get("start_time") or ""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", st)
    if not m:
        return None
    d = datetime.datetime.strptime(m.group(1), "%Y-%m-%d")
    lo = (d - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    hi = (d + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    return lo, hi


def _date_glob_window(date: str) -> list[str]:
    """壳页报告 glob 的日期窗口 [date-1, date, date+1]。

    2026-10-29 固化：跨午夜场次报告文件名日期（start_time 的 UTC 日期）与
    壳页日期（北京时间 / 结构化库 date 字段）可能差一天，单一日期 glob 会漏配
    （教训：MKOI-T1 报告用 2026-10-28、壳用 2026-10-29，壳显示"本场暂无情报"）。
    """
    try:
        d = datetime.datetime.strptime((date or "")[:10], "%Y-%m-%d")
    except ValueError:
        return [date] if date else []
    return [
        (d - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        d.strftime("%Y-%m-%d"),
        (d + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    ]


def league_files(m: dict, files: list[Path]) -> list[Path]:
    """按比赛游戏过滤直播间文件（2026-09-10 改为按 danmu/<game>/ 目录分）。

    旧实现（2026-08-26）靠文件名关键词猜游戏（csboy/blast/huya/kick），
    采集层新增 game 维度后，这里改为直接按目录取文件，不再猜词：
      cs2 比赛 -> 只取 danmu/cs2/ 下文件；lol -> danmu/lol/；dota2 -> danmu/dota2/。
    若对应 game 目录下没有文件（数据仍在旧目录 danmu/<platform>/），退回原
    文件名关键词逻辑兜底，避免历史数据漏抓。
    最后再按比赛开赛日 ±1 天收窄，避免对跨数月的历史弹幕全量扫描
    （2026-10-25：game 层迁移未落地 -> league_files 退回关键词拿到 ~260 个文件，
    verify_end/slice_rows 每节点全量扫一遍，实时场次情报严重滞后）。
    """
    game = _match_game(m)
    if game is None:
        out = files  # 未知联赛：全量（保持旧行为）
    else:
        scoped = [p for p in files if _game_of_file(p) == game]
        if scoped:
            out = scoped
        elif game == "cs2":
            out = [
                p for p in files
                if ("huya" in p.name and any(k in p.name for k in ("csboy", "blast")))
                or "kick" in p.name
            ]
        elif game == "lol":
            out = [p for p in files if ("huya" in p.name or "soop" in p.name) and "csboy" not in p.name]
        else:
            out = files
    win = _date_window(m)
    if win is None:
        return out
    lo, hi = win
    return [p for p in out if (fd := _file_date(p)) is None or lo <= fd <= hi]


def bp_slice_from(g_start, start_dt):
    """BP 切片起点：不早于比赛实际开赛（教训 2026-08-26：Spirit-DENDELE
    g1_bp 切片从开赛前 37 分钟开始，等待期 LCK/G2-Aurora 杂音混入）。"""
    frm = g_start - datetime.timedelta(minutes=15)
    if start_dt and frm < start_dt:
        return start_dt
    return frm


# 节点页 JSON 字段 schema（2026-10-18 模板化生成；2026-10-24 起只保留 4 栏所需字段）：
# AI 只填内容字段，不写 HTML。仅 bp_anchors/direction/gray_signals 三组字段进入页面，
# 比赛局势为规则层注入（stats.win_signal + 虎扑评分），其余栏位不再生成。
# 2026-11-21：BP 栏按游戏分口径——LoL/Dota2 选人（lineup），CS2 只有选图（maps）。
def _node_json_schema(game: str) -> str:
    if game == "cs2":
        bp = '{"maps":"地图禁选/队伍×地图（弹幕口径·待官方）","type":"正|负","content":"锚点内容","bp_note":"战绩情报 或 无战绩情报提及"}'
    else:
        bp = '{"lineup":"英雄+选手映射（弹幕口径·待官方）","type":"正|负","content":"锚点内容","bp_note":"战绩情报 或 无战绩情报提及"}'
    return (
        "{\n"
        f'  "bp_anchors": [{bp}],\n'
        '  "direction": {"positive":["正锚"], "negative":["负锚"], "consensus":"群体共识（含净值/样本）", "gray_conditional":["灰信号条件预测"]},\n'
        '  "gray_signals": [{"text":"灰信号内容","target":"指向对象","warning":"低|中|高"}]\n'
        "}"
    )


def _strip_json(text: str) -> str:
    """剥离 markdown 代码块围栏与前后杂讯，尽量得到纯 JSON。"""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    lo = t.find("{")
    hi = t.rfind("}")
    if lo >= 0 and hi > lo:
        t = t[lo:hi + 1]
    return t


def _deepseek_call(prompt: str, max_tokens: int) -> str | None:
    """直连 DeepSeek，返回 message 文本；失败返回 None。"""
    key = deepseek_key()
    if not key:
        return None
    body = json.dumps(
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=180).read())
        return r["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001
        return None


def _finalize_html(html: str, teams: list[str], gi: int, gphase: str, max_games: int) -> str:
    """收尾：BO 赛制强制替换 + 缺 doctype 时补壳（教训 2026-08-26）。"""
    html = re.sub(r"BO\s*[0-9]", f"BO{max_games}", html, flags=re.I)
    if f"BO{max_games}" not in html:
        note = (
            f'<div style="font-size:12px;color:#6e6e73;margin:6px 0 2px">'
            f"赛制：BO{max_games}（本场共 {max_games} 局）</div>"
        )
        # 2026-10-24：结果总览栏已删，赛制注记改为插在首张卡片之前（页面顶部元数据）
        anchor = re.search(r'(<div class="card">)', html)
        if anchor:
            html = html[: anchor.start()] + note + html[anchor.start():]
    if not html.lower().startswith("<!doctype") and not html.lstrip().lower().startswith("<html"):
        html = (
            f'<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8">'
            f"<title>{teams[0]} vs {teams[1]} · G{gi} {gphase}</title></head><body>"
            f"{html}</body></html>"
        )
    return html


def fast_intel_node(
    slug_id: str,
    teams: list[str],
    date: str,
    gi: int,
    gphase: str,
    intel_json: Path,
    slice_file: Path,
    end_basis: str = "",
    late: bool = False,
    max_games: int = 3,
    ratings: dict | None = None,
) -> tuple[int, str, str]:
    """快节点（2026-08-26，及时性核心）：规则层统计摘要 + 直连 DeepSeek API。

    目标：小局结束/关键节点后 3-5 分钟内上线（实测单节点 ~10-60s、~$0.002）。
    只喂统计与精选样本，不裸喂整窗弹幕；无样本写「样本不足」，不编造。
    失败返回非 0，调用方回退 codex 路径。
    """
    rep = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_g{gi}_{gphase}.html"
    if rep.exists():
        return 0, "exists", ""
    key = deepseek_key()
    if not key:
        return 2, "", "no deepseek key"
    stats: dict = {}
    try:
        stats = json.loads(intel_json.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        stats = {}
    # 意见聚类与归因（2026-08-26 加工层）：复用同一弹幕切片，失败不阻塞页面
    clusters_txt = ""
    try:
        cr = subprocess.run(
            [str(PY), str(ROOT / "tools" / "opinion_cluster.py"),
             "--match", slug_id, "--input", str(slice_file),
             "--teams", ",".join(teams)],
            capture_output=True, text=True, timeout=180,
        )
        if cr.returncode == 0 and cr.stdout.strip():
            clusters_txt = cr.stdout.strip()[:1800]
            try:
                stats["opinion_clusters"] = json.loads(cr.stdout)
                intel_json.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        clusters_txt = ""
    meta = stats.get("meta", {})

    def brief(samples, k: int = 2) -> str:
        out = []
        for s in (samples or [])[:k]:
            s = str(s).strip()
            if len(s) > 90:
                s = s[:90] + "…"
            out.append(s)
        return "｜".join(out) or "无"

    teams_txt = ""
    for t, v in (stats.get("teams") or {}).items():
        tone = danmu_intel.tone_label(v.get("pos", 0), v.get("neg", 0), v.get("mentions", 0))
        teams_txt += (
            f"\n- {t}: 情绪{tone} 提及{v.get('mentions', 0)} 正向{v.get('pos', 0)}/负向{v.get('neg', 0)}"
            f" 例:{brief(v.get('samples'))}"
        )
    gray = stats.get("gray_signals") or {}
    gray_txt = ""
    if isinstance(gray, dict):
        for g in (gray.get("samples") or [])[:6]:
            gray_txt += f"\n- {str(g)[:80]}"
    elif isinstance(gray, list):
        for g in gray[:6]:
            gray_txt += f"\n- {str(g.get('text', g))[:80]}" if isinstance(g, dict) else f"\n- {str(g)[:80]}"
    if not gray_txt:
        gray_txt = "无"
    dens_txt = ""
    for d in (stats.get("density_bursts") or [])[:5]:
        if isinstance(d, dict):
            dens_txt += f"\n- {d.get('minute_utc','')} {d.get('count',0)}条 {str((d.get('samples') or [''])[0])[:40]}"
    if not dens_txt:
        dens_txt = "无"
    # 阶段3：把阶段2产出的比赛叙事（共识/情绪时间轴/转折点）喂给 AI，
    # 让 AI 用自然语言复述比赛情绪走向，而不是只搬规则层计数。
    narr = stats.get("narrative") or {}
    narr_txt = ""
    cons = narr.get("consensus") or {}
    if cons.get("pos") or cons.get("neg"):
        narr_txt += (
            f"观众共识：{cons.get('tone', '中性')}"
            f"（正 {cons.get('pos', 0)}/负 {cons.get('neg', 0)}，净 {cons.get('net', 0):+d}）"
        )
    tl = narr.get("timeline") or []
    if len(tl) >= 2:
        narr_txt += "；情绪走势：" + " → ".join(f"{b['tone']}({b['net']:+d})" for b in tl)
    for t in (narr.get("turning_points") or [])[:4]:
        narr_txt += (
            f"；转折 {t.get('minute_utc', '')} {t.get('tone', '')}"
            f"（{t.get('count', 0)}条）{str(t.get('sample', ''))[:40]}"
        )
    if not narr_txt:
        narr_txt = "无（样本不足，勿编造）"
    # 阶段4：中性弹幕抢救候选（规则层判中性·待 LLM 二次判定情绪）
    salvage_txt = ""
    for s in (stats.get("neutral_salvage") or [])[:30]:
        tag = "·提及实体" if s.get("entity") else ""
        salvage_txt += f"\n- ×{s.get('count', 1)} {str(s.get('text', ''))[:50]}{tag}"
    if not salvage_txt:
        salvage_txt = "无"

    glabel = {
        "bp": "BP 后/开局（S0 · EARLY-GAME）",
        "mid": "局中（S1-S3 快照 · MID-GAME）",
        "end": "局末/局间（S4 · GAME-REVIEW）",
    }.get(gphase, gphase)
    end_note = ""
    if gphase == "end" and end_basis:
        end_note = f"（结束依据：{end_basis}，结果待官方核对）"
    if late:
        end_note += "（补发节点：流水线延迟，窗口后生成）"
    game = (slug_id or "").split("-")[0].lower()
    game = "cs2" if game.startswith("cs") else ("dota2" if (game.startswith("dota") or game.startswith("ti")) else "lol")
    game_label = {"cs2": "CS2", "dota2": "Dota2", "lol": "LoL"}.get(game, "LoL")
    if game == "cs2":
        html_bp_title = "1 BP 锚点与地图禁选情报（弹幕讨论·非确认）"
        html_bp_item6 = (
            f"6) BP 锚点（第 1 段）：地图禁选/队伍×地图为「弹幕口径·待官方」，BP 后战绩情报"
            f"（无则写「无战绩情报提及」），禁止把弹幕讨论当实际选图；\n"
        )
    else:
        html_bp_title = "1 BP 锚点与选人情报（弹幕讨论·非确认）"
        html_bp_item6 = (
            f"6) BP 锚点（第 1 段）：阵容（英雄+选手）为「弹幕口径·待官方」，BP 后战绩情报"
            f"（无则写「无战绩情报提及」），禁止把弹幕讨论当实际选人；\n"
        )
    html_prompt = (
        f"你是电竞弹幕情报分析师。生成一场 {game_label} 比赛的局中弹幕情报 HTML 页（节点=G{gi}｜{glabel}{end_note}）。\n"
        f"比赛：{teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行第 {gi} 小局，赛制 BO{max_games}（本场共 {max_games} 局，页面对阵/赛制处必须写 BO{max_games}，禁止写错）。\n"
        f"页面标注「局中·非终局，结果待定」。\n"
        f"规则层统计（来自弹幕）：窗口 {meta.get('window_utc','')}，共 {meta.get('total',0)} 条，"
        f"{meta.get('active_users',0)} 人，{meta.get('density_per_min',0)} 条/分，样本状态 {meta.get('sample_status','-')}。\n"
        f"队伍提及：{teams_txt or '无'}\n"
        f"灰信号（观众质疑，非结论）：{gray_txt}\n"
        f"弹幕密度峰值：{dens_txt}\n"
        f"比赛叙事（观众共识/情绪时间轴/关键转折点）：{narr_txt}\n"
        f"中性弹幕抢救候选（规则层判中性·待二次判定情绪，×N=出现次数）：{salvage_txt}\n"
        f"规则层情报文件：{intel_json}\n"
        f"要求（决策导向，2026-10-24 用户定稿：只保留 4 栏）：\n"
        f"1) 页面结构只保留 4 段（其余栏不生成，禁止多写），每段用 "
        f"<h2><span class=\"no\">N</span>标题</h2> 编号，编号连续、禁止合并/省略："
        f"{html_bp_title} → 2 比赛局势（系统注入，本段不写）→ "
        f"3 方向性情报板（正锚×负锚×共识×灰信号条件预测）→ 4 灰信号汇总（风险·观众质疑非结论）；\n"
        f"2) 输出 SAP/Apple 风格完整 HTML（内联CSS：浅底#f5f5f7、白圆角卡片、单一强调色#0071e3、"
        f"系统字体栈 -apple-system/PingFang SC、充足留白），内容紧凑、信息密度高，全文约 400-600 字；\n"
        f"3) 韩/英弹幕信号层只给中文意译一句话，原文折叠在 <details>（格式「中文意译（原文摘录）」），"
        f"黑话保留双语（如 야필패=亚索必败）；每条约 1-2 条样本+计数，不堆原文；\n"
        f"4) 方向板（第 3 段）：正锚点（看好谁赢，含对象/依据/时间/验证）、负锚点（看衰谁输）、"
        f"群体共识（+分歧+样本量，由比赛叙事提炼）、灰信号条件预测（若兑现指向哪边）；"
        f"无锚点写「今日无锚点」，无共识写「共识不足」，无灰信号写「今日无灰信号」；\n"
        f"5) 灰信号（第 4 段）：每条写明「观众质疑，非结论」+ 指向对象 + 风险等级，"
        f"只作风险标注与盘口对照，禁止写成实锤；无则写「今日无灰信号」；\n"
        f"{html_bp_item6}"
        f"7) 【情报来源分层·最高纪律】每条结论必须带证据来源标签（本场弹幕/前局弹幕/历史画像/盘口/"
        f"推测·待验证），核心情报必须来自本场弹幕，严禁无中生有；推测必须显式标注「推测·待验证」；\n"
        f"8) 只依据给定统计与示例样本，禁止编造具体弹幕内容、比分或事实；样本不足的板块写「样本不足」；\n"
        f"9) 中性弹幕二次判定：对「中性弹幕抢救候选」逐条判定情绪，发现真实正面/负面（如「666」=夸赞、"
        f"「这把拉了」=失误）时纳入方向板并标注「模型二次判定」；纯聊天/表情/无情绪的丢弃不写；\n"
        f"10) 直接输出 HTML（不要 markdown 代码块包裹），完整写完 </body></html>。\n"
        f""
    )
    # ---- 新路径：JSON 字段化（2026-10-18 模板化生成，治本提速）----
    if game == "cs2":
        bp_instr = (
            f"1) bp_anchors：每个锚点给 maps（地图禁选/队伍×地图强图，标「弹幕口径·待官方」）、type（正/负）、"
            f"content（锚点内容）、bp_note（战绩情报，无则「无战绩情报提及」）；CS2 无英雄选人，只写地图；无锚点写空数组；\n"
        )
        bp_pair_instr = f"9) 地图禁选配对只写「弹幕口径·待官方」，禁止把弹幕讨论当实际选图。\n"
    else:
        bp_instr = (
            f"1) bp_anchors：每个锚点给 lineup（英雄+选手映射，标「弹幕口径·待官方」）、type（正/负）、"
            f"content（锚点内容）、bp_note（战绩情报，无则「无战绩情报提及」）；无锚点写空数组；\n"
        )
        bp_pair_instr = f"9) 阵容配对只写「弹幕口径·待官方」，禁止把弹幕讨论当实际选人。\n"
    json_prompt = (
        f"你是电竞弹幕情报分析师。基于下方规则层统计，提炼一场比赛的局中弹幕情报"
        f"（节点=G{gi}｜{glabel}{end_note}）。\n"
        f"比赛：{teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行第 {gi} 小局，"
        f"赛制 BO{max_games}（本场共 {max_games} 局）。\n"
        f"页面标注「局中·非终局，结果待定」。\n"
        f"规则层统计（来自弹幕）：窗口 {meta.get('window_utc','')}，共 {meta.get('total',0)} 条，"
        f"{meta.get('active_users',0)} 人，{meta.get('density_per_min',0)} 条/分，"
        f"样本状态 {meta.get('sample_status','-')}。\n"
        f"队伍提及：{teams_txt or '无'}\n"
        f"灰信号（观众质疑，非结论）：{gray_txt}\n"
        f"弹幕密度峰值：{dens_txt}\n"
        f"比赛叙事（观众共识/情绪时间轴/关键转折点）：{narr_txt}\n"
        f"中性弹幕抢救候选（规则层判中性·待二次判定情绪，×N=出现次数）：{salvage_txt}\n"
        f"\n【只输出一个 JSON 对象，不要输出任何解释、markdown 代码块或 HTML】\n"
        f"JSON 字段如下（三组字段都要给出；没有就写空数组/空字符串或「无/样本不足/待回填」）：\n"
        f"{_node_json_schema(game)}\n"
        f"\n填写纪律（最高优先级）：\n"
        f"{bp_instr}"
        f"2) direction：positive/negative 分别列正锚/负锚对象（含对象/依据/时间/验证）；"
        f"consensus 写群体共识（含净值/样本量，不足写「共识不足」）；"
        f"gray_conditional 写灰信号条件预测（若兑现指向哪边）；无则写空数组；\n"
        f"3) gray_signals：每条 text（灰信号内容）、target（指向对象）、warning（低/中/高）；"
        f"一律「观众质疑·非结论」；无则写空数组；\n"
        f"4) 每条结论带来源标签（本场弹幕/前局延续/历史库/推测），推测必须条件化并标「推测」；\n"
        f"5) 结果/比分只标「弹幕口径·待官方」，禁止凭弹幕定胜负；\n"
        f"6) 无样本不硬撑（写「样本不足」）、无信号不硬造（写「今日无信号」）；\n"
        f"7) 只依据给定统计与示例样本，禁止编造具体弹幕内容、比分或事实；\n"
        f"8) 英文俚语不得当战队信号（OKBRO/bro 是玩梗，非 BRO 战队）；韩/英黑话需双语映射；\n"
        f"{bp_pair_instr}"
    )

    # 1) 优先走 JSON 路径：解析成功 -> 本地模板渲染
    raw = _deepseek_call(json_prompt, 4000)
    if raw:
        data = None
        try:
            data = json.loads(_strip_json(raw))
        except Exception:  # noqa: BLE001
            data = None
        if isinstance(data, dict):
            try:
                html = render_node_page.render(
                    data, stats,
                    teams=teams, date=date, gi=gi, gphase=gphase, slug_id=slug_id,
                    max_games=max_games, end_basis=end_basis, late=late,
                    ratings=ratings,
                )
                html = _finalize_html(html, teams, gi, gphase, max_games)
                rep.write_text(html, encoding="utf-8")
                write_md_mirror(rep)  # HTML + MD 双格式
                return 0, f"json ok {len(html)} bytes", ""
            except Exception as e:  # noqa: BLE001
                print(f"[pipeline] {slug_id}: G{gi} {gphase} json render failed: {e}，回退 HTML", flush=True)

    # 2) 兜底：旧 HTML prompt（JSON 解析/渲染失败时）
    raw = _deepseek_call(html_prompt, 8000)
    if raw is None:
        return 1, "", "fast failed: no deepseek response"
    html = re.sub(r"^```(?:html)?\s*|\s*```$", "", raw.strip())
    # 2026-08-26 教训：DeepSeek 偶发不写 </body>/</html>（截断感）——自动补全收尾。
    if "</body>" not in html.lower():
        html += "\n</body>\n</html>"
    elif "</html>" not in html.lower():
        html += "\n</html>"
    html = _finalize_html(html, teams, gi, gphase, max_games)
    rep.write_text(html, encoding="utf-8")
    write_md_mirror(rep)  # HTML + MD 双格式
    return 0, f"fast ok {len(html)} bytes", ""


def write_md_mirror(html_path: Path) -> Path | None:
    """HTML 情报页 → MD 全文镜像（2026-08-26 用户定稿：所有情报页 HTML+MD 双格式）。

    供情报库分析/沉淀使用；转换轻量保结构（标题/列表/详情折叠），不丢硬信息。
    """
    md_path = html_path.with_suffix(".md")
    try:
        if md_path.exists() and html_path.stat().st_mtime <= md_path.stat().st_mtime:
            return md_path
        t = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    # 去掉导航/面包屑等站点装饰，只留情报正文（供分析镜像）
    t = re.sub(r"<nav.*?</nav>", "", t, flags=re.S)
    t = re.sub(r"<div[^>]*max-width:1020px;margin:-10px.*?</div>", "", t, flags=re.S)
    t = re.sub(r"<div class=\"crumb\".*?</div>", "", t, flags=re.S)
    for lv, mark in ((1, "# "), (2, "## "), (3, "### "), (4, "#### ")):
        t = re.sub(
            rf"<h{lv}[^>]*>(.*?)</h{lv}>",
            lambda m, mk=mark: "\n" + mk + re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n",
            t,
            flags=re.S,
        )
    t = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "- " + re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n", t, flags=re.S)
    t = re.sub(
        r"<details[^>]*>(.*?)</details>",
        lambda m: "\n<details>\n" + re.sub(r"<[^>]+>", "", m.group(1)).strip() + "\n</details>\n",
        t,
        flags=re.S,
    )
    t = re.sub(r"</(p|div|tr|section)>", "\n", t)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    try:
        md_path.write_text(t.strip() + "\n", encoding="utf-8")
        return md_path
    except OSError:
        return None


def build_timeline_shell(
    mid: str, teams: list[str], league: str, date: str, max_games: int = MAX_GAME
) -> Path:
    """Generate a timeline shell (pre -> per-game nodes -> full) for a match.

    节点发现按队伍名归一化匹配真实文件（去掉点/空格/大小写差异），
    兼容两种命名：流水线 `_g1_bp/_g1_mid/_g1_end` 与回补 `_G1/_G2/_G3`。
    教训 2026-08-25：按 teams 硬拼文件名（BFX.Y vs BFXY）导致壳按钮
    `__none__`/全部指向整场页——节点数据"同一份"假象。
    """
    a, b = teams
    def norm(s: str) -> str:
        return re.sub(r"[.\s]", "", (s or "").lower())

    na, nb = norm(a), norm(b)

    # 2026-08-29：队伍别名/全称候选（如 BRO -> [bro, hanjinbrion, brion...]），
    # 用于匹配全称命名的节点页（"HANJIN BRION-BNK FEARX" 对 teams=["BRO","BFX"]）。
    def cands(name: str) -> list[str]:
        n = norm(name)
        out = {n}
        for row in _team_rows():
            abbr = norm(row.get("abbr", ""))
            full = norm(row.get("full", ""))
            aliases = [norm(x) for x in row.get("aliases", [])]
            if n in (abbr, full) or n in aliases or (abbr and n.startswith(abbr)):
                out.update([abbr, full, *aliases])
        return sorted((c for c in out if c), key=len, reverse=True)

    ca, cb = cands(a), cands(b)

    def pair_of(f: Path) -> str | None:
        stem = f.stem
        if not stem.startswith("intel_danmu_"):
            return None
        body = stem[len("intel_danmu_"):]
        body = re.sub(r"_\d{4}-\d{2}-\d{2}", "", body)  # 去掉日期 token（可能在中间或末尾）
        body = body.split("_", 1)[0]
        low = body.lower()
        for pfx in ("lck-", "lpl-", "lec-", "lcs-", "lcp-",
                    "cs2-", "dota2-", "valorant-", "lol-", "cs-", "dota-"):
            if low.startswith(pfx):
                body = body[len(pfx):]
                break
        return body

    def team_match(pair: str) -> bool:
        parts = pair.split("-", 1)
        if len(parts) != 2:
            return False
        x, y = norm(parts[0]), norm(parts[1])
        for p, q in ((x, y), (y, x)):
            if (any(p == c or p.startswith(c) or c.startswith(p) for c in ca)) and (
                any(q == c or q.startswith(c) or c.startswith(q) for c in cb)
            ):
                return True
        return False

    candidates: list[Path] = []
    # 2026-10-29 固化：跨午夜场次报告文件名日期（UTC）与壳页日期（北京）差一天，
    # 单一 date glob 会漏配（教训：MKOI-T1 报告 2026-10-28 / 壳 2026-10-29 显示"暂无"）。
    # 用 ±1 天窗口 glob，去重后交给 team_match 精确匹配。
    seen_f: set[Path] = set()
    for dd in _date_glob_window(date):
        for f in REPORTS.glob(f"intel_danmu_*{dd}*.html"):
            if f in seen_f:
                continue
            seen_f.add(f)
            pair = pair_of(f)
            if pair and team_match(pair):
                candidates.append(f)

    # 精确匹配优先（顺序不敏感）；无精确命中才用前缀容错（DNS-KRX vs DNS.C-KRX.C）。
    # 2026-08-29 修复：exact 只做排序/去重优先级，不再"有 exact 就丢弃全部候选"——
    # 否则 abbr 命名的整场页（CS2-Aurora-DENDELE_full）会挤掉全称命名节点页。
    exact = [
        f for f in candidates
        if norm(pair_of(f)) in (f"{na}-{nb}", f"{nb}-{na}")
    ]
    ordered = exact + [f for f in candidates if f not in exact]

    def node_slot(f: Path) -> tuple:
        stem = f.stem
        body = stem[len("intel_danmu_"):]
        body = re.sub(r"_\d{4}-\d{2}-\d{2}", "", body)
        suffix = body[body.split("_", 1)[0].__len__():]
        if suffix == "_pre":
            return ("pre", 0)
        if suffix == "":
            return ("series", 99)
        if suffix == "_full":
            return ("full", 98)
        if suffix == "_live":
            return ("live", 0)
        m = re.match(r"_g(\d+)_(bp|mid|end)$", suffix)
        if m:
            return ("node", int(m.group(1)), m.group(2))
        m = re.match(r"_G(\d+)$", suffix)
        if m:
            return ("g", int(m.group(1)))
        m = re.match(r"_live_(\d{4})$", suffix)
        if m:
            return ("live", m.group(1))
        return ("other", suffix)

    seen: set[tuple] = set()
    chosen: list[Path] = []
    for f in ordered:
        slot = node_slot(f)
        if slot not in seen:
            seen.add(slot)
            chosen.append(f)
    found: dict[str, Path] = {}
    for f in chosen:
        found[f.stem] = f

    entries: list[tuple[str, str, str, tuple]] = []
    for stem, f in found.items():
        body = stem[len("intel_danmu_"):]
        body = re.sub(r"_\d{4}-\d{2}-\d{2}", "", body)
        suffix = body[body.split("_", 1)[0].__len__():]
        if suffix == "_pre":
            entries.append(("赛前", "S0 · PRE-MATCH", f.name, (0, 0)))
        elif suffix == "":
            entries.append(("系列复盘", "FINAL · SERIES-REVIEW", f.name, (99, 0)))
        else:
            m = re.match(r"_g(\d+)_(bp|mid|end)$", suffix)
            if m:
                gi, ph = int(m.group(1)), m.group(2)
                label = {"bp": "BP 后", "mid": "局中", "end": "结束"}[ph]
                code = {"bp": "EARLY", "mid": "MID", "end": "REVIEW"}[ph]
                order = {"bp": 1, "mid": 2, "end": 3}[ph]
                entries.append((f"G{gi} · {label}", f"G{gi} · {code}", f.name, (gi, order)))
                continue
            m = re.match(r"_G(\d+)$", suffix)
            if m:
                gi = int(m.group(1))
                entries.append((f"G{gi} · 情报", f"G{gi} · GAME-INTEL", f.name, (gi, 4)))
                continue
            m = re.match(r"_live_(\d{4})$", suffix)
            if m:
                t = m.group(1)
                entries.append((f"局中 {t[:2]}:{t[2:]}", "IN-GAME 快照", f.name, (50, int(t))))
                continue
            if suffix == "_live":
                entries.append(("局中快照", "IN-GAME", f.name, (50, 0)))
                continue
            if suffix == "_full":
                entries.append(("整场复盘", "FULL", f.name, (98, 0)))
                continue
            entries.append((suffix.lstrip("_"), "NODE", f.name, (60, 0)))
    entries.sort(key=lambda e: e[3])
    # 已知但未采集的节点占位（2026-08-26 用户定稿：G1/G2 停用，
    # 前端显示「此节点暂未采集数据」，不 404）
    have = {(e[3][0], e[3][1]) for e in entries}
    for gi in range(1, max_games + 1):
        for ph, label, code, order in (
            ("bp", "BP 后", "EARLY", 1),
            ("mid", "局中", "MID", 2),
            ("end", "结束", "REVIEW", 3),
        ):
            if (gi, order) not in have:
                entries.append((f"G{gi} · {label}", "此节点暂未采集数据", None, (gi, order)))
    entries.sort(key=lambda e: e[3])
    views = [(e[0], e[1], e[2]) for e in entries]
    has_data = any(v[2] for v in views)

    # 首个"有数据"的节点设为默认展示。此前按 i == 0 设 aria-pressed，但第 0 项
    # 常是"此节点暂未采集数据"的占位（无 data-src），导致唯一可点的"系列复盘"
    # 拿不到 aria-pressed，iframe 空载（教训：TES-AL 回填后页面空白）。
    first_enabled = next((i for i, v in enumerate(views) if v[2]), 0)
    btns = "".join(
        (
            f'<button class="nbtn" data-src="{v[2]}"'
            + (' aria-pressed="true"' if i == first_enabled else "")
            + f'>{v[0]}<span class="s">{v[1]}</span></button>'
            if v[2]
            else f'<button class="nbtn" disabled style="opacity:.5;cursor:not-allowed" title="此节点暂未采集数据">{v[0]}<span class="s">{v[1]}</span></button>'
        )
        for i, v in enumerate(views)
    )
    if has_data:
        body = (
            f'<div class="picker">{btns}</div>'
            '<iframe id="view" class="frame" title="时间点情报"></iframe>'
            '<div class="note">时间轴自动产出：赛前 -> 每小局（BP 后 / 局中 / 局末）-> '
            '赛后整场复盘；缺失节点自动出现，不 404。</div>'
        )
    else:
        # 无任何节点文件：明确标注「本场暂无弹幕情报」，不硬造。
        # 教训 2026-10-25：BETBOOM vs Nemiga / Vitality vs The MongolZ 19:00
        # 国际 CS2 场次英文 KICK 源故障、中文解说未覆盖，0 弹幕；旧逻辑给
        # 9 个「此节点暂未采集数据」占位按钮语义含糊，且早退让陈旧壳残留在线。
        body = (
            '<div style="background:var(--card);border:1px solid var(--line);'
            'border-radius:16px;padding:28px 24px;margin-bottom:14px">'
            '<div style="font-size:15px;font-weight:700;color:var(--ink);'
            'margin-bottom:6px">本场暂无弹幕情报</div>'
            '<div style="font-size:13px;color:var(--sub);line-height:1.7">'
            '当前未采集到弹幕数据，暂无情报输出，不硬造。</div>'
            '<div style="font-size:12px;color:var(--sub);margin-top:8px;'
            'line-height:1.6">可能原因：比赛尚未进入采集窗口，或该时段无可用弹幕源'
            '（英文 KICK 源故障 / 中文解说未覆盖）。</div>'
            '</div>'
            '<div class="note">缺失节点随采集推进自动出现，不 404。</div>'
        )
    shell = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>比赛详情 · {a} vs {b} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 56px}}
.wrap{{max-width:980px;margin:0 auto}}
.top{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
.brand{{font-weight:700;font-size:14px;color:var(--ink);text-decoration:none}}
.crumb{{font-size:12px;color:var(--sub)}} .crumb b{{color:var(--ink)}}
.navi{{font-size:12px;color:var(--sub);text-decoration:none;margin-left:4px}} .navi:hover{{color:var(--accent)}}
h1{{font-size:24px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:14px}}
.picker{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.nbtn{{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:8px 16px;font-size:13px;font-weight:600;color:var(--sub);cursor:pointer}}
.nbtn:hover{{color:var(--accent)}} .nbtn[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
.nbtn .s{{display:block;font-size:10px;font-weight:400;opacity:.85}}
.frame{{width:100%;height:900px;border:1px solid var(--line);border-radius:16px;background:#fff}}
.note{{color:var(--sub);font-size:12px;margin-top:12px}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<div class="top">
  <a class="brand" href="../index.html">弹幕情报库</a>
  <span class="crumb">首页 › <a href="today.html" class="navi">今日比赛</a> › <b>{a} vs {b}</b></span>
  <span style="margin-left:auto"><a class="navi" href="history.html">历史情报库</a> <a class="navi" href="../subscribe.html">订阅</a></span>
</div>
<h1>{a} vs {b}</h1>
<div class="sub">{league} · {date} · 按时间点切换查看该场比赛不同阶段的情报输出</div>
{body}
<footer>弹幕情报库 · 比赛时间轴 · {date}</footer>
</div>
<script>
(function () {{
  var btns = document.querySelectorAll(".nbtn");
  var view = document.getElementById("view");
  function show(src) {{ view.src = src + (src.indexOf("?") < 0 ? "?embed=1" : "&embed=1"); }}
  btns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      btns.forEach(function (x) {{ x.setAttribute("aria-pressed", x === b ? "true" : "false"); }});
      show(b.getAttribute("data-src"));
    }});
  }});
  var first = document.querySelector(".nbtn[aria-pressed='true']");
  if (first) show(first.getAttribute("data-src"));
}})();
</script>
</body></html>"""
    out = REPORTS / f"match_{mid}.html"
    out.write_text(shell, encoding="utf-8")
    return out


def process_match(m: dict, all_files: list) -> None:
    """单个比赛的节点生成流程（预节点 / 结束检测 / 局节点 / 终局复盘）。

    2026-10-18（③ 并行度再加）：从 main() 的 for-matches 循环体抽出为独立函数，
    供 ThreadPoolExecutor 跨比赛并行。原本面向 for-matches 循环的 continue 已改为
    return（函数级提前返回）；面向 for-gi 内层循环的 continue 保持不变。
    """
    mid = m.get("id") or "-"
    is_non_pm = bool(m.get("_hupu") or m.get("_official"))
    # 作废场次跳过（2026-08-26 固化，AGENTS 19：Aurora-G2 混源作废后
    # 流水线仍尝试生成节点，浪费 Codex 资源并阻塞其他比赛）
    if m.get("intel_voided"):
        print(f"[pipeline] {mid}: intel_voided, skip", flush=True)
        return
    # 已结束的非 Polymarket 场次跳过（2026-10-16 固化，AGENTS 数据可靠性红线）：
    # hupu/官方场次无 Polymarket 小局市场，整场复盘路径本就被 all_closed 门禁挡住；
    # closed=true 时仍走兜底时间窗切片，会把闲时/他场弹幕误切成该场节点
    # （教训：10-16 C9-KC / FUR-MVK / Legacy-FURIA 被误生成 G1 节点，
    #  562 行 Aurora-9z 弹幕混入 Legacy-FURIA）。跳过判定见 _closed_non_polymarket_skip：
    # 仅当从未生成过小局节点才跳过，已开始的场次继续跑完剩余节点。
    if _closed_non_polymarket_skip(m, mid):
        print(f"[pipeline] {mid}: 非 Polymarket 已结束且从未生成节点，跳过（避免误切片）", flush=True)
        return
    st_file = STATE_DIR / f"{mid}.json"
    if st_file.exists():
        print(f"[pipeline] {mid}: already done, skip")
        return
    files = league_files(m, all_files)
    max_games = format_of(m)
    # 2026-10-25 回归修复：closed 的 hupu 场次用官方比分定实际局数（如 2:0 -> 2），
    # 防止兜底时间窗按 format_of 默认 5 补出不存在的 G3/G4/G5 节点（10-16 教训）。
    if m.get("closed") and m.get("_hupu"):
        hg = _hupu_total_games(m)
        if hg:
            max_games = min(hg, MAX_GAME)
    teams = m["teams"]
    # 2026-10-28 固化：结算合并的精简条目只有 date 无 start_time（merge_settlements
    # 只落 id/date/teams/league/result_inferred），start_time 兜底 date 避免 date="" 导致
    # 报告文件名双下划线（教训：T1-CFO / KC-BLG 10-26 BO1 结算后 start_time=null）。
    date = (m.get("start_time") or m.get("date") or "")[:10]
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # 赛前节点：开赛前 60 分钟内生成赛前情报页（幂等）
    pre_state = STATE_DIR / f"{mid}_pre.json"
    start_dt = None
    try:
        start_dt = datetime.datetime.fromisoformat(str(m.get("start_time", "")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        start_dt = None
    if (
        not pre_state.exists()
        and start_dt
        and now_utc < start_dt
        and (start_dt - now_utc).total_seconds() <= 3600
    ):
        slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
        pre_report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_pre.html"
        gtype = (mid or "").split("-")[0].lower()
        gtype = "cs2" if gtype.startswith("cs") else ("dota2" if (gtype.startswith("dota") or gtype.startswith("ti")) else "lol")
        rc = 0
        slice_rows_n = 0
        pre_mode = "history"
        if gtype in ("lol", "cs2"):
            # 规则层渲染赛前历史页（1 队伍交手情况 + 2 队伍比赛近况），不走 Codex/切片
            # （2026-11-22 用户定稿：赛前页从 4 段改为两栏历史数据，规则层系统注入）。
            try:
                render_pregame.build_pregame(gtype, teams, date, m.get("league", "-"), slug_id, pre_report,
                                             before=(m.get("start_time") or date))
            except Exception as e:  # noqa: BLE001
                print(f"[pipeline] {mid}: pre history render failed: {e}", flush=True)
                rc = 1
        else:
            # dota2 无历史数据源，保持旧 Codex 4 段路径
            pre_mode = "codex"
            pre_slice = SLICE_DIR / f"{slug_id}_pre.jsonl"
            pre_start = (start_dt - datetime.timedelta(minutes=90)).isoformat()
            slice_rows_n = slice_rows(pre_start, files, pre_slice)
            pre_intel = STATE_DIR / f"{slug_id}_pre_intel.json"
            subprocess.run(
                [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
                 "--input", str(pre_slice), "--out", str(pre_intel)],
                timeout=180,
                check=False,
            )
            print(f"[pipeline] {mid}: pre slice {slice_rows_n} rows, generating pre intel...", flush=True)
            rc, so, se = run_codex_report(slug_id, teams, date, pre_intel, pre_slice, pre=True)
        pre_state.write_text(
            json.dumps(
                {
                    "match": mid,
                    "slice_rows": slice_rows_n,
                    "mode": pre_mode,
                    "report": str(pre_report),
                    "report_exists": pre_report.exists(),
                    "codex_rc": rc,
                    "generated_at": now_iso(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[pipeline] {mid}: pre done rc={rc} exists={pre_report.exists()}", flush=True)
        build_timeline_shell(mid, teams, m.get("league", "-"), date)

    print(f"[pipeline] {mid}: checking end...", flush=True)
    # 防误判门槛：比赛必须已开始且进行 ≥30 分钟，才允许结束检测
    # （教训 2026-08-25：GX-G2 / CS2 场次在开赛前被弹幕闲聊误判"结束"）
    started_enough = True
    if start_dt:
        started_enough = (now_utc - start_dt).total_seconds() >= 1800
    if not started_enough:
        print(f"[pipeline] {mid}: not started or started <30min ago, skip end-detect")
        out = "未确认（进行中）"
    else:
        out = verify_end(teams, files)
    first = out.splitlines()[0] if out else "no output"
    print(f"  {first}", flush=True)
    # 2026-08-26 教训：verify_end 返回「需人工确认」（未确认信号）时
    # 仍要继续出局中节点，禁止当终局写整场状态跳过后续节点
    # （KT-BRO 曾因此整场被"already done, skip"，G1 BP/MID 全部缺失）。
    # 2026-10-25 回归修复：非 Polymarket 场次（hupu/官方）无小局市场，终局路径的
    # all_closed 门禁永远 false -> 直接 return，会把已开始的场次后半程节点截断。
    # 非 Polymarket 场次一律走小局节点路径（兜底时间窗，实际局数已由官方比分定），
    # 不走终局整场复盘路径。
    slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
    # 2026-11-01 固化：弹幕「确认结束」是软信号，须经 game_status 结构事实仲裁；
    # 系列未结算（未 all_closed 且未已决）时，即使弹幕判结束也继续走小局节点路径，
    # 否则 G1 后的假终局会把 G2+ 节点整段截断（教训：HLE-BLG 2-0 只剩 G1 + 终局复盘）。
    if "确认结束" not in out or is_non_pm or not _series_settled(slug_id, max_games):
        # 未结束 -> 先按小局出节点（G{i} BP后 / 局中 / 局末）；
        # 小局市场不可用时退回 30 分钟局中快照（兜底）
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        start_dt_parse = None
        try:
            start_dt_parse = datetime.datetime.fromisoformat(
                str(m.get("start_time", "")).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            start_dt_parse = None
        gstatus: dict[int, dict] = {}
        if start_dt_parse and now_utc >= start_dt_parse:
            gstatus = read_game_status(slug_id)
            if gstatus is None:
                gstatus = fetch_game_markets(slug_id)  # 服务器直连通常 451，仅兜底
        if gstatus is None:
            gstatus = {}
        if not gstatus:
            # 兜底：无小局结算状态 -> 时间窗估算 + 弹幕 GG 检测
            if start_dt_parse is None:
                # 2026-10-31 固化：start_time 缺失/不可解析时无法锚定时间窗，
                # 直接返回下轮重试，禁止 game_t=None 做 timedelta 算术导致崩溃
                # （教训：T1-CFO / KC-BLG 结算后 start_time=null）。
                print(f"[pipeline] {mid}: start_time missing, skip fallback window", flush=True)
                return
            game_t = start_dt_parse
            for gi in range(1, max_games + 1):
                # 教训 2026-08-25：now_utc 必须每局刷新——节点生成是串行的
                # （单个 Codex 8-9 分钟），用启动时刻判断窗口会跳过后续节点
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                # 2026-10-31 修复：进行中的 hupu 场次用官方比分（scores 增量）判定
                # 系列是否结束，替代弹幕 GG 兜底——弹幕关键词"夺冠/晋级/出局"是
                # 赛事级闲谈，会在 G2 就误判系列结束（教训：Vitality vs MOUZ G2
                # 节点被 detect_match_end_gg 假阳性截断）。弹幕 GG 仅作比分读不到时兜底。
                h_played: int | None = None
                h_completed = False
                if m.get("_hupu"):
                    h_played, h_completed = _hupu_score_state(m)
                if gi > 1:
                    if h_played is not None:
                        # 已结束系列最多补到已结算局数；进行中系列再 +1（当前局）。
                        # 尚未打到 gi 即系列结束，停止推进，不再生成后续小局节点。
                        last_gi = h_played + (0 if h_completed else 1)
                        if gi > last_gi:
                            print(
                                f"[pipeline] {mid}: series over per hupu score "
                                f"(played={h_played}, completed={h_completed}), "
                                f"stop game nodes",
                                flush=True,
                            )
                            break
                    elif detect_match_end_gg(files, game_t - datetime.timedelta(minutes=10)):
                        print(f"[pipeline] {mid}: series-end GG detected, stop game nodes", flush=True)
                        break
                g_start = game_t + datetime.timedelta(minutes=bp_gap_minutes(m))
                if now_utc >= g_start + datetime.timedelta(minutes=bp_node_wait_minutes(m)):
                    # BP 节点不因错过窗口而放弃：切片限定 BP/开局时段，晚生成标注"补发"
                    generate_game_node(
                        mid, teams, date, slug_id, gi, "bp",
                        bp_slice_from(g_start, start_dt_parse), files,
                        slice_end=(g_start + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN)).isoformat(),
                        late=now_utc > g_start + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN),
                        max_games=max_games,
                    )
                if now_utc >= g_start + datetime.timedelta(minutes=GAME_NODE_MID_MIN):
                    generate_game_node(
                        mid, teams, date, slug_id, gi, "mid", g_start, files,
                        max_games=max_games,
                    )
                gg = detect_game_end_gg(files, g_start)
                # 2026-10-16 修复：CS2 弹幕"赢/结束/gg"是轮次级闲谈，8 分钟轻松 ≥8 条，
                # 会在局刚开始几分钟就误判"局末"（教训：Aurora vs 9z G2 开局 4 分钟即
                # 被误判结束、推进到不存在的 G3）。加最小局时长门禁。
                gg = gg and (now_utc - g_start).total_seconds() >= GAME_MIN_LEN_MIN * 60
                est_len = GAME_EST_LEN_MIN
                if m.get("league") == "CS2":
                    # CS2 轮次级"gg/下一把/第X局"噪声极多，gg 兜底不可靠直接禁用；
                    # 地图含加时可 40-60 分钟，时间窗估算更保守（10-16 OT 图 63 分钟）。
                    gg = False
                    est_len = GAME_EST_LEN_MIN_CS2
                g_end_est = g_start + datetime.timedelta(minutes=est_len)
                # 2026-10-31：hupu 场次小局结束以官方比分为准（gi 已计入 scores），
                # 不再用时间窗/弹幕估计；比分读不到时退回 gg/时间窗兜底。
                # 注意：比分可读时不能用 now>=g_end_est 的时间窗兜底——锚点跨局后
                # g_start 可能已是过去时，时间窗会把未结束的当前局误判为结束。
                if h_played is not None:
                    game_ended = gi <= h_played
                else:
                    game_ended = gg or now_utc >= g_end_est
                if game_ended:
                    if h_played is not None and gi <= h_played:
                        end_basis = "hupu"
                    elif gg:
                        end_basis = "gg"
                    else:
                        end_basis = "est"
                    generate_game_node(
                        mid, teams, date, slug_id, gi, "end", g_start, files,
                        end_basis=end_basis,
                        max_games=max_games,
                    )
                    game_t = anchor_next_game(mid, gi, now_utc)
                else:
                    # 2026-10-16 修复：当前小局尚未结束（无市场状态，时间/弹幕都不满足）
                    # 时，必须 break 停止推进局号；若继续 game_t=g_start 会让下一局
                    # g_start=本局g_start+8min，导致提前生成不存在的 G2/G3 节点
                    # （教训：Aurora vs 9z 无 g2_end 却生成 g3_bp）。
                    break
            return

        if gstatus:
            game_t = start_dt_parse
            prev_ended = True  # 第 1 局：开赛后即可进行
            for gi in range(1, max_games + 1):
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                # 及时性：每个小局迭代时重读结算状态（一次生成 8-9 分钟，
                # 期间新结束的小局必须当轮就捕获，不能等下一轮）
                gstatus = read_game_status(slug_id) or gstatus
                mk = gstatus.get(gi)
                if mk is None:
                    # 2026-10-29 固化：系列已决（如 BO3 2-0）时，缺失市场的小局是
                    # "不存在的局"，兜底时间窗会误生成 G3 节点（教训：MKOI-T1 2-0
                    # 却生成 g3_bp/mid/end）。此时停止推进，不再生成后续小局节点。
                    if _series_decided(gstatus, max_games):
                        print(
                            f"[pipeline] {mid}: series already decided (BO{max_games}), "
                            f"stop extra game nodes at G{gi}",
                            flush=True,
                        )
                        break
                    # 市场缺失（如 G5 条件市场）-> 按时间窗/弹幕兜底出节点
                    g_start_est = game_t + datetime.timedelta(minutes=bp_gap_minutes(m))
                    if prev_ended:
                        tasks = []
                        if now_utc >= g_start_est + datetime.timedelta(minutes=bp_node_wait_minutes(m)):
                            tasks.append(functools.partial(
                                generate_game_node,
                                mid, teams, date, slug_id, gi, "bp",
                                bp_slice_from(g_start_est, start_dt_parse), files,
                                slice_end=(g_start_est + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN)).isoformat(),
                                late=now_utc > g_start_est + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN),
                                max_games=max_games,
                            ))
                        if now_utc >= g_start_est + datetime.timedelta(minutes=GAME_NODE_MID_MIN):
                            tasks.append(functools.partial(
                                generate_game_node,
                                mid, teams, date, slug_id, gi, "mid", g_start_est, files,
                                max_games=max_games,
                            ))
                        run_nodes_parallel(tasks)
                        gg = detect_game_end_gg(files, g_start_est)
                        gg = gg and (now_utc - g_start_est).total_seconds() >= GAME_MIN_LEN_MIN * 60
                        est_len = GAME_EST_LEN_MIN
                        if m.get("league") == "CS2":
                            # CS2 轮次级"gg/下一把/第X局"噪声极多，gg 兜底不可靠直接禁用；
                            # 地图含加时可 40-60 分钟，时间窗估算更保守。
                            gg = False
                            est_len = GAME_EST_LEN_MIN_CS2
                        g_end_est = g_start_est + datetime.timedelta(minutes=est_len)
                        if gg or now_utc >= g_end_est:
                            generate_game_node(
                                mid, teams, date, slug_id, gi, "end", g_start_est, files,
                                end_basis="gg" if gg else "est",
                                max_games=max_games,
                            )
                            game_t = anchor_next_game(mid, gi, now_utc)
                        else:
                            game_t = g_start_est
                    else:
                        game_t = g_start_est
                    prev_ended = False
                    continue
                g_start = game_t + datetime.timedelta(minutes=bp_gap_minutes(m))
                # 2026-08-26 教训：game_status 快照滞后（winner 未及时置位）时，
                # 局后节点会延迟——小局结束判定必须覆盖「价格 ≥0.99 即结算」
                # （Polymarket 小局市场常保持 closed=false 但已定价 99.95c）。
                _prices = mk.get("prices") or []
                ended = (
                    bool(mk.get("closed"))
                    or mk.get("winner") is not None
                    or any(
                        isinstance(p, (int, float)) and p >= 0.99
                        for p in _prices
                    )
                )
                if ended:
                    generate_game_node(
                        mid, teams, date, slug_id, gi, "end", g_start, files, end_basis="market",
                        max_games=max_games, winner_side=_winner_side(mk, teams),
                    )
                    # 锚定上一局真实结束时间（教训 2026-08-25：用 now 会每轮滑动，
                    # 导致 G2+ 的 BP 窗口永远追不上、节点永不生成）
                    end_state = STATE_DIR / f"{mid}_g{gi}_end.json"
                    try:
                        game_t = datetime.datetime.fromisoformat(
                            json.loads(end_state.read_text(encoding="utf-8"))["generated_at"]
                            .replace("Z", "+00:00")
                        )
                    except Exception:  # noqa: BLE001
                        game_t = now_utc
                    prev_ended = True
                else:
                    if prev_ended:
                        tasks = []
                        if now_utc >= g_start + datetime.timedelta(minutes=bp_node_wait_minutes(m)):
                            tasks.append(functools.partial(
                                generate_game_node,
                                mid, teams, date, slug_id, gi, "bp",
                                bp_slice_from(g_start, start_dt_parse), files,
                                slice_end=(g_start + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN)).isoformat(),
                                late=now_utc > g_start + datetime.timedelta(minutes=GAME_NODE_BP_MAX_MIN),
                                max_games=max_games,
                            ))
                        if now_utc >= g_start + datetime.timedelta(minutes=GAME_NODE_MID_MIN):
                            tasks.append(functools.partial(
                                generate_game_node,
                                mid, teams, date, slug_id, gi, "mid", g_start, files,
                                max_games=max_games,
                            ))
                        run_nodes_parallel(tasks)
                    game_t = g_start
                    prev_ended = False
            return

        # 兜底：30 分钟局中快照
        live_file = STATE_DIR / f"{mid}_live.json"
        recent = False
        if live_file.exists():
            try:
                prev = datetime.datetime.fromisoformat(
                    json.loads(live_file.read_text(encoding="utf-8"))["generated_at"]
                    .replace("Z", "+00:00")
                )
                recent = (now_utc - prev).total_seconds() < LIVE_INTERVAL_SEC
            except Exception:  # noqa: BLE001
                recent = False
        if recent:
            print(f"[pipeline] {mid}: live snapshot fresh, skip")
            return

        def parse_utc(v: str):
            try:
                return datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        start_dt = parse_utc(m.get("start_time", ""))
        end_dt = parse_utc(m.get("end_time", ""))
        if not start_dt or start_dt > now_utc or (end_dt and end_dt < now_utc):
            print(f"[pipeline] {mid}: not in live window, skip")
            return

        slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
        slice_file = SLICE_DIR / f"{slug_id}_live.jsonl"
        n = slice_rows(m.get("start_time", ""), files, slice_file)
        intel_json = STATE_DIR / f"{slug_id}_live_intel.json"
        subprocess.run(
            [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
             "--input", str(slice_file), "--out", str(intel_json)],
            timeout=180,
            check=False,
        )
        print(f"[pipeline] {mid}: live slice {n} rows, generating live snapshot...", flush=True)
        rc, so, se = run_codex_report(slug_id, teams, date, intel_json, slice_file, live=True)
        ts = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%H%M")
        report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_live_{ts}.html"
        live_file.write_text(
            json.dumps(
                {
                    "match": mid,
                    "slice_rows": n,
                    "report": str(report),
                    "report_exists": report.exists(),
                    "codex_rc": rc,
                    "generated_at": now_iso(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[pipeline] {mid}: live snapshot done rc={rc} exists={report.exists()}", flush=True)
        build_timeline_shell(mid, teams, m.get("league", "-"), date)
        return

    # 2026-11-01 固化：终局门禁已前移到路由前（_series_settled 在路由条件里仲裁），
    # 走到这里 = 弹幕判「确认结束」且系列已在结构上结算，直接出整场复盘 + 补 end。
    # 2026-10-28 固化：终局补 end——BO1/已确认结束的场次，小局路径的 end 兜底
    # （时间窗 est_len / gg）常来不及在 verify_end 判终局前触发，导致已生成
    # bp/mid 的小局缺 end 节点（教训：T1-CFO、KC-BLG 10-26 BO1 只有 g1_bp/mid）。
    # 终局时把「有 bp/mid 无 end」的小局补成 end 节点，切片用 mid 的 slice_from
    # （= 本局起点）到 now（终局已过，全量），幂等（有 end 状态即跳过）。
    for _gi in range(1, max_games + 1):
        if (STATE_DIR / f"{mid}_g{_gi}_end.json").exists():
            continue
        _gstart = None
        for _ph in ("mid", "bp"):
            _st = STATE_DIR / f"{mid}_g{_gi}_{_ph}.json"
            if not _st.exists():
                continue
            try:
                _gstart = datetime.datetime.fromisoformat(
                    json.loads(_st.read_text(encoding="utf-8"))
                    .get("slice_from", "")
                    .replace("Z", "+00:00")
                )
            except Exception:  # noqa: BLE001
                _gstart = None
            if _gstart:
                break
        if not _gstart:
            continue
        generate_game_node(
            mid, teams, date, slug_id, _gi, "end", _gstart, files,
            end_basis="settlement", max_games=max_games,
        )

    slice_file = SLICE_DIR / f"{slug_id}.jsonl"
    n = slice_rows(m.get("start_time", ""), files, slice_file)
    intel_json = STATE_DIR / f"{slug_id}_intel.json"
    subprocess.run(
        [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
         "--input", str(slice_file), "--out", str(intel_json)],
        timeout=180,
        check=False,
    )
    print(f"[pipeline] {mid}: slice {n} rows, generating report via Codex...", flush=True)
    rc, so, se = run_codex_report(slug_id, teams, date, intel_json, slice_file)
    report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}.html"
    # 2026-10-26 固化：整场复盘 HTML 未落盘时禁止写 st_file（否则下次 tick
    # 看到 st_file 存在 -> "already done, skip" -> 复盘永久缺失）。
    # 教训：HLE-IG 10-25 因 reports 目录属主错误致 Codex 写盘失败，series 状态
    # 仍标 done，复盘页再也补不回来（与节点页 report missing 同类根因）。
    if not report.exists():
        print(f"[pipeline] {mid}: series report missing rc={rc}（下轮重试）", flush=True)
        return
    st_file.write_text(
        json.dumps(
            {
                "match": mid,
                "teams": teams,
                "date": date,
                "verified": "确认结束" in out,
                "slice_rows": n,
                "intel_json": str(intel_json),
                "report": str(report),
                "report_exists": report.exists(),
                "codex_rc": rc,
                "generated_at": now_iso(),
                "note": "弹幕多信号确认" if "确认结束" in out else "需人工确认·结果待官方",
                "codex_stdout_tail": so,
                "codex_stderr_tail": se,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[pipeline] {mid}: done rc={rc} report_exists={report.exists()}", flush=True)
    build_timeline_shell(mid, teams, m.get("league", "-"), date)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--match", default=None)
    args = ap.parse_args()

    if not MATCHES.exists():
        print("[pipeline] no data/matches_today.json (run local export_today_matches.py)")
        return
    data = json.loads(MATCHES.read_text(encoding="utf-8"))
    matches = [m for m in data.get("matches", []) if m.get("teams") and len(m["teams"]) == 2]
    if args.match:
        matches = [m for m in matches if m.get("id") == args.match]
    if not matches:
        print("[pipeline] no matches for today")
        return

    # 弹幕原始源目录结构兼容：采集端仍在写旧结构 danmu/<platform>/<file>.jsonl
    # （platform = huya/kick/soop/twitch），而读取端 2026-09-10 改成了
    # danmu/<game>/<platform>/<file>.jsonl（game = lol/cs2/dota2）。game 层目录
    # 从未存在 -> all_files 扫出 0 文件 -> 所有比赛切片 0 字节（2026-10-25 回归）。
    # 两种结构都扫，用 set 去重（两种 glob 结果天然不相交，set 仅兜底）。
    # 避免误把 danmu/slices/ 等派生目录的切片文件当成原始弹幕源：派生目录
    # 不在这两种 glob 的一级/二级通配层内（slices 是 DANMU 的兄弟目录）。
    all_files = sorted(
        set(
            list(DANMU.glob("*/*.jsonl"))  # 旧结构 danmu/<platform>/<file>.jsonl
            + [  # 新结构 danmu/<game>/<platform>/<file>.jsonl
                p
                for game in GAME_SLUGS
                for p in (DANMU / game).glob("*/*.jsonl")
            ]
        )
    )
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # 及时性（2026-08-26）：定时器改 1 分钟后必须加锁，防止多实例重叠
    # 争抢 AI 额度导致每个节点更慢；已有实例运行时本轮直接跳过。
    lock_fd = open(STATE_DIR / "pipeline.lock", "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[pipeline] another run in progress, skip")
        return

    # ③ 并行度再加（2026-10-18）：跨比赛并行，多场同时生成不再互相阻塞。
    # 有界并发（MAX_MATCH_WORKERS，默认 3），避免争抢 AI 额度；每场内部仍走
    # run_nodes_parallel 的 BP+局中并行。I/O 密集（子进程/HTTP），线程即可。
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=MAX_MATCH_WORKERS) as ex:
        futs = [ex.submit(process_match, m, all_files) for m in matches]
        for f in futs:
            f.result()


if __name__ == "__main__":
    main()
