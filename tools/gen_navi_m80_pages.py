#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 NAVI vs M80（BLAST Open Porto · 2026-08-26）G1 局后复盘页。

触发背景：流水线 game_status 快照滞后（Map1 winner=null），g1_end 未自动触发；
本页由线上端本地快速生成补发（数据窗口 14:50–15:09 UTC，CSBOY 双房）。
"""

from __future__ import annotations

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


G1_END = page(
    "BLAST Open Porto · NAVI vs M80 · G1 结束情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一 Anubis（弹幕口径）· NAVI 胜",
    speed_block(
        "NAVI 1-0 M80（G1 结束）",
        [("b-ok", "G1 结束 · 市场仲裁"), ("b-ok", "灰信号 0 条"), ("b-anchor", "M80 自选图翻车")],
        [
            sig("风险", "var(--bad)", "灰信号 0 条——观众无假赛/剧本质疑；\u201cM80 花式送人头\u201d为操作批评，非指控 → 详 §2"),
            sig("锚点", "var(--accent)", 'M80 自选 Anubis（赛前\u201c长局制造机\u201d预期）被 NAVI 大比分带走，自选图翻车（"匪图一分不得"）→ 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；Map 1 市场口径：NAVI 99.95c、总回合 ≤18、净胜 ≥7（13-5/13-4 区间）→ 详 §4"),
            sig("共识", "var(--purple)", '观众批评 M80 送人头/干拉无补枪（"优势下包冲出去送""全是干拉"）→ 详 §5'),
        ],
        "G1 结果与市场一致（NAVI 大胜）；M80 自选图翻车 + 大量\u201c送\u201d批评是最大信号；G2 关注 M80 心态/BP 调整与 NAVI 延续性（系列 Under 2.5 市场方向 68c）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>NAVI（Natus Vincere）</b> vs <b>M80</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>G1 结果</td><td><b>NAVI 胜</b>（Polymarket Map 1 Winner NAVI 99.95c；总回合 ≤18、净胜 ≥7 → 13-5/13-4 区间；弹幕"匪图一分不得"印证 M80 T 侧零分；官方比分待核对）</td></tr>
    <tr><td>节点</td><td>G1 · 结束 / 局间（GAME-REVIEW）· 图一 Anubis（弹幕口径，官方待核对）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 14:50–15:09 UTC（北京 22:50–23:09）</td></tr>
    <tr><td>关键数据</td><td>1,649 条弹幕 · 669 活跃用户 · 密度 82.6 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点未采（G1 期间整体覆盖不足，显式标注，VOD 可回捞）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>本节点 <b>0 条</b>。观众无假赛/剧本质疑；"M80搁这花式送人头呢"为操作/心态批评，非指控。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>M80 自选 Anubis</td><td>赛前被称\u201c长局制造机\u201d（对 FNC 超长局/最长加时）</td><td><b>未兑现</b>——被大比分带走（自选图翻车样本）</td></tr>
    <tr><td>M80 T 侧</td><td>"匪图一分不得"（15:07）</td><td>观众口径：T 侧零分（官方待核对）</td></tr>
    <tr><td>翻盘互搏</td><td>"这俩哥们谁赢手枪都翻可还行"（15:03）· "又翻好了这下压力来到m80"（15:06）</td><td>过程样本：双方轮流反扑</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Map 1 市场口径（可核验）：Map 1 Winner NAVI 99.95c、-3.5 让分 ✓、-6.5 接近结算（90c）、总回合 O/U 21.5 Under ✓、18.5 Under 倾向 → <b>13-5/13-4 区间</b>。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NAVI · 图一</td><td>大比分拿下（市场 + 观众"GG"共识）</td><td>应验（NAVI 胜）</td></tr>
    <tr><td>负锚</td><td>M80 · 自选图/执行</td><td>"优势下包冲出去送" · "全是干拉，没有补枪啊" · "大比分，哪位数据这么差"</td><td>过程兑现（自选图翻车）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>本节点 0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：G1 结论明确（NAVI 1-0，市场一致）；NAVI 状态优于赛前\u201c状态差\u201d叙事预期；</li>
    <li><b>SHORT</b>：M80\u201c送\u201d模式 + 自选图翻车是 G2 关键观察；若 NAVI 延续可 2-0（系列 Under 2.5 市场 68c 方向）；</li>
    <li><b>观察点</b>：G2 BP（M80 是否调整）、NAVI 延续性、官方比分/MVP。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>14:50–15:01</td><td>M80 落后挣扎："枪法不行。脑子还不行。GG"（15:01）· "大比分，哪位数据这么差"</td></tr>
    <tr><td>15:02–15:06</td><td>双方互翻："翻！""m80给我翻""又翻好了这下压力来到m80"——\u201c谁赢手枪都翻\u201d乱局</td></tr>
    <tr><td>15:07–15:08</td><td>GG 刷屏 + "匪图一分不得"；15:07 密度峰值 168（"全是干拉，没有补枪啊"）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI 全队</td><td>提及 46；正 3 / 负 4——赢下图一，wdf 局中高光延续</td></tr>
    <tr><td>M80</td><td>批评集中："搁这花式送人头" · "优势下包冲出去送" · "全是干拉"</td></tr>
    <tr><td>donk（跨场）</td><td>提及 13——Spirit 相关闲聊，非本场信号（明确标注）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>BLAST Open Porto 小组赛 BO3；M80×Anubis 自选图翻车样本；</li>
    <li>\u201c谁赢手枪都翻\u201d——低质量互翻乱局样本（双方执行力波动大）；</li>
    <li>观众高要求：自选图被大比分带走即被批\u201c送人头\u201d。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>G1 BP 节点</td><td>"NAVI 状态差成局内底色"（赛前叙事）</td><td>未兑现为败局——NAVI 大胜（状态差叙事修正）</td></tr>
    <tr><td>赛前</td><td>M80 自选 Anubis = 长局制造机</td><td>未兑现（速败，自选图翻车）</td></tr>
    <tr><td>15:02–15:06</td><td>"翻！/给我翻"（M80 反扑预期）</td><td>过程部分出现，终局未兑现</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 1,649 条，窗口 14:50–15:09 UTC）；BLAST 官方 660729 本节点未采（缺口，VOD 可回捞）。结果仲裁：Polymarket Map 1 Winner（NAVI 99.95c）+ 总回合/让分市场交叉；弹幕比分作过程佐证。来源标签：本场弹幕（核心）/ 前局延续（§7）/ 市场口径（§4）。待官方核对：图一比分、MVP。</p>"""),
    ],
    "G1 结束节点 2026-08-26 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_Natus Vincere-M80_2026-08-26_g1_end.html"
    out.write_text(G1_END, encoding="utf-8")
    print("wrote", out)


