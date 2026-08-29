# 官方 / 公开数据源清单（阵容 · 结果 · 比分）

> 定位：弹幕是"情绪与共识层"，阵容/结果/比分是"事实层"——事实层必须走官方或权威公开源。
> 本清单 2026-08-27 实测验证（NS vs BFX G1/G2 官方阵容双源一致），供本地与线上情报库复用。

## 0. 核心原则

1. **选手×英雄对照 = 只信官方**：弹幕提及/讨论 ≠ 实际选人（2026-08-27 教训：弹幕"狐狸"实为 BFX VicLa，曾被误配给 Scout）。
2. **结果判定优先级**：Polymarket 结算价 / 官方比分源 > 官方直播间标题 > 中文战报 > 弹幕情绪（弹幕禁止单独定胜负）。
3. **多源交叉**：至少两路权威源一致才写"官方确认"；单源写"待交叉"。
4. 数据源要可脚本化、可复用，避免每次手工搜索。

---

## 1. LoL：Riot 官方赛事 API（首选，权威阵容实时可得）

### 接口（2026-08-27 实测可用）

```text
赛程    GET https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=zh-CN[&leagueId=<id>]
详情    GET https://esports-api.lolesports.com/persisted/gw/getEventDetails?hl=zh-CN&id=<matchId>
实时局  GET https://feed.lolesports.com/livestats/v1/window/<gameId>
```

请求头必须带：

```text
x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z
accept: application/json
```

（该 key 来自 lolesports.com 前端 / npm lck-analytics@0.4.0，2026-08-27 验证有效；失效时从 lolesports.com 页面 JS 或最新 npm 包重新提取。）

### 常用 leagueId（2026-08-27 官方 getLeagues 核实）

| 联赛 | leagueId |
| --- | --- |
| LCK | 98767991310872058 |
| LCK Challengers | 98767991335774713 |
| LPL | 98767991314006698 |
| LEC | 98767991302996019 |
| LCS | 98767991299243165 |
| LCP | 113476371197627891 |

> 注意：不同赛事（如 LCK 入围赛/季后赛与常规赛同 id，LCK CL 独立）用对应 id；不确定时先拉 `getLeagues` 或全量 `getSchedule` 再按队伍名/日期过滤。

### 关键字段

```text
getSchedule  -> data.schedule.events[].match.id（matchId）、teams[].name/code/result.gameWins
getEventDetails -> data.event.match.games[]：id（gameId）、state（completed/inProgress/unstarted）、number
window/{gameId} -> gameMetadata.blueTeamMetadata/redTeamMetadata.participantMetadata[]：
                   summonerName（含队伍前缀，如 "NS Kingen"）、championId（英雄英文 ID）
```

### 用法要点

- **赛后**：任一已结束 gameId 的 window 接口长期可查，直接给全队 5 人×英雄（最权威，无需人工配对）。
- **局中**：开局后 window 即有数据；BP/选人阶段 window 可能为空（实测 G3 BP 阶段无数据）——BP 阶段阵容可用官方直播间/战报快报过渡，开局后立刻用官方窗口校准。
- 单局胜者：`window` 无直接 winner 字段时，用赛程 `match.teams[].result.gameWins`（小局数）或官方战报核对。

### 现成封装

- npm：`lck-analytics`（@0.4.0，LCK 专用，含 standings/analytics）；`lol-esports-api`（通用）。
- 本项目工具：`tools/fetch_official_game_data.py`（按联赛+日期/队伍拉官方阵容）。

---

## 2. LoL：中文快报（最快、可交叉）

| 源 | URL 规律 | 内容 | 时效 |
| --- | --- | --- | --- |
| 直播吧 zhibo8 | `news.zhibo8.com/game/<yyyy-mm-dd>/<hash>native.htm`（按日期+队名搜索可得） | 首发名单、BP、关键时间线 | 赛后 5-20 分钟 |
| 虎扑 hupu | `bbs.hupu.com/<id>.html`（搜 "[赛后]队A X-Y 队B"） | 完整 BP+阵容+逐分钟时间线 | 赛后 5-20 分钟 |

示例（2026-08-27 NS vs BFX）：

