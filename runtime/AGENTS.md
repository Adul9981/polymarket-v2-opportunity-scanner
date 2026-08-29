# runtime/ 模块规则

职责：每笔交易的运行时产物：状态 JSON、五类 .command 启动器、日志。除 run_task2_live_scan.command 外均被 gitignore，不入库。

## 五类启动器

- run_*.command：首次执行（挂单 + 进入监控）。
- monitor_*.command：monitor-only 接管，不新增买单。
- status_*.command：只读状态摘要。
- close_*.command：撤未成交挂单（不卖持仓）。
- review_*.command：生成复盘文件。
- 例外保留入库：run_task2_live_scan.command（V2 只读扫描入口）。

## 命名与约定

- 文件名用 <比赛>_<策略> 前缀，同一场比赛共用前缀。
- 状态 JSON 是防重复下单的依据：每成功一档买单立即保存；已有状态文件时不重复买入。
- 日志写 runtime/logs/，与状态文件同名。
- 手动编辑状态 JSON 属于高风险操作：必须用户明确要求，并先备份原文件。
- 新增交易流程时，五类启动器要成组创建，不要只建其中一部分。
- 重启或新会话先读状态文件再行动；状态文件路径即交易标识，改名等于新建交易。
- 启动器由 tools/prepare_grid_trade.py / create_trade_launcher.py 自动生成，不要手写。

## 比赛管理目录

- runtime/match_management/：每场比赛一张状态卡（<slug>.json），轻量记录系列赛进度
  （进行到第几局、比分、是否结束）与挂单状态标识（没给机会 / 计划取消 / 已挂单 / 已成交等）。
- 工具：tools/match_manager.py（init / record / series / show / list）；一律用工具读写，不手改 JSON。
- 字段与枚举约定见 runtime/match_management/AGENTS.md。
