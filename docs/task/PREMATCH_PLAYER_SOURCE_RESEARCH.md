# 赛前队伍 / 选手 / 名单数据源核查（2026-11-23）

## 实施状态（2026-11-23 23:10 CST）

本轮已把结论落到项目代码，不再停留在“候选数据源”：

- `tools/stake_lmt.py`：足球 / NBA 的 LMT Plus 授权、token、feed 和归一化；
- `tools/stake_oddin.py`：从 Stake 比赛页提取电竞 widget 参数，读取
  Oddin GraphQL，归一化 CS2 / Dota2 / LoL 队伍、选手、地图/英雄池、
  H2H 和赛事数据；
- `tools/build_stake_prematch_site.py`：把两类深包接入“完整赛前数据”卡片；
- `tools/prematch_detail.py`：生成 43 个单场完整详情页，并同步输出单场
  JSON 与指标 CSV；
- `runtime/stake_lmt_cache.json`、`runtime/stake_oddin_cache.json`：短时缓存；
- `tests/test_stake_prematch.py`：授权解密、URL 构造、归一化、历史首发侧别、
  零值展示和中性品牌回归测试。

2026-11-23 当前窗口全量结果：43 场，42 场有效主市场、1 场 provider
fixture detail 500 缺口，43 场完整深包
（足球 21、NBA 10、CS2 8、Dota2 4、LoL 0）。LMT 31/31 成功，
Oddin 12/12 成功；没有把旧 `teams.json`、`players.json`、`rosters.json`
作为本场证据。每场比赛同时生成完整详情 HTML、JSON 和 CSV；
详情页展示全部已归一化队伍指标、选手指标、地图/英雄池、近期/H2H、
赛事名单/赛程/积分/池统计，并单独列出数据覆盖与缺口。

## 最新结论（2026-11-23 22:52 CST）

上一版只分析了 Stake 的公开盘口接口，结论不完整。Stake 比赛页右侧的
“队伍 / 选手 / 赛事统计”不是从 `odds-data.stake.com` 返回，而是由比赛页
下发的另一个内嵌数据组件提供。不同项目使用不同供应商和数据协议：

| 项目 | Stake 右侧组件数据源 | 数据协议 | 是否同一组件 |
| --- | --- | --- | --- |
| 足球 | Sportradar LMT Plus | Fishnet feed JSON | 同一比赛详情布局，独立数据层 |
| NBA | Sportradar LMT Plus | Fishnet feed JSON | 与足球同类，字段按项目变化 |
| CS2 | Oddin Disir | GraphQL + 直播订阅 | 与 Dota2 / LoL 同一 Oddin 组件族 |
| Dota 2 | Oddin Disir | GraphQL + 直播订阅 | 与 CS2 / LoL 同一 Oddin 组件族 |
| LoL | Oddin Disir | GraphQL + 直播订阅 | 组件代码已确认；本次无当前 LoL 场次做页面实测 |

因此不能再用一套“比赛信息”接口覆盖所有项目，也不能把盘口里的选手名当作
完整队伍/选手统计。正确结构是：

```text
Stake 赛程 / 市场
  -> odds-data.stake.com
  -> 时间、队伍、联赛、赛制、赔率、选手盘

Stake 比赛页右侧详情组件
  -> 足球 / NBA：Sportradar LMT Plus
  -> CS2 / Dota2 / LoL：Oddin Disir
  -> 近期战绩、地图/英雄池、队伍统计、选手统计、赛事统计、伤停/阵容等
```

### 1. 足球 / NBA：先解密组件授权，再读 LMT feed

Stake 使用公开 widget client
`7d2f8da584734cf9ab52112c1022d183` 加载 Sportradar 组件：

- 授权密文：
  `https://ws-cdn001.akamaized.net/7d2f8da584734cf9ab52112c1022d183/licensing`
- 解密方式：AES-256-CBC，OpenSSL `Salted__` 格式，
  MD5 `EVP_BytesToKey`，密码为公开 widget client id；
