#!/usr/bin/env python3
"""Reformat legacy intel HTML pages into the decision-first 12-section template.

2026-08-26 standard (knowledge/INTEL_HTML_TEMPLATE.md 二.10/二.11):
  0 速览卡 / 1 结果 / 2 灰信号 / 3 BP锚点 / 4 盘口 / 5 方向板 /
  6 含义 / 7 逐局 / 8 画像 / 9 规律 / 10 预测验证 / 11 溯源

Guarantees:
  - ALL original h2-section content is preserved (unmatched sections go to 附录);
  - 速览卡 is auto-extracted from real content with "待人工确认" fallback,
    never invents content;
  - Output written to <name>_v2_<date>.html next to the source.

Usage:
  python3 tools/reformat_intel_template.py --html reports/intel_danmu_DNS-DRX_2026-08-24.html
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

CARD_CSS = """
  :root { --bg:#f5f5f7; --card:#fff; --ink:#1d1d1f; --sub:#6e6e73; --accent:#0b6bcb; --line:#e3e3e8; --good:#1a7f37; --bad:#c0392b; --warn:#b45309; --purple:#6d4fc4; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.62; padding:22px 12px 56px; }
  .wrap { max-width:920px; margin:0 auto; }
  .card { background:var(--card); border-radius:16px; padding:20px 22px; margin:14px 0; box-shadow:0 1px 4px rgba(0,0,0,.05); }
  h1 { font-size:22px; font-weight:700; }
  h2 { font-size:16px; font-weight:650; margin:10px 0 8px; display:flex; align-items:center; gap:7px; }
  h2 .no { flex:0 0 22px; height:22px; background:var(--accent); color:#fff; border-radius:7px; font-size:12px; display:inline-flex; align-items:center; justify-content:center; }
  .meta { color:var(--sub); font-size:12px; margin-top:6px; }
  .badge { display:inline-block; border-radius:999px; padding:2px 9px; font-size:11px; margin:2px 4px 2px 0; }
  .b-pend { background:#fdf0e6; color:var(--warn); }
  .b-ok { background:#e8f6ec; color:var(--good); }
  .b-risk { background:#fdeaea; color:var(--bad); }
  .b-anchor { background:#eaf2fb; color:var(--accent); }
  .b-odds { background:#e8f6ec; color:var(--good); }
  .b-con { background:#f3f0fa; color:var(--purple); }
  .speed { background:linear-gradient(180deg,#fbfcff,#f4f7fd); border:1px solid #dbe5f5; }
  .speed .top { display:flex; flex-wrap:wrap; gap:8px; align-items:center; border-bottom:1px solid var(--line); padding-bottom:10px; }
  .score-big { font-size:20px; font-weight:750; color:var(--accent); }
  .sig { display:flex; gap:10px; padding:9px 0; border-bottom:1px dashed var(--line); font-size:13px; }
  .sig:last-child { border-bottom:none; }
  .sig .tag { flex:0 0 52px; font-size:11px; font-weight:650; padding-top:2px; }
  .act { background:#f0faf3; border:1px solid #cfe8d8; border-radius:12px; padding:11px 14px; margin-top:10px; font-size:13.5px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
  th { text-align:left; color:var(--sub); font-weight:600; font-size:11px; padding:6px 7px; border-bottom:1px solid var(--line); }
  td { padding:6px 7px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  details { margin:6px 0; }
  summary { cursor:pointer; color:var(--accent); font-size:12.5px; }
  ul { padding-left:20px; margin:6px 0; } li { margin:4px 0; font-size:13.5px; }
  .warnbox { background:#fdf6ec; border-left:3px solid var(--warn); padding:8px 12px; border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  .footer { color:var(--sub); font-size:11.5px; text-align:center; margin-top:18px; }
"""


def text_only(html_frag: str, limit: int = 160) -> str:
    t = re.sub(r"<[^>]+>", " ", html_frag)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def split_sections(html: str) -> list[tuple[str, str]]:
    """Split on <h2> headings -> [(heading_text, inner_html)]."""
    parts = re.split(r"(<h2[^>]*>.*?</h2>)", html, flags=re.S)
    sections = []
    # 第一个 h2 之前的内容（页面头部卡片）保留为 "header" 段，不丢弃
    if parts and not re.match(r"<h2", parts[0]):
        head = parts.pop(0)
        if re.search(r"\w", re.sub(r"<[^>]+>", "", head)):
            sections.append(("header", head.strip()))
    cur_head = None
    cur_body = []
    for part in parts:
        if re.match(r"<h2", part):
            if cur_head is not None:
                sections.append((cur_head, "".join(cur_body).strip()))
            cur_head = re.sub(r"<[^>]+>", "", part).strip()
            cur_body = []
        else:
            cur_body.append(part)
    if cur_head is not None:
        sections.append((cur_head, "".join(cur_body).strip()))
    return sections


def map_section(heading: str) -> str | None:
    h = heading
    if h == "header":
        return "meta"
    if any(k in h for k in ["比赛信息", "对阵"]):
        return "meta"
    if any(k in h for k in ["结果总览", "当前进度", "状态核验", "最新更新"]):
        return "s1"
    if "灰信号" in h:
        return "s2"
    if any(k in h for k in ["BP", "锚点", "选人", "英雄讨论", "阵容与"]):
        return "s3"
    if any(k in h for k in ["盘口", "市场讨论", "市场"]):
        return "s4"
    if any(k in h for k in ["方向性", "方向板"]):
        return "s5"
    if any(k in h for k in ["情报含义", "后续观察", "LONG", "长期沉淀"]):
        return "s6"
    if any(k in h for k in ["逐局复盘", "逐图复盘", "逐图"]):
        return "s7"
    if "队伍画像" in h:
        return "s8a"
    if "人员画像" in h:
        return "s8b"
    if any(k in h for k in ["联赛规律", "版本"]):
        return "s9"
    if any(k in h for k in ["预测验证", "可验证悬念", "观众预测"]):
        return "s10"
    if any(k in h for k in ["数据与溯源", "溯源"]):
        return "s11"
    if any(k in h for k in ["弹幕规模", "密度", "时间线"]):
        return "s1density"
    if any(k in h for k in ["情绪", "组织背景", "盘口情绪"]):
        return "s8c"
    return None


def extract_score(s1_body: str) -> str:
    t = text_only(s1_body, 400)
    m = re.search(r"(\d\s*[:：]\s*\d)", t)
    return m.group(1) if m else "待人工确认"


def extract_gray(s2_body: str) -> str:
    t = text_only(s2_body, 500)
    m = re.search(r"(.{0,50}条.{0,60}指向.{0,60})", t)
    return (m.group(1).strip() + "…") if m else "今日无信号/待确认"


def extract_anchor(s3_body: str) -> str:
    t = text_only(s3_body, 500)
    m = re.search(r"(.{0,60}(?:应验|负锚|正锚).{0,40})", t)
    return (m.group(1).strip() + "…") if m else "今日无锚点/待确认"


def extract_odds(s4_body: str) -> str:
    t = re.sub(r"^(?:[0-9零一二三四五六七八九十]+[、. ]*)?[^：:。]{2,24}[：:]", "", text_only(s4_body, 500))
    m = re.search(r"(.{0,60}(?:c|张|让分|盘口|赔率|结算).{0,40})", t)
    return (m.group(1).strip() + "…") if m else "样本不足/待确认"


def extract_consensus(s5_body: str, s10_body: str) -> str:
    t = text_only((s5_body or "") + " " + (s10_body or ""), 500)
    m = re.search(r"(.{0,50}(?:命中|共识|看好|预测).{0,40})", t)
    return (m.group(1).strip() + "…") if m else "共识不足/待确认"


def extract_action(s6_body: str) -> str:
    t = text_only(s6_body, 700)
    matches = re.findall(r"(?:LONG|SHORT|长期|短期)[：:]?\s*([^。]{5,90})", t)
    if matches:
        # 标题里的 LONG/SHORT 出现在最前，正文内容在最后
        return ("LONG/SHORT：" + matches[-1].strip() + "…")
    return "待人工确认"


def build_speed(
    score: str, gray: str, anchor: str, odds: str, consensus: str, action: str
) -> str:
    return f"""<div class="card speed">
  <h2><span class="no">0</span>核心情报速览</h2>
  <div class="top">
    <span class="score-big">{score}</span>
    <span class="badge b-pend">弹幕口径 · 官方待回填</span>
    <span class="badge b-risk">灰信号见 §2</span>
    <span class="badge b-anchor">锚点见 §3</span>
    <span class="badge b-odds">盘口见 §4</span>
  </div>
  <div style="margin-top:8px">
    <div class="sig"><span class="tag" style="color:var(--bad)">风险</span><span>{gray} <span class="meta">→ 详 §2</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--accent)">锚点</span><span>{anchor} <span class="meta">→ 详 §3</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--good)">盘口</span><span>{odds} <span class="meta">→ 详 §4</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--purple)">共识</span><span>{consensus} <span class="meta">→ 详 §5/§10</span></span></div>
  </div>
  <div class="act"><b>决策落点：</b>{action}</div>
</div>"""


def section_card(no: str, title: str, body: str) -> str:
    return f"""<div class="card">
  <h2><span class="no">{no}</span>{title}</h2>
  {body}
</div>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, help="source intel HTML")
    args = ap.parse_args()

    src = Path(args.html)
    html = src.read_text(encoding="utf-8")
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    title = title_m.group(1).strip() if title_m else src.stem

    sections = split_sections(html)
    buckets: dict[str, list[tuple[str, str]]] = {}
    appendix: list[tuple[str, str]] = []
    for heading, body in sections:
        key = map_section(heading)
        if key:
            buckets.setdefault(key, []).append((heading, body))
        elif body.strip():
            appendix.append((heading, body))

    def join(key: str) -> str:
        items = buckets.get(key, [])
        if not items:
            return ""
        return "".join(
            f'<h3 style="font-size:13.5px;color:var(--sub);margin:8px 0 4px">{h}</h3>{b}'
            for h, b in items
        )

    score = extract_score(join("s1"))
    gray = extract_gray(join("s2"))
    anchor = extract_anchor(join("s3"))
    odds = extract_odds(join("s4"))
    consensus = extract_consensus(join("s5"), join("s10"))
    action = extract_action(join("s6"))

    parts = [
        f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}（v2 决策导向版）</title>
<style>{CARD_CSS}</style>
</head>
<body>
<div class="wrap">""",
        build_speed(score, gray, anchor, odds, consensus, action),
        section_card("1", "比赛信息与结果总览 / 状态核验", join("meta") + join("s1") + join("s1density")),
        section_card("2", "灰信号汇总（风险 · 观众质疑非结论）", join("s2")),
        section_card("3", "BP 锚点与选人情报", join("s3")),
        section_card("4", "盘口与市场讨论", join("s4")),
        section_card("5", "方向性情报板（锚点×共识×灰信号）", join("s5") or '<p class="meta">今日无方向板章节</p>'),
        section_card("6", "情报含义与决策落点（LONG/SHORT）", join("s6")),
        section_card("7", "逐局复盘（证据层）", join("s7")),
        section_card("8", "队伍 / 人员画像（证据层）", join("s8a") + join("s8b") + join("s8c")),
        section_card("9", "联赛规律与版本（沉淀层）", join("s9")),
        section_card("10", "预测验证回填明细（沉淀层）", join("s10")),
        section_card("11", "数据与溯源", join("s11")),
    ]
    if appendix:
        parts.append(
            section_card("附", "附录（原始章节未归类，内容完整保留）", join_body_appendix(appendix))
        )
    parts.append(
        '<div class="footer">v2 决策导向重排 · 弹幕口径 · 灰信号仅为观众质疑非结论 · 由 tools/reformat_intel_template.py 生成</div>\n</div>\n</body>\n</html>'
    )

    out = src.with_name(src.stem + "_v2" + src.suffix)
    out.write_text("\n".join(parts), encoding="utf-8")
    print("written:", out)
    return 0


def join_body_appendix(appendix: list[tuple[str, str]]) -> str:
    return "".join(f"<h3>{h}</h3>{b}" for h, b in appendix)


if __name__ == "__main__":
    raise SystemExit(main())
