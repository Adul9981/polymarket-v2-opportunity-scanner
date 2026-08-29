# 虎牙弹幕采集配置要求（线上工具 / 现场工具交接）

> 用途：让线上/现场工具按本项目同一套配置采集虎牙直播弹幕，确保数据格式、健康检查与完整性标准一致。
> 版本：2026-08-27（LCK NS vs BFX 场次实测配置）

## 一、采集目标与方式

- 平台：虎牙（Huya）直播弹幕。
- 用途：LCK / LPL / LEC / CS2 等比赛的多路弹幕采集，按比赛分组落盘，供情报分析。
- 方式：虎牙 WebSocket 弹幕协议（protobuf），每房间一个独立采集进程，持续监听（`--seconds 0`），边抓边写 JSONL，一行一条。
- 注意：**当前只采虎牙**。Twitch 采集已暂停（连接假死问题），SOOP/KICK 按需另配。

## 二、单房间必配参数（每个直播间）

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `--url` | `https://www.huya.com/<房间号>` | 直播间链接 |
| `--source` | 稳定来源标识（如 `huya_we957`） | 写入每条弹幕，用于多路区分 |
| `--out` | `docs/data/danmu/huya/<日期>_<source>.jsonl` | 输出路径，边抓边写 |
| `--status` | `runtime/danmu_sessions/<session>/<source>.status.json` | 健康状态文件（原子更新） |
| `--first-message-timeout` | `120` | 页面开播后 120 秒仍无首条弹幕 → 告警，禁止报"无弹幕" |
| `--seconds` | `0` | 持续采集到手动停止 |

单房间底层脚本示例：

```bash
python3 tools/fetch_huya_danmu.py \
  --url https://www.huya.com/890001 \
  --out docs/data/danmu/huya/2026-08-27_huya_we957.jsonl \
  --status runtime/danmu_sessions/lck_ns_bfx_2026-08-27/huya_we957.status.json \
  --source huya_we957 \
  --first-message-timeout 120
```

## 三、多房间同会话（关键原则）

1. **同一场比赛的所有直播间放同一个 session**（`run_danmu_session.py --session <名>`），由聚合器统一生成 `intel.json`；禁止按房间拆 session。
2. 每个房间独立子进程、独立 JSONL；断线自动重启（10 秒退避）。
3. 并发建议 3-4 路/场（WebSocket 轻量，资源占用极小）；比赛开场前开、赛后停。
4. 新会话先读 `runtime/danmu_sessions/<session>/session.json`，状态仍新鲜且 `running` 时不得重复启动同一房间。

统一入口示例：

```bash
python3 tools/run_danmu_session.py \
  --session lck_ns_bfx_2026-08-27 \
  --title "LCK 季后赛 NS vs BFX（虎牙四路）" \
  --room huya_we957=https://www.huya.com/890001 \
  --room huya_mile=https://www.huya.com/149361 \
  --room huya_remember=https://www.huya.com/528222 \
  --room huya_shuoshuo=https://www.huya.com/323444
```

## 四、当前 LCK 比赛房间配置（2026-08-27，NS vs BFX BO5）

| 直播间 | URL | source | 状态 |
| --- | --- | --- | --- |
| 957（WE957） | `https://www.huya.com/890001` | `huya_we957` | 采集中 |
| 米勒 | `https://www.huya.com/149361` | `huya_mile` | 采集中 |
| Remember（记得） | `https://www.huya.com/528222` | `huya_remember` | 采集中 |
| 硕硕 | `https://www.huya.com/323444` | `huya_shuoshuo` | 采集中 |
| 毛毛 | `https://www.huya.com/149346` | `huya_maomao` | 已暂停（无赛事/噪音源，2026-08-27） |

## 五、联赛默认采集集（完整性依据）

- **LCK**：957(890001) + 硕硕(323444) + 米勒(149361)（毛毛暂停）。
- **CS2**：CSBOY 官方/马西西(123321) + CSBOY-Mo(321123) + BLAST 官方(blast)。
- **LPL**：957 + 硕硕 + 米勒（+毛毛按需）。
- **LCK CL（二队）**：硕硕 + SOOP LCK_CL。

同场比赛必须覆盖所有已登记直播源；离线房间在完整性清单中标注"离线未采"，禁止静默跳过。

## 六、健康检查（线上端必须实现）

每房间 `status.json` 需包含：`page_live / heartbeat_at / last_message_at / message_count / restart_count / warning / error`。

| 现象 | 判定 | 动作 |
| --- | --- | --- |
| 页面未开播 | `offline_waiting` | 继续等待，不得判"无弹幕" |
| 页面开播但 120 秒无首条弹幕 | `live_no_danmaku_alert` | 告警排查 |
| 长时间无新数据 / 心跳停滞 | 连接假死 | 自动重启，记录完整性缺口 |
| 断线重连 | restart_count 增加 | 补记完整性说明 |

弹幕 0 条 / 长时间无新数据 → 先怀疑工具（进程死/断线），告警排查，**禁止直接报"无弹幕/无信号"**。

## 七、数据格式

- 落盘路径：`docs/data/danmu/huya/<日期>_<source>.jsonl`，一行一条 JSON。
- 虎牙字段：`text`（内容）、`nick`（昵称）、`ts`（数值时间戳）、`uid` 等；`source` 由 `--source` 注入。
- 原始层永不改写；分析层使用切片 `docs/data/danmu/slices/<match_id>/`（整场 + 逐局）。

## 八、已知故障与处理

1. 部分房间页把 `profileRoom/lChannelId` 序列化为带引号字符串（如 `uid 1199652774074`），解析须容忍可选引号。
2. 聊天服务器 IP 直播中会轮换，脚本自动重连续写同一 JSONL。
3. 弹幕字段解析统一用 `_ts_value()`（unixtime 优先，字符串时间戳自动解析）。

## 九、交付物（采集端）

每场比赛采集完成后，把以下内容同步回情报端：

- 原始 JSONL（`docs/data/danmu/huya/`）
- 会话健康状态（`runtime/danmu_sessions/<session>/`）
- 聚合情报 JSON（`intel.json`）
- 完整性说明（缺源/断档标注）
