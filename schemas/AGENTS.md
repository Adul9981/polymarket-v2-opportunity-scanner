# schemas/ 模块规则

职责：JSON 产物字段契约。schema 是工具间接口，改动影响生成方、消费方与报告。

## 各文件

- trade_config.schema.json：交易配置字段约定（market_slug、side、buy_ladders、sell_plan、lottery_cost_basis_usd、profit_lock_plan 等）。
- opportunity_candidate.schema.json：任务 2 扫描候选结构（phenomenon_tags、recommended_strategy、route_strategy、strategy_maturity、diagnostics 等）。
- intel_signal.schema.json：主观情报信号契约（knowledge/intel_signals.json 的字段约定：来源/标签/对象/方向/采集时机/市场验证/应验状态/时效）。

要点：

- trade_config 的 amount_mode 固定为 fixed_usd；买入每档含 price + amount_usd，卖出每档含 price + sell_cost_basis_usd。
- 候选 required 字段：event_title、market_title、phenomenon_tags、recommended_strategy、route_strategy、opportunity_score、metrics。
- diagnostics 用于解释空结果：fetched_events → within_time_window → watchlist_matches → candidates 逐层定位。

## 约定

- 改 schema 必须同步更新：tools/ 生成方、runtime/ 消费方、相关报告模板与文档。
- 字段 snake_case；产品层字段与底层字段分开命名。
- 新增字段向后兼容，或先改所有消费方再发布。
- 每次修改后跑相关工具的 dry-run / 校验命令验证。
