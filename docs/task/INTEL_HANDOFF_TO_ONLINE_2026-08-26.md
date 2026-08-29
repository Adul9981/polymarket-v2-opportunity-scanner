# 弹幕情报交接文档（本地 → 线上端 · 2026-08-26）

> 用途：给线上情报库端（danmupulse.com / VPS danmu-intel）的交接材料。
> 目标：两端执行同一套标准与防错规则，结果口径统一，避免今天 KT-BRO
> 赛果不一致这类冲突。本文档可直接复制给线上对话参考执行。

## 一、结果口径：最高优先级（本次教训）

```text
1. 比赛"终局结果"发布前，必须用 Polymarket 结算价 / 官方比分源仲裁；
   弹幕"一波了/结束了/拿下/恭喜X"只能作候选信号，不能作最终结果。
2. 弹幕终局信号必须持续确认到比赛真结束（基地爆炸/官方结算/
   Polymarket 收敛 99+），禁止凭推进阶段弹幕提前判终局。
3. 多端结果不一致时，以 Polymarket 结算价为最终仲裁，立即修正所有发布物。

教训（KT-BRO G5，2026-08-26）：
- 本地端 20:38 凭"一波了/恭喜bro"提前判 BRO 3-2；
- 实际 20:45 KT 鳄鱼偷家翻盘，KT 3-2（Polymarket lol-kt-bro2 结算 KT 99.95c）；
- 线上端判定正确（KT 3-2）。本地端已修正全部页面并固化规则。
```

## 二、情报输出标准（v2 12 段决策导向模板）

```text
0  核心情报速览（第一屏·硬门槛）：比分 + TOP 信号（风险→锚点→盘口→共识）+
   决策落点；每条信号可溯源（→ 详 §N）
1  比赛信息与结果总览 / 状态核验
2  灰信号汇总（条数/指向/预警 + "观众质疑·非结论"纪律）
3  BP 锚点与选人情报（BP 后战绩情报必抓项）
4  盘口与市场讨论
5  方向性情报板（锚点 × 共识 × 灰信号）
6  情报含义与决策落点（LONG/SHORT）
7  逐局复盘（证据层）
8  队伍 / 人员画像（带提及量）
9  联赛规律与版本（沉淀层）
10 预测验证回填明细（闭环）
11 数据与溯源

多语言规范：信号层全中文意译、原文折叠（≤2 条/信号）、黑话双语
（야필패=亚索必败、마핸=让分盘）、队名/选手名统一。
来源分层标签：本场弹幕 / 前局延续 / 历史库 / 推测（外推三型，条件化）。
```

## 三、防错规则（AGENTS.md 规则 1-18，两端必须一致）

```text
重点规则：
9   结果校验自主化：多信号共振 + 多源交叉 + 官方/比分源核对；
12d 比赛状态与结束检测：时间门槛（≥30 分钟才可判结束）、真实时间优先、
    跨时区禁止 UTC 日期与北京比较、误判产物清理；
12d5 结果判定门禁（match_state_guard）：时间门槛 / 结构源优先 /
    反讽识别 / 比分源滞后 四道闸，门禁不过 = 情报未交付；
14  赛果判定优先级：官方比分源 / 比分机器 / 权威比分站 / 用户确认 > 弹幕情绪；
    英文弹幕反讽（"FNC ARE BACK" 等）必须先做语气判定；
16  队名歧义防误：英文俚语 "OKBRO/bro tax" 不得当作 BRO 战队信号；
17  情报来源分层：核心=本场弹幕、补充=前局+历史库（先验时效）、
    推测=条件化+标注；无中生有零容忍；
18  终局判定结构源仲裁（见第一节）。
```

## 四、采集现状（两端并行不冲突）

```text
主源：虎牙（当前 LCK/LPL/LEC/CS2/Dota2 中文弹幕）。
  LCK 默认采集集：957(890001) / 毛毛(149346) / 米勒(149361) /
  Remember(528222) / 硕硕(323444)
  CS2 默认采集集：CSBOY(123321) / CSBOY-Mo(321123) / BLAST(blast) /
  BLAST 官方(blast)
SOOP：LCK CL 官方流（afchall 296450537）+ VOD 回捞。
KICK：CS2（eslcs / gaules / esportsworldcup / cs2_maincast），Pusher WS。
Twitch：2026-08-26 用户决定暂停（连接假死问题已修静默重连，注册表标记
  "暂停可恢复"）——两端都不要自动启用 Twitch，除非用户明确恢复。

原则（数据端完备性）：同一场比赛必须覆盖该联赛所有已登记直播间，
同一比赛所有房间同一 session；缺源显式标注（实际/预期/缺口）。
```

## 五、数据与配置清单（迁移/同步参考）

```text
docs/data/danmu/streamer_registry.json  直播间注册表（25 源，12 启用；
  Twitch 8 暂停可恢复 / KICK CS2 4 已恢复 / maxixi 已删除（与 123321 同房，2026-08-27 彻底移除））
docs/data/intel/team_names.json         队伍命名唯一权威（abbr/aliases）
docs/data/intel/aliases.json            队名/选手名映射
docs/data/intel/leagues.json            联赛档案（默认采集集/灰信号风险/规律）
docs/data/intel/matches.json            比赛档案（含 result_inferred 字段）
docs/data/intel/gray_signals.json      灰信号记录（条数/指向/兑现）
docs/data/intel/bp_signals.json        BP 锚点记录（正负锚/验证回填）
config/market_watchlist.json            赛事白名单（tag_id=64）
```

## 六、标准样例（本地端产出，供线上核对样式）

```text
reports/intel_danmu_LCK-KT-BRO_G1..G5_2026-08-26.html   逐局页（v2 12 段）
reports/intel_danmu_LCK-KT-BRO_full_2026-08-26.html     整场复盘（KT 3-2）
reports/intel_danmu_BFX.Y-HLE.C_v2_2026-08-26.html      A 类标杆（速览卡/多语言）
reports/intel_danmu_DNS-DRX_2026-08-24_v2.html          A 类（盘口交叉）
reports/intel_danmu_NAVI-FNC_2026-08-24_v2.html         B 类（防错核验示范）
每页必须带同名 MD 镜像（knowledge/intel_pages/）。
```

## 七、建议的两端分工

```text
线上端（danmupulse.com）：发布主端——7×24 采集、订阅/付费墙、站点展示、
  时间轴壳、画像页上线。
本地端：质量基准 + 快速生成——v2 模板规范、防错规则、标准样例、
  终局仲裁（Polymarket 结算）。
同步机制：结果口径统一用 Polymarket 结算仲裁；新规则先写 AGENTS.md +
  INTEL_HTML_TEMPLATE.md，再同步到线上生成器；两端采集并行不冲突。
```

## 八、本次 KT vs BRO 系列最终口径（供线上核对）

```text
KT 3-2 BRO（KT 晋级第 5 种子/季后赛；BRO 出局）
G1 KT 胜（用户确认）| G2 BRO 胜（大龙翻盘）| G3 BRO 胜（碾压）
| G4 KT 胜（四保一寒冰）| G5 KT 胜（BRO 双龙未终结，KT 鳄鱼偷家）
灰信号：G2/G3 指向输家侧 KT（兑现）；G4/G5 指向赢家侧（未兑现输球）
Polymarket：lol-kt-bro2-2026-08-26 结算 KT 99.95c
```
