# 文档管理规范

最后更新：2026-08-07

本文是项目文档的总章程，所有会话先读根目录 AGENTS.md，再读本文，然后按窗口类型读对应手册。

## 1. 原则

```text
一个主题一个文档，一个文档一个职责；不堆大杂烩。
根目录只留两个入口：AGENTS.md（项目档案）+ README.md（项目导航）。
现行规范与历史研究材料严格分开：现行文档进 docs/ 对应目录，历史材料进 docs/research/。
每个目录一份 AGENTS.md 说明职责与规则；新增内容先找归属，找不到就改本规范。
状态变更先更新 docs/task/PROJECT_PROGRESS.md，再动其他文档。
文档一律中文；代码 docstring/注释以英文为主。
git：默认不提交、不推送，git 操作只在用户显式要求时做。
```

## 2. 顶层结构

```text
polymarket/
├── AGENTS.md                  # 项目档案：会话分工、模块地图、红线（入口）
├── README.md                  # 项目导航：给人和会话看的文档地图
├── docs/                      # 全部文档（规范 + 历史）
│   ├── AGENTS.md              # 本文：文档管理规范
│   ├── framework/             # 核心方法论与策略（现行规范）
│   │   ├── PROJECT_FRAMEWORK.md            # 固定金额制与策略参数
│   │   ├── PHENOMENON_STRATEGY_FRAMEWORK.md # P/S/M 分层总规则
│   │   └── STRATEGY_PATTERN_LIBRARY.md      # 策略模式与成熟度
│   ├── VIDEO_PRODUCTION_STANDARDS.md      # 视频制作最高准则（图文并茂/LoL 元素/对比分析）
│   ├── runbook/               # 执行手册（现行规范）
│   │   ├── V1_RUNBOOK.md                    # 任务 1 执行专用手册
│   │   ├── V1_1_TRADE_COMMAND_GUIDE.md      # 交易命令与价格纪律
│   │   └── V1_1_PROFIT_LOCK.md              # D2 自动锁盈
│   ├── forensics/             # 交易者拆解域（外部交易者行为 -> 可复制策略）
│   │   ├── KNOWLEDGE_BASE.md                # 基础知识库：概念/规则/账号/数据源
│   │   ├── STRATEGY_LIBRARY.md              # 策略库：可复制策略与成熟度
│   │   ├── DISSECTION_GUIDE.md              # 逐场拆解流程与反馈机制
│   │   ├── data/                            # 基础资料库：原始数据与账号资料
│   │   └── cases/                           # 逐场拆解案例
│   ├── task/                  # 任务进度、设计、交接（现行规范）
│   │   ├── PROJECT_PROGRESS.md              # 任务 1-5 进度库
│   │   ├── TASK2_AUTOMATION_CANDIDATE_FLOW.md # 自动化候选流程设计
│   │   └── V2_VALIDATION_HANDOFF.md         # 任务 2 live 验证交接
│   ├── data/                  # 数据采集与打点（现行规范）
│   │   └── DATA_COLLECTION_GUIDE.md         # 抓取、粒度、打点、切片
│   └── research/              # 历史研究材料（不作现行规范，不再新增）
├── config/                    # 策略模板、现象标签、白名单、风控限额（配置即文档）
├── schemas/                   # JSON 字段约定
├── tools/                     # Python 工具（执行准备 / 实盘执行 / 发现回测）
├── runtime/                   # 运行状态、打点标记、.command 启动器、日志
├── reports/                   # 回测、扫描、诊断、风险报告
├── knowledge/                 # 交易复盘知识库与成交明细
└── examples/                  # 示例文件
```

## 3. 文档类型与归属

| 类型 | 目录 | 说明 |
| --- | --- | --- |
| 项目档案 | 根 `AGENTS.md` | 会话分工、模块地图、红线，每个会话必读 |
| 项目导航 | 根 `README.md` | 文档地图，新会话先看它找路 |
| 方法论与策略 | `docs/framework/` | 固定金额制、P/S/M 分层、策略库、成熟度 |
| 执行手册 | `docs/runbook/` | V1 实盘执行、价格纪律、锁盈 |
| 任务进度与设计 | `docs/task/` | 任务状态、验收、设计文档、交接说明 |
| 数据采集 | `docs/data/` | 抓取接口、粒度、打点、切片 |
| 交易者拆解 | `docs/forensics/` | 外部交易者行为拆解、可复制策略、原始数据 |
| 历史研究 | `docs/research/` | 旧版产品稿、原型、研究材料，只读不增 |
| 配置 | `config/` | 策略模板、现象标签、白名单、风控限额 |
| Schema | `schemas/` | 交易配置、候选、打点等 JSON 字段约定 |
| 工具 | `tools/` | 每个工具自带 docstring，目录规则见 tools/AGENTS.md |
| 运行状态 | `runtime/` | 状态文件、打点标记、启动器、日志 |
| 报告 | `reports/` | 回测、扫描、诊断、风险报告，按日期命名 |
| 复盘知识库 | `knowledge/` | 交易复盘（reviews/）、成交明细（trades/） |

> 2026-08-19 新增：`knowledge/VERIFICATION_METHODOLOGY.md` 结果校验自主化方法论
> （全项目通用：默认自主校验、多信号共振、灰信号不放大、误判修正流程）。

