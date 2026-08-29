#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Spirit vs DENDELE CS（BLAST Open Porto · 2026-08-26）情报页。

数据来源：/private/tmp/spirit_clean/ 下按修复后精确窗口切出的干净切片
（教训 2026-08-26：-1800 起点前移 + 未按联赛过滤导致混源，已修复）。
输出：reports/intel_danmu_Spirit-DENDELE_2026-08-26_{g1_bp,g1_mid,g1_end,
g2_bp,g2_mid,g2_end,full}.html + match_cs2-ts7-dendel-2026-08-26.html（时间轴壳）。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/Users/ad/Documents/polymarket")
REPORTS = ROOT / "reports"


CSS = """
  :root { --bg:#f5f5f7; --card:#fff; --ink:#1d1d1f; --sub:#6e6e73; --accent:#0b6bcb; --line:#e3e3e8; --good:#1a7f37; --bad:#c0392b; --warn:#b45309; --purple:#6d4fc4; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.62; padding:22px 12px 56px; }
  .wrap { max-width:920px; margin:0 auto; }
  .card { background:var(--card); border-radius:16px; padding:20px 22px; margin:14px 0; box-shadow:0 1px 4px rgba(0,0,0,.05); }
  h1 { font-size:22px; font-weight:700; }
  h2 { font-size:16px; font-weight:650; margin:10px 0 8px; display:flex; align-items:center; gap:7px; }
  h2 .no { flex:0 0 22px; height:22px; background:var(--accent); color:#fff; border-radius:7px; font-size:12px; display:inline-flex; align-items:center; justify-content:center; }
  .meta { color:var(--sub); font-size:12px; margin-top:6px; }
  .badge { display:inline-block; border-radius:999px; padding:2px 9px; font-size:11px; margin:2px 4px 2px 0; }
  .b-pend { background:#fdf0e6; color:var(--warn); }
  .b-ok { background:#e8f6ec; color:var(--good); }
  .b-risk { background:#fdeaea; color:var(--bad); }
  .b-anchor { background:#eaf2fb; color:var(--accent); }
  .b-odds { background:#e8f6ec; color:var(--good); }
  .b-con { background:#f3f0fa; color:var(--purple); }
  .speed { background:linear-gradient(180deg,#fbfcff,#f4f7fd); border:1px solid #dbe5f5; }
  .speed .top { display:flex; flex-wrap:wrap; gap:8px; align-items:center; border-bottom:1px solid var(--line); padding-bottom:10px; }
  .score-big { font-size:20px; font-weight:750; color:var(--accent); }
  .sig { display:flex; gap:10px; padding:9px 0; border-bottom:1px dashed var(--line); font-size:13px; }
  .sig:last-child { border-bottom:none; }
  .sig .tag { flex:0 0 52px; font-size:11px; font-weight:650; padding-top:2px; }
  .act { background:#f0faf3; border:1px solid #cfe8d8; border-radius:12px; padding:11px 14px; margin-top:10px; font-size:13.5px; }
  table { width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
  th { text-align:left; color:var(--sub); font-weight:600; font-size:11px; padding:6px 7px; border-bottom:1px solid var(--line); }
  td { padding:6px 7px; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  ul { padding-left:20px; margin:6px 0; } li { margin:4px 0; font-size:13.5px; }
  .warnbox { background:#fdf6ec; border-left:3px solid var(--warn); padding:8px 12px; border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  .badbox { background:#fdf1f0; border-left:3px solid var(--bad); padding:8px 12px; border-radius:0 8px 8px 0; margin:8px 0; font-size:13px; }
  .srcbox { background:#f4f6fb; border:1px solid #dde3f0; border-radius:10px; padding:9px 12px; margin:8px 0; font-size:12px; color:var(--ink); }
  .footer { color:var(--sub); font-size:11.5px; text-align:center; margin-top:18px; }
"""


