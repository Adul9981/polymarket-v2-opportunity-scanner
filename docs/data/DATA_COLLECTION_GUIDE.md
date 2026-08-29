# 电竞小局赔率数据采集指南

最后更新：2026-08-07

状态：已收尾（2026-08-07）。朋友自行爬取数据，本仓库不再对接其纳秒级订单簿日志。本文保留为方法论参考：波动分析以成交价为主、订单簿为辅；打点程序 v1（tools/event_marker.py）保留在仓库，暂不推进 v2（打点 + 记录）。

目标：分析每场比赛、每个小局内双方赔率的变化情况。

需要的数据：一份"价格时间序列 + 盘口快照"，不是订单簿全量流。

## 1. 数据源与分工

| 数据 | 接口 | 用途 | 推荐粒度 |
| --- | --- | --- | --- |
| 比赛与市场元数据 | Gamma `/events` | 比赛列表、子市场、token id、双方名称、开始/结束时间、成交量、是否 closed | 每次扫描拉一次 |
| 价格时间序列 | CLOB `/prices-history?market={token_id}&interval=1d&fidelity=1` | 分析主体：双方每分钟赔率 | 1 分钟 |
| 盘口快照 | CLOB `/book?token_id={token_id}` | best bid / ask、spread、3c 深度（流动性质量） | 比赛进行中每 10-30 秒 |
| 成交价事件（可选） | CLOB WebSocket market channel | 只记录 last trade price 成交价，用于捕捉反弹瞬间 | 事件级，只存成交价 |

## 2. 抓取流程

```text
第一步：拉 Gamma /events，筛出目标比赛，展开子市场。
        拿到每个子市场的 clobTokenIds 和 outcomes（哪一边是哪个队）。
第二步：对每个 token，用 CLOB /prices-history 拉每分钟价格点，这是主体数据。
第三步：比赛进行中，每 10-30 秒拉一次 /book 快照，记录 best bid/ask、spread、深度。
第四步：（可选）订阅 WebSocket，只记录 last trade price，不记录整个盘口变动。
第五步：按小局切分窗口（Game 1 / Game 2 / Game 3），一行一条落盘。
```

落盘格式（CSV 或 JSONL 一行一条）：

```text
timestamp, event_slug, market_slug, outcome, price, best_bid, best_ask, spread, depth3c_usd
```

## 3. 必须遵守的纪律（来自项目复盘沉淀）

```text
1. gamma 的价格字段滞后严重（实测可差 20c+），只用于确认市场存在、
   token id、名称、成交量、closed，绝不用 gamma 价格做分析或决策。
2. 盘口存在 1c/99c 假数据，不要直接信盘口数值，用中间价并做边界过滤。
3. 分析用价格历史（1 分钟粒度）就够；实时盘口只用于流动性检查，
   不需要记录每一次盘口变动。
4. 小局切分注意：BO3/BO5 的第三局起没有独立 Winner 小市场，
   第三局胜负直接体现在整场 Moneyline 市场，别漏掉。
5. 采样不能太粗：10 分钟采样会漏掉 <5c 极值和反弹瞬间
   （08-06 IG vs NIP 实测：NIP <5c 后 10 分钟内拉到 34.5c）。
```

## 4. 不要做的

```text
- 不记录全量订单簿 diff（每个价位每次挂单/撤单/成交）。
  数据量爆炸，对"小局内赔率变化"分析用不上。
- 不用 gamma 快照价格当成交价或分析价。
- 不按 10 分钟采样，会漏极值和反弹瞬间。
```

## 5. 数据校验

```text
- 价格必须在 0-1 之间。
- 时间戳单调递增，无重复、无倒退。
- 双方价格加起来接近 1（如果同市场两边都抓了）。
- 抽几条与 CLOB /prices-history 交叉核对，确认采样没错位。
```

## 6. 打点程序（从纳秒日志里切出比赛窗口）

背景：朋友的日志是全量订单簿、纳秒级、不能改。我们需要的是"每场比赛、每个小局"的数据窗口，所以用打点程序做标记，之后按标记切片。

打点程序做什么：

```text
轮询 Gamma（每 10-30 秒一次），检测目标比赛和子市场的状态变化，打四个点：
event_start   比赛开始（事件 startTime 或第一个子市场激活）
game_start   每个小局开始（Game Winner 子市场 open）
game_end     每个小局结束（Game Winner 子市场 closed）
event_end    整场结算（Match Winner 市场 closed）
```

关键要求：

