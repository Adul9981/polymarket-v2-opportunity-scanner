#!/usr/bin/env python3
"""Build C-type profile pages (teams/players/leagues) + gray verification stats.

Reads docs/data/intel/*.json and generates:
  reports/intel_profiles_index.html
  reports/intel_profile_team_<id>.html
  reports/intel_profile_player_<id>.html
  reports/intel_profile_league_<id>.html
  reports/intel_gray_verification_stats.html

Run: python3 tools/build_intel_profiles.py
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"
OUT = ROOT / "reports"


def load(name: str) -> dict:
    return json.loads((INTEL / name).read_text(encoding="utf-8"))


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.7;padding:28px 16px 60px}
.wrap{max-width:880px;margin:0 auto}
h1{font-size:25px;font-weight:700;margin-bottom:6px}
.sub{color:var(--sub);font-size:14px;margin-bottom:22px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px}
.stat{background:var(--card);border-radius:16px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.stat .num{font-size:22px;font-weight:700;color:var(--accent)}
.stat .lbl{color:var(--sub);font-size:12px;margin-top:2px}
.card{background:var(--card);border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h2{font-size:18px;font-weight:700;margin-bottom:10px}
h3{font-size:14px;font-weight:600;margin-bottom:6px;color:var(--accent)}
.block{margin-bottom:16px}
ul{margin:0 0 8px 18px}li{margin-bottom:4px;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--sub);font-weight:600}
.warn{background:#fff7f0;border-left:4px solid #ff9500;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:12px}
.ok{background:#f2f9f2;border-left:4px solid #34c759;padding:12px 14px;border-radius:8px;font-size:14px;margin-bottom:12px}
.note{color:var(--sub);font-size:12px;margin-top:20px;line-height:1.8}
a.item{display:block;text-decoration:none;color:var(--ink);padding:10px 12px;border:1px solid var(--line);border-radius:12px;margin-bottom:8px}
a.item:hover{border-color:var(--accent)}
a.item .t{font-weight:600;color:var(--accent);font-size:14px}
a.item .d{color:var(--sub);font-size:12px;margin-top:2px}
.tag{display:inline-block;background:#eef4ff;color:var(--accent);border-radius:20px;padding:1px 10px;font-size:12px;margin-right:6px}
.sev-high{color:#d0021b;font-weight:600}
.sev-mid{color:#d97706;font-weight:600}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}}
"""


def page(title: str, sub: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><div class=\"wrap\">\n"
        f"<h1>{esc(title)}</h1>\n<p class=\"sub\">{sub}</p>\n{body}\n"
        '<p class="note">生成：' + datetime.now().strftime("%Y-%m-%d %H:%M") +
        " · 情报库自动构建（tools/build_intel_profiles.py）· 数据来源 docs/data/intel/ · "
        "弹幕情报为观众集体智慧，灰信号只作风险标注非结论；官方确认后回填。</p>\n</div></body></html>\n"
    )


def stats(cells: list[tuple[str, str]]) -> str:
    return '<div class="stats">' + "".join(
        f'<div class="stat"><div class="num">{esc(v)}</div><div class="lbl">{esc(k)}</div></div>'
        for k, v in cells
    ) + "</div>"


def ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def matches_for(name: str, matches: list[dict]) -> list[dict]:
    def norm(s: str) -> str:
        return re.sub(r"[（(].*?[）)]", "", str(s)).strip().lower()

    base = norm(name)
    out = []
    for m in matches:
        ts = [norm(t) for t in m.get("teams", [])]
        if any(t and (t == base or base in t or t in base) for t in ts):
            out.append(m)
    return out


def gray_for(ref_id: str, ref_name: str, entities: list[dict]) -> list[dict]:
    out = []
    for e in entities:
        if e.get("id") == ref_id:
            out.append(e)
        elif ref_name and ref_name.lower() in str(e.get("name", "")).lower():
            out.append(e)
    return out