def page(title: str, sub: str, speed: str, sections: list[tuple[str, str, str]], footer: str) -> str:
    cards = "".join(
        f'<div class="card"><h2><span class="no">{no}</span>{h2}</h2>{body}</div>'
        for no, h2, body in sections
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<div class="card speed">
  <h2><span class="no">0</span>核心情报速览</h2>
  {speed}
</div>

{cards}

<div class="footer">{footer}</div>
</div>
</body>
</html>"""


def sig(tag: str, color: str, text: str) -> str:
    return f'<div class="sig"><span class="tag" style="color:{color}">{tag}</span><span>{text}</span></div>'


def speed_block(score: str, badges: list[str], sigs: list[str], act: str) -> str:
    b = "".join(f'<span class="badge {cls}">{txt}</span>' for cls, txt in badges)
    s = "".join(sigs)
    return f"""<div class="top">
    <span class="score-big">{score}</span>
    {b}
  </div>
  <div style="margin-top:8px">{s}</div>
  <div class="act"><b>决策落点：</b>{act}</div>"""


def src_box(actual: str, expect: str, gap: str) -> str:
    return (
        '<div class="srcbox"><b>数据源完整性：</b>实际数据源 = ' + actual
        + '；预期数据源 = ' + expect + '；缺口 = ' + gap + '</div>'
    )


# ---------------------------------------------------------------- G1 BP

G1_BP = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G1 BP 后/开局情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一 遗迹（Ancient，弹幕口径）",
    speed_block(
        "G1 进行中 · 图一 遗迹",
        [("b-pend", "BP 后/开局节点"), ("b-risk", "灰信号 4 条"), ("b-anchor", "Spirit×遗迹 历史优势图")],
        [
            sig("风险", "var(--bad)", '灰信号 4 条指向 Spirit 侧（"夺冠后就吃 / 故意输败者组 / 吃力=买了"）——<b>观众质疑，非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", 'Spirit×遗迹 历史优势叙事（"一百胜率遗迹"），本图 Spirit 自选；开局未见明显劣势 → 详 §3'),
            sig("盘口", "var(--good)", "无明确数字盘提及，<b>样本不足</b> → 详 §4"),
            sig("共识", "var(--purple)", '观众普遍预期 Spirit 大胜弱旅，开局即出现"打三线队吃力"质疑 → 详 §5'),
        ],
        "图一为 Spirit 主场图遗迹，但开局即被批\u201c打三线队这么吃力\u201d——市场方向未变（Spirit 高概率），过程质量是后续观察变量；若这种\u201c强图吃力\u201d模式延续到 G2 叉车（历史弱图），翻车叙事有发酵空间。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>节点</td><td>G1 · BP 后 / 开局（EARLY-GAME）· 图一 遗迹（Ancient，弹幕口径，官方待核对）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 11:55–12:24 UTC（北京 19:55–20:24）</td></tr>
    <tr><td>关键数据</td><td>5,265 条弹幕 · 1,861 活跃用户 · 密度 181.6 条/分</td></tr>
    <tr><td>状态</td><td>本节点为进行中快照；G1 最终结果见 G1 结束节点 / 整场复盘（Polymarket 仲裁）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（4,862 条）+ CSBOY-Mo 321123（403 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点 0 条（G1 前半段未采，赛后 VOD 可回捞）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>4 条</td><td>Spirit 侧：夺冠后\u201c吃\u201d/故意输败者组/吃力=买了</td><td>"经典夺冠后就吃 这出生比赛能不能改下剧本" · "打个三线队伍这样吃力？买了？" · "绿龙应该是故意想输去败者组逮捕猎鹰" · "这是集结号的剧本？"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（集中于 Spirit 侧、时间分散；多为\u201c预期 Spirit 演\u201d的博彩叙事与情绪，无局内实锤）。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>Spirit×遗迹 历史优势图</td><td>"一百胜率遗迹"（局中 12:08 提及）；本图 Spirit 自选（"自己选遗迹"）</td><td>方向待 G1 结束回填（最终 13-8 拿下）</td></tr>
    <tr><td>开局节奏</td><td>11:55 开图密度 367（手枪局）；"上半场20个人头都没有"（半场击杀少=慢节奏）</td><td>过程样本：胶着感强</td></tr>
    <tr><td>donk 情绪面</td><td>"donk加油"多条 + "小驴长胡子/没精神"外形话题</td><td>与赛果无关（非技术信号）</td></tr>
  </table>
  <p class="meta">BP 后战绩情报（必抓项）：本窗口无\u201c选手×地图 X胜Y负\u201d类明确战绩提及，已记录。</p>"""),
        ("4", "盘口与市场讨论", '<p>无明确数字盘提及。<b>样本不足。</b>"有700万可以追明日晴吗"为投注闲聊（标的非本场），不纳入盘口。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚（预期）</td><td>Spirit · 图一</td><td>"绿龙雄起"助威 + 历史优势图叙事</td><td>最终应验（Spirit 13-8）</td></tr>
    <tr><td>负锚（过程）</td><td>Spirit · 表现</td><td>"打三线队这么吃力"（12:02/12:08）· "打个三线队伍这样吃力？买了？"</td><td>过程兑现（胶着/送分），结果未变</td></tr>
    <tr><td>共识</td><td>DENDELE 定位</td><td>"打这种纯纯无脑莽就完了动脑子太吃亏了"——观众定义对手为三线队</td><td>—</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（4 条）</td><td>吃/剧本/故意输败者组</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：Spirit 遗迹主场 + 实力差（观众共识）——市场已高概率定价 Spirit 方向；</li>
    <li><b>SHORT</b>：若对弱旅仍\u201c吃力\u201d，说明状态/经济管理有隐患；G2 叉车为 Spirit 历史弱图（"绿龙叉车太差了"），存在翻车叙事候选；</li>
    <li><b>观察点</b>：Spirit 经济管理、叉车图（G2）执行质量。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>11:55–12:00</td><td>开图高密度（367/375）："绿龙雄起"助威 + donk 加油；手枪局/早期回合</td></tr>
    <tr><td>12:02–12:08</td><td>领先未拉开 → "绿龙还是这么戏剧化 打三线队吃力的哦""打个三线队这么吃力""开吃"质疑出现</td></tr>
    <tr><td>12:18</td><td>密度峰值 385："俩队菜b让猎鹰炸一下就老实了俩"——过程胶着感</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 311；正 3 / 负 19——开局负向情绪占优（"吃力/开吃"）</td></tr>
    <tr><td>donk</td><td>提及 208；开局助威多（"donk加油"），另有外形话题（胡子/没精神）——情绪面</td></tr>
    <tr><td>\u201cNiko 脸\u201d选手</td><td>提及 173（"右下角怎么有个niko""这息肉怎么跟Niko一样"）——观众认人话题，非本场信号</td></tr>
    <tr><td>sh1ro</td><td>提及 6；"又稳又强/从不软脚"——正向</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>BLAST Open Porto 小组赛 BO3；遗迹 = Spirit 历史优势图（观众口径："一百胜率遗迹"）；</li>
    <li>观众参照历史："FUT 的遗迹要不是浪了，冠军都不是绿龙的"（12:11）——优势图叙事有先例参照；</li>
    <li>版本符号：遗迹慢节奏/击杀少（"上半场20个人头都没有"）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>11:55–12:08</td><td>"绿龙雄起/应该赢"（观众预期）</td><td>图一兑现（Spirit 13-8，见 G1 结束节点）</td></tr>
    <tr><td>12:02/12:08</td><td>"打三线队吃力/买了"</td><td>过程部分兑现（胶着/送分），结果未变</td></tr>
    <tr><td>11:55–12:24</td><td>灰信号 4 条（吃/剧本）</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（4,862 条）+ CSBOY-Mo 321123（403 条），合计 5,265 条；BLAST 官方 660729 本节点 0 条（缺口）。窗口 2026-08-26 11:55–12:24 UTC。来源标签：本场弹幕（核心）；历史画像（§3/§9 标注）。待官方核对：地图名、阵容。</p>"""),
    ],
    "BP 后/开局节点 2026-08-26 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- G1 MID

G1_MID = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G1 局中情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一 遗迹（Ancient，弹幕口径）",
    speed_block(
        "G1 进行中 · 图一 遗迹",
        [("b-pend", "局中节点"), ("b-risk", "灰信号 6 条"), ("b-anchor", "\u201c一百胜率遗迹\u201d受挑战")],
        [
            sig("风险", "var(--bad)", '灰信号 6 条——"无脑刚送分""还买了俩把吹风机"等，观众批评 Spirit 送分/经济——<b>观众质疑，非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", '"一百胜率遗迹要没了"（12:08）——主场图优势叙事受挑战；DENDELE eco 翻盘片段 → 详 §3'),
            sig("盘口", "var(--good)", "无明确数字盘提及，<b>样本不足</b> → 详 §4"),
            sig("共识", "var(--purple)", '观众对 Spirit 遗迹表现不满（"自己选遗迹打成这个逼样"）→ 详 §5'),
        ],
        "图一并未如市场预期\u201c碾压\u201d：Spirit 送分/经济管理问题被反复点名；若此模式延续到 G2 叉车（历史弱图），\u201c状态差/送分\u201d叙事有升级空间。市场方向仍维持 Spirit 高概率。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>节点</td><td>G1 · 局中（MID-GAME）· 图一 遗迹（Ancient，弹幕口径，官方待核对）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 12:05–12:44 UTC（北京 20:05–20:44）</td></tr>
    <tr><td>关键数据</td><td>6,777 条弹幕 · 2,106 活跃用户 · 密度 174.5 条/分</td></tr>
    <tr><td>状态</td><td>本节点为进行中快照；G1 最终结果见 G1 结束节点 / 整场复盘（Polymarket 仲裁）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（6,226 条）+ CSBOY-Mo 321123（551 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点 0 条（G1 期间未采，赛后 VOD 可回捞）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>6 条</td><td>Spirit 侧：送分/吃/剧本</td><td>"这是集结号的剧本？" · "经典夺冠后就吃 这出生比赛能不能改下剧本" · "打个三线队伍这样吃力？买了？" · "绿龙应该是故意想输去败者组逮捕猎鹰" · "无脑刚送分" · "还买了俩把吹风机 我没想到"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（多指向 Spirit\u201c送分/吃\u201d叙事，无局内实锤）。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>Spirit×遗迹 优势叙事</td><td>"一百胜率遗迹要没了"（12:08）</td><td>图一未兑现（最终 13-8 仍赢），过程有惊险</td></tr>
    <tr><td>DENDELE eco 翻盘</td><td>"这是被对面eco翻盘了吗？"（12:05）· "被翻盘了芽"（12:06）</td><td>过程样本：对手 eco 拿回数回合</td></tr>
    <tr><td>自选图表现</td><td>"自己选遗迹打成这个逼样"（12:09，观众骂）</td><td>过程低于预期</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", '<p>无明确数字盘提及。<b>样本不足。</b>"不缺钱换人头"为操作调侃，非盘口数据。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>负锚（图内）</td><td>Spirit×遗迹</td><td>"一百胜率遗迹要没了"</td><td>未兑现（仍赢），过程惊险</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（6 条）</td><td>"无脑刚送分"等送分叙事</td><td>兑现统计待回填</td></tr>
    <tr><td>共识</td><td>观众不满</td><td>"gg，马西西滚去二线，自己选遗迹打成这个逼样"（12:09）</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：Spirit 主场图仍高概率（市场方向未变），但\u201c过程质量\u201d是主要变量；</li>
    <li><b>SHORT</b>：若\u201c强图吃力\u201d延续至 G2 叉车（历史弱图），翻车叙事候选上升；</li>
    <li><b>观察点</b>：Spirit 经济管理、送分频率、G2 叉车执行。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 局中 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>12:05–12:11</td><td>eco 翻盘片段 + "gg" 刷屏（观众以为要翻车）；"遗迹输了就二比零了"（观众观点）</td></tr>
    <tr><td>12:18</td><td>密度峰值 385："俩队菜b让猎鹰炸一下就老实了俩"——胶着感</td></tr>
    <tr><td>12:25–12:35</td><td>胶着/经济问题；12:35 密度峰值 421："直接拆/为什么不捡枪啊/没烟怎么拆"——残局拆包关键点</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 320；正 6 / 负 18——局中负向情绪持续</td></tr>
    <tr><td>donk</td><td>提及 298；正 5 / 负 8</td></tr>
    <tr><td>sh1ro</td><td>提及 13；"又稳又强"正向</td></tr>
    <tr><td>tN1R（特尼尔）</td><td>"特尼尔次次遗迹都晕"（g1end 窗口 12:33）——遗迹表现被批</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>观众参照历史："FUT 的遗迹要不是浪了，冠军都不是绿龙的"（12:11）——Spirit 遗迹优势叙事有先例；</li>
    <li>遗迹节奏慢/击杀少（"上半场20个人头都没有"）；</li>
    <li>BLAST Open Porto 小组赛 BO3。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>12:08</td><td>"一百胜率遗迹要没了"</td><td>未兑现（Spirit 仍赢 13-8），过程有惊险</td></tr>
    <tr><td>12:05–12:44</td><td>灰信号 6 条（送分/吃）</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（6,226 条）+ CSBOY-Mo 321123（551 条），合计 6,777 条；BLAST 官方 660729 本节点 0 条（缺口）。窗口 2026-08-26 12:05–12:44 UTC。来源标签：本场弹幕（核心）；历史画像（§9 标注）。待官方核对：地图名、阵容。</p>"""),
    ],
    "局中节点 2026-08-26 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- G1 END