```text
G1: https://news.zhibo8.com/game/2026-08-27/6a8fb20cd7ec6native.htm
G2: https://bbs.hupu.com/642121470.html
```

用法：一次 search 调用塞多个查询；能靠 snippet 定案就不 open_page（省 token）。

---

## 3. LoL：Leaguepedia（免费结构化，历史全量）

- 入口：`https://lol.fandom.com/api.php`
- Cargo 查询示例：

```text
action=cargoquery&tables=ScoreboardGames=SG&fields=SG.GameId,SG.Team1,SG.Team2,SG.Winner,SG.DateTime_UTC&where=SG.DateTime_UTC LIKE '2026-08-27%' AND SG.OverviewPage LIKE '%LCK%'&limit=50&format=json
```

- 选手×英雄在 `ScoreboardPlayers` 表（Link、Champion、Team 字段）。
- 注意：匿名限流严格（实测频繁 429），必须带 User-Agent、控制频率、失败退避；适合"历史回填"而非实时。

---

## 4. LoL：gol.gg / Oracle's Elixir（历史数据研究）

| 源 | 说明 |
| --- | --- |
| gol.gg | 比赛页含完整 BP/阵容/数据；无公开 API，可抓 HTML |
| Oracle's Elixir | GitHub 定期发布全联赛 CSV（选手、英雄、结果、经济等），适合回测/画像，非实时 |

---

## 5. CS2：公开结果 / 阵容源

CS2 没有 Riot 式统一官方 API，事实层按以下优先级拼装（命中即停）：

```text
P0  Liquipedia CS（免费结构化，可脚本化）—— 时间/队伍/逐图比分/HLTV id
P1  HLTV（权威：阵容/地图禁选/排名）—— Cloudflare 反爬，走非官方封装或人工抽查
P2  赛事官方（blast.tv / ESL / EWC 官网 + 规则书）—— 赛程/阵容/规则真源
P3  中文快报（直播吧 / 虎扑 / 5EPlay / 完美世界电竞）—— 快且含地图 BP
P4  FACEIT Data API（官方，需 key）—— 仅 FACEIT 旗下赛事
P5  PandaScore（商用，免费档有限）—— 全阵容 + 实时事件 WebSocket
仲裁  Polymarket 结算价 + 赛事官方比分页
```

### P0 Liquipedia CS（首选，工具已落地）

- 入口：`https://liquipedia.net/counterstrike/api.php`（标准 MediaWiki API）
- 必须带 User-Agent + `Accept-Encoding: gzip`，否则 HTTP 406
- 事件页 wikitext 内含 `{{Match|opponent1=...|opponent2=...|date=August 27, 2026 - 11:00 CEST|finished=...|map1={{Map|map=Anubis|t1t=..|t1ct=..|t2t=..|t2ct=..}}|hltv=2396927}}`
- 可解析出：精确开赛时间（含时区）、双方队伍、逐图 T/CT 比分、finished 状态、HLTV match id、VOD
- 事件页标题约定：`BLAST/Open/2026/Fall`（先 `list=search` 搜标题）
- 工具：`python3 tools/fetch_cs2_liquipedia.py --event "BLAST/Open/2026/Fall" [--date 2026-08-27] [--teams IC,VIT]`
- ⚠️ 实测注意：**Liquipedia 比分可能滞后数分钟**（IC vs Vitality Cache 曾显示 12:12，实际 16:13 加时）——终局比分必须 HLTV/战报/官方交叉；时间与队伍基本准确

### 重要但容易漏的 CS2 维度（用户关注外必补）

