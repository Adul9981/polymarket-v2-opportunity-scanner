#!/usr/bin/env python3
"""Build a closed-loop evidence HTML page for a finished danmaku-intel match.

Reads a match entry from docs/data/intel/matches.json plus the match's intel
report HTML, extracts audience predictions (hit/miss/pending), gray-signal
highlights and result info, and emits a SAP/Apple-style closed-loop page.

Usage:
  python3 tools/build_closed_loop.py \
      --report reports/intel_danmu_WE-LGD_2026-08-22.html \
      --match-id 2026-08-22_we_lgd \
      --out /private/tmp/danmu-intel-site/intel/closed_loop_WE-LGD_2026-08-22.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def plain_text(report_html: str) -> str:
    t = re.sub(r"<style.*?</style>", "", report_html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t)


def extract_predictions(text: str) -> list[dict]:
    rows: list[dict] = []
    seg = text
    m = re.search(r"预测验证(.*?)(?:八、|九、|十、|情报含义|$)", text)
    if m:
        seg = m.group(1)
    for m in re.finditer(
        r"[\"\u201c]([^\"\u201d]{2,60})[\"\u201d]([^命落待]{0,150}?)(命中|落空|待确认)",
        seg,
    ):
        pred, between, status = m.group(1), m.group(2).strip(), m.group(3)
        pred = re.split(r"[、，,——]", pred)[0].strip()
        between = re.split(r"(?:六、|七、|八、|九、|十、|情报含义)", between)[0].strip()[:90]
        if len(pred) < 2 or pred.startswith("（"):
            continue
        rows.append({"pred": pred, "detail": between, "status": status})
    # Pass 2: misses/pending noted in odds / notes sections as （落空）/（待确认）.
    for m in re.finditer(
        r"[\"\u201c]([^\"\u201d]{2,60})[\"\u201d]([^命落待]{0,120}?)[\(（](落空|待确认)[\)）]",
        text,
    ):
        pred = re.split(r"[、，,——]", m.group(1))[0].strip()
        if len(pred) < 2 or len(pred) > 40 or pred.startswith("（") or "：" in pred:
            continue
        rows.append({"pred": pred, "detail": m.group(2).strip()[:80], "status": m.group(3)})
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in rows:
        key = (r["pred"], r["status"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def load_match(matches_json: Path, match_id: str) -> dict | None:
    data = json.loads(matches_json.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("matches", [])
    for m in items:
        if m.get("id") == match_id:
            return m
    return None


def predictions_from_match(match: dict) -> list[dict]:
    status_map = {"hit": "命中", "miss": "落空", "pending": "待确认"}
    rows = []
    for p in match.get("predictions", []):
        detail = p.get("note") or f"（{p.get('time', '')}）{p.get('category', '')}"
        rows.append(
            {
                "pred": p.get("text", ""),
                "detail": detail[:90],
                "status": status_map.get(p.get("status", "pending"), "待确认"),
            }
        )
    return rows


def build(match: dict, predictions: list[dict], report_rel: str) -> str:
    teams = " vs ".join(match.get("teams", [])) or match_id
    league = match.get("league", "-")
    date = match.get("date", "-")
    result = match.get("result_inferred", "待确认")
    pending = match.get("pending", "-")
    hit = sum(1 for r in predictions if r["status"] == "命中")
    miss = sum(1 for r in predictions if r["status"] == "落空")
    pend = sum(1 for r in predictions if r["status"] == "待确认")
    total = len(predictions)
    rate = f"{hit}/{total}" if total else "-"
    slug = match.get("event_slug", "")
    market_row = (
        f'<div class="row"><span class="k">Polymarket 市场</span>'
        f'<span><a href="https://polymarket.com/event/{esc(slug)}" style="color:var(--accent)">{esc(slug)} →</a></span></div>'
        if slug
        else '<div class="row"><span class="k">Polymarket 市场</span><span>链接待补</span></div>'
    )

    pred_rows = ""
    for r in predictions:
        cls = "hit" if r["status"] == "命中" else "miss" if r["status"] == "落空" else "pend"
        pred_rows += (
            f'<tr><td>{esc(r["pred"])}</td><td>{esc(r["detail"])}</td>'
            f'<td class="{cls}">{esc(r["status"])}</td></tr>'
        )
    if not pred_rows:
        pred_rows = '<tr><td colspan="3">未解析到结构化预测（待人工复核 / 报告补齐）</td></tr>'

    gray_lines = "".join(
        f'<div class="row"><span class="k">信号</span><span>{esc(s[:180])}</span></div>'
        for s in match.get("key_signals", [])[:4]
    )
    if not gray_lines:
        gray_lines = '<div class="note">本场无灰信号记录（或待回填）</div>'

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>闭环佐证 · {esc(teams)}（{esc(date)}）</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3;--green:#1e8e3e;--red:#c92a2a}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:26px 16px 60px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:22px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-bottom:14px}}
.card h2{{font-size:15px;font-weight:700;margin-bottom:8px}}
.result{{background:#eaf7ef;border:1px solid #bfe6cd;border-radius:14px;padding:14px 18px;margin-bottom:14px}}
.score{{font-size:23px;font-weight:800}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{font-size:11.5px;color:var(--sub);text-align:left;padding:7px 9px;border-bottom:1px solid var(--line)}}
td{{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}}
.hit{{color:var(--green);font-weight:700}}.miss{{color:var(--red);font-weight:700}}.pend{{color:var(--amber, #b45309);font-weight:700}}
.row{{display:flex;justify-content:space-between;gap:12px;padding:6px 0;font-size:13px;border-bottom:1px solid var(--line)}}
.row .k{{color:var(--sub);flex:none}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}}
.stat{{background:#fafafa;border:1px solid var(--line);border-radius:12px;padding:11px 14px}}
.stat .num{{font-size:19px;font-weight:700;color:var(--accent)}}.stat .lbl{{font-size:11.5px;color:var(--sub)}}
.note{{color:var(--sub);font-size:12px;margin-top:8px}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>闭环佐证 · {esc(teams)}</h1>
<div class="sub">{esc(league)} · BO 系列 · {esc(date)} · 弹幕情报 → 比赛结果 → 验证回填（自动生成）</div>
<div class="result"><div class="score">{esc(result)}</div><div style="font-size:12.5px;color:var(--sub)">状态：{esc(pending or "待官方确认")}</div></div>
<div class="card"><h2>预测验证（弹幕 → 结果）</h2>
<table><thead><tr><th>局中弹幕预测</th><th>细节 / 结果</th><th>判定</th></tr></thead><tbody>{pred_rows}</tbody></table>
<div class="note">本轮解析命中 {hit} / 落空 {miss} / 待确认 {pend}（样本 {total} 条）</div></div>
<div class="card"><h2>灰信号与关键信号</h2>{gray_lines}
<div class="note">灰信号为观众风险标注，非结论；数据为聚合统计，不展示弹幕用户身份。</div></div>
<div class="card"><h2>本轮统计</h2><div class="stats">
<div class="stat"><div class="num">{rate}</div><div class="lbl">预测命中</div></div>
<div class="stat"><div class="num">{match.get("danmu_count", "-")}</div><div class="lbl">弹幕条数</div></div>
<div class="stat"><div class="num">{match.get("gray_signals_count", "-")}</div><div class="lbl">灰信号计数</div></div>
</div></div>
<div class="card"><h2>数据与溯源</h2>
{market_row}
<div class="row"><span class="k">完整情报页</span><span><a href="{esc(report_rel)}" style="color:var(--accent)">整场弹幕情报 →</a></span></div>
<div class="row"><span class="k">结构化库</span><span>docs/data/intel/matches.json（{esc(match.get("id", "-"))}）</span></div></div>
<footer>弹幕情报库 · 闭环佐证（自动流水线 v1） · {esc(date)}</footer>
</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="", help="match intel report HTML path (optional if JSON predictions exist)")
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--out", required=True, help="output closed-loop HTML path")
    ap.add_argument("--matches-json", default="docs/data/intel/matches.json")
    ap.add_argument("--report-rel", default="", help="relative link shown on page")
    args = ap.parse_args()

    match = load_match(Path(args.matches_json), args.match_id) or {}
    if match.get("predictions"):
        predictions = predictions_from_match(match)
    else:
        if not args.report:
            print("error: no structured predictions and no --report provided")
            raise SystemExit(1)
        text = plain_text(Path(args.report).read_text(encoding="utf-8"))
        predictions = extract_predictions(text)
    report_rel = args.report_rel or (Path(args.report).name if args.report else "")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(match, predictions, report_rel), encoding="utf-8")
    print(f"wrote {out}")
    print("note: generated from structured predictions (v2)." if match.get("predictions")
          else "note: generated from report HTML parsing (v1, review before publish).")
    for p in predictions:
        print(f"  [{p['status']}] {p['pred'][:40]} | {p['detail'][:50]}")


if __name__ == "__main__":
    main()