def build_team(t: dict, matches: list[dict], entities: list[dict], leagues: list[dict],
               players: list[dict], champions: list[dict], comps: list[dict]) -> str:
    name = t["name"]
    danmu = t.get("danmu", {})
    tags = danmu.get("tags", [])
    samples = danmu.get("samples", [])
    gh = t.get("gray_history", {})
    mlist = matches_for(name, matches)
    gle = [e for e in gray_for(t["id"], name, entities)]
    league_name = t.get("league", "未知")
    body = stats([
        ("提及量", danmu.get("mentions_total", "样本不足")),
        ("信任等级", t.get("trust", "未定")),
        ("灰信号条数", gh.get("total_signals", 0)),
        ("比赛样本", len(mlist)),
    ])
    league_risk = " / ".join(
        f"{l.get('gray_risk')}（{l.get('name')}）" for l in leagues
        if l.get("id") == str(league_name).lower().replace(" ", "_")
    )
    info_rows = [
        "联赛：" + str(league_name),
        "档案更新：" + str(t.get("updated", "?")),
        "身份/平台信息待官方核对",
    ]
    if league_risk:
        info_rows.append("联赛灰风险：" + league_risk)
    body += '<div class="card"><h2>一、组织与联赛</h2>' + ul(info_rows) + "</div>"
    body += '<div class="card"><h2>二、弹幕画像</h2>'
    if tags or samples:
        body += ul(["基调：" + esc(danmu.get("tone", "未记录"))] + ["标签：" + esc(x) for x in tags])
        if samples:
            body += '<div class="block"><h3>样本弹幕（聚合，脱敏）</h3>' + ul([f"“{esc(x)}”" for x in samples]) + "</div>"
    else:
        body += '<div class="ok">样本不足：暂无有效弹幕画像，后续比赛自动补充。</div>'
    body += "</div>"
    mk = t.get("market", {})
    body += '<div class="card"><h2>三、盘口定位</h2>'
    body += ul([f"{k}：{esc(v)}" for k, v in mk.items()]) if mk else '<div class="ok">样本不足：暂无盘口定位记录。</div>'
    body += "</div>"
    body += '<div class="card"><h2>四、灰信号历史</h2>'
    if gh:
        body += ul([
            "累计质疑：" + esc(gh.get("total_signals", 0)) + " 条 · 最近：" + esc(gh.get("last_seen", "?")) + " · 最高：" + esc(gh.get("max_severity", "?")),
            "状态：" + esc(gh.get("status", "观察")),
            "备注：" + esc(gh.get("note", "")),
        ])
        for e in gle:
            body += (
                '<div class="block"><h3>实体留痕：' + esc(e.get("name")) + "</h3>"
                + ul(["状态：" + esc(e.get("status")), "备注：" + esc(e.get("watch_notes", ""))]) + "</div>"
            )
    else:
        body += '<div class="ok">今日无灰信号留痕。</div>'
    body += "</div>"
    body += '<div class="card"><h2>五、近期比赛（' + str(len(mlist)) + ' 场）</h2>'
    if mlist:
        rows = ["<tr><th>日期</th><th>对阵</th><th>结果（口径）</th><th>要点</th></tr>"]
        for m in sorted(mlist, key=lambda x: str(x.get("date", "")), reverse=True):
            ks = m.get("key_signals", [])
        rows.append(
            "<tr><td>" + esc(m.get("date")) + "</td><td>" + esc(" vs ".join(m.get("teams", []))) + "</td>"
            "<td>" + esc(m.get("result_inferred", "待确认")) + "</td><td>" + esc("；".join(ks[:2])) + "</td></tr>"
        )
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">暂无已建档比赛。</div>'
    body += "</div>"
    # 近期走势（W/L 序列，从结果口径推导）
    seq = []
    for m in sorted(mlist, key=lambda x: str(x.get("date", ""))):
        r = str(m.get("result_inferred", ""))
        kw = [t for t in (t.get("name"), t["id"]) if t]
        won = any(k and k in r for k in kw) and any(s in r for s in ("2:0", "2:1", "3:0", "3:1", "3:2", "1:0", "13-10", "16-13", "16-14"))
        lost = any(k and k in r for k in kw) and any(s in r for s in ("0:2", "1:2", "0:3", "1:3", "2:3", "0:1", "10-13", "13-16", "14-16"))
        seq.append("胜" if won else ("负" if lost else "?"))
    if seq:
        chips = "".join(
            f'<span style="display:inline-block;background:{"#eaf6ec;color:#1d7a35" if s=="胜" else ("#fff0f0;color:#d0021b" if s=="负" else "#f2f2f7;color:#86868b")};border-radius:8px;padding:2px 8px;margin:2px;font-size:12px;font-weight:700">{s}</span>'
            for s in seq
        )
        body += f'<div class="card"><h2>五b、近期走势（{len(seq)} 场，倒序=最近在后）</h2><div>{chips}</div></div>'
    # 关联层：选手 / 英雄锚点 / 体系 / 比赛报告
    tid = t["id"]
    tname = str(t.get("name", ""))
    tplayers = [p for p in players if str(p.get("team", "")).split("(")[0].strip().lower().replace(" ", "_") == tid or tname.lower() in str(p.get("team", "")).lower()]
    body += '<div class="card"><h2>六、关联选手（' + str(len(tplayers)) + "）</h2>"
    body += ul([f'<a href="intel_profile_player_{esc(p["id"])}.html">{esc(p.get("name") or p["id"])}</a>（{esc(p.get("role","待确认"))}）' for p in tplayers]) if tplayers else '<div class="ok">暂无登记选手。</div>'
    body += "</div>"
    tchamps = [c for c in champions if any(a.get("team") == tid or a.get("player_id") in {x["id"] for x in tplayers} for a in c.get("anchors", [])) or any(tf.get("team_id") == tid for tf in c.get("team_fit", []))]
    body += '<div class="card"><h2>七、关联英雄锚点（' + str(len(tchamps)) + "）</h2>"
    body += ul([f'<a href="intel_profile_champion_{esc(c["id"])}.html">{esc(c.get("name"))}</a>（{esc((c.get("version_sign") or {}).get("label","待观察"))}）' for c in tchamps]) if tchamps else '<div class="ok">暂无关联英雄锚点。</div>'
    body += "</div>"
    tcomps = [co for co in comps if any(x.get("team_id") == tid for x in co.get("teams", []))]
    body += '<div class="card"><h2>八、惯用体系（' + str(len(tcomps)) + "）</h2>"
    body += ul([f'<a href="intel_profile_composition_{esc(co["id"])}.html">{esc(co.get("name"))}</a>' for co in tcomps]) if tcomps else '<div class="ok">暂无登记体系。</div>'
    body += "</div>"
    report_links = []
    for m in mlist:
        for r in (m.get("data") or {}).get("reports", []) or m.get("reports", []):
            rel = r.replace("reports/", "")
            report_links.append(f'<a href="{esc(rel)}">{esc(rel)}</a>')
    body += '<div class="card"><h2>九、比赛情报页（' + str(len(report_links)) + "）</h2>"
    body += ul(report_links) if report_links else '<div class="ok">暂无情报页。</div>'
    body += "</div>"
    long = ["画像标签：" + esc(x) for x in tags[:4]]
    if gh:
        long.append("灰信号留痕：" + esc(gh.get("status", "")) + "（共 " + esc(gh.get("total_signals", 0)) + " 条）")
    body += '<div class="card"><h2>六、长期沉淀（跨场复用）</h2>' + (ul(long) if long else '<div class="ok">样本不足：暂无跨场沉淀。</div>') + "</div>"
    return page(name + " · 队伍画像", esc(league_name) + " · 档案更新 " + esc(t.get("updated", "?")) + " · 情报库 C 型画像", body)


