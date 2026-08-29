弹幕情报库 · 系统分类框架 v1

# 弹幕情报库 · 系统分类框架

v1（2026-08-24）· 从"每场比赛的弹幕整理"升级为"可跨场复用的专业情报库" · 实体化 + 关系化 + 验证化

13英雄锚点（champions）
8阵容/体系（compositions）
36昵称映射（aliases）
11验证样本（应验/反例）

## 一、四大域分类

| 域 | 实体 | 文件 | 状态 |
| --- | --- | --- | --- |
| **A 实体域** 谁/什么 跨场复用 | 联赛 | leagues.json | 已有格式/爆冷传统/卡时间文化/灰风险 |
| 队伍 | teams.json | 已有风格/核心/纪律/灰历史 |  |
| 选手 | players.json | 已有英雄池焦点/正负锚/留痕 |  |
| 英雄 / 阵容 / 地图 | champions.json / compositions.json | 新增 v1版本符号/搭配/克制/体系/图池 |  |
| **B 事件域** 发生了什么 | 比赛 + 局级节点 | matches.json + node_data/ | 已有47 场 |
| **C 信号域** 观众共识/异常 | BP 信号 / 实体留痕 | bp_signals.json / bp_entities.json | 已有17 条信号 |
| 灰信号 / 实体留痕 | gray_signals.json / gray_entities.json | 已有27 条 · 兑现率统计 |  |
| **D 市场域** 盘口对照 | 盘口/价格 | match 内嵌 + snapshots/ | 已有 |

### 跨切面

- 记忆分层 LONG / SHORT / TRANSIENT（MEMORY_TIERS.md）

- 验证双轨：应验 / 未应验并列（validation_samples.json，11 条）

- 版本/时间：patch + 有效期（patches.json）· 阵容 as-of（rosters.json.changes）

- 多路共振：信号记录带 routes 字段（单路=低置信，两路=升置信）

## 二、关系模型

league ──< team ──< player
player ──(熟练度/锚)── champion        （杰斯×Zeus=正锚 / 杰斯×弱队=负锚）
champion ──(搭配)── champion           （卢锡安 × 米利欧/娜美）
champion ──(克制)── champion           （冰鸟 > 蛇女 > 发条）
composition = 核心英雄 + 体系类型 + 克制关系 + 适用队伍
team ──(惯用体系)── composition        （KC = 乌龟/卡时间体系）
match ──(局级 BP)── pick 组合 → bp_signals（选手×英雄锚）
客观层 official/official_matches.json ↔ matches.json（按 match_id 关联）

## 三、已落地文件（v1）

| 文件 | 内容 |
| --- | --- |
| docs/data/intel/aliases.json | 36 条昵称→官方名映射（绿龙=Spirit / 超雄=Monki / 啪哒克=待核实…），全部带证据，未核实不猜 |
| docs/data/intel/rosters.json | 队伍名册（GX/TH/KC/SHFT/SK/NS/BFX）+ 阵容变动（TH Sheo→Daglas / KC 中单疑似变动） |
| docs/data/intel/champions.json | 13 个英雄锚点（杰斯/蛇女/冰鸟/卢锡安/剑魔/永恩/卡牌/盲僧/纳尔/维克托/瑞兹/女警/赵信） |
| docs/data/intel/compositions.json | 8 个体系 + 3 条图池锚（卢锡安+米利欧 / 蛇女+盲僧 / 卡时间 / 锁头 / 卡牌上单 / 剑魔打野负锚…） |
| docs/data/intel/validation_samples.json | 应验/反例 11 条（含 KC 灰信号方向反例、蛇女单局未应验） |
| docs/data/intel/patches.json | patch 登记 + "锚点必须带版本窗口"约定 |
| docs/data/intel/official/official_matches.json | 客观层：10 场官方结算（Polymarket closed / 战报） |
| tools/intel_query.py | 检索：`python3 tools/intel_query.py 蛇女` / `--entity team kc` |

## 四、路线图

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 地基 | 官方名册/昵称映射 + patch 版本 + 多路 routes 约定 | 已完成 v1 |
| 1 实体层 | champions / compositions / 客观层初版 | 已完成 v1 |
| 2 自动采集 | BP 锁定自动记录 pick 组合入库 + 锚点自动检索推送（黄金窗口） | 待做 |
| 3 统计画像 | 锚点应验率/体系胜率统计 + champion/composition 画像页 + 交叉检索 | 待做 |
| 4 产品化 | 聚合展示 + 付费墙（免费赛后 / 付费实时节点） | 待定 |

范围定稿（2026-08-24 用户确认）：1/2/4/5/6/7/9 做；3（官方基线胜率对照）不做；8（产品/合规）只加提醒。规范全文：knowledge/INTEL_LIBRARY_TAXONOMY.md。
