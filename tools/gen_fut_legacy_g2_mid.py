#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FUT vs Legacy G2 局中情报（2026-08-27，图二 Dust II 沙二）。

按线上参考标准（intel_danmu_CS2-FUT-Legacy_G2_2026-08-27.html）格式。
官方系列：Legacy 1-0 FUT（图一 Ancient 13:10）；图二 Dust II 进行中、Legacy 大比分压制。
数据窗口 23:36-23:52 北京时间，三路源。
"""

from pathlib import Path

from gen_fut_legacy_g1_end import page  # noqa: E402  (共享样式/渲染)

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


SPEED = """
  <div class="top">
    <span class="score-big">G2 局中 · Legacy 大比分压制（沙二）· 系列 FUT 0-1 Legacy</span>
    <span class="badge b-ok">官方系列比分确认</span>
    <span class="badge b-anchor">图二 Dust II · Legacy 选图</span>
    <span class="badge b-risk">灰信号 15 条（图一 12 + 图二 3）· 两房共振</span>
  </div>
  <div style="margin-top:8px">
    <div class="sig"><span class="tag" style="color:var(--accent)">锚点</span><span><b>狙击手差距是全场胜负手</b>：Legacy try（图一官方 26-9/+17）vs FUT cmtry（图一 14-18），图二"敌我狙击手差距太大"刷屏；FUT 沙二没战术（"怪不得FUT ban沙2"） <span class="meta">→ 详 §3/§5/§8</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--bad)">风险</span><span><b>FUT 图二被打崩 + 灰信号簇</b>：图一 12 条（23:07-23:16）+ 图二 BLAST 房"吃菠菜/吃菜/剧本"3 条（23:49-23:51）——<b>观众质疑·非结论</b> <span class="meta">→ 详 §2</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--purple)">共识</span><span><b>"菊花王朝"叙事刷屏</b>："菊花真的太猛了""猎鹰&lt;FUT&lt;菊花"；胜者路径聚焦 Falcons（"菊花三擒猎鹰"） <span class="meta">→ 详 §5/§6</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--sub)">盘口</span><span><b>大额单线索延续（$132,997，~59%，21:35）</b>方向待确认；图二投注情绪（"菊花让老子输了1000+"）→ 详 §4</span></div>
  </div>
  <div class="errbox"><b>节点说明：</b>本页为 G2 局中节点。图一已按 BLAST 官方源修正为 <b>Legacy 1-0 FUT（Ancient 13:10）</b>（详见 G1 结束页）；图二 Dust II 进行中，Legacy 大比分压制（弹幕口径"13比0来！！"），官方逐回合比分待核对。</div>
