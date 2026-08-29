# 预测市场网格交易 MVP 实施笔记

## 第一版范围

第一版先不做全自动机会发现；下单前必须先 dry-run 检查。

工作流：

```text
用户发比赛截图/链接/语音转文字描述
-> 用户只补充：想买哪一边，或描述比赛形态
-> Codex 辅助判断策略 A/B，后续扩展到 C/D
-> Codex 判断当前价格是否适合执行
-> 自动生成 trade_config.json
-> dry-run 检查多档买卖计划
-> grid_plan_runner.py 复用现有执行机器人挂买单
-> 成交后按卖出计划立即挂卖单
-> 保留固定成本金额的彩票仓
```

## 最小输入格式

用户日常只需要发：

```text
市场链接：
Game / Map：
想买方向：
策略类型：可选，A / B；不填则由系统判断
固定金额：可选，默认按模板
```

当前准备器支持：

```text
--strategy auto
```

如果用户不指定策略，系统会先按自然语言和价格区间识别：

```text
A：低位拉扯 / 深度反转
B：强队临时低估 / 热门方回撤
C：强势碾压 / 理财局，仅建议
D：已有持仓救援 / 成本管理，仅建议
```

系统自动决定：

```text
买入价
买入档位
每档金额
卖出价
每档卖出成本金额
彩票仓金额
```

如果用户没有指定更细参数，使用默认模板。

自然语言输入示例：

```text
这场 Game 2 我想买 PlayTime，感觉是强队回撤，按默认金额。
这局赛前差不多四六开，现在一边掉到 30 多，帮我看看能不能接。
我之前买了热门方，现在跌下来了，不想止损，帮我做持仓管理。
```

## 两类策略

任务 1 当前只执行 A/B。
C/D 先作为待设计策略登记，不直接进入自动实盘。

### A 型：深度反转 / 彩票型

适用场景：

```text
真实逆风方跌到 20-30c，甚至 10c 以下。
不是强队小回调，而是市场认为它明显落后。
```

默认执行：

```text
20-30c 分层买入
40c / 50c / 60c 分批卖出
保留固定成本金额的彩票仓
最多 2 轮
```

10c 以下归为彩票子类：

```text
小金额买入
3x / 5x 分批卖
保留 20% 彩票仓
不加仓
```

### B 型：强队临时低估

适用场景：

```text
赛前热门 >65%，最好 >75%。
比赛中因短期事件被压到 60-80%。
```

默认执行：

```text
70-80%：优先小网格，质量最高
60-70%：可执行
40-60%：小仓谨慎
跌破40%：B型失效，停止B型加仓，转A型重新判断
```

卖出：

```text
当前买入价 +12c：卖固定成本金额
当前买入价 +22c：卖固定成本金额
98c：卖固定成本金额
保留固定成本金额的彩票仓
```

### C 型：强势碾压 / 理财局（待设计）

适用场景：

```text
优势方持续领先，价格多数在 70-90c。
只在小回撤时接，不追 90c 以上。
```

### D 型：已有持仓救援 / 成本管理（待设计）

适用场景：

```text
用户已有仓位，价格下跌后不想直接止损。
系统先识别旧仓，再给减仓、补仓、止盈和彩票仓方案。
```

## 配置生成命令

示例 A 型：

```bash
python3 tools/grid_config_generator.py \
  --strategy A \
  --market-slug lol-example-game3 \
  --side Dorado \
  --current-price 0.28 \
  --match-budget 100 \
  --cycle-budget 25 \
  --league NACL \
  --market-title "Conviction vs Dorado Gaming - Game 3 Winner" \
  --output trade_config.json
```

示例 B 型：

```bash
python3 tools/grid_config_generator.py \
  --strategy B \
  --market-slug lol-t1-bfx-game2 \
  --side T1 \
  --pre-match-price 0.87 \
  --current-price 0.72 \
  --match-budget 100 \
  --cycle-budget 25 \
  --league LCK \
  --market-title "T1 vs BNK FEARX - Game 2 Winner" \
  --output trade_config.json
```

## 执行桥接

现有执行机器人在：

```text
/Users/ad/Documents/polydata/polymarket_trading_bot_strategy
```

策略库新增执行桥接入口：

```text
tools/grid_plan_runner.py
```

它读取：

```text
market_slug
side
amount_mode
buy_ladders
sell_plan
lottery_cost_basis_usd
max_cycles
stop_new_entry_below
stop_new_entry_above
```

字段约定：

```text
buy_ladders.amount_usd：
每档买入固定美元金额。

sell_plan.sell_cost_basis_usd：
从已成交买入批次里，按该成本金额对应的 shares 计算卖出数量。

lottery_cost_basis_usd：
保留不普通止盈的固定成本份额。
```

dry-run 示例：

```bash
python3 tools/grid_plan_runner.py \
  --plan runtime/trade_config.json \
  --token-id <目标方向 token_id> \
  --dry-run
```

实盘执行前必须确认：

```text
买入方向正确
token_id 正确
买入阶梯金额正确
卖出阶梯价格正确
彩票仓金额正确
```

生成器不会下单，只负责把用户判断转成标准配置。
执行桥接在没有 `--dry-run` 时会真实调用现有机器人下单模块。
