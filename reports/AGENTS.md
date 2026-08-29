# reports/ 模块规则

职责：回测、扫描、诊断、风控教训报告。命名带赛事与日期，让结论可被后续决策直接引用。

## 命名

- 回测：<赛事>_<策略>_backtest[_fullwindow|_emotional][_YYYY-MM-DD].md/.json，md 与 json 成对。
- 扫描：opportunity_scan[_live_task2]_YYYY-MM-DD.md。
- 诊断：diag_<联赛>_scan_YYYY-MM-DD.md。
- 总结/教训：strategy_*_YYYY-MM-DD.md、risk_management_lessons_*.md。
- 弹幕情报：intel_danmu_<赛事>_<阶段>_YYYY-MM-DD.html
  （如 intel_danmu_KC-GX_full_2026-08-18.html；阶段：live 实时监控 / G1 局间小结 /
  full 整场复盘）；弹幕报告索引页 reports/intel_danmu_index.html 自动维护。

## 内容要求

- 回测：结论与形态分开头，再给目标方向、价格点、买入/卖出计划、彩票仓、逐笔结果表。
- 扫描：赛事时间线 → 候选机会 → 扫描诊断块。
- 诊断块用于定位问题：fetched_events / within_time_window / watchlist_matches / candidates 逐层看。
- 结论优先回答"是否符合策略形态、能否路由到 S1/S2"，数据只是支撑。
- 日期统一用 YYYY-MM-DD；时间数据标注 UTC，避免歧义。
- 扫描报告区分 live / offline 模式，命名用 _live_task2 / _test 标明，防止混读。
- json 报告是机器可读版本，md 是给人看的版本，两者结论必须一致。
- 弹幕报告：SAP/Apple 风格 HTML；只展示聚合结论与代表性弹幕（不裸展示弹幕流）；
  灰信号（假赛/剧本/卡盘质疑）标注"观众质疑，非结论"；比赛结果/选手/盘口
  为弹幕推断时写"待官方确认"；报告可溯源到 docs/data/danmu/ 的 JSONL 原文。

## 约定

- 报告是知识沉淀不是流水账；每份都能被下次决策引用。
- 不把 runtime 产物内容原样贴进报告，只保留结论与关键数字。
