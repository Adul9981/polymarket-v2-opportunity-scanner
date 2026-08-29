情报库数据资产总览 · 2026-08-18

# 情报库数据资产总览

*情报库平台（任务 6）· 数据底座 · 更新于 2026-08-18 · 弹幕/评论均为主观数据，对外只展示聚合结论与统计

    **46**结构化情报条目（6 类数据文件）
    **~1.8万**弹幕样本（虎牙 + SOOP，近两日）
    **175+**评论者画像（EurekaWTI 全量）
    **4**假赛疑似案例（1 高度疑似×2 / 疑似×2）

## 结构化数据层（docs/data/intel/）

### matches.json · 4 场

比赛情报：弹幕推断结果、关键信号、数据文件、报告与复盘链接（每场分析后更新）。`docs/data/intel/matches.json`

### gray_signals.json · 5 条

灰信号：假赛/剧本/卡盘质疑，含时段、关键词、关联盘口、严重度；只作风险标注。`docs/data/intel/gray_signals.json`

### leagues.json · 5 个

联赛档案：灰信号风险、覆盖平台/直播间、规律观察（LCK CL 风险已上调至低-中）。`docs/data/intel/leagues.json`

### teams.json · 7 队

队伍画像：弹幕提及、情绪、标签、盘面倾向、信任等级（BRO 新增瑞兹送局标签）。`docs/data/intel/teams.json`

### players.json · 15 人

选手画像：讨论焦点、褒贬、特征英雄、待确认项（新增 BRO 中单瑞兹待确认）。`docs/data/intel/players.json`

### users.json · 10 人

高价值弹幕用户：虎牙/SOOP 跨平台聚合，按专业特征分型，跨场累计可信度。`docs/data/intel/users.json`

### 评论情报

Polymarket 评论区：规则库、series 层快照、comment_intel 已接入扫描流水线；EurekaWTI 单日 5/5 命中。`knowledge/COMMENT_ANALYSIS_RULES.md · COMMENTERS.md`

### 弹幕情报

虎牙 + SOOP 全链路（抓取→监控→分析→复盘）；密度峰值=价格异动窗口已多次应验。`knowledge/DANMU_README.md · DANMU_INTEL.md`

## 近期比赛 × 情报关联

    [](../knowledge/reviews/2026-08-17_lol-t1-dnf-2026-08-17_g1g2.md)
    [](../knowledge/reviews/2026-08-17_lol-navi-th-2026-08-17_navi.md)
    [](../knowledge/reviews/2026-08-18_lol-genga-bro1-2026-08-18_genga.md)

| 比赛 | 结果 | 复盘 | 弹幕/评论 | 灰信号 / 案例 |
| --- | --- | --- | --- | --- |
| T1 vs DNS 08-17 · BO5 | DNS 3:1 | 复盘 | 评论区暂停舆情（match fixing / chronobreak） | 案例 2 疑似IS-001 confirmed |
| NAVI vs TH 08-17 · LEC | NAVI 2:0 | 复盘 | 弹幕任务论 248 条关键词命中 | 案例 3 疑似观察用户 65c 正样本 |
| GGA vs BRO 08-18 · LCK CL | 1:1 待终局 | 复盘 | 两路弹幕（虎牙+SOOP）指瑞兹故意送 | 案例 4 高度疑似LCK CL 观察升级 |
| DNS vs NS（K杯决赛） 08-18 | DNS 3:0 | DANMU_INTEL | 暂停潮灰信号（做局/回溯冠军） | 灰信号 40+ 条 |

## 关键结论

### ① 弹幕密度峰值 = 价格异动窗口

GGA/BRO（20:40 峰值 82 条/分 vs BRO 91c→0.5c）、DNS/NS 多次应验；可作实时事件告警。

### ② 评论区 lead-lag 可检验

方向性发言与后续价格可对照（EurekaWTI 08-17 单日 5/5 + DNS 3:1 系列赛验证）。

### ③ 两路独立弹幕共识 = 强灰信号

虎牙中文 + SOOP 韩语指向同一选手（瑞兹）= 高价值印证，但仍是"观众质疑，非结论"。

### ④ LCK CL 联赛级观察升级

"高位崩盘 + 送局论"从个例（DNS/NS 暂停潮）升级为联赛规律观察项，待统计验证。

    溯源：数据文件见 docs/data/danmu/、docs/data/snapshots/*/comments/、docs/data/intel/；
    规则见 knowledge/DANMU_CAPTURE_RULES.md、COMMENT_ANALYSIS_RULES.md；
    灰信号纪律：只作风险标注与盘口对照素材，不作为假赛证据；对外呈现写明"观众质疑，非结论"。