def build_player(p: dict, matches: list[dict], entities: list[dict], champions: list[dict], team_ids: set) -> str:
    name = p.get("name") or p["id"]
    nick = p.get("nicknames", [])
    gh = p.get("gray_history", {})
    gle = [e for e in gray_for(p["id"], str(name), entities)]
    body = stats([
        ("位置", p.get("role", "待确认")),
        ("队伍", p.get("team", "待确认")),
        ("灰信号", gh.get("total_signals", 0)),
        ("最近证据", p.get("evidence_ts", "—")),
    ])
    info = [
        "别称：" + (esc(" / ".join(nick)) if nick else "待补充"),
        "队伍：" + esc(p.get("team", "待确认")),
        "位置：" + esc(p.get("role", "待确认")),
        "证据时间：" + esc(p.get("evidence_ts", "—")),
    ]
    if p.get("pending"):
        info.append("待确认：" + esc(p.get("pending")))
    body += '<div class="card"><h2>一、基本信息</h2>' + ul(info) + "</div>"
    body += '<div class="card"><h2>二、英雄池与打法</h2>'
    focus = p.get("focus", [])
    body += ul(["常玩/焦点：" + (esc(" / ".join(focus)) if focus else "样本不足")] + (["节奏/风格：" + esc(p.get("tone", "未记录"))] if p.get("tone") else []))
    body += "</div>"
    body += '<div class="card"><h2>三、弹幕评价</h2>' + (ul([esc(p.get("notes", "样本不足"))]) if p.get("notes") else '<div class="ok">样本不足：暂无有效评价。</div>') + "</div>"
    body += '<div class="card"><h2>四、灰信号留痕</h2>'
    if gh:
        body += ul([
            "累计：" + esc(gh.get("total_signals", 0)) + " 条 · 最近：" + esc(gh.get("last_seen", "?")) + " · 最高：" + esc(gh.get("max_severity", "?")),
            "状态：" + esc(gh.get("status", "观察")),
            "备注：" + esc(gh.get("note", "")),
        ])
        for e in gle:
            body += (
                '<div class="block"><h3>实体留痕</h3>'
                + ul(["状态：" + esc(e.get("status")), "备注：" + esc(e.get("watch_notes", ""))]) + "</div>"
            )
    else:
        body += '<div class="ok">今日无灰信号留痕。</div>'
    body += "</div>"
    hits = []
    for m in matches:
        ks = " ".join(m.get("key_signals", [])) + " " + json.dumps(m.get("games", []), ensure_ascii=False)
        names = [str(n) for n in nick] + [str(name)]
        if any(n and n.lower() in ks.lower() for n in names):
            hits.append(m)
    body += '<div class="card"><h2>五、关联比赛（' + str(len(hits)) + ' 场）</h2>'
    if hits:
        rows = ["<tr><th>日期</th><th>对阵</th><th>结果（口径）</th></tr>"]
        for m in sorted(hits, key=lambda x: str(x.get("date", "")), reverse=True)[:8]:
            rows.append("<tr><td>" + esc(m.get("date")) + "</td><td>" + esc(" vs ".join(m.get("teams", []))) + "</td><td>" + esc(m.get("result_inferred", "待确认")) + "</td></tr>")
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">样本不足：暂无明确关联比赛。</div>'
    body += "</div>"
    pchamps = [c for c in champions if any(a.get("player_id") == p["id"] for a in c.get("anchors", []))]
    body += '<div class="card"><h2>六、关联英雄锚点（' + str(len(pchamps)) + "）</h2>"
    body += ul([f'<a href="intel_profile_champion_{esc(c["id"])}.html">{esc(c.get("name"))}</a>（{esc((c.get("version_sign") or {}).get("label","待观察"))}）' for c in pchamps]) if pchamps else '<div class="ok">暂无关联英雄锚点。</div>'
    body += "</div>"
    if p.get("team"):
        tid = str(p["team"]).split("(")[0].strip().lower().replace(" ", "_")
        if tid in team_ids:
            body += f'<div class="card"><h2>七、队伍画像</h2><ul><li><a href="intel_profile_team_{esc(tid)}.html">{esc(p.get("team"))}</a></li></ul></div>'
    return page(name + " · 选手画像", esc(p.get("team", "?")) + " · " + esc(p.get("role", "?")) + " · 情报库 C 型画像", body)


