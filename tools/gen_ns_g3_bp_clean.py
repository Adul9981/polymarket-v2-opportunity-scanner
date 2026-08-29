#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NS vs BFX G3 BP 后/开局情报（干净窗口版，2026-08-27）。
窗口 17:22-17:44 北京（09:22-09:44 UTC，G3 BP/开局，不含 G2 尾段与局间）；
阵容为 Riot 官方 window API 校准（规则 22：事实层只信官方源）。
"""

from pathlib import Path

from gen_spirit_dendele_pages import page, speed_block, sig, src_box  # noqa: E402

REPORTS = Path("/Users/ad/Documents/polymarket/reports")


G3_BP = page(
    "LCK Play-In · NS vs BFX · G3 BP 后/开局情报 · 2026-08-27",
    "LoL · LCK 骑士之路 R1 · BO5 · G3（系列 1-1）",
    speed_block(
        "G3 进行中 · BP 后/开局",
        [("b-pend", "BP 后/开局节点"), ("b-risk", "灰信号 11 条（G3 窗口）"), ("b-anchor", "官方阵容已校准")],
        [
            sig("风险", "var(--bad)", '灰信号 11 条——"这不是故意送吗""梦魇打假赛"（<b>非结论</b>）→ 详 §2'),
            sig("锚点", "var(--accent)", "G3 官方阵容（Riot API）：NS Syndra 中野 / BFX Azir 中单——弹幕\u201c狐狸\u201d为 G2 沿用，勿配对 → 详 §3"),
            sig("盘口", "var(--good)", "Polymarket Game 3 NS 领先（约 54.5c）→ 详 §4"),
            sig("共识", "var(--purple)", '"洛克优势 队友团战开得好 大招直接融化"（NS 中野）· "大龙推进不了"（节奏讨论）→ 详 §5'),
        ],
        "G3 决胜关键局；本页数据窗口为 G3 BP/开局（不含 G2 尾段），阵容走官方源；NS 中野组合 vs BFX Azir 体系是主观察点。",
    ),
    [
        ("1", "比赛信息与结果总览 / 状态核验", f"""<table>
    <tr><td>对阵</td><td><b>Nongshim Red Force（NS）</b> vs <b>BNK FEARX（BFX）</b> · LCK 骑士之路 R1 · BO5（系列 1-1）</td></tr>
    <tr><td>节点</td><td>G3 · BP 后 / 开局（EARLY-GAME）· <b>实时节点</b></td></tr>
    <tr><td>数据窗口</td><td>2026-08-27 17:22–17:44（北京时间；G3 BP/开局，<b>不含 G2 尾段与局间</b>）</td></tr>
    <tr><td>关键数据</td><td>1,528 条弹幕 · 672 活跃用户 · 密度 66.8 条/分</td></tr>
  </table>
  {src_box("硕硕 323444 + 957 890001 + 米勒 149361 + LOL 官方 660000 + Riot 官方 window API（阵容）", "同左 + 官方数据源", "阵容为官方 API 校准（非弹幕推断）；窗口严格限定 G3 开局")}"""),
        ("2", "灰信号汇总（风险 · 观众质疑非结论）", """<table>
    <tr><th>条数</th><th>指向</th><th>样本（意译）</th></tr>
    <tr><td>11 条</td><td>NS/BFX 演·剧本叙事（G3 窗口内）</td><td>"这不是故意送吗" · "这就是故意送的啊 有大的狐狸一直飞" · "梦魇打假赛" · "风暴龙翻盘剧本"</td></tr>
  </table>
  <div class="warnbox">预警等级：<b>中</b>（G3 窗口内观众\u201c故意送/打假赛/剧本\u201d质疑 11 条；无盘口即时重合证据，非实锤）。兑现统计待回填。纪律：灰信号只作风险标注，不作假赛结论。</div>"""),
        ("3", "BP 锚点与选人情报（官方校准）", """<table>
    <tr><th>队伍</th><th>官方阵容（Riot API window，17:44 抓取）</th><th>说明</th></tr>
    <tr><td>NS（红）</td><td>Kingen Jax / Sponge Naafiri / Scout Syndra / Diable Varus / Lehends Nautilus</td><td>中野 Naafiri+Syndra（"洛克优势 大招直接融化"）</td></tr>
    <tr><td>BFX（蓝）</td><td>Clear KSante / Raptor Olaf / VicLa Azir / Taeyoon Ashe / Kellin Seraphine</td><td>VicLa 换 Azir；弹幕\u201c狐狸\u201d为 G2 沿用/口误</td></tr>
  </table>
  <p class="meta">阵容以官方 window 数据为准（非弹幕推断）；弹幕英雄名（狐狸等）若与官方不一致，一律以官方为准并标注（规则 22 实践）。</p>"""),
        ("4", "盘口与市场讨论", '<p>弹幕无明确数字盘。<b>样本不足。</b>Polymarket Game 3 NS 领先（约 54.5c）；系列 1-1 决胜盘口悬念大。</p>'),
        ("5", "方向性情报板（锚点 × 共识 × 灰信号）", """<table>
    <tr><th>类型</th><th>对象</th><th>内容</th><th>验证</th></tr>
    <tr><td>正锚</td><td>NS · 中野</td><td>"洛克优势 队友团战开得好 大招直接融化"（Naafiri+Syndra）</td><td>待 G3 结束回填</td></tr>
    <tr><td>负锚（条件）</td><td>NS · 推进</td><td>"大龙推进不了" · "把狐狸终结了不亏 大龙也推不了"</td><td>待 G3 结束回填</td></tr>
    <tr><td>灰信号</td><td>NS/BFX 演·剧本（11 条）</td><td>"故意送/打假赛/风暴龙翻盘剧本"</td><td>兑现统计待回填</td></tr>
  </table>"""),
        ("6", "情报含义与决策落点", """<ul>
    <li><b>LONG</b>：NS 中野组合（官方确认）是 G3 主看点，市场 NS 领先；</li>
    <li><b>SHORT</b>：NS 推进/大龙节奏（"大龙推进不了"）与灰信号叙事是变量；BFX Azir 体系能否延续翻盘势头；</li>
    <li><b>观察点</b>：G3 中段节奏、官方 gameWins 回填。</li>
  </ul>"""),
        ("7", "逐局复盘（G3 早期 · 证据层）", """<table>
    <tr><th>阶段</th><th>内容（弹幕口径）</th></tr>
    <tr><td>17:22–17:30</td><td>G3 BP/选人：官方阵容锁定（NS Jax/Naafiri/Syndra/Varus/Nautilus；BFX KSante/Olaf/Azir/Ashe/Seraphine）；"这阵容没有前排"讨论</td></tr>
    <tr><td>17:30–17:44</td><td>开局：NS 中野优势（"洛克优势 大招直接融化"）；推进节奏讨论（"大龙推进不了"）；灰信号 11 条（故意送/打假赛）</td></tr>
  </table>"""),
        ("8", "队伍 / 人员画像（证据层）", """<table>
    <tr><th>选手（队）</th><th>评价（弹幕口径 + 官方阵容）</th></tr>
    <tr><td>NS Scout（中）</td><td>G3 Syndra（官方）；"洛克优势"（弹幕赞 NS 中野）</td></tr>
    <tr><td>BFX VicLa（中）</td><td>G3 Azir（官方）；弹幕\u201c狐狸\u201d为 G2 沿用/口误，勿配给本局</td></tr>
    <tr><td>NS/BFX 全队</td><td>灰信号叙事（故意送/打假赛，非结论）</td></tr>
  </table>"""),
        ("9", "联赛规律与版本（沉淀层）", "<ul><li>LCK 骑士之路 BO5 决胜局；Azir/Syndra 中单对决版本焦点；\u201c大龙推进不了\u201d节奏叙事。</li></ul>"),
        ("10", "预测验证回填（沉淀层）", """<table>
    <tr><th>时刻</th><th>预测</th><th>结果</th></tr>
    <tr><td>17:3x</td><td>"洛克优势 大招直接融化"（NS 中野）</td><td>待 G3 结束回填</td></tr>
    <tr><td>17:4x</td><td>"大龙推进不了"（条件式）</td><td>待 G3 结束回填</td></tr>
  </table>"""),
        ("11", "数据与溯源", """<p class="meta">弹幕：硕硕 323444 + 957 890001 + 米勒 149361 + LOL 官方 660000（1,528 条，17:22–17:44 北京时间，<b>G3 窗口不含 G2 尾段/局间</b>）；阵容：Riot 官方 window API（gameId 117030752644841580，17:44 抓取）。来源标签：阵容=官方源；共识/灰信号=本场弹幕。待官方核对：G3 比分。</p>"""),
    ],
    "G3 BP 后/开局节点 2026-08-27 · 官方阵容 + 弹幕口径 · 灰信号仅为观众质疑非结论",
)


if __name__ == "__main__":
    out = REPORTS / "intel_danmu_Nongshim Red Force-BNK FEARX_2026-08-27_g3_bp.html"
    out.write_text(G3_BP, encoding="utf-8")
    print("wrote", out)
