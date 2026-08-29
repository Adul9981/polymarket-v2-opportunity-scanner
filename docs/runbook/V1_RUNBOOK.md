# 预测市场网格交易 V1 运行手册

最后更新：2026-08-03

## 1. V1 定位

V1 是交易执行专用版本。

目标：

```text
用户用很少输入给出市场和想法。
系统负责解析市场、选择子市场、生成固定金额网格、执行挂单、monitor-only 管理、关闭订单和复盘。
```

V1 不负责复杂产品讨论。
复杂策略演进、任务 2/3/4/5 继续留在主项目会话讨论。

## 2. 新会话使用方式

新开“交易执行专用会话”后，第一条消息可以贴：

```text
你是我的 Polymarket 网格交易 V1 执行助手。

只负责 V1 执行，不展开产品战略讨论。

工作目录：
/Users/ad/Documents/polymarket

执行项目：
/Users/ad/Documents/polydata/polymarket_trading_bot_strategy

核心文件：
- docs/runbook/V1_RUNBOOK.md
- docs/runbook/V1_1_TRADE_COMMAND_GUIDE.md
- docs/runbook/V1_1_PROFIT_LOCK.md
- docs/task/PROJECT_PROGRESS.md
- docs/framework/STRATEGY_PATTERN_LIBRARY.md
- config/risk_limits.json
- tools/prepare_grid_trade.py
- tools/grid_plan_runner.py
- tools/grid_status_summary.py
- tools/cancel_grid_orders.py
- tools/create_trade_review.py
- tools/append_knowledge_review.py
- tools/check_open_orders.py（订单真实性核验，查询失败会大声报错）
- knowledge/（交易复盘知识库）

我的输入通常很短：
市场链接 + Game/Map/整场 + 想买方向 + 策略/自然语言判断。

你需要：
1. 解析 Polymarket 链接。
2. 定位对应 Game/Map/整场 Winner 市场。
3. 匹配我说的方向；如果简称无法唯一匹配，使用市场正式 outcome 名称重试。
4. 按 V1 策略生成计划。
5. 实盘执行时使用本地 .command 入口。
6. 首次执行后切换 monitor-only。
7. 不重复买入。
8. 成交后自动挂止盈。
9. D2 自动锁盈优先：低位买对后，60c 以上开始回收，75c 以上锁定大部分，80c 以上只留小彩票仓。
10. 关闭订单只撤未成交挂单，不卖已成交持仓。
11. 交易结束后生成复盘。
12. 每笔挂单后必须验证订单真实存在（INVALID=未挂上）；open-orders 为空不代表无挂单，
    用 tools/check_open_orders.py 复核（详见 docs/runbook/V1_1_TRADE_COMMAND_GUIDE.md 第 8 节）。
```

## 3. 用户输入格式

推荐输入：

```text
链接：
目标：Game 1 / Game 2 / Map 1 / 整场
方向：队伍名或简称
策略：A / B / C，或一句自然语言
金额：可选，不填按默认
```

自然语言也可以：

```text
这场第二小局我想买 DK，策略A。
这场整局买 BNK，策略B。
这个 Game 2 像理财局，少量试一下。
```

## 4. 当前策略范围

```text
A：深度反转 / 彩票型
状态：V1 可执行

B：强队临时低估 / 热门回撤
状态：V1 可执行

C：强势碾压 / 理财局
状态：实验性小额可执行，需要 --allow-experimental

D：已有持仓救援 / 成本管理
状态：V1 只建议，不自动执行
```

## 5. 赛前小底仓规则

用户倾向：

```text
赛前少量买一点看好的方向。
赛中如果出现好价格，再用更多资金做网格。
```

V1 处理方式：

```text
赛前小底仓不是 A/B/C/D 单独策略，而是执行层的 pre-position 模块。
```

建议规则：

```text
只买看好方向。
金额小于赛中网格主仓。
默认 5-10 USDC。
只用于热门方或用户强主观方向。
买入后不要急着满仓。
赛中下跌后再按 A/B/C 判断是否加仓。
```

风险：

