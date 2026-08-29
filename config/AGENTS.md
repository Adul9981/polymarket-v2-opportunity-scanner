# config/ 模块规则

职责：策略与风控的"配置即文档"。改配置前先读 docs/framework/PROJECT_FRAMEWORK.md、docs/framework/STRATEGY_PATTERN_LIBRARY.md、docs/task/PROJECT_PROGRESS.md。

## 各文件

- risk_limits.json：硬性风控限额与 autopilot 开关。执行任何动作前先核对；放宽限额必须用户确认，收紧可自主。
- strategy_templates.json：S1/S2 策略模板（兼容旧 A/B 命名）。新策略模板按成熟度登记，未成熟不得进入默认执行。
- discovery_patterns.json：现象标签 P1–P6 配置，任务 2 扫描器使用。
- market_watchlist.json：赛事白名单（LoL/CS2/Dota2），扫描入口过滤用。

要点：

- risk_limits.json 的 market_filters：新开 C 策略仅在 0.68–0.90 区间且 spread ≤ 6c；市场关闭或价格停滞直接跳过。
- strategy_templates.json 默认附带 profit_lock_plan（D2 锁盈）；新增策略模板必须同步定义。
- market_watchlist.json 只放赛事/联赛关键词，扫描标题过滤依赖它；增减条目要同步更新相关文档。
- JSON 不支持注释，说明一律写进 description 字段。

## 约定

- 结构变更必须同步更新 schemas/ 和相关工具。
- 保持 JSON 合法：改动后用 python3 -m json.tool 校验。
- 字段用 snake_case，与 schema 一致。
- autopilot 开关代表"会话级自主执行"授权：默认关闭，只有用户显式开启才生效。