```text
- 时间戳用 UTC epoch，单位与朋友日志一致（毫秒或纳秒），否则对不上。
- 落盘 runtime/markers/*.jsonl，一行一个点：
  timestamp, event_slug, market_slug, marker_type, price
- 比赛起止点是最低要求；小局窗口（game_start/game_end）是增强，
  因为目标是"每个小局内双方赔率变化"。
```

第一版已实现（tools/event_marker.py）：

```text
单次跑一遍：            python3 tools/event_marker.py
持续盯盘：              python3 tools/event_marker.py --watch --interval 30
只看指定比赛：          python3 tools/event_marker.py --event-slug <slug>
与纳秒日志对齐：        python3 tools/event_marker.py --time-unit ns
输出：                  runtime/markers/YYYY-MM-DD.jsonl + runtime/markers/state.json
离线回放验收：          python3 tools/event_marker.py --event-file tests/fixtures/marker_fixture_events.json
```

切片流程：

```text
1. 读打点文件，按 event_slug 拿到比赛窗口 [event_start, event_end]。
2. 从纳秒日志里过滤出窗口内的数据，比赛级数据就缩小了。
3. 再按 game_start / game_end 细分到每个小局。
4. 每小局输出双方价格统计：min / max / 最低点后反弹 / 50% 穿越次数 / 成交密集度。
```

## 7. 成交价与订单簿的分工

```text
成交价（last trade price）：波动分析主力。
  恐慌砸盘、团战混乱直接反映在成交价上；
  已选比赛流动性充足，成交价足够反映波动，不用靠订单簿猜。

订单簿（朋友日志）：辅助。
  只用于流动性检查（spread、深度）和未来执行层的成交模拟；
  不做发现层波动分析的主力。

回测"给个价格能不能买进"：这是执行层（任务 4/5）的能力，发现层不需要，
第一版不做，避免把事情复杂化。
```

## 8. 要跟朋友确认的两件事

```text
1. 他的日志里有没有"成交"事件（trade），还是只有订单簿变动？
   有成交 -> 直接用他的日志切成交价；
   没有成交 -> 我们自己补一条很轻的成交价流（CLOB last trade / 每分钟价格历史）。
2. 日志的时间戳单位（毫秒还是纳秒）和存储格式（文件还是数据库）？
   切片程序要按这个对接。
```

## 9. 1 分钟赔率快照取数（工具化）

用途：把单场比赛的双方赔率以 1 分钟粒度落盘为可复现素材，供复盘/回测/策略研究使用。

取数逻辑：

```text
1. Gamma /events?slug=<事件slug> -> 事件与市场列表（token id、outcomes、outcomePrices）。
2. 过滤出 Winner / Moneyline 市场（排除 Both Teams / Slay / Inhibitors / Quadra / Penta /
   Odd-Even / Handicap / Total Games 等子市场）。
3. 对每个市场的每个方向 token：
   CLOB /prices-history?market=<TOKEN_ID>&startTs=..&endTs=..&interval=1d&fidelity=1
   -> 1 分钟价格序列；为空则回退 interval=1m&fidelity=10。
4. 落盘 JSONL（一行一条）：timestamp, event_slug, market_slug, side, price；
   同时生成 README（结果、文件清单、关键点位、分辨率说明）。
```

必须注意的坑（实际踩过）：

```text
1. gamma 的 clobTokenIds 和 outcomes 是 JSON 字符串，不是数组，必须先 json.loads。
2. /prices-history 的 market 参数是 TOKEN id（asset id），不是 condition id。
3. interval=1d&fidelity=1 只有对短生命周期市场才返回真正 1 分钟粒度；
   生命周期超过约 2 天的市场会被降采样到 5-13 分钟（README 会记录中位间隔）。
4. 需要 startTs/endTs 限定窗口；默认最近 24 小时，历史比赛需显式传时间戳。
5. SSL 抖动频繁，工具内置重试。
```

工具用法：

```text
python3 tools/fetch_price_snapshot.py --slug lol-blg-tes-2026-08-07
python3 tools/fetch_price_snapshot.py --url <polymarket链接>
python3 tools/fetch_price_snapshot.py --slug <slug> --start-ts <ts> --end-ts <ts>
```

输出目录：`docs/data/snapshots/<slug>/`。

现有快照：

```text
2026-08-06_lol-we-al        WE vs AL（G1/G2/Moneyline）
2026-08-07_lol-hle-drxc     HLE Challengers vs DRX Challengers
2026-08-07_lol-we-tt        WE vs TT（G1/Moneyline 双方）
2026-08-07_lol-fox1-bro2    FOX(BFX) vs BRO（G1/G2/Moneyline 双方）
2026-08-07_lol-blg-tes      BLG vs TES（G1/G2/Moneyline 双方）
```
