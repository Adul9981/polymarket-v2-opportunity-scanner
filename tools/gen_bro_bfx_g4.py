#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HANJIN BRION vs BNK FEARX G4 BP 后/局中情报（2026-08-28，LCK 入围赛 BO5）。

官方（Riot getEventDetails + window）：系列 BRO 2-1 BFX（G1 BFX、G2/G3 BRO），
G4 inProgress（BP 已结束）。G4 官方阵容（window）：
BRO 蓝 Renekton/Pantheon/Ahri/Xayah/Lulu；BFX 红 Aatrox/Maokai/Orianna/Yunara/Nautilus。
数据源：硕硕单路（用户指定本场只采硕硕）。
"""

from pathlib import Path

from gen_fut_legacy_g1_end import page  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


SPEED = """
  <div class="top">
    <span class="score-big">G4 进行中 · BRO 2-1 BFX（赛点局）</span>
    <span class="badge b-ok">官方系列比分 2-1</span>
    <span class="badge b-anchor">官方阵容已校准</span>
    <span class="badge b-risk">灰信号（G2/G3 尾段·观众质疑非结论）</span>
  </div>
  <div style="margin-top:8px">
    <div class="sig"><span class="tag" style="color:var(--accent)">锚点</span><span><b>G4 官方阵容：BRO 鳄鱼/潘森/阿狸/霞/璐璐 vs BFX 剑魔/茂凯/发条/芸阿娜/泰坦</b>；弹幕核心：BRO 选霞被质疑（"霞团战咋玩"）、BFX 红方阵容被夸扎实（"有大树有泰坦有发条，30分钟不知道怎么输"） <span class="meta">→ 详 §3/§5/§8</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--bad)">风险</span><span><b>灰信号（观众质疑·非结论）</b>：G2 尾段"演/做任务" + G3 尾段"故意送 任务"（单条）——<b>无实锤，不上升结论</b> <span class="meta">→ 详 §2</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--purple)">共识</span><span><b>弹幕多数预期 BRO 3-1 带走</b>："3-1""3比1带走了""出剑魔那才是要3：1结束"——<b>意味着 BRO 若 G4 拿下即晋级，BFX 需赢下 G4 拖入决胜局</b> <span class="meta">→ 详 §5/§6</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--sub)">盘口</span><span><b>弹幕无数字盘</b>；观众在讨论阵容优劣（"豆包说左边阵容好到发瘟" vs "右边太扎实"）→ 详 §4</span></div>
  </div>
  <div class="errbox"><b>节点说明：</b>本页为 G4 BP 后/局中节点。官方系列 BRO 2-1（G1 BFX 胜、G2/G3 BRO 胜）；G4 官方阵容已用 Riot window 校准；G3 复盘：BFX 上单薇恩被批、BRO 杰斯阵容翻盘拿下。</div>
