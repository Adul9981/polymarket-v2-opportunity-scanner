# V2 一分钟信号驱动捕捉闭环

最后更新：2026-08-09

版本名：**V2 一分钟信号驱动捕捉闭环**（代号：V2-盯盘执行闭环 / V2 Execution Loop）

```text
真实资金模式：V2-Live（tools/bar_monitor_runner.py --execute-live）
dry-run 模式：V2-Signal（--autopilot / --execute）
文档入口：本文档（定义与验收）+ docs/runbook/V2_LIVE_RUNBOOK.md（实盘手册）
核心工具：tools/bar_monitor_runner.py
```

## 0. 多策略框架（V2 不是一个策略，是一组策略模块）

```text
V2-S1 盘中信号捕捉：每分钟盯 1 分钟 bar，形态信号出现才挂单。
      工具 tools/bar_monitor_runner.py（--autopilot / --execute-live）—— 已建。

V2-S2 赛前预测挂单：赛前预测今天可能出现什么形态，按预测提前挂 resting 单。
      工具 tools/prematch_predictor.py（--event-file 离线测试 / --slug 实盘）—— v1 已建。
      输入：赛前赔率（热门>=65%）、形态气候（反转日/崩塌日）、队伍画像
      （TEAM_PROFILES）、情报信号（intel_signals）、联赛信誉（LPL/LEC 降档）。
      输出：预测形态 + 置信度 + 依据；对应策略模板的预挂单计划（dry-run）。

V2-S3 未来可扩展：赛前预测 + 盘中信号合并执行（同一市场防重复挂单）。
```

## 1. 定义

V2 = 基于 1 分钟 bar 监控的形态信号捕捉闭环：

```text
开赛前用户给一句："交易这个市场，S2 买热门侧"
-> bar 引擎每分钟盯 1 分钟 bar + 实时中间价
-> 形态信号出现（跌进回撤区 / 极低位单根拉升 >=10c / 破止损线）
-> 自动生成 resting 限价单计划（不市价追）
-> 计划经 dry-run 展示并确认后挂单
-> 成交后自动配止盈 + 止损卖单（monitor 常驻）
-> 全程状态 / 动作 / 复盘自动记录
```

与 V1 的区别：V1 是"用户链接 + 手动确认 + 一次性挂单"；V2 是"引擎盯盘 + 信号驱动 + 自动管理仓位"。

## 2. 行为契约（2026-08-09 用户确认）

```text
1. autopilot 默认关闭；用户在本会话显式开启后才进入自动执行。
2. 自动执行前仍 dry-run 展示计划一次（符合"实盘前先 dry-run"纪律）。
3. 盘中用户可以随时喊停（撤单 / 关闭 monitor）。
4. 金额沿用现有风控上限：单市场 $80、单日 $200、并发 3。
5. 方向 / token 解析有歧义时不猜、不下单。
```

## 3. 实现状态（v1 已建，2026-08-09）

```text
已实现：
- bar_monitor_runner --autopilot：信号 -> 计划 -> grid_plan_runner dry-run ->
  待确认（pending_plan 状态），不自动下单。
- --execute-live：仅在有待确认计划且 autopilot 开启时执行；执行后自动拉起
  grid_plan_runner monitor（成交 -> 自动配止盈 + 止损卖单）。
- 计划内交易所级止损：trade_config.stop_loss（非彩票型策略，S2/Mid80 用
  no_entry_below 作止损价），monitor 成交后自动挂 resting 卖单（D3 落地）。
- 风控闸前置：autopilot 开关、策略白名单、预算上限、并发市场上限、计划去重。
- 离线验证：门禁（未开启不下单）、计划生成含止损单、去重、无待确认计划拒绝执行。
```

待真实比赛 live 验收：

```text
1. 活跃比赛上验证 1 分钟 bar 流 + 信号（08-13/14 LCK 进窗口，或指定一场真实比赛）。
2. 全链路 dry-run：信号 -> 计划 -> 待确认（不碰真钱）。
3. 小额实盘：用户确认 + autopilot 开启后，小金额跑通 挂单 -> 成交 -> 止盈/止损。
4. 验收通过后从 L3 小额实盘升级节奏（每笔复盘闭环）。
```

## 4. 用法

```bash
# 盯盘 + 信号 + 计划（dry-run，不碰钱）
python3 tools/bar_monitor_runner.py --slug <event-slug> --outcome <队名> \
  --strategy B_FAVORITE_DIP --autopilot --watch

# 确认待确认计划并执行（真实资金！需交互输入 yes，或 --yes 显式确认）
python3 tools/bar_monitor_runner.py --slug <event-slug> --outcome <队名> \
  --strategy B_FAVORITE_DIP --execute-live
```

前置条件：config/risk_limits.json 的 autopilot.enabled=true（用户显式开启）；
网络可访问 Polymarket；polydata 钱包可用。

真实资金路径说明：`--execute-live` 是唯一真实下单入口（走 grid_plan_runner），
`--autopilot`/`--execute` 均为 dry-run 不碰钱。真实挂单前有余额预检 + 交互确认；
完整流程见 docs/runbook/V2_LIVE_RUNBOOK.md。

## 5. 边界

```text
只挂 resting 限价单，绝不市价追。
止损卖单是交易所级 resting sell（Polymarket 无原生止损单类型）；
盘中 D2/D3 跟踪止损由引擎输出动作，由 monitor/人工确认执行。
彩票型策略（S1 深反）不挂止损单（归零预算即止损）。
```
