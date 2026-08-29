#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 NS vs BFX（LCK 骑士之路 R1）G1 局末情报页（2026-08-27）。
数据：VPS g1_end 切片/统计（08:08-08:36 UTC，多源）；结果 Polymarket Game 1 NS 99.95c。
"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


PAGE = page(
    "LCK Play-In · NS vs BFX · G1 结束情报 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · G1（NS 胜）",
    speed_block(
        "NS 1-0 BFX（G1 结束）",
        [("b-ok", "G1 结束 · 市场仲裁"), ("b-risk", "灰信号 15 条（观众质疑 BFX）"), ("b-anchor", "NS 发条皇子组合")],
        [
            sig("风险", "var(--bad)", '灰信号 15 条——观众质疑 BFX"收钱/加里奥买了"（<b>非结论</b>）；G1 BFX 输，说明灰信号兑现率是后续关键 → 详 §2'),
            sig("锚点", "var(--accent)", '"发条皇子组合技太权威"（08:19:36）——NS 中野组合收官，优势兑现；Kingen 开团 → 详 §3'),
            sig("盘口", "var(--good)", "Polymarket Game 1 NS 99.95c，预示 NS 拿下；弹幕人头盘讨论（人头多但领先少）→ 详 §4"),
            sig("共识", "var(--purple)", '观众批 BFX 阵容"送分局"（"选出来就是送分"），看衰方向应验 → 详 §5'),
        ],
        "G1 NS 拿下（发条皇子组合）；BFX 灰信号（收钱/加里奥买了）集中在失利侧，兑现率统计待回填；G2 关注 BFX 阵容调整。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5</td></tr>
    <tr><td>G1 结果</td><td><b>NS 胜</b>（Polymarket Game 1 Winner NS 99.95c；弹幕 08:19 GG 刷屏确认）</td></tr>
    <tr><td>节点</td><td>G1 · 结束（GAME-REVIEW）· <b>实时节点</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 08:08–08:36 UTC（北京 16:08–16:36）</td></tr>
    <tr><td>关键数据</td><td>2,387 条弹幕 · 901 活跃用户 · 密度 84.1 条/分（多源）</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000", "同左（LCK 默认集）", "窗口内各源均覆盖；跨场闲聊（T1/KT/WBG）已甄别标注")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>15 条</td><td>BFX 侧：收钱/加里奥买了/故意送</td><td>"bfx收钱了？" · "收钱了？" · "这加里奥不是买了？" · "这加里奥肯定买了" · "这不是各种故意送嘛" · "左边这个阵容选出来就是送分局"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（观众对 BFX\u201c收钱/加里奥买了\u201d质疑集中，时间分散；无盘口即时重合证据，非实锤）。兑现状态：G1 BFX 输——\u201c被质疑方输球\u201d方向待兑现统计回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>NS 发条皇子</td><td>"发条皇子组合技太权威"（08:19:36）· "发条皇子组合技还是太权威了"</td><td>G1 收官组合（应验）</td></tr>
    <tr><td>BFX 加里奥</td><td>"这加里奥不是买了？肯定买了" · "大光加里奥赢过吗就选"</td><td>加里奥表现被批（灰信号中心）</td></tr>
    <tr><td>BFX 杰斯</td><td>"玩个杰斯必输" · "杰斯怎么赢游戏啊" · "杰斯就是吃压力的英雄"</td><td>杰斯选角被看衰（方向应验）</td></tr>
    <tr><td>Kingen 开团</td><td>"kingen第一波开的好" · "king嗨吃人头吃爽了"</td><td>NS 侧正向</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无明确数字盘；人头讨论为主（"人头多但领先少""才6.5要翻"）。Polymarket Game 1 Winner NS 99.95c 结算方向与弹幕 GG 一致。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NS · 中野组合</td><td>发条皇子组合"太权威"</td><td>应验（NS 赢 G1）</td></tr>
    <tr><td>负锚</td><td>BFX · 阵容</td><td>"选出来就是送分" · 加里奥/杰斯被批</td><td>应验方向（BFX 输）</td></tr>
    <tr><td>灰信号</td><td>BFX 侧（15 条）</td><td>收钱/加里奥买了</td><td>BFX 输——兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：G1 NS 拿下（市场一致）；NS 中野组合是系列优势点；</li>
    <li><b>SHORT</b>：BFX 灰信号（收钱/加里奥买了）集中在失利侧，兑现率统计是后续观察；BFX 阵容（加里奥/杰斯）若延续将被继续看衰；</li>
    <li><b>观察点</b>：G2 BP、BFX 阵容调整、官方 MVP。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>08:16–08:17</td><td>NS 打出一波优势团（"NS打赢了""拿下了"）；Kingen 开团（"第一波开的好"）</td></tr>
    <tr><td>08:18–08:19</td><td>GG 刷屏（08:18:55 GG · 08:19:04 结束啦 · 08:19:36 "发条皇子组合技太权威"）——G1 结束，NS 胜</td></tr>
    <tr><td>08:20–08:36</td><td>局间：观众批 BFX 阵容（"选出来就是送分"）+ 跨场闲聊（T1/KT/WBG）；灰信号集中"收钱/加里奥买了"</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NS 全队</td><td>发条皇子组合（中野）收官；Kingen 开团正向（"kingen第一波开的好"）</td></tr>
    <tr><td>BFX 全队</td><td>加里奥/杰斯选角被批（"必输"）；灰信号 15 条质疑收钱/买了（非结论）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>LCK 骑士之路（Play-In）：BO5 入围；观众对"送分局/收钱"叙事敏感（灰信号纪律待兑现统计）；</li>
    <li>发条皇子中野组合本场样本（NS 收官）；加里奥/杰斯负锚样本（BFX）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>08:17-19</td><td>"发条皇子组合技太权威"（NS 收官）</td><td>兑现（NS 赢 G1）</td></tr>
    <tr><td>08:18</td><td>"玩个杰斯必输"（BFX 选角看衰）</td><td>应验方向（BFX 输）</td></tr>
    <tr><td>08:2x</td><td>灰信号 15 条（BFX 收钱/买了）</td><td>兑现统计待回填（0 实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000（合计 2,387 条，窗口 08:08–08:36 UTC）。跨场闲聊（T1/KT/WBG）已甄别。结果仲裁：Polymarket Game 1（NS 99.95c）+ 弹幕 GG。来源标签：本场弹幕（核心）/ 市场口径（§4）。待官方核对：G1 比分、MVP。</p>"""),
    ],
    "G1 结束节点 2026-08-27 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g1_end.html"
    out.write_text(PAGE, encoding="utf-8")
    print("wrote", out)


G2_BP = page(
    "LCK Play-In · NS vs BFX · G2 BP 后/开局情报 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · G2（系列 1-0）",
    speed_block(
        "G2 进行中 · BP 后/开局",
        [("b-pend", "BP 后/开局节点"), ("b-ok", "灰信号 1 条（模糊）"), ("b-anchor", "BFX 换主动阵容")],
        [
            sig("风险", "var(--bad)", '灰信号 1 条（"昨天的剧本"）语境模糊，非有效指控——<b>观众质疑，非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", '"这把bfx要选主动阵容了"——BFX 调整方向；NS 阵容被评"飘了？" → 详 §3'),
            sig("盘口", "var(--good)", "弹幕无数字盘；观众预测 2-0 或 1-1 分歧 → 详 §4"),
            sig("共识", "var(--purple)", '"BFX没戏了，今天农心虐杀"（NS 被看好）vs "1-1红色方赢"（反方）→ 详 §5'),
        ],
        "G2 BP 后观众主流看好 NS 2-0，但存在 1-1 反方预期；BFX 主动阵容调整是观察点。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5（系列 NS 1-0）</td></tr>
    <tr><td>节点</td><td>G2 · BP 后 / 开局（EARLY-GAME）· <b>实时节点</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 16:37–16:57（北京时间；局间 + BP）</td></tr>
    <tr><td>关键数据</td><td>649 条弹幕 · 343 活跃用户 · 密度 33.2 条/分（多源）</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000", "同左（LCK 默认集）", "窗口内各源覆盖；跨场闲聊（T1/DNS/WBG）已甄别")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>1 条（"昨天的剧本"）语境模糊，不构成有效指控；其余"买"类为玩梗。有效灰信号 <b>0</b>。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>BFX 调整</td><td>"这把bfx要选主动阵容了"（08:53）</td><td>G2 BP 主动化（过程样本）</td></tr>
    <tr><td>NS 阵容评价</td><td>"奖励一把云又奖励一把朗姆？？？NS飘了？"（08:56）· "这个阵容 又是要打架啊"</td><td>观众对 NS 选择有"飘"评价</td></tr>
    <tr><td>英雄讨论</td><td>"纳尔狐狸" · "瞎子胜率这么低还一直选" · "狗头选就输，敢选狗头"</td><td>BP 焦点（待 G2 验证）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>观众预测分歧："2-0了"（NS 横扫）vs "1-1红色方赢"（BFX 扳平）。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NS · 系列</td><td>"BFX没戏了，今天农心虐杀" · "2-0了"</td><td>待 G2 结束回填</td></tr>
    <tr><td>反方预期</td><td>BFX · G2</td><td>"1-1红色方赢"（部分观众）</td><td>待 G2 结束回填</td></tr>
    <tr><td>灰信号</td><td>—</td><td>1 条模糊，不计有效</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：NS 系列 1-0、主流看好 2-0；</li>
    <li><b>SHORT</b>：BFX 主动阵容调整 + NS"飘"评价——若 BFX 调整奏效，1-1 反方预期有空间；</li>
    <li><b>观察点</b>：G2 开局节奏、BFX 主动阵容执行、NS 阵容"飘"是否付出代价。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>16:37–16:47</td><td>局间：NS 1-0 领先讨论（"BFX没戏了"）；回顾 G1（"第一局狐狸被ns屠杀"）</td></tr>
    <tr><td>16:52–16:57</td><td>BP：BFX 主动阵容（"要选主动阵容了"）；NS 阵容被评"飘了？"；"这个阵容 又是要打架啊"</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NS</td><td>G1 狐狸/发条组合强势（"狐狸被ns屠杀"）；G2 阵容被评"飘"（云/朗姆奖励选）</td></tr>
    <tr><td>BFX</td><td>"没戏了"看衰 vs 主动阵容调整；G1 狐狸被批"菜的可怕"</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>LCK 骑士之路 BO5：0-1 落后方次局主动化调整样本（BFX）；观众对强队\u201c飘\u201d阵容敏感。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>16:39</td><td>"BFX没戏了，今天农心虐杀"（NS 2-0）</td><td>待 G2 结束回填</td></tr>
    <tr><td>16:40</td><td>"1-1红色方赢"（反方）</td><td>待 G2 结束回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000（合计 649 条，窗口 16:37–16:57 北京时间）。跨场闲聊已甄别。来源标签：本场弹幕（核心）/ 前局延续（§7）。待官方核对：G2 BP 阵容。</p>"""),
    ],
    "G2 BP 后/开局节点 2026-08-27 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g1_end.html", PAGE),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g2_bp.html", G2_BP),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)


