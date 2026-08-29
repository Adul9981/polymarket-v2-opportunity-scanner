# SOOP（前 AfreecaTV）弹幕抓取说明

最后更新：2026-08-18

SOOP = sooplive.com，韩国直播平台，LCK_CL 频道（BJ id `afchall`）直播
LCK 二线联赛 LCK CL。弹幕为韩文，需在分析阶段做翻译与词表映射。

## 两条链路（均已验证可用）

### 1. 实时弹幕（WebSocket 二进制协议）

工具：`tools/fetch_soop_danmu.py`

流程：
1. `POST https://live.sooplive.com/afreeca/player_live_api.php?bjid=<bj>`
   （表单：bid/bno/type=LIVE/player_type=html5/...）→ 返回 `CHANNEL`：
   `CHIP`（聊天 IP，如 110.10.76.71）、`CHPT`（端口，wss 用 +1）、
   `CHATNO`（频道号）、`BSTATUS`（BROADING=直播中）。
2. 聊天域名：IP 四位转十六进制（110.10.76.71 → 6E0A4C47），
   `wss://chat-<HEX>.sooplive.com:<CHPT+1>/Websocket/<bj>`，
   WebSocket 子协议 `chat`。
3. 二进制包：头 50 字节 = `0x1D 0x09` + 服务码(4位ASCII) + 长度(6位ASCII)
   + `00` + UUID(36)；体 = 字段用 `0x0C` 分隔（首尾各一个）。
   - SVC_LOGIN(1)：`0x0C` ticket `0x0C` 昵称 `0x0C` 标志(游客=16) `0x0C`
   - 收到 LOGIN 应答后发 SVC_JOINCH(2)：
     `0x0C` 频道号 `0x0C` 粉丝券 `0x0C` 0 `0x0C` 扩展串 `0x0C` 日志串 `0x0C`
     （官方客户端带 11 个字段；漏字段会收到 ret=3 协议错误）
   - SVC_CHATMESG(5) 字段：`[0]`消息 `[1]`用户ID `[5]`昵称
   - 每 60 秒发 SVC_KEEPALIVE(0)。
4. 坑：
   - 聊天服务器 IP 会在直播中轮换（每次请求可能不同），连接被踢后需
     重新取 room info 再连（工具已自动重连）。
   - 仅能收到"进频道之后"的实时弹幕；比赛开始前的弹幕拿不到（靠 VOD 回捞）。

### 2. 回放历史弹幕（VOD 分片接口）

工具：`tools/fetch_soop_vod_chat.py`

流程：
1. 回放列表：`GET https://bjapi.afreecatv.com/api/<bj>/vods/all?page=&per_page=60`
   → 每条含 `title_no`（= 直播间 broad_no）、`ucc.thumb` 里的
   `rowKey=20260811_3F2039B0_296274595_2_r`、`ucc.total_file_duration`（毫秒）。
2. 聊天 rowKey = 缩略图 rowKey 去掉 `_r` 换成 `_c`。
3. 分片拉取：`GET https://videoimg.sooplive.com/php/ChatLoadSplit.php
   ?rowKey=<key>_c&startTime=<秒>`，每片覆盖约 300 秒，从 0 翻页到总时长。
   返回 XML `<chat>`：`<m>`消息 `<u>`用户ID `<n>`昵称 `<t>`VOD 内秒数。
4. 已验证：NS vs DK | LCK CL ROUND 4 回放（title_no=204038307）第 1 小时
   拉到 1109 条、124 个活跃用户。
5. 坑：
   - VOD 只在整场直播结束后生成；直播中调 stbbs/video_info 会 404。
   - 当前场（如 296450537 DNS vs NS）等结束后用同工具回捞全量，再按
     VOD 时间切片（第一局 ≈ 开场后 40–60 分钟）。
   - SOOP CDN 偶发 TLS 抖动，请求已加自动重试。

## 与虎牙的差异

| 维度 | 虎牙 | SOOP |
| --- | --- | --- |
| 语言 | 中文 | 韩文（需翻译） |
| 实时抓取 | Tars/WebSocket（real-url 库） | 自研二进制聊天协议 |
| 历史弹幕 | 无 VOD 聊天接口（仅录播视频） | 有 ChatLoadSplit 全量回捞 |
| 覆盖赛事 | LPL/LEC 等中文解说 | LCK CL（LCK 二线）等韩语频道 |

## 已建词表方向（韩文）

NS=농심、DK=디앤케이(DK)、DNS=디엔에스；选手常见昵称（세텝/새텝=赛特、
카이사=卡莎、클레드=克烈、렐=蕾尔、나피리=娜菲丽、자르반=嘉文）等，持续扩充。