"""


SECTIONS = [
    ("1", "比赛信息与状态（官方源）", """<table>
    <tr><td>对阵</td><td>FUT（EWC 亚军）vs Legacy（菊花，EWC 季军）· BLAST Premier Open Porto 2026 小组赛 B 组 · BO3 · 胜者组八强（UB QF3）</td></tr>
    <tr><td>官方时间</td><td>2026-08-27 22:30 CST 开赛 · hltv match 2396929 · BLAST match fcc5ce44</td></tr>
    <tr><td>官方地图</td><td>图一 <b>Ancient</b>（Legacy 13:10 结束）· 图二 <b>Dust II</b>（进行中）· 图三 Cache（候选）</td></tr>
    <tr><td>系列状态（官方）</td><td><b>Legacy 1 - 0 FUT</b>（图一官方）；图二 Dust II 进行中，弹幕口径 Legacy 大比分压制（"13比0来！！""图二直接被虐了啊fut"）</td></tr>
    <tr><td>今日同组赛果</td><td>17:00 IC 2-0 Vitality（爆冷）· 20:00 MOUZ 2-0 9z（Cache 13:4 / Nuke 13:7）· 00:30 Falcons vs LVG（未开）</td></tr>
    <tr><td>弹幕规模</td><td>G2 局中窗口（23:36-23:52）弹幕密集：狙击手对比簇（"敌我狙击手/两个try/厘米try"）117+ 条；FUT 崩盘吐槽持续</td></tr>
    <tr><td>完整性</td><td><span class="badge b-ok">三路齐采</span>系列比分 = BLAST 官方页（23:32 抓取）；图二局中比分 = 弹幕口径（官方逐回合待核对）</td></tr>
  </table>
  <p class="meta">系列/图一比分 = BLAST 官方页（2026-08-27 23:32 抓取）；图二局中比分以弹幕口径为主，官方 window 刷新后校准。</p>"""),
    ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<p><b>累计 15 条</b>，两房共振：</p>
  <ul>
    <li><b>图一 12 条</b>（CSBOY 官方 9 + BLAST 官方 3，23:07-23:16，FUT 输选图段）："到底在演什么剧本啊""感觉就是在演比分啊""演的吧""故意送""fut不想赢""fut明显不想赢"</li>
    <li><b>图二 BLAST 房 3 条</b>（23:49-23:51）："我fut防守就是大拉出去送赚疯了吃菠菜""fut这种逼队伍就喜欢吃菜""这分菊花突然不会玩了，一切都有剧本，懂吗"</li>
  </ul>
  <div class="warnbox"><b>纪律声明：</b>以上均为观众质疑/玩梗，语境多为 FUT 崩盘（大拉送/空狙）与菊花突然失误的嘲讽，<b>非假赛证据</b>；按灰信号纪律仅作风险标注、不上升结论。若出现"吃了/收钱/带老板"类明确指控或盘口价格异动，升级重点监控。</div>"""),
    ("3", "地图与选图情报（官方 + 弹幕）", """<p><b>✅ 官方地图顺序（Liquipedia + BLAST）：</b>图一 <b>Ancient</b> · 图二 <b>Dust II</b> · 图三 <b>Cache</b></p>
  <table>
    <tr><th>锚点</th><th>内容</th><th>置信</th></tr>
    <tr><td>图二 Dust II（Legacy 选图）</td><td>"菊花选的沙二"（22:51）"菊花沙二强图"（22:35）"菊花王图是小镇沙二"——<b>局中 Legacy 大比分压制</b>（弹幕口径）</td><td>官方图序 + 弹幕</td></tr>
    <tr><td>狙击手差距</td><td>官方图一：try 26-9/+17 vs cmtry 14-18/-4；图二弹幕"敌我狙击手差距太大""两个try的差距怎么这么大""厘米try不行"——<b>全场核心胜负手</b></td><td>官方（图一）+ 多源（图二）</td></tr>
    <tr><td>FUT 沙二没战术</td><td>"fut沙二 没战术 没思路 不然为什么ban啊""怪不得fut 把沙2搬了""FUT自己也知道沙二这图他们打不了"——FUT 曾主动 ban 沙二（历史）</td><td>多源（弹幕口径）</td></tr>
    <tr><td>FUT 崩盘负锚（图二）</td><td>"图二直接被虐了啊fut""fut被打飞了""fut被打懵了""fut这种小孩队打逆风局不行的"</td><td>多源</td></tr>
    <tr><td>图三候选 Cache</td><td>"别急，这俩队要打图三的"（22:43）——若 1-1 进 Cache 决胜</td><td>官方记录</td></tr>
  </table>
  <p class="meta">BP 后战绩情报：图一"try vs cmtry 谁更厉害"对比已由官方数据兑现（26-9 vs 14-18）；图二延续同一话题（"敌我try差距"）。</p>"""),
    ("4", "盘口与市场讨论", """<ul>
    <li><b>大额单线索：</b>chaincatcher 报道本场胜者盘出现约 <b>$132,997.1</b> 大额单，定价约 <b>59%</b>（21:35 交易），方向仅标注"match winner"、<b>未明确方向</b>——待确认，勿据此直接下方向。</li>
    <li><b>图二局中定价预期：</b>Legacy 图一已拿下 + 图二大比分压制，盘口应继续向 Legacy 倾斜；具体价格待查证，查证后回填。</li>
    <li><b>投注情绪：</b>"这你妈的菊花让老子输了1000+"（买 FUT 者亏损）；"买FUT的真的想死了"（图一末段）——情绪面偏空 FUT。</li>
  </ul>"""),
    ("5", "方向性情报板（锚点 × 共识 × 风险）", """<table>
    <tr><th>维度</th><th>FUT</th><th>Legacy（菊花）</th></tr>
    <tr><td>强度层</td><td>EWC 亚军；枪法刚但"喜欢浪"；沙二历史主动 ban（弹幕口径）</td><td>EWC 季军；"菊花王朝"叙事；沙二王图（"王图是小镇沙二"）</td></tr>
    <tr><td>本场信号（图二局中）</td><td>被打崩/空狙/大拉送（"fut被打飞了"）；cmtry 被建议换人（"让青训王德发来打狙"）</td><td>大比分压制（"13比0来！！"）；try 状态延续；拉托有发挥（"拉托！"）</td></tr>
    <tr><td>反方声音</td><td>"fut枪这么刚，咋打不过菊花了"（不解）；"上次5比0都打回来了"（翻盘希望）</td><td>"菊花一点战术都没吗"（早段）；"这分菊花突然不会玩了"（单条）</td></tr>
    <tr><td>共识</td><td colspan="2">"菊花是真的猛 除了绿龙其他队真干不过他"；"猎鹰&lt;FUT&lt;菊花"；"猎鹰严父选拔赛/菊花三擒猎鹰"——若 2-0，Legacy 晋级路径聚焦 Falcons</td></tr>
  </table>"""),
    ("6", "情报含义与决策落点", """<ul>
    <li><b>短期：</b>Legacy 图一已拿下（官方）、图二大比分压制（弹幕口径），<b>2-0 趋势明显</b>；FUT 沙二没战术 + 狙击手崩盘，暂无解。</li>
    <li><b>方向信号：</b>弹幕共识全面倒向 Legacy（敌我狙击手 + FUT 崩盘 + 沙二 BAN 背景）；"fut这种小孩队打逆风局不行"。</li>
    <li><b>风险提示：</b>灰信号累计 15 条（观众质疑·非结论）；图二局中比分尚为弹幕口径，须等官方 window 校准；盘口大单方向未确认。</li>
    <li><b>决策动作：</b>不提前定终局；优先官方比分源；若 G2 结束立即按官方回填；关注 try 手感与 FUT 是否调整（"FUT 喜欢浪"模式是否应验）。</li>
  </ul>"""),
    ("7", "今日 BLAST Open 逐场复盘（事实层）", """<table>
    <tr><th>时间</th><th>对阵</th><th>结果</th></tr>
    <tr><td>17:00</td><td>IC vs Vitality</td><td>IC <b>2-0</b> 爆冷（Anubis 13:8 / Cache 16:13 加时；ZywOo 低迷）</td></tr>
    <tr><td>20:00</td><td>MOUZ vs 9z</td><td>MOUZ <b>2-0</b>（Cache 13:4 / Nuke 13:7）</td></tr>
    <tr><td>22:30</td><td>FUT vs Legacy</td><td>进行中：图一 Legacy <b>13:10</b>（官方）；图二 Dust II Legacy 大比分压制（弹幕口径）</td></tr>
    <tr><td>00:30</td><td>Falcons vs LVG</td><td>未开</td></tr>
  </table>"""),
    ("8", "队伍 / 人员画像（证据层 · 官方 + 弹幕口径）", """<p><b>FUT：</b>土耳其俱乐部；枪法刚（"fut枪这么刚"）但逆风局崩（"小孩队打逆风局不行"）；图一输掉 Ancient 选图、图二沙二被压制（历史主动 ban 沙二，弹幕口径）；狙击手 <b>cmtry</b>（18 岁，官方图一 14-18/-4）被集中质疑，观众建议提青训 <b>wdf（王德发）</b> 打狙。</p>
  <p><b>Legacy（菊花）：</b>"菊花王朝"叙事；狙击手 <b>try</b>（阿根廷人，21 岁，官方图一 26-9/+17/ADR 90）——本场 MVP 级；<b>拉托（latt）</b>图二有发挥（"拉托！"）；"菊花主要看艺术哥，艺术哥一犯病谁都打不过"。</p>
  <p><b>周边叙事：</b>"navi软完蜜蜂软，蜜蜂软完fut软"（强队状态传导梗）；"猎鹰&lt;FUT&lt;菊花"评级；NiKo 生病梗（"打菊花的时候niko生病了"）。</p>"""),
    ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>沙二（Dust II）为典型狙击图：try 类顶级 AWPer 影响力被放大，无狙队（FUT"本质无狙队"）在此图被完克（"沙二没狙打不了"）。</li>
    <li>FUT 历史主动 ban 沙二（"fut bo5搬沙二有原因的"）——被逼打劣势图的选图决策风险是本场教训型案例。</li>
    <li>B 组"肌肉派对决"延续：IC/MOUZ/FUT/Legacy 均为刚枪风格，狙击手质量成为分水岭。</li>
  </ul>"""),
    ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>预测/锚点</th><th>时间</th><th>状态</th></tr>
    <tr><td>"fut 遗迹还是太硬了 / 遗迹是fut强图"（FUT×Ancient 正锚）</td><td>22:52/23:10</td><td><b>未兑现</b>（图一 FUT 10-13 告负·官方）</td></tr>
    <tr><td>"到了沙二你就看try神怎么狙吧"（try 图二爆发）</td><td>22:59</td><td>图二局中兑现中（"敌我狙击手差距太大"）</td></tr>
    <tr><td>"正常的fut就是喜欢浪然后打不过图二"（FUT 图二崩盘模式）</td><td>23:15</td><td>图二局中兑现中（"fut被打飞了"）</td></tr>
    <tr><td>灰信号簇 15 条（FUT 不想赢/吃菜）</td><td>23:07-23:51</td><td>待终局回填（观众质疑·非结论）</td></tr>
  </table>"""),
    ("11", "数据与溯源", """<p><b>官方源</b>：BLAST 官方比赛页 fcc5ce44（23:32 抓取）：<b>Legacy 1-0 FUT</b>（图一 Ancient 13:10，T7/CT6 vs T5/CT5，endedAt 23:22:04 CST）；图二 Dust II 进行中。</p>
  <p class="meta"><b>数据窗口</b>：2026-08-27 23:36-23:52 CST（G2 局中切片，未混入其他场次）。</p>
  <p class="meta"><b>数据源</b>：虎牙三路同会话：CSBOY 官方 123321 / CSBOY-Mo 321123 / BLAST 官方 blast；采集会话 cs2_blast_2026-08-27 运行中。</p>
  <p class="meta"><b>密度峰值</b>：23:46-23:48 CST 狙击手对比刷屏（"敌我狙击手""两个try"高频）；23:48 "13比0来！！"。</p>
  <p class="meta"><b>修正记录</b>：图一初版误判已在 G1 结束页修正（23:32 BLAST 官方源）；本页为 G2 局中，图二比分以弹幕口径为主，官方 window 刷新后校准。</p>
  <p class="meta">生成时间：2026-08-27 23:52 CST · 情报原则：核心=本场弹幕，事实层=官方源仲裁，推测显式标注。</p>"""),
]


G2_MID = page(
    "BLAST Open Porto · FUT vs Legacy · G2 局中情报 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图二 Dust II（沙二）· 系列 FUT 0-1 Legacy",
    SPEED,
    SECTIONS,
    "弹幕情报 · 观众质疑非结论 · 比分以官方源为准 · Polymarket 电竞情报项目",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_FUT-Legacy_2026-08-27_g2_mid.html"
    out.write_text(G2_MID, encoding="utf-8")
    print("wrote", out)
