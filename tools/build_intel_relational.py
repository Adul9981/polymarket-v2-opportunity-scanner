#!/usr/bin/env python3
"""生成情报库「关联浏览台」（静态 HTML）：从任意实体出发，浏览其关联网络。

数据：docs/data/intel/graph.json（tools/build_intel_graph.py 生成）
输出：reports/intel_relational.html
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "docs" / "data" / "intel"
OUT = ROOT / "reports" / "intel_relational.html"

EDGE_LABEL = {
    "contains": "联赛包含队伍",
    "plays_for": "效力于",
    "in_match": "参赛比赛",
    "anchored_by": "英雄锚点（选手/队伍）",
    "counters": "克制",
    "pairs_with": "搭配",
    "in_composition": "构成体系",
    "uses": "惯用体系",
    "sampled_in": "样本比赛",
    "at_match": "关联比赛（信号）",
    "refers_to": "指代",
    "official_result": "官方结算",
    "report": "情报页",
}
TYPE_LABEL = {
    "league": "联赛", "team": "队伍", "player": "选手", "champion": "英雄",
    "composition": "体系", "match": "比赛", "gray_signal": "灰信号", "bp_signal": "BP 信号",
    "alias": "昵称", "report": "情报页", "official": "客观层",
}


def main() -> int:
    graph = json.loads((INTEL / "graph.json").read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]
    rel: dict[str, list[dict]] = {}
    for e in edges:
        if e["from"] == e["to"]:
            continue
        rel.setdefault(e["from"], []).append({"type": e["type"], "id": e["to"]})
        rel.setdefault(e["to"], []).append({"type": e["type"], "id": e["from"]})
    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "nodes": nodes,
        "rel": rel,
        "shells": [f"match_{p.stem[6:]}.html" for p in (ROOT / "reports").glob("match_*.html")],
        "labels": EDGE_LABEL,
        "tlabels": TYPE_LABEL,
    }
    data = json.dumps(payload, ensure_ascii=False)
    css = """
:root{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#86868b;--accent:#0071e3;--line:#e8e8ed}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",Arial,sans-serif;line-height:1.6;padding:24px 16px 60px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:24px;font-weight:700;margin-bottom:4px}
.sub{color:var(--sub);font-size:13px;margin-bottom:16px}
.search{width:100%;padding:12px 16px;font-size:15px;border:1px solid var(--line);border-radius:14px;outline:none;background:var(--card)}
.search:focus{border-color:var(--accent)}
.hint{color:var(--sub);font-size:12px;margin:8px 2px 12px}
.card{background:var(--card);border-radius:14px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.head{font-size:17px;font-weight:700;color:var(--accent)}
.meta{color:var(--sub);font-size:12px;margin:2px 0 8px}
.sec{font-size:13px;font-weight:700;margin:10px 0 4px}
.lnk{display:inline-block;background:#f0f4ff;border:1px solid var(--line);border-radius:10px;padding:5px 10px;margin:3px 4px 3px 0;font-size:12px;cursor:pointer;color:var(--accent)}
.lnk:hover{border-color:var(--accent)}
a.go{color:var(--accent);text-decoration:none;font-weight:600}
.empty{color:var(--sub);padding:20px;text-align:center}
.note{color:var(--sub);font-size:12px;margin-top:18px}
"""
    js = r"""
const D = DATA;
const N = {}; D.nodes.forEach(n=>N[n.id]=n);
const L = D.labels, T = D.tlabels;
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function hrefFor(n){
  const m={team:'intel_profile_team_',champion:'intel_profile_champion_',player:'intel_profile_player_',league:'intel_profile_league_',composition:'intel_profile_composition_'};
  if(n.type==='report')return n.id+'.html';
  if(m[n.type])return m[n.type]+n.id+'.html';
  if(n.type==='match'&&D.shells.includes('match_'+n.id+'.html'))return 'match_'+n.id+'.html';
  return null;
}
function pick(ids){
  const box=document.getElementById('picker');
  box.innerHTML='<div class="sec">选择实体（'+ids.length+' 个候选）</div>'+
    ids.slice(0,40).map(id=>{const n=N[id];const h=hrefFor(n);
      return '<span class="lnk" onclick="show(\''+id+'\')">'+esc(T[n.type]||n.type)+' · '+esc(n.label)+'</span>';}).join('')
    || '<div class="empty">无匹配</div>';
}
function show(id){
  const n=N[id]; if(!n)return; const h=hrefFor(n);
  document.getElementById('picker').innerHTML='';
  let body='<div class="card"><div class="head">'+esc(T[n.type]||n.type)+' · '+esc(n.label)+'</div>'+
    '<div class="meta">ID: '+esc(id)+(n.sub?' · '+esc(n.sub):'')+(h?' · <a class="go" target="_blank" href="'+h+'">打开画像页 ↗</a>':'')+'</div>';
  const rel=D.rel[id]||[]; const groups={};
  rel.forEach(r=>{(groups[r.type]=groups[r.type]||[]).push(r.id);});
  Object.keys(groups).forEach(t=>{
    body+='<div class="sec">'+esc(L[t]||t)+'（'+groups[t].length+'）</div>'+
      groups[t].map(nid=>{const nn=N[nid];const hh=hrefFor(nn);
        if(nn.type==='report')return '<span class="lnk"><a class="go" target="_blank" href="'+nid+'.html">'+esc(nn.label)+'</a></span>';
        return '<span class="lnk" onclick="show(\''+nid+'\')">'+esc(T[nn.type]||nn.type)+' · '+esc(nn.label)+(hh?' ↗':'')+'</span>';}).join('');
  });
  body+='</div>';
  document.getElementById('detail').innerHTML=body; window.scrollTo(0,0);
}
document.getElementById('q').addEventListener('input',e=>{
  const q=e.target.value.trim().toLowerCase();
  if(!q){pick([]);return;}
  const ids=D.nodes.filter(n=>(n.label+' '+n.id+' '+(n.sub||'')).toLowerCase().includes(q)).map(n=>n.id);
  pick(ids);
});
"""
    js = js.replace("const D = DATA;", "const D = " + data + ";")
    page = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>情报库 · 关联浏览台</title><style>%s</style></head>
<body><div class="wrap">
<h1>弹幕情报库 · 关联浏览台</h1>
<p class="sub">从任意实体出发，沿关系链浏览：队伍 → 比赛 → 情报页 → 灰信号/BP 锚 → 官方结算；英雄 → 锚点选手/队伍 → 体系。</p>
<input id="q" class="search" placeholder="输入实体：KC / 杰斯 / zeus / 2026-08-24_kc_shft / 绿龙" autofocus>
<div class="hint">搜索选择实体 → 详情内点关联块继续跳转；情报页/画像页可打开实际报告。</div>
<div id="picker" class="card"></div>
<div id="detail"></div>
<p class="note">灰信号纪律：观众质疑非结论。关联图自动生成（tools/build_intel_graph.py + build_intel_relational.py）。数据更新至 %s。</p>
</div>
<script>%s</script></body></html>""" % (css, payload["generated"], js)
    OUT.write_text(page, encoding="utf-8")
    print("generated reports/intel_relational.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
