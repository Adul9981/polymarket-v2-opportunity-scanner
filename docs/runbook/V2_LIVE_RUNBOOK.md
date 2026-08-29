# V2 实盘运行手册（真实资金）

最后更新：2026-08-09

用途：把 V2 一分钟信号捕捉闭环从 dry-run 切换到真实资金执行。**先读完再动手。**

## 0. 前提（缺一不可）

```text
1. config/risk_limits.json 的 autopilot.enabled 已由你显式改为 true。
   （红线：autopilot 必须用户在本会话显式开启，助手不代开。）
2. polydata 钱包配置有效、余额充足（真实挂单前有余额预检）。
3. 网络可访问 Polymarket。
4. 目标比赛是真实进行中的市场（预挂盘会被流动性闸拦截，属正常）。
```

## 1. 两步流程

第一步：盯盘 + 信号 + 生成计划（**dry-run，不花钱**）

```bash
python3 tools/bar_monitor_runner.py \
  --slug <event-slug> --outcome <队名> \
  --strategy B_FAVORITE_DIP --autopilot --watch
```

看到输出"待确认计划已生成"，先核对 dry-run 计划：

```text
买入档位（价格 / 金额）
止盈档（0.62 / 0.75 / 0.88）
止损单（0.35 (stop)）
彩票仓
```

第二步：确认后真实执行（**真正花 USDC**）

```bash
# 交互确认版（推荐）：会弹出"输入 yes 确认"
python3 tools/bar_monitor_runner.py \
  --slug <event-slug> --outcome <队名> \
  --strategy B_FAVORITE_DIP --execute-live

# 或启动器（等价命令）
./runtime/run_v2_live.command <event-slug> --outcome <队名> --strategy B_FAVORITE_DIP
```

执行成功后：

```text
- 挂出 resting 买单；
- 自动拉起 monitor（后台进程），成交后自动配止盈 + 止损卖单；
- monitor pid 记录在 runtime/bar_monitor_state/<slug>.json。
```

## 2. 盘中管理

```text
查状态：  python3 tools/check_grid_status.py --name <label>
撤单：    python3 tools/cancel_grid_orders.py ...
停止盯盘：关掉 --watch 进程即可（已挂单不受影响，monitor 继续跑）。
```

## 3. 必须遵守

```text
- 真实挂单前必须已经看过 dry-run 计划。
- 绝不市价追；只挂 resting 限价单。
- 超过风控限额自动停：单市场 $80、单日 $200、并发 3。
- 成交后复盘写 knowledge/reviews/。
- 异常（重复单 / 订单状态不明 / 数据停滞 / spread 过大）自动暂停并询问。
```

## 4. 验收顺序（不要跳级）

```text
第一步：真实比赛上 dry-run 全链路（信号 -> 计划 -> 待确认），不碰钱。
第二步：小额实盘 1-3 笔，验证挂单 -> 成交 -> 止盈/止损 -> 复盘闭环。
第三步：连续 5-10 笔样本后，再评估放开额度或升级。
```
