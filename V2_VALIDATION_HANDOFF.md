# V2 验证交接说明

最后更新：2026-08-04

## 1. 当前结论

V2 当前状态：

```text
待验收。
```

不是策略未完成，而是 live 网络验证还没有最终跑通。

已经完成：

```text
任务 2 自动扫描器。
赛事 watchlist。
P/S 分层输出。
候选 JSON schema。
Markdown 扫描报告。
空结果诊断。
一键 live 只读扫描入口。
```

待朋友验证：

```text
在网络稳定的环境下，重新跑一次 live 只读扫描。
确认最近两天赛事能否进入 watchlist。
确认候选是否能输出 P1/P2/P3/P5 -> S1/S2。
```

## 2. 重要安全边界

V2 只做机会发现：

```text
不下单。
不读取私钥。
不调用交易执行脚本。
不创建订单。
只读取 Polymarket 公开赛事、价格历史和盘口数据。
```

本次验证不涉及实盘交易。

## 3. 如何运行

在项目目录：

```text
/Users/ad/Documents/polymarket
```

运行：

```bash
./runtime/run_task2_live_scan.command
```

如果不能直接运行，也可以执行：

```bash
python3 tools/market_scanner.py \
  --live \
  --live-limit 100 \
  --live-pages 8 \
  --skip-book \
  --output-json runtime/opportunity_candidates_live_task2.json \
  --output-events runtime/watchlist_events_live_task2.json \
  --output-report reports/opportunity_scan_live_task2_2026-08-04.md

python3 tools/summarize_scan_diagnostics.py \
  --candidates runtime/opportunity_candidates_live_task2.json \
  --events runtime/watchlist_events_live_task2.json
```

## 4. 需要回传的文件

请把以下三个文件的结果回传：

```text
runtime/opportunity_candidates_live_task2.json
runtime/watchlist_events_live_task2.json
reports/opportunity_scan_live_task2_2026-08-04.md
```

如果命令行有报错，也请回传报错文本。

## 5. 验证重点

优先看报告里的“扫描诊断”：

```text
抓取事件
标题过滤后
时间窗口内
Watchlist 匹配
最终赛事
候选机会
事件样本
```

判断逻辑：

```text
如果 fetched_events = 0：
说明 Polymarket 公开事件源没有返回数据，可能是网络或 API 访问问题。

如果 fetched_events > 0，但 within_time_window = 0：
说明事件源返回了数据，但最近两天赛事没有进来，需要继续调整事件抓取方式。

如果 within_time_window > 0，但 watchlist_matches = 0：
说明赛事有了，但 watchlist 关键词需要调整。

如果 watchlist_matches > 0，但 candidates = 0：
说明赛事进池了，但当前价格形态没有触发 S1/S2 候选，这可以接受。

如果 candidates > 0：
重点检查候选是否有 phenomenon_tags、recommended_strategy、strategy_maturity。
```

## 6. 当前已知问题与修复

已发现问题：

```text
Gamma active events 按 startDate 正序返回时，会先返回大量 2024/2025 长期 active 事件。
这导致最近两天的电竞赛事没有进入扫描窗口。
```

已修复：

```text
扫描器已改成 startDate 正序 + 倒序双向抓取，并去重。
```

朋友验证时，重点确认这个修复是否让：

```text
within_time_window
watchlist_matches
final_events
```

恢复到合理数量。

## 7. V2 验收标准

V2 可以标记为完成，需要满足：

```text
1. live scan 能成功生成 runtime/opportunity_candidates_live_task2.json。
2. live scan 能成功生成 runtime/watchlist_events_live_task2.json。
3. 报告中出现扫描诊断块。
4. 若有目标赛事，能进入 watchlist_events。
5. 若有候选，候选中包含：
   phenomenon_tags
   recommended_strategy
   recommended_strategy_detail
   route_strategy
   strategy_maturity
6. 全流程不触发实盘下单。
```

当前 V2 尚未满足第 4 条，因为我的网络环境下最近一次 live scan 仍未抓到时间窗口内赛事。

因此当前状态是：

```text
V2 待验收，可以交给网络更稳定的朋友验证。
```