"""


SECTIONS = [
    ("1", "比赛信息与状态（官方源）", """<table>
    <tr><td>对阵</td><td><b>HANJIN BRION（BRO）</b> vs <b>BNK FEARX（BFX）</b> · LCK 入围赛 · BO5</td></tr>
    <tr><td>系列状态（官方）</td><td><b>BRO 2-1 BFX</b>（Riot getEventDetails gameWins）：G1 BFX 胜（轮子妈一波）· G2 BRO 胜（BFX 卡莉斯塔+打野送）· G3 BRO 胜（BRO 杰斯阵容团战翻盘，BFX 薇恩上单被批）</td></tr>
    <tr><td>G4 状态</td><td><b>进行中（inProgress，官方）</b>· BP 已结束 · BRO 赛点局</td></tr>
    <tr><td>G4 官方阵容</td><td><b>BRO（蓝）</b>：Casting 鳄鱼 / GIDEON 潘森 / Roamer 阿狸 / Teddy 霞 / Namgung 璐璐；<b>BFX（红）</b>：Clear 剑魔 / Raptor 茂凯 / VicLa 发条 / Taeyoon 芸阿娜 / Kellin 泰坦</td></tr>
    <tr><td>情报输出时间</td><td><b>2026-08-28 18:50（北京时间）</b></td></tr>
    <tr><td>弹幕采集时间</td><td>2026-08-28 18:34–18:50（北京时间，G4 BP + 开局）</td></tr>
    <tr><td>数据源</td><td>硕硕直播间（虎牙 323444，用户指定本场单路）· 官方源：Riot API（阵容/比分）</td></tr>
    <tr><td>完整性</td><td><span class="badge b-ok">硕硕单路</span>其他直播间按用户要求未采集；事实层（阵容/比分）由官方源仲裁</td></tr>
  </table>"""),
    ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<p><b>累计灰信号（观众质疑·非结论）</b>：</p>
  <ul>
    <li><b>G2 尾段</b>（17:26-17:28）："演员队""就为了演大头，也是没谁了""做任务32分钟"——BFX 领先后拖沓被嘲讽</li>
    <li><b>G3 尾段</b>（18:07）："尼玛故意跟人家打 故意送 任务，，"（单条，BRO 团战翻盘语境）</li>
    <li>G4 BP 阶段暂无明显灰信号指控</li>
  </ul>
  <div class="warnbox"><b>纪律声明：</b>以上均为观众质疑/玩梗，<b>非假赛证据</b>；按灰信号纪律仅作风险标注、不上升结论。若后续出现明确指控或盘口异动，升级重点监控。</div>"""),
    ("3", "BP 与选人情报（官方校准）", """<p><b>✅ G4 官方阵容（Riot window，开局后校准）：</b></p>
  <table>
    <tr><th>位置</th><th>BRO（蓝）</th><th>BFX（红）</th></tr>
    <tr><td>上路</td><td>Casting 鳄鱼（Renekton）</td><td>Clear 剑魔（Aatrox）</td></tr>
    <tr><td>打野</td><td>GIDEON 潘森（Pantheon）</td><td>Raptor 茂凯（Maokai）</td></tr>
    <tr><td>中单</td><td>Roamer 阿狸（Ahri）</td><td>VicLa 发条（Orianna）</td></tr>
    <tr><td>下路</td><td>Teddy 霞（Xayah）</td><td>Taeyoon 芸阿娜（Yunara）</td></tr>
    <tr><td>辅助</td><td>Namgung 璐璐（Lulu）</td><td>Kellin 泰坦（Nautilus）</td></tr>
  </table>
  <p class="meta">弹幕对位讨论：BRO 选霞被质疑（"霞不好啊""霞团战咋玩""有这么多选择一定要玩个逼霞"）；BFX 红方前排控制扎实（"有大树，有泰坦，有发条，你告诉我被拉扯""太扎实了右边阵容。30分钟不知道怎么输"）；剑魔后期被看好（"剑魔20分钟后砍疯"）；VicLa 发条（"大光发条能赢"）与自 ban 阿卡丽被讨论。</p>"""),
    ("4", "盘口与市场讨论", """<ul>
    <li>弹幕无明确数字盘（<b>样本不足</b>）。</li>
    <li>BP 阶段观众在问 AI/豆包阵容预测（"豆包说左边阵容好到发瘟"）与自行比较两边阵容（"这把谁阵容好一点"）——情绪面，非盘口。</li>
    <li>"3-1""3比1带走了"为观众对系列结果的预期表达，非赔率。</li>
  </ul>"""),
    ("5", "方向性情报板（锚点 × 共识 × 风险）", """<table>
    <tr><th>维度</th><th>BRO（蓝）</th><th>BFX（红）</th></tr>
    <tr><td>G4 阵容</td><td>鳄鱼/潘森/阿狸/霞/璐璐——前中期节奏强、开团靠潘森/阿狸</td><td>剑魔/茂凯/发条/芸阿娜/泰坦——前排控制扎实、后期团战强（"30分钟不知道怎么输"）</td></tr>
    <tr><td>系列状态</td><td><b>2-1 领先（官方）</b>，G4 赛点局；G3 杰斯阵容翻盘拿下</td><td>1-2 落后，G4 必须赢拖入决胜局</td></tr>
    <tr><td>局中/BP 信号（弹幕口径）</td><td>选霞被质疑（"霞团战咋玩"）；"左边阵容好到发瘟"（AI 口径，单方）</td><td>红方阵容被多数认可（"太扎实了"）；剑魔后期强；发条发育起来难处理</td></tr>
    <tr><td>反方声音</td><td>"豆包说左边阵容好到发瘟"（AI 看好 BRO）</td><td>"云安娜/发条/狗头放两条龙发育"（前期乏力风险被点出）</td></tr>
    <tr><td>共识</td><td colspan="2">弹幕多数预期 BRO 3-1 带走（"3-1""3比1带走了"）；BFX 需赢 G4 拖入决胜局</td></tr>
  </table>"""),
    ("6", "情报含义与决策落点", """<ul>
    <li><b>短期：</b>BRO 2-1 领先（官方），G4 赛点局；弹幕共识：BFX 红方阵容扎实（后期团战强）、BRO 霞选择被质疑——<b>局中博弈点：BRO 前中期节奏 vs BFX 后期团战</b>。</li>
    <li><b>方向信号：</b>弹幕多数预期 BRO 3-1；但 BP 讨论中 BFX 阵容口碑更好（前排控制+发条+剑魔）——若 BFX 拖到后期，存在变数。</li>
    <li><b>风险提示：</b>灰信号（G2/G3 尾段，观众质疑·非结论）；G4 局中状态为弹幕口径，最终以官方结算仲裁。</li>
    <li><b>观察点：</b>BRO 潘森/阿狸前中期能否滚雪球、BFX 发条/剑魔发育、龙团节奏；若 BFX 拿下 G4 则进决胜局 G5。</li>
  </ul>"""),
    ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>结果</th><th>内容（弹幕口径）</th></tr>
    <tr><td>G1</td><td><b>BFX 胜</b></td><td>Taeyoon 轮子妈不死一波带走；BFX 低水无痛拿下</td></tr>
    <tr><td>G2</td><td><b>BRO 胜</b></td><td>BFX 卡莉斯塔阵亡即崩；打野两波送；尾段 BFX 拖沓被嘲"演/做任务"</td></tr>
    <tr><td>G3</td><td><b>BRO 胜</b></td><td>BRO 杰斯阵容团战翻盘（"翻了翻了/一波打回来了"）；BFX 上单薇恩被狂批（"菜逼还选vn""vn落后40刀"）；观众"3-1结束"</td></tr>
    <tr><td>G4（进行中）</td><td>待回填</td><td>BRO 蓝方选霞被质疑、BFX 红方扎实（18:34-18:50 弹幕）</td></tr>
  </table>"""),
    ("8", "队伍 / 人员画像（证据层 · 官方 + 弹幕口径）", """<p><b>BRO：</b>2-1 领先（官方）；G3 杰斯阵容翻盘拿下（"今天巨魔全胜，选出来就是赢"）；G4 蓝色方选鳄鱼/潘森/阿狸/霞/璐璐——前中期节奏型（弹幕质疑霞的团战能力）；Teddy 连续两局被针对后 G4 换霞。</p>
  <p><b>BFX：</b>1-2 落后；G3 上单 Clear 薇恩被狂批（"vn落后40刀""菜逼还选vn"）；G4 红方选剑魔/茂凯/发条/芸阿娜/泰坦——前排控制扎实（"太扎实了，30分钟不知道怎么输"）；VicLa 发条（"大光发条能赢"）与自 ban 阿卡丽被讨论。</p>
  <p><b>周边：</b>"T1 选 KT 还是 BRO"（后续对阵猜测）· "3-1结束"（观众系列预期）。</p>"""),
    ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>LCK 入围赛 BO5：BRO 让一追二后拿赛点；G4 选边与阵容节奏（BRO 前中期 vs BFX 后期团战）成关键。</li>
    <li>薇恩上单（G3 BFX Clear）在观众口径中属于高风险选择（"养个爹""选出来就是送"）——上单射手需打野/团队保护，未兑现即崩。</li>
    <li>红色方前排控制流（茂凯/泰坦/发条）在弹幕口碑中"扎实"——后期团战容错高，前期需让资源发育。</li>
  </ul>"""),
    ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>预测/锚点</th><th>状态</th></tr>
    <tr><td>"这把打完2-1了"（G3 中段，观众预期 BRO 赢 G3 → 2-1）</td><td><b>兑现</b>（官方 BRO 2-1）</td></tr>
    <tr><td>"3-1结束"（G3 尾段/G4 BP 观众预期）</td><td>待 G4 结果回填（弹幕口径）</td></tr>
    <tr><td>"今天巨魔全胜，选出来就是赢"（G3 打野锚点）</td><td><b>兑现</b>（G3 BRO 巨魔胜）</td></tr>
    <tr><td>灰信号（G2/G3 尾段"演/做任务/故意送"）</td><td>待终局回填（观众质疑·非结论）</td></tr>
  </table>"""),
    ("11", "数据与溯源", """<p><b>官方源</b>：Riot getEventDetails（match 117030752644841583）：BRO 2 / BFX 1，G4 inProgress；G4 window（117030752644841587）官方阵容（开局后校准）。</p>
  <p class="meta"><b>弹幕源</b>：硕硕直播间（虎牙 323444），会话 lck_bro_bfx_2026-08-28；G4 窗口 18:34-18:50 北京（BP + 开局）。</p>
  <p class="meta"><b>完整性</b>：本场按用户指定只采硕硕；其他直播间未采集（非缺口，属设定）；事实层以官方为准。</p>
  <p class="meta"><b>情报输出时间</b>：2026-08-28 18:50 CST · 弹幕采集截止：18:50 CST · 情报原则：核心=本场弹幕，事实层=官方源仲裁，推测显式标注。</p>"""),
]


G4 = page(
    "LCK 入围赛 · BRO vs BFX · G4 BP 后/局中情报 · 2026-08-28",
    "LoL · LCK 入围赛 · BO5 · 系列 BRO 2-1 BFX（赛点局）· G4 进行中",
    SPEED,
    SECTIONS,
    "弹幕情报 · 观众质疑非结论 · 阵容/比分以官方源为准 · Polymarket 电竞情报项目",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_HANJIN BRION-BNK FEARX_2026-08-28_g4_bp.html"
    out.write_text(G4, encoding="utf-8")
    print("wrote", out)