G1_END = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G1 结束情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图一 遗迹 13-8（Spirit 胜）",
    speed_block(
        "Spirit 1-0 DENDELE（G1 结束）",
        [("b-ok", "G1 结束 · 弹幕口径+市场仲裁"), ("b-risk", "灰信号 6 条"), ("b-anchor", "遗迹 13-8")],
        [
            sig("风险", "var(--bad)", '灰信号 6 条——"操控比赛？""无脑刚送分""放分就是押注大分小分"——观众质疑 Spirit 送分，<b>非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", "Spirit×遗迹 历史优势图兑现（13-8，Polymarket Map 1 Spirit 99.95c 一致）；过程充满\u201c送分/经济差\u201d批评 → 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；Map 1 市场结算可核验：总回合 21（13-8）、Spirit -3.5 让分赢 → 详 §4"),
            sig("共识", "var(--purple)", '观众认为 Spirit 状态差（"一优势就喜欢送""这状态真差"）→ 详 §5'),
        ],
        "G1 结果与市场一致（Spirit 13-8）；过程质量差（送分/经济）是 G2 叉车（历史弱图）的真正考验，\u201c翻车/故意输\u201d叙事候选上升。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>G1 结果</td><td><b>Spirit 13-8 DENDELE</b>（弹幕明确"图一绿龙赢了 13-8"13:01；Polymarket Map 1 Winner Spirit 99.95c 结算方向一致）</td></tr>
    <tr><td>节点</td><td>G1 · 结束 / 局间（GAME-REVIEW）· 图一 遗迹（Ancient，弹幕口径）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 12:30–12:59 UTC（北京 20:30–20:59）</td></tr>
    <tr><td>关键数据</td><td>3,945 条弹幕 · 1,469 活跃用户 · 密度 136.4 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（3,554 条）+ CSBOY-Mo 321123（358 条）+ BLAST 官方 660729（33 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点仅 33 条（G1 中后期才接入，前段缺口）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>6 条</td><td>Spirit 侧：送分/操控；附 DENDELE 历史叙事</td><td>"无脑刚送分" · "还买了俩把吹风机 我没想到" · "操控比赛？" · "真10秒啊，我还故意数了一下。"（拆包计时质疑） · "假如假赛成立的话，放分就是押注大分小分了么，和整局输赢没关系" · "我记得对面这队不是major连续给天禄送分的吗"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（Spirit\u201c送分/操控\u201d叙事 + 对 DENDELE 的历史质疑；无局内实锤，多属情绪与玩梗）。纪律：灰信号只作风险标注，不作假赛结论；兑现统计待回填。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>Spirit×遗迹 优势图</td><td>"一百胜率遗迹"叙事；Spirit 自选遗迹</td><td><b>兑现（13-8 拿下）</b>，但过程被批难看</td></tr>
    <tr><td>经济管理</td><td>"绿龙一直在赢但是经济没养好""连拿分但是经济还是拉完了"</td><td>跨图持续问题（G2 延续）</td></tr>
    <tr><td>领先策略</td><td>"放到9分一波带走"（观众吐槽）</td><td>过程样本</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Map 1 市场结算口径（可核验）：总回合 21（13-8，Over 18.5 ✓ / Under 21.5 ✓ / Under 24.5 ✓）、Spirit -3.5 让分 ✓、-6.5 未过 ✓——与弹幕\u201c13-8\u201d口径一致。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>Spirit×遗迹 优势图</td><td>"一百胜率遗迹"叙事</td><td>应验（13-8）</td></tr>
    <tr><td>负锚（过程）</td><td>Spirit 送分/经济</td><td>"一优势就喜欢送""这状态真差，几分优势局掉枪那么严重"</td><td>过程兑现（送分模式跨图延续）</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（6 条）</td><td>送分/操控/放分押大分小分</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：G1 结论明确（Spirit 1-0），与市场一致；</li>
    <li><b>SHORT</b>：\u201c过程质量\u201d信号（送分/经济）是 G2 叉车预警——若 G2 再送，观众\u201c故意输/吃\u201d叙事将进一步发酵；</li>
    <li><b>观察点</b>：G2 叉车执行、经济管理、灰信号兑现统计。</li>
  </ul>"""),
        ("7", "逐局复盘（G1 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>12:31–12:34</td><td>sh1ro 残局获胜（"西若又赢了一个残局"）；随后 Spirit 连续 2v1 白送（"2打1非要送吗""又他妈二打一送""明送"）</td></tr>
    <tr><td>12:32</td><td>经济问题明确："刚是对的，绿龙没经济"</td></tr>
    <tr><td>12:47</td><td>密度峰值 340："数据/NB！！！/不吃晃的"——结束前高光</td></tr>
    <tr><td>12:56–13:01</td><td>比分确认："大比分1：0，绿龙2"（12:56）· "图一绿龙赢了 13-8"（13:01）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 116；正 6 / 负 9——赢下图一但负向情绪仍多</td></tr>
    <tr><td>sh1ro</td><td>残局高光："又稳又强""西若又赢了一个残局"</td></tr>
    <tr><td>donk</td><td>提及 126；正 0 / 负 2——图一末段存在感低，观众未特别肯定</td></tr>
    <tr><td>tN1R（特尼尔）</td><td>"特尼尔次次遗迹都晕"——遗迹表现被批</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>Spirit 遗迹 = 历史优势图（观众叙事），但\u201c优势图过程难看\u201d样本 +1；</li>
    <li>叉车（Cache） = Spirit 历史弱图（"绿龙叉车太差了"）→ G2 检验；</li>
    <li>BLAST Open Porto 小组赛 BO3。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>11:55–12:08</td><td>"绿龙雄起/应该赢"（观众预期）</td><td>兑现（Spirit 13-8）</td></tr>
    <tr><td>12:08</td><td>"一百胜率遗迹要没了"</td><td>未兑现（仍赢）</td></tr>
    <tr><td>12:02/12:08</td><td>"打三线队吃力/买了"</td><td>过程部分兑现（胶着/送分），结果未变</td></tr>
    <tr><td>12:30–12:59</td><td>灰信号 6 条</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（3,554 条）+ CSBOY-Mo 321123（358 条）+ BLAST 官方 660729（33 条），合计 3,945 条。窗口 2026-08-26 12:30–12:59 UTC。结果仲裁：Polymarket Map 1 Winner（Spirit 99.95c）+ 弹幕\u201c13-8\u201d。来源标签：本场弹幕（核心）；历史画像（§3/§9 标注）。待官方核对：地图名、MVP。</p>"""),
    ],
    "G1 结束节点 2026-08-26 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- G2 BP