G2_BP = page(
    "BLAST Open Porto · NAVI vs M80 · G2 BP 后/开局情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二 米垃圾（Mirage，弹幕口径）",
    speed_block(
        "G2 进行中 · 图二 米垃圾",
        [("b-pend", "BP 后/开局节点"), ("b-ok", "灰信号 0 条"), ("b-anchor", "NAVI 自选图二叙事")],
        [
            sig("风险", "var(--bad)", "灰信号 0 条——观众无假赛/剧本质疑；\u201cNAVI 图二老输\u201d为历史玩梗，非指控 → 详 §2"),
            sig("锚点", "var(--accent)", '图二米垃圾（"打米垃圾啊"15:24）；观众点出"navi经典输图二自选图" → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；Map 2 市场 NAVI 领先（约 70c）→ 详 §4"),
            sig("共识", "var(--purple)", '观众吐槽 NAVI 图二执行力（"枪械优势，进攻磨磨唧唧"）→ 详 §5'),
        ],
        "G2 米垃圾开局胶着；\u201cNAVI 自选图二经典翻车\u201d是情绪底色，关注 NAVI 是否延续 G1 状态、M80 能否咬住（系列 Under 2.5 方向仍有利）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>NAVI（Natus Vincere）</b> vs <b>M80</b> · BLAST Open Porto Group A · BO3（系列 1-0）</td></tr>
    <tr><td>节点</td><td>G2 · BP 后 / 开局（EARLY-GAME）· 图二 米垃圾（Mirage，弹幕口径，官方待核对）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 15:20–15:40 UTC（北京 23:20–23:40）</td></tr>
    <tr><td>关键数据</td><td>1,123 条弹幕 · 530 活跃用户 · 密度 63.1 条/分</td></tr>
    <tr><td>状态</td><td>本节点为进行中快照；G2 最终结果见 G2 结束节点（Polymarket 仲裁）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点未采（显式标注，VOD 可回捞）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>本节点 <b>0 条</b>。观众无假赛/剧本质疑；"navi经典输图二自选图""辣味永远不赢图二"为历史玩梗，非指控。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图二确认</td><td>"打米垃圾啊"（15:24）→ 图二 = 米垃圾（Mirage，弹幕口径）</td><td>—</td></tr>
    <tr><td>NAVI 自选图二叙事</td><td>"速通不了navi经典输图二自选图"（观众玩梗）</td><td>过程观察（开局胶着）</td></tr>
    <tr><td>开局执行</td><td>"枪械优势，进攻磨磨唧唧" · "我不知道人数优势他们在急什么" · "纯e翻盘？"</td><td>过程样本：执行力受批</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Map 2 Winner NAVI 领先（约 70c，G2 进行中）；系列 Under 2.5 方向仍有利。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NAVI · G2</td><td>系列 1-0 领先 + 市场领先（约 70c）</td><td>待 G2 结束回填</td></tr>
    <tr><td>负锚（叙事）</td><td>NAVI × 图二</td><td>"navi经典输图二自选图" · "辣味永远不赢图二"（观众玩梗）</td><td>过程观察（开局胶着）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>本节点 0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：NAVI 系列 1-0、G2 市场领先，方向未变；</li>
    <li><b>SHORT</b>：\u201c图二老输\u201d叙事是最大情绪变量——若 M80 咬住/翻盘，叙事将强化；关注 NAVI 执行力；</li>
    <li><b>观察点</b>：G2 中段节奏、M80 调整、Map 2 结算。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>15:23–15:27</td><td>图二开始（"打米垃圾啊"）；观众点出 NAVI 自选图二历史叙事</td></tr>
    <tr><td>15:30–15:34</td><td>开局胶着；15:34 密度峰值 177："辣味永远不赢图二"（NAVI 图二玩梗）</td></tr>
    <tr><td>15:35+</td><td>"枪械优势，进攻磨磨唧唧"——执行力批评延续</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI 全队</td><td>提及 40；正 4 / 负 2——图二开局情绪混合（"经典输图二"叙事）</td></tr>
    <tr><td>M80</td><td>本节点提及少；观众关注其能否调整（"纯e翻盘？"）</td></tr>
    <tr><td>donk（跨场）</td><td>提及 25——Spirit 相关闲聊，非本场信号（明确标注）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>BLAST Open Porto 小组赛 BO3；NAVI\u201c图二自选图翻车\u201d叙事为观众历史口径，本场待验证；</li>
    <li>米垃圾 = 常见图池；开局执行力批评（磨叽/不集合）为过程样本。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>15:24</td><td>"打米垃圾啊"（图二确认）</td><td>图二 = 米垃圾（弹幕口径）</td></tr>
    <tr><td>15:2x</td><td>"navi经典输图二自选图"（历史叙事）</td><td>待 G2 结束回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 1,123 条，窗口 15:20–15:40 UTC）；BLAST 官方 660729 本节点未采（缺口，VOD 可回捞）。来源标签：本场弹幕（核心）/ 历史画像（§3/§9 标注）/ 市场口径（§4）。待官方核对：图二地图名。</p>"""),
    ],
    "G2 BP 后/开局节点 2026-08-26 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_Natus Vincere-M80_2026-08-26_g1_end.html", G1_END),
        ("intel_danmu_Natus Vincere-M80_2026-08-26_g2_bp.html", G2_BP),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)
