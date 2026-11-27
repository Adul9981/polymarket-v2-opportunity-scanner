#!/usr/bin/env python3
"""Build the static search index and search page for the intel site."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES_JSON = ROOT / "docs" / "data" / "intel" / "matches.json"

FIXED_SEARCH = (
    ("今日情报", "today.html", "今日赛程和进行中比赛", "页面"),
    ("比赛局势", "match_situation.html", "当前比赛比分、评分和实时局势", "页面"),
    ("历史库", "history.html", "按日期和比赛查找历史情报", "页面"),
    ("赛前情报", "intel_prematch.html", "赛前市场共识、队伍状态和准备信息", "页面"),
    ("问答 FAQ", "intel_help.html", "使用指南和常见问题", "页面"),
    ("形态决策台", "pattern_decision_workspace.html", "方向、价格、止盈和失效位", "页面"),
    ("形态图谱", "pattern_atlas.html", "正式形态、结构家族和历史路径", "页面"),
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _page_shell(title: str, body: str, description: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(description)}">
<link rel="icon" type="image/svg+xml" href="../favicon.svg">
<title>{esc(title)} · 弹幕情报库</title>
<style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--blue:#0071e3}}
*{{box-sizing:border-box}}body{{margin:0;padding-top:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:14px 16px 64px}}
header{{padding:24px 0 18px}}header h1{{margin:0;font-size:clamp(30px,4vw,48px);letter-spacing:-1.5px;line-height:1.08}}
header p{{max-width:760px;margin:10px 0 0;color:var(--sub)}}.eyebrow{{color:var(--blue);font-size:11px;font-weight:750;letter-spacing:.09em}}
.searchbox{{position:sticky;top:58px;z-index:5;display:flex;gap:9px;padding:12px;margin:16px 0;background:rgba(245,245,247,.95);backdrop-filter:blur(16px);border:1px solid var(--line);border-radius:17px}}
.searchbox input{{flex:1;min-width:0;border:1px solid #d7d7dc;border-radius:12px;background:#fff;padding:12px 14px;font:inherit;font-size:16px;outline:none}}.searchbox input:focus{{border-color:var(--blue);box-shadow:0 0 0 3px rgba(0,113,227,.1)}}
.chips{{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 12px}}.chip{{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 11px;font:inherit;font-size:12px;color:#515154;cursor:pointer}}.chip.on{{background:#111318;color:#fff;border-color:#111318}}
.result-head{{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:14px 0 8px;color:var(--sub);font-size:11px}}.results{{display:grid;gap:9px}}
.result{{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:center;padding:14px 15px;background:#fff;border:1px solid var(--line);border-radius:15px;text-decoration:none;color:inherit}}.result:hover{{border-color:#b9d8f6}}.result .type{{padding:4px 7px;border-radius:8px;background:#f1f5f8;color:#52606d;font-size:10px;font-weight:700}}.result b{{display:block;font-size:15px}}.result small{{display:block;color:var(--sub);font-size:11.5px;margin-top:3px}}.result .arrow{{color:var(--blue);font-weight:800}}
.empty{{padding:40px;text-align:center;color:var(--sub);background:#fff;border:1px dashed #d9d9de;border-radius:16px}}
@media(max-width:640px){{header h1{{letter-spacing:-1px}}.searchbox{{top:0}}.result{{grid-template-columns:auto minmax(0,1fr)}}.result .arrow{{display:none}}}}
</style></head><body>{body}</body></html>"""


def _node_title(name: str) -> str:
    body = re.sub(r"^intel_(?:danmu|soop)_|\.html$", "", name)
    body = re.sub(r"_\d{4}-\d{2}-\d{2}", "", body)
    return body.replace("_", " ").replace("-", " vs ", 1)


