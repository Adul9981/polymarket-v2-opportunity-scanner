# 直播弹幕平台接入方法论（通用 SOP）

> 目的：把"接入一个新直播平台"从一次性摸索变成可复用的标准流程。
> 已用该方法论完成：虎牙（2026-08-18）、SOOP（2026-08-18）、Twitch（2026-08-24）、
> KICK（2026-08-24）。每接入一个新平台，按本文执行并沉淀该平台专属文档。

## 六步法

### 0. 明确目标比赛 / 联赛
先回答"我们要盯什么比赛"，而不是"我们想抓哪个平台"：
1. 查 Polymarket 电竞赛事标签（tag_id=64）全量事件，按我们已登记的白名单
   （config/market_watchlist.json：LoL LCK/LPL/LEC/…，CS2 IEM/BLAST/EWC，Dota2 TI/ESL One）过滤；
2. 从 docs/data/intel/matches.json 看近期已建立情报的比赛；
3. 确定赛程窗口（赛前 1-2 天到赛后），再去找对应直播间。

### 1. 找直播间（官方优先 + 高流量二路）
搜索顺序：
1. **官方频道**（league official / tournament official）——信号最权威、覆盖全；
2. **高流量二路 / co-stream**——弹幕密度通常远高于官方（官方常有慢速/表情模式），
   如 Twitch Caedrel、KICK Gaules；
3. 多语言分流（英文主源 + 必要时韩/法/西/葡语补充）。

每个候选频道记录：slug/房间号、开播状态、流量参考（第三方统计口径）、是否区锁。

### 2. 探测弹幕通道
按成本从低到高：
1. **官方/公开 API 文档**（如 Twitch IRC、Kick v2 channel API）；
2. **页面源码 / JS 资源**搜关键词（pusher/websocket/chatrooms/ws://、app key、cluster）；
3. **浏览器 DevTools** 抓 Network/WS 帧（适用于无文档的网页端协议）；
4. **社区工具**（GitHub/PyPI 搜索 "platform chat downloader/reader"）——先跑通再读实现，
   确认接口细节（鉴权？事件名？数据格式？）；
5. **第三方教程/博客**（scraping 教程常总结当前可用端点与失效情况）。

探测结论必须落到文档：端点 URL、鉴权要求、事件名、消息字段、限速/模式限制、历史回捞能力。

### 3. 写采集器（统一接口）
所有平台采集器保持同一 CLI 约定，便于 run_danmu_session 无差别调用：
```text
--url <直播间URL>       必填（或 --channel <房间号/slug>）
--seconds N            0 = 持续运行直到 Ctrl-C
--out <jsonl路径>      每条弹幕立即追加（中断安全）
--status <json路径>    健康状态（connected/reconnecting/alert/…）
--source <稳定来源id>  写入每条记录（如 kick_eslcs）
--first-message-timeout N  超时无首条弹幕 = 告警（连接假死检测）
```
输出 JSONL 统一字段：platform / channel / source / user / nick / text / ts（ISO UTC）。

### 4. 实测验证
1. 匿名/免鉴权连接是否成功；
2. 连续 60-90 秒采样：弹幕条数/分钟、语言构成、噪音比例（表情 spam）；
3. 记录频道模式限制（emote-only / slow mode / followers-only）对密度的影响；
4. 比较官方流 vs 二路流的密度，确定主源；
5. 断网/重连行为验证（自动重连是否生效）。

### 5. 登记 + 接入监控框架
1. 写进 docs/data/danmu/streamer_registry.json（platform/room_id/live_url/focus/优先级/实测状态）；
2. tools/run_danmu_session.py 的 platform_of() 与采集器映射表注册新平台；
3. 用 run_danmu_session 起一个真实监控会话，确认聚合情报页正常刷新。

### 6. 沉淀 + 词表 + 回归
1. 平台专属文档：knowledge/<PLATFORM>_CAPTURE_RESEARCH.md（频道清单 + 采集方式 + 实测数据）；
2. 主索引 knowledge/DANMU_README.md 登记新平台与工具；
3. 按平台语言补充弹幕词表（灰信号词、队伍/选手昵称），不能直接复用其他语言词表；
4. 平台接口易变（如 Kick Pusher key 轮换、Twitch IRC 匿名昵称规则）——文档中标注
   "失效排查路径"，避免下次从零摸索。

## 通用注意点
```text
1. 鉴权边界：优先匿名/只读公开数据；需要登录的通道记入文档但先不实现。
2. 区锁：部分官方流区域限制（如 Twitch lck_korea）——实测后再定主源。
3. 历史回捞：平台差异大——Twitch VOD 可回捞，Kick 无历史弹幕，SOOP 可回捞。
4. 合规：只读公开聊天、不抓私聊、遵守平台 ToS 与限速。
5. 数据一致性（最高优先级）：弹幕必须与比赛准确对应；无法判定归属哪场比赛时
   记为"待归属"，禁止硬套到某场比赛。
6. 连接假死：无数据 ≠ 无弹幕，必须靠 first-message-timeout / 心跳检测区分，
   禁止直接报"无弹幕/无信号"。
```

## 平台速查表（截至 2026-08-24）
| 平台 | 主要覆盖 | 采集方式 | 实测状态 | 专属文档 |
| --- | --- | --- | --- | --- |
| 虎牙 | LPL/LCK/CS2/Dota2（中文） | WebSocket 逆向（Tars） | ✅ 生产可用 | knowledge/DANMU_CAPTURE_RULES.md |
| SOOP | LCK CL（韩文） | 官方播放器二进制协议 + VOD 回捞 | ✅ 生产可用 | knowledge/SOOP_NOTES.md |
| Twitch | LCK/LEC/LPL/国际赛（英文为主） | 匿名 IRC（零依赖） + chat-downloader VOD | ✅ 已实测 | knowledge/TWITCH_CAPTURE_RESEARCH.md |
| KICK | CS2 IEM/ECL/EWC（英文/葡语） | Pusher WS 匿名直连（无历史回捞） | ✅ 已实测 | knowledge/KICK_CAPTURE_RESEARCH.md |
