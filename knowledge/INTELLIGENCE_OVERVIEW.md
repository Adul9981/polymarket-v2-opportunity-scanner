# 情报资产总览（数据情报库）

最后更新：2026-08-18

定位：把分散在评论、弹幕、信号、画像、案例中的情报资产统一编排，
作为情报库平台（任务 6）的数据底座与人工复核入口。
可视化总览：reports/intel_assets_overview_2026-08-18.html（SAP/Apple 风格）

## 一、结构化数据层（docs/data/intel/，机器可读）

| 文件 | 条数 | 内容 | 更新约定 |
| --- | --- | --- | --- |
| matches.json | 4 | 比赛情报（弹幕推断结果/关键信号/数据文件/报告/复盘） | 每场分析后更新 |
| gray_signals.json | 5 | 灰信号（假赛/剧本/卡盘质疑：时段/关键词/关联盘口/严重度） | 每场分析后更新 |
| leagues.json | 5 | 联赛档案（灰信号风险/平台/直播间/规律观察） | 联赛级事件后更新 |
| teams.json | 7 | 队伍画像（弹幕提及/情绪/标签/盘面倾向/信任等级） | 每场分析后更新 |
| players.json | 15 | 选手画像（讨论焦点/褒贬/特征英雄/待确认项） | 每场分析后更新 |
| users.json | 10 | 高价值弹幕用户（跨平台聚合/专业分型） | 跨场累计 |

## 二、评论情报（Polymarket 评论区）

```text
规则：knowledge/COMMENT_ANALYSIS_RULES.md（series 层抓取/时间线对照/情绪分级）
数据：docs/data/snapshots/*/comments/（原始 + 切片）
批量工具：tools/fetch_series_comments.py + tools/comment_intel.py（已接 task2_pipeline）
评论者画像：knowledge/COMMENTERS.md（EurekaWTI：08-17 单日 5/5 命中 + DNS 3:1 系列赛验证）
信号库：knowledge/INTEL_SIGNALS.md + knowledge/intel_signals.json（9 条，含评论/弹幕/解说）
```

## 三、弹幕情报（虎牙 + SOOP，观众集体智慧）

```text
总入口：knowledge/DANMU_README.md；规则：knowledge/DANMU_CAPTURE_RULES.md
数据：docs/data/danmu/（虎牙 4 房 + SOOP LCK_CL；近期 ~1.9 万条）
工具：fetch_huya_danmu / fetch_soop_danmu / danmu_intel / danmu_report / danmu_live_monitor
报告：reports/intel_danmu_*.html（SAP/Apple 风格）
情报汇总：knowledge/DANMU_INTEL.md；画像：TEAM_PROFILES / DANMU_USERS / STREAMER_PROFILES
```

## 四、假赛疑似案例库（FIXED_MATCH_SUSPECT_CASES.md）

| 案例 | 场次 | 状态 | 核心证据 |
| --- | --- | --- | --- |
| 1 | GIANTX vs Vitality（08-14） | 高度疑似 | 领先 1 万经济不打团 + ADC 肉装 + 解说提示 |
| 2 | T1 vs DNS G2（08-17） | 疑似 | 暂停/chronobreak + 评论区 match fixing 共识 |
| 3 | NAVI vs TH（08-17） | 疑似观察 | G1 有优势不兑现 + G2 开局送 + 弹幕任务论 |
| 4 | GGA vs BRO（08-18） | 高度疑似 | BRO 91c->0.5c + 两路弹幕指瑞兹故意送 |

## 五、近期比赛复盘（knowledge/reviews/）

| 比赛 | 结果 | 情报关联 |
| --- | --- | --- |
| T1 vs DNS（08-17） | DNS 3:1 | 评论区舆情 + 案例 2 + IS-2026-08-17-001/002 |
| NAVI vs TH（08-17） | NAVI 2:0 | 弹幕任务论 + 案例 3 + 用户 65c 正样本 |
| GGA vs BRO（08-18） | BRO 2:1 | 两路弹幕印证 + 案例 4 + 用户 G3 恐慌卖出/20U 反手 |

## 六、已确认方法与待办

```text
已确认方法：
1. 弹幕密度峰值 = 价格异动窗口（GGA/BRO、DNS/NS 多次应验）——可作实时事件告警；
2. 评论区 lead-lag：方向性发言与后续价格可对照（EurekaWTI 单日 5/5）；
3. 两路独立弹幕共识（虎牙+SOOP）指向同一对象 = 强灰信号。
待办：
1. 灰信号关键词词表定期扩充（KC/GX/Canna 等新队伍/选手易漏）；
2. 弹幕×行情自动对照接入（DANMU_POLYMARKET_ROADMAP）；
3. 案例 1-4 逐项核查（录像/官方/后续表现）；
4. 评论者与弹幕用户画像跨场累计样本。
```
