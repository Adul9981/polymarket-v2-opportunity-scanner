# KICK 平台弹幕采集调研（2026-08-24 · 已实测）

> 目的：把 KICK 平台上 CS2 赛事直播间的弹幕（chat）接入现有情报体系。
> 背景：ESL 与 KICK 深度合作（2026-04 起）——IEM/EPT 系列在 kick.com/eslcs 英文直播，
> ESL Challenger League（ECL）**独家**在 KICK 播出；EWC 电竞世界杯官方频道也在 KICK。
> 结论：**可采集，匿名直连 Pusher WebSocket，无需鉴权、无需开发者账号**；
> 但 KICK 无历史弹幕回捞接口（仅实时），且 Pusher app key 会不定期轮换。

## 一、为什么 CS2 必须关注 KICK
1. Polymarket 白名单 CS2 赛事 = IEM / BLAST / EWC（config/market_watchlist.json）；
2. IEM 系列（含 IEM Beijing 2026 资格赛）英文官方流在 KICK（kick.com/eslcs），
   Twitch/YouTube 并行但不是唯一；
3. ECL（ESL Challenger League）只在 KICK 播——想盯 ESL 次级赛事，KICK 是唯一弹幕源；
4. 巴西头部 CS 主播 Gaules 在 KICK（kick.com/gaules），国际赛期间高流量葡语二路。

## 二、已验证频道（2026-08-24 API 实测）
| 频道 | 链接 | 覆盖 | 状态 |
| --- | --- | --- | --- |
| ESL CS2 官方 | https://kick.com/eslcs | IEM / EPT / ECL（英文） | ✅ 在线（回放中），chatroom=101198156 |
| Gaules | https://kick.com/gaules | 巴西 CS 二路（葡语） | ✅ 在线（回放中），chatroom=66973867 |
| EWC 官方 | https://kick.com/esportsworldcup | EWC 电竞世界杯 | ✅ 已登记，chatroom=29459281（当前未开播） |
| cs2_maincast | https://kick.com/cs2_maincast | 乌克兰语 CS（BLAST/PGL 等） | ✅ 已登记，chatroom=8258917（当前未开播） |

> 流量参考：Gaules KICK 近 30 天日均约 2000-4000、峰值 2.8-3.7 万（第三方口径，以实测为准）。

## 三、采集方式（已实测 ✅）

### 1. 频道信息（拿 chatroom id）
```text
GET https://kick.com/api/v2/channels/<slug>
（UA 用浏览器 UA；返回 JSON，取 chatroom.id）
```

### 2. 实时弹幕（Pusher WebSocket，匿名直连）
```text
地址：wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=7.4.0&flash=false
订阅：{"event":"pusher:subscribe","data":{"auth":"","channel":"chatrooms.<chatroom_id>.v2"}}
事件：App\Events\ChatMessageEvent
注意：data 是 JSON 字符串，需二次 json.loads；字段含 id/content/sender.username/created_at
```

### 3. 已失效路径（别浪费时间）
```text
GET https://kick.com/api/v2/channels/<slug>/messages?cursor=0
-> 2026-08-24 实测返回 {"message":"Server Error"}（曾可用于翻页回看，现已失效）
```

### 4. Pusher key 轮换（重要！）
```text
Kick 会不定期更换 Pusher app key：
2024 年：eb_1d69c545558f017c307c6f21e1cb0e2d（us2）
2026-04 后：32cbd69e4b950bf97679（us2，当前有效）
连接报 4001 "App key not in this cluster" = key 已轮换。
排查路径：抓 kick.com 页面 JS（assets.kick.com/main/_next/static/chunks/…）
搜索 pusher/app key，或查社区（kick-push-key-checker、kickforge、roundproxies 教程）。
```

## 四、实测数据（2026-08-24 22:30-23:10 CST）
```text
eslcs：回放时段（IEM Cologne Major RERUN）订阅成功，20s 内 0 条
gaules：回放时段（683 观众）60s 采集 8 条；45s 原始监听 5 条事件
说明：回放时段密度低，比赛直播时段密度会显著更高；需在 IEM Beijing 直播时复测。
```

## 五、与现有体系集成
```text
采集器：tools/fetch_kick_danmu.py（统一 CLI：--url/--seconds/--out/--status/--source/--first-message-timeout）
框架：tools/run_danmu_session.py 已注册 kick 平台（platform_of + 采集器映射）
注册表：docs/data/danmu/streamer_registry.json（kick_eslcs / kick_gaules / kick_cs2_maincast / kick_esportsworldcup）
输出：JSONL 统一字段 platform=kick / channel / source / user / nick / text / ts
```

## 六、注意点
```text
1. 无历史回捞：Kick 聊天只有实时 Pusher 通道，断档无法事后补数——断连必须自动重连 + 告警；
2. 弹幕语言：eslcs 英文为主；gaules 葡语为主；词表需按语言补充；
3. 表情：[emote:<id>:<name>] 占比较高，聚合时按表情计数处理，不当作文字信号；
4. 合规：只读公开聊天、不登录账号、不抓私聊；遵守 Kick ToS。
```

> 状态：调研 + 采集链路实测完成（2026-08-24）。IEM Beijing 直播时需复测密度并决定主源。
