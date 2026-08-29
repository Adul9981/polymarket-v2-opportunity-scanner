# 打点程序 event_marker v1 使用说明

用途：记录比赛和小局的时间窗口（比赛开始 / 小局开始 / 小局结束 / 整场结算），输出带 UTC 时间戳的打点文件，供按窗口切分历史日志数据。

## 文件结构

```text
├── README.md                        # 本说明
├── tools/
│   ├── event_marker.py              # 打点程序
│   └── market_scanner.py            # 依赖：抓取赛事 + 白名单过滤
├── config/
│   └── market_watchlist.json        # 白名单关键词（可自行修改）
└── tests/
    └── fixtures/
        └── marker_fixture_events.json  # 离线测试数据
```

## 依赖

```text
Python 3.8+，无需第三方库。
需要网络能访问 Polymarket 公共接口（gamma-api.polymarket.com / clob.polymarket.com）。
```

## 运行

```bash
# 跑一遍（先试这个）
python3 tools/event_marker.py

# 持续盯盘，每 30 秒查一次
python3 tools/event_marker.py --watch --interval 30

# 只看指定比赛（多个用逗号分隔）
python3 tools/event_marker.py --event-slug <event_slug>

# 时间戳用纳秒（对齐纳秒级日志）
python3 tools/event_marker.py --time-unit ns

# 离线自测（不用网络）
python3 tools/event_marker.py --event-file tests/fixtures/marker_fixture_events.json
```

## 输出

```text
runtime/markers/YYYY-MM-DD.jsonl   一行一个点：
  {"ts": ..., "ts_iso": "...", "event_slug": "...", "market_slug": "...",
   "market_title": "...", "marker_type": "...", "game_index": ...}
runtime/markers/state.json         去重状态（重启不重复打点）
```

## marker_type 说明

```text
event_start   比赛开始
game_start    小局开始
game_end      小局结束
event_end     整场结算
```

## 注意事项

```text
- 时间戳为 UTC；与日志对齐时使用同一时基和单位（--time-unit ms/s/ns）。
- 只读公开数据，不下单、不读私钥。
- 白名单关键词在 config/market_watchlist.json 里修改。
```
