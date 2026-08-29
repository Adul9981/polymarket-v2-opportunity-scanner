# Polymarket 预测市场电竞网格交易项目

项目导航（中文）。会话入口与红线见 AGENTS.md；文档总章程见 docs/AGENTS.md。

## 这是什么

从 Polymarket 公开行情识别可交易的电竞市场现象，用固定金额网格策略交易，并把每笔交易沉淀为复盘知识库。本仓库不持有私钥，真实下单复用 polydata 仓库的钱包能力。

核心方法论：现象（P1–P6）→ 策略（S1–S4）→ 验证（L0–L4）→ 自动化（三层框架：触发 / 决策 / 输出）。

## 文档地图

| 目录 | 内容 | 入口 |
| --- | --- | --- |
| docs/framework/ | 方法论、策略库、固定金额制 | [PROJECT_FRAMEWORK.md](docs/framework/PROJECT_FRAMEWORK.md) |
| docs/runbook/ | V1 执行手册、价格纪律 | [V1_RUNBOOK.md](docs/runbook/V1_RUNBOOK.md) |
| docs/task/ | 任务进度、自动化设计、情报库产品、验证交接 | [PROJECT_PROGRESS.md](docs/task/PROJECT_PROGRESS.md) · [TASK6 情报库产品](docs/task/TASK6_INTELLIGENCE_LIBRARY_PRODUCT.md) |
| docs/data/ | 数据采集、打点、切片、采集目标清单 | [DATA_COLLECTION_GUIDE.md](docs/data/DATA_COLLECTION_GUIDE.md) · [采集目标清单](docs/data/COLLECTION_TARGETS.md) |
| docs/research/ | 历史研究材料（只读） | - |
| tools/ | 执行准备 / 实盘执行 / 发现回测工具 | tools/AGENTS.md |
| config/ | 策略模板、白名单、风控限额 | config/AGENTS.md |
| schemas/ | JSON 字段约定 | schemas/AGENTS.md |
| runtime/ | 状态文件、打点标记、启动器、日志 | runtime/AGENTS.md |
| reports/ | 回测、扫描、诊断报告 | reports/AGENTS.md |
| knowledge/ | 交易复盘与成交明细 | knowledge/README.md |

## 当前状态

```text
任务 1（手动交易闭环）：已完成
任务 2（自动扫描机会）：待验收，设计文档已定稿
任务 3-5：未开始
任务 6（电竞交易情报库·订阅制网站）：进行中 · 高优先级
```

## 快速上手

运行任务 2 live 只读扫描（验证交接见 docs/task/V2_VALIDATION_HANDOFF.md）：

```bash
./runtime/run_task2_live_scan.command
```

打点比赛窗口（详情见 docs/data/DATA_COLLECTION_GUIDE.md）：

```bash
python3 tools/event_marker.py --watch --interval 30
```

## 安全边界

```text
只读取公开行情，不读取私钥。
发现层（任务 2/3）不下单；执行必须经过任务 1 链路与用户确认。
autopilot 默认关闭，需用户在本会话显式开启。
```