| 维度 | 为什么重要 | 获取 |
| --- | --- | --- |
| 地图池与地图禁选（veto） | CS 胜负第一变量；弹幕"队伍×地图强图"必须与官方 veto 交叉 | HLTV 比赛页 / 中文战报（2026-08-27 IC vs VIT：IC 禁 Inferno、VIT 禁 Ancient；IC 选 Anubis、VIT 选 Cache；IC 禁 Nuke、VIT 禁 Mirage，决胜 Dust2 未用上） |
| 逐图比分（含加时） | 13:8 / 16:13 加时差异影响判断强度 | Liquipedia / HLTV / 战报 |
| 赛制与晋级含义 | 双败 GSL、BO3、胜者组进半决赛 vs 败者组单败 | Liquipedia Format 段 / 赛事官方 |
| 阵容完整度（替补/换人） | 临时替补（stand-in）显著影响强度 | HLTV 比赛页阵容 |
| 选手角色（IGL/AWPer）与状态 | 狙击手状态（如 ZywOo 低迷）常是冷门信号 | HLTV 选手页 / 近期 rating |
| HLTV 世界排名 | 盘口定价的重要锚 | HLTV ranking 页 |
| H2H 与地图胜率（近 3 月） | "弱队爆冷"验证 | HLTV 队伍页 / Liquipedia team 页 |
| 官方规则书 | 暂停/加时/换人规则影响节奏判断 | 赛事官方（BLAST Handbook 在 Liquipedia infobox 直接有 URL） |
| 奖池与赛事级别 | S-Tier/Tier1 强度分层 | Liquipedia infobox（BLAST Open Fall 2026：$1.1M，S-Tier，葡萄牙+丹麦） |

### 已验证案例（2026-08-27）

IC（Inner Circle）2-0 Vitality（BLAST Open Porto Day2 首场）：

- 时间：08-27 17:00 CST 开赛（Liquipedia 11:00 CEST）
- 图一 Anubis 13:8 IC（IC 自选）；图二 Cache 16:13 IC（加时，VIT 自选）
- 爆冷口径：ZywOo 状态低迷数据垫底，VIT 掉入败者组；IC 晋级
- 数据源一致性：Liquipedia（队伍/时间/Anubis 13:8 一致；Cache 显示 12:12 滞后）< 虎扑/直播吧（完整 2-0+选图）< HLTV（终局权威）
- 当日其余赛程（北京时间）：20:00 MOUZ vs 9z、22:00 FUT vs Legacy、次日 00:30 Falcons vs LVG

---

## 6. Polymarket 结算 = 最终仲裁

- 已有工具：`python3 tools/verify_match_result.py --match-id <id> [--apply]`
- 结算价（outcomePrice ≥0.99 或 closed=true）即官方结果；多端不一致以 Polymarket 结算为准（规则 18）。

---

## 7. 建议接入方式（本地 + 线上情报库）

1. **比赛开局后 1 分钟内**：用官方 `window/{gameId}` 拉全队阵容，覆盖弹幕版"提及清单"——从根上消灭"选手×英雄配错"。
2. **小局结束**：赛程 `match.teams[].gameWins` + 中文战报交叉 → 回填局结果。
3. **整场结束**：Polymarket 结算仲裁 → 战报复核 → 更新情报库。
4. 新增联赛/新赛事先登记 leagueId（getSchedule 全量过滤），固化进 `leagues.json`。
5. 所有结论保留一行可溯源标注（源 + 抓取时间），不重复贴来源长文。

CS2 对照版：

1. **赛前/开赛**：Liquipedia 事件页确认开赛时间与队伍（`fetch_cs2_liquipedia.py --event <标题> --date <日期>`）。
2. **地图 BP**：开局前/首图前抓选图记录（虎扑/HLTV 比赛页），与弹幕"队伍×地图"讨论交叉。
3. **局中/图末**：Liquipedia 逐图比分 + 直播流比分交叉；终局以 HLTV/战报/官方比分页为准（Liquipedia 可能滞后）。
4. **整场结束**：Polymarket 结算仲裁 → 更新情报库；补录地图池/加时信息。

---

## 8. 已验证案例（2026-08-27）

NS vs BFX（LCK 入围赛 BO5）：

- matchId `117030752644841577`；G1 `117030752644841578`、G2 `117030752644841579`（completed）、G3 `117030752644841580`（inProgress）。
- 官方 window 数据与虎扑战报逐位一致（G1：NS 青钢影/皇子/发条/烬/慎，BFX 杰斯/盲僧/加里奥/女警/巴德；G2：NS 安蓓萨/梦魇/洛克/芸阿娜/璐璐，BFX 兰博/蔚/阿狸/EZ/扇子妈）。
- 新英雄官方英文 ID：Locke=洛克（中单 AP 刺客，2026 新英雄）、Yunara=芸阿娜（ADC，2025 新英雄）、Ambessa=安蓓萨/狼母。