G2_BP = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G2 BP 后/开局情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二 叉车（Cache，弹幕口径）",
    speed_block(
        "G2 进行中 · 图二 叉车",
        [("b-pend", "BP 后/开局节点"), ("b-ok", "灰信号 0 条"), ("b-anchor", "叉车=历史弱图")],
        [
            sig("风险", "var(--bad)", "本节点灰信号 0 条（观众未提假赛/剧本质疑）→ 无风险信号，说明本节点情绪干净 → 详 §2"),
            sig("锚点", "var(--accent)", 'Spirit×叉车 历史弱图叙事（"绿龙叉车太差了""叉车看特尼尔"）；观众预期"叉车绿龙应该能大比分获胜" → 弱图若大胜则叙事修正，值得关注 → 详 §3'),
            sig("盘口", "var(--good)", "无明确数字盘提及，<b>样本不足</b> → 盘口面无信号，需关注市场结算口径 → 详 §4"),
            sig("共识", "var(--purple)", '观众对 G2 叉车持"看衰历史 + 期待大胜"混合态度 → 若大胜则弱图叙事修正（看衰→优势），叉车是本场关键观察 → 详 §5'),
        ],
        "图二为 Spirit 历史弱图；若 Spirit 叉车也拿下且大比分，则\u201c弱图\u201d叙事被削弱；若胶着/再送分，翻车叙事升级。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3（系列 1-0）</td></tr>
    <tr><td>节点</td><td>G2 · BP 后 / 开局（EARLY-GAME）· 图二 叉车（Cache，弹幕口径，官方待核对）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 13:00–13:24 UTC（北京 21:00–21:24）</td></tr>
    <tr><td>关键数据</td><td>3,850 条弹幕 · 密度 156.6 条/分</td></tr>
    <tr><td>状态</td><td>本节点为进行中快照；G2 最终结果见 G2 结束节点 / 整场复盘（Polymarket 仲裁）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（3,533 条）+ CSBOY-Mo 321123（224 条）+ BLAST 官方 660729（93 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房本节点 93 条（部分采，G1 前半段缺口仍存）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", '<p>本节点 <b>0 条</b>。观众未对图二开局提出假赛/剧本质疑。</p>'),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>图二确认</td><td>"图二是叉车？"（12:39 局间确认）→ G2 = Cache（弹幕口径\u201c叉车\u201d）</td><td>—</td></tr>
    <tr><td>历史弱图</td><td>"绿龙叉车太差了""叉车绝对的菜中菜""绿龙什么时候能把叉车练出来"</td><td>待 G2 结果回填（最终 Spirit 胜，弱图叙事修正）</td></tr>
    <tr><td>预期大胜</td><td>"叉车绿龙应该能大比分获胜，有感觉吗"（13:01）</td><td>兑现（Spirit 胜，净胜 4–6）</td></tr>
    <tr><td>关键选手</td><td>"叉车看特尼尔"</td><td>过程观察</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>无明确数字盘提及。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚（预期）</td><td>Spirit · 叉车</td><td>"叉车绿龙应该能大比分获胜"（13:01）</td><td>最终应验（Spirit 胜）</td></tr>
    <tr><td>负锚（历史）</td><td>Spirit × 叉车</td><td>"绿龙叉车太差了/菜中菜"</td><td>过程观察（13:22 异常密度）</td></tr>
    <tr><td>灰信号</td><td>—</td><td>本节点 0 条</td><td>—</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：Spirit 系列 1-0 领先，市场 Map 2 Spirit 高概率；</li>
    <li><b>SHORT</b>：叉车为历史弱图，若 Spirit 大胜则弱图叙事失效，若胶着/送分则强化\u201c状态差\u201d信号；</li>
    <li><b>观察点</b>：叉车执行、送分是否延续。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>13:00–13:01</td><td>图二开始："看手枪局吧，绿龙叉车太差了"· "叉车是那一边选的图？"</td></tr>
    <tr><td>13:04</td><td>密度 295（手枪局/早期）</td></tr>
    <tr><td>13:22</td><td>密度峰值 777："？？？"刷屏——异常回合/操作</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 117；正 11 / 负 12——图二开局情绪混合</td></tr>
    <tr><td>donk</td><td>提及 99；正 1 / 负 6</td></tr>
    <tr><td>tN1R（特尼尔）</td><td>"叉车看特尼尔"——叉车关键选手预期</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>Spirit 叉车历史弱图叙事（观众口径）；BLAST Open Porto 小组赛 BO3；</li>
    <li>观众口径的图池倾向：首 Ban Inferno（炼狱）后叉车必被点（13:46 补充印证）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>13:01</td><td>"叉车绿龙应该能大比分获胜"</td><td>兑现（Spirit 胜，净胜 4–6，见 G2 结束/整场）</td></tr>
    <tr><td>13:00–13:24</td><td>"绿龙叉车太差"（历史叙事）</td><td>过程观察（13:22 异常密度）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（3,533 条）+ CSBOY-Mo 321123（224 条）+ BLAST 官方 660729（93 条），合计 3,850 条。窗口 2026-08-26 13:00–13:24 UTC。来源标签：本场弹幕（核心）；历史画像（§3/§9 标注）。待官方核对：地图名。</p>"""),
    ],
    "BP 后/开局节点 2026-08-26 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- G2 MID

G2_MID = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G2 局中情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二 叉车（Cache，弹幕口径）",
    speed_block(
        "G2 进行中 · 图二 叉车",
        [("b-pend", "局中节点"), ("b-risk", "灰信号 6 条"), ("b-anchor", "送分叙事升级")],
        [
            sig("风险", "var(--bad)", '灰信号 6 条——"暂停又送分""看来教练是买了"等，观众"送分"质疑显著升级 → 若终局前不消除，翻车/假赛叙事风险上升 → 详 §2'),
            sig("锚点", "var(--accent)", 'Spirit 叉车领先但"送分"反复（"有啥用 绿龙马上送分"）；教练读唇语话题（花絮）→ 领先质量存疑，说明 Spirit 执行与经济管理是关键变量 → 详 §3'),
            sig("盘口", "var(--good)", "无明确数字盘提及，<b>样本不足</b> → 盘口面无信号，需关注市场结算口径 → 详 §4"),
            sig("共识", "var(--purple)", '观众认为 Spirit"明着送分"，对教练组玩梗（"被哈利附身"）→ 若 2-0 横扫则归为浪/放松，否则质疑将升级，值得关注 → 详 §5'),
        ],
        "观众\u201c送分\u201d叙事在 G2 局中升级；若 Spirit 仍大胜则\u201c送分=浪/放松\u201d，若被翻盘则叙事强化为假赛质疑——需以结构源（比分/市场）仲裁。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3（系列 1-0）</td></tr>
    <tr><td>节点</td><td>G2 · 局中（MID-GAME）· 图二 叉车（Cache，弹幕口径）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 13:10–13:44 UTC（北京 21:10–21:44）</td></tr>
    <tr><td>关键数据</td><td>5,180 条弹幕 · 密度 149.7 条/分</td></tr>
    <tr><td>状态</td><td>本节点为进行中快照；G2 最终结果见 G2 结束节点 / 整场复盘（Polymarket 仲裁）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（4,710 条）+ CSBOY-Mo 321123（378 条）+ BLAST 官方 660729（92 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房部分采；G1 前半段缺口仍存")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>6 条</td><td>Spirit 侧：送分/故意的/教练买了</td><td>"有啥用 绿龙马上送分" · "故意的吧" · "故意的" · "暂停又送分" · "看来教练是买了" · "明着送分而已，"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（集中 Spirit\u201c送分\u201d叙事；含\u201c教练买了\u201d直接指控，但无局内实锤）。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>叉车领先执行</td><td>"5V4就是集合一波啊"· "一波1打五给打软了"（1v5 残局被打没）</td><td>过程样本</td></tr>
    <tr><td>教练花絮</td><td>"教练为什么要捂着嘴说话""对面的教练被哈利附身了"（13:11–13:16）</td><td>非技术信号</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", "<p>无明确数字盘提及。<b>样本不足。</b></p>"),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>donk · 局中</td><td>提及 232；正 13——"都是手枪为什么donk打的那么牛逼"（赛后亦出现）</td><td>过程正向</td></tr>
    <tr><td>负锚</td><td>Spirit · 送分</td><td>"明着送分而已，"</td><td>兑现统计待回填</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（6 条）</td><td>送分/故意的/教练买了</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：Spirit 领先（观众口径），donk 局中正向；</li>
    <li><b>SHORT</b>：\u201c送分\u201d叙事若在终局前不消除，将放大\u201c假赛/剧本\u201d质疑；若 2-0 横扫则归为浪/放松；</li>
    <li><b>观察点</b>：终局是否维持、市场 Under 2.5 方向。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 局中 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>13:11–13:16</td><td>教练读唇语/哈利附身话题（花絮）</td></tr>
    <tr><td>13:22</td><td>密度峰值 777："？？？"刷屏——异常回合/操作</td></tr>
    <tr><td>13:40+</td><td>持续"送分"批评（"暂停又送分""明着送分而已"）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 192；正 11 / 负 23——局中负向情绪占优</td></tr>
    <tr><td>donk</td><td>提及 232；正 13 / 负 10——正负混合，正向略多</td></tr>
    <tr><td>教练组（哈利/hally）</td><td>玩梗话题（"被哈利附身""怕读唇语"）——非技术信号</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>Spirit 领先后的\u201c送分\u201d模式跨图延续（G1 也有）；</li>
    <li>观众对 Spirit 教练组有玩梗文化（哈利/读唇语）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>13:01</td><td>"叉车大比分获胜"</td><td>待回填（最终 Spirit 胜）</td></tr>
    <tr><td>13:10–13:44</td><td>"送分"叙事（6 条灰信号）</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（4,710 条）+ CSBOY-Mo 321123（378 条）+ BLAST 官方 660729（92 条），合计 5,180 条。窗口 2026-08-26 13:10–13:44 UTC。来源标签：本场弹幕（核心）；历史画像（§9 标注）。待官方核对：地图名。</p>"""),
    ],
    "局中节点 2026-08-26 · 弹幕口径 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- G2 END