def build_league(l: dict, matches: list[dict]) -> str:
    body = stats([
        ("赛区", l.get("region", "待确认")),
        ("灰风险", l.get("gray_risk", "待观察")),
        ("平台数", len(l.get("platforms", []))),
        ("直播源", len(l.get("streamers", []))),
    ])
    body += f'<div class="card"><h2>一、赛事特征</h2>{ul([esc(l.get("notes","样本不足"))])}</div>'
    if l.get("key_samples"):
        body += f'<div class="card"><h2>二、关键样本</h2>{ul([esc(x) for x in l["key_samples"]])}</div>'
    rows = [
        "平台：" + esc(" / ".join(l.get("platforms", []))),
        "直播间：" + esc(" / ".join(l.get("streamers", []))),
    ]
    if l.get("keywords"):
        rows.append("词表方向：" + esc(" / ".join(l.get("keywords", []))))
    body += '<div class="card"><h2>三、平台与词表</h2>' + ul(rows) + "</div>"
    lid = l.get("id", "")
    lname = str(l.get("name", ""))
    lm = [m for m in matches if str(m.get("league", "")).lower().replace(" ", "_") == lid or lname.lower() in str(m.get("league", "")).lower()]
    body += '<div class="card"><h2>四、近期比赛（' + str(len(lm)) + " 场）</h2>"
    if lm:
        rows2 = ["<tr><th>日期</th><th>对阵</th><th>结果（口径）</th></tr>"]
        for m in sorted(lm, key=lambda x: str(x.get("date", "")), reverse=True)[:12]:
            rows2.append(f"<tr><td>{esc(m.get('date'))}</td><td>{esc(' vs '.join(m.get('teams', [])))}</td><td>{esc(m.get('result_inferred','待确认'))}</td></tr>")
        body += "<table>" + "".join(rows2) + "</table>"
    else:
        body += '<div class="ok">暂无已建档比赛。</div>'
    body += "</div>"
    return page(f"{l.get('name')} · 联赛画像", f"情报库 C 型画像 · 更新 {esc(l.get('updated_at','?'))}", body)


def build_champion(c: dict, comps: list[dict]) -> str:
    name = c.get("name") or c["id"]
    anchors = c.get("anchors", [])
    v = [a.get("verified") for a in anchors]
    hit = sum(1 for x in v if x == "应验")
    miss = sum(1 for x in v if x == "未应验")
    pend = sum(1 for x in v if x not in ("应验", "未应验"))
    body = stats([
        ("角色", " / ".join(c.get("roles", []))),
        ("锚点数", len(anchors)),
        ("应验", hit),
        ("未应验/待验证", f"{miss}/{pend}"),
    ])
    vs = c.get("version_sign", {})
    body += '<div class="card"><h2>一、版本符号（观众共识，非官方 meta）</h2>'
    body += ul([
        "符号：" + esc(vs.get("label", "待观察")),
        "窗口：" + esc(vs.get("period", "?")) + "（patch 见 patches.json）",
        "证据：" + esc(vs.get("evidence", "样本不足")),
        "样本量：" + esc(vs.get("samples", "?")) + "（<3 不登记为规律）",
    ])
    body += "</div>"
    body += '<div class="card"><h2>二、锚点明细（选手×英雄）</h2>'
    if anchors:
        rows = ["<tr><th>极性</th><th>选手/队伍</th><th>比赛</th><th>弹幕口径</th><th>验证</th></tr>"]
        for a in anchors:
            rows.append(
                f"<tr><td>{esc(a.get('polarity'))}</td><td>{esc(a.get('player_id') or a.get('team') or '待核实')}</td>"
                f"<td>{esc(a.get('match_id'))}</td><td>{esc(a.get('quote',''))}</td><td>{esc(a.get('verified','待验证'))}</td></tr>"
            )
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">样本不足：暂无锚点。</div>'
    body += "</div>"
    body += '<div class="card"><h2>三、搭配与克制</h2>'
    lines = []
    for p in c.get("pairing_needs", []):
        lines.append("搭配需求：" + esc(p.get("with")) + " —— " + esc(p.get("note", "")))
    for p in c.get("pairing", []):
        lines.append("组合：" + esc(p.get("with")) + " —— " + esc(p.get("note", "")))
    for k in c.get("counters", []):
        lines.append("克制关系：" + esc(k.get("vs")) + " —— " + esc(k.get("note", "")))
    body += ul(lines) if lines else '<div class="ok">样本不足：暂无搭配/克制记录。</div>'
    body += "</div>"
    body += '<div class="card"><h2>四、适用队伍</h2>'
    body += ul([f"{esc(x.get('team_id'))}：{esc(x.get('note',''))}" for x in c.get("team_fit", [])]) if c.get("team_fit") else '<div class="ok">样本不足。</div>'
    body += "</div>"
    rel = [co for co in comps if c["id"] in co.get("core", [])]
    body += '<div class="card"><h2>五、关联体系（' + str(len(rel)) + '）</h2>'
    body += ul([f"<a href='intel_profile_composition_{esc(co['id'])}.html'>{esc(co.get('name'))}</a>" for co in rel]) if rel else '<div class="ok">暂无关联体系。</div>'
    body += "</div>"
    return page(name + " · 英雄画像", "版本符号 + 锚点 + 搭配/克制 · 情报库 C 型画像 · LONG", body)


