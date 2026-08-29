#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FUT vs Legacy G2 BP/开局情报（2026-08-27，图二 Dust II 沙二）。

按线上参考标准（intel_danmu_CS2-FUT-Legacy_G2_2026-08-27.html）格式。
官方系列：Legacy 1-0 FUT（图一 Ancient 13:10）；图二 Dust II 开赛（Legacy 选图）。
数据窗口 23:24-23:36 北京时间，三路源。
"""

from pathlib import Path

from gen_fut_legacy_g1_end import page  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


SPEED = """
  <div class="top">
    <span class="score-big">G2 BP 后/开局 · 图二 Dust II（Legacy 选图）· 系列 FUT 0-1 Legacy</span>
    <span class="badge b-ok">官方系列比分确认</span>
    <span class="badge b-anchor">沙二 = 狙击图</span>
    <span class="badge b-risk">灰信号（图一 12 条延续）</span>
  </div>
  <div style="margin-top:8px">
    <div class="sig"><span class="tag" style="color:var(--accent)">锚点</span><span><b>try 图一 Carry（官方 26-9/+17）延续预期</b>："try神一人杀了二十五个""try神的大狙吊不吊"；沙二为狙击图（"沙二肯定狙击图啊"）——图二关键变量 <span class="meta">→ 详 §3/§5/§8</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--bad)">风险</span><span><b>FUT 0-1 落后 + cmtry 压力</b>：图一灰信号 12 条（观众质疑·非结论）；"敌我try差距""cmtry不换的话fut走不远"——狙击手话题延续 <span class="meta">→ 详 §2</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--purple)">共识</span><span><b>观众多数偏 Legacy</b>："如果try神继续这个发挥fut赢不了啊""fut图二要被小分带走了"（BLAST 房） <span class="meta">→ 详 §5/§6</span></span></div>
    <div class="sig"><span class="tag" style="color:var(--sub)">盘口</span><span><b>大额单线索延续（$132,997，~59%，21:35）</b>方向待确认；情绪面偏 Legacy → 详 §4</span></div>
  </div>
  <div class="errbox"><b>节点说明：</b>本页为 G2 BP/开局节点。图一已按 BLAST 官方源修正为 <b>Legacy 1-0 FUT（Ancient 13:10）</b>；图二 Dust II 为 Legacy 选图（弹幕口径"菊花选的沙二"），开赛初段弹幕即出现"fut图二要被小分带走"。</div>
