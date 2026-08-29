#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NS vs BFX 整场复盘（2026-08-27，BFX 3-1 NS，Polymarket 仲裁）。"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


FULL = page(
    "LCK Play-In · NS vs BFX · 整场复盘 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · BFX 3-1 NS",
    speed_block(
        "BFX 3-1 NS（BFX 晋级）",
        [("b-ok", "系列结束 · Polymarket 仲裁"), ("b-risk", "灰信号跨局累计约 50 条（演/剧本叙事）"), ("b-anchor", "BFX 连扳三局翻盘")],
        [
            sig("风险", "var(--bad)", '灰信号跨局累计约 50 条（G1 15 / G2 28 / G3 11）——观众"演/剧本"叙事随 BFX 连扳升温（<b>非结论</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", "G1 NS 发条皇子拿下 → G2 BFX 翻盘（\u201c1-1红色方赢\u201d应验）→ G3/G4 BFX Azir 体系终结 → 详 §3"),
            sig("盘口", "var(--good)", "Polymarket：G3/G4 BFX 99.95c、O/U3.5 Over、O/U4.5 Under（4 局结束）→ 详 §4"),
            sig("共识", "var(--purple)", '观众对 BFX"先演后赢/剧本"质疑跨局升温，但结果 BFX 3-1 晋级 → 详 §5'),
        ],
        "BFX 让一追三（3-1）翻盘 NS；观众\u201c演/剧本\u201d灰信号跨局约 50 条（非实锤，兑现统计待回填）；官方阵容/结果全程以 Polymarket+Riot API 仲裁。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5</td></tr>
    <tr><td>系列结果</td><td><b>BFX 3-1 NS（BFX 晋级）</b>——Polymarket 仲裁：G1 NS / G2-G4 BFX（各 99.95c）、O/U3.5 Over、O/U4.5 Under</td></tr>
    <tr><td>逐局</td><td>G1 NS 胜（发条皇子组合）· G2 BFX 翻盘（"1-1红色方赢"应验）· G3 BFX 胜（Azir）· G4 BFX 胜（终结）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 16:00–20:00（北京时间，多局）</td></tr>
    <tr><td>关键数据</td><td>多源弹幕（硕硕/957/米勒/记得/官方）+ Riot 官方阵容 + Polymarket 结算</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000 + Riot 官方 API + Polymarket", "同左 + 官方数据源", "G4 局中弹幕节点未完整产出（流水线未补，标注缺口）；整场结果以 Polymarket 仲裁为准")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>节点</th><th>条数</th><th>代表样本（意译）</th></tr>
    <tr><td>G1 局末</td><td>15</td><td>"bfx收钱了？" · "这加里奥肯定买了"</td></tr>
    <tr><td>G2 局末</td><td>28</td><td>"跟上昨天的剧本" · "今日剧本谁一血谁输" · "ns今天不演了"</td></tr>
    <tr><td>G3 窗口</td><td>11</td><td>"这不是故意送吗" · "梦魇打假赛" · "风暴龙翻盘剧本"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（观众\u201c演/剧本/买了\u201d叙事跨局约 50 条，含博彩叙事与玩梗；无盘口即时重合证据，非实锤）。兑现状态：BFX 连扳三局晋级——\u201c被质疑方（BFX）反而赢\u201d，与\u201c被质疑方输球\u201d模式相反，兑现统计待回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>局</th><th>官方阵容（Riot API）</th><th>关键锚点</th></tr>
    <tr><td>G1</td><td>NS 青钢影/皇子/发条/烬/慎；BFX 杰斯/盲僧/加里奥/女警/巴德</td><td>NS 发条皇子组合"太权威"（G1 收官）</td></tr>
    <tr><td>G2</td><td>NS 安蓓萨/梦魇/洛克/芸阿娜/璐璐；BFX 兰博/蔚/阿狸/EZ/扇子妈</td><td>BFX 主动阵容翻盘（"1-1红色方赢"应验）</td></tr>
    <tr><td>G3</td><td>NS Jax/Naafiri/Syndra/Varus/Nautilus；BFX KSante/Olaf/Azir/Ashe/Seraphine</td><td>BFX Azir 体系（弹幕"狐狸"为 G2 沿用，勿配对）</td></tr>
    <tr><td>G4</td><td>待官方核对（弹幕节点未完整产出）</td><td>BFX 终结局（Polymarket 99.95c）</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>Polymarket 系列口径：G1 NS / G2-G4 BFX（99.95c）、O/U3.5 Over、O/U4.5 Under → <b>4 局结束，BFX 3-1</b>。弹幕无明确数字盘。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚（G1）</td><td>NS · 发条皇子</td><td>G1 收官组合</td><td>兑现（G1 NS 胜）</td></tr>
    <tr><td>正锚（G2 反方）</td><td>BFX · 主动阵容</td><td>"1-1红色方赢"</td><td>兑现（G2 翻盘）</td></tr>
    <tr><td>负锚（NS）</td><td>NS · 控龙/推进</td><td>"打赢了不拿龙就是信号" · "大龙推进不了"</td><td>过程兑现（NS 连丢三局）</td></tr>
    <tr><td>灰信号</td><td>NS/BFX 演·剧本（约 50 条）</td><td>"跟上昨天的剧本"等</td><td>BFX 连扳——兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：BFX 3-1 晋级（市场一致）；\u201c0-1 落后方主动化翻盘\u201d样本（G2 后连扳三局）；</li>
    <li><b>SHORT</b>：NS 团后资源处理（不拿龙）+ 推进乏力是连败主线；灰信号"剧本"叙事集中在 BFX 连扳局，兑现统计待回填；</li>
    <li><b>观察点</b>：官方逐局比分/MVP、G4 阵容补核、灰信号兑现率。</li>
  </ul>"""),
        ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>内容（弹幕口径 + 官方）</th></tr>
    <tr><td>G1 13-x（NS）</td><td>NS 发条皇子收官（"组合技太权威"）；BFX 加里奥/杰斯被批；灰信号 15 条</td></tr>
    <tr><td>G2（BFX）</td><td>BFX 主动阵容翻盘（"翻了翻了""1-1"）；NS 团后不拿龙被批；灰信号 28 条</td></tr>
    <tr><td>G3（BFX）</td><td>BFX Azir 体系；NS 中野 Syndra 优势但推进乏力（"大龙推进不了"）；灰信号 11 条</td></tr>
    <tr><td>G4（BFX）</td><td>BFX 终结（Polymarket 99.95c）；弹幕节点未完整产出（缺口标注）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径 + 官方）</th></tr>
    <tr><td>BFX</td><td>让一追三晋级；VicLa 阿狸→Azir 体系调整见效；"先演后赢"灰信号叙事（非结论）</td></tr>
    <tr><td>NS</td><td>G1 强势后连丢三局；团后不拿龙/推进乏力被批；Scout（中）G1 发条→G3 Syndra 高光不足</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>LCK 骑士之路（Play-In）BO5：0-1 落后方主动化翻盘样本（BFX 连扳三局）；</li>
    <li>\u201c谁一血谁输\u201d局内叙事；Azir/Syndra 中单对决版本焦点；</li>
    <li>灰信号\u201c被质疑方反而赢\u201d（BFX）——兑现统计待积累。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>G2 BP</td><td>"1-1红色方赢"（反方预期）</td><td>兑现（G2 BFX 扳平）</td></tr>
    <tr><td>G1 局末</td><td>NS 发条皇子收官</td><td>兑现（G1 NS 胜）</td></tr>
    <tr><td>G2 末段</td><td>灰信号 28 条（演/剧本）</td><td>BFX 连扳——兑现统计待回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">弹幕：硕硕 323444 + 957 890001 + 米勒 149361 + 记得 + LOL 官方 660000（多局）；阵容/结果：Riot 官方 API + Polymarket 结算（G1-G4 仲裁）。缺口：G4 局中弹幕节点未完整产出（标注）。来源标签：阵容/结果=官方源；共识/灰信号=本场弹幕。待官方核对：逐局比分、MVP、G4 阵容。</p>"""),
    ],
    "整场复盘 2026-08-27 · 官方仲裁 + 弹幕口径 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27.html"
    out.write_text(FULL, encoding="utf-8")
    print("wrote", out)