G2_END = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · G2 结束情报 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · 图二 叉车（Cache，弹幕口径）· Spirit 胜",
    speed_block(
        "Spirit 2-0 DENDELE（系列结束）",
        [("b-ok", "系列结束 · 市场仲裁"), ("b-risk", "灰信号 2 条"), ("b-anchor", "叉车弱图拿下")],
        [
            sig("风险", "var(--bad)", '灰信号 2 条（"明着送分而已"延续；另一条无关）→ 无实锤，说明末段情绪以 GG/翻盘调侃为主 → 详 §2'),
            sig("锚点", "var(--accent)", "Spirit×叉车（历史弱图）拿下——弱图叙事修正；\u201cGG\u201d于 13:44–13:47 集中出现 → 历史看衰图翻转为优势兑现，值得关注 → 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；Map 2 市场口径：Spirit 99.95c、总回合 19–21、净胜 4–6（13-7/13-8 区间）→ 与市场方向一致，需关注官方比分 → 详 §4"),
            sig("共识", "var(--purple)", '观众对 Spirit 图二过程仍不满（"爆头数比人家人头高""50个人头没有闹麻了"）→ 高预期低过程质量，说明弱队横扫要求下状态信号偏负 → 详 §5'),
        ],
        "Spirit 2-0 横扫与市场一致（系列 Spirit 99.95c、Under 2.5）；\u201c送分/状态差\u201d是跨图持续信号——对后续对手参考价值：Spirit 弱图执行与经济管理是观察项。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>系列结果</td><td><b>Spirit 2-0 DENDELE</b>（Polymarket：系列 Spirit 99.95c、Games Total Under 2.5）</td></tr>
    <tr><td>G2 结果</td><td>Spirit 胜（市场口径：总回合 19–21、净胜 4–6，即 13-7/13-8 区间；弹幕未出现明确比分）</td></tr>
    <tr><td>节点</td><td>G2 · 结束 / 局间（GAME-REVIEW）· 图二 叉车（Cache）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 13:40–14:05 UTC（北京 21:40–22:05）</td></tr>
    <tr><td>关键数据</td><td>2,763 条弹幕 · 密度 104.6 条/分</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（2,537 条）+ CSBOY-Mo 321123（180 条）+ BLAST 官方 660729（46 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729", "BLAST 官方房部分采；G1 前半段缺口仍存（详见整场页）")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>2 条</td><td>Spirit 送分延续；其余为无关玩笑</td><td>"明着送分而已，" · "别在zhaoxintong打的时候吵就行 兄弟没毛"（与比赛无关）</td></tr>
  </table>
  <div class="warnbox">G2 末段观众更多转向 GG/翻盘调侃而非实锤指控；灰信号 2 条均为情绪/玩梗，兑现统计待回填。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>Spirit×叉车 弱图</td><td>历史\u201c叉车太差\u201d叙事</td><td><b>拿下（弱图叙事修正样本）</b></td></tr>
    <tr><td>BP 逻辑</td><td>"都是先首ban炼狱叉车肯定被点啊"（13:46）——首 Ban Inferno 后叉车必被点</td><td>过程印证</td></tr>
    <tr><td>末段残局</td><td>"真菜，2打1被翻盘"（13:47）</td><td>观众口径，队伍归属待官方核对</td></tr>
  </table>"""),
        ("4", "盘口与市场讨论", """<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Map 2 市场口径（可核验）：Map 2 Winner Spirit 99.95c、总回合 O/U 18.5 Over ✓ / 21.5 Under ✓、Spirit -3.5 ✓ / -6.5 未过 ✗ → 13-7 或 13-8 区间。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>donk · 手枪局</td><td>"都是手枪为什么donk打的那么牛逼"</td><td>过程正向</td></tr>
    <tr><td>负锚</td><td>Spirit · 击杀数</td><td>"打个三线队，50个人头没有闹麻了""爆头数比人家人头高"</td><td>过程样本</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（2 条）</td><td>"明着送分而已，"</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：2-0 横扫确认，与市场一致（系列 Under 2.5）；</li>
    <li><b>SHORT</b>：\u201c送分/经济\u201d过程质量信号跨场延续；同日 NAVI vs M80（14:00 UTC 开赛）与 FURIA vs paiN（16:30 UTC）可对照参考；</li>
    <li><b>观察点</b>：Spirit 后续对手战（弱图执行、经济管理、灰信号兑现）。</li>
  </ul>"""),
        ("7", "逐局复盘（G2 末段 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>13:44–13:47</td><td>"gg" 刷屏 + "翻盘我就笑拉了/翻盘有感觉了吗"——末段 DENDELE 反扑未果</td></tr>
    <tr><td>13:46</td><td>密度峰值 434："都是先首ban炼狱叉车肯定被点啊""TNIR是真菜"</td></tr>
    <tr><td>14:00–14:05</td><td>赛后花絮（抽奖/举报玩梗/赵心童），主播转场 NAVI vs M80（"NAVI几点开"）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>提及 80；正 3 / 负 14——赢系列但负向情绪仍高</td></tr>
    <tr><td>donk</td><td>提及 76；正 5 / 负 2——"都是手枪为什么donk打的那么牛逼"</td></tr>
    <tr><td>tN1R（特尼尔）</td><td>"TNIR是真菜"（13:46）——末段被批</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>Spirit 跨图\u201c领先送分\u201d模式（G1/G2 均出现）；</li>
    <li>观众对 Spirit 高要求：弱队必须横扫，过程差仍被骂（"50个人头没有闹麻了"）。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>13:01</td><td>"叉车大比分获胜"</td><td>兑现（Spirit 胜，净胜 4–6）</td></tr>
    <tr><td>13:44</td><td>"翻盘我就笑拉了"</td><td>未发生翻盘（DENDELE 反扑未果）</td></tr>
    <tr><td>13:40–14:05</td><td>灰信号 2 条</td><td>兑现统计待回填（无实锤）</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（2,537 条）+ CSBOY-Mo 321123（180 条）+ BLAST 官方 660729（46 条），合计 2,763 条。窗口 2026-08-26 13:40–14:05 UTC。结果仲裁：Polymarket Map 2 Winner（Spirit 99.95c）+ 系列市场（Under 2.5）。来源标签：本场弹幕（核心）；历史画像（§9 标注）。待官方核对：地图名、MVP。</p>"""),
    ],
    "G2 结束节点 2026-08-26 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


