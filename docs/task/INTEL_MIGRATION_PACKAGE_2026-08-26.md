# 弹幕情报线上迁移配置包（2026-08-26）

> 用途：把本地弹幕情报体系迁移/同步到线上产品。
> 框架规格见 knowledge/INTEL_TEMPLATE_HANDOFF.md（模板/层级/多语言/门禁）；
> 本文档 = 迁移所需的配置与数据文件清单 + 字段口径，直接照单搬运。

## 一、必须迁移的文件（配置 + 数据）

### 1. 配置类（线上工具运行时读取）
```text
docs/data/danmu/streamer_registry.json   直播间注册表（平台/房间/关注赛事/优先级/采集状态）
docs/data/intel/team_names.json          队伍命名唯一权威（id/abbr/full/aliases）——所有归一化以此为准
docs/data/intel/aliases.json             队名/选手名映射补充
docs/data/intel/leagues.json             联赛档案（默认采集集/灰信号风险/联赛规律/词表方向）
config/market_watchlist.json             赛事白名单（LoL：LCK/LPL/LCP/LEC/KeSPA Cup；
                                          CS2：IEM/BLAST/EWC；Dota2：TI/ESL One；tag_id=64）
config/risk_limits.json                  风控限额（每日 $200 / 单市场 $80 / 并发 3，唯一权威）
```

### 2. 情报数据类（结构化库，随比赛持续更新）
```text
docs/data/intel/matches.json       比赛档案（id/日期/联赛/队伍/比分/逐局/灰信号/锚点/预测）
docs/data/intel/gray_signals.json  灰信号记录（条数/指向/预警/兑现统计）
docs/data/intel/bp_signals.json    BP 锚点记录（正锚/负锚/方向/验证回填）
docs/data/intel/teams.json         队伍画像（风格/核心/盘面倾向/信任等级）
docs/data/intel/players.json       选手画像（英雄池/状态/提及量）
docs/data/intel/users.json         高价值用户画像
```

### 3. 原始弹幕数据（按需迁移，量大）
```text
docs/data/danmu/<platform>/<date>_<source>.jsonl
字段：platform / channel / source / user / nick / text / ts（ISO UTC）
线上建议：VPS 直接采集落盘，本地不再搬运原始数据。
```

## 二、字段口径（与线上库对齐，避免两侧对不上）

```text
1. 队伍：只用 team_names.json 的 abbr 展示（KRX.C/BFX.Y/KT/BRO）；
   全称仅用于详情页标题；禁止裸用新写法。
2. 联赛：一级=游戏（LoL/CS2/Dota2/Valorant），二级=联赛（LCK/LCK CL/LPL/LEC/…）；
   判定优先级：标题关键词 -> matches.json 元数据 -> 已知队伍反推 -> 不硬猜（"-"）。
3. 结果：一律带"弹幕口径·官方待回填"；系列终局须 2-0/2-1 类比分或官方积分榜
   （1-0/1-1 只是局末）；判定走 match_state_guard 四道闸。
4. 灰信号：只作聚合风险标注 + 盘口对照；对外必写"观众质疑·非结论"。
5. 来源分层标签：本场弹幕 / 前局延续 / 历史库 / 推测（每条信号级结论必带）。
6. 时间：判定统一 UTC epoch 比较，页面按北京时间展示。
```

## 三、线上适配要点（与本地差异）

```text
1. 三层情报：整场（_full_）/ 小局（_G1_…）/ 局内节点（_BP_/_S0_-_S4_）；
   线上默认生成三层，整场页顶部带小局+节点导航。
2. 付费边界：已结束比赛实时情报免费；仅"实时进行中/未开赛"节点为 Pro 付费
   （按比赛是否结束判定，勿按文件名一刀切）。
3. 及时性：小局结束/节点后 3-5 分钟内输出（快节点 + 并行生成 + 结算状态迭代）。
4. 生成端审计：速览卡/方向板信号缺来源标签 = 阻止发布。
5. 结果校验：复用 match_state_guard（时间门槛/结构源/反讽/滞后四道闸）。
6. 双格式：每份情报 HTML + MD 镜像（MD 为全文，覆盖 12 段骨架）。
```

## 四、迁移步骤建议

```text
1. 拷配置：streamer_registry / team_names / aliases / leagues / market_watchlist；
2. 建库表：matches / gray_signals / bp_signals / teams / players / users（字段同本地 schema）；
3. 接采集：VPS 上跑 run_danmu_session（虎牙为主，SOOP/KICK 按需），落盘 JSONL；
4. 接输出：按 INTEL_TEMPLATE_HANDOFF.md 12 段模板生成 HTML+MD；
5. 接校验：match_state_guard + speedcard_consistency 作为发布门禁；
6. 接付费/免费墙：add_paywall（按比赛结束状态）；
7. 回归：跑 tests/（93 项）保证口径一致。
```