def build_champion_linked(c: dict, comps: list[dict], matches: list[dict], player_ids: set, team_ids: set) -> str:
    """英雄画像（带链接版）：锚点选手/队伍可点，相关比赛带情报页链接。"""
    name = c.get("name") or c["id"]
    anchors = c.get("anchors", [])
    v = [a.get("verified") for a in anchors]
    hit = sum(1 for x in v if x == "应验")
    miss = sum(1 for x in v if x == "未应验")
    pend = sum(1 for x in v if x not in ("应验", "未应验"))
    body = stats([
        ("角色", " / ".join(c.get("roles", []))),
        ("锚点数", len(anchors)),
        ("应验", hit),
        ("未应验/待验证", f"{miss}/{pend}"),
    ])
    vs = c.get("version_sign", {})
    body += '<div class="card"><h2>一、版本符号（观众共识，非官方 meta）</h2>' + ul([
        "符号：" + esc(vs.get("label", "待观察")),
        "窗口：" + esc(vs.get("period", "?")) + "（patch 见 patches.json）",
        "证据：" + esc(vs.get("evidence", "样本不足")),
        "样本量：" + esc(vs.get("samples", "?")) + "（<3 不登记为规律）",
    ]) + "</div>"
    body += '<div class="card"><h2>二、锚点明细（选手×英雄）</h2>'
    if anchors:
        rows = ["<tr><th>极性</th><th>选手/队伍</th><th>比赛</th><th>弹幕口径</th><th>验证</th></tr>"]
        for a in anchors:
            who = a.get("player_id") or a.get("team") or "待核实"
            if a.get("player_id") and a["player_id"] in player_ids:
                who = f'<a href="intel_profile_player_{esc(a["player_id"])}.html">{esc(a["player_id"])}</a>'
            elif a.get("team") and a["team"] in team_ids:
                who = f'<a href="intel_profile_team_{esc(a["team"])}.html">{esc(a["team"])}</a>'
            mlink = a.get("match_id", "")
            rows.append(
                f"<tr><td>{esc(a.get('polarity'))}</td><td>{who}</td><td>{esc(mlink)}</td>"
                f"<td>{esc(a.get('quote',''))}</td><td>{esc(a.get('verified','待验证'))}</td></tr>"
            )
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">样本不足：暂无锚点。</div>'
    body += "</div>"
    body += '<div class="card"><h2>三、搭配与克制</h2>'
    lines = []
    for p in c.get("pairing_needs", []):
        lines.append("搭配需求：" + esc(p.get("with")) + " —— " + esc(p.get("note", "")))
    for p in c.get("pairing", []):
        lines.append("组合：" + esc(p.get("with")) + " —— " + esc(p.get("note", "")))
    for k in c.get("counters", []):
        lines.append("克制关系：" + esc(k.get("vs")) + " —— " + esc(k.get("note", "")))
    body += ul(lines) if lines else '<div class="ok">样本不足：暂无搭配/克制记录。</div>'
    body += "</div>"
    body += '<div class="card"><h2>四、适用队伍</h2>'
    body += ul([f"{esc(x.get('team_id'))}：{esc(x.get('note',''))}" for x in c.get("team_fit", [])]) if c.get("team_fit") else '<div class="ok">样本不足。</div>'
    body += "</div>"
    rel = [co for co in comps if c["id"] in co.get("core", [])]
    body += '<div class="card"><h2>五、关联体系（' + str(len(rel)) + "）</h2>"
    body += ul([f'<a href="intel_profile_composition_{esc(co["id"])}.html">{esc(co.get("name"))}</a>' for co in rel]) if rel else '<div class="ok">暂无关联体系。</div>'
    body += "</div>"
    import re as _re
    mid_map = {}
    for m in matches:
        mid_map[m["id"]] = m
        mid_map.setdefault(_re.sub(r"(_g\d+)$", "", m["id"]), m)
    rel_matches = []
    for a in anchors:
        mid = _re.sub(r"(_g\d+)$", "", a.get("match_id", ""))
        if mid in mid_map:
            rel_matches.append(mid_map[mid])
    body += '<div class="card"><h2>六、相关比赛情报页（' + str(len(rel_matches)) + "）</h2>"
    links = []
    for m in rel_matches:
        reps = (m.get("data") or {}).get("reports", []) or m.get("reports", [])
        for r in reps:
            relr = str(r).replace("reports/", "")
            links.append(f'<a href="{esc(relr)}">{esc(m["id"])} · {esc(relr)}</a>')
    body += ul(links) if links else '<div class="ok">暂无关联比赛情报页。</div>'
    body += "</div>"
    return page(name + " · 英雄画像", "版本符号 + 锚点 + 搭配/克制 + 关联体系/比赛 · 情报库 C 型画像 · LONG", body)