```text
赛前小底仓可能占用可用余额，导致赛中网格第二档挂不上。
如果账户可用余额不足，优先保证已有仓位止盈卖单，不强行加买单。
```

V1 暂不自动开赛前底仓，除非用户明确说：

```text
赛前小买一点
小底仓
先买一点
```

## 6. 默认资金

```text
A：默认 25 USDC 一轮。
B：默认 25 USDC 一轮。
C：默认 15 USDC 实验小额。
赛前小底仓：默认 5-10 USDC。
单市场最大默认 30 USDC。
```

如果余额不足：

```text
成功挂出的订单必须保存状态。
后续失败不应导致前面订单丢失。
进入 monitor-only 管理已成功订单。
不要重复买入。
```

## 7. 标准执行流程

```text
1. prepare：
   tools/prepare_grid_trade.py 生成计划和入口。

2. run：
   打开 runtime/run_*.command 做首次执行。

3. monitor：
   首次执行后使用 runtime/monitor_*.command 接管。

4. status：
   使用 runtime/status_*.command 或 tools/grid_status_summary.py 查看状态。

5. close：
   比赛结束或用户要求退出时，使用 runtime/close_*.command。
   close 只撤未成交挂单，不卖已成交持仓。

6. review：
   使用 runtime/review_*.command 生成复盘。
```

## 8. V1.1 自动锁盈优先级

V1.1 新增最高优先级：

```text
已经买对并出现浮盈时，系统优先保护利润。
```

执行原则：

```text
低位买入后，60c 以上开始回收。
75c 以上必须锁定大部分。
80c 以上只允许小彩票仓。
剩余仓位如果还能明显影响心态，就不是彩票仓。
```

交易计划必须包含：

```text
profit_lock_plan
```

状态摘要必须关注：

```text
剩余仓位成本
剩余仓位当前市值
已锁定利润
如果当前归零会损失多少市值
是否超过彩票仓上限
```

## 9. 当前进行中的样本

### 样本 1：GEN vs HLE Game 2，C 型理财局

```text
状态文件：
/Users/ad/Documents/polydata/polymarket_trading_bot_strategy/.runtime/gen_hle_game2_c_finance_pilot.json

计划文件：
/Users/ad/Documents/polymarket/runtime/gen_hle_game2_c_finance_pilot.json

状态：
已成交一档买入。
已挂 84c 止盈卖单。
monitor-only 正在运行。
```

### 样本 2：BRO vs FOXY 整场，B 型热门回撤

```text
状态文件：
/Users/ad/Documents/polydata/polymarket_trading_bot_strategy/.runtime/bro_foxy_series_strategy_b.json

计划文件：
/Users/ad/Documents/polymarket/runtime/bro_foxy_series_strategy_b.json

状态：
第一档买入已成交。
75c / 85c 止盈卖单已挂出。
monitor-only 正在运行。
```

### 样本 3：DNSC vs DKC Game 1，A 型低位反转

```text
状态文件：
/Users/ad/Documents/polydata/polymarket_trading_bot_strategy/.runtime/dnsc_dkc_game1_dk_strategy_a.json

计划文件：
/Users/ad/Documents/polymarket/runtime/dnsc_dkc_game1_dk_strategy_a.json

状态：
30c 买单已挂出，等待成交。
monitor-only 正在运行。
```

## 10. 任务 1 验收口径

任务 1 完成前，还需要验证：

```text
1. 至少 3 个真实样本有状态文件和日志。
2. 至少 1 个样本完成关闭订单。
3. 至少 1 个样本生成复盘。
4. monitor-only 不重复买入。
5. 成交后止盈卖单能挂出并写入状态文件。
```

满足后可以进入任务 2：

```text
自动扫描比赛列表，给出机会排名。
```

## 11. 复盘知识库闭环

每笔交易结束后，把结果写回知识库：

```text
python3 tools/append_knowledge_review.py \
  --state-file <状态文件路径> \
  --result "<最终结果>" \
  --lessons "<教训要点>"
```

复盘文件自动写入 `knowledge/reviews/` 并更新 `reviews/index.md`。

交易前先看：

```text
knowledge/README.md
knowledge/reviews/index.md
```
