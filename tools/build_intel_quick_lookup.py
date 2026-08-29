#!/usr/bin/env python3
"""生成情报速查台（静态 HTML，浏览器内搜索队伍/英雄/选手/昵称/比赛）。

用法：python3 tools/build_intel_quick_lookup.py
输出：reports/intel_quick_lookup.html（数据内嵌，无需服务器）
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"
OUT = ROOT / "reports" / "intel_quick_lookup.html"
TZ = timezone(timedelta(hours=8))


def load(name: str) -> dict:
    return json.loads((INTEL / name).read_text(encoding="utf-8"))


def build_dataset() -> dict:
    teams = load("teams.json")["teams"]
    champs = load("champions.json")["champions"]
    comps = load("compositions.json")["compositions"]
    players = load("players.json")["players"]
    aliases = load("aliases.json")["aliases"]
    matches = load("matches.json")["matches"]
    sched = json.loads((ROOT / "docs" / "data" / "danmu" / "schedule.json").read_text(encoding="utf-8"))["matches"]

    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    recent = sorted(matches, key=lambda m: str(m.get("date", "")), reverse=True)[:15]

    def gray_sum(t: dict) -> str:
        gh = t.get("gray_history", {})
        return f"灰 {gh.get('total_signals', 0)} 条 · {gh.get('status', '观察')}" if gh else "灰信号 0"

    return {
        "generated": now.strftime("%Y-%m-%d %H:%M"),
        "today": today,
        "today_matches": [
            {"id": m.get("match_id"), "date": m.get("date"), "time": m.get("start_local"),
             "teams": m.get("teams", []), "status": m.get("status"), "result": m.get("result", "")}
            for m in sched if (m.get("date") or "").replace("-", "") >= "2026-08-24".replace("-", "") or m.get("date") == today
        ],
        "teams": [
            {"id": t.get("id"), "name": t.get("name"), "league": t.get("league"), "tone": (t.get("danmu") or {}).get("tone"),
             "tags": (t.get("danmu") or {}).get("tags", [])[:3], "gray": gray_sum(t), "updated": t.get("updated")}
            for t in teams
        ],
        "champions": [
            {"id": c.get("id"), "name": c.get("name"), "roles": c.get("roles", []),
             "version_sign": (c.get("version_sign") or {}).get("label"), "period": (c.get("version_sign") or {}).get("period"),
             "anchors": [f"{a.get('polarity')}:{a.get('player_id') or a.get('team') or '?'}@{a.get('match_id')}→{a.get('verified')}" for a in c.get("anchors", [])][:4],
             "counters": [k.get("vs") for k in c.get("counters", [])]}
            for c in champs
        ],
        "compositions": [
            {"id": co.get("id"), "name": co.get("name"), "type": co.get("type", []), "core": co.get("core", []),
             "note": co.get("note", ""), "samples": len(co.get("samples", []))}
            for co in comps
        ],
        "players": [
            {"id": p.get("id"), "name": p.get("name") or p.get("id"), "team": p.get("team"), "role": p.get("role"),
             "notes": (p.get("notes") or "")[:120]}
            for p in players
        ],
        "aliases": [
            {"alias": a.get("alias"), "official": a.get("official") or "待核实", "game": a.get("game"),
             "confidence": a.get("confidence")}
            for a in aliases
        ],
        "recent_matches": [
            {"id": m.get("id"), "date": m.get("date"), "teams": m.get("teams", []),
             "result": (m.get("result_inferred") or "")[:80], "signals": (m.get("key_signals") or [])[:2]}
            for m in recent
        ],
    }


CSS = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.6;padding:24px 16px 60px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:24px;font-weight:700;margin-bottom:4px}
.sub{color:var(--sub);font-size:13px;margin-bottom:16px}
.search{width:100%;padding:12px 16px;font-size:15px;border:1px solid var(--line);border-radius:14px;outline:none;background:var(--card);box-shadow:0 1px 2px rgba(0,0,0,.04)}
.search:focus{border-color:var(--accent)}
.tabs{margin:12px 0;display:flex;gap:8px;flex-wrap:wrap}
.tab{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 14px;font-size:13px;cursor:pointer;color:var(--sub)}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.card{background:var(--card);border-radius:14px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.card h3{font-size:15px;font-weight:700;margin-bottom:4px;color:var(--accent)}
.meta{color:var(--sub);font-size:12px;margin-bottom:6px}
.tag{display:inline-block;background:#eef4ff;color:var(--accent);border-radius:999px;padding:1px 9px;font-size:11px;margin:2px 4px 2px 0}
.empty{color:var(--sub);padding:20px;text-align:center}
.note{color:var(--sub);font-size:12px;margin-top:18px;line-height:1.8}
@media(max-width:640px){.tabs{overflow-x:auto}}
"""


