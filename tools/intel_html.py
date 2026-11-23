#!/usr/bin/env python3
"""Shared SAP/Apple-style HTML helpers for intel pages.

CSS + card/escaping helpers, extracted so the node-page template renderer and
rule-layer reports share one visual spec instead of duplicating inline CSS per
tool (2026-10-18: template-based node generation).
"""

from __future__ import annotations

import html

# 站点壳同族（--accent:#0071e3 / --sub:#6e6e73 / --line:#e5e5ea），
# 与 knowledge/INTEL_HTML_TEMPLATE.md 的强调色 #0071e3 规范一致。
CSS = """
  :root { --bg:#f5f5f7; --card:#fff; --ink:#1d1d1f; --sub:#6e6e73; --accent:#0071e3; --line:#e5e5ea; --good:#1a7f37; --bad:#c0392b; --warn:#b45309; --purple:#6d4fc4; }
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
  ul { padding-left:20px; margin:6px 0; } li { margin:4px 0; font-size:13.5px; }
  .warnbox { background:#fdf6ec; border-left:3px solid var(--warn); padding:8px 12px; border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  .badbox { background:#fdf1f0; border-left:3px solid var(--bad); padding:8px 12px; border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  .srcbox { background:#f4f6fb; border:1px solid #dde3f0; border-radius:10px; padding:9px 12px; margin:8px 0; font-size:12px; color:var(--ink); }
  .note { color:var(--sub); font-size:12px; margin-top:8px; }
  .footer { color:var(--sub); font-size:11.5px; text-align:center; margin-top:18px; }
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def card(no: str, title: str, body: str, dom_id: str = "") -> str:
    """一张编号卡片。no=编号，title=段标题，body=已拼好的 HTML 内容。

    dom_id：可选 DOM id（如比赛局势卡 #situation-card），供前端实时轮询就地替换定位。
    """
    id_attr = f' id="{esc(dom_id)}"' if dom_id else ""
    return f'<div class="card"{id_attr}><h2><span class="no">{esc(no)}</span>{esc(title)}</h2>{body}</div>'


def sig(tag: str, color: str, text: str) -> str:
    """速览卡一条关键信息（带类型标签）。text 会转义。"""
    return f'<div class="sig"><span class="tag" style="color:{color}">{esc(tag)}</span><span>{esc(text)}</span></div>'


def src_box(actual: str, expect: str, gap: str) -> str:
    """数据源完整性三栏。"""
    return (
        '<div class="srcbox"><b>数据源完整性：</b>实际数据源 = ' + esc(actual)
        + '；预期数据源 = ' + esc(expect) + '；缺口 = ' + esc(gap) + '</div>'
    )


def speed_block(score: str, badges: list[tuple[str, str]], sigs_html: str, act: str) -> str:
    """速览卡主体：比分/进度 + 徽章 + 关键信息列表 + 决策落点。

    sigs_html 是已拼好的 <div class="sig"> 片段（不再转义）；其余均转义。
    """
    b = "".join(f'<span class="badge {cls}">{esc(txt)}</span>' for cls, txt in badges)
    return (
        f'<div class="top"><span class="score-big">{esc(score)}</span>{b}</div>'
        f'<div style="margin-top:8px">{sigs_html}</div>'
        f'<div class="act"><b>决策落点：</b>{esc(act)}</div>'
    )


def page(title: str, sub: str, sections: list[tuple[str, str, str]], footer: str, extra_html: str = "") -> str:
    """整页骨架：编号卡片列表 + 页脚（2026-10-24 起不再渲染速览卡，页面只保留选定栏）。

    sections 每项为 (编号, 标题, 正文)，可追加第 4 元素 dom_id（给该卡加 id）。
    extra_html：可选，注入 </body> 前的额外片段（如实时轮询 <script>）。
    """
    cards = "".join(
        card(it[0], it[1], it[2], dom_id=it[3] if len(it) > 3 else "")
        for it in sections
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

{cards}

<div class="footer">{footer}</div>
</div>
{extra_html}
</body>
</html>"""