def collect_entries(site_dir: Path) -> list[dict]:
    intel = site_dir / "intel"
    entries: list[dict] = []
    seen: set[str] = set()

    def add(kind: str, title: str, subtitle: str, url: str, keywords: list[str], sort_key: str = "") -> None:
        if not url or url in seen or not (intel / url).exists():
            return
        seen.add(url)
        entries.append({
            "type": kind,
            "title": title,
            "subtitle": subtitle,
            "url": url,
            "keywords": [k for k in keywords if k],
            "sort": sort_key,
        })

    if MATCHES_JSON.exists():
        try:
            matches = json.loads(MATCHES_JSON.read_text(encoding="utf-8")).get("matches", [])
        except (OSError, json.JSONDecodeError):
            matches = []
        for match in matches:
            teams = match.get("teams") or []
            if len(teams) != 2:
                continue
            slug = str(match.get("event_slug") or match.get("slug") or match.get("id") or "")
            if not slug:
                continue
            date = str(match.get("date") or (match.get("start_time") or "")[:10])
            league = str(match.get("league") or "")
            result = str(match.get("result_inferred") or "")
            add(
                "比赛", " vs ".join(map(str, teams)),
                " · ".join(v for v in (league, date, result) if v),
                f"match_{slug}.html", [slug, league, date, result, *map(str, teams)], date,
            )

    for path in sorted(intel.glob("intel_danmu_*.html"), reverse=True):
        if path.name.startswith((".", "._")):
            continue
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
        add(
            "节点", _node_title(path.name),
            "弹幕情报节点" + (f" · {date_match.group(1)}" if date_match else ""),
            path.name, [path.stem.replace("_", " "), "弹幕", "情报"], date_match.group(1) if date_match else "",
        )

    for path in sorted(intel.glob("intel_profile_*.html")):
        kind = path.stem.replace("intel_profile_", "").split("_", 1)[0]
        title = path.stem.replace("intel_profile_", "").replace("_", " ")
        add("画像", title, f"{kind} 画像与历史样本", path.name, [title, kind, "画像"])

    for title, url, desc, kind in FIXED_SEARCH:
        add(kind, title, desc, url, [title, desc])
    return entries


def build_search_page() -> str:
    body = """<main class="wrap"><header><div class="eyebrow">GLOBAL SEARCH</div><h1>搜索情报库</h1>
<p>按比赛、队伍、选手、联赛、日期或报告节点搜索。输入中文、英文缩写均可。</p></header>
<div class="searchbox"><input id="q" type="search" autocomplete="off" autofocus placeholder="例如：T1、LCK、2026-11-27、BP、Faker"></div>
<div class="chips" id="chips"><button class="chip on" data-type="">全部</button><button class="chip" data-type="比赛">比赛</button><button class="chip" data-type="节点">节点</button><button class="chip" data-type="画像">画像</button><button class="chip" data-type="页面">页面</button></div>
<div class="result-head"><span id="count">正在载入索引…</span><span id="updated"></span></div>
<div class="results" id="results"></div></main>
<script>
(function(){
  const $=id=>document.getElementById(id);
  let entries=[],type='';
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
  const norm=s=>String(s||'').toLocaleLowerCase('zh-CN').replace(/\\s+/g,' ').trim();
  function render(){
    const q=norm($('q').value);
    let rows=entries.filter(x=>!type||x.type===type);
    if(q){const terms=q.split(' ').filter(Boolean);rows=rows.filter(x=>{const hay=norm([x.title,x.subtitle,...(x.keywords||[])].join(' '));return terms.every(t=>hay.includes(t))});}
    const total=rows.length;rows=rows.slice(0,80);
    $('count').textContent=(q?'搜索结果 ':'浏览结果 ')+total+' 条'+(total>rows.length?' · 当前显示 '+rows.length+' 条':'');
    $('results').innerHTML=rows.length?rows.map(x=>'<a class="result" href="'+esc(x.url)+'"><span class="type">'+esc(x.type)+'</span><span><b>'+esc(x.title)+'</b><small>'+esc(x.subtitle)+'</small></span><span class="arrow">→</span></a>').join(''):'<div class="empty">没有找到匹配结果，请尝试队伍缩写、联赛或日期。</div>';
  }
  $('q').addEventListener('input',render);
  document.querySelectorAll('[data-type]').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('[data-type]').forEach(x=>x.classList.remove('on'));btn.classList.add('on');type=btn.dataset.type;render();});
  fetch('search_index.json?v='+Date.now(),{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(data=>{entries=data.entries||[];$('updated').textContent='索引更新 '+String(data.generated_at||'').replace('T',' ').slice(0,16);render();}).catch(err=>{$('count').textContent='搜索索引加载失败';$('results').innerHTML='<div class="empty">'+esc(err.message||err)+'</div>';});
})();
</script>"""
    return _page_shell("搜索", body, "搜索弹幕情报库的比赛、队伍、选手、联赛和报告节点")


def build_all(site_dir: Path) -> dict[str, int]:
    intel = site_dir / "intel"
    intel.mkdir(parents=True, exist_ok=True)
    entries = collect_entries(site_dir)
    entries.sort(key=lambda row: (row.get("sort", ""), row["title"]), reverse=True)
    type_rank = {"比赛": 0, "页面": 1, "画像": 2, "节点": 3}
    entries.sort(key=lambda row: type_rank.get(row["type"], 9))
    payload = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds"),
        "entries": entries,
    }
    (intel / "search_index.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (intel / "search.html").write_text(build_search_page(), encoding="utf-8")
    return {"entries": len(entries), "search": 1}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", default=".danmu_intel_site")
    args = parser.parse_args()
    counts = build_all(Path(args.site_dir))
    print(f"[site-search] entries={counts['entries']}")


if __name__ == "__main__":
    main()
