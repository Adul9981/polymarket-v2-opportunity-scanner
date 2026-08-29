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
    text = re.sub(
        r'\n?<div[^>]*style="max-width:1020px;margin:-10px auto 14px;[^"]*"[^>]*>.*?</div>\n?',
        "",
        text,
        flags=re.S,
    )
    return text


def nav_html(pre: str, active: str = "") -> str:
    def link(href: str, label: str, key: str) -> str:
        # 完整内联样式（text-decoration:none + 固定字重/字号），禁止继承页面样式
        on = (
            ' style="color:#0071e3;font-weight:700;font-size:13px;text-decoration:none"'
            if key == active
            else ' style="color:#6e6e73;font-weight:500;font-size:13px;text-decoration:none"'
        )
        return f'<a href="{href}"{on}>{label}</a>'

    in_sub = bool(pre)
    home_h = pre + "index.html"
    today_h = "today.html" if in_sub else "intel/today.html"
    hist_h = "history.html" if in_sub else "intel/history.html"
    mkt_h = "market_links.html" if in_sub else "intel/market_links.html"
    sub_h = pre + "subscribe.html"
    return (
        f'<nav style="position:sticky;top:0;z-index:20;background:rgba(245,245,247,.92);'
        f'backdrop-filter:saturate(180%) blur(14px);border-bottom:1px solid #e5e5ea;'
        f'padding:10px 16px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;'
        f'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',sans-serif;'
        f'max-width:1020px;margin:0 auto 18px;box-sizing:border-box">'
        f'<a href="{home_h}" style="color:#1d1d1f;text-decoration:none;font-weight:800;font-size:14px;margin-right:auto">'
        f'<span style="display:inline-grid;place-items:center;width:22px;height:22px;border-radius:7px;'
        f'background:linear-gradient(135deg,#0071e3,#5ac8fa);color:#fff;font-size:11px;font-weight:800;'
        f'margin-right:7px">DI</span>弹幕情报库</a>'
        f'{link(home_h, "首页", "home")}'
        f'{link(today_h, "今日比赛", "today")}'
        f'{link(hist_h, "历史情报库", "history")}'
        f'{link(mkt_h, "市场链接", "market")}'
        f'{link(sub_h, "订阅", "subscribe")}'
        f"</nav>"
    )


def breadcrumb_html(pre: str, kind: str, title: str = "", name: str = "") -> str:
    if kind == "root":
        return ""
    home = f'<a href="{pre}index.html" style="color:#6e6e73;text-decoration:none">首页</a>'
    in_sub = bool(pre)
    labels = {
        "today": "今日比赛",
        "history": "历史情报库",
        "market": "市场链接",
        "profiles": "画像速查",
        "verification": "可验证情报痕迹",
        "stats": "数据统计",
        "subscribe": "订阅",
        "report": "历史情报库",
        "shell": "今日比赛",
    }
    label = labels.get(kind, "")
    if not label:
        return ""
    # 父级页可点击返回（教训 2026-08-26：面包屑只有首页可点，
    # 看完情报页无法一键退回清单页）
    parents = {
        "today": "today.html",
        "history": "history.html",
        "market": "market_links.html",
        "profiles": "profiles.html",
        "verification": "verification_traces.html",
        "stats": "stats.html",
        "subscribe": "subscribe.html",
        "report": "history.html",
        "shell": "today.html",
    }
    if kind == "shell":
        # 壳的父级：今日开赛的比赛回「今日比赛」，历史比赛回「历史情报库」
        mm = re.search(r"(\d{4}-\d{2}-\d{2})", name or "")
        today = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))
        ).date().isoformat()
        if mm and mm.group(1) == today:
            parents["shell"] = "today.html"
        else:
            parents["shell"] = "history.html"
            label = "历史情报库"
    parent_link = parents.get(kind)
    # 父级页与当前页同目录（intel/ 内页面 -> intel/history.html），
    # 不能再加 pre("../")——教训 2026-08-26：曾拼成 ../history.html 导致 404
    label_html = (
        f'<a href="{parent_link}" style="color:#6e6e73;text-decoration:none">{label}</a>'
        if parent_link
        else f'<b style="color:#1d1d1f">{label}</b>'
    )
    # 情报页/壳加当前标题
    cur = f" › <b style=\"color:#1d1d1f\">{title}</b>" if title else ""
    return (
        f'<div style="max-width:1020px;margin:-10px auto 14px;padding:0 16px;'
        f'font-size:12px;color:#6e6e73;font-family:-apple-system,\'PingFang SC\',sans-serif">'
        f"{home} › {label_html}{cur}</div>"
    )


def kind_of(name: str) -> str:
    mapping = {
        "index.html": "root",
        "subscribe.html": "subscribe",
        "stats.html": "stats",
        "today.html": "today",
        "history.html": "history",
        "market_links.html": "market",
        "profiles.html": "profiles",
        "verification_traces.html": "verification",
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


def active_of(kind: str) -> str:
    return {
        "today": "today",
        "history": "history",
        "market": "market",
        "subscribe": "subscribe",
        "root": "home",
        "report": "history",
        "shell": "today",
        "profiles": "history",
        "verification": "history",
        "stats": "home",
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


def inject_all(site: Path = SITE) -> int:
    changed = 0
    for p in site.rglob("*.html"):
        pre = "" if p.parent == site else _prefix(p, site)
        text = p.read_text(encoding="utf-8")
        clean = _clean(text)
        kind = kind_of(p.name)
        block = nav_html(pre, active_of(kind)) + breadcrumb_html(pre, kind, title_of(p.name), p.name)
        m = re.search(r"<body[^>]*>", clean, re.I)
        if not m:
            continue
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
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    print(f"normalized nav on {inject_all()} pages")


if __name__ == "__main__":
    main()
