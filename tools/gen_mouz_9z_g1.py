#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOUZ vs 9z G1 三节点修正页（2026-08-27，官方 20:00 CST 开赛）。
修正原因：此前登记 start_time 提前 30 分钟，切片混入开赛前等待期；
本组按官方窗口 20:00-20:51（北京）重切，阵容/地图走官方源。
"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


G1_BP = page(
    "BLAST Open Porto · MOUZ vs 9z · G1 BP 后/开局情报（修正）· 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图一 Cache",
    speed_block(
        "G1 进行中（修正窗口）· 图一 Cache",
        [("b-pend", "BP 后/开局 · 窗口已修正"), ("b-risk", "灰信号 9 条"), ("b-anchor", "观众质疑小蜜蜂（跨场）")],
        [
            sig("风险", "var(--bad)", '灰信号 9 条——"小蜜蜂故意去败者组"等（<b>跨场叙事，非本场指控</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", "图一 Cache（官方）；MOUZ 翻盘率话题（“老鼠得翻盘率最高”）→ 详 §3"),
            sig("盘口", "var(--good)", "Polymarket Map1 MOUZ 高概率（最终 99.95c）→ 详 §4"),
            sig("共识", "var(--purple)", "开局弹幕以跨场讨论为主（蜜蜂/猎鹰），本场信号稀疏 → 详 §5"),
        ],
        "本页为修正版（官方 20:00 开赛窗口 20:00-20:19）；G1 最终 MOUZ 13:4 拿下（Liquipedia/Polymarket）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>MOUZ</b> vs <b>9z</b> · BLAST Open Porto Group B · BO3</td></tr>
    <tr><td>节点</td><td>G1 · BP 后 / 开局（EARLY-GAME）· <b>窗口修正版</b>（官方 20:00 CST 开赛）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 20:00–20:19（北京时间）</td></tr>
    <tr><td>关键数据</td><td>2,193 条弹幕（CSBOY 官方主源）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123 + Liquipedia（时间/地图）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方开赛时间修正（此前提前 30 分钟混入等待期）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>9 条——多为跨场叙事（"小蜜蜂故意去败者组逮捕猎鹰"，指 Vitality 场次），非本场指控；有效本场灰信号 <b>低</b>。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图一 Cache</td><td>Liquipedia 官方（Cache 13:4）</td><td>MOUZ 拿下（13:4）</td></tr>
    <tr><td>MOUZ 翻盘率</td><td>"老鼠得翻盘率好像是最高得"（观众）</td><td>G1 未翻盘（MOUZ 直接拿下）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘；Polymarket Map1 MOUZ 最终 99.95c（MOUZ 13:4 拿下）。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>MOUZ · 图一</td><td>市场高概率 + 拿下</td><td>应验（13:4）</td></tr>
    <tr><td>灰信号</td><td>跨场（蜜蜂）</td><td>"故意去败者组"（Vitality 叙事）</td><td>非本场，不纳入本场统计</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：MOUZ 图一优势（市场一致）；</li><li><b>SHORT</b>：开局信号稀疏，G1 结果 MOUZ 13:4——9z 图一被压制；</li><li><b>观察点</b>：G2 地图（Nuke）与 9z 调整。</li></ul>"),
        ("7", "逐局复盘（G1 早期 · 证据层）", "<p>20:00-20:19（北京）：BP/开局；弹幕以跨场讨论为主，本场信号稀疏；MOUZ 开局压制。</p>"),
        ("8", "队伍 / 人员画像（证据层）", '<p>MOUZ：图一 Cache 压制（13:4）；9z：图一被压制。弹幕提及以跨场闲聊为主。</p>'),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Open Porto Group B：Cache 首图；MOUZ 图一强攻样本。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>MOUZ 图一市场高概率 → 兑现（13:4）。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（2,193 条，20:00-20:19 北京）；时间/地图：Liquipedia（20:00 CST、Cache）。<b>修正版</b>（此前窗口提前 30 分钟）。待官方核对：G1 阵容。</p>"""),
    ],
    "G1 BP 后节点（修正）2026-08-27 · 官方时间窗口 + 弹幕口径",
)


G1_MID = page(
    "BLAST Open Porto · MOUZ vs 9z · G1 局中情报（修正）· 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图一 Cache",
    speed_block(
        "G1 进行中（修正窗口）· 图一 Cache",
        [("b-pend", "局中 · 窗口已修正"), ("b-risk", "灰信号 16 条"), ("b-anchor", "观众\u201c剧本\u201d叙事")],
        [
            sig("风险", "var(--bad)", '灰信号 16 条——"商量剧本？？？""故意的搞人心态"（<b>非结论</b>），说明观众情绪化但无实锤 → 详 §2'),
            sig("锚点", "var(--accent)", "图一 Cache 局中；MOUZ 压制优势（最终 13:4）→ 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；Map1 总回合 17（13:4），预示碾压 → 详 §4"),
            sig("共识", "var(--purple)", "观众局中情绪化（剧本质疑），信号密度中等，说明情绪不作方向依据 → 详 §5"),
        ],
        "G1 局中 MOUZ 保持压制；灰信号 16 条为观众情绪（非实锤）；G1 最终 MOUZ 13:4。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G1 · 局中（MID-GAME）· <b>窗口修正版</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 20:15–20:39（北京时间）</td></tr>
    <tr><td>关键数据</td><td>1,904 条弹幕</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方开赛时间修正")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>16 条——"商量剧本？？？""故意的搞人心态呢，真贱啊"（观众情绪化质疑）；无盘口即时重合证据，非实锤。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", "<p>图一 Cache（官方）；MOUZ 局中压制（13:4 终局）。</p>"),
        ("4", "盘口与市场讨论", "<p>弹幕无数字盘；Map1 总回合 17（13:4，低回合碾压）。</p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>MOUZ · 图一</td><td>局中压制</td><td>应验（13:4）</td></tr>
    <tr><td>灰信号</td><td>情绪化（16 条）</td><td>“商量剧本”</td><td>兑现统计待回填（非实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：MOUZ 图一压制明确；</li><li><b>SHORT</b>：灰信号为情绪，不作方向依据；</li><li><b>观察点</b>：G2 Nuke。</li></ul>"),
        ("7", "逐局复盘（G1 局中 · 证据层）", "<p>20:15-20:39：MOUZ 压制（Cache 13:4 终局）；观众情绪化质疑（剧本叙事）。</p>"),
        ("8", "队伍 / 人员画像（证据层）", "<p>MOUZ：图一压制；9z：图一被压制（13:4）。</p>"),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>Cache 低回合碾压样本（13:4）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", "<p>MOUZ 压制 → 兑现（13:4）。</p>"),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（1,904 条，20:15-20:39 北京）。<b>修正版</b>。待官方核对：G1 阵容。</p>"""),
    ],
    "G1 局中节点（修正）2026-08-27 · 官方时间窗口 + 弹幕口径",
)