- 解密结果包含短时 `fishnetToken`；
- 数据基址：
  `https://lt-fn-cdn001.akamaized.net/{alias}/{language}/{timezone}/gismo/{feed}/{params}?T={token}`；
- 请求必须带 `Origin: https://stake.com` 与比赛页 `Referer`。

当前已验证 feed：

```text
match_info/{matchId}
stats_match_form/{matchId}
match_squads/{matchId}
stats_team_lastx/{teamUid}
stats_team_versusrecent/{homeTeamUid}/{awayTeamUid}
stats_team_squad/{teamUid}
season_livetable/{seasonId}          # 足球积分榜
season_dynamictable/{seasonId}       # NBA 动态积分榜/分区榜
stats_season_uniqueteamstats/{seasonId}
stats_season_injuries/{seasonId}
stats_season_topgoals/{seasonId}
```

2026-11-23 复测 Brentford vs Everton：
`match_info/72221396` 成功返回，主队 uid `50`、客队 uid `48`、
赛季 id `140756`。本地实现位于 `tools/stake_lmt.py`。

### 2. CS2 / Dota2 / LoL：Oddin iframe + 公共 GraphQL

Stake 比赛页 SSR 数据中的 `slugFixture` 包含：

```text
provider = "oddin"
widget.type = "iframe"
widget.data.url = "https://disir.oddin.gg/{game}/match?..."
```

iframe URL 已经带齐查询所需参数：

```text
brandToken={public brand token}
id={base64 match id}
homeTeamId={base64 home team id}
awayTeamId={base64 away team id}
tournamentId={base64 tournament id}
lang=zh
timeframe=THREE_MONTHS
availableData=tournament
availableData=teams
availableData=players
```

页面内 JS 将同一 URL 的 `brandToken` 作为 API key，调用：

```text
POST https://api-disir.oddin.gg/main/disir/query
Header: X-Api-Key: {brandToken}
Header: X-Locale: zh
Header: Origin: https://disir.oddin.gg
Content-Type: application/json
```

实时比分使用：

```text
wss://api-disir.oddin.gg/main/disir/query?apiKey={brandToken}
```

`brandToken` 是 Stake 页面公开下发的品牌 token，不是用户账号凭证。
工程实现仍应在每次任务中从当页 widget URL 解析，不能把 token、schema
或 base64 ID 当成永久常量。

#### CS2 可查询的数据

组件 bundle 已确认的 operation：

```text
CsgoMatch
CsgoTeams
CsgoPlayers
CsgoTournament
CsgoScoreboard / CsgoScoreboardEncrypted
OnCsgoScoreboardFeed / OnCsgoScoreboardFeedEncrypted
```

2026-11-23 实测 9z Team vs Lynn Vision：

- 页面：
  `https://stake.com/zh/sports/counter-strike/international-3/pgl-major-singapore-2026-t3/1795510800000-9z-team-lynn-vision`
- Oddin match id：`match/od:match:3389075`
- tournament id：`tournament/od:tournament:15491`
- 9z Team：`team/od:competitor:1141`
- Lynn Vision：`team/od:competitor:482`

`csgoTournamentInfo` 返回：

- 赛事名称、PGL 组织方、Kallang 地点、125 万美元奖池；
- 32 支参赛队伍及每队当前选手名单；
- 8 场当前赛程、BO 类型、比分与状态；
- 积分榜和淘汰赛 bracket（赛事阶段允许时）。

`csgoTeamsHistoricalStatistics` 返回：

- 近三个月近期比赛和 form；
- 总地图胜率及样本量；
- 逐地图胜率，例如 9z Team 对 Mirage `50% / 3 张`、
  Inferno `33.3% / 2 张`；总体地图胜率
  `32.26% / 31 张`；
- Lynn Vision 总体地图胜率 `50% / 10 张`；
- H2H 最近交锋。

`CsgoTeamStatistics` 还提供：

- map vote 的 pick / ban；
- 手枪局胜率与转化率；
- 开局击杀、开局转化、进攻/防守回合、首 3/6/9/12 回合胜率；
- kills、deaths、K/D、damage、headshot、opening kills、AWP kills、
  utility damage、flash assists、multi-kill、clutch 等；
