#!/usr/bin/env python3
"""Live monitor for SOOP danmaku: refresh an SAP-style HTML page every N seconds.

Reads the JSONL being appended by tools/fetch_soop_danmu.py, extracts Korean
danmaku signals (teams / champions / BP / predictions / gray signals / density /
top users), and rewrites an auto-refreshing HTML page. Only reads the JSONL.

Usage:
  python3 tools/soop_live_monitor.py \
      --input docs/data/danmu/soop/2026-08-18_afchall_296450537_full.jsonl \
      --html reports/intel_soop_DNS-NS_live_2026-08-18.html \
      --title "DNS vs NS 实时情报（SOOP LCK CL）" --interval 300
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import time
from collections import Counter, defaultdict
from pathlib import Path


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


KEYWORDS = {
    "teams": {
        "NS": ["농심", "엔에스"],
        "DNS": ["든숲", "든슾", "디엔에스", "든섶"],
    },
    "champions": {
        "제이스(杰斯)": ["제이스"],
        "코그모(大嘴)": ["코그모"],
        "신드라(辛德拉)": ["신드라"],
        "라이즈(瑞兹)": ["라이즈"],
        "요릭(约里克)": ["요릭"],
        "올라프(奥拉夫)": ["올라프"],
        "클레드(克烈)": ["클레드"],
        "렐(蕾尔)": ["렐"],
        "카이사(卡莎)": ["카이사"],
        "나피리(娜菲丽)": ["나피리"],
        "세탭/세텝(Sett)": ["세탭", "세텝", "새텝"],
    },
    "bp": ["조합", "밴픽", "선픽", "픽", "카드", "라인전"],
    "prediction": ["3꽉", "삼꽉", "이길", "이긴", "이기겠", "이김", "승", "역전", "질", "패"],
    "situation": ["바론", "한타", "퍼블", "솔킬", "킬", "탑", "미드", "정글", "봇"],
    "gray": ["조작", "고의", "던짐", "배팅", "카지노", "뷰봇", "고의패"],
}


def match_count(text: str, words: list[str]) -> int:
    return sum(1 for w in words if w in text)


def extract(rows: list[dict]) -> dict:
    out: dict = {
        "total": len(rows),
        "users": len({r.get("user_id") for r in rows}),
        "time_min": min((r.get("unixtime") or 0 for r in rows), default=0),
        "time_max": max((r.get("unixtime") or 0 for r in rows), default=0),
        "per_min": Counter(),
        "bursts": [],
        "teams": {},
        "champions": {},
        "bp": [],
        "prediction": [],
        "situation": [],
        "gray": [],
        "top_users": [],
    }
    user_msgs: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        msg = (r.get("message") or "").strip()
        if not msg:
            continue
        t = int(r.get("unixtime") or 0)
        minute = time.strftime("%H:%M", time.localtime(t))
        out["per_min"][minute] += 1
        user_msgs[r.get("user_id", "?")].append((r.get("nickname", "?"), msg))

        for cat, name_map in (("teams", KEYWORDS["teams"]), ("champions", KEYWORDS["champions"])):
            for name, words in name_map.items():
                if match_count(msg, words):
                    d = out[cat].setdefault(name, {"mentions": 0, "samples": []})
                    d["mentions"] += 1
                    if len(d["samples"]) < 3:
                        d["samples"].append(msg)
        for cat, words in (
            ("bp", KEYWORDS["bp"]),
            ("prediction", KEYWORDS["prediction"]),
            ("situation", KEYWORDS["situation"]),
            ("gray", KEYWORDS["gray"]),
        ):
            if match_count(msg, words):
                out[cat].append(msg)

    out["bursts"] = [
        {"minute": m, "count": c}
        for m, c in sorted(out["per_min"].items(), key=lambda kv: -kv[1])[:3]
    ]
    for uid, msgs in sorted(user_msgs.items(), key=lambda kv: -len(kv[1]))[:7]:
        nick = msgs[0][0]
        out["top_users"].append(
            {"id": uid, "nick": nick, "count": len(msgs), "samples": [m for _, m in msgs[:2]]}
        )
    return out


def render_page(intel: dict, title: str, updated: str) -> str:
    t0 = time.strftime("%H:%M:%S", time.localtime(intel["time_min"])) if intel["time_min"] else "-"
    t1 = time.strftime("%H:%M:%S", time.localtime(intel["time_max"])) if intel["time_max"] else "-"
    peak = "、".join(f'{b["minute"]} {b["count"]} 条' for b in intel["bursts"]) or "暂无"

    teams_html = ""
    for name, d in sorted(intel["teams"].items(), key=lambda kv: -kv[1]["mentions"]):
        samples = "".join(f"<li>{esc(s)}</li>" for s in d["samples"])
        teams_html += (
            f'<div class="row"><b>{esc(name)}</b> 提及 {d["mentions"]}'
            f"<ul>{samples}</ul></div>"
        )
    if not teams_html:
        teams_html = '<p class="meta">样本不足</p>'

    champs_html = ""
    for name, d in sorted(intel["champions"].items(), key=lambda kv: -kv[1]["mentions"]):
        samples = "".join(f"<li>{esc(s)}</li>" for s in d["samples"])
        champs_html += (
            f'<div class="row"><b>{esc(name)}</b> 提及 {d["mentions"]}'
            f"<ul>{samples}</ul></div>"
        )
    if not champs_html:
        champs_html = '<p class="meta">样本不足</p>'

    bp_html = "".join(f"<li>{esc(s)}</li>" for s in intel["bp"][:6]) or '<p class="meta">暂无</p>'
    pred_html = "".join(f"<li>{esc(s)}</li>" for s in intel["prediction"][:6]) or '<p class="meta">暂无</p>'
    sit_html = "".join(f"<li>{esc(s)}</li>" for s in intel["situation"][:6]) or '<p class="meta">暂无</p>'

    gray_html = "".join(f"<li>{esc(s)}</li>" for s in intel["gray"][:6])
    gray_block = (
        f'<section class="card"><h2>灰信号（假赛/剧本/卡盘质疑）</h2><ul>{gray_html}</ul>'
        f'<p class="meta">观众质疑，非结论</p></section>'
        if gray_html
        else ""
    )

    users_html = ""
    for u in intel["top_users"]:
        samples = "".join(f"<li>{esc(s)}</li>" for s in u["samples"])
        users_html += (
            f'<div class="row"><b>{esc(u["nick"])}</b>（{esc(u["id"])}）发言 {u["count"]}'
            f"<ul>{samples}</ul></div>"
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="300">
<title>{esc(title)}</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.6;padding:28px 16px 60px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:25px;font-weight:700;margin-bottom:6px}}
.sub{{color:var(--sub);font-size:14px;margin-bottom:20px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.stat{{background:var(--card);border-radius:16px;padding:15px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.stat .num{{font-size:23px;font-weight:700;color:var(--accent)}}
.stat .lbl{{color:var(--sub);font-size:12px;margin-top:2px}}
.card{{background:var(--card);border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
h2{{font-size:18px;font-weight:700;margin-bottom:10px}}
h3{{font-size:14px;font-weight:600;margin-bottom:6px;color:var(--accent)}}
.row{{margin-bottom:12px}}
ul{{margin:4px 0 0 18px}}li{{font-size:13px;margin-bottom:2px}}
.warn{{background:#fff7f0;border-left:4px solid #ff9500;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:12px}}
.meta{{color:var(--sub);font-size:12px;margin-top:12px;line-height:1.7}}
@media(max-width:640px){{.stats{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div class="wrap">
<h1>{esc(title)}</h1>
<p class="sub">比赛：[CC] DNS vs NS | 2026 LCK CL ROUND 4 · G1 已结束（DNS 胜，弹幕推断）· 当前局进行中 · 页面每 5 分钟自动刷新</p>
<div class="stats">
<div class="stat"><div class="num">{intel["total"]}</div><div class="lbl">累计弹幕</div></div>
<div class="stat"><div class="num">{intel["users"]}</div><div class="lbl">活跃用户</div></div>
<div class="stat"><div class="num">{peak}</div><div class="lbl">密度峰值(条/分)</div></div>
<div class="stat"><div class="num">{t0}~{t1}</div><div class="lbl">数据窗口</div></div>
</div>

<div class="warn"><b>当前核心信号：</b>观众延续"NS 扳回一局"预期——开局即出现"NS 赢"喊话与"没人不知道要打满三局吧"（预测打满），DNS 杰斯上路被压使 BP 看衰部分兑现；反方观点认为 DNS 后期阵容价值更高（"后期价值 DNS 压胜，还得再看"）。</div>

<section class="card"><h2>队伍情报</h2>{teams_html}</section>
<section class="card"><h2>英雄/选手观察</h2>{champs_html}</section>
<section class="card"><h2>BP 与对线讨论</h2><ul>{bp_html}</ul></section>
<section class="card"><h2>预测信号</h2><ul>{pred_html}</ul></section>
<section class="card"><h2>局势/事件</h2><ul>{sit_html}</ul></section>
{gray_block}
<section class="card"><h2>高价值用户（本窗口）</h2>{users_html}</section>
<p class="meta">数据来源：SOOP LCK_CL 实时弹幕（tools/fetch_soop_danmu.py 持续采集）· 韩文弹幕直译要点 ·
完整 G1 历史待直播结束后 VOD 回捞补全 · 更新时间 {esc(updated)}</p>
</div></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="SOOP live danmaku monitor")
    ap.add_argument("--input", required=True, help="growing JSONL path")
    ap.add_argument("--html", required=True, help="output HTML path")
    ap.add_argument("--title", default="SOOP 弹幕实时监控")
    ap.add_argument("--interval", type=int, default=300)
    args = ap.parse_args()

    src = Path(args.input)
    dst = Path(args.html)
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_render = 0.0
    while True:
        try:
            rows = []
            if src.exists():
                for line in src.open(encoding="utf-8"):
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            intel = extract(rows)
            updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dst.write_text(render_page(intel, args.title, updated), encoding="utf-8")
            print(f"[soop-monitor] {len(rows)} lines -> {dst.name} @ {updated}", flush=True)
        except Exception as e:
            print(f"[soop-monitor] error: {e}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
