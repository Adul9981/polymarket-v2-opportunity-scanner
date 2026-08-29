#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量补齐 2026-08-26 缺失节点情报页（事后回补，标注来源）。

覆盖：
  FURIA 2-0 paiN：g1_bp/g1_mid/g1_end + g2_bp/g2_mid/g2_end + 整场
  M80 2-1 NAVI：g3_bp/g3_mid/g3_end + 整场
数据：CSBOY 虎牙主源重切（剔除 KICK 广告噪音），Polymarket 结算仲裁。
"""

from __future__ import annotations

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


def w(name: str, html: str) -> None:
    (REPORTS / name).write_text(html, encoding="utf-8")
    print("wrote", name)


# ---------------------------------------------------------------- FURIA G1 BP

FURIA_G1_BP = page(
    "BLAST Open Porto · FURIA vs paiN · G1 BP 后/开局情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一（弹幕口径，官方待核对）",
    speed_block(
        "G1 进行中（回补快照）· 图一",
        [("b-pend", "BP 后/开局 · 事后回补"), ("b-ok", "灰信号 0 条"), ("b-anchor", "paiN 被看低")],
        [
            sig("风险", "var(--bad)", "灰信号 0 条——观众无假赛/剧本质疑，说明开局情绪干净 → 详 §2"),
            sig("锚点", "var(--accent)", '观众将 paiN 定义为弱旅（"pain都打不过天禄"）；FURIA 被要求碾压，优势预期明确 → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；图一市场方向 FURIA 大胜，预示碾压 → 详 §4"),
            sig("共识", "var(--purple)", '"黑豹没有输的角度"——FURIA 一边倒预期，看好 FURIA 兑现 → 详 §5'),
        ],
        "图一 BP 后观众一边倒看好 FURIA；结果印证（13-2 碾压）。paiN 的\u201c弱旅\u201d定位是全系列底色。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>FURIA（黑豹）</b> vs <b>paiN</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>节点</td><td>G1 · BP 后 / 开局（EARLY-GAME）· <b>事后回补</b>（流水线当时未产出）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 17:50–18:09 UTC（北京 08-27 01:50–02:09）</td></tr>
    <tr><td>关键数据</td><td>987 条弹幕 · 404 活跃用户 · 密度 49.7 条/分（CSBOY 虎牙主源）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入（KICK 广告噪音高，主源可覆盖）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", "<p>本节点 <b>0 条</b>。</p>"),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>paiN 定位</td><td>"pain都打不过天禄的" · "黑豹没有输的角度啊"</td><td>图一 FURIA 13-2 碾压（应验）</td></tr>
    <tr><td>FURIA 状态</td><td>"furia状态不是特别好吧"（个别反方）· "黑豹状态也一般，还疲惫"</td><td>过程有反方声音，结果仍碾压</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>弹幕无明确数字盘。<b>样本不足。</b>图一市场结算口径：FURIA 大胜（净胜 ≥9、总回合 ≤15 → 13-2 区间，见整场页）。</p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 图一</td><td>"黑豹没有输的角度"（一边倒）</td><td>应验（13-2）</td></tr>
    <tr><td>负锚</td><td>paiN · 实力</td><td>"pain都打不过天禄"</td><td>应验方向（paiN 惨败）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 一边倒预期，图一结果印证；</li>
    <li><b>SHORT</b>：paiN 弱旅定位下，系列 2-0（Under 2.5）是主流预期；</li>
    <li><b>观察点</b>：图二 FURIA 延续性、paiN 能否拿分。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>17:50–17:55</td><td>BP 讨论（"出图了，图一黑豹选的"）· 观众闲聊其他场次（NAVI 翻车话题）</td></tr>
    <tr><td>17:55–18:09</td><td>开局；观众预期 FURIA 碾压（"黑豹没有输的角度"）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 33；观众普遍看好（"黑豹没有输的角度"）</td></tr>
    <tr><td>paiN</td><td>被定义为弱旅（"打不过天禄"）；nqz 离队话题（"nqz走了影响pain了吧"）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Open Porto 小组赛 BO3；观众对南美队伍\u201c弱旅碾压\u201d预期明确。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>17:5x</td><td>"黑豹没有输的角度"（FURIA 一边倒）</td><td>兑现（13-2）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 987 条，窗口 17:50–18:09 UTC）。本页为<b>赛后回补</b>（流水线当时未产出，基于整场弹幕按时间窗切出）。结果仲裁：Polymarket Map 1（FURIA 99.95c+ 结算）。来源标签：本场弹幕（核心）/ 历史画像（§3/§9 标注）。待官方核对：图一地图名。</p>"""),
    ],
    "G1 BP 后节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- FURIA G1 MID

