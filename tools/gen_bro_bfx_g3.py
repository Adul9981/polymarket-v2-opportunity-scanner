#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HANJIN BRION vs BNK FEARX G3 BP 后/局中情报（2026-08-28，LCK 入围赛 BO5）。

官方（Riot getEventDetails + window）：系列 1-1（BFX 1 / BRO 1），G3 inProgress。
G3 阵容（官方 window）：BRO 蓝 Kennen/Trundle/Jayce/Draven/Milio；
BFX 红 Vayne/Wukong/Galio/Lucian/Yuumi。
数据源：硕硕单路（用户指定本场只采硕硕）。
"""

from pathlib import Path

from gen_fut_legacy_g1_end import page  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


SPEED = """
  <div class="top">
    <span class="score-big">G3 进行中 · 系列 1-1（决胜局）</span>
    <span class="badge b-ok">官方系列比分 1-1</span>
    <span class="badge b-anchor">官方阵容已校准</span>
    <span class="badge b-risk">灰信号（G2 尾段·观众质疑非结论）</span>
  </div>
  <div style="margin-top:8px">
    <div class="sig"><span class="tag" style="color:var(--accent)">锚点</span><span><b>G3 官方阵容：BRO 凯南/巨魔/杰斯/德莱文/米利欧 vs BFX 薇恩/悟空/加里奥/卢锡安/悠米</b>；弹幕核心：BRO 下路德莱文被针对炸（"下路炸了""德子废了"）、中单杰斯被质疑、BFX 猴子带悠米体系被认可 <span class="meta">→ 详 §3/§5/§8</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--bad)">风险</span><span><b>灰信号（观众质疑·非结论）</b>：G2 尾段"演员队/演大头/做任务32分钟"（BFX 迟迟不结束比赛被嘲讽）+ G3 开局"被庄家盯上"ID 玩梗——<b>无实锤，不上升结论</b> <span class="meta">→ 详 §2</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--purple)">共识</span><span><b>弹幕多数看衰 BRO</b>："左边没了""下路玩不了了""德莱文待会被洗晕"——<b>意味着 G3 若 BRO 下路继续崩，BFX 2-1 赛点预期强化</b> <span class="meta">→ 详 §5/§6</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--sub)">盘口</span><span><b>弹幕无数字盘</b>；G2 尾段观众在算大龙/龙魂与大/小（"大28.5稳不稳"）；G3 无盘口弹幕 → 详 §4</span></div>
  </div>
  <div class="errbox"><b>节点说明：</b>本页为 G3 BP 后/局中节点。官方系列 1-1（G1 BFX 胜·轮子妈一波、G2 BRO 胜·BFX 卡莉斯塔+打野送）；G3 官方阵容已用 Riot window 校准；本场按用户指定只采硕硕直播间。</div>
