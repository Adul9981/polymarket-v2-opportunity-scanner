# 交接：自动扫描 + 自动交易（用户需求清单与现状盘点）

创建日期：2026-08-16

> 用途：本文件是"让另一个会话完成自动交易工作"的交接底稿。
> 新会话先读本文件，再读引用的核心文档；按"三步路径"推进，
> 不跳级、不越过红线。

## 1. 用户需求（原话整理）

```text
核心需求：基于已有的能力和整个项目库的能力，自动去交易——
  自己扫完比赛，然后自己执行交易。
背景：已经复盘了大量比赛、积累了大量队伍情报（DNS 新打野、KT 射手弱点、
  SK 定价失真、让一追二深反、假赛疑似信号等）；
  用户希望自动化来克服人性弱点（全仓、追高、不止损等）。
```

## 2. 现状盘点（已核实）

### 已能做的

```text
1. 扫比赛：任务 2 扫描器 tools/market_scanner.py 已实现
   （自动扫比赛列表、识别机会、给出候选排名），状态：待验收；
2. 做判断：knowledge/ 情报库 + 复盘库可作方向依据
   （INTEL_SIGNALS.md / EWC_CS2_LIBRARY.md / PSYCHOLOGY_NOTES.md 等）；
3. 出计划：固定金额、分档买入、止盈、风控的完整交易计划
   （tools/grid_config_generator.py / prepare_grid_trade.py）；
4. 盯盘：1 分钟价格流 tools/fetch_price_snapshot.py +
   bar 监控 tools/bar_monitor_runner.py；
5. 手动交易闭环（任务 1）：已完成，可真实挂单/止盈/复盘。
```

### 还差的（为什么现在不能直接全自动）

```text
1. 任务 4（半自动交易台：用户点确认后执行）未开始；
2. 任务 2 扫描器停在"待验收"，未完成真实比赛 live 验证；
3. V2 执行闭环（1 分钟信号驱动）代码已实现，但未经过真实比赛
   live 验收 + 小额实盘，按成熟度纪律不算完成；
4. 下单链路仍需人工确认环节（任务 1 手动闭环）。
```

### 风控配置（config/risk_limits.json，已核实）

```text
全局：每日上限 $200 / 单市场上限 $80 / 并发 3 个市场；
autopilot：enabled=true（注意：与根 AGENTS.md 描述"默认关闭"存在出入，
  需新会话核实生效口径），requires_user_enabled_session=true
  （需要用户在本会话显式开启）；
允许自主执行：S1 低价反转（A_DEEP_REVERSAL）、S2 热门回撤（B_FAVORITE_DIP）；
S3（强势小回撤）需确认；S4（持仓管理）仅建议；
主动平仓（卖出已有持仓）必须用户明确表达。
```

### 红线（不得越过）

```text
1. 超出风控限额；放宽限额必须用户确认（收紧可自主）；
2. 方向/token 解析有歧义时不猜、不下单；
3. 策略成熟度不足（S3 未验证、S4 只建议、未到 L3 的新策略）不自动实盘；
4. 异常状态（疑似重复下单、订单状态不明、数据不更新、
   接近终局/spread 过大）自动暂停；
5. 绝不读取/复制/移动私钥；绝不修改 polydata 仓库，只调用其接口；
6. 主动平仓必须用户明确表达；按计划自动止盈/卖出除外。
```

## 3. 三步路径（不跳级）

```text
第 1 步（现在就能做）：
  自动扫完比赛 -> 输出机会清单（方向/形态/买入区间/预期回报/风险提示）
  -> 用户挑选 -> 用户确认后执行下单。
  产出物：runtime/opportunity_candidates.json + reports/opportunity_scan_*.md

第 2 步：任务 4 半自动交易台
  用户只需在确认台点"确认"，其余自动（读取候选 -> 生成计划 ->
  挂单 -> 止盈 -> 状态检查）。

第 3 步：任务 5 全自动小额试运行
  最小金额跑通"扫 -> 判 -> 下 -> 复盘"闭环，带风控和自动复盘，
  连续验证稳定后再放开额度。
```

## 4. 新会话第一步的具体任务

```text
1. 读本文件 + docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md（三层框架）
   + docs/task/PROJECT_PROGRESS.md（任务进度）；
2. 跑一次自动扫描（dry-run，只读不下单）：
   python3 tools/task2_pipeline.py --once
   或 python3 tools/market_scanner.py --live
3. 输出机会清单给用户挑选：每场注明
   方向 / 形态 / 买入区间 / 预期回报 / 风险提示 / 建议仓位（<=30%）；
4. 用户确认后，用任务 1 流程执行（先 dry-run，再实盘）；
5. 每笔交易结束后写复盘到 knowledge/reviews/ 并更新比赛库。
```

## 5. 关键资源索引

```text
项目档案：AGENTS.md（红线/窗口分工）
进度：docs/task/PROJECT_PROGRESS.md
自动化设计：docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md
风控：config/risk_limits.json
白名单/扫描：config/market_watchlist.json、config/discovery_patterns.json
策略模板：config/strategy_templates.json
情报库：knowledge/INTEL_SIGNALS.md、knowledge/leagues/EWC_CS2_LIBRARY.md
心理记录：knowledge/PSYCHOLOGY_NOTES.md（全仓/追高/止损模式与规则）
复盘索引：knowledge/reviews/index.md
扫描器：tools/market_scanner.py
候选流程：tools/task2_pipeline.py
bar 监控：tools/bar_monitor_runner.py
价格流：tools/fetch_price_snapshot.py
```

## 6. 用户纪律要求（写入执行规则）

```text
1. 单笔 <=30%，全仓一票否决（任何理由不例外）；
2. 高位 80c+ 先锁盈（D2），不赌翻倍；
3. 疑似假赛/解说提示信号：先减仓/锁盈，不反手；
4. 连亏 2 笔强制降档；情绪激动后 30 分钟不开新仓；
5. 盈利新高先提现；连续 3 笔盈利后下一笔强制最小仓（连胜奖励预警）；
6. 方向判断双侧对照（熟悉队 + 对手侧情报），缺一侧视为信息不足，
   信息不足时只允许小仓试注或不下注；
7. 试仓 -> 验证 -> 滚仓顺序不可逆。
```
