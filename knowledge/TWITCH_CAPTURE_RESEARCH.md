# Twitch 英雄联盟弹幕采集调研（2026-08-24 · 已实测）

> 目的：评估把 Twitch 上 LoL 联赛直播间的弹幕（chat）接入现有情报体系。
> 结论：**可行，且比虎牙/SOOP 更简单**——Twitch 有官方 IRC/API/EventSub，
> 无需逆向 WebSocket；另有免鉴权工具可直接读直播+VOD 弹幕。
> 2026-08-24 已实测：匿名 IRC 直连成功，官方频道可匿名 JOIN 读取弹幕，
> 纯 Python 标准库即可采集，零鉴权、零依赖。
> 与现有虎牙（中文）、SOOP（韩文官方流）互补：Twitch 提供英文国际流 + 高流量，
> 多语言/多渠道共振价值高。

## 一、实测结果（2026-08-24 22:30 CST）

### IRC 匿名连接验证 ✅
```text
服务器：irc.chat.twitch.tv:6697（TLS）
匿名昵称：justinfan+随机数字（本次 justinfan74810）
结果：CAP ACK -> 001 Welcome -> 成功 JOIN #lck / #lec
无需 token、无需开发者账号，纯 Python socket+ssl 即可
```

### 频道房间状态（ROOMSTATE 实测）
| 频道 | 模式 | 含义 |
| --- | --- | --- |
| #lck | followers-only=60 | 关注 60 分钟可发言，非 emote-only |
| #lec | emote-only=1; followers-only=10; slow=5; r9k=1 | 表情模式 + 5 秒慢速，发言密度受限 |
| #otplol_ | 无特殊限制 | 法语流，自由发言 |

### 实时密度实测（50 秒样本，北京时间 22:30）
| 频道 | 是否开播 | 弹幕实测 | 备注 |
| --- | --- | --- | --- |
| #lec | ✅ 直播中 | 3 条/分钟 | slow=5 + emote-only 限制；多为表情梗弹幕 |
| #otplol_ | ✅ 直播中 | 1 条/分钟 | 取样时段可能为局间 |
| #lck | ❌ 未开播 | - | LCK 比赛为韩国白天时段 |

> 说明：官方频道普遍开启慢速/表情模式，单用户发言受限，但用户基数大时总量仍可观。
> **高流量来源是 Caedrel 等二路 co-stream**（无慢速模式，弹幕量远高于官方流），详见下节。
> 需在比赛进行中（LCK 白天 KST / LEC 晚间 CET）再测一轮确认峰值密度。

## 二、推荐的直播间（官方 + 高流量二路）

| 频道 | 链接 | 联赛/语种 | 流量参考（第三方统计口径） | 备注 |
| --- | --- | --- | --- | --- |
| LCK（英文主转播） | https://www.twitch.tv/lck | LCK · 英文 | Twitch 近 30 日均值约 1.1 万、峰值 2.2 万；全平台峰值 130 万 | 分析深度标杆；**首选英文韩赛源** |
| LCK Korea | https://www.twitch.tv/lck_korea | LCK · 韩文 | 韩文主力流，观众量大 | 部分区域可能限制，需实测 |
| LEC | https://www.twitch.tv/lec | LEC · 英文 | Twitch 均值约 1-2.7 万、峰值 40 万；全平台峰值 56 万 | 欧洲官方主频道；emote-only+slow 模式 |
| **Caedrel（二路）** | https://www.twitch.tv/caedrel | LCK/LEC/LPL 全赛季二路 · 英文 | 近 30 日均值 5.9 万、峰值 22-60 万，粉丝 153 万 | **全球最大 LoL 二路**，无慢速限制，弹幕密度最高；**首选高流量源** |
| **Kameto（二路）** | https://www.twitch.tv/Kamet0 | LEC/国际赛二路 · 法语 | 峰值 10-14 万，Karmine Corp 主理 | 法语高流量，欧洲第二大 |
| LoL Esports（Riot 国际） | https://www.twitch.tv/lolesports | 国际赛事（S 赛/MSI/First Stand）· 多语 | 国际赛峰值极高 | 分语言子频道多（见下） |
| LPL 国际 | https://www.twitch.tv/lpl_official | LPL · 英文 | 中国联赛英文国际流 | 弹幕英文为主，量级中等 |
| LFL（法国） | https://www.twitch.tv/otplol_ | LFL 法国联赛 | 2026-07 Twitch 电竞频道观看时长第 1（4038 均看、719.5h） | 法语弹幕，欧洲次级人气最高 |
| EMEA Masters | https://www.twitch.tv/emeamasters | 欧洲大师赛 · 英文 | 多语言分流 | 另有西语 LVPes、法语 otplol_ 等 |
| PCS（台港澳/东南亚） | https://www.twitch.tv/lolpacifictw | PCS/国际赛 · 中文 | 均值约 1 万、峰值 16.5 万 | 中文弹幕补充，与虎牙互补 |