def render(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    today_cards = "".join(
        f'<div class="card"><h3>{html.escape(" vs ".join(m["teams"]))}</h3>'
        f'<div class="meta">{html.escape(m["date"])} {html.escape(m.get("time") or "")} · {html.escape(m["status"])}'
        f'{(" · " + html.escape(m["result"])) if m.get("result") else ""}</div></div>'
        for m in data["today_matches"]
    ) or '<div class="empty">今日暂无已登记比赛（开赛后自动登记）</div>'
    shell_ids = {f"match_{m['id']}.html" for m in data["recent_matches"]} if False else set()
    import os as _os
    shells = {m["id"] for m in data["recent_matches"] if _os.path.exists(ROOT / "reports" / f"match_{m['id']}.html")}
    shell_js = json.dumps(list(shells), ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>弹幕情报速查台</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>弹幕情报速查台</h1>
<p class="sub">输入队伍 / 英雄 / 选手 / 昵称 / 比赛关键词，即时出情报 · 数据更新至 {html.escape(data['generated'])}</p>
<input id="q" class="search" placeholder="例：KC / 杰斯 / 绿龙 / 蛇女 / 2026-08-24_kc_shft" autofocus>
<div class="tabs" id="tabs">
<span class="tab on" data-t="all">全部</span><span class="tab" data-t="team">队伍</span>
<span class="tab" data-t="champion">英雄</span><span class="tab" data-t="composition">体系</span>
<span class="tab" data-t="player">选手</span><span class="tab" data-t="alias">昵称</span>
<span class="tab" data-t="match">近期比赛</span>
</div>
<div class="card"><h3>今日比赛</h3><div class="meta">最近 24 小时窗口</div>{today_cards}</div>
<div id="results"></div>
<p class="note">速查台为静态页（内嵌 docs/data/intel/ 数据快照），重新生成：python3 tools/build_intel_quick_lookup.py。
灰信号纪律：观众质疑非结论；未核实实体（如 啪哒克/少爷）标注待核实，不猜名。详情见各画像页。</p>
</div>
<script>
const D = {payload};
const cards = {{}};
function esc(s){{return String(s==null?'':s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));}}
function teamCard(t){{return `<div class="card"><h3>${{esc(t.name)}}</h3><div class="meta">队伍 · ${{esc(t.league)}} · ${{esc(t.gray)}} · 更新 ${{esc(t.updated||'?')}}</div>${{(t.tags||[]).map(x=>`<span class="tag">${{esc(x)}}</span>`).join('')}}<div>${{esc(t.tone||'')}}</div></div>`;}}
function champCard(c){{return `<div class="card"><h3>${{esc(c.name)}}</h3><div class="meta">英雄 · ${{esc(c.roles.join('/'))}} · ${{esc(c.period||'?')}}</div><span class="tag">${{esc(c.version_sign||'待观察')}}</span>${{(c.counters||[]).map(x=>`<span class="tag">克制:${{esc(x)}}</span>`).join('')}}<div>${{(c.anchors||[]).map(a=>`<div>· ${{esc(a)}}</div>`).join('')}}</div></div>`;}}
function compCard(c){{return `<div class="card"><h3>${{esc(c.name)}}</h3><div class="meta">体系 · ${{esc(c.type.join('/'))}} · 样本 ${{c.samples}}</div><span class="tag">核心:${{esc(c.core.join('/')||'节奏型')}}</span><div>${{esc(c.note||'')}}</div></div>`;}}
function playerCard(p){{return `<div class="card"><h3>${{esc(p.name)}}</h3><div class="meta">选手 · ${{esc(p.team||'?')}} · ${{esc(p.role||'待确认')}}</div><div>${{esc(p.notes||'样本不足')}}</div></div>`;}}
function aliasCard(a){{return `<div class="card"><h3>${{esc(a.alias)}}</h3><div class="meta">昵称 → ${{esc(a.official)}} · ${{esc(a.game)}} · ${{esc(a.confidence)}}</div></div>`;}}
function matchCard(m){{return `<div class="card"><h3>${{esc(m.teams.join(' vs '))}}</h3><div class="meta">${{esc(m.date)}} · ${{esc(m.id)}}</div><div>${{esc(m.result)}}</div>${{(m.signals||[]).map(s=>`<div>· ${{esc(s.slice(0,60))}}</div>`).join('')}}</div>`;}}
cards.team=D.teams.map(teamCard); cards.champion=D.champions.map(champCard);
cards.composition=D.compositions.map(compCard); cards.player=D.players.map(playerCard);
cards.alias=D.aliases.map(aliasCard); cards.match=D.recent_matches.map(matchCard);
const SHELLS = {shell_js};
cards.match = D.recent_matches.map(m=>`<div class="card"><h3>${{esc(m.teams.join(' vs '))}}</h3><div class="meta">${{esc(m.date)}} · ${{esc(m.id)}}</div><div>${{esc(m.result)}}</div>${{(m.signals||[]).map(s=>`<div>· ${{esc(s.slice(0,60))}}</div>`).join('')}}${{SHELLS.includes(m.id)?`<div style="margin-top:4px"><a class="go" target="_blank" href="match_${{m.id}}.html">比赛详情 · 时间轴 ↗</a></div>`:''}}</div>`);
function render(){{const q=document.getElementById('q').value.trim().toLowerCase();
let types=[...document.querySelectorAll('.tab.on')].map(t=>t.dataset.t);
if(types.includes('all'))types=['team','champion','composition','player','alias','match'];
let out='';
for(const t of types){{for(const h of cards[t]){{if(!q||h.toLowerCase().includes(q))out+=h;}}}}
document.getElementById('results').innerHTML=out||'<div class="empty">无命中（试试昵称/英文ID/队伍名）</div>';}}
document.getElementById('q').addEventListener('input',render);
document.getElementById('tabs').addEventListener('click',e=>{{
  if(e.target.classList.contains('tab')){{
    const all=document.getElementById('tabs').querySelectorAll('.tab');
    if(e.target.dataset.t==='all'){{all.forEach(x=>x.classList.remove('on'));e.target.classList.add('on');}}
    else{{all.forEach(x=>x.classList.remove('on'));e.target.classList.add('on');}}
    render();
  }}}});
render();
</script></body></html>"""


def main() -> int:
    OUT.write_text(render(build_dataset()), encoding="utf-8")
    print("generated reports/intel_quick_lookup.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