## 4. 会话窗口 -> 文档映射

| 窗口类型 | 必读 | 产出写入 |
| --- | --- | --- |
| 交易执行窗口 | docs/runbook/ 三个手册 | runtime/ 状态 + knowledge/reviews/ 复盘 |
| 交易复盘窗口 | knowledge/README.md | knowledge/reviews/ |
| 主窗口（默认） | docs/framework/ + docs/task/PROJECT_PROGRESS.md | 按下表主题定位 |

内容主题映射（主窗口说什么 -> 落到哪个文档）：

| 我在会话里提到/产出 | 落到哪里 |
| --- | --- |
| 新现象、新策略、成熟度变更 | docs/framework/STRATEGY_PATTERN_LIBRARY.md + PHENOMENON_STRATEGY_FRAMEWORK.md |
| 固定金额、策略参数、风控限额 | docs/framework/PROJECT_FRAMEWORK.md + config/risk_limits.json |
| 任务状态、验收、下一步 | docs/task/PROJECT_PROGRESS.md |
| 自动化设计（触发/决策/输出） | docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md（其他任务按任务建 TASKx_*.md） |
| 执行规则、挂单、止盈、撤单 | docs/runbook/ 对应手册 |
| 数据抓取、打点、切片 | docs/data/DATA_COLLECTION_GUIDE.md |
| 交易者拆解、可复制策略 | docs/forensics/（AGENTS.md 起步） |
| 回测、扫描、诊断 | reports/（前缀 backtest_ / scan_ / diag_） |
| 交易复盘、经验教训 | knowledge/reviews/（daily 或事件级） |
| 成交明细 | knowledge/trades/ |
| 弹幕情报 / 主观情报（解说信号、队伍画像、高价值用户） | knowledge/DANMU_README.md（总索引）+ DANMU_INTEL.md / DANMU_USERS.md / TEAM_PROFILES.md |
| 弹幕×行情对接规划 | docs/task/DANMU_POLYMARKET_ROADMAP.md |
| 工具代码 | tools/ |
| 配置变更 | config/ |
| 历史研究、不再现行 | docs/research/（不再新增） |

## 5. 阶段映射

| 阶段 | 文档去向 |
| --- | --- |
| L0 观察 / 现象 | STRATEGY_PATTERN_LIBRARY.md 样本区 + 复盘库 |
| L1 建议 | framework 文档登记 |
| L2 回测 / 模拟 | reports/backtest + framework 成熟度更新 |
| L3 小额实盘 | runbook + runtime 状态 + knowledge/reviews |
| L4 稳定实盘 | framework 策略库升级 |
| 任务设计 / 验收 / 交接 | docs/task/：设计文档 -> 进度库状态 -> 交接文档 |

## 6. 命名规范

```text
目录：小写（framework / runbook / task / data / research）。
文件：小写 + 下划线，保持现有风格（PROJECT_FRAMEWORK.md）。
日期：reports/ 与 knowledge/reviews/ 用 YYYY-MM-DD 前缀；同一天多次产出加时间或序号。
类型前缀：backtest_ / scan_ / diag_ / review_ / trade_ / intel_danmu_（弹幕情报）。
报告不覆盖历史，按日期追加新文件。
打点标记：runtime/markers/YYYY-MM-DD.jsonl，状态在 runtime/markers/state.json。
拆解案例：docs/forensics/cases/YYYY-MM-DD_<slug>/README.md。
原始数据：docs/forensics/data/<目标>/<内容>.json，只增不改。
```

## 7. 维护纪律

```text
1. 新增文档先查第 3 节归属；没有归属，先改本规范再加文档。
2. 移动或重命名文档，必须用 rg 全库搜旧名字，更新所有引用。
3. 每次会话结束前检查：本次说过/产出过的东西，有没有文档该写没写。
4. 状态变更顺序：PROJECT_PROGRESS 先行，再改策略库/手册。
5. 历史材料只进 docs/research/，不删除、不改造。
```

## 8. 迁移对照（2026-08-07 已执行）

| 原位置 | 新位置 |
| --- | --- |
| PROJECT_FRAMEWORK.md | docs/framework/PROJECT_FRAMEWORK.md |
| PHENOMENON_STRATEGY_FRAMEWORK.md | docs/framework/PHENOMENON_STRATEGY_FRAMEWORK.md |
| STRATEGY_PATTERN_LIBRARY.md | docs/framework/STRATEGY_PATTERN_LIBRARY.md |
| V1_RUNBOOK.md | docs/runbook/V1_RUNBOOK.md |
| V1_1_TRADE_COMMAND_GUIDE.md | docs/runbook/V1_1_TRADE_COMMAND_GUIDE.md |
| V1_1_PROFIT_LOCK.md | docs/runbook/V1_1_PROFIT_LOCK.md |
| PROJECT_PROGRESS.md | docs/task/PROJECT_PROGRESS.md |
| TASK2_AUTOMATION_CANDIDATE_FLOW.md | docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md |
| V2_VALIDATION_HANDOFF.md | docs/task/V2_VALIDATION_HANDOFF.md |
| DATA_COLLECTION_GUIDE.md | docs/data/DATA_COLLECTION_GUIDE.md |
| esports_volatility_product_spec.md 等 7 个历史文件 | docs/research/ |
