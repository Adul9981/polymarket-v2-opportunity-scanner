#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOUZ vs 9z G2 结束 + 整场复盘（2026-08-27，MOUZ 2-0，官方窗口）。"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


G2_END = page(
    "BLAST Open Porto · MOUZ vs 9z · G2 结束情报 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图二 Nuke 13:7",
    speed_block(
        "MOUZ 2-0 9z（G2 结束）",
        [("b-ok", "系列结束 · 官方+市场仲裁"), ("b-ok", "灰信号 7 条（玩梗）"), ("b-anchor", "Nuke 13:7 收官")],
        [
            sig("风险", "var(--bad)", "灰信号 7 条（观众玩梗，非指控）——<b>非结论</b>，说明无实锤 → 详 §2"),
            sig("锚点", "var(--accent)", "图二 Nuke 13:7（Liquipedia + Polymarket MOUZ 99.95c），优势收官 → 详 §3"),
            sig("盘口", "var(--good)", "Map2 MOUZ 99.95c、总回合 20（13:7），预示 2-0 → 详 §4"),
            sig("共识", "var(--purple)", '“9z真的菜啊”"神人9z"——9z 表现被批，看衰方向应验 → 详 §5'),
        ],
        "MOUZ 2-0 9z（Cache 13:4 + Nuke 13:7）；9z 两图被压制；系列结束，MOUZ 晋级方向。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>MOUZ 2-0 9z</b>（Liquipedia finished=true + Polymarket Map1/2 MOUZ 99.95c、Under 2.5）</td></tr>
    <tr><td>逐图</td><td>图一 Cache <b>13:4</b>（17 回合）· 图二 Nuke <b>13:7</b>（20 回合）</td></tr>
    <tr><td>节点</td><td>G2 · 结束（GAME-REVIEW）· <b>窗口修正版</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 21:20–21:39（北京时间）</td></tr>
    <tr><td>关键数据</td><td>2,222 条弹幕（CSBOY 主源）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123 + Liquipedia + Polymarket", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方开赛时间（20:00 CST）修正")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>7 条——“if主队路边，其他队夺冠printf没含金量”（观众玩梗，非本场假赛指控）；有效灰信号 <b>低</b>。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", "<p>图二 Nuke（官方）；MOUZ 13:7 收官（20 回合）。</p>"),
        ("4", "盘口与市场讨论", "<p>Polymarket Map2 MOUZ 99.95c、总回合 20（13:7）；系列 Under 2.5（2-0）。</p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>MOUZ · 系列</td><td>两图压制（13:4 / 13:7）</td><td>应验（2-0）</td></tr>
    <tr><td>负锚</td><td>9z · 表现</td><td>“9z真的菜啊”（观众批评）</td><td>应验方向（9z 两图败）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：MOUZ 2-0（市场一致）；9z 两图强度不足；</li><li><b>SHORT</b>：9z 大匪图（Nuke）仍 13:7 败——图池短板；</li><li><b>观察点</b>：官方 MVP、MOUZ 后续。</li></ul>"),
        ("7", "逐局复盘（G2 末段 · 证据层）", "<p>21:20-21:39：G2 收尾（9z 被批“神人9z”）；13:34-37 高密度 GG；MOUZ 13:7 收官。</p>"),
        ("8", "队伍 / 人员画像（证据层）", "<p>MOUZ：两图压制；9z：Nuke 大匪图仍败（13:7），被观众批评。</p>"),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Open Porto Group B：MOUZ 2-0 横扫样本；9z Nuke 短板。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", "<p>MOUZ 系列高概率 → 兑现（2-0）。</p>"),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（2,222 条，21:20-21:39 北京）；结果：Liquipedia + Polymarket。<b>窗口修正版</b>。待官方核对：G2 阵容。</p>"""),
    ],
    "G2 结束节点 2026-08-27 · 官方窗口 + 弹幕口径",
)


FULL = page(
    "BLAST Open Porto · MOUZ vs 9z · 整场复盘 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · MOUZ 2-0 9z",
    speed_block(
        "MOUZ 2-0 9z",
        [("b-ok", "系列结束 · 官方+市场仲裁"), ("b-ok", "灰信号 7 条（玩梗）"), ("b-anchor", "Cache 13:4 + Nuke 13:7")],
        [
            sig("风险", "var(--bad)", "灰信号 7 条（观众玩梗，非指控）——<b>非结论</b>，说明无实锤 → 详 §2"),
            sig("锚点", "var(--accent)", "MOUZ 两图压制（Cache 13:4 / Nuke 13:7），优势明确 → 详 §3"),
            sig("盘口", "var(--good)", "Polymarket：Map1/2 MOUZ 99.95c、Under 2.5，方向一致 → 详 §4"),
            sig("共识", "var(--purple)", "9z 两图被压制（“神人9z”），看衰方向应验 → 详 §5"),
        ],
        "MOUZ 2-0 9z（官方 Liquipedia + Polymarket 仲裁）；9z 图池/强度短板显现；本场开局时间按官方 20:00 CST 修正。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>MOUZ 2-0 9z</b>（Liquipedia finished + Polymarket：Map1/2 MOUZ 99.95c、Under 2.5）</td></tr>
    <tr><td>逐图</td><td>图一 Cache <b>13:4</b> · 图二 Nuke <b>13:7</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 20:00–21:39（北京时间，官方开赛 20:00）</td></tr>
    <tr><td>关键数据</td><td>多源弹幕 + Liquipedia/Polymarket 官方仲裁</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123 + Liquipedia + Polymarket", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "开局时间按官方修正（此前登记提前 30 分钟）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>约 7 条（观众玩梗“if主队路边"），非本场假赛指控；有效灰信号 <b>低</b>。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", "<p>图一 Cache 13:4（17 回合）· 图二 Nuke 13:7（20 回合）——MOUZ 两图压制。</p>"),
        ("4", "盘口与市场讨论", "<p>Polymarket：Map1/2 MOUZ 99.95c、系列 Under 2.5、总回合 17/20——与官方一致。</p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>MOUZ · 系列</td><td>两图压制</td><td>应验（2-0）</td></tr>
    <tr><td>负锚</td><td>9z · 图池/强度</td><td>“9z真的菜啊” · 大匪图 Nuke 仍败</td><td>应验方向</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：MOUZ 2-0（市场一致）；9z 图池短板；</li><li><b>SHORT</b>：9z 强度不足（两图 11 回合合计）——后续遇强队参考有限；</li><li><b>观察点</b>：官方 MVP、MOUZ 晋级路径。</li></ul>"),
        ("7", "逐局复盘（证据层）", "<p>G1 Cache 13:4（MOUZ 碾压）→ G2 Nuke 13:7（MOUZ 收官）——2-0 横扫。</p>"),
        ("8", "队伍 / 人员画像（证据层）", "<p>MOUZ：两图压制；9z：强度/图池短板（被观众批评）。</p>"),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Open Porto Group B 横扫样本；9z Nuke 短板。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", "<p>MOUZ 系列高概率 → 兑现（2-0）。</p>"),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（多节点）；结果：Liquipedia + Polymarket。<b>开局时间按官方修正</b>（20:00 CST）。待官方核对：两图阵容、MVP。</p>"""),
    ],
    "整场复盘 2026-08-27 · 官方仲裁 + 弹幕口径",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_MOUZ-9z_2026-08-27_g2_end.html", G2_END),
        ("intel_danmu_MOUZ-9z_2026-08-27.html", FULL),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)
