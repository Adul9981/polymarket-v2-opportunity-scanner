# EWC CS2 赛事族台账（Esports World Cup - Counter-Strike 2）

> 用途：登记 EWC 体系下所有已采集/已复盘的 CS2 比赛（主赛事 + Open Qualifier），
> 按赛事标签归类，沉淀赔率形态与交易模式。
> 赛事标签以 Polymarket Gamma 官方标题为准。

## 赛事标签体系

```text
Esports World Cup（EWC）主赛事：
  Group A/B/C/D：小组赛 BO1/BO3，各队按组内循环/淘汰推进
  （本库已收录：Group B / Group C / Group D）
Esports World Cup Open Qualifier（公开资格赛）：
  Group 9 / Group 10 / Group 13 / Group 14：入围阶段 BO3
  Play-Ins：附加赛 BO3
```

## 比赛台账

| 比赛（slug） | 日期 | 赛事标签 | 赛果 | 赔率形态（快照分类） | 状态 |
| --- | --- | --- | --- | --- | --- |
| cs2-vael-og1-2026-08-07 | 08-07 | EWC Open Qualifier Group 9 | OG 2:0 | G1/G2 热门全程压制（OG 48-51c -> 100c）；整场 A3 折价修复 | 已复盘（G1/G2/整场） |
| cs2-lone-pha-2026-08-07 | 08-07 | EWC Open Qualifier Group 10 | Phantom 2:0 | G1/G2 B4 阴跌（levelONE 44-50c -> 0）；整场 Phantom A3 折价修复 | 已复盘（G1/G2/整场） |
| cs2-eye-pha-2026-08-08 | 08-08 | EWC Open Qualifier Group 10 | **EYE 2:1**（Map1 EYE、Map2 PHA、Map3 EYE） | Moneyline 5:5 开 -> Map1 EYE 赢 70-79c -> Map2 EYE 一度 86.5c 被 PHA 逆转 -> G3 EYE 拿下 | 已复盘（终局回填） |
| cs2-fokus-par3-2026-08-07 | 08-07 | EWC Open Qualifier Group 13 | FOKUS 2:0 | G1 A1 极值反转（9c -> 100c）；G2 A3 折价修复；整场热门压制 | 已复盘（G1/G2/整场） |
| cs2-shu1-nrg-2026-08-07 | 08-07 | EWC Open Qualifier Group 14 | NRG 2:0 | G1/G2 C2 五五开开局碾压（NRG 44-45c -> 100c） | 已复盘（G1/G2/整场） |
| cs2-ace1-van1-2026-08-07 | 08-07 | EWC Open Qualifier Group 14 | Acend 2:0 | G1/G2 B4 阴跌（Vandulken -> 0）；整场 Acend 热门压制 | 已复盘（G1/G2/整场） |
| cs2-fnc-k271-2026-08-09 | 08-09 | EWC Open Qualifier Play-Ins | K27 2:1（让一追二） | Map1 K27 B4 阴跌；Map2 A1 极值反转（11c -> 100c）；整场 6c -> 100c | 已复盘（终局回填） |
| cs2-prv-b8-2026-08-12 | 08-12 | EWC 主赛事 Group C（BO1） | B8 赢 | B8 40c -> 8.5c -> 24-27 卖出 -> 终局 0.9995（单图硬币波动） | 已复盘 |
| cs2-bb3-faze-2026-08-12 | 08-12 | EWC 主赛事 Group B（BO1） | FaZe 赢 | BetBoom 5c 深水区未反转（50/50 -> 5/95 -> 回拉）；深水区多数归零补证 | 已复盘 |
| cs2-fut-mouz-2026-08-14 | 08-14 | EWC 主赛事 Group C（BO3） | **FUT 2:1**（Map1 FUT、Map2 MOUZ、Map3 FUT） | Map1 MOUZ 51c -> 37c -> 24c -> 0.7c（B4 阴跌）；Map2 MOUZ 21.5c -> 99.5c（A2 反转）；整场 FUT 26.5c -> 99.5c | 已复盘（终局回填） |
| cs2-wc1-pain-2026-08-15 | 08-15 | EWC 主赛事 Group D（BO3） | **paiN 2:1**（G1 Wildcard、G2/G3 paiN） | G1 Wildcard A2 中位反转（20.5c -> 100c）；G2/G3 paiN 反转；整场 paiN 29.5c -> 98c | 已复盘（G1/G2/整场，待正式结算） |
| cs2-mglz-navi-2026-08-15 | 08-15 | EWC 主赛事 Group D（BO3） | G1 NAVI、G2 MGLZ（1:1；G3 价格指向 NAVI 2:1，未结算） | G1 MGLZ B4 阴跌；G2 MGLZ A2/A5 双底（25c -> 100c）；整场 W 型 | 已复盘（G1/G2/整场，**待终局回填**） |

## 赔率形态统计（当前样本 n=12）

```text
G1/G2 单图常见形态：
  B4 直线阴跌（领先方被翻/弱侧归零）  8 次
  A1/A2/A5 反转（深水或中位翻盘）    5 次
  C2 五五开开局碾压                  3 次
整场（Moneyline）常见形态：
  A3 折价修复 / 热门全程压制          6 次
  A1/A2 反转（让一追二）             3 次
  B4 阴跌（下狗归零）                3 次
```

## 已提炼的 CS2 交易模式（对照复盘结论）

```text
1. BO3 系列赛 Moneyline 的"让一追二"深反（K27 6c->100c、paiN 29.5c->98c、
   MGLZ G2 25c->100c）：深水区（<=20c）低买、中位（25-40c）确认后加仓，
   正期望主要来自"翻盘确认后"的加仓段，不是极值抄底段；
2. BO1 单图（Group B/C 小组赛）硬币波动：40c->8c->70c 级别摆动，
   不适合价格止损（B8 卖飞案例），只按彩票预算参与或不参与；
3. 热门全程压制（Acend/Phantom/OG/NRG/FOKUS 2:0）：赛前 50c 上下、
   开图即碾 -> 100c，强队侧赛前建仓需早（<55c），追高无价值；
4. 弱侧 B4 阴跌归零是多数情况（8/12 图含 B4），"深水区多数归零"
   仍是基准，反转是少数——低买必须按彩票仓处理；
5. 5:5 开盘的"五五开"场（EYE/PHA、BB3/FaZe）波动剧烈且方向不定，
   属于观察样本，不主动下注（需等 Map1 方向确认）。
```

## 待办

```text
1. MGLZ vs NAVI G3 终局确认（当前价格指向 NAVI 2:1，市场未正式结算）；
2. EYE vs PHA 已终局回填（EYE 2:1）✅；
3. FUT vs MOUZ 已终局回填（FUT 2:1）✅；
4. 07 系列 5 场 Open Qualifier 已逐场复盘（Group 9/10/13/14）✅；
5. 后续 EWC 主赛事小组赛（Group A-D）继续按本台账登记，
   重点积累"BO1 vs BO3"形态差异与让一追二样本。
```