def build_composition(co: dict, champs: list[dict]) -> str:
    name = co.get("name") or co["id"]
    teams = co.get("teams", [])
    wins = sum(t.get("wins", 0) for t in teams)
    losses = sum(t.get("losses", 0) for t in teams)
    samples = co.get("samples", [])
    body = stats([
        ("类型", " / ".join(co.get("type", []))),
        ("核心数", len(co.get("core", []))),
        ("样本", len(samples)),
        ("胜/负", f"{wins}/{losses}"),
    ])
    body += '<div class="card"><h2>一、体系定义</h2>' + ul([
        "核心：" + (esc(" / ".join(co.get("core", []))) if co.get("core") else "待补充（非固定英雄）"),
        "要求：" + esc(co.get("requires", "无")),
        "说明：" + esc(co.get("note", "样本不足")),
        "克制：" + esc(" / ".join(co.get("countered_by", []))) if co.get("countered_by") else "克制：待观察",
    ]) + "</div>"
    body += '<div class="card"><h2>二、适用队伍</h2>'
    if teams:
        rows = ["<tr><th>队伍</th><th>说明</th><th>胜</th><th>负</th></tr>"]
        for t in teams:
            rows.append(f"<tr><td>{esc(t.get('team_id'))}</td><td>{esc(t.get('note',''))}</td><td>{t.get('wins',0)}</td><td>{t.get('losses',0)}</td></tr>")
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">样本不足。</div>'
    body += "</div>"
    body += '<div class="card"><h2>三、样本验证（' + str(len(samples)) + '）</h2>'
    if samples:
        rows = ["<tr><th>比赛</th><th>验证</th></tr>"]
        for s in samples:
            rows.append(f"<tr><td>{esc(s.get('match_id'))}</td><td>{esc(s.get('verdict','待验证'))}</td></tr>")
        body += "<table>" + "".join(rows) + "</table>"
    else:
        body += '<div class="ok">样本不足：暂无验证样本。</div>'
    body += "</div>"
    rel = [c for c in champs if c["id"] in co.get("core", [])]
    body += '<div class="card"><h2>四、关联英雄（' + str(len(rel)) + '）</h2>'
    body += ul([f"<a href='intel_profile_champion_{esc(c['id'])}.html'>{esc(c.get('name'))}</a>" for c in rel]) if rel else '<div class="ok">无固定核心英雄（节奏/体系类）。</div>'
    body += "</div>"
    return page(name + " · 阵容/体系画像", "体系类型 + 克制 + 适用队伍 + 样本验证 · 情报库 C 型画像 · LONG", body)


