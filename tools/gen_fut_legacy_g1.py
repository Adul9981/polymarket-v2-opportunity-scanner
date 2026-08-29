#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FUT vs Legacy G1 节点（2026-08-27，22:30 CST 开赛，图一 Ancient）。"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


G1_BP = page(
    "BLAST Open Porto · FUT vs Legacy · G1 BP 后/开局情报 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图一 Ancient（遗迹）",
    speed_block(
        "G1 进行中 · 图一 Ancient",
        [("b-pend", "BP 后/开局节点"), ("b-ok", "灰信号低"), ("b-anchor", "FUT 状态好（枪法硬）+ 换人话题")],
        [
            sig("风险", "var(--bad)", "灰信号低（观众玩梗为主）；FUT 刚丢冠军——心态是变量 → 详 §2"),
            sig("锚点", "var(--accent)", "图一 Ancient（遗迹）；FUT 状态好（\u201cfut牛逼啊进化了\u201d\u201c这枪法真猛\u201d）；FUT 有换人话题 → 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；观众普遍看好 FUT（\u201cfut实力打猎鹰跟打儿子\u201d等）→ 详 §4"),
            sig("共识", "var(--purple)", "观众共识：FUT 状态/枪法优于 Legacy（\u201c菊花这图被暴打\u201d）；Legacy 被玩梗 → 详 §5"),
        ],
        "FUT vs Legacy 22:30 CST 开赛，图一 Ancient；观众共识 FUT 状态好（枪法硬/进化）、Legacy 图一被压制；FUT 刚丢冠军+阵容换人是变量。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>FUT</b> vs <b>Legacy</b> · BLAST Open Porto Group B · BO3</td></tr>
    <tr><td>节点</td><td>G1 · BP 后 / 开局（EARLY-GAME）· 官方 22:30 CST 开赛</td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 22:28–22:47（北京时间）</td></tr>
    <tr><td>关键数据</td><td>1,344 条弹幕（CSBOY 主源）· 观众参与度高（猎鹰叙事刷屏）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123 + Liquipedia（时间/地图）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方 22:30 CST 开赛修正（此前登记 22:00）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>灰信号低（1 条"剧本"模糊，不计有效）。主要风险是 FUT 刚丢冠军的心态变量（观众多次提及，非指控）。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图一 Ancient</td><td>弹幕"图一遗迹"（22:30 北京时间）</td><td>官方地图待核对（Liquipedia 图序 Ancient）</td></tr>
    <tr><td>FUT 换人</td><td>"提问fut被换的是谁 换来的是谁"（观众问）· "狙击手换了？"</td><td>阵容变化待官方核对</td></tr>
    <tr><td>FUT 狙击手</td><td>"fut的狙击手好像不太灵" · "这队就不刚需狙击枪，打补枪就行"</td><td>狙击手角色讨论（补枪流）</td></tr>
    <tr><td>FUT 沙二历史</td><td>"fut沙二干过巅峰小蜜蜂"（历史）</td><td>非本图，图池背景</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>观众普遍看好 FUT（"fut实力打猎鹰不是跟打儿子一样吗"——预期叙事）。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FUT · 状态</td><td>"fut牛逼啊进化了" · "这枪法真猛啊" · "fut枪很硬呀"</td><td>G1 开局 FUT 优势（弹幕口径）</td></tr>
    <tr><td>负锚</td><td>Legacy · 图一</td><td>"菊花这图被暴打" · "混完了菊花"</td><td>Legacy 图一被压制（待回填）</td></tr>
    <tr><td>变量</td><td>FUT · 心态/阵容</td><td>"fut刚丢了冠军，心态会不会受影响" · 换人话题</td><td>待官方/后续验证</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FUT 状态好（枪法硬/进化），观众共识优于 Legacy；</li>
    <li><b>SHORT</b>：FUT 刚丢冠军的心态、阵容换人、狙击手角色是变量；Legacy（菊花）有"也不差"反方声音；</li>
    <li><b>观察点</b>：G1 中段比分、FUT 换人/狙击手官方信息。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>22:28–22:35</td><td>BP：图一遗迹确认；观众玩梗（"猎鹰严父选拔赛"· "争夺猎鹰抚养权"）；FUT 换人/狙击手话题</td></tr>
    <tr><td>22:36–22:47</td><td>开局：FUT 状态好（"进化了""枪法真猛"）；Legacy 被批（"这图被暴打"）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FUT</td><td>状态好（"进化了""枪很硬"）；刚丢冠军（心态变量）；有换人话题；狙击手角色讨论（补枪流）</td></tr>
    <tr><td>Legacy（菊花）</td><td>图一被暴打（"混完了菊花"）；"也不差"反方；观众想"看菊花打猎鹰"（叙事）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Open Porto Group B：Ancient 首图；FUT 补枪流（不刚需狙击）风格样本；观众\u201c猎鹰严父\u201d叙事。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>观众普遍看好 FUT → G1 <b>Legacy 13-10 胜（未兑现）</b>（Liquipedia 官方比分，弹幕口径被打脸）。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（1,344 条，22:28-22:47 北京）；时间：Liquipedia（22:30 CST）。<b>窗口修正版</b>。待官方核对：图一地图、FUT 换人/阵容、狙击手。</p>"""),
    ],
    "G1 BP 后节点 2026-08-27 · 官方时间窗口 + 弹幕口径",
)


G1_MID = page(
    "BLAST Open Porto · FUT vs Legacy · G1 局中情报 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图一 Ancient",
    speed_block(
        "G1 进行中 · 图一 Ancient",
        [("b-pend", "局中节点"), ("b-ok", "灰信号低"), ("b-anchor", "FUT 优势 + Legacy 被压制")],
        [
            sig("风险", "var(--bad)", "灰信号低（观众玩梗为主）——<b>非结论</b> → 详 §2"),
            sig("锚点", "var(--accent)", "G1 局中 FUT 优势：\u201cfut牛逼啊进化了\u201d\u201c这枪法真猛\u201d；Legacy 被批\u201c菊花这图被暴打\u201d → 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；观众叙事看好 FUT → 详 §4"),
            sig("共识", "var(--purple)", "观众玩梗：\u201cFUT 和菊花争夺猎鹰抚养权\u201d——谁赢谁打猎鹰 → 详 §5"),
        ],
        "G1 局中 FUT 状态好、Legacy 图一被压制（弹幕口径）；FUT 刚丢冠军+换人是变量；观众普遍预期 FUT 拿下并\u201c打猎鹰\u201d。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G1 · 局中（MID-GAME）· 官方 22:30 CST 开赛</td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 22:44–23:00（北京时间）</td></tr>
    <tr><td>关键数据</td><td>多源弹幕（CSBOY 主源）· 观众对 FUT/猎鹰叙事密集</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方开赛时间修正")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>灰信号低（观众玩梗为主："猎鹰抚养权"等），非本场实锤指控。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>FUT 状态</td><td>"fut牛逼啊进化了" · "这枪法真猛啊" · "fut枪很硬呀"</td><td>G1 局中 FUT 优势（弹幕口径）</td></tr>
    <tr><td>Legacy 表现</td><td>"菊花这图被暴打" · "混完了菊花" · "菊花运队"</td><td>Legacy 图一被压制</td></tr>
    <tr><td>FUT 换人</td><td>"提问fut被换的是谁 换来的是谁" · "狙击手换了？"</td><td>阵容变化待官方核对</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>观众叙事：FUT 实力被高看（"打猎鹰跟打儿子"），且赢者将\u201c获得猎鹰抚养权\u201d（玩梗）。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FUT · 局中</td><td>"进化了""枪法真猛"（状态好）</td><td>G1 优势（待回填）</td></tr>
    <tr><td>负锚</td><td>Legacy · 图一</td><td>"被暴打""混完了"</td><td>被压制（待回填）</td></tr>
    <tr><td>叙事</td><td>谁赢谁打猎鹰</td><td>"争夺猎鹰抚养权"（观众玩梗）</td><td>非方向信号</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：FUT 局中优势（弹幕口径）；<b>SHORT</b>：FUT 心态（刚丢冠军）/换人/狙击手是变量；<b>观察点</b>：G1 比分、FUT 换人官方信息。</li></ul>"),
        ("7", "逐局复盘（G1 局中 · 证据层）", "<p>22:44-23:00：FUT 状态好（观众多次肯定枪法）；Legacy 被批（图一被暴打）；观众叙事集中在\u201c谁赢谁打猎鹰\u201d。</p>"),
        ("8", "队伍 / 人员画像（证据层）", "<p>FUT：状态好/枪法硬/进化；换人+刚丢冠军变量；Legacy：图一被压制（观众批评）。</p>"),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>FUT 补枪流（不刚需狙击）风格样本；Ancient 首图。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>观众看好 FUT → G1 <b>Legacy 13-10 胜（未兑现）</b>（Liquipedia 官方比分，弹幕口径被打脸）。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（局中窗口，22:44-23:00 北京）。<b>窗口修正版</b>。待官方核对：比分、FUT 换人/阵容。</p>"""),
    ],
    "G1 局中节点 2026-08-27 · 官方时间窗口 + 弹幕口径",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_FUT-Legacy_2026-08-27_g1_bp.html", G1_BP),
        ("intel_danmu_FUT-Legacy_2026-08-27_g1_mid.html", G1_MID),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)
