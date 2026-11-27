#!/usr/bin/env python3
"""Idempotent unified top nav + simple breadcrumb for every site page.

幂等保证：先清除页面上所有旧 <nav> 与旧面包屑，再插入唯一一份统一导航，
运行任意次数结果相同（每页 1 导航 + 1 面包屑 + 1 favicon）。
由 publish / vps_publish 在复制后运行，覆盖服务器自动产出页。
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

SITE = Path(".danmu_intel_site")
FREE_MODE_FLAG = Path(__file__).resolve().parents[1] / "runtime" / "free_mode.flag"


def free_mode() -> bool:
    """True = 全公开模式：隐藏订阅入口（2026-10-26 用户要求暂停订阅）。"""
    return FREE_MODE_FLAG.exists()

_TEAM_ABBR: dict[str, str] = {}
_REG_PATH = Path(__file__).resolve().parents[1] / "docs" / "data" / "intel" / "team_names.json"
if _REG_PATH.exists():
    try:
        for _t in json.loads(_REG_PATH.read_text(encoding="utf-8")).get("teams", []):
            for _k in [_t["abbr"], _t["full"], *_t.get("aliases", [])]:
                _TEAM_ABBR[str(_k).lower()] = _t["abbr"]
    except Exception:  # noqa: BLE001
        pass


def _prefix(p: Path, root: Path) -> str:
    rel = p.relative_to(root)
    depth = len(rel.parts) - 1
    return "../" * depth


def _clean(text: str) -> str:
    # 删除所有导航（连同前后换行，保证幂等）
    text = re.sub(r"\n?<nav[^>]*>.*?</nav>\n?", "", text, flags=re.S)
    # 删除旧顶栏 div.top（比赛壳/情报页残留，统一导航已覆盖）
    text = re.sub(r"\n?<div class=\"top\"[^>]*>.*?</div>\n?", "", text, flags=re.S)
    # 删除所有旧面包屑 div（连同前后换行）
    # 2026-10-04：不能吃掉面包屑后面的换行——原有 `\n?` 会在第二次注入时多删 1 个字符，
    # 使注入"要跑两遍才收敛"（回归 tests/test_site_framework.py::test_nav_injection_is_idempotent）
    text = re.sub(
        r'\n?<div[^>]*style="max-width:(?:1020|1280)px;margin:(?:-10px|4px) auto 14px;[^"]*"[^>]*>.*?</div>',
        "",
        text,
        flags=re.S,
    )
    return text


def nav_html(pre: str, active: str = "") -> str:
    if active:
        active = active_of(active)

    def link(href: str, label: str, key: str) -> str:
        on = (
            ' style="display:inline-flex;align-items:center;height:32px;padding:0 11px;'
            'border-radius:999px;background:#1d1d1f;color:#fff;font-weight:650;font-size:13px;'
            'text-decoration:none;white-space:nowrap" aria-current="page"'
            if key == active
            else ' style="display:inline-flex;align-items:center;height:32px;padding:0 10px;'
            'border-radius:999px;background:rgba(255,255,255,.72);border:1px solid rgba(0,0,0,.055);'
            'color:#515154;font-weight:500;font-size:13px;text-decoration:none;white-space:nowrap"'
        )
        return f'<a href="{href}"{on}>{label}</a>'

    def divider() -> str:
        return '<span aria-hidden="true" style="width:1px;height:16px;background:#d8d8dd;margin:0 3px;flex:none"></span>'

    in_sub = bool(pre)
    home_h = pre + "index.html"
    today_h = "today.html" if in_sub else "intel/today.html"
    situation_h = "match_situation.html" if in_sub else "intel/match_situation.html"
    hist_h = "history.html" if in_sub else "intel/history.html"
    prematch_h = "intel_prematch.html" if in_sub else "intel/intel_prematch.html"
    help_h = "intel_help.html" if in_sub else "intel/intel_help.html"
    pattern_h = "pattern_decision_workspace.html" if in_sub else "intel/pattern_decision_workspace.html"
    atlas_h = "pattern_atlas.html" if in_sub else "intel/pattern_atlas.html"
    analytics_h = "analytics.html" if in_sub else "intel/analytics.html"
    search_h = "search.html" if in_sub else "intel/search.html"
    sub_h = pre + "subscribe.html"
    return (
        f'<nav aria-label="弹幕情报库主导航" style="position:sticky;top:0;z-index:20;'
        f'background:rgba(245,245,247,.94);backdrop-filter:saturate(180%) blur(18px);'
        f'border-bottom:1px solid rgba(0,0,0,.08);font-family:-apple-system,BlinkMacSystemFont,'
        f'\'PingFang SC\',sans-serif;box-sizing:border-box">'
        f'<div style="max-width:1280px;margin:0 auto;padding:9px 16px;display:flex;gap:5px;'
        f'align-items:center;flex-wrap:wrap;overflow-x:auto;scrollbar-width:none;'
        f'-webkit-overflow-scrolling:touch">'
        f'<a href="{home_h}" style="display:inline-flex;align-items:center;color:#1d1d1f;'
        f'text-decoration:none;font-weight:800;font-size:14px;margin-right:auto;white-space:nowrap">'
        f'<span style="display:inline-grid;place-items:center;width:25px;height:25px;border-radius:8px;'
        f'background:linear-gradient(135deg,#0071e3,#5ac8fa);color:#fff;font-size:11px;font-weight:800;'
        f'margin-right:7px;box-shadow:0 4px 10px rgba(0,113,227,.18)">DI</span>弹幕情报库</a>'
        f'{link(today_h, "今日情报", "today")}'
        f'{link(situation_h, "比赛局势", "situation")}'
        f'{link(hist_h, "历史库", "library")}'
        f'{divider()}'
        f'{link(prematch_h, "赛前情报", "prematch")}'
        f'{link(help_h, "FAQ", "help")}'
        f'{divider()}'
        f'{link(pattern_h, "形态决策台", "pattern")}'
        f'{link(atlas_h, "形态图谱", "pattern-atlas")}'
        f'{divider()}'
        f'{link(analytics_h, "访问统计", "analytics")}'
        f'{link(search_h, "搜索", "search")}'
        + ("" if free_mode() else link(sub_h, "订阅", "subscribe"))
        + '</div></nav>'
    )


def _shell_date(name: str, text: str = "") -> str:
    """比赛时间轴壳（match_*.html）的比赛日期。

    优先从文件名取（match_2026-08-23_x_y.html / match_x-y-2026-08-26.html）；
    文件名无日期时（hupu 壳 match_cs2-hupu-<id>.html / match_lol-dk-dns.html）
    回退到页面内容里的日期（sub 行 / footer / 节点文件名），壳内容恒带比赛日期。
    （教训 2026-10-25：hupu 壳文件名无日期，旧逻辑一律归「历史情报库」——
    今日直播的 Spirit-TYLOO 从今日情报页点进去，导航却高亮「历史情报库」。）
    """
    mm = re.search(r"(\d{4}-\d{2}-\d{2})", name or "")
    if mm:
        return mm.group(1)
    mm = re.search(r"(\d{4}-\d{2}-\d{2})", text or "")
    return mm.group(1) if mm else ""


def _shell_is_today(name: str, text: str = "") -> bool:
    """比赛时间轴壳（match_*.html）是否属于今天（北京时间）。"""
    today = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).date().isoformat()
    return bool(_shell_date(name, text) == today)


def _shell_title(name: str, text: str = "") -> str:
    """比赛时间轴壳的面包屑标题：优先用壳内容自带的 <h1> 对阵（"Spirit vs TYLOO"），
    取不到再回退文件名解析（title_of）。hupu 壳文件名解析不出队名（"hupu vs <id>"），
    必须走 <h1>。"""
    mm = re.search(r"<h1[^>]*>([^<]+)</h1>", text or "")
    if mm:
        t = mm.group(1).strip()
        if t:
            return t
    return title_of(name)


def breadcrumb_html(pre: str, kind: str, title: str = "", name: str = "", text: str = "") -> str:
    if kind == "root":
        return ""
    home = f'<a href="{pre}index.html" style="color:#6e6e73;text-decoration:none">首页</a>'
    in_sub = bool(pre)
    labels = {
        "pattern": "形态决策台",
        "pattern-atlas": "形态图谱",
        "prematch": "赛前情报",
        "help": "问答与使用指南",
        "today": "今日情报",
        "situation": "比赛局势",
        "history": "历史库",
        "market": "市场链接",
        "profiles": "四维画像",
        "maps": "地图战绩",
        "verification": "灰信号·验证闭环",
        "analytics": "访问统计",
        "stats": "数据统计",
        "subscribe": "订阅",
        "research": "形态研究",
        "search": "搜索",
        "report": "历史库",
        "shell": "今日情报",
    }
    label = labels.get(kind, "")
    if not label:
        return ""
    # 父级页可点击返回（教训 2026-08-26：面包屑只有首页可点，
    # 看完情报页无法一键退回清单页）
    parents = {
        "pattern": None,
        "pattern-atlas": "pattern_decision_workspace.html",
        "prematch": None,
        "help": None,
        "today": None,
        "situation": "today.html",
        "history": None,
        "market": None,
        "profiles": None,
        "maps": None,
        "verification": None,
        "analytics": None,
        "stats": None,
        "subscribe": None,
        "research": None,
        "search": None,
        "report": "history.html",
        "shell": "today.html",
    }
    if kind == "shell":
        # 壳的父级：今日开赛的比赛回「今日比赛」，历史比赛回「历史情报库」
        if _shell_is_today(name, text):
            parents["shell"] = "today.html"
        else:
            parents["shell"] = "history.html"
            label = "历史库"
    parent_link = parents.get(kind)
    parent_label = label
    # 父级页与当前页同目录（intel/ 内页面 -> intel/history.html），
    # 不能再加 pre("../")——教训 2026-08-26：曾拼成 ../history.html 导致 404
    label_html = (
        f'<a href="{parent_link}" style="color:#6e6e73;text-decoration:none">{parent_label}</a>'
        if parent_link
        else f'<b style="color:#1d1d1f">{label}</b>'
    )
    # 情报页/壳加当前标题
    fixed_titles = {
        "pattern": "形态决策台",
        "pattern-atlas": "形态图谱",
        "profiles": "四维画像",
        "maps": "地图战绩",
        "help": "问答与使用指南",
        "situation": "比赛局势",
        "prematch": "赛前情报",
        "research": "",
        "search": "",
    }
    cur_title = fixed_titles.get(kind, title)
    if cur_title == label:
        cur_title = ""
    cur = f" › <b style=\"color:#1d1d1f\">{cur_title}</b>" if cur_title else ""
    return (
        f'<div style="max-width:1280px;margin:4px auto 14px;padding:0 16px;'
        f'font-size:12px;color:#6e6e73;font-family:-apple-system,\'PingFang SC\',sans-serif">'
        f"{home} › {label_html}{cur}</div>"
    )


def kind_of(name: str) -> str:
    mapping = {
        "index.html": "root",
        "subscribe.html": "subscribe",
        "stats.html": "stats",
        "today.html": "today",
        "match_situation.html": "situation",
        "history.html": "history",
        "market_links.html": "market",
        "profiles.html": "profiles",
        "verification_traces.html": "verification",
        "intel_map_records.html": "maps",
        "research.html": "research",
        "search.html": "search",
        "pattern_decision_workspace.html": "pattern",
        "pattern_atlas.html": "pattern-atlas",
        "intel_prematch.html": "prematch",
        "intel_help.html": "help",
        "analytics.html": "analytics",
    }
    if name in mapping:
        return mapping[name]
    if name.startswith("match_"):
        return "shell"
    if name.startswith("case_"):
        return "report"
    if name.startswith("node_"):
        return "report"
    if name.startswith("closed_loop_"):
        return "report"
    if name.startswith("intel_"):
        return "report"
    return "root"


def active_of(kind: str, name: str = "", text: str = "") -> str:
    if kind == "shell":
        # 壳页导航高亮跟面包屑同一口径：今天的比赛高亮「今日情报」，
        # 历史比赛（含文件名无日期但内容也无日期的壳）高亮「历史情报库」。
        return "today" if _shell_is_today(name, text) else "library"
    return {
        "today": "today",
        "situation": "situation",
        "history": "library",
        "market": "library",
        "subscribe": "subscribe",
        "root": "",
        "report": "library",
        "shell": "today",
        "profiles": "",
        "maps": "",
        "verification": "",
        "stats": "today",
        "pattern": "pattern",
        "pattern-atlas": "pattern-atlas",
        "prematch": "prematch",
        "help": "help",
        "analytics": "analytics",
        "research": "",
        "search": "search",
    }.get(kind, "")


def title_of(name: str) -> str:
    if name.startswith("match_"):
        body = re.sub(r"^match_|\.html$", "", name)
        body = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", body)
        parts = body.split("-")
        if len(parts) >= 3 and parts[0] in ("lol", "cs2", "dota2", "dota"):
            parts = parts[1:]
        if len(parts) == 2:
            a = _TEAM_ABBR.get(parts[0].lower(), parts[0])
            b = _TEAM_ABBR.get(parts[1].lower(), parts[1])
            return f"{a} vs {b}"
        return body
    if name.startswith("intel_danmu_") or name.startswith("intel_soop_"):
        body = re.sub(r"^intel_(danmu|soop)_|\.html$", "", name)
        return body.replace("_", " ")
    return ""


def inject_file(p: Path, site: Path = SITE) -> bool:
    """Inject the canonical nav into one HTML file.

    Kept as a small public seam because systemd post-refresh hooks rewrite a
    single generated page and should not rescan the entire site every cycle.
    """
    # macOS AppleDouble resource forks (._foo.html) are binary metadata, not
    # pages. Published from an external disk they otherwise abort the entire
    # nav injection with UnicodeDecodeError.
    if p.name.startswith("._"):
        return False
    pre = "" if p.parent == site else _prefix(p, site)
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"[add-site-nav] skip non-utf8 file: {p}")
        return False
    clean = _clean(text)
    kind = kind_of(p.name)
    # 比赛局势是顶级工作台页（非比赛壳），面包屑不带 title（避免 title_of 把
    # "match_situation" 误解析成 "situation" 后缀）；比赛壳的标题优先用页面 <h1>
    # 对阵（hupu 壳文件名解析不出队名，否则显示 "hupu vs <id>"）
    title = "" if kind == "situation" else (_shell_title(p.name, clean) if kind == "shell" else title_of(p.name))
    block = nav_html(pre, active_of(kind, p.name, clean)) + breadcrumb_html(pre, kind, title, p.name, clean)
    m = re.search(r"<body[^>]*>", clean, re.I)
    if not m:
        return False
    # 统一 body 基础排版（参照今日比赛页观感：SF Pro 优先字体栈、
    # 行高 1.6、文字色、顶部留白 0）——无条件重建，幂等并修复历史重复
    body_tag = (
        '<body style="padding-top:0;font-family:-apple-system,BlinkMacSystemFont,'
        '&quot;SF Pro Text&quot;,&quot;PingFang SC&quot;,&quot;Microsoft YaHei&quot;,sans-serif;'
        'line-height:1.6;color:#1d1d1f">'
    )
    new = clean[: m.start()] + body_tag + "\n" + block + clean[m.end() :]
    # 嵌入模式：被比赛时间轴壳 iframe 加载（?embed=1）时隐藏本页导航/面包屑，
    # 避免"壳导航 + 页内导航"重复出现（教训 2026-08-25：详情页导航重复）
    # 幂等 + 自愈：先移除历史重复的嵌入脚本，再注入唯一一份
    new = re.sub(
        r'<script>if\(location\.search\.indexOf\("embed=1"\)[^<]*?</script>',
        "",
        new,
        flags=re.S,
    )
    embed_js = (
        '<script>'
        'if(location.search.indexOf("embed=1")>-1){'
        'document.querySelectorAll("nav").forEach(function(n){n.style.display="none"});'
        'document.querySelectorAll("div[style*=\'max-width:1020px\']").forEach(function(n){n.style.display="none"});'
        '}'
        '</script>'
    )
    if 'location.search.indexOf("embed=1")' not in new:
        new = new.replace("</body>", embed_js + "</body>", 1)
    # intel 子页内旧面包屑链接（../intel/xxx.html -> xxx.html）
    if p.parent != site:
        new = re.sub(r'href="\.\./intel/([^"]+)"', r'href="\1"', new)
    if new == text:
        return False
    p.write_text(new, encoding="utf-8")
    return True


def inject_all(site: Path = SITE) -> int:
    return sum(1 for p in site.rglob("*.html") if inject_file(p, site))


def main() -> None:
    print(f"normalized nav on {inject_all()} pages")


if __name__ == "__main__":
    main()