"""


SECTIONS = [
    ("1", "比赛信息与状态（官方源）", """<table>
    <tr><td>对阵</td><td><b>HANJIN BRION（BRO）</b> vs <b>BNK FEARX（BFX）</b> · LCK 入围赛 · BO5</td></tr>
    <tr><td>系列状态（官方）</td><td><b>1-1</b>（BFX 1 / BRO 1，Riot getEventDetails gameWins）：G1 BFX 胜（Taeyoon 轮子妈一波带走）· G2 BRO 胜（BFX 卡莉斯塔阵亡 + 打野两波送）</td></tr>
    <tr><td>G3 状态</td><td><b>进行中（inProgress，官方）</b>· BP 已结束 · 决胜局</td></tr>
    <tr><td>G3 官方阵容</td><td><b>BRO（蓝）</b>：Casting 凯南 / GIDEON 巨魔 / Roamer 杰斯 / Teddy 德莱文 / Namgung 米利欧；<b>BFX（红）</b>：Clear 薇恩 / Raptor 悟空 / VicLa 加里奥 / Taeyoon 卢锡安 / Kellin 悠米</td></tr>
    <tr><td>情报输出时间</td><td><b>2026-08-28 18:05（北京时间）</b></td></tr>
    <tr><td>弹幕采集时间</td><td>2026-08-28 17:28–18:05（北京时间，G3 BP 尾段 + 局中）</td></tr>
    <tr><td>数据源</td><td>硕硕直播间（虎牙 323444，用户指定本场单路）· 官方源：Riot API（阵容/比分）</td></tr>
    <tr><td>完整性</td><td><span class="badge b-ok">硕硕单路</span>其他直播间按用户要求未采集；事实层（阵容/比分）由官方源仲裁</td></tr>
  </table>"""),
    ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<p><b>本场灰信号集中在 G2 尾段</b>（17:26-17:28，BFX 领先却迟迟不结束比赛）：</p>
  <ul>
    <li>"演员队""就为了演大头，也是没谁了""右边就像在做任务一样，大龙不去打""给我拖到32分钟"——观众嘲讽 BFX 不结束比赛、疑似拖延</li>
    <li>"这跟第一把是一个队我我真不信"（BFX 前后两局表现反差）· "泰勇真能送啊"（Taeyoon 被批）</li>
    <li>G3 开局少量玩梗："被庄家盯上的人"（ID，非指控）</li>
  </ul>
  <div class="warnbox"><b>纪律声明：</b>以上均为观众质疑/玩梗（语境：BFX G2 领先后节奏拖沓被嘲讽），<b>非假赛证据</b>；按灰信号纪律仅作风险标注、不上升结论。</div>"""),
    ("3", "BP 与选人情报（官方校准）", """<p><b>✅ G3 官方阵容（Riot window，开局后校准）：</b></p>
  <table>
    <tr><th>位置</th><th>BRO（蓝）</th><th>BFX（红）</th></tr>
    <tr><td>上路</td><td>Casting 凯南（Kennen）</td><td>Clear 薇恩（Vayne）</td></tr>
    <tr><td>打野</td><td>GIDEON 巨魔（Trundle）</td><td>Raptor 悟空（MonkeyKing）</td></tr>
    <tr><td>中单</td><td>Roamer 杰斯（Jayce）</td><td>VicLa 加里奥（Galio）</td></tr>
    <tr><td>下路</td><td>Teddy 德莱文（Draven）</td><td>Taeyoon 卢锡安（Lucian）</td></tr>
    <tr><td>辅助</td><td>Namgung 米利欧（Milio）</td><td>Kellin 悠米（Yuumi）</td></tr>
  </table>
  <p class="meta">BP 阶段硕硕房弹幕稀疏（转场安静）；官方阵容为事实层唯一口径。弹幕对位讨论：德莱文 vs 卢锡安+悠米（"下路德莱文打奥巴马猫，前期没优势后期被吊打"）；"左边五个人凑不出一个位移"（BRO 阵容机动性低）。</p>"""),
    ("4", "盘口与市场讨论", """<ul>
    <li>弹幕无明确数字盘（<b>样本不足</b>）。</li>
    <li>G2 尾段观众在讨论大龙/龙魂与大/小盘（"大28.5稳不稳""大27.5没了，家放了"）——G2 结果相关，非 G3 盘口。</li>
    <li>G3 开局无盘口弹幕；后续如出现大额单/赔率提及再补录。</li>
  </ul>"""),
    ("5", "方向性情报板（锚点 × 共识 × 风险）", """<table>
    <tr><th>维度</th><th>BRO（蓝）</th><th>BFX（红）</th></tr>
    <tr><td>G3 阵容</td><td>凯南/巨魔/杰斯/德莱文/米利欧——强对线但机动性低、开团依赖凯南/巨魔</td><td>薇恩/悟空/加里奥/卢锡安/悠米——猴子带猫（"是不是无敌？"）+ 中野支援强</td></tr>
    <tr><td>局中信号（弹幕口径）</td><td>下路德莱文被针对炸（"下路炸了""德子废了""德莱文太菜"）；巨魔逛街（"巨魔还在逛""不抓人有啥用"）；中单杰斯被质疑（"有卵用"）</td><td>下路卢锡安+悠米压制（"奥巴马猫"）；猴子体系被认可；加里奥被嘲"1-9 胜率"但中野节奏在 BFX 侧</td></tr>
    <tr><td>反方声音</td><td>"杰斯不是一直在赢吗"（反驳）· "经济没多少领先，一个头就翻"（仍有翻盘点）</td><td>"维克拉的加里奥没赢过，0胜率"（VicLa 加里奥被质疑）</td></tr>
    <tr><td>共识</td><td colspan="2">弹幕多数看衰 BRO（"左边没了""下路玩不了了"）；"这把打完2-1了"——若 G3 BRO 下路继续崩，BFX 2-1 拿赛点</td></tr>
  </table>"""),
    ("6", "情报含义与决策落点", """<ul>
    <li><b>短期：</b>系列 1-1 决胜局（官方）；G3 局中弹幕口径 BRO 下路崩（德莱文被针对）、BFX 占优——<b>若维持，BFX 2-1 拿赛点</b>。</li>
    <li><b>方向信号：</b>弹幕共识倒向 BFX（下路对位 + 猴子体系 + BRO 阵容机动性差）；G3 开局"一波了/翻了"密集出现在 BRO 下路团战。</li>
    <li><b>风险提示：</b>灰信号（G2 尾段"演/做任务"，观众质疑·非结论）；G3 局中状态为弹幕口径，最终以官方结算仲裁。</li>
    <li><b>观察点：</b>BRO 德莱文能否被保起来（巨魔是否开始照顾下路）、BFX 猴子带猫中野节奏、VicLa 加里奥 0-4 后是否稳住。</li>
  </ul>"""),
    ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>结果</th><th>内容（弹幕口径）</th></tr>
    <tr><td>G1</td><td><b>BFX 胜</b></td><td>Taeyoon 轮子妈不死一波带走（16:39-16:41"轮子妈不死就一波了""早说了一波了"）；BFX 低水无痛拿下</td></tr>
    <tr><td>G2</td><td><b>BRO 胜</b></td><td>BFX 卡莉斯塔阵亡即崩（17:05"卡莉斯塔一死就没了"）；打野两波操作送掉（17:26"打野两波操作把游戏整没了"）；尾段 BFX 迟迟不结束被嘲"演/做任务"</td></tr>
    <tr><td>G3（进行中）</td><td>待回填</td><td>BRO 下路德莱文被针对炸（"下路炸了""德子废了"）；巨魔逛街、杰斯被质疑；BFX 猴子+悠米体系占优（18:00 弹幕爆发）</td></tr>
  </table>"""),
    ("8", "队伍 / 人员画像（证据层 · 官方 + 弹幕口径）", """<p><b>BRO：</b>G1 告负后 G2 扳回（"bro经典让一追二"叙事）；G3 蓝色方选强对线下路（Teddy 德莱文）但被针对（"选德莱文是什么意思""德子废了"）；GIDEON 巨魔被批"逛街"；Roamer 杰斯中单被质疑（"这阵容中单杰斯有卵用"）。</p>
  <p><b>BFX：</b>G1 轮子妈体系拿下；G2 卡莉斯塔阵亡崩盘（"泰勇真能送"）；G3 下路卢锡安+悠米（Taeyoon+Kellin）压制、Raptor 悟空带猫体系被认可；VicLa 加里奥被嘲"0胜率/1-9"（弹幕口径）但中野节奏在 BFX 侧。</p>
  <p><b>周边：</b>"昨天打大根打出自信了"（BFX 状态延续）；"第二局送的莫名其妙"（G2 复盘吐槽）。</p>"""),
    ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>LCK 入围赛 BO5：1-1 后决胜局，选边与阵容机动性成关键（BRO 蓝色方低机动阵容被弹幕点名）。</li>
    <li>德莱文体系需要下路照顾：Teddy 德莱文被针对（巨魔不保下）→ 弹幕"德莱文需要照顾，但是被照顾就没了"。</li>
    <li>BFX 双 C 风格延续：轮子妈/卢锡安类站撸 AD + 保护辅（Karma/Yuumi）——G1/G3 同一体系思路。</li>
  </ul>"""),
    ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>预测/锚点</th><th>状态</th></tr>
    <tr><td>"2-0犯法？"（G2 中段观众预期某队 2-0）</td><td><b>未兑现</b>（官方 1-1，G2 BRO 扳回）</td></tr>
    <tr><td>"bro经典让一追二"（BRO 追回叙事）</td><td><b>部分兑现</b>（G2 扳回 1-1；G3 待定）</td></tr>
    <tr><td>G3 弹幕多数看衰 BRO（下路崩）</td><td>待 G3 结果回填（弹幕口径）</td></tr>
    <tr><td>灰信号（G2 尾段"演/做任务"）</td><td>待终局回填（观众质疑·非结论）</td></tr>
  </table>"""),
    ("11", "数据与溯源", """<p><b>官方源</b>：Riot getEventDetails（match 117030752644841583）：BFX 1 / BRO 1，G3 inProgress；G3 window（117030752644841586）官方阵容（BP 后开局即有数据）。</p>
  <p class="meta"><b>弹幕源</b>：硕硕直播间（虎牙 323444），会话 lck_bro_bfx_2026-08-28；G3 窗口 17:28-18:05 北京（BP 尾段稀疏、局中 18:00 爆发）。</p>
  <p class="meta"><b>完整性</b>：本场按用户指定只采硕硕；其他直播间未采集（非缺口，属设定）；事实层以官方为准。</p>
  <p class="meta"><b>情报输出时间</b>：2026-08-28 18:05 CST · 弹幕采集截止：18:05 CST · 情报原则：核心=本场弹幕，事实层=官方源仲裁，推测显式标注。</p>"""),
]


G3 = page(
    "LCK 入围赛 · BRO vs BFX · G3 BP 后/局中情报 · 2026-08-28",
    "LoL · LCK 入围赛 · BO5 · 系列 1-1（决胜局）· G3 进行中",
    SPEED,
    SECTIONS,
    "弹幕情报 · 观众质疑非结论 · 阵容/比分以官方源为准 · Polymarket 电竞情报项目",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_HANJIN BRION-BNK FEARX_2026-08-28_g3_bp.html"
    out.write_text(G3, encoding="utf-8")
    print("wrote", out)
