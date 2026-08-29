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
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path("/opt/danmu-intel")
MATCHES = ROOT / "data" / "matches_today.json"
STATE_DIR = ROOT / "runtime" / "vps_intel"
SLICE_DIR = ROOT / "data" / "intel_slices"
REPORTS = ROOT / "reports"
DANMU = ROOT / "docs" / "data" / "danmu"
PY = ROOT / ".venv" / "bin" / "python"
CODEX = "/root/.local/bin/codex"
LIVE_INTERVAL_SEC = 1800  # 局中情报快照限频：30 分钟一份
GAME_BP_GAP_MIN = 8    # 开赛/上一局结束后到本小局 BP 的估计间隔（分钟）
GAME_NODE_BP_MIN = 4   # 小局 BP 后/开局节点：小局开始后 X 分钟（2026-08-26 由 12+8 提速）
GAME_NODE_MID_MIN = 16  # 小局局中节点：小局开始后 X 分钟（由 22 提速）
GAME_NODE_BP_MAX_MIN = 20  # BP 后节点最晚窗口（错过则不再补发，避免"BP后"内容失真）
MAX_GAME = 5
GAME_STATUS_FILE = ROOT / "data" / "game_status.json"
GAME_STATUS_FRESH_SEC = 1200  # 本地推送的小局状态 20 分钟内视为新鲜

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
GAME_EST_LEN_MIN = 35  # 无市场状态时的小局时长估计（LoL BO 系列）
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
        out[gi] = {"closed": bool(mk.get("closed")), "prices": prices, "winner": winner}
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
                ts = r.get("unixtime")
                if ts is None:
                    ts = r.get("ts")
                    try:
                        ts = datetime.datetime.fromisoformat(
                            str(ts).replace("+0800", "+08:00")
                        ).timestamp()
                    except Exception:  # noqa: BLE001
                        ts = None
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
                ts = r.get("unixtime")
                if ts is None:
                    ts = r.get("ts")
                    try:
                        ts = datetime.datetime.fromisoformat(
                            str(ts).replace("+0800", "+08:00")
                        ).timestamp()
                    except Exception:  # noqa: BLE001
                        ts = None
                if ts is None or ts < lo:
                    continue
                msg = (r.get("message") or r.get("text") or "").lower()
                if any(k in msg for k in MATCH_END_KW):
                    hits += 1
                    if hits >= 5:
                        return True
    return False


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
) -> None:
    """生成一个小局节点（幂等，成功后写状态；失败不写，下轮重试）。"""
    st = STATE_DIR / f"{mid}_g{gi}_{gphase}.json"
    if st.exists():
        return
    slice_file = SLICE_DIR / f"{slug_id}_g{gi}_{gphase}.jsonl"
    n = slice_rows(slice_from.isoformat(), files, slice_file, slice_end)
    intel_json = STATE_DIR / f"{slug_id}_g{gi}_{gphase}_intel.json"
    subprocess.run(
        [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
         "--input", str(slice_file), "--out", str(intel_json)],
        timeout=180,
        check=False,
    )
    # 2026-08-26 用户定稿：弃用快节点输出（未经验证、结构混乱），
    # 恢复 Codex 全量路径——时效可稍慢（数分钟），但信息准确、结构清晰（昨日标准）。
    source = "codex"
    print(f"[pipeline] {mid}: G{gi} {gphase} slice {n} rows, generating (Codex 全量)...", flush=True)
    rc, so, se = run_codex_report(
        slug_id, teams, date, intel_json, slice_file,
        game=gi, gphase=gphase, end_basis=end_basis, late=late,
    )
    report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_g{gi}_{gphase}.html"
    if not report.exists():
        print(f"[pipeline] {mid}: G{gi} {gphase} report missing rc={rc}（下轮重试）", flush=True)
        return
    write_md_mirror(report)  # HTML + MD 双格式（2026-08-26 定稿）
    st.write_text(
        json.dumps(
            {
                "match": mid,
                "game": gi,
                "phase": gphase,
                "slice_rows": n,
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
            else:
                end_note = (
                    f"第 {game} 小局按时间窗估计已结束（局末·待结算校准），结果待官方核对。"
                )
        phase = (
            f"比赛 {teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行第 {game} 小局，"
            f"节点=G{game}｜{glabel}。{end_note}生成「局中弹幕情报快照（G{game}）」，"
            f"页面显著标注「局中·非终局，结果待定」，进度以弹幕口径为准；"
            f"内容聚焦本小局：BP/阵容、对线、节奏、关键团战、灰信号、盘口讨论、弹幕密度峰值；"
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
            phase += f"（本场已确认结果：{result_note}，页面结果总览直接采用并标注来源「Polymarket 结算」）"
    prompt = (
        f"{phase}。\n"
        f"【时间显示规范（2026-08-27 用户定稿，最高）】页面所有时间（数据窗口、"
        f"弹幕样本时间戳、节点时刻）一律用北京时间展示（UTC+8）；弹幕原始时间戳"
        f"换算后展示北京时间（如 16:08 而不是 08:08），UTC 仅作括号备注；"
        f"禁止直接展示 UTC 时间。\n"
        f"请按以下流程生成情报页：\n"
        f"1) 先完整阅读技能文件 /root/.codex/skills/intel-report/SKILL.md 与模板 "
        f"knowledge/INTEL_HTML_TEMPLATE.md、knowledge/LIVE_INTEL_SCHEMA.md；\n"
        f"2) 读取规则层情报 JSON {intel_json} 与弹幕切片 {slice_file}；\n"
        f"3) 页面结构必须严格按 12 段决策导向模板（INTEL_HTML_TEMPLATE 二.10，缺一不可），"
        f"每段用 <h2><span class=\"no\">N</span>标题</h2> 编号："
        f"0 核心情报速览 → 1 比赛信息与结果总览/状态核验 → 2 灰信号汇总（风险·观众质疑非结论）→ "
        f"3 BP 锚点与选人情报 → 4 盘口与市场讨论 → 5 方向性情报板（正锚×负锚×共识×灰信号条件预测）→ "
        f"6 情报含义与决策落点（LONG/SHORT）→ 7 逐局复盘（证据层）→ 8 队伍/人员画像（带提及量）→ "
        f"9 联赛规律与版本 → 10 预测验证回填 → 11 数据与溯源；禁止合并/省略段落；\n"
        f"4) 【核心情报速览·硬性格式】第一屏 = 比分/进度一行（含「弹幕口径·官方待回填」）+ "
        f"TOP 信号 3-5 条，按「风险→锚点→盘口→共识」顺序，每条 = 类型标签（风险/锚点/盘口/共识）+ "
        f"一句话中文意译（≤30 字，含关键对象与方向）+ 溯源（→ 详 §N）+ "
        f"一句话决策落点（本场边际信息/关注点）。样例见 reports/intel_danmu_LCK-KT-BRO_G3_2026-08-26.html "
        f"（用户定稿标准，速览卡禁止出现裸弹幕原文/队伍提及表原始数据）；\n"
        f"5) 结果总览（标注「弹幕口径·待官方确认」）、逐局复盘（当前局已发生片段+时间线，未发生写「待观察」）、"
        f"队伍/人员画像（必须引用长期库，带提及量）、灰信号（写明「观众质疑，非结论」）、"
        f"弹幕密度峰值、可验证情报痕迹、结果来源；\n"
        f"6) 方向板：正锚点（看好谁赢，含对象/依据/时间/验证）、负锚点（看衰谁输）、群体共识（+分歧+样本量）、"
        f"灰信号条件预测（若兑现指向哪边）；无锚点写「今日无锚点」，无共识写「共识不足」，"
        f"无灰信号写「今日无灰信号」；\n"
        f"7) 「数据完整性」三栏：实际数据源（本场用到的直播间列表）/ 预期数据源"
        f"（该联赛默认采集集，见 knowledge/DANMU_CAPTURE_RULES.md 第 17 节）/ 缺口"
        f"（离线未采/采集中断/VOD 未补，无缺口写「无」）；缺源不交付完整结论；\n"
        f"8) 硬信息六项禁止删除：人员画像带提及量、逐局阵容（英雄+选手）、BP 后战绩情报"
        f"（无则写「无战绩情报提及」）、密度时间线、跨源一致性提示、比赛元数据（全称/league/slug/赛制）；\n"
        f"9) 结尾给「本场长期沉淀点」至少 1 条；无样本写「样本不足」，不硬造。\n"
        f"10) 【情报来源分层·最高纪律（2026-08-26 用户定稿）】每条结论必须带证据来源标签"
        f"（本场弹幕 / 前局弹幕 / 历史画像 / 盘口 / 推测·待验证），溯源段逐条对应；"
        f"核心情报必须来自本场弹幕，严禁无中生有；仅简单推断、无数据支撑的不写；"
        f"推测必须显式标注「推测·待验证」并与事实分离呈现；历史画像引用须带时间；"
        f"缺源（如 SOOP 离线）显式标注为缺口，禁止用历史画像冒充本场数据。\n"
        f"11) 生成 SAP/Apple 风格（浅底 #f5f5f7、白卡片、单一强调色、系统字体栈）紧凑清爽完整 HTML "
        f"写入 {report}（含 </body></html>）。"
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
                return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return ""


def league_files(m: dict, files: list[Path]) -> list[Path]:
    """按比赛联赛过滤直播间文件（2026-08-26 用户定稿：国外源已停用，虎牙优先）。
    - LoL：只用虎牙 + SOOP；
    - CS2：只用虎牙 CSBOY 系（csboy_official=马西西 123321 / csboy_mo=321123 / blast；
      maxixi 已删除——与 csboy_official 123321 同一直播间，2026-08-27 彻底移除）
      + KICK（eslcs/gaules/esportsworldcup/cs2_maincast）；
    - 其他：全量。
    教训：CS2 切片曾混入虎牙 LoL 直播间导致 CS2 页出现 KT/BRO；LoL 页曾混入
    Twitch co-stream 的跨场噪音（T1/WE 等）。
    """
    slug = str(m.get("id") or "")
    if slug.startswith("cs2"):
        return [
            p for p in files
            if (
                ("huya" in p.name and any(k in p.name for k in ("csboy", "blast")))
                or "kick" in p.name
            )
        ]
    if slug.startswith("lol"):
        # LoL 排除 CSBOY（CS2 虎牙房，2026-08-26 教训：曾混入 LoL 切片）
        return [p for p in files if ("huya" in p.name or "soop" in p.name) and "csboy" not in p.name]
    return files


def bp_slice_from(g_start, start_dt):
    """BP 切片起点：不早于比赛实际开赛（教训 2026-08-26：Spirit-DENDELE
    g1_bp 切片从开赛前 37 分钟开始，等待期 LCK/G2-Aurora 杂音混入）。"""
    frm = g_start - datetime.timedelta(minutes=15)
    if start_dt and frm < start_dt:
        return start_dt
    return frm


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
        teams_txt += (
            f"\n- {t}: 提及{v.get('mentions', 0)} 正向{v.get('pos', 0)}/负向{v.get('neg', 0)}"
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
    prompt = (
        f"你是电竞弹幕情报分析师。生成一场 LoL 比赛的局中弹幕情报 HTML 页（节点=G{gi}｜{glabel}{end_note}）。\n"
        f"比赛：{teams[0]} vs {teams[1]}（{date}，slug={slug_id}）正在进行第 {gi} 小局，赛制 BO{max_games}（本场共 {max_games} 局，页面对阵/赛制处必须写 BO{max_games}，禁止写错）。\n"
        f"页面标注「局中·非终局，结果待定」。\n"
        f"规则层统计（来自弹幕）：窗口 {meta.get('window_utc','')}，共 {meta.get('total',0)} 条，"
        f"{meta.get('active_users',0)} 人，{meta.get('density_per_min',0)} 条/分，样本状态 {meta.get('sample_status','-')}。\n"
        f"队伍提及：{teams_txt or '无'}\n"
        f"灰信号（观众质疑，非结论）：{gray_txt}\n"
        f"弹幕密度峰值：{dens_txt}\n"
        f"规则层情报文件：{intel_json}\n"
        f"要求（决策导向，2026-08-26 定稿）：\n"
        f"1) 第一屏必须是「核心情报速览」，且用标准容器："
        f"<div class=\"card speed\"> + <h2><span class=\"no\">0</span>核心情报速览</h2> + "
        f"进度/比分一行（标注「弹幕口径·官方待回填」）+ 关键信息 <li> 列表 3-5 条"
        f"（不加分类标签）+ 一句话决策落点；正文确实没有任何信息时才写「今日无关键信息」。\n"
        f"【关键情报价值呈现机制·最高（BLUF×Key Judgment×So-What，2026-08-26 固化）】"
        f"每条关键信息 = 信号（发生了什么，含方向与关键对象）＋「→」＋一句价值/含义"
        f"（意味着什么、为什么重要，≤35 字，含方向与置信标签：多源确认/单源待验证/弹幕口径·待官方）"
        f"＋溯源（→ 详 §N）。禁止：章节号/章节标题（如「3 BP 锚点与选人情报」"
        f"「10 预测验证回填明细」）、元数据碎片（如「灰信号留痕（入 gray_signals…）」）、"
        f"纯时间线（10:56→11:28→11:32）、表格头/维度词（位置/维度/验证状态）。"
        f"每条必须过「So-What 检验」：读者 5 秒内知道这条信息对判断意味着什么；\n"
        f"2) 页面必须按决策导向 12 段完整结构（2026-08-26 模板标准，缺一不可）："
        f"0 核心情报速览（card speed）→ 1 结果总览/状态核验 → 2 灰信号汇总（观众质疑·非结论）→ "
        f"3 BP 锚点与选人情报 → 4 盘口与市场讨论 → 5 方向性情报板（正锚×负锚×共识×灰信号条件预测）→ "
        f"6 情报含义与决策落点（LONG/SHORT）→ 7 本局复盘（证据层）→ 8 队伍/人员画像（带提及量）→ "
        f"9 联赛规律与版本 → 10 预测验证回填 → 11 数据与溯源（实际数据源/预期/缺口三栏）；"
        f"每段用 <h2><span class=\"no\">N</span>标题</h2> 编号，禁止合并或省略；\n"
        f"3) 输出 SAP/Apple 风格完整 HTML（内联CSS：浅底#f5f5f7、白圆角卡片、单一强调色#0071e3、"
        f"系统字体栈 -apple-system/PingFang SC、充足留白），内容紧凑、信息密度高，全文约 700-1000 字；\n"
        f"4) 韩/英弹幕信号层只给中文意译一句话，原文折叠在 <details>（格式「中文意译（原文摘录）」），"
        f"黑话保留双语（如 야필패=亚索必败）；每条约 1-2 条样本+计数，不堆原文；\n"
        f"5) 数据完整性三栏（实际数据源/预期数据源/缺口）必须保留；只依据给定统计与示例样本，"
        f"禁止编造具体弹幕内容、比分或事实；样本不足的板块写「样本不足」；\n"
        f"6) 【速览卡一致性·最高要求】速览卡关键信息必须与本页正文实际内容一致：正文有"
        f"锚点/盘口/共识/灰信号等信息，速览卡就必须列出具体内容（含方向与关键对象），"
        f"且每条必须带一句价值/含义（同第 1 条机制），禁止只列原始时间线或章节标题；"
        f"禁止写「今日无…/不足/待确认」；只有正文确实没有任何信息时才允许写「无」。"
        f"生成后系统会用一致性检查校验，不一致会被拦截修复。\n"
        f"7) 不输出「群体意见与归因/聚类」区块（2026-08-26 用户定稿：聚类方案回滚弃用）。\n"
        f"8) 信息密度要求（收敛不丢硬信息，2026-08-26 用户定稿）：必须包含——"
        f"人员画像表（带提及量/正负向）、本局阵容（英雄+选手映射）、BP 后战绩情报（选人窗口"
        f"选手×英雄胜率/战绩提及，无则写「无战绩情报提及」）、弹幕密度峰值时间线（分钟+条数+样本）、"
        f"跨源一致性提示（本场实际数据源与缺口）、比赛元数据（全称/league id/Polymarket slug/赛制 BO{max_games}）；"
        f"禁止为版面清爽删掉以上硬信息。\n"
        f"9) 直接输出 HTML（不要 markdown 代码块包裹），完整写完 </body></html>。\n"
        f""
    )
    body = json.dumps(
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
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
        html = r["choices"][0]["message"]["content"]
        html = re.sub(r"^```(?:html)?\s*|\s*```$", "", html.strip())
        # 2026-08-26 教训：DeepSeek 输出偶发不写 </body>/</html>（页面截断感），
        # 缺收尾会导致付费墙注入与发布审计失败——自动补全收尾标签。
        if "</body>" not in html.lower():
            html += "\n</body>\n</html>"
        elif "</html>" not in html.lower():
            html += "\n</html>"
        # 赛制标注（教训 2026-08-26：模型偶发写 BO3 或漏写赛制，实际 BO{max_games}）
        html = re.sub(r"BO\s*[0-9]", f"BO{max_games}", html, flags=re.I)
        if f"BO{max_games}" not in html:
            note = (
                f'<div style="font-size:12px;color:#6e6e73;margin:6px 0 2px">'
                f"赛制：BO{max_games}（本场共 {max_games} 局）</div>"
            )
            anchor = re.search(
                r'(<h2[^>]*><span class="no">1</span>结果总览[^<]*</h2>)',
                html,
            )
            if anchor:
                html = html[: anchor.end()] + note + html[anchor.end():]
        if not html.lower().startswith("<!doctype") and not html.lstrip().lower().startswith("<html"):
            html = f"<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"><title>{teams[0]} vs {teams[1]} · G{gi} {gphase}</title></head><body>{html}</body></html>"
        rep.write_text(html, encoding="utf-8")
        write_md_mirror(rep)  # HTML + MD 双格式
        return 0, f"fast ok {len(html)} bytes", ""
    except Exception as e:  # noqa: BLE001
        return 1, "", f"fast failed: {e}"


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
    for f in REPORTS.glob(f"intel_danmu_*{date}*.html"):
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
    if not any(v[2] for v in views):
        return REPORTS / f"match_{mid}.html"

    btns = "".join(
        (
            f'<button class="nbtn" data-src="{v[2]}"'
            + (' aria-pressed="true"' if i == 0 else "")
            + f'>{v[0]}<span class="s">{v[1]}</span></button>'
            if v[2]
            else f'<button class="nbtn" disabled style="opacity:.5;cursor:not-allowed" title="此节点暂未采集数据">{v[0]}<span class="s">{v[1]}</span></button>'
        )
        for i, v in enumerate(views)
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
<div class="picker">{btns}</div>
<iframe id="view" class="frame" title="时间点情报"></iframe>
<div class="note">时间轴自动产出：赛前 -> 每小局（BP 后 / 局中 / 局末）-> 赛后整场复盘；缺失节点自动出现，不 404。</div>
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

    all_files = sorted(DANMU.glob("*/*.jsonl"))
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # 及时性（2026-08-26）：定时器改 1 分钟后必须加锁，防止多实例重叠
    # 争抢 AI 额度导致每个节点更慢；已有实例运行时本轮直接跳过。
    lock_fd = open(STATE_DIR / "pipeline.lock", "w", encoding="utf-8")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[pipeline] another run in progress, skip")
        return

    for m in matches:
        mid = m.get("id") or "-"
        # 作废场次跳过（2026-08-26 固化，AGENTS 19：Aurora-G2 混源作废后
        # 流水线仍尝试生成节点，浪费 Codex 资源并阻塞其他比赛）
        if m.get("intel_voided"):
            print(f"[pipeline] {mid}: intel_voided, skip", flush=True)
            continue
        st_file = STATE_DIR / f"{mid}.json"
        if st_file.exists():
            print(f"[pipeline] {mid}: already done, skip")
            continue
        files = league_files(m, all_files)
        max_games = format_of(m)
        teams = m["teams"]
        date = (m.get("start_time") or "")[:10]
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
            pre_slice = SLICE_DIR / f"{slug_id}_pre.jsonl"
            pre_start = (start_dt - datetime.timedelta(minutes=90)).isoformat()
            n = slice_rows(pre_start, files, pre_slice)
            pre_intel = STATE_DIR / f"{slug_id}_pre_intel.json"
            subprocess.run(
                [str(PY), str(ROOT / "tools" / "danmu_intel.py"),
                 "--input", str(pre_slice), "--out", str(pre_intel)],
                timeout=180,
                check=False,
            )
            print(f"[pipeline] {mid}: pre slice {n} rows, generating pre intel...", flush=True)
            rc, so, se = run_codex_report(slug_id, teams, date, pre_intel, pre_slice, pre=True)
            pre_report = REPORTS / f"intel_danmu_{teams[0]}-{teams[1]}_{date}_pre.html"
            pre_state.write_text(
                json.dumps(
                    {
                        "match": mid,
                        "slice_rows": n,
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
        if "确认结束" not in out:
            # 未结束 -> 先按小局出节点（G{i} BP后 / 局中 / 局末）；
            # 小局市场不可用时退回 30 分钟局中快照（兜底）
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
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
                game_t = start_dt_parse
                for gi in range(1, max_games + 1):
                    # 教训 2026-08-25：now_utc 必须每局刷新——节点生成是串行的
                    # （单个 Codex 8-9 分钟），用启动时刻判断窗口会跳过后续节点
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    if gi > 1 and detect_match_end_gg(files, game_t - datetime.timedelta(minutes=10)):
                        print(f"[pipeline] {mid}: series-end GG detected, stop game nodes", flush=True)
                        break
                    g_start = game_t + datetime.timedelta(minutes=GAME_BP_GAP_MIN)
                    if now_utc >= g_start + datetime.timedelta(minutes=GAME_NODE_BP_MIN):
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
                    g_end_est = g_start + datetime.timedelta(minutes=GAME_EST_LEN_MIN)
                    if gg or now_utc >= g_end_est:
                        generate_game_node(
                            mid, teams, date, slug_id, gi, "end", g_start, files,
                            end_basis="gg" if gg else "est",
                            max_games=max_games,
                        )
                        game_t = anchor_next_game(mid, gi, now_utc)
                    else:
                        game_t = g_start
                continue

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
                        # 市场缺失（如 G5 条件市场）-> 按时间窗/弹幕兜底出节点
                        g_start_est = game_t + datetime.timedelta(minutes=GAME_BP_GAP_MIN)
                        if prev_ended:
                            tasks = []
                            if now_utc >= g_start_est + datetime.timedelta(minutes=GAME_NODE_BP_MIN):
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
                            g_end_est = g_start_est + datetime.timedelta(minutes=GAME_EST_LEN_MIN)
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
                    g_start = game_t + datetime.timedelta(minutes=GAME_BP_GAP_MIN)
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
                            max_games=max_games,
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
                            if now_utc >= g_start + datetime.timedelta(minutes=GAME_NODE_BP_MIN):
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
                continue

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
                continue

            def parse_utc(v: str):
                try:
                    return datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    return None

            start_dt = parse_utc(m.get("start_time", ""))
            end_dt = parse_utc(m.get("end_time", ""))
            if not start_dt or start_dt > now_utc or (end_dt and end_dt < now_utc):
                print(f"[pipeline] {mid}: not in live window, skip")
                continue

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
            continue

        # 整场终局门禁（教训 2026-08-26：G1 结束的弹幕信号曾把整场误判结束，
        # 生成假复盘并跳过后续节点）——BO 系列必须所有小局结构上已结算才终局。
        if max_games > 1:
            gs_now = read_game_status(re.sub(r"[^a-zA-Z0-9_-]", "_", mid))
            if gs_now is None:
                gs_now = {}
            all_closed = all(
                bool((gs_now.get(i) or {}).get("closed"))
                or (gs_now.get(i) or {}).get("winner") is not None
                for i in range(1, max_games + 1)
            )
            if not all_closed:
                print(
                    f"[pipeline] {mid}: 弹幕判结束但小局未全部结算，暂不终局，继续出节点",
                    flush=True,
                )
                continue

        slug_id = re.sub(r"[^a-zA-Z0-9_-]", "_", mid)
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


if __name__ == "__main__":
    main()