"""


SECTIONS = [
    ("1", "比赛信息与状态（官方源）", """<table>
    <tr><td>对阵</td><td>FUT（EWC 亚军）vs Legacy（菊花，EWC 季军）· BLAST Premier Open Porto 2026 小组赛 B 组 · BO3 · 胜者组八强（UB QF3）</td></tr>
    <tr><td>官方时间</td><td>2026-08-27 22:30 CST 开赛 · hltv match 2396929 · BLAST match fcc5ce44</td></tr>
    <tr><td>官方地图</td><td>图一 <b>Ancient</b>（Legacy 13:10 结束）· 图二 <b>Dust II</b>（开赛）· 图三 Cache（候选）</td></tr>
    <tr><td>系列状态（官方）</td><td><b>Legacy 1 - 0 FUT</b>（图一官方）；图二 Dust II 开赛（Legacy 选图，弹幕口径"菊花选的沙二"）</td></tr>
    <tr><td>今日同组赛果</td><td>17:00 IC 2-0 Vitality（爆冷）· 20:00 MOUZ 2-0 9z（Cache 13:4 / Nuke 13:7）· 00:30 Falcons vs LVG（未开）</td></tr>
    <tr><td>弹幕规模</td><td>G2 BP 窗口（23:24-23:36）：try 话题刷屏（"try神一人杀了二十五个""try才21"）；"猎鹰严父/抚养权"叙事延续</td></tr>
    <tr><td>完整性</td><td><span class="badge b-ok">三路齐采</span>系列比分 = BLAST 官方页（23:32 抓取）；图二开局 = 弹幕口径</td></tr>
  </table>
  <p class="meta">系列/图一比分 = BLAST 官方页（2026-08-27 23:32 抓取）；图二局中比分以弹幕口径为主，官方 window 刷新后校准。</p>"""),
    ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<p><b>图一累计 12 条</b>（CSBOY 官方 9 + BLAST 官方 3，23:07-23:16）："到底在演什么剧本啊""感觉就是在演比分啊""演的吧""故意送""fut不想赢""fut明显不想赢"——语境为 FUT 人数优势局被翻的嘲讽。</p>
  <div class="warnbox"><b>纪律声明：</b>以上均为观众质疑，<b>非假赛证据</b>；按灰信号纪律仅作风险标注、不上升结论。图二若出现"吃了/收钱/带老板"类明确指控或盘口异动，升级重点监控。</div>"""),
    ("3", "地图与选图情报（官方 + 弹幕）", """<p><b>✅ 官方地图顺序（Liquipedia + BLAST）：</b>图一 <b>Ancient</b> · 图二 <b>Dust II</b> · 图三 <b>Cache</b></p>
  <table>
    <tr><th>锚点</th><th>内容</th><th>置信</th></tr>
    <tr><td>图二 Dust II（Legacy 选图）</td><td>"菊花选的沙二"（23:29）"菊花沙二强图"（22:35）"沙二都挺厉害的"——<b>Legacy 选图</b>，开赛</td><td>官方图序 + 弹幕</td></tr>
    <tr><td>try 图一 Carry</td><td>官方数据 <b>try 26-9 / +17</b>（图一）；"try神一人杀了二十五个""try神的大狙吊不吊""try要成为顶级狙击手了"——图二延续预期</td><td>官方（图一）+ 多源</td></tr>
    <tr><td>沙二 = 狙击图</td><td>"沙二肯定狙击图啊""沙二ct高手""fut 进攻得避开这个人的狙，尽量拿信息打另一个"——战术判断</td><td>弹幕（多源）</td></tr>
    <tr><td>FUT · cmtry</td><td>"cmtry不换的话fut走不远感觉""敌我try差距""太惨了, cmtry"——图一 14-18 延续质疑</td><td>官方（图一）+ 弹幕</td></tr>
    <tr><td>图三候选 Cache</td><td>"别急，这俩队要打图三的"（22:43）——若 1-1 进 Cache 决胜</td><td>官方记录</td></tr>
  </table>
  <p class="meta">BP 后战绩情报：无"选手×地图历史胜率"类弹幕；"try vs cmtry"对比锚点由图一官方数据支撑（26-9 vs 14-18）。</p>"""),
    ("4", "盘口与市场讨论", """<ul>
    <li><b>大额单线索：</b>chaincatcher 报道本场胜者盘出现约 <b>$132,997.1</b> 大额单，定价约 <b>59%</b>（21:35 交易），方向仅标注"match winner"、<b>未明确方向</b>——待确认，勿据此直接下方向。</li>
    <li><b>图二开局定价预期：</b>Legacy 1-0 领先 + 手握图二选图，盘口应继续偏 Legacy；具体价格待查证，查证后回填。</li>
    <li><b>弹幕口径：</b>无具体赔率/让分数字；"买FUT的真的想死了"（图一末段投注情绪）延续。</li>
  </ul>"""),
    ("5", "方向性情报板（锚点 × 共识 × 风险）", """<table>
    <tr><th>维度</th><th>FUT</th><th>Legacy（菊花）</th></tr>
    <tr><td>强度层</td><td>EWC 亚军；枪法刚但"喜欢浪"；图一输掉 Ancient 选图</td><td>EWC 季军；try 状态火热；沙二为 Legacy 选图（"菊花王图"叙事）</td></tr>
    <tr><td>本场信号（图二开局）</td><td>0-1 落后；cmtry 狙击压力（"敌我try差距"）；"fut图二要被小分带走了"（BLAST 房）</td><td>1-0 领先；try 手感延续预期；"如果try神继续这个发挥fut赢不了啊"</td></tr>
    <tr><td>反方声音</td><td>"图二调整战术，fut赢""这图FUT赢放心看"（BLAST 房反话）</td><td>"菊花一点战术都没吗"（早段质疑）</td></tr>
    <tr><td>共识</td><td colspan="2">观众多数偏 Legacy（try 延续 + FUT 崩盘模式）；"猎鹰严父选拔赛/抚养权争夺"叙事延续——胜者路径聚焦 Falcons</td></tr>
  </table>"""),
    ("6", "情报含义与决策落点", """<ul>
    <li><b>短期：</b>Legacy 1-0 领先（官方）且图二为 Legacy 选图（沙二）；FUT 容错率低，若图二再负则 0-2 出局。</li>
    <li><b>方向信号：</b>弹幕共识偏 Legacy（try 延续 + FUT 大狙差距）；"fut图二要被小分带走"（BLAST 房）开局即现。</li>
    <li><b>风险提示：</b>灰信号 12 条（观众质疑·非结论）；图二局中比分待官方 window 校准；盘口大单方向未确认。</li>
    <li><b>决策动作：</b>开局后优先官方比分源；关注 try 手感延续与 FUT 是否针对调整（避开大狙/换战术）；若 G2 结束立即按官方回填。</li>
  </ul>"""),
    ("7", "今日 BLAST Open 逐场复盘（事实层）", """<table>
    <tr><th>时间</th><th>对阵</th><th>结果</th></tr>
    <tr><td>17:00</td><td>IC vs Vitality</td><td>IC <b>2-0</b> 爆冷（Anubis 13:8 / Cache 16:13 加时；ZywOo 低迷）</td></tr>
    <tr><td>20:00</td><td>MOUZ vs 9z</td><td>MOUZ <b>2-0</b>（Cache 13:4 / Nuke 13:7）</td></tr>
    <tr><td>22:30</td><td>FUT vs Legacy</td><td>进行中：图一 Legacy <b>13:10</b>（官方）；图二 Dust II 开局</td></tr>
    <tr><td>00:30</td><td>Falcons vs LVG</td><td>未开</td></tr>
  </table>"""),
    ("8", "队伍 / 人员画像（证据层 · 官方 + 弹幕口径）", """<p><b>FUT：</b>土耳其俱乐部；"年轻人火力猛"、枪法刚但"喜欢浪"；图一输掉 Ancient 选图；狙击手 <b>cmtry</b>（18 岁，官方图一 14-18/-4）被集中质疑（"厘米try不行""敌我try差距"）。</p>
  <p><b>Legacy（菊花）：</b>狙击手 <b>try</b>（阿根廷人，21 岁，"潘帕斯闪光"），图一官方 <b>26-9/+17/ADR 90</b>；"try打破平衡了""没try菊花真赢不了"——图二延续预期核心。</p>
  <p><b>周边叙事：</b>"猎鹰严父/抚养权争夺"；"菊花三擒法尔孔"；Falcons 粉丝自嘲（"猎鹰让这俩菜逼队拿五分算我输"）。</p>"""),
    ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>沙二（Dust II）为典型狙击图：大狙影响力高，try 类顶级 AWPer 是胜负手（"沙二没狙打不了"）。</li>
    <li>B 组"肌肉派对决"：IC/MOUZ/FUT/Legacy 均为刚枪风格，狙击手质量成为分水岭。</li>
    <li>猎鹰叙事：Legacy 对 Falcons 历史占优（"三擒法尔孔"），若晋级，H2H 心理优势是观众共识级话题。</li>
  </ul>"""),
    ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>预测/锚点</th><th>时间</th><th>状态</th></tr>
    <tr><td>"fut 遗迹还是太硬了 / 遗迹是fut强图"（FUT×Ancient 正锚）</td><td>22:52/23:10</td><td><b>未兑现</b>（图一 FUT 10-13 告负·官方）</td></tr>
    <tr><td>"到了沙二你就看try神怎么狙吧"（try 图二爆发）</td><td>22:59</td><td>图二验证中（开赛）</td></tr>
    <tr><td>"正常的fut就是喜欢浪然后打不过图二"（FUT 图二崩盘模式）</td><td>23:15</td><td>图二验证中（开局"要被小分带走"）</td></tr>
    <tr><td>灰信号簇 12 条（FUT 不想赢）</td><td>23:07-23:16</td><td>待终局回填（观众质疑·非结论）</td></tr>
  </table>"""),
    ("11", "数据与溯源", """<p><b>官方源</b>：BLAST 官方比赛页 fcc5ce44（23:32 抓取）：<b>Legacy 1-0 FUT</b>（图一 Ancient 13:10，endedAt 23:22:04 CST）；图二 Dust II 开赛。</p>
  <p class="meta"><b>数据窗口</b>：2026-08-27 23:24-23:36 CST（G2 BP/开局切片，未混入其他场次）。</p>
  <p class="meta"><b>数据源</b>：虎牙三路同会话：CSBOY 官方 123321 / CSBOY-Mo 321123 / BLAST 官方 blast；采集会话 cs2_blast_2026-08-27 运行中。</p>
  <p class="meta"><b>修正记录</b>：图一初版误判已在 G1 结束页修正（23:32 BLAST 官方源）；本页为 G2 BP/开局节点。</p>
  <p class="meta">生成时间：2026-08-27 23:57 CST · 情报原则：核心=本场弹幕，事实层=官方源仲裁，推测显式标注。</p>"""),
]


G2_BP = page(
    "BLAST Open Porto · FUT vs Legacy · G2 BP 后/开局情报 · 2026-08-27",
    "CS2 · BLAST Open Porto Group B · BO3 · 图二 Dust II（沙二）· 系列 FUT 0-1 Legacy",
    SPEED,
    SECTIONS,
    "弹幕情报 · 观众质疑非结论 · 比分以官方源为准 · Polymarket 电竞情报项目",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_FUT-Legacy_2026-08-27_g2_bp.html"
    out.write_text(G2_BP, encoding="utf-8")
    print("wrote", out)