FURIA_G1_MID = page(
    "BLAST Open Porto · FURIA vs paiN · G1 局中情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一",
    speed_block(
        "G1 进行中（回补快照）· 图一",
        [("b-pend", "局中 · 事后回补"), ("b-ok", "灰信号 1 条（模糊）"), ("b-anchor", "经济碾压")],
        [
            sig("风险", "var(--bad)", "灰信号 1 条（\u201c想去找买了否冷\u201d，语境模糊）——<b>观众质疑，非结论</b> → 详 §2"),
            sig("锚点", "var(--accent)", '"全是钱 无敌经济""麦乐迪大狙能玩到结束了这经济"——FURIA 经济/火力碾压 → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；样本不足 → 详 §4"),
            sig("共识", "var(--purple)", "观众对 paiN 翻盘不抱期望（\u201c大CT图 0分都能翻\u201d反讽）→ 详 §5"),
        ],
        "图一 FURIA 经济与火力全面碾压（13-2 收尾），paiN 局中毫无还手之力；\u201c0 分翻盘\u201d为反讽，未出现。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G1 · 局中（MID-GAME）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 18:05–18:29 UTC（北京 02:05–02:29）</td></tr>
    <tr><td>关键数据</td><td>1,263 条弹幕 · 456 活跃用户 · 密度 50.7 条/分（CSBOY 虎牙主源）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入（KICK 广告噪音高）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>1 条（模糊）："想去找买了否冷"——语境不明，不构成有效指控；其余"买了"类为玩梗。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>FURIA 经济/火力</td><td>"全是钱 无敌经济" · "麦乐迪大狙能玩到结束了这经济"</td><td>图一 13-2 碾压（应验）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>无明确数字盘提及。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 图一</td><td>经济/火力碾压（"无敌经济"）</td><td>应验（13-2）</td></tr>
    <tr><td>共识</td><td>paiN 翻盘无望</td><td>"大CT图 0分都能翻"（反讽）</td><td>未出现翻盘</td></tr>
    <tr><td>灰信号</td><td>—</td><td>1 条模糊，不计有效</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 碾压态势明确，图一无悬念；</li>
    <li><b>SHORT</b>：paiN 局中毫无抵抗 → 系列 2-0 预期强化（最终兑现）；</li>
    <li><b>观察点</b>：图二 paiN 能否调整。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 局中 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>18:05–18:20</td><td>FURIA 经济/火力碾压（"全是钱 无敌经济"）；观众闲聊 NAVI 翻车（跨场）</td></tr>
    <tr><td>18:21–18:29</td><td>"图一就一分 不用想了"——paiN 图一仅 1-2 分；"这图0分都能翻"反讽</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 35；火力/经济碾压（"麦乐迪大狙"）</td></tr>
    <tr><td>paiN</td><td>图一仅 1-2 分（"图一就一分"）——毫无还手</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>弱旅碾压局特征：经济差被反复点名（无敌经济/没经济别送）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>18:2x</td><td>"图一就一分 不用想了"</td><td>兑现（paiN 图一 2 分）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 1,263 条，窗口 18:05–18:29 UTC）。<b>赛后回补</b>。来源标签：本场弹幕（核心）。待官方核对：图一地图名。</p>"""),
    ],
    "G1 局中节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


if __name__ == "__main__":
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_bp.html", FURIA_G1_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_mid.html", FURIA_G1_MID)


# ---------------------------------------------------------------- FURIA G1 END

FURIA_G1_END = page(
    "BLAST Open Porto · FURIA vs paiN · G1 结束情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一 13-2（FURIA 胜）",
    speed_block(
        "FURIA 1-0 paiN（G1 结束）",
        [("b-ok", "G1 结束 · 市场仲裁"), ("b-ok", "灰信号 0 条"), ("b-anchor", "图一 13-2 碾压")],
        [
            sig("风险", "var(--bad)", "灰信号 0 条——无有效质疑，说明无假赛情绪 → 详 §2"),
            sig("锚点", "var(--accent)", '"图一就一分 不用想了"应验——图一 FURIA 13-2（paiN 仅 2 分），碾压优势兑现 → 详 §3'),
            sig("盘口", "var(--good)", "图一市场口径：FURIA 净胜 ≥9、总回合 ≤15，与 13-2 一致 → 详 §4"),
            sig("共识", "var(--purple)", '"史上第二伟大的翻盘即将来领"为反讽——paiN 未翻盘，看好方向应验 → 详 §5'),
        ],
        "G1 无悬念（13-2）；paiN 弱旅定位完全兑现。系列 2-0（Under 2.5）预期进入图二。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>G1 结果</td><td><b>FURIA 13-2 paiN</b>（Polymarket Map 1 FURIA 结算 + 弹幕"2分？赢了11分？"印证）</td></tr>
    <tr><td>节点</td><td>G1 · 结束 / 局间（GAME-REVIEW）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 18:25–18:39 UTC（北京 02:25–02:39）</td></tr>
    <tr><td>关键数据</td><td>735 条弹幕 · 310 活跃用户 · 密度 49.2 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", "<p><b>0 条</b>有效灰信号。</p>"),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>paiN 图一得分</td><td>"图一就一分 不用想了" · "2分？赢了11分？"</td><td>13-2（paiN 2 分，观众口径吻合）</td></tr>
    <tr><td>翻盘预期</td><td>"大CT图 0分都能翻" · "史上第二伟大的翻盘即将来领"（反讽）</td><td>未翻盘（反讽未兑现）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无数字盘。Polymarket 图一口径：FURIA -9.5 过 ✓ / -12.5 未过 ✗ → 净胜 10–12；总回合 O/U 15.5 Under ✓ → 13-1/13-2；弹幕"2分"锁定 <b>13-2</b>。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 图一</td><td>"黑豹没有输的角度"</td><td>应验（13-2）</td></tr>
    <tr><td>负锚</td><td>paiN · 图一</td><td>"图一就一分"（弱旅定位）</td><td>应验（2 分）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 1-0，碾压态势；</li>
    <li><b>SHORT</b>：paiN 图一仅 2 分 → 图二若仍无调整，2-0 收官（最终兑现）；</li>
    <li><b>观察点</b>：图二地图与 paiN 调整。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>18:25–18:29</td><td>"这图0分都能翻"反讽 · "翻给我看来"（观众玩梗）</td></tr>
    <tr><td>18:29–18:33</td><td>"gg" · "2分？赢了11分？"——图一结束确认</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 20；图一碾压（经济/火力全线）</td></tr>
    <tr><td>paiN</td><td>图一 2 分（"赢了11分"反推）——惨败</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>南美弱旅碾压局：强队经济/火力碾压，弱旅难拿分（图一 2 分样本）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>18:21</td><td>"图一就一分 不用想了"</td><td>兑现（paiN 2 分）</td></tr>
    <tr><td>18:25</td><td>"史上第二伟大的翻盘即将来领"（反讽）</td><td>未兑现（未翻盘）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 735 条，窗口 18:25–18:39 UTC）。<b>赛后回补</b>。结果仲裁：Polymarket Map 1 + 弹幕比分。待官方核对：图一地图名。</p>"""),
    ],
    "G1 结束节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- FURIA G2 BP

FURIA_G2_BP = page(
    "BLAST Open Porto · FURIA vs paiN · G2 BP 后/开局情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二",
    speed_block(
        "G2 进行中（回补快照）· 图二",
        [("b-pend", "BP 后/开局 · 事后回补"), ("b-ok", "灰信号 0 条（玩梗已剔除）"), ("b-anchor", "系列 1-0")],
        [
            sig("风险", "var(--bad)", "灰信号 4 条均为\u201c腾讯买 CS\u201d玩梗，非指控——有效 0 条，说明无假赛质疑 → 详 §2"),
            sig("锚点", "var(--accent)", '图二开局；观众问"啥比分"（图一 13-2 后转入图二），系列 1-0 领先优势明确 → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；系列 Under 2.5 方向有利，预示 2-0 收官 → 详 §4"),
            sig("共识", "var(--purple)", "观众讨论其他场次为主（跨场闲聊），本场关注度低，说明深夜档信号稀疏 → 详 §5"),
        ],
        "G2 开局观众关注度低（跨场闲聊多）；系列 1-0 下 2-0 收官预期主流（最终兑现 13-6）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G2 · BP 后 / 开局（EARLY-GAME）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 18:35–18:54 UTC（北京 02:35–02:54）</td></tr>
    <tr><td>关键数据</td><td>648 条弹幕 · 254 活跃用户 · 密度 32.5 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>4 条均为\u201c如果腾讯把 cs 买了…\u201d玩梗（非假赛指控），已剔除。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图二开局</td><td>"啥比分"（观众确认图一后进入图二）</td><td>—</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无数字盘。<b>样本不足。</b>系列 Under 2.5 市场最终兑现（2-0）。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 系列</td><td>1-0 领先，碾压态势</td><td>应验（2-0）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 条（玩梗剔除）</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：系列 1-0，2-0 收官预期主流；</li>
    <li><b>SHORT</b>：关注度低不改变方向；图二结果见 G2 结束页；</li>
    <li><b>观察点</b>：图二比分（13-6）。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 早期 · 证据层）", "<p>本窗口弹幕以跨场闲聊为主（NAVI 翻车、LVG 赢猎鹰等），本场信号稀疏；图二开局无异常信号。</p>"),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 9；系列领先</td></tr>
    <tr><td>paiN</td><td>提及少；图一惨败后关注度低</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>深夜场观众注意力分散，弹幕信号密度低（跨场闲聊占比高）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>本窗口无明确本场预测；系列 2-0 预期最终兑现。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 648 条，窗口 18:35–18:54 UTC）。<b>赛后回补</b>。待官方核对：图二地图名。</p>"""),
    ],
    "G2 BP 后节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- FURIA G2 MID

FURIA_G2_MID = page(
    "BLAST Open Porto · FURIA vs paiN · G2 局中情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二",
    speed_block(
        "G2 进行中（回补快照）· 图二",
        [("b-pend", "局中 · 事后回补"), ("b-ok", "灰信号 0 条（玩梗剔除）"), ("b-anchor", "比分胶着于观众视角")],
        [
            sig("风险", "var(--bad)", "灰信号 3 条均为\u201c腾讯买 CS\u201d玩梗——有效 0 条，说明无假赛质疑 → 详 §2"),
            sig("锚点", "var(--accent)", '观众问"大比分几比几？"——图二进程信息未完全掌握，FURIA 仍控制局面 → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；样本不足，需关注市场结算口径 → 详 §4"),
            sig("共识", "var(--purple)", '观众对 FURIA 执行仍认可（"没经济。"· 观望），看好 FURIA 收官 → 详 §5'),
        ],
        "图二局中 FURIA 继续控制局面（最终 13-6）；本场深夜档弹幕稀疏，信号密度低。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G2 · 局中（MID-GAME）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 18:50–19:09 UTC（北京 02:50–03:09）</td></tr>
    <tr><td>关键数据</td><td>701 条弹幕 · 268 活跃用户 · 密度 35.2 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>3 条均为\u201c腾讯买 CS\u201d玩梗，剔除。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图二进程</td><td>"大比分几比几？"（观众询问）</td><td>图二 FURIA 13-6 收尾</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>无明确数字盘。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 图二</td><td>继续控制局面（"没经济。"为 paiN 侧批评）</td><td>应验（13-6）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 图二控制局面，2-0 方向稳定；</li>
    <li><b>SHORT</b>：信号稀疏下无额外变量；图二结果见 G2 结束页；</li>
    <li><b>观察点</b>：图二比分 13-6。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 局中 · 证据层）", "<p>弹幕稀疏；观众询问比分 + 观望为主，无异常信号。</p>"),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 40；局中控制（paiN "没经济"）</td></tr>
    <tr><td>paiN</td><td>"没经济。"——经济受限</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>碾压系列第二图特征：弱旅经济受限，强队继续控图。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>本窗口无明确本场预测。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 701 条，窗口 18:50–19:09 UTC）。<b>赛后回补</b>。</p>"""),
    ],
    "G2 局中节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- FURIA G2 END

FURIA_G2_END = page(
    "BLAST Open Porto · FURIA vs paiN · G2 结束情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二 13-6（FURIA 胜）",
    speed_block(
        "FURIA 2-0 paiN（系列结束）",
        [("b-ok", "系列结束 · 市场仲裁"), ("b-ok", "灰信号 0 条"), ("b-anchor", "2-0 收官")],
        [
            sig("风险", "var(--bad)", "灰信号 1 条（\u201c优瑞买了高爆手雷\u201d）为道具语境，非指控——有效 0 条，说明无假赛质疑 → 详 §2"),
            sig("锚点", "var(--accent)", '"没经济别去送吧"——paiN 图二经济受限，FURIA 13-6 收官，优势延续 → 详 §3'),
            sig("盘口", "var(--good)", "系列市场：FURIA 2-0、Under 2.5 兑现，方向一致 → 详 §4"),
            sig("共识", "var(--purple)", '"2-0 结束战斗"（G2 中段观众预期）→ 兑现，看好方向应验 → 详 §5'),
        ],
        "FURIA 2-0 横扫 paiN（图一 13-2、图二 13-6），与市场一致；paiN 弱旅定位全系列兑现。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>FURIA 2-0 paiN</b>（Polymarket 系列 FURIA + Under 2.5 结算）</td></tr>
    <tr><td>逐图</td><td>图一 <b>13-2</b>（净胜 11）· 图二 <b>13-6</b>（净胜 7）</td></tr>
    <tr><td>节点</td><td>G2 · 结束（GAME-REVIEW）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 19:05–19:21 UTC（北京 03:05–03:21）</td></tr>
    <tr><td>关键数据</td><td>748 条弹幕 · 318 活跃用户 · 密度 44.2 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>1 条（"优瑞买了高爆手雷"）为游戏内道具语境，非假赛指控。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>paiN 图二经济</td><td>"没经济别去送吧"</td><td>图二 13-6（paiN 经济受限）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无数字盘。Polymarket 系列口径：FURIA 2-0、Under 2.5、Map Handicap FURIA -1.5 ✓；图二总回合 19（Over 18.5 ✓ / Under 21.5 ✓）、净胜 7（-6.5 ✓ / -9.5 ✗）→ <b>13-6</b>。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 系列</td><td>"不用想 2-0带走"（G2 中段）</td><td>应验（2-0）</td></tr>
    <tr><td>负锚</td><td>paiN · 经济/执行</td><td>"没经济别去送吧"</td><td>应验方向（paiN 连败）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 2-0 横扫（市场一致）；</li>
    <li><b>SHORT</b>：paiN 弱旅定位（图一 2 分）全系列兑现；FURIA 状态正常（无灰信号）；</li>
    <li><b>观察点</b>：官方地图名/MVP 回填。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>19:05–19:15</td><td>图二收尾；"没经济别去送吧"——paiN 经济受限</td></tr>
    <tr><td>19:15–19:21</td><td>系列结束（Polymarket 结算方向锁定）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>提及 11；系列 2-0 收官</td></tr>
    <tr><td>paiN</td><td>图一 2 分 / 图二经济受限——全系列被碾压</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>碾压系列全样本：强队 2-0、弱旅两图合计 8 分（2+6）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>17:5x</td><td>"黑豹没有输的角度"</td><td>兑现（2-0）</td></tr>
    <tr><td>18:5x</td><td>"不用想 2-0带走"</td><td>兑现</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 748 条，窗口 19:05–19:21 UTC）。<b>赛后回补</b>。结果仲裁：Polymarket 系列 + 图二市场。待官方核对：地图名、MVP。</p>"""),
    ],
    "G2 结束节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


if __name__ == "__main__":
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_bp.html", FURIA_G1_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_mid.html", FURIA_G1_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_end.html", FURIA_G1_END)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_bp.html", FURIA_G2_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_mid.html", FURIA_G2_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_end.html", FURIA_G2_END)


# ---------------------------------------------------------------- FURIA FULL

FURIA_FULL = page(
    "BLAST Open Porto · FURIA vs paiN · 整场复盘（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · FURIA 2-0 paiN",
    speed_block(
        "FURIA 2-0 paiN",
        [("b-ok", "系列结束 · Polymarket 仲裁"), ("b-ok", "灰信号约 1 条（模糊，0 有效）"), ("b-anchor", "图一 13-2 + 图二 13-6")],
        [
            sig("风险", "var(--bad)", "灰信号约 1 条（\u201c想去找买了否冷\u201d语境模糊）——有效 0，说明无假赛质疑 → 详 §2"),
            sig("锚点", "var(--accent)", "图一 13-2（paiN 仅 2 分）· 图二 13-6——弱旅定位全系列兑现，碾压优势明显 → 详 §3"),
            sig("盘口", "var(--good)", "市场口径：系列 FURIA 2-0、Under 2.5、两图净胜 7–11，方向一致 → 详 §4"),
            sig("共识", "var(--purple)", '"黑豹没有输的角度"（BP 后）→ 2-0 应验，看好方向兑现 → 详 §5'),
        ],
        "FURIA 2-0 横扫（图一 13-2、图二 13-6），观众与市场一致；本场无灰信号，属于干净的强弱分明样本。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>FURIA 2-0 paiN</b>（Polymarket：系列 FURIA、Under 2.5、Map Handicap -1.5 均结算）</td></tr>
    <tr><td>逐图</td><td>图一 <b>13-2</b>（总回合 15、净胜 11）· 图二 <b>13-6</b>（总回合 19、净胜 7）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 17:50–19:21 UTC（北京 08-27 01:50–03:21）</td></tr>
    <tr><td>关键数据</td><td>约 4,000 条弹幕（CSBOY 虎牙主源）· 全程灰信号 0 有效</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入（KICK 广告噪音高）；本场为深夜档，信号密度低")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>全程约 1 条模糊样本（"想去找买了否冷"，G1 局中）——语境不明，不计有效；其余"买了/腾讯买 CS"均为玩梗。有效灰信号 <b>0</b>，无假赛质疑。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>paiN 弱旅定位</td><td>"pain都打不过天禄的" · "黑豹没有输的角度"</td><td>应验（图一 13-2）</td></tr>
    <tr><td>FURIA 状态</td><td>"furia状态不是特别好吧"（个别反方）</td><td>未兑现为败局（2-0）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<table>
    <tr><th>市场</th><th>结算口径（Polymarket）</th><th>与弹幕对照</th></tr>
    <tr><td>系列 / Under 2.5</td><td>FURIA 2-0 / Under 兑现</td><td>"不用想 2-0带走"一致</td></tr>
    <tr><td>图一</td><td>总回合 ≤15、净胜 ≥9（-9.5 ✓ / -12.5 ✗）</td><td>13-2（弹幕"2分"吻合）</td></tr>
    <tr><td>图二</td><td>总回合 19、净胜 7（-6.5 ✓ / -9.5 ✗）</td><td>13-6</td></tr>
  </table>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>FURIA · 系列</td><td>"黑豹没有输的角度" · "2-0 结束战斗"</td><td>应验（2-0）</td></tr>
    <tr><td>负锚</td><td>paiN · 实力</td><td>"pain都打不过天禄" · "图一就一分"</td><td>应验（图一 2 分）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 有效</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：FURIA 2-0（市场一致）；状态正常、无灰信号；</li>
    <li><b>SHORT</b>：paiN 弱旅定位（两图合计 8 分）——后续遇强队参考价值有限；</li>
    <li><b>观察点</b>：官方地图名/MVP 回填；FURIA 后续对阵。</li>
  </ul>"""),
        ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>内容（弹幕口径）</th></tr>
    <tr><td>G1 13-2</td><td>17:50 BP（"图一黑豹选的"）；18:2x "图一就一分"；18:33 "2分？赢了11分？"——13-2</td></tr>
    <tr><td>G2 13-6</td><td>18:35 图二开局；18:5x "不用想 2-0带走"；19:0x "没经济别去送吧"——13-6 收官</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>FURIA（黑豹）</td><td>图一碾压（"无敌经济"）、图二控局；nqz 离队话题为跨场闲聊</td></tr>
    <tr><td>paiN</td><td>图一 2 分、图二 6 分——经济/火力全面受限（"没经济"）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BLAST Porto 小组赛强弱分明样本：强队 2-0、弱旅两图合计 8 分；深夜档弹幕稀疏（跨场闲聊占比高）。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>17:5x</td><td>"黑豹没有输的角度"</td><td>兑现（2-0）</td></tr>
    <tr><td>18:21</td><td>"图一就一分 不用想了"</td><td>兑现（paiN 2 分）</td></tr>
    <tr><td>18:5x</td><td>"不用想 2-0带走"</td><td>兑现</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（约 4,000 条，窗口 17:50–19:21 UTC）。<b>赛后回补</b>（整场复盘页，基于全时段弹幕）。结果仲裁：Polymarket 系列/图一/图二市场。来源标签：本场弹幕（核心）/ 市场口径（§4）。待官方核对：地图名、MVP。</p>"""),
    ],
    "整场复盘（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- NAVI G3 BP

NAVI_G3_BP = page(
    "BLAST Open Porto · NAVI vs M80 · G3 BP 后/开局情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图三（系列 1-1）",
    speed_block(
        "G3 进行中（回补快照）· 图三",
        [("b-pend", "BP 后/开局 · 事后回补"), ("b-risk", "灰信号 1 条（玩梗）"), ("b-anchor", "决胜局")],
        [
            sig("风险", "var(--bad)", "灰信号 1 条（\u201c都猜错了，因为我买了\u201d玩梗）——有效 0，说明无假赛质疑 → 详 §2"),
            sig("锚点", "var(--accent)", '"那个狙手里面有8500块，经济影响不大"——G3 开局经济讨论，决胜局悬念大 → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；决胜局市场悬念大，需关注结算方向 → 详 §4"),
            sig("共识", "var(--purple)", "观众仍讨论图一/图二比分（跨场信息滞后），说明关注焦点分散 → 详 §5"),
        ],
        "系列 1-1 进入决胜局；G3 开局信号稀疏，最终 M80 拿下（2-1）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G3 · BP 后 / 开局（EARLY-GAME）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 16:25–16:54 UTC（北京 00:25–00:54）</td></tr>
    <tr><td>关键数据</td><td>2,021 条弹幕 · 837 活跃用户 · 密度 67.4 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入（KICK 广告噪音高）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>1 条（"都猜错了，因为我买了"）为投注玩梗。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>G3 经济</td><td>"那个狙手里面有8500块，经济影响不大"</td><td>过程样本</td></tr>
    <tr><td>观众信息滞后</td><td>"图一比分多少 打这么久"（观众仍问图一）</td><td>跨场闲聊，非本场信号</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>弹幕无数字盘。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>系列</td><td>1-1 决胜局</td><td>G3 定系列</td><td>M80 拿下（2-1）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>0 有效</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：决胜局悬念；</li>
    <li><b>SHORT</b>：G3 结果 M80 胜（2-1）——NAVI 让一追二失败；</li>
    <li><b>观察点</b>：G3 中段灰信号（观众质疑 NAVI"买了"）。</li>
  </ul>"""),
        ("7", "逐局复盘（G3 早期 · 证据层）", "<p>开局弹幕以跨场信息（图一/图二比分讨论）为主；本场信号稀疏。</p>"),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI</td><td>提及 105；决胜局开局</td></tr>
    <tr><td>M80</td><td>提及少；系列 1-1 后士气（观众"m80不也赢了"）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>BO3 决胜局：观众跨场闲聊占比高，信号需结合后续节点。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>本窗口无明确本场预测。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 2,021 条，窗口 16:25–16:54 UTC）。<b>赛后回补</b>。</p>"""),
    ],
    "G3 BP 后节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- NAVI G3 MID

NAVI_G3_MID = page(
    "BLAST Open Porto · NAVI vs M80 · G3 局中情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图三",
    speed_block(
        "G3 进行中（回补快照）· 图三",
        [("b-pend", "局中 · 事后回补"), ("b-risk", "灰信号 6 条（观众质疑 NAVI）"), ("b-anchor", "送分质疑")],
        [
            sig("风险", "var(--bad)", '灰信号 6 条——"那tm是故意的""是不是买了啊""故意的？"——观众质疑 NAVI（<b>非结论</b>），若兑现指向 NAVI 输球 → 详 §2'),
            sig("锚点", "var(--accent)", "G3 中段 NAVI 执行受批；观众\u201c人头数这么少\u201d质疑，劣势信号集中 → 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；样本不足，需关注结算口径 → 详 §4"),
            sig("共识", "var(--purple)", '"gg"刷屏（G3 收尾阶段），说明局面已定 → 详 §5'),
        ],
        "G3 局中观众对 NAVI 产生\u201c故意/买了\u201d质疑（6 条）；G3 最终 M80 拿下，\u201c被质疑方输球\u201d方向待兑现统计。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>节点</td><td>G3 · 局中（MID-GAME）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 16:50–17:14 UTC（北京 00:50–01:14）</td></tr>
    <tr><td>关键数据</td><td>4,063 条弹幕 · 1,350 活跃用户 · 密度 162.8 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>6 条</td><td>NAVI 侧：故意/买了</td><td>"那tm是故意的" · "是不是买了啊" · "故意的？" · "买了" · "都猜错了，因为我买了"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（观众对 NAVI\u201c故意/买了\u201d质疑集中；无盘口即时重合证据，非实锤）。G3 结果 M80 胜——\u201c被质疑方（NAVI）输球\u201d方向待兑现统计。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>NAVI 执行</td><td>"人头数这么少不排除都是运"（观众质疑强度）</td><td>过程样本</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>弹幕无数字盘。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>灰信号</td><td>NAVI 侧（6 条）</td><td>故意/买了质疑</td><td>G3 NAVI 输——待兑现统计</td></tr>
    <tr><td>共识</td><td>G3 收尾</td><td>"gg"刷屏</td><td>M80 拿下 G3</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：G3 悬念收尾（最终 M80 胜，系列 2-1）；</li>
    <li><b>SHORT</b>：NAVI\u201c故意/买了\u201d灰信号是系列尾声的重要观察（兑现统计待回填）；</li>
    <li><b>观察点</b>：G3 结束页与整场页。</li>
  </ul>"""),
        ("7", "逐局复盘（G3 局中 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>16:50–17:03</td><td>G3 中段；观众质疑 NAVI 强度（"人头数这么少"）</td></tr>
    <tr><td>17:04–17:14</td><td>17:04 密度峰值 285；"gg"刷屏——G3 收尾</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI</td><td>提及 307；局中被质疑"故意/买了"（灰信号）</td></tr>
    <tr><td>M80</td><td>提及少；G3 拿下</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>决胜局被质疑方输球样本（NAVI 被质疑 → NAVI 输 G3），待兑现统计。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", '<p>灰信号 6 条 → 兑现统计待回填（无实锤）。</p>'),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 4,063 条，窗口 16:50–17:14 UTC）。<b>赛后回补</b>。来源标签：本场弹幕（核心）。</p>"""),
    ],
    "G3 局中节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


