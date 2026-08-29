# tools/ 模块规则

职责：项目全部 Python 工具，按三条链组织。工具之间不跨链调用，改动前先读 docs/framework/PROJECT_FRAMEWORK.md 与对应模块规则。

## 三条链

执行准备链（不下单，可放心运行）

- grid_config_generator.py：生成 trade_config JSON。
- prepare_grid_trade.py：URL→解析→计划→五类启动器（任务 1 胶水层）。
- prematch_predictor.py：V2-S2 赛前形态预测 + 预挂单计划（预测层：赔率/形态气候/
  队伍画像/情报/联赛信誉 -> 策略模板 -> dry-run 计划，不下单）。
- create_trade_launcher.py / create_trade_review.py / append_knowledge_review.py：启动器、复盘文件、知识库追加。

实盘执行链（真实资金操作，最高关注）

- grid_plan_runner.py：挂单 + 成交后止盈，唯一真实下单入口。
- cancel_grid_orders.py：撤未成交挂单（不卖持仓）。
- check_grid_status.py / grid_status_summary.py：只读状态检查与中文摘要。
- bar_monitor_runner.py：1 分钟 bar 监控 + 策略状态引擎（执行层，只监控）。
  每 60 秒拉窄窗口 1 分钟 bar + 实时中间价，输出 resting 限价单动作队列；
  默认 dry-run，不下单；--execute 走 grid_plan_runner --dry-run，--execute-live 为真实挂单
  （需待确认计划 + autopilot 开启）；--autopilot 为 V2 信号->计划->待确认闭环；
  成交后自动拉起 monitor 配止盈 + 交易所级止损单；内置 D3 跟踪止损状态机；
  动作带 classify_pattern 形态标签。定义见 docs/task/V2_EXECUTION_LOOP.md。
- 纪律：先 dry-run；方向无歧义；已有状态文件时不重复买入。

发现回测链（永远只读）

- market_scanner.py / summarize_scan_diagnostics.py：任务 2 机会扫描与诊断。
- polymarket_strategy_backtester.py：历史价格回测。
- build_backtest_visual.py：回测可视化。
- event_marker.py：打点程序，记录比赛/小局起止窗口（只读公开数据）。已收尾，保留参考，暂不推进 v2。
- fetch_price_snapshot.py：1 分钟赔率快照取数（只读公开数据），输出 docs/data/snapshots/<slug>/。
- classify_pattern.py：形态分类（启发式 v1.1，只读），输入快照/价格序列，输出 A/B/C 形态标签 + 频率统计。
- counterfactual_review.py：反事实复盘（只读），给定快照+交易参数，算"若按 D2/D3 规则执行"的结果 vs 实际。
- 不下单、不读私钥、不调用执行链。

情报采集链（主观情报库，与执行链完全隔离）

- record_intel_signal.py：信号录入/赛后回填（写 knowledge/intel_signals.json，只录入、不下单）。
- intel_stats.py：按来源 x 标签的可信度统计（只读，--json 供 TASK6 UI 后台）。
- fetch_series_comments.py：series 评论批量抓取/按比赛窗口切片（只读，
  规则 knowledge/COMMENT_ANALYSIS_RULES.md；输出 docs/data/snapshots/comments_batch/ 与
  docs/data/snapshots/<slug>/comments/；不读私钥、不下单）。
- comment_intel.py：赛前/赛中评论区情报提示（只读，接入 task2_pipeline --watch；
  读取 runtime/watchlist_events.json，输出 runtime/comment_intel.json +
  reports/comment_intel_<date>.md；关键词命中仅作辅助参考，不构成信号）。
- fetch_huya_danmu.py：虎牙直播间实时弹幕抓取（轻量，复用 real-url 的 Tars/WebSocket 实现；
  依赖 aiohttp/requests/pycrptodome，运行需 PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python）。
- danmu_intel.py：弹幕 JSONL -> 交易情报提炼（队伍/选手情绪、盘口、局势、灰信号、密度峰值，
  输出 runtime/danmu_intel.json；只读）。
- danmu_report.py：弹幕 JSONL -> SAP/Apple 风格 HTML 简报（reports/intel_danmu_*.html；只读）。
- 字段契约：schemas/intel_signal.schema.json；设计文档：docs/task/INTEL_SIGNAL_LIBRARY_PLAN.md。
- 纪律：信号只作边际信息叠加，不改变止损/止盈；短摘录入库，不存完整转录稿。

套利研究链（只读，S-F1 完整集套利）

- forensics_arb_scanner.py：两级只读扫描（标记价粗筛 Σp + 订单簿 ask 精筛），
  只扫描 48 小时内结算的负风险组，输出 runtime/forensics/scan_*.jsonl 与
  每日报告；不创建订单。配置 config/forensics_arb.json；字段契约 schemas/arb_cycle.schema.json。
- 后续：forensics_arb_backtester.py（回测）、forensics_arb_engine.py（状态机+dry-run 执行）。
- 纪律：判定只用订单簿可成交成本；实盘前必须回测为正并经用户授权。

交易者拆解数据采集链（只读，mapread 集成，2026-08-27 登记）

- mapread_wallet_tracker.py：mapread.gg 公开 JSON 接口（market-flow 看板 /
  wallet-activity 钱包级逐笔 / wallet-profiles 180 天画像）的封装采集器，
  内置我方 forensics 名单（WATCHLIST）盯梢；原始 JSON 只增不改地落盘
  docs/forensics/data/mapread/；子命令 board / market / watch。
  底层数据源 = Polymarket Goldsky 链上成交，与 forensics 同源可交叉验证。
  纪律：只读公开数据，不读私钥、不下单；接口无鉴权但需限速（watch 默认 0.25s 间隔）。

自动化流水线（编排层，只调用命令行接口，不跨链 import）

- task2_pipeline.py：扫描 -> 候选动作队列 -> bar 盯盘接线；--watch 定时循环；
  默认 dry-run，唯一下单入口仍是 grid_plan_runner.py。

## 约定

- 工具默认硬编码 ROOT=/Users/ad/Documents/polymarket，新工具沿用此风格。
- 新增工具先明确归属链并写清 docstring，再考虑是否更新根 AGENTS.md。
- token 解析不唯一时必须要求用户指定 --token-id，禁止猜测。
- 不修改 /Users/ad/Documents/polydata/polymarket_trading_bot_strategy，只 import 其 config.py / trading.py / market_resolver.py。