G2_END = page(
    "LCK Play-In · NS vs BFX · G2 结束情报 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · G2（BFX 胜）",
    speed_block(
        "NS 1-1 BFX（G2 结束）",
        [("b-ok", "G2 结束 · 市场仲裁"), ("b-risk", "灰信号 28 条（演/剧本叙事）"), ("b-anchor", "BFX 翻盘扳平")],
        [
            sig("风险", "var(--bad)", '灰信号 28 条——"ns今天不演了""故意的""跟上昨天的剧本"（<b>非结论</b>）；BFX 赢 G2 → 详 §2'),
            sig("锚点", "var(--accent)", '"翻了翻了""翻盘了"（09:11/09:15）——BFX 翻盘拿下 G2；"打赢了不拿龙就是信号" → 详 §3'),
            sig("盘口", "var(--good)", "Polymarket Game 2 BFX 89.5c；系列 1-1 → 详 §4"),
            sig("共识", "var(--purple)", '"1-1红色方赢"（第二局 BP 的反方预期）<b>应验</b>，说明反方预期兑现 → 详 §5'),
        ],
        "BFX 翻盘扳平（系列 1-1）；BP 情报\u201c1-1红色方赢\u201d反方预期兑现；G2 灰信号（演/剧本）集中在扳平节点，兑现统计待回填。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5（系列 1-1）</td></tr>
    <tr><td>G2 结果</td><td><b>BFX 胜</b>（Polymarket Game 2 BFX 89.5c；弹幕"1-1""1比1"确认）</td></tr>
    <tr><td>节点</td><td>G2 · 结束（GAME-REVIEW）· <b>实时节点</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 17:05–17:27（北京时间）</td></tr>
    <tr><td>关键数据</td><td>2,636 条弹幕 · 910 活跃用户 · 密度 114.8 条/分（多源）</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000", "同左（LCK 默认集）", "窗口内各源覆盖；跨场闲聊已甄别")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>28 条</td><td>NS/BFX 演·剧本叙事（含"跟上昨天的剧本"）</td><td>"ns今天不演了" · "故意的，明显打不了打野飞什么" · "今日剧本谁一血谁输" · "果然 跟上昨天的剧本就行 二三局必死" · "11联赛不会买的跟上"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（观众"演/剧本"叙事在扳平局集中，含博彩叙事与玩梗；无盘口即时重合证据，非实锤）。兑现状态：BFX 赢 G2 扳平——\u201c被质疑方\u201d方向待兑现统计回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>BFX 主动阵容</td><td>"这把bfx要选主动阵容了"（G2 BP）</td><td>应验（BFX 主动翻盘拿下）</td></tr>
    <tr><td>NS 运营批评</td><td>"打赢了不拿龙就是信号"（09:12-14）· "打赢了团也不打龙？"</td><td>过程样本（NS 团后资源处理被批）</td></tr>
    <tr><td>BFX 翻盘</td><td>"翻了翻了"（09:11）· "翻盘了"（09:15）· "狐狸死一次就GG"</td><td>应验（BFX 翻盘）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Game 2 BFX 89.5c 结算方向与弹幕"1-1"一致；系列 1-1 后 G3 悬念。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>反方预期</td><td>BFX · G2</td><td>"1-1红色方赢"（G2 BP 弹幕）</td><td><b>应验</b>（BFX 扳平）</td></tr>
    <tr><td>负锚</td><td>NS · 运营</td><td>"打赢了不拿龙就是信号"（团后资源处理）</td><td>过程样本（NS 输 G2）</td></tr>
    <tr><td>灰信号</td><td>NS/BFX 演·剧本（28 条）</td><td>"跟上昨天的剧本""谁一血谁输"</td><td>兑现统计待回填（非实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：系列 1-1 回到均势；BFX 主动调整见效（G2 BP 情报兑现）；</li>
    <li><b>SHORT</b>：NS 团后资源处理（不拿龙）是 G3 观察项；灰信号"剧本/谁一血谁输"叙事升温，兑现统计待回填；</li>
    <li><b>观察点</b>：G3 BP、NS 运营修正、BFX 延续性。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>17:05–17:10</td><td>G2 中后段；观众预测 1-1（"相信我1:1 34分钟结束"）；NS 团后不拿龙被批</td></tr>
    <tr><td>17:11–17:15</td><td>BFX 翻盘信号（"翻了翻了""翻盘了"）；"1-1""1比1"确认（09:12-13 UTC）</td></tr>
    <tr><td>17:16–17:27</td><td>赛后：灰信号集中（"跟上昨天的剧本""谁一血谁输"）；BFX 打野/大菠萝话题</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>NS</td><td>团后不拿龙被批（"打赢了不拿龙就是信号"）；输 G2 被质疑"演"（灰信号）</td></tr>
    <tr><td>BFX</td><td>主动阵容翻盘扳平；打野被批（"BFX的打野真的是个大财B"）；"像wbg。下路没优势赢不了"（讨论）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>LCK 骑士之路 BO5：0-1 落后方次局主动化翻盘样本（BFX）；\u201c谁一血谁输\u201d局内叙事样本。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>G2 BP</td><td>"1-1红色方赢"（反方预期）</td><td><b>兑现</b>（BFX 扳平）</td></tr>
    <tr><td>09:00</td><td>"相信我1:1 34分钟结束"</td><td>兑现（1-1）</td></tr>
    <tr><td>G2 末段</td><td>灰信号 28 条（演/剧本）</td><td>兑现统计待回填（非实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000（合计 2,636 条，窗口 17:05–17:27 北京时间）。结果仲裁：Polymarket Game 2（BFX 89.5c）+ 弹幕"1-1"。来源标签：本场弹幕（核心）/ 前局延续（§7）/ 市场口径（§4）。待官方核对：G2 比分、MVP。</p>"""),
    ],
    "G2 结束节点 2026-08-27 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g1_end.html", PAGE),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g2_bp.html", G2_BP),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g2_end.html", G2_END),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)


G3_BP = page(
    "LCK Play-In · NS vs BFX · G3 BP 后/开局情报 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · G3（系列 1-1）",
    speed_block(
        "G3 进行中 · BP 后/开局",
        [("b-pend", "BP 后/开局节点"), ("b-risk", "灰信号 31 条（演/剧本叙事）"), ("b-anchor", "官方阵容已校准")],
        [
            sig("风险", "var(--bad)", '灰信号 31 条——"跟上昨天的剧本""谁一血谁输"（<b>非结论</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", "G3 官方阵容（Riot API 校准）：NS Syndra 中单 / BFX Azir 中单，NS 中野 Naafiri+Syndra 组合 → 详 §3"),
            sig("盘口", "var(--good)", "Polymarket Game 3 NS 领先（约 54.5c）→ 详 §4"),
            sig("共识", "var(--purple)", '"右边中野优势不是随便打"（NS 中野被看好）· 但"不控龙没大优势都得输" → 详 §5'),
        ],
        "G3 决胜关键局；官方阵容（非弹幕推断）已就位，NS 中野组合 vs BFX Azir 体系是主观察点；灰信号叙事延续。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5（系列 1-1）</td></tr>
    <tr><td>节点</td><td>G3 · BP 后 / 开局（EARLY-GAME）· <b>实时节点</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 17:08–17:42（北京时间；局间 + G3 BP）</td></tr>
    <tr><td>关键数据</td><td>3,531 条弹幕 · 1,180 活跃用户 · 密度 100.9 条/分</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000 + Riot 官方 window API（阵容）", "同左 + 官方数据源", "阵容为官方 API 校准（非弹幕推断）；跨场闲聊已甄别")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>31 条</td><td>NS/BFX 演·剧本叙事（延续）</td><td>"跟上昨天的剧本" · "今日剧本谁一血谁输" · "11联赛不会买的跟上" · "故意的，明显打不了打野飞什么" · "Ns把dns那个打野买了有的搞"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（观众\u201c演/剧本\u201d叙事连续三局升温，含博彩叙事与玩梗；无盘口即时重合证据，非实锤）。兑现统计待回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>队伍</th><th>官方阵容（Riot API window，2026-08-27 17:42 抓取）</th><th>说明</th></tr>
    <tr><td>NS（红）</td><td>Kingen Jax / Sponge Naafiri / Scout Syndra / Diable Varus / Lehends Nautilus</td><td>中野 Naafiri+Syndra 组合（观众"右边中野优势"）</td></tr>
    <tr><td>BFX（蓝）</td><td>Clear KSante / Raptor Olaf / VicLa Azir / Taeyoon Ashe / Kellin Seraphine</td><td>VicLa 换 Azir（G2 阿狸之后换体系）</td></tr>
  </table>
  <p class="meta">阵容以官方 window 数据为准（非弹幕推断）；弹幕英雄讨论（狐狸等）为 G2 回顾，不用于本局阵容配对（规则 22）。</p>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Game 3 NS 领先（约 54.5c）；系列 1-1 决胜盘口悬念大。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NS · 中野</td><td>"右边中野优势不是随便打"（Naafiri+Syndra）</td><td>待 G3 结束回填</td></tr>
    <tr><td>负锚（条件）</td><td>NS · 控龙</td><td>"右边不控龙没大优势都得输"（G2 教训延续）</td><td>待 G3 结束回填</td></tr>
    <tr><td>灰信号</td><td>NS/BFX 演·剧本（31 条）</td><td>"跟上昨天的剧本""谁一血谁输"</td><td>兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：NS 中野组合（官方确认）是 G3 主看点，市场 NS 领先；</li>
    <li><b>SHORT</b>：NS 控龙（G2 不拿龙教训）与灰信号叙事是变量；BFX Azir 体系能否延续 G2 翻盘势头；</li>
    <li><b>观察点</b>：G3 中段节奏、官方 gameWins 回填。</li>
  </ul>"""),
        ("7", "逐局复盘（G3 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>17:08–17:20</td><td>局间：回顾 G2（"还是1-1""狐狸游了这么多波"）；灰信号延续（"跟上昨天的剧本"）</td></tr>
    <tr><td>17:2x–17:42</td><td>G3 BP/开局：官方阵容锁定（NS Syndra 中野 / BFX Azir）；"右边中野优势"讨论</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径 + 官方阵容）</th></tr>
    <tr><td>NS Scout（中）</td><td>G3 Syndra（官方）；弹幕"盗圣当地缚灵"（G2 回顾）· "右边中野优势"</td></tr>
    <tr><td>BFX VicLa（中）</td><td>G3 Azir（官方；G2 阿狸——弹幕"狐狸"即指他，勿配给 Scout）</td></tr>
    <tr><td>NS/BFX 全队</td><td>灰信号叙事延续（演/剧本，非结论）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>LCK 骑士之路 BO5 决胜局；\u201c谁一血谁输\u201d局内叙事；Azir/Syndra 中单对决版本焦点。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>17:2x</td><td>"右边中野优势不是随便打"（NS 中野）</td><td>待 G3 结束回填</td></tr>
    <tr><td>17:3x</td><td>"不控龙没大优势都得输"（条件式）</td><td>待 G3 结束回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">弹幕：硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000（3,531 条，17:08–17:42 北京时间）；阵容：Riot 官方 window API（gameId 117030752644841580，17:42 抓取）。来源标签：阵容=官方源；共识/灰信号=本场弹幕。待官方核对：G3 比分。</p>"""),
    ],
    "G3 BP 后/开局节点 2026-08-27 · 官方阵容 + 弹幕口径 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    for name, html in (
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g1_end.html", PAGE),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g2_bp.html", G2_BP),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g2_end.html", G2_END),
        ("intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g3_bp.html", G3_BP),
    ):
        out = REPORTS / name
        out.write_text(html, encoding="utf-8")
        print("wrote", out)