if __name__ == "__main__":
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_bp.html", FURIA_G1_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_mid.html", FURIA_G1_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_end.html", FURIA_G1_END)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_bp.html", FURIA_G2_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_mid.html", FURIA_G2_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_end.html", FURIA_G2_END)
    w("intel_danmu_FURIA-paiN_2026-08-26.html", FURIA_FULL)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_bp.html", NAVI_G3_BP)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_mid.html", NAVI_G3_MID)


# ---------------------------------------------------------------- NAVI G3 END

NAVI_G3_END = page(
    "BLAST Open Porto · NAVI vs M80 · G3 结束情报（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图三（M80 胜）",
    speed_block(
        "M80 2-1 NAVI（系列结束）",
        [("b-ok", "系列结束 · 市场仲裁"), ("b-risk", "灰信号 9 条（观众质疑 NAVI）"), ("b-anchor", "NAVI 图二自选图叙事应验")],
        [
            sig("风险", "var(--bad)", '灰信号 9 条——"故意的？""买了""NAVI拿的绿龙剧本"——观众质疑 NAVI（<b>非结论</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", '"navi经典输图二自选图"叙事 → 图二 M80 翻盘 + 图三 M80 拿下（2-1）→ 详 §3'),
            sig("盘口", "var(--good)", "市场口径：M80 2-1（NAVI -1.5 未过）、三图总回合均 Under 21.5 → 详 §4"),
            sig("共识", "var(--purple)", '"navi输了啊""只有辣味翻车了"——NAVI 爆冷出局情绪 → 详 §5'),
        ],
        "M80 2-1 爆冷 NAVI：图二/图三连下，\u201cNAVI 图二老输\u201d叙事应验；系列尾声观众对 NAVI\u201c故意/买了\u201d质疑集中（0 实锤）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>M80 2-1 NAVI</b>（Polymarket：系列 M80、Map Handicap NAVI -1.5 未过）</td></tr>
    <tr><td>逐图</td><td>图一 NAVI 13-5/13-4（Anubis）· 图二 M80 13-6/13-7 · 图三 M80 胜（总回合 ≤21）</td></tr>
    <tr><td>节点</td><td>G3 · 结束（GAME-REVIEW）· <b>事后回补</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 17:05–17:27 UTC（北京 01:05–01:27）</td></tr>
    <tr><td>关键数据</td><td>2,954 条弹幕 · 1,085 活跃用户 · 密度 128.5 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>9 条</td><td>NAVI 侧：故意/买了/剧本</td><td>"故意的？" · "买了" · "NAVI拿的绿龙剧本，先输然后全胜夺冠😂" · "都猜错了，因为我买了"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（系列尾声观众对 NAVI\u201c故意/买了\u201d质疑集中；含玩梗，无实锤、无盘口即时重合证据）。兑现状态：NAVI 输 G3/G2——\u201c被质疑方输球\u201d方向待兑现统计（观众质疑非结论）。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>NAVI 图二自选图</td><td>"navi经典输图二自选图"（图二开局玩梗）</td><td>应验（图二 M80 翻盘，系列 2-1）</td></tr>
    <tr><td>M80 韧性</td><td>"m80不也赢了"（观众认可）</td><td>G2/G3 连下</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无数字盘。Polymarket 系列口径：M80 2-1（NAVI -1.5 未过）、三图总回合均 Under 21.5（低回合）；图三 M80 -3.5 让分过 ✓ → M80 净胜 ≥4。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>负锚</td><td>NAVI × 图二</td><td>"navi经典输图二自选图"（历史叙事）</td><td>应验（图二 M80 翻盘）</td></tr>
    <tr><td>正锚</td><td>M80 · 系列</td><td>"m80不也赢了"（观众认可 M80 表现）</td><td>应验（2-1）</td></tr>
    <tr><td>灰信号</td><td>NAVI 侧（9 条）</td><td>故意/买了/剧本</td><td>NAVI 输——待兑现统计</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：M80 2-1 爆冷（市场一致）；\u201cNAVI 图二老输\u201d历史叙事兑现；</li>
    <li><b>SHORT</b>：NAVI\u201c故意/买了\u201d灰信号集中在失利节点——兑现率统计是后续关键观察（0 实锤）；</li>
    <li><b>观察点</b>：官方比分/MVP、灰信号兑现回填。</li>
  </ul>"""),
        ("7", "逐局复盘（G3 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>17:05–17:11</td><td>G3 末段胶着；观众质疑 NAVI（"故意的？""买了"）</td></tr>
    <tr><td>17:11–17:16</td><td>密度峰值 537/400——G3 赛点/结束；"gg"刷屏</td></tr>
    <tr><td>17:2x</td><td>"navi输了啊""只有辣味翻车了"——系列确认 M80 2-1</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI</td><td>提及 278；被质疑"故意/买了"（灰信号 9 条）+ "辣味翻车"情绪</td></tr>
    <tr><td>M80</td><td>提及少；G2/G3 连下（"m80不也赢了"）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>\u201cNAVI 图二自选图翻车\u201d历史叙事兑现样本（跨场规律）；被质疑方输球待统计。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>图二开局</td><td>"navi经典输图二自选图"</td><td>兑现（图二 M80 翻盘）</td></tr>
    <tr><td>17:1x</td><td>灰信号 9 条（故意/买了）</td><td>NAVI 输——兑现统计待回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（合计 2,954 条，窗口 17:05–17:27 UTC）。<b>赛后回补</b>。结果仲裁：Polymarket 系列/图三市场。待官方核对：图三地图名、MVP。</p>"""),
    ],
    "G3 结束节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


# ---------------------------------------------------------------- NAVI FULL

NAVI_FULL = page(
    "BLAST Open Porto · NAVI vs M80 · 整场复盘（回补）· 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · M80 2-1 NAVI",
    speed_block(
        "M80 2-1 NAVI",
        [("b-ok", "系列结束 · Polymarket 仲裁"), ("b-risk", "灰信号约 15 条（跨节点去重）"), ("b-anchor", "NAVI 图二自选图翻车")],
        [
            sig("风险", "var(--bad)", '灰信号约 15 条（G3 局中 6 + 末段 9，跨节点去重）——观众对 NAVI"故意/买了"质疑集中，<b>非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", "图一 NAVI 13-5/13-4（Anubis）· 图二/图三 M80 连下——\u201cNAVI 图二老输\u201d叙事兑现 → 详 §3"),
            sig("盘口", "var(--good)", "市场口径：M80 2-1（NAVI -1.5 未过）、三图低回合 → 详 §4"),
            sig("共识", "var(--purple)", '"navi输了啊""只有辣味翻车了"——NAVI 爆冷出局 → 详 §5'),
        ],
        "M80 2-1 爆冷 NAVI（图二/图三连下）；\u201cNAVI 图二自选图翻车\u201d历史叙事兑现；系列尾声 NAVI\u201c故意/买了\u201d灰信号集中（0 实锤，兑现统计待回填）。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>M80 2-1 NAVI</b>（Polymarket：系列 M80、Map Handicap NAVI -1.5 未过）</td></tr>
    <tr><td>逐图</td><td>图一 Anubis NAVI 13-5/13-4（总回合 ≤18）· 图二 M80 13-6/13-7 · 图三 M80 胜（总回合 ≤21）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 14:25–17:27 UTC（北京 22:25–01:27）</td></tr>
    <tr><td>关键数据</td><td>约 2.6 万条弹幕（CSBOY 虎牙主源，含短暂采集断流缺口 14:48-14:49）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321 + CSBOY-Mo 321123", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 + KICK", "BLAST 官方/KICK 未纳入（KICK 广告噪音高）；14:48-14:49 约 1 分钟采集断流已标注")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>节点</th><th>条数</th><th>代表样本（意译）</th></tr>
    <tr><td>G3 局中</td><td>6</td><td>"那tm是故意的" · "是不是买了啊" · "故意的？" · "买了"</td></tr>
    <tr><td>G3 末段</td><td>9</td><td>"故意的？" · "买了" · "NAVI拿的绿龙剧本，先输然后全胜夺冠😂"</td></tr>
  </table>
  <div class="warnbox"><b>预警等级：中</b>。灰信号集中于系列尾声 NAVI\u201c故意/买了\u201d质疑（含玩梗）；无局内实锤、无盘口即时重合证据。兑现状态：NAVI 输图二/图三——\u201c被质疑方输球\u201d方向待兑现统计回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图一 Anubis（M80 自选）</td><td>赛前"长局制造机"预期</td><td>未兑现——NAVI 大胜（自选图翻车）</td></tr>
    <tr><td>NAVI 图二自选图</td><td>"navi经典输图二自选图"（观众历史叙事）</td><td>应验（图二 M80 翻盘）</td></tr>
    <tr><td>M80 韧性</td><td>"m80不也赢了"</td><td>G2/G3 连下（2-1）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<table>
    <tr><th>市场</th><th>结算口径（Polymarket）</th><th>与弹幕对照</th></tr>
    <tr><td>系列 / -1.5</td><td>M80 2-1 / NAVI -1.5 未过</td><td>"只有辣味翻车了"一致</td></tr>
    <tr><td>图一</td><td>NAVI 净胜 ≥7（-6.5 ✓ / -9.5 ✗）、总回合 ≤18</td><td>13-5/13-4 区间</td></tr>
    <tr><td>图二</td><td>M80 净胜 ≥6（-6.5 ✓ / -9.5 ✗）、总回合 19-21</td><td>13-6/13-7 区间</td></tr>
    <tr><td>图三</td><td>M80 净胜 ≥4（-3.5 ✓）、总回合 ≤21</td><td>13-x（≤8）</td></tr>
  </table>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚（G1）</td><td>NAVI · 图一</td><td>大胜 Anubis</td><td>应验（13-5/13-4）</td></tr>
    <tr><td>负锚</td><td>NAVI × 图二</td><td>"navi经典输图二自选图"</td><td>应验（图二翻盘）</td></tr>
    <tr><td>正锚</td><td>M80 · 系列</td><td>"m80不也赢了"（G2 后）</td><td>应验（2-1）</td></tr>
    <tr><td>灰信号</td><td>NAVI 侧（约 15 条去重）</td><td>故意/买了/剧本</td><td>NAVI 输——兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：M80 2-1 爆冷（市场一致）；</li>
    <li><b>SHORT</b>：\u201cNAVI 图二自选图翻车\u201d规律样本 +1；NAVI\u201c故意/买了\u201d灰信号集中在失利节点，兑现率统计是后续关键（0 实锤）；</li>
    <li><b>观察点</b>：官方比分/MVP、灰信号兑现回填、NAVI 后续状态。</li>
  </ul>"""),
        ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>内容（弹幕口径）</th></tr>
    <tr><td>G1 Anubis 13-5/13-4</td><td>14:26 开赛；15:07 GG + "匪图一分不得"（M80 T 侧零分）——NAVI 大胜</td></tr>
    <tr><td>G2 13-6/13-7</td><td>15:23 图二米垃圾；"navi经典输图二自选图"；M80 翻盘拿下</td></tr>
    <tr><td>G3 M80 胜</td><td>16:29 图三开局；17:11 密度峰值 537（赛点/结束）；"navi输了啊"——M80 2-1</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NAVI</td><td>图一强势（wdf 高光）→ 图二/图三被翻；"辣味翻车"情绪 + 灰信号（故意/买了）</td></tr>
    <tr><td>M80</td><td>图一惨败后连下两图（"m80不也赢了"）；韧性样本</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>\u201cNAVI 图二自选图翻车\u201d跨场规律样本（观众历史叙事兑现）；</li>
    <li>被质疑方（NAVI）输球方向待兑现统计；</li>
    <li>BLAST Porto 小组赛：强队首图碾压后连丢两图样本（NAVI 本场）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>14:2x</td><td>NAVI 图一优势（市场 + 弹幕）</td><td>兑现（图一胜）</td></tr>
    <tr><td>15:2x</td><td>"navi经典输图二自选图"</td><td>兑现（图二翻盘）</td></tr>
    <tr><td>16:5x</td><td>灰信号（故意/买了）</td><td>NAVI 输——兑现统计待回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321 + CSBOY-Mo 321123（约 2.6 万条，窗口 14:25–17:27 UTC）；缺口：14:48-14:49 采集断流约 1 分钟（已标注）；BLAST 官方/KICK 未纳入。结果仲裁：Polymarket 系列/逐图市场。来源标签：本场弹幕（核心）/ 前局延续（§7）/ 历史画像（§3/§9）/ 市场口径（§4）。待官方核对：逐图比分、地图名、MVP。</p>"""),
    ],
    "整场复盘（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


if __name__ == "__main__":
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_bp.html", FURIA_G1_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_mid.html", FURIA_G1_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_end.html", FURIA_G1_END)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_bp.html", FURIA_G2_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_mid.html", FURIA_G2_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_end.html", FURIA_G2_END)
    w("intel_danmu_FURIA-paiN_2026-08-26.html", FURIA_FULL)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_bp.html", NAVI_G3_BP)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_mid.html", NAVI_G3_MID)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_end.html", NAVI_G3_END)
    w("intel_danmu_Natus Vincere-M80_2026-08-26.html", NAVI_FULL)