def build_verification(records: list[dict]) -> str:
    total = sum(r.get("count", 0) for r in records)
    decided = [r for r in records if r.get("verification") in ("confirmed", "partial", "refuted")]
    confirmed = sum(1 for r in decided if r["verification"] == "confirmed")
    partial = sum(1 for r in decided if r["verification"] == "partial")
    refuted = sum(1 for r in decided if r["verification"] == "refuted")
    pending = len(records) - len(decided)
    rate = round((confirmed + partial) / len(decided) * 100) if decided else 0
    body = stats([
        ("记录数", len(records)),
        ("质疑弹幕", total),
        ("方向兑现", f"{confirmed + partial}/{len(decided)}"),
        ("兑现率", f"{rate}%（提示性）"),
    ])
    body += '<div class="warn"><b>方法论：</b>"方向兑现"指被质疑侧（演/送/不敢赢）输球或质疑事件发生；"未兑现"指被质疑侧反而赢球。样本量小（已判定 ' + str(len(decided)) + ' 条），兑现率只作方向观察，不作结论。灰信号纪律：观众质疑非结论。</div>'
    label = {"confirmed": '<span class="sev-high">兑现</span>', "partial": '<span class="sev-mid">弱兑现</span>', "refuted": "未兑现", "pending": "待确认"}
    rows = ["<tr><th>比赛</th><th>条数</th><th>严重度</th><th>质疑对象</th><th>验证</th><th>说明</th></tr>"]
    for r in sorted(records, key=lambda x: str(x.get("id", "")), reverse=True):
        v = r.get("verification", "pending")
        rows.append(
            f"<tr><td>{esc(r.get('match'))}</td><td>{esc(r.get('count'))}</td><td>{esc(r.get('severity'))}</td>"
            f"<td>{esc('；'.join(r.get('keywords', [])[:3]))}</td><td>{label.get(v, label['pending'])}</td>"
            f"<td>{esc(r.get('verification_note', r.get('notes',''))[:120])}</td></tr>"
        )
    body += '<div class="card"><h2>一、逐场验证明细</h2><table>' + "".join(rows) + "</table></div>"
    by_league = {}
    for r in records:
        v = r.get("verification", "pending")
        d = by_league.setdefault(r.get("league", "?"), {"n": 0, "c": 0, "r": 0, "p": 0})
        d["n"] += 1
        if v == "confirmed":
            d["c"] += 1
        elif v == "partial":
            d["c"] += 0.5
        elif v == "refuted":
            d["r"] += 1
        else:
            d["p"] += 1
    rows2 = ["<tr><th>联赛</th><th>记录数</th><th>兑现（含弱）</th><th>未兑现</th><th>待确认</th></tr>"]
    for lg, d in sorted(by_league.items()):
        rows2.append(f"<tr><td>{esc(lg)}</td><td>{d['n']}</td><td>{d['c']}</td><td>{d['r']}</td><td>{d['p']}</td></tr>")
    body += '<div class="card"><h2>二、按联赛</h2><table>' + "".join(rows2) + "</table></div>"
    body += '<div class="card"><h2>三、观察</h2><ul>'
    body += "<li>已判定 " + str(len(decided)) + " 条：兑现（含弱）" + str(confirmed + partial) + "、未兑现 " + str(refuted) + "、待确认 " + str(pending) + "。</li>"
    body += "<li>高预警记录中" + str(sum(1 for r in records if r.get("severity") == "高" and r.get("verification") in ("confirmed", "partial"))) + "条方向兑现（WE-EDG、BRO-BFX 等）；" + str(sum(1 for r in records if r.get("severity") == "高" and r.get("verification") == "refuted")) + "条未兑现（WBG-LNG、DK-HLE 反向）。</li>"
    body += "<li>跨场模式：'被疑队领先被翻/优势送'类质疑兑现率更高（BRO-BFX G1、T1-KT G3、TH-NAVI）；'排名博弈/演'类猜测多为未兑现（GEN-KT、TES-AL）。</li></ul></div>"
    body += '<div class="card"><h2>三、操作视角（决策层，2026-08-22 用户确认）</h2><ul>'
    body += "<li><b>模式 A（优势方被疑送 → 该队输，高价值）：</b>BRO-BFX G1、T1-KT G3、SK-TH G1/G2、TH-NAVI 连续兑现——操作候选：被质疑侧为热门/领先时，反向/对侧买入；结合水位（水位不动=市场已定价，评估剩余空间）。</li>"
    body += "<li><b>模式 B（排名博弈/演，多未兑现）：</b>GEN-KT、TES-AL、WE-AL 均未兑现——只作叙事记录，不作操作依据。</li>"
    body += "<li><b>模式 C（卡盘/收米/剧本终局）：</b>KC-GX、SK-TH G1、TT-JDG G3——盘口对照素材，需价格数据回填后才能验证。</li>"
    body += "<li><b>再犯升级加权：</b>SK（两局连续兑现）、TH（历史 248 条）、Monki（多次再犯但 08-21 未兑现）、BRO（三线留痕）——实体灰信号历史是操作加权项，再犯实体出现同类质疑时优先考虑。</li>"
    body += "<li>纪律：灰信号非结论；操作需兑现率 + 再犯状态 + 价格三维确认，单靠灰信号不下单。</li></ul></div>"
    return page("灰信号 · 质疑→兑现率统计", "情报库风险层 · 观众集体智慧 · 逐场验证回填", body)