- 队伍常用武器及逐选手完整统计。

实测 9z Team 的 `playerStatistics` 返回 5 人和近三月逐选手指标，包括
kills、deaths、assists、K/D、ADR、headshot rate、flash assists、
opening kills、AWP kills、utility damage、enemies flashed、
multi-kill rounds、clutch rounds。Lynn Vision 的本场历史选手统计为空，
但赛事 roster 仍有 5 人，说明“名单可用”和“统计已覆盖”必须分开标记。

#### Dota2 可查询的数据

组件 bundle 已确认的 operation：

```text
Dota2Match
Dota2Teams
Dota2Players
Dota2Tournament
Dota2Scoreboard / Dota2ScoreboardEncrypted
Dota2Minimap / Dota2MinimapEncrypted
OnDota2ScoreboardFeed / OnDota2ScoreboardFeedEncrypted
OnDota2MinimapFeed / OnDota2MinimapFeedEncrypted
OnDota2PickAndBanFeed
```

2026-11-23 实测 Aurora vs LGD：

- match id：`match/od:match:3442628`
- tournament id：`tournament/od:tournament:15514`
- BLAST SLAM IX：18 支队伍、20 场赛程、75 万美元奖池；
- `dota2TournamentInfo` 成功返回赛事元数据、队伍和选手名单。

Dota2 队伍统计支持：

- 近期比赛与 form、总体/逐地图胜率；
- kills、K/D、gold、XP、hero damage、Roshan、tower、barracks；
- first blood、first tower、first Roshan、first barracks；
- first 5/10/15/20 kills、比赛时长；
- 常用英雄 pick/ban rate；
- 逐选手 KDA、参团率、gold、XP、补刀、反补、英雄伤害、治疗、
  建筑伤害、真假眼、堆野、控制时长、常用英雄和英雄胜率。

赛局内另有比分板、英雄、装备/净值、pick/ban、塔和兵营小地图状态。
本次静态接口查询偏慢，赛事信息和 schema 已验证，历史统计接口应在正式
接入时加超时、重试和缓存，避免阻塞整页生成。

#### LoL 可查询的数据

Oddin 共享 bundle 中已确认存在：

```text
LolMatch
LolTeams
LolTournament
lolPlayers
lolScoreboard
lolScoreboardMinimap
onLolScoreboard
onLolScoreboardMinimap
```

GraphQL schema 提供赛事、队伍历史、选手、积分榜、英雄池、比分板和小地图。
队伍统计可覆盖 kills/deaths/KDA、gold、15 分钟经济差、英雄伤害、
小龙/大龙/先锋/塔/水晶、first blood / first turret / first dragon 等；
选手统计可覆盖 KDA、参团率、gold、补刀、视野、控制、建筑伤害、
常用英雄与英雄胜率。本次没有当前 LoL fixture，上线前仍须用一场真实页面
核对 operation 参数和字段覆盖。

### 3. 相同点与不同点

相同点：

- 都是比赛详情页右侧的嵌入式情报组件；
- 都按“赛事信息 / 两队 / 选手 / 近期表现”组织；
- 都有当前场次与历史统计分层；
- 数据可用性受赛事阶段、供应商覆盖和样本量限制。

不同点：

- 足球/NBA 是 Sportradar LMT feed，一次请求一个具名 feed；
- CS2/Dota2/LoL 是 Oddin GraphQL，一次 query 返回一棵结构化对象；
- 足球字段围绕联赛排名、伤停、阵型、射手和赛季统计；
- 电竞字段围绕地图/英雄池、选手操作指标、BP、地图/局统计和实时比分；
- NBA 与足球共用 LMT 客户端；NBA 积分榜使用 `season_dynamictable`，
  已验证返回总体、分区、分组排名以及胜率、近10场、主客场记录。

### 4. 推荐接入方案

不要把所有项目硬塞进一个“大而全”的请求。建议新增独立读客户端
`tools/stake_oddin.py`，与现有 `tools/stake_lmt.py` 并列：