G1_END = page(
    "BLAST Open Porto · MOUZ vs 9z · G1 结束情报（修正）· 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图一 Cache 13:4",
    speed_block(
        "MOUZ 1-0 9z（G1 结束）",
        [("b-ok", "G1 结束 · 官方+市场仲裁"), ("b-ok", "灰信号 6 条"), ("b-anchor", "Cache 13:4 碾压")],
        [
            sig("风险", "var(--bad)", '灰信号 6 条——“完全上个blast的剧本”（<b>非结论</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", "图一 Cache 13:4（Liquipedia + Polymarket MOUZ 99.95c）→ 详 §3"),
            sig("盘口", "var(--good)", "Map1 MOUZ 99.95c、总回合 17 → 详 §4"),
            sig("共识", "var(--purple)", '“最伟大的翻盘”为反讽——9z 未翻盘，MOUZ 碾压 → 详 §5'),
        ],
        "G1 MOUZ 13:4 碾压 9z（Cache）；灰信号 6 条为情绪（非实锤）；系列 1-0。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>G1 结果</td><td><b>MOUZ 13:4 9z</b>（Liquipedia + Polymarket Map1 MOUZ 99.95c）</td></tr>
    <tr><td>节点</td><td>G1 · 结束（GAME-REVIEW）· <b>窗口修正版</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 20:38–20:51（北京时间）</td></tr>
    <tr><td>关键数据</td><td>1,388 条弹幕</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方", "窗口按官方开赛时间修正")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>6 条——"这nm完全上个blast的剧本啊，米人爆了蜜蜂跪了"（观众将本场与 BLAST 过往剧本对照）；非本场实锤指控。</p>'),
        ("3", "BP 锚点与选人情报（官方校准）", "<p>图一 Cache（官方）；MOUZ 13:4 碾压（低回合）。</p>"),
        ("4", "盘口与市场讨论", "<p>Polymarket Map1 MOUZ 99.95c、总回合 17（13:4）——与官方一致。</p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>MOUZ · 图一</td><td>碾压（13:4）</td><td>应验</td></tr>
    <tr><td>共识</td><td>“最伟大的翻盘”（反讽）</td><td>9z 未翻盘</td><td>未兑现（MOUZ 碾压）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", "<ul><li><b>LONG</b>：MOUZ 1-0；图一碾压（13:4）；</li><li><b>SHORT</b>：9z 图一被压制，G2 Nuke 是调整观察点；</li><li><b>观察点</b>：G2。</li></ul>"),
        ("7", "逐局复盘（G1 末段 · 证据层）", "<p>20:38-20:51：GG 刷屏；MOUZ 13:4 收下（Liquipedia/Polymarket 一致）。</p>"),
        ("8", "队伍 / 人员画像（证据层）", "<p>MOUZ：图一碾压；9z：图一惨败（13:4）。</p>"),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>Cache 低回合碾压样本；9z 图一强度不足。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", "<p>MOUZ 高概率 → 兑现（13:4）。</p>"),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（1,388 条，20:38-20:51 北京）；结果：Liquipedia + Polymarket。<b>修正版</b>。</p>"""),
    ],
    "G1 结束节点（修正）2026-08-27 · 官方窗口 + 弹幕口径",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_MOUZ-9z_2026-08-27_g1_bp.html", G1_BP),
        ("intel_danmu_MOUZ-9z_2026-08-27_g1_mid.html", G1_MID),
        ("intel_danmu_MOUZ-9z_2026-08-27_g1_end.html", G1_END),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)
