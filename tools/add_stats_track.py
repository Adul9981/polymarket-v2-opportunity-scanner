#!/usr/bin/env python3
"""Inject page-view tracking snippet into every site page (idempotent).

在 .danmu_intel_site/ 下所有 HTML 的 </body> 前插入打点脚本：
POST https://danmu-intel-api.vercel.app/api/track（页面路径 + 稳定访客 ID），
统计数据经 Vercel 中转记录到 VPS stats server。
访客 ID 用 localStorage 持久化（uuid），服务端据此算"累计访问人数/今日访问人数"
（2026-08-26 用户要求新增指标）。
"""

from __future__ import annotations

import re
from pathlib import Path

SITE = Path(".danmu_intel_site")
SNIPPET = (
    '<script>'
    '(function(){'
    'var v=null;'
    'try{v=localStorage.getItem("di_v")}catch(e){}'
    'if(!v){v=(window.crypto&&crypto.randomUUID)?crypto.randomUUID():("v"+Date.now()+"-"+Math.random().toString(36).slice(2));'
    'try{localStorage.setItem("di_v",v)}catch(e){}}'
    'fetch("https://danmu-intel-api.vercel.app/api/track",{'
    'method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({page:location.pathname,visitor:v})'
    '}).catch(function(){})})();</script>'
)

OLD_TRACK_RE = re.compile(
    r"<script>.*?danmu-intel-api\.vercel\.app/api/track.*?</script>",
    re.S,
)


def inject_all(site_dir: Path = SITE) -> int:
    changed = 0
    for p in Path(site_dir).rglob("*.html"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if '"di_v"' in text:
            continue
        text = OLD_TRACK_RE.sub("", text)
        if "</body>" not in text:
            continue
        text = text.replace("</body>", SNIPPET + "</body>", 1)
        p.write_text(text, encoding="utf-8")
        changed += 1
    return changed


def main() -> None:
    print(f"injected track into {inject_all()} pages")


if __name__ == "__main__":
    main()
