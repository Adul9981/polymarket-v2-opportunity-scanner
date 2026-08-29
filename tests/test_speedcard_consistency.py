"""速览卡「信号+价值」一致性回归（2026-08-26 固化）。

教训：速览卡曾混入章节号/章节标题碎片（"3 BP 锚点与选人情报"、
"10 预测验证回填明细"、"灰信号留痕（入 gray_signals…)"）与纯时间线，
且不写关键信息的价值/含义；title/h2 文本还会与正文拼接，
把紧随标题的 Winner 正锚句整段误判为噪音丢弃。
"""

from __future__ import annotations

from speedcard_consistency import (
    body_text,
    check_page,
    fix_speedcard,
    items_issues,
    key_items,
    speedcard_items,
)


def _page(li_items, body_paras):
    lis = "".join(f"<li>{i}</li>" for i in li_items)
    paras = "".join(f"<p>{p}</p>" for p in body_paras)
    return (
        '<!doctype html><html><head><meta charset="UTF-8">'
        "<title>DRXC vs BFXY G4 mid</title></head><body>"
        '<div class="card speed"><h2><span class="no">0</span>核心情报速览</h2>'
        '<div class="top"><span class="score-big">DRXC 1:2 BFXY</span></div>'
        f'<div style="margin-top:8px"><ul>{lis}</ul></div>'
        '<div class="act"><b>决策落点：</b>关注奇亚娜节奏与亚索送头风险。</div></div>'
        f'<div class="card"><h2><span class="no">3</span>BP 锚点与选人情报</h2>{paras}</div>'
        "</body></html>"
    )


def test_key_items_strips_title_and_heading_noise():
    """title/h2 的章节标题不能把紧随其后的真实信号句一起丢掉。"""
    page = (
        "<html><head><title>G4 mid DRXC vs BFXY</title></head><body>"
        '<div class="card"><h2>3 BP 锚点与选人情报</h2>'
        "<p>Winner×奇亚娜 正锚：10:56（위너 키아나 lck1위）→ 11:28 大龙强抢（스틸 ㄷㄷ）"
        "→ G4 结束应验（弹幕口径）。</p></div></body></html>"
    )
    items = key_items(body_text(page))
    assert any("奇亚娜" in i for i in items)
    assert not any("BP 锚点与选人情报" in i for i in items)


def test_chapter_noise_flagged_and_fixed():
    page = _page(
        [
            "3 BP 锚点与选人情报 三、G4 BP / 阵容（弹幕口径推导 · 待官方确认） 位置 Kiwoom DRX（키움） BNK FearX",
            "灰信号留痕（入 gray_signals / gray_entities） ：FearX 单场 44 条灰信号相关弹幕（直接指控 26 条）",
        ],
        [
            "Winner×奇亚娜 正锚：10:56（위너 키아나 lck1위）→ 11:28 大龙强抢（스틸 ㄷㄷ）→ G4 结束应验（弹幕口径）。",
            "Slayer×亚索 负锚：10:57（야필패）→ 11:15（야스오는 승리가없어）→ 11:32 G4 结束（应验，弹幕口径）。",
        ],
    )
    assert "noisy" in check_page(page)
    fixed = fix_speedcard(page, use_llm=False)
    # 无 LLM 时只保证清掉章节/元数据碎片；价值句依赖生成端或 LLM 改写
    items = speedcard_items(fixed)
    assert not any("BP 锚点与选人情报" in i or "灰信号留痕" in i or "三、G4 BP / 阵容" in i for i in items)


def test_old_sig_format_without_li_is_empty():
    page = _page([], ["观众 3:0 赛前共识命中，说明市场情绪与弹幕共识一致。"])
    assert "empty" in check_page(page)


def test_value_items_pass():
    page = _page(
        [
            "观众 3:0 赛前共识命中 → 说明市场情绪与弹幕共识一致，利于热门侧（多源确认）",
            "Winner 奇亚娜大龙强抢成功 → 节奏优势确立，可能主导比赛（单源待验证）",
        ],
        ["观众 3:0 赛前共识命中，说明市场情绪与弹幕共识一致。"],
    )
    assert check_page(page) == []
    assert fix_speedcard(page, use_llm=False) == page


def test_items_issues_no_value():
    assert "no_value" in items_issues(["Winner 奇亚娜 10:56 被提及"])
    assert items_issues(["Winner 奇亚娜强抢 → 节奏优势确立，可能主导比赛（单源待验证）"]) == []