def build_hub(teams, players, leagues, records, champions=None, compositions=None) -> str:
    champions = champions or []
    compositions = compositions or []
    body = '<div class="card"><h2>队伍画像（' + str(len(teams)) + "）</h2>"
    for t in sorted(teams, key=lambda x: x.get("updated", ""), reverse=True):
        gh = t.get("gray_history", {})
        body += f'<a class="item" href="intel_profile_team_{esc(t["id"])}.html"><span class="tag">{esc(t.get("league","?"))}</span><span class="t">{esc(t.get("name"))}</span><div class="d">提及 {esc(t.get("danmu",{}).get("mentions_total","不足"))} · 信任 {esc(t.get("trust","未定"))} · 灰信号 {esc(gh.get("total_signals",0))} · 更新 {esc(t.get("updated","?"))}</div></a>'
    body += "</div>"
    body += '<div class="card"><h2>选手画像（' + str(len(players)) + "）</h2>"
    for p in sorted(players, key=lambda x: x.get("evidence_ts", ""), reverse=True):
        gh = p.get("gray_history", {})
        body += f'<a class="item" href="intel_profile_player_{esc(p["id"])}.html"><span class="tag">{esc(p.get("team","?"))}</span><span class="t">{esc(p.get("name") or p["id"])}</span><div class="d">{esc(p.get("role","待确认"))} · 灰信号 {esc(gh.get("total_signals",0))} · 最近 {esc(p.get("evidence_ts","—"))}</div></a>'
    body += "</div>"
    body += '<div class="card"><h2>联赛画像（' + str(len(leagues)) + "）</h2>"
    for l in sorted(leagues, key=lambda x: x.get("id", "")):
        body += f'<a class="item" href="intel_profile_league_{esc(l["id"])}.html"><span class="tag">{esc(l.get("region","?"))}</span><span class="t">{esc(l.get("name"))}</span><div class="d">灰风险 {esc(l.get("gray_risk","待观察"))} · 直播源 {esc(" / ".join(l.get("streamers",[])))}</div></a>'
    body += "</div>"
    body += '<div class="card"><h2>英雄画像（' + str(len(champions)) + "）</h2>"
    for c in sorted(champions, key=lambda x: x.get("id", "")):
        vs = c.get("version_sign", {})
        body += f'<a class="item" href="intel_profile_champion_{esc(c["id"])}.html"><span class="tag">{esc(" / ".join(c.get("roles",[])))}</span><span class="t">{esc(c.get("name"))}</span><div class="d">符号 {esc(vs.get("label","待观察"))} · 锚点 {len(c.get("anchors",[]))} · 窗口 {esc(vs.get("period","?"))}</div></a>'
    body += "</div>"
    body += '<div class="card"><h2>阵容/体系画像（' + str(len(compositions)) + "）</h2>"
    for co in sorted(compositions, key=lambda x: x.get("id", "")):
        body += f'<a class="item" href="intel_profile_composition_{esc(co["id"])}.html"><span class="tag">{esc(" / ".join(co.get("type",[])[:1]))}</span><span class="t">{esc(co.get("name"))}</span><div class="d">样本 {len(co.get("samples",[]))} · 核心 {esc(" / ".join(co.get("core",[])) or "节奏型")}</div></a>'
    body += "</div>"
    body += f'<a class="item" href="intel_gray_verification_stats.html"><span class="tag">风险层</span><span class="t">灰信号 · 质疑→兑现率统计（{len(records)} 条记录）</span><div class="d">逐场验证回填 · 方向兑现率 · 按联赛统计</div></a>'
    return page("弹幕情报 · 画像库总览", "队伍 / 选手 / 联赛 / 英雄 / 体系长期画像 · C 型情报资产 · 每页可跨场复用", body)


def main() -> None:
    teams = load("teams.json")["teams"]
    players = load("players.json")["players"]
    leagues = load("leagues.json")["leagues"]
    matches = load("matches.json")["matches"]
    entities = load("gray_entities.json")["entities"]
    records = load("gray_signals.json")["records"]
    champions = load("champions.json")["champions"]
    compositions = load("compositions.json")["compositions"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "intel_profiles_index.html").write_text(build_hub(teams, players, leagues, records, champions, compositions), encoding="utf-8")
    (OUT / "intel_gray_verification_stats.html").write_text(build_verification(records), encoding="utf-8")
    player_ids = {p["id"] for p in players}
    team_ids = {t["id"] for t in teams}
    for t in teams:
        (OUT / f"intel_profile_team_{t['id']}.html").write_text(build_team(t, matches, entities, leagues, players, champions, compositions), encoding="utf-8")
    for p in players:
        (OUT / f"intel_profile_player_{p['id']}.html").write_text(build_player(p, matches, entities, champions, team_ids), encoding="utf-8")
    for l in leagues:
        (OUT / f"intel_profile_league_{l['id']}.html").write_text(build_league(l, matches), encoding="utf-8")
    for c in champions:
        (OUT / f"intel_profile_champion_{c['id']}.html").write_text(build_champion_linked(c, compositions, matches, player_ids, team_ids), encoding="utf-8")
    for co in compositions:
        (OUT / f"intel_profile_composition_{co['id']}.html").write_text(build_composition(co, champions), encoding="utf-8")
    print(f"generated: 1 hub + {len(teams)} teams + {len(players)} players + {len(leagues)} leagues + {len(champions)} champions + {len(compositions)} compositions + 1 verification")


if __name__ == "__main__":
    main()