> 需要实测确认当前状态：频道是否 live、是否区锁、弹幕密度；国际赛按赛事切换频道
> （如 Worlds 期间 lolesports + 各语言频道），赛前用 lolesports.com 查官方流列表。

## 三、公开采集方式（按推荐排序）

### 1. 官方 IRC 匿名连接（最简单，已验证 ✅，建议首选）
```text
服务器：irc.chat.twitch.tv:6697（TLS）
流程：连接 -> PASS oauth:<token> / NICK <name>（匿名可用 "justinfan12345"）-> JOIN #<频道>
数据：PRIVMSG 行 = 弹幕（tags 带 user-id/display-name/emotes 等）
优点：官方协议、轻量、实时、无额外依赖、零鉴权
缺点：只读直播时弹幕；无历史回放；需自己处理重连/限速
文档：dev.twitch.tv/docs/chat/irc
```

### 2. chat-downloader（免鉴权，最快跑通 + VOD 回捞）
```text
pip install sebastientromp-chat-downloader   # 社区维护版（原版 2025 有 bug 修复）
示例：python -m chat_downloader https://www.twitch.tv/lck --output lck.jsonl
支持：直播弹幕 + 往期 VOD/剪辑弹幕（回捞补数极方便）
优点：零配置、无需开发者账号、直播+回放都行
注意：非官方库，接口可能随 Twitch 变动（有社区维护分支）
```

### 3. EventSub（官方现代方案，适合生产/7×24）
```text
事件：channel.chat.message
接入：Twitch Developer App（client-id/secret）-> 用户 token(channel:read:chat 等)
     -> EventSub WebSocket 订阅 -> 实时推送
优点：官方正式接口、结构化字段（回复/表情/徽章/首次发言）、稳定
缺点：需要开发者账号 + token 管理；subscribe 数量有限制
Python：pyTwitchAPI（支持 Helix + EventSub）；Node：tmi.js / @twurple
```

### 4. 其他公开工具/库
```text
- tmi.js（Node）：老牌 IRC 弹幕库，示例多
- pyTwitchAPI（Python）：Helix + EventSub，适合并入现有 Python 采集链
- Twitch-Chat-Downloader（TheDrHax）：VOD 弹幕下载
- Twitch Archiver / twitch-logger：整场录制+弹幕归档（重流量场景）
```

## 四、与现有体系的差异与注意点

```text
1. 语言/噪音：Twitch 弹幕以英文/韩文/emoji 为主，表情 spam 和 "PogChamp" 类
   梗弹幕占比高——需要沿用现有"聚合+样本"思路，不能把单条弹幕当信号。
2. 多频道分流：Riot 官方同一场常分英文/韩文/西语/法语等多频道，流量被拆散；
   高流量首选 Caedrel（无慢速模式）或官方主源；必要时多源共振，不必全抓。
3. 区锁：lck_korea 等韩文流可能区域限制；英文 lck/lolesports 一般全球可看。
4. 高流量：LCK 决赛等峰值弹幕量极大，单 IRC 连接可能跟不上——先按频道
   实测每分钟条数，超限再考虑多连接或降采样。
5. 时区互补：LCK 白天/下午（KST），LEC 傍晚-凌晨（欧洲时间），与现有
   虎牙夜场、SOOP 官方流形成全天覆盖。
6. VOD 回捞：chat-downloader 可拉往期比赛弹幕——断档补数比虎牙/SOOP 更顺。
7. 合规：只读公开聊天数据、不登录他人账号、不抓私聊；遵守 Twitch ToS 与
   速率限制（IRC 消息限速约 20 条/20s 发送，读取连接按频道带宽）。
8. 慢速模式：官方频道（LEC slow=5、LCK followers-only=60）限制单用户发言频率，
   弹幕总量仍大但"用户密度"低于二路；二路频道（Caedrel 等）无此限制。
9. 词表：英文/韩文弹幕词表需补充（alpha/omega/throw/scripted/rigged 等灰信号词），
   与现有中文词表并行，不能直接复用。
```

## 五、建议的落地路径

```text
1. 试点（已过半）：匿名 IRC 已验证可连；下一步在比赛进行中抓 lck / lec / caedrel
   各 10 分钟，统计弹幕密度/语言/噪音，产出与虎牙/SOOP 同构的 JSONL；
2. 评估：若密度与信息量达标，写 tools/fetch_twitch_danmu.py（IRC 为主、EventSub 可选），
   复用 run_danmu_session 多源监控框架（twitch 平台注册进 streamer_registry）；
3. 上线：并入 VPS 采集清单，Twitch 作为英文/高流量补充源；Caedrel 为高流量首选；
4. 可选：开发 EventSub 版本作为 7×24 生产方案（需用户提供/注册 Twitch Dev App）。
```

> 状态：调研 + IRC 可行性实测完成（2026-08-24）。频道流量为公开第三方统计口径，
> 以实测为准。接入前需在 streamer_registry.json 登记 Twitch 源并跑一次 live 验证。