# ---------------------------------------------------------------- FULL

FULL = page(
    "BLAST Open Porto · Spirit vs DENDELE CS · 整场复盘 · 2026-08-26",
    "CS2 · BLAST Open Porto Group A · BO3 · Spirit 2-0 DENDELE",
    speed_block(
        "Spirit 2-0 DENDELE",
        [("b-ok", "系列结束 · Polymarket 仲裁"), ("b-risk", "灰信号约 14 条（跨节点去重）"), ("b-anchor", "遗迹 13-8 + 叉车 13-7/13-8")],
        [
            sig("风险", "var(--bad)", '全场合计灰信号约 14 条（开局 4 + 局中 6 + 末段 2，跨节点去重）——观众对 Spirit"送分/吃/操控"跨图质疑；<b>无实锤，非结论</b> → 详 §2'),
            sig("锚点", "var(--accent)", "G1 遗迹 13-8（优势图兑现但过程难看）；G2 叉车（历史弱图）拿下（13-7/13-8 区间）→ 详 §3"),
            sig("盘口", "var(--good)", "弹幕无数字盘；市场结算：系列 Spirit 99.95c、Under 2.5、两图净胜 4–6 → 详 §4"),
            sig("共识", "var(--purple)", '观众对 Spirit 状态/经济/送分批评跨图持续（"打个三线队，50个人头没有闹麻了"）→ 详 §5'),
        ],
        "Spirit 2-0 与市场一致；最大信号 = Spirit\u201c领先送分/经济管理差\u201d跨图模式 + 灰信号叙事（夺冠后吃）升温——对后续比赛是\u201c高预期低过程质量\u201d参考样本。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Spirit</b> vs <b>DENDELE CS</b> · BLAST Open Porto Group A · BO3</td></tr>
    <tr><td>系列结果</td><td><b>Spirit 2-0 DENDELE</b>（Polymarket 系列 Spirit 99.95c、Games Total Under 2.5）</td></tr>
    <tr><td>逐图</td><td>G1 遗迹 <b>13-8</b>（弹幕"图一绿龙赢了 13-8"）· G2 叉车 <b>13-7/13-8</b>（市场推算：总回合 19–21、净胜 4–6）</td></tr>
    <tr><td>数据窗口</td><td>2026-08-26 11:55–14:05 UTC（北京 19:55–22:05）</td></tr>
    <tr><td>关键数据</td><td>约 19,300 条弹幕（两虎牙房为主 + BLAST 官方房 207 条）</td></tr>
  </table>
  {src_box("CSBOY 官方 123321（17,678 条）+ CSBOY-Mo 321123（1,415 条）+ BLAST 官方 660729（207 条）", "CSBOY 官方 + CSBOY-Mo + BLAST 官方 660729（+ 可选的 SOOP/KICK，本联赛未启用）", "BLAST 官方房 G1 前半段（11:55–12:49）未采，其余覆盖；缺源显式标注，赛后 VOD 可回捞")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>节点</th><th>条数</th><th>代表样本（意译）</th></tr>
    <tr><td>G1 BP/开局</td><td>4</td><td>"经典夺冠后就吃" · "打个三线队伍这样吃力？买了？" · "故意想输去败者组逮捕猎鹰" · "集结号的剧本？"</td></tr>
    <tr><td>G1 局中</td><td>6</td><td>"无脑刚送分" · "还买了俩把吹风机 我没想到" · "打个三线队伍这样吃力？买了？"</td></tr>
    <tr><td>G1 结束</td><td>6</td><td>"操控比赛？" · "真10秒啊，我还故意数了一下" · "放分就是押注大分小分了么" · "对面这队不是major连续给天禄送分的吗"</td></tr>
    <tr><td>G2 局中</td><td>6</td><td>"有啥用 绿龙马上送分" · "故意的吧/故意的" · "暂停又送分" · "看来教练是买了" · "明着送分而已，"</td></tr>
    <tr><td>G2 末段</td><td>2</td><td>"明着送分而已，"（延续）· 一条无关玩笑</td></tr>
  </table>
  <div class="warnbox"><b>预警等级：中</b>。灰信号集中于 Spirit\u201c送分/吃/操控\u201d叙事（跨图持续、时间分散），另含对 DENDELE 的历史送分叙事；全程无局内实锤、无盘口即时重合证据。兑现状态：G1/G2 Spirit 均胜，\u201c被质疑方输球\u201d模式未出现；灰信号兑现率统计待回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（验证）", """<table>
    <tr><th>锚点</th><th>内容</th><th>验证</th></tr>
    <tr><td>G1 遗迹（Spirit 自选）</td><td>历史优势图（"一百胜率遗迹"）</td><td><b>兑现 13-8</b>，但过程被批送分/经济差</td></tr>
    <tr><td>G2 叉车（Cache）</td><td>历史弱图（"绿龙叉车太差了"）；"首ban炼狱叉车肯定被点"</td><td><b>拿下</b>（弱图叙事修正样本）</td></tr>
    <tr><td>donk 手枪局</td><td>"都是手枪为什么donk打的那么牛逼"</td><td>过程正向</td></tr>
  </table>
  <p class="meta">BP 后战绩情报（必抓项）：本场无\u201c选手×地图 X胜Y负\u201d类明确战绩提及（仅观众弱图/强图叙事），已记录。</p>"""),
        ("4", "盘口与市场讨论", """<table>
    <tr><th>市场</th><th>结算口径（Polymarket）</th><th>与弹幕对照</th></tr>
    <tr><td>Map 1 Winner</td><td>Spirit 99.95c</td><td>弹幕"13-8"一致</td></tr>
    <tr><td>Map 2 Winner</td><td>Spirit 99.95c</td><td>弹幕无明确比分，方向一致</td></tr>
    <tr><td>系列 Winner / O/U 2.5</td><td>Spirit 99.95c / Under 2.5 99.95c</td><td>2-0 横扫</td></tr>
    <tr><td>Map1 总回合 21.5 / Map2 总回合</td><td>Under ✓（G1=21 回合）/ 19–21 回合</td><td>低回合慢节奏（观众"上半场20个人头都没有"）</td></tr>
    <tr><td>Map1/2 让分 -3.5 / -6.5</td><td>-3.5 过 ✓ / -6.5 未过 ✗</td><td>净胜 4–6 分</td></tr>
  </table>
  <p class="meta">弹幕侧无明确数字盘提及（样本不足），以上为市场口径交叉核验。</p>"""),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>Spirit · 遗迹 + 叉车</td><td>强图兑现 + 弱图拿下</td><td>应验（2-0）</td></tr>
    <tr><td>正锚</td><td>donk · 手枪局</td><td>"都是手枪为什么donk打的那么牛逼"</td><td>过程正向</td></tr>
    <tr><td>负锚</td><td>Spirit · 送分/经济</td><td>"一优势就喜欢送""绿龙一直在赢但是经济没养好"</td><td>跨图过程兑现（未影响结果）</td></tr>
    <tr><td>负锚</td><td>Spirit · 击杀数</td><td>"打个三线队，50个人头没有闹麻了"</td><td>过程样本</td></tr>
    <tr><td>灰信号</td><td>Spirit 侧（约 14 条去重）</td><td>送分/吃/操控</td><td>未实锤；兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：Spirit 2-0 横扫（市场一致，系列 Under 2.5 应验）；</li>
    <li><b>SHORT</b>：\u201c领先送分/经济管理差\u201d跨图模式是后续强队战的主要风险信号——若对强队仍\u201c送\u201d，翻车概率上升；</li>
    <li><b>灰信号叙事</b>：\u201c夺冠后吃/故意演\u201d的观众质疑跨图升温，需以兑现率统计持续跟踪（本场 0 实锤）；</li>
    <li><b>观察点</b>：Spirit 后续对手（同日 NAVI vs M80、FURIA vs paiN 对照）、弱图执行、官方 MVP。</li>
  </ul>"""),
        ("7", "逐局复盘（证据层）", """<table>
    <tr><th>局</th><th>内容（弹幕口径）</th></tr>
    <tr><td>G1 遗迹 13-8</td><td>11:55 开图；12:05–12:11 被 eco 翻回数回合（"被对面eco翻盘了吗？"）；12:31–12:34 sh1ro 残局 + Spirit 连续 2v1 白送（"明送"）；12:56 大比分 1-0；13:01 "图一绿龙赢了 13-8"</td></tr>
    <tr><td>G2 叉车 13-7/13-8</td><td>13:00 图二开始（"绿龙叉车太差了"）；13:22 密度 777（"？？？"刷屏）；13:40+ 送分批评（"暂停又送分""明着送分而已"）；13:44–13:47 GG 刷屏 + DENDELE 反扑未果；14:00+ 赛后转场 NAVI vs M80</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径）</th></tr>
    <tr><td>Spirit 全队</td><td>赢系列但被批：送分（"明送"）、经济管理差（"经济没养好"）、击杀少（"50个人头没有闹麻了"）</td></tr>
    <tr><td>donk</td><td>手枪局正向（"都是手枪为什么donk打的那么牛逼"）；G1 末段存在感低</td></tr>
    <tr><td>sh1ro</td><td>残局强（"西若又赢了一个残局""又稳又强"）</td></tr>
    <tr><td>tN1R（特尼尔）</td><td>被批：遗迹"次次都晕"、叉车"真菜"（13:46）</td></tr>
    <tr><td>教练组（哈利/hally）</td><td>玩梗（"被哈利附身""怕读唇语"）——非技术信号</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", """<ul>
    <li>BLAST Open Porto 小组赛 BO3；Spirit 强图（遗迹）兑现 + 弱图（叉车）修正，图池叙事更新；</li>
    <li>Spirit\u201c领先送分\u201d模式跨图延续（观众口径，跨场待验证）；</li>
    <li>观众高要求文化：弱队必须横扫，过程差仍被骂。</li>
  </ul>"""),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>11:55–13:01</td><td>观众预期 Spirit 大胜（"绿龙雄起/应该赢"）</td><td>兑现（2-0）</td></tr>
    <tr><td>12:08</td><td>"一百胜率遗迹要没了"</td><td>未兑现（遗迹仍 13-8 拿下）</td></tr>
    <tr><td>13:01</td><td>"叉车绿龙应该能大比分获胜"</td><td>兑现（净胜 4–6）</td></tr>
    <tr><td>13:44</td><td>"翻盘我就笑拉了"</td><td>未发生翻盘</td></tr>
    <tr><td>全场</td><td>灰信号约 14 条（送分/吃/操控）</td><td>0 实锤；兑现率统计待回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">CSBOY 官方 123321（17,678 条）+ CSBOY-Mo 321123（1,415 条）+ BLAST 官方 660729（207 条），合计约 19,300 条；窗口 2026-08-26 11:55–14:05 UTC。完整性缺口：BLAST 官方房 G1 前半段未采（显式标注，VOD 可回捞）。结果仲裁：Polymarket（系列/两图/总回合/让分）为首要结构源；弹幕比分作过程佐证。来源标签：本场弹幕（核心）/ 前局延续（§7）/ 历史画像（§3、§9）/ 市场口径（§4）。待官方核对：两图地图名、MVP、Spirit 小组排名。</p>"""),
    ],
    "整场复盘 2026-08-26 · 弹幕口径 + Polymarket 仲裁 · 灰信号仅为观众质疑非结论",
)


