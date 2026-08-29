#!/usr/bin/env python3
"""速览卡 ↔ 正文一致性检查与自动修复（2026-08-26 用户定稿，最高）。

原则（用户）：**放不好就不放——速览卡只列关键信息，不加分类标签**。
每条关键信息必须回答两问：发生了什么（信号）+ 意味着什么（价值/含义）。

机制（2026-08-26 固化：BLUF × Key Judgment × So-What）：
- 速览卡 = 第一屏 BLUF（结论先行，3-5 条按影响×置信×可行动性排序）；
- 每条 = Key Judgment：信号一句话 +「→」+ 价值/含义一句话（含方向与置信）；
- 决策落点 = So-What / Now-What（该关注什么）。
生成端（fast_intel_node prompt）原生产出「信号+价值」；
本工具兜底：--fix 从正文重建；缺价值条目用 LLM 改写（无 key 时退化为干净提取）；
--check 是发布审计门禁，仅本地正则、不发网络请求。

本工具：
  --check 扫描页面，报告速览卡问题（empty / noisy / no_value）（退出码 1）
  --fix   修复：重建关键信息列表；缺价值时 LLM 改写（幂等，改一次即达标）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

EMPTY_RE = re.compile(r"(今日无|样本不足|待确认|待人工|不足/待)")

# 信号/方向词（提取时证明句子带方向性）
SIGNAL_RE = re.compile(
    r"方向|指向|兑现|应验|质疑|指控|正锚|负锚|看好|看衰|共识|齐呼|反转|反手|"
    r"押注|呼声|刷屏|一致|背离|主导|定调"
)

# 价值/含义词（宽松，仅用于提取排序）：句子含解释性措辞则优先。
# 教训 2026-08-26：仅「正锚/应验」等信号词不算价值句——还要有解释性措辞。
VALUE_RE = re.compile(
    r"意味着|说明|表明|预示|利好|利空|看好|看衰|风险|危险|分歧|关键变量|主导|定调|"
    r"翻盘|崩盘|送头|质疑|指控|共识|反转|反手|值得关注|胜算|失控|劣势|优势|翻车|"
    r"警惕|需注意|弹幕口径·待官方|多源确认|单源待验证|应验.{0,6}(说明|意味着|方向)|→\s*(多源|单源|待官方)"
)

# 价值句（严格，用于速览卡门禁）：必须出现解释性动词/方向词，
# 纯时间线/原文引用堆砌不达标（2026-08-26 用户定稿）。
VALUE_STRONG_RE = re.compile(
    r"意味着|说明|表明|预示|利好|利空|看好|看衰|主导|定调|翻盘|崩盘|送头|"
    r"值得关注|需关注|需注意|胜算|优势|劣势|失控|翻车|警惕|"
    r"弹幕口径·待官方|多源确认|单源待验证|应验.{0,6}(说明|意味着|方向)"
)

META_BAD = re.compile(
    r"slug|切片|intel_json|JSON|窗口|window|header|20\d\d-\d\d-\d\d|g\d+ (?:mid|bp|end)"
)

# 章节标题/元数据碎片（禁止进入速览卡；教训 2026-08-26：
# "3 BP 锚点与选人情报"、"10 预测验证回填明细"、"灰信号留痕（入 gray_signals…）"等被误当关键信息）
SECTION_NOISE = re.compile(
    r"(证据层|沉淀层|决策层|回填明细|选人情报|比赛信息与结果总览|预测验证框架|"
    r"方向性情报板|核心情报速览|状态核验|位置\s|时间轴锚点|弹幕口径推导|灰信号留痕|"
    r"gray_signals|gray_entities|维度|验证状态|赛前/局中共识|系列胜负|"
    r"G\d+ BP|阵容（弹幕口径推导|整场页|节点页|小局导航)"
)

HEAD_NOISE_RE = re.compile(r"^\d+\s+\S{2,16}\s|^[一二三四五六七八九十]+[、.．]|^\d+[、.]")

TABLE_HEAD_RE = re.compile(
    r"^(时刻|预测|结果|阵容|要点|选手|提及|评价|局\s|比赛|进度|状态|队伍|灰信号|窗口|条数|方向|簇|对象)([:：\s]|$)"
)

HEADING_RE = re.compile(r"^\d+\s+\S{2,18}(（[^）]{1,10}）)?$")


def _speedcard_region(html: str) -> tuple[int, int] | None:
    """定位速览卡卡片区域：优先 class='card speed'，回退按文本「核心情报速览」定位。

    2026-08-26 教训：fast_intel_node 生成的页面曾用 badge 样式
    （<div class="card"><span class="badge">核心情报速览…</span>），
    与标准容器不一致导致审计误判「速览卡为空」。
    """
    m = re.search(
        r'<div class="card speed">.*?(?=<div class="act">)',
        html,
        re.S,
    )
    if m:
        return m.start(), m.end()
    # 无 act 卡片（旧格式）：退回到「两个连续闭合 div」为终点
    m = re.search(
        r'<div class="card speed">.*?(?=</div>\s*</div>)',
        html,
        re.S,
    )
    if m:
        return m.start(), m.end()
    idx = html.find("核心情报速览")
    if idx < 0:
        return None
    start = html.rfind('<div class="card', 0, idx)
    if start < 0:
        start = html.rfind("<div", 0, idx)
    if start < 0:
        start = idx
    nxt = html.find('<div class="card', idx + 10)
    if nxt > start:
        return start, nxt
    return start, len(html)


def body_text(html: str) -> str:
    """去掉速览卡/导航/页脚等装饰，返回正文纯文本。"""
    t = re.sub(r'<div class="card speed">.*?</div>\s*</div>', "", html, flags=re.S)
    t = re.sub(r'<div class="card speed">.*?</div>', "", t, flags=re.S)
    r = _speedcard_region(t)
    if r:
        t = t[: r[0]] + t[r[1]:]
    # 标题/章节标题文本会与正文拼接（教训 2026-08-26：<title> 与 h2 的
    # "3 BP 锚点与选人情报"曾把紧随其后的 Winner 正锚句整段判为噪音丢弃）
    t = re.sub(r"<title>.*?</title>", "", t, flags=re.S)
    t = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", t, flags=re.S)
    t = re.sub(r"<nav.*?</nav>", "", t, flags=re.S)
    t = re.sub(r"<footer.*?</footer>", "", t, flags=re.S)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _seg_score(seg: str) -> int:
    score = 0
    if VALUE_RE.search(seg):
        score += 3
    if SIGNAL_RE.search(seg):
        score += 2
    if re.search(r"\d+\s*条|×\s*\d+|\d+[c％%]|9대1|99:1|14대8|深水|\d+:\d+", seg):
        score += 2
    if re.search(r"[\uac00-\ud7af]|[“\"『（(]", seg):
        score += 1
    return score


def key_items(text: str) -> list[str]:
    """从正文提取关键信息列表：3-5 条「信号」句（无章节噪音，不带分类标签）。"""
    segs = [s.strip() for s in re.split(r"[。！？;\n]", text) if len(s.strip()) >= 8]
    scored: list[tuple[int, str]] = []
    for seg in segs:
        if EMPTY_RE.search(seg) or META_BAD.search(seg):
            continue
        if HEADING_RE.match(seg) or TABLE_HEAD_RE.match(seg) or SECTION_NOISE.search(seg):
            continue
        if HEAD_NOISE_RE.match(seg):
            continue
        if len(seg) > 90 and seg.count("：") >= 4:
            continue  # 疑似整段表格转文本
        if "核心卖点" in seg or "产品核心" in seg:
            continue
        # 纯时间线（≥2 个 →）且无信号/价值词 -> 噪音
        if seg.count("→") >= 2 and not (VALUE_RE.search(seg) or SIGNAL_RE.search(seg)):
            continue
        s = _seg_score(seg)
        if s >= 3:
            scored.append((s, seg))
    scored.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    out: list[str] = []
    for _s, seg in scored:
        key = seg[:30]
        if key in seen:
            continue
        seen.add(key)
        if len(seg) > 70:
            seg = seg[:70] + "…"
        out.append(seg)
        if len(out) >= 5:
            break
    return out


def body_has_content(text: str) -> bool:
    """正文是否包含可提取的实质信息（用于「速览卡不应为空」判定）。"""
    return bool(key_items(text))


def speedcard_items(html: str) -> list[str]:
    """取速览卡现有 <li> 条目文本。"""
    r = _speedcard_region(html)
    if not r:
        return []
    seg = html[r[0]:r[1]]
    items = [re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<li>(.*?)</li>", seg, re.S)]
    # 兼容 Codex 全量标准页（2026-08-26 用户认可：KT-BRO 参考页）的
    # <div class="sig"> 条目；教训 2026-08-26：门禁只认 <li> 会把
    # 现行标准页误判为「速览卡为空」。
    if not items:
        items = [
            re.sub(r"<[^>]+>", " ", x).strip()
            for x in re.findall(r'<div class="sig">(.*?)</div>', seg, re.S)
        ]
    return items


def extract_decision(html: str) -> str:
    m = re.search(r'<div class="act">(.*?)</div>', html, re.S)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", " ", m.group(1)).strip()


def items_issues(items: list[str]) -> list[str]:
    bad: list[str] = []
    if not items:
        return ["empty"]
    if any(
        SECTION_NOISE.search(i) or HEAD_NOISE_RE.match(i) or TABLE_HEAD_RE.match(i)
        or (i.count("→") >= 2 and not VALUE_STRONG_RE.search(i))
        for i in items
    ):
        bad.append("noisy")
    if not any(VALUE_STRONG_RE.search(i) for i in items):
        bad.append("no_value")
    return bad


def check_page(html: str) -> list[str]:
    """返回速览卡问题列表：正文有内容时，速览卡必须是有价值的关键信息列表。"""
    body = body_text(html)
    if not body_has_content(body):
        return []
    return items_issues(speedcard_items(html))


def deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    try:
        cfg = Path.home() / ".codex" / "config.toml"
        if cfg.exists():
            m = re.search(
                r'experimental_bearer_token\s*=\s*"([^"]+)"',
                cfg.read_text(encoding="utf-8"),
            )
            if m:
                return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    return ""


def llm_rewrite_items(title: str, items: list[str], decision: str) -> list[str] | None:
    """把缺价值的条目改写为「信号 → 价值（置信）」；失败返回 None（调用方降级）。"""
    key = deepseek_key()
    if not key:
        return None
    draft = "\n".join(f"- {i}" for i in items[:8])
    prompt = (
        "你是电竞弹幕情报分析师。把下面的「核心情报速览」草稿改写为「信号 + 价值」条目。\n"
        "要求：\n"
        "1) 每条 = 信号（发生了什么，含方向与关键对象）+「→」+ 一句价值/含义"
        "（意味着什么、为什么重要，≤35 字，含方向与置信标签）。\n"
        "2) 置信标签只用：单源待验证（默认）/ 多源确认（仅当草稿明确出现多路/多房间共振）/"
        "弹幕口径·待官方（结果、比分类）。依据草稿判断，禁止臆造。\n"
        "3) 禁止出现：章节号或章节标题（如「3 BP 锚点与选人情报」「10 预测验证回填明细」）、"
        "元数据碎片（如「灰信号留痕（入 gray_signals…）」）、纯时间线（10:56→11:28→11:32）、"
        "表格头或维度词（位置/维度/验证状态/系列胜负）。\n"
        "4) 只改写草稿已有信息，禁止编造草稿没有的事实；草稿信息不足时精简为信号本身。\n"
        "5) 灰信号类条目必须保留「观众质疑，非结论」语义（可写「观众质疑/风险标注」），"
        "禁止写成实锤或违规结论。\n"
        "6) 输出 JSON 对象，字段 items 为数组（3-5 条），每项含 signal / value / confidence。\n"
        f"页面：{title or '未知页面'}\n草稿：\n{draft}\n决策落点：{decision or '无'}"
    )
    body = json.dumps(
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1600,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=120).read())
        content = r["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            i, j = content.find("{"), content.rfind("}")
            if i < 0 or j <= i:
                return None
            parsed = json.loads(content[i:j + 1])
        if isinstance(parsed, dict):
            parsed = parsed.get("items") or parsed.get("key_items") or []
        out: list[str] = []
        for it in (parsed if isinstance(parsed, list) else [])[:5]:
            if not isinstance(it, dict):
                continue
            sig = str(it.get("signal", "")).strip()
            val = str(it.get("value", "")).strip()
            conf = str(it.get("confidence", "")).strip()
            if not sig:
                continue
            line = sig
            if val:
                line += " → " + val
            if conf and conf not in line:
                line += f"（{conf}）"
            out.append(line)
        return out or None
    except Exception:  # noqa: BLE001
        return None


def fix_speedcard(html: str, page_name: str = "", use_llm: bool = True) -> str:
    """重建速览卡为「信号+价值」列表；已有合格列表则幂等跳过。"""
    items_now = speedcard_items(html)
    if items_now and not items_issues(items_now):
        return html  # 已是合格列表（含价值句），不重复改写
    body = body_text(html)
    items = key_items(body)
    if use_llm and items and items_issues(items):
        rew = llm_rewrite_items(page_name, items, extract_decision(html))
        if rew:
            items = rew
    if items:
        lis = "".join(f"<li>{esc(i)}</li>" for i in items)
        block = (
            '<div style="margin-top:8px"><ul style="padding-left:18px;margin:6px 0;'
            'font-size:13px;line-height:1.75">' + lis + "</ul></div>"
        )
    else:
        block = (
            '<div style="margin-top:8px"><p style="font-size:13px;color:var(--sub)">'
            "今日无关键信息（样本不足/待确认）</p></div>"
        )
    # 2026-08-26 教训：局部正则替换会把嵌套结构的速览卡破坏成空（KT-BRO G1 BP
    # 曾被重建后 <li> 全丢、审计判空）——改为整卡重建为标准结构。
    r = _speedcard_region(html)
    if not r:
        return html
    new_card = (
        '<div class="card speed">\n'
        '  <h2><span class="no">0</span>核心情报速览</h2>\n'
        + block
        + "\n</div>"
    )
    return html[: r[0]] + new_card + html[r[1]:]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".danmu_intel_site/intel")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="修复时不调用 LLM 改写（仅正则提取）")
    ap.add_argument("--file", default="")
    args = ap.parse_args()

    files = [Path(args.file)] if args.file else sorted(Path(args.dir).glob("intel_danmu_*.html"))
    bad_pages = 0
    fixed = 0
    for p in files:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        if "核心情报速览" not in t:
            continue
        issues = check_page(t)
        if args.check and issues:
            bad_pages += 1
            print(f"[check] {p.name}: 速览卡问题 -> {issues}")
        if args.fix:
            t2 = fix_speedcard(t, page_name=p.stem, use_llm=not args.no_llm)
            if t2 != t:
                fixed += 1
                p.write_text(t2, encoding="utf-8")
                print(f"[fix] {p.name}: 已重建速览卡（信号+价值）")
    print(f"结果: 问题页 {bad_pages}，修复 {fixed}")
    return 1 if (args.check and bad_pages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