# ---------------------------------------------------------------- KT G5 END

KT_G5_END = page(
    "LCK Play-In · KT vs BRO · G5 结束情报（回补）· 2026-08-26",
    "LoL · LCK 季后赛入围赛 · BO5 · G5（KT 胜）",
    speed_block(
        "KT 3-2 BRO（系列结束）",
        [("b-ok", "系列结束 · Polymarket 仲裁"), ("b-risk", "灰信号约 16 条（含跨场噪音，本场相关约 4-5）"), ("b-anchor", "G5 鳄鱼偷家翻盘")],
        [
            sig("风险", "var(--bad)", "灰信号统计 16 条含 WBG 跨场菠菜话题（甄别后本场相关约 4-5 条）——<b>观众质疑，非结论</b> → 详 §2"),
            sig("锚点", "var(--accent)", '"选鳄鱼右边就炸了"（13:37）→ G5 KT 鳄鱼翻盘，系列 3-2 拿下 → 详 §3'),
            sig("盘口", "var(--good)", "Polymarket lol-kt-bro2 结算 KT 99.95c；弹幕\u201c一波\u201d刷屏对应终局 → 详 §4"),
            sig("共识", "var(--purple)", '"恭喜长沙陀螺"（13:52）——观众确认 KT 拿下 G5 → 详 §5'),
        ],
        "KT 3-2 BRO 晋级（G5 鳄鱼偷家/翻盘终局）；灰信号集中局末\u201c演/假/剧本\u201d质疑，0 实锤，兑现统计待回填。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>系列结果</td><td><b>KT 3-2 BRO</b>（KT 晋级第 5 种子；Polymarket lol-kt-bro2 结算 KT 99.95c 交叉确认）</td></tr>
    <tr><td>G5 结果</td><td>KT 胜（终局弹幕\u201c一波\u201d刷屏 + \u201c恭喜长沙陀螺\u201d；G5 鳄鱼关键选角/翻盘，官方比分待核对）</td></tr>
    <tr><td>节点</td><td>G5 · 结束（GAME-REVIEW）· <b>事后回补</b>（流水线当时未产出 g5_end）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 13:35–13:54 UTC（北京 21:35–21:54）</td></tr>
    <tr><td>关键数据</td><td>814 条弹幕 · 308 活跃用户 · 密度 41.2 条/分（4 路 LCK 直播间）</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + Remember 528222 + 米勒 149361", "同左（LCK 默认集）", "无缺源；注意同窗口混入 WBG（LPL）跨场讨论，已甄别标注")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>16 条（统计）</td><td>部分为本场局末质疑，部分为 WBG 跨场菠菜话题</td><td>本场："这把盲猜下剧本 一波团灭 直接gg"（13:40）· "太假了"（13:46）· "演得不真实一点怕你们不信"（13:48）· "是加还是假？"（13:51）· "不打假赛哪来的钱"（13:51）；跨场："WBG现在全是菠菜选手"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>。本场相关约 4-5 条（局末\u201c演/假/剧本\u201d节奏质疑），方向待归因；\u201cWBG 菠菜\u201d为跨场噪音已甄别。0 实锤、无盘口即时重合证据；兑现统计待回填。纪律：观众质疑非结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>G5 鳄鱼</td><td>"选鳄鱼右边就炸了"（13:37）</td><td>KT 鳄鱼关键，终局翻盘/偷家（弹幕口径）</td></tr>
    <tr><td>终局推进</td><td>"大龙绝对一波结束"（13:43）· "龙魂拿完 大龙直接一波"（13:45）</td><td>13:51-52 一波收尾</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无数字盘（"买的小时间"为投注闲聊）。Polymarket lol-kt-bro2 系列结算 KT 99.95c——与弹幕"恭喜长沙陀螺"一致。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>KT · G5</td><td>鳄鱼关键角 + "一波"推进</td><td>应验（KT 拿下 G5）</td></tr>
    <tr><td>共识</td><td>KT 晋级</td><td>"恭喜长沙陀螺"（13:52）</td><td>兑现（3-2 晋级）</td></tr>
    <tr><td>灰信号</td><td>局末节奏（方向待归因）</td><td>演/假/剧本质疑（约 4-5 条本场相关）</td><td>兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：KT 3-2 晋级（Polymarket 结算）；G5 鳄鱼/翻盘为决胜关键；</li>
    <li><b>SHORT</b>：局末灰信号（演/假）待兑现统计——本系列灰信号模式（G2/G3 指向输家侧 KT、G5 局末质疑）需回填验证；</li>
    <li><b>观察点</b>：官方比分/MVP、灰信号兑现、KT 后续赛程。</li>
  </ul>"""),
        ("7", "逐局复盘（G5 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>13:35–13:40</td><td>G5 后期；"选鳄鱼右边就炸了" · "gg 斯密达"（13:36）· "kt赢了？"（13:39）</td></tr>
    <tr><td>13:42–13:52</td><td>"一波"刷屏（大龙/中路/龙魂）；13:46-51 灰信号（太假了/演/是加还是假）；13:51-52 "GGGGG" + "恭喜长沙陀螺"——KT 拿下</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>KT</td><td>G5 鳄鱼关键 + 一波推进；系列 3-2 晋级（"恭喜长沙陀螺"）</td></tr>
    <tr><td>BRO</td><td>G5 局末被"一波"；系列 2-3 出局（越打越好但终结能力差规律延续）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>BRO\u201c终结能力差\u201d跨场规律：G5 被一波带走（系列多次领先未终结）；</li>
    <li>KT 鳄鱼决胜角样本；LCK 入围赛 BO5 打满（3-2）节奏。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>13:43-45</td><td>"大龙/龙魂一波结束"</td><td>兑现（13:51 一波收尾）</td></tr>
    <tr><td>13:46-51</td><td>灰信号（演/假/剧本）</td><td>兑现统计待回填（0 实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">硕硕 323444 + 957 890001 + Remember 528222 + 米勒 149361（合计 814 条，窗口 13:35–13:54 UTC）。<b>赛后回补</b>。混入 WBG 跨场讨论已甄别。结果仲裁：Polymarket lol-kt-bro2（KT 99.95c）。待官方核对：G5 比分、MVP。</p>"""),
    ],
    "G5 结束节点（回补）2026-08-26 · 弹幕口径 + Polymarket 仲裁",
)


if __name__ == "__main__":
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_bp.html", FURIA_G1_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_mid.html", FURIA_G1_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g1_end.html", FURIA_G1_END)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_bp.html", FURIA_G2_BP)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_mid.html", FURIA_G2_MID)
    w("intel_danmu_FURIA-paiN_2026-08-26_g2_end.html", FURIA_G2_END)
    w("intel_danmu_FURIA-paiN_2026-08-26.html", FURIA_FULL)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_bp.html", NAVI_G3_BP)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_mid.html", NAVI_G3_MID)
    w("intel_danmu_Natus Vincere-M80_2026-08-26_g3_end.html", NAVI_G3_END)
    w("intel_danmu_Natus Vincere-M80_2026-08-26.html", NAVI_FULL)
    w("intel_danmu_LCK-KT-BRO_G5_2026-08-26.html", KT_G5_END)