1. 从 fixture 和 Stake canonical URL 读取比赛页；
2. 从 SSR `slugFixture.widget.data.url` 提取 Oddin iframe 参数；
3. 按项目分别查询 `CsgoTournament/CsgoTeams`、
   `Dota2Tournament/Dota2Teams`、`LolTournament/LolTeams`；
4. 原始 GraphQL 响应按比赛 id 落缓存；
5. 归一化为统一的 `tournament / teams / players / maps_or_heroes /
   recent_form / tournament_stats / h2h / live_scoreboard`；
6. UI 对空数据显式显示“该赛事阶段未覆盖 / 样本不足”，
   不回退旧 `teams.json`、`players.json` 或别场名单；
7. 公开页面保持中性品牌，但 JSON 和内部审计必须保留真实 provider、
   operation、抓取时间和原始响应路径。

建议先完成 CS2，因为当前样本已覆盖 roster、近期比赛、地图胜率、
选手详细统计和赛事统计；随后接 Dota2，再找真实 LoL 场次校准。

### 5. 风险与边界

- 不把 Oddin / LMT 的 roster 自动写成“官方首发”；
- 不把盘口选手对位当完整阵容或选手统计；
- 不让“最近比赛有数据”掩盖“本场首发未公布”；
- 不把 provider 缺失写成 0，必须区分 `null`、空数组、未覆盖和真实 0；
- 页面可以不出品牌来源，但不能声称这些统计是项目独立采集或
  AI 从零识别；内部 provenance 必须保留；
- Stake `robots.txt` 对 sportsbook 路径有限制，正式生产前需复核
  使用条款、频率和缓存策略；只能读取公开页面，不登录、不碰账户接口。

### 6. 本次证据

- 2026-11-23 22:30 CST：读取 Stake CS2 match HTML，确认
  `provider=oddin`、`widget.type=iframe`，iframe 指向
  `https://disir.oddin.gg/csgo/match?...`。
- 2026-11-23 22:33 CST：Oddin GraphQL introspection 成功；确认
  `csgoTournamentInfo`、`csgoTeamsHistoricalStatistics`、
  `dota2TournamentInfo`、`lolTournamentInfo` 等 query 字段。
- 2026-11-23 22:40 CST：9z vs Lynn Vision 的赛事 roster、近期比赛、
  地图胜率和逐选手统计查询成功。
- 2026-11-23 22:42 CST：Aurora vs LGD 的 Dota2 赛事信息成功返回，
  18 队 / 20 场 / BLAST SLAM IX。
- 2026-11-23 22:52 CST：重新验证 Sportradar
  `match_info/72221396`，Brentford/Everton 主客队和赛季 id 正常返回。
- 2026-11-23 23:05 CST：全量生成 43 场完成；Oddin 12/12、LMT 31/31，
  公开 HTML 无平台品牌文本。
- GitHub 代码检索：`api-disir.oddin.gg` 命中 0；
  `csgoTeamsHistoricalStatistics` / `dota2TeamsHistoricalStatistics` 命中 0；
  `disir.oddin.gg` 仅命中文档 / iframe 集成示例。结论是没有必要复制
  第三方爬虫，应维护本项目适配器。

## 结论

当前“AI 赛前情报”页面不再读取项目内旧的 `teams.json`、`players.json`
或 `rosters.json`。这些库含主观画像、旧名单和待核实项，不适合冒充当前首发。

当前模块只用比赛页下发的结构化字段：

- 整场赛程与队伍：fixture 的 `name` / `competitors`；
- 比赛项目、联赛、时间、赛制：fixture 与地图/局市场；
- 当前可识别选手：`players` 组中的
  `Duel of Player Kills Draw No Bet` 对位盘；
- 选手盘口基准：单选手 `Total Kills`、`Total Headshots` 等
  Over/Under 市场；
- 市场共识：整场 Winner / 1X2 去水概率。

平台盘口能证明“本场盘口覆盖了这名选手”，但不能单独证明官方首发。
因此页面统一写“平台盘口识别”，角色、替补和临时换人仍标“待官方确认”。

## 实测结果

2026-11-23 当前 72 小时窗口：