def shell_html(a: str, b: str, league: str, date: str, views: list[tuple[str, str, str | None]]) -> str:
    btns = "".join(
        (
            f'<button class="nbtn" data-src="{v[2]}"' + (' aria-pressed="true"' if i == 0 else "") + f'>{v[0]}<span class="s">{v[1]}</span></button>'
            if v[2]
            else f'<button class="nbtn" disabled style="opacity:.5;cursor:not-allowed" title="此节点暂未采集数据">{v[0]}<span class="s">{v[1]}</span></button>'
        )
        for i, v in enumerate(views)
    )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>比赛详情 · {a} vs {b} · 弹幕情报库</title><style>
:root{{--bg:#f5f5f7;--card:#fff;--ink:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#0071e3}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6;padding:24px 16px 56px}}
.wrap{{max-width:980px;margin:0 auto}}
.top{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
.brand{{font-weight:700;font-size:14px;color:var(--ink);text-decoration:none}}
.crumb{{font-size:12px;color:var(--sub)}} .crumb b{{color:var(--ink)}}
.navi{{font-size:12px;color:var(--sub);text-decoration:none;margin-left:4px}} .navi:hover{{color:var(--accent)}}
h1{{font-size:24px;font-weight:800;margin-bottom:4px}}
.sub{{color:var(--sub);font-size:13px;margin-bottom:14px}}
.picker{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.nbtn{{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:8px 16px;font-size:13px;font-weight:600;color:var(--sub);cursor:pointer}}
.nbtn:hover{{color:var(--accent)}} .nbtn[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:#fff}}
.nbtn .s{{display:block;font-size:10px;font-weight:400;opacity:.85}}
.frame{{width:100%;height:900px;border:1px solid var(--line);border-radius:16px;background:#fff}}
.note{{color:var(--sub);font-size:12px;margin-top:12px}}
footer{{margin-top:16px;font-size:11.5px;color:var(--sub);border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<div class="top">
  <a class="brand" href="../index.html">弹幕情报库</a>
  <span class="crumb">首页 › <a href="today.html" class="navi">今日比赛</a> › <b>{a} vs {b}</b></span>
  <span style="margin-left:auto"><a class="navi" href="history.html">历史情报库</a> <a class="navi" href="../subscribe.html">订阅</a></span>
</div>
<h1>{a} vs {b}</h1>
<div class="sub">{league} · {date} · 按时间点切换查看该场比赛不同阶段的情报输出</div>
<div class="picker">{btns}</div>
<iframe id="view" class="frame" title="时间点情报"></iframe>
<div class="note">时间轴自动产出：赛前 -> 每小局（BP 后 / 局中 / 局末）-> 赛后整场复盘；缺失节点自动出现并标注"此节点暂未采集数据"，不 404。</div>
<footer>弹幕情报库 · 比赛时间轴 · {date}</footer>
</div>
<script>
(function () {{
  var btns = document.querySelectorAll(".nbtn");
  var view = document.getElementById("view");
  function show(src) {{ view.src = src + (src.indexOf("?") < 0 ? "?embed=1" : "&embed=1"); }}
  btns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      btns.forEach(function (x) {{ x.setAttribute("aria-pressed", x === b ? "true" : "false"); }});
      show(b.getAttribute("data-src"));
    }});
  }});
  var first = document.querySelector(".nbtn[aria-pressed='true']");
  if (first) show(first.getAttribute("data-src"));
}})();
</script>
<script>if(location.search.indexOf("embed=1")>-1){{document.querySelectorAll("nav").forEach(function(n){{n.style.display="none"}});document.querySelectorAll("div[style*='max-width:1020px']").forEach(function(n){{n.style.display="none"}});}}</script>
</body></html>"""


def build_shell() -> Path:
    views = [
        ("G1 · BP 后", "G1 · EARLY", "intel_danmu_Spirit-DENDELE_2026-08-26_g1_bp.html"),
        ("G1 · 局中", "G1 · MID", "intel_danmu_Spirit-DENDELE_2026-08-26_g1_mid.html"),
        ("G1 · 结束", "G1 · REVIEW", "intel_danmu_Spirit-DENDELE_2026-08-26_g1_end.html"),
        ("G2 · BP 后", "G2 · EARLY", "intel_danmu_Spirit-DENDELE_2026-08-26_g2_bp.html"),
        ("G2 · 局中", "G2 · MID", "intel_danmu_Spirit-DENDELE_2026-08-26_g2_mid.html"),
        ("G2 · 结束", "G2 · REVIEW", "intel_danmu_Spirit-DENDELE_2026-08-26_g2_end.html"),
        ("系列复盘", "FINAL · SERIES-REVIEW", "intel_danmu_Spirit-DENDELE_2026-08-26_full.html"),
    ]
    html = shell_html("Spirit", "DENDELE CS", "CS2 · BLAST Open Porto Group A", "2026-08-26", views)
    return write("match_cs2-ts7-dendel-2026-08-26.html", html)


def write(name: str, html: str) -> Path:
    out = REPORTS / name
    out.write_text(html, encoding="utf-8")
    print("wrote", out)
    return out


if __name__ == "__main__":
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g1_bp.html", G1_BP)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g1_mid.html", G1_MID)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g1_end.html", G1_END)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g2_bp.html", G2_BP)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g2_mid.html", G2_MID)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_g2_end.html", G2_END)
    write("intel_danmu_Spirit-DENDELE_2026-08-26_full.html", FULL)
    build_shell()