- 43 场比赛中 43 场有完整深包；
- 足球 21、NBA 10、CS2 8、Dota2 4、LoL 0；
- CS2 对位盘可给出双方各 5 人；
- Dota 2 深包每场可给出双方共 10 人左右，赛事英雄池 127 项；
- CS2 深包每场可给出双方共 10 人、地图池与阵营/回合拆分；
- 没有选手盘的场次留空，不用旧画像补位；
- 足球 / NBA 的球员进球或得分盘不当作首发名单。

## 外部补充源研究（暂停，不在本模块接入）

以下资料保留为研究记录。用户已明确要求先完整复现 Stake 页面自身的数据，
因此当前版本不接 Riot / Liquipedia / OpenDota / HLTV，也不把它们混入
“赛前情报”数据包。

### 1. Riot LoL Esports（英雄联盟）

- 赛程 / 对局 / gameId：
  `https://esports-api.lolesports.com/persisted/gw/getSchedule`
- 详情：
  `https://esports-api.lolesports.com/persisted/gw/getEventDetails`
- 局内阵容：
  `https://feed.lolesports.com/livestats/v1/window/{gameId}`

边界：官方 window 在开局后才稳定提供选手×英雄；赛前 BP 未开始或
window 尚未生成时不能伪造阵容。现有封装为
`tools/fetch_official_game_data.py`。

### 2. Liquipedia Counter-Strike（CS2）

- MediaWiki API：
  `https://liquipedia.net/counterstrike/api.php`
- 实测返回 MediaWiki 1.43.12；
- 请求必须带有效 User-Agent 和 gzip；
- 队伍页的 `Player Roster` 表可解析当前登记选手、教练及加入时间。

2026-11-23 抽查 Team Liquid 队伍页可读到 NAF、EliGE、malbsMd、
Jorko、JT 与教练 flashie。该名单反映“队伍页登记 roster”，
不一定等于本场实际首发；平台对位盘仍优先用于当前场次。

### 3. OpenDota（Dota 2）

- API：`https://api.opendota.com/api/`
- 队伍列表：`GET /teams`
- 队伍详情：`GET /teams/{team_id}`
- 队伍选手历史：`GET /teams/{team_id}/players`

2026-11-23 实测 Team Liquid：

- `team_id=2163`；
- `rating=1333.98`；
- `/players` 带 `is_current_team_member` 字段，但当前样本只返回
  部分 current 标记，不能把 null/缺失自动当离队。

用途：队伍评级、历史选手、最近比赛与跨场背景。
不能替代赛事官方首发。

### 4. 赛事官方 / HLTV（CS2 深挖）

CS2 的地图 veto、首发替补、教练、rank、近期地图胜率优先：

1. 赛事官方规则页与阵容公告；
2. HLTV match/team 页面；
3. Liquipedia roster；
4. 平台本场对位盘。

HLTV 有 Cloudflare 与抓取限制，不做高频爬取。需要时使用低频缓存或人工核验。

## 展示层级

```text
当前比赛事实（已接入）
  fixture：时间 / 队伍 / 联赛 / 赛制

平台深包（已接入）
  足球 / NBA：Sportradar LMT Plus
  CS2 / Dota2 / LoL：Oddin Disir GraphQL

市场识别层（已接入）
  players group：双人对位盘 + 单人数据盘

外部补充层（暂停）
  Riot window / 赛事官方 / HLTV / Liquipedia / OpenDota
```

每层必须独立标注。没有当前平台选手盘时显示“未覆盖”，
不能回退到旧画像、历史名单或其他比赛的阵容。

## 下一步

1. 找一场真实 LoL 页面，完成 Oddin `lolTeamsHistoricalStatistics` 的现场验收；
2. NBA 积分榜已切换到 `season_dynamictable`，并保留
   `season_livetable` 作为足球路径；
3. 把“赛事 roster 有名单”和“近三个月有统计”在 JSON 中继续分开保存；
4. 生产环境落实频率限制、缓存 TTL、请求超时和字段降级；
5. 只有用户明确要求时，再单独接入外部官方源做交叉校验。
