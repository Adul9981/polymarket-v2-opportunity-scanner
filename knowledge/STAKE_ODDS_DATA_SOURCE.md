# Stake Odds Data API 数据源评估（2026-10-22）

> 2026-11-23 复核补充：官方 OpenAPI 仍是首选接入方式；已新增独立“赛前情报”
> 生成器与页面。GitHub 调研、主站抓取边界、足球/NBA 接入口径见
> [docs/task/PREMATCH_INTEL_MODULE.md](../docs/task/PREMATCH_INTEL_MODULE.md)。

结论先行：**Stake 有可用的官方赔率数据源，可以作为 Polymarket 的跨市场交叉参考，但不能替代 Polymarket 的分钟级历史与成交主源。**

本次只做了公开、只读 GET 核验，没有登录 Stake、没有使用账户 Token、没有下注，也没有绕过 Cloudflare、403 或地域限制。

## 1. 官方入口与验证状态

| 项目 | 结果 | 证据级别 |
| --- | --- | --- |
| 官方文档 | `https://docs-odds-data.stake.com/` | 已核对 |
| OpenAPI 规范 | `https://docs-odds-data.stake.com/dist.yaml/dist.yaml` | 已取得，HTTP 200 |
| API base | `https://odds-data.stake.com` | 已核对 |
| OpenAPI 版本 | 1.0.0，文件修改时间 2026-10-21 15:36:59 GMT | 已核对 |
| 鉴权声明 | OpenAPI 声明 `X-API-KEY` header | 文档已核对 |
| 实际未鉴权访问 | 2026-10-22 00:33-00:36 UTC，未带 API Key 请求 `/sports`、赛事目录与 `/fixtures/{fixture}` 均返回 HTTP 200 | 本次实测 |
| 长期授权边界 | 未鉴权可用可能是临时公开或网关策略；不能据此认定获准长期、商用或高频采集 | 待确认 |
| 联系入口 | `developers@easygo.io`（OpenAPI contact） | 已核对 |

正式上线前应向 Stake/开发者联系人确认：使用条款、API Key 获取方式、生产配额、限流、商用许可、数据再分发限制，以及是否有 WebSocket/历史序列服务。

## 2. 已验证的覆盖

2026-10-22 00:33 UTC 的 `/sports` 快照中：

- 共 46 个运动/电竞项目；
- 其中 19 个 `type=esport`，16 个当前 `enabled=true`；
- 当前启用的重点电竞项目包括 League of Legends、CS2、Dota 2、Valorant；
- 篮球项目存在，`Basketball / USA / NBA` 可返回 fixture 和独赢、让分、总分市场。

当时 LoL 的赛事目录有：

- World Championship 2026；
- EMEA Masters 2026 Summer。

当时 CS2 目录包括 PGL Masters Bucharest 2026、IEM Beijing 2026、BLAST Rivals Fall 2026 等；Dota 2 目录包括 EPL Masters III、Nexus Series II 等。这里只能说明“当时可发现”，不能据此推断所有历史联赛都能回查。

## 3. 已验证的端点与字段

公开规范中的主要只读端点：

```text
GET /sports
GET /sports/{sport}/categories
GET /sports/{sport}/{category}/tournaments
GET /sports/{sport}/{category}/{tournament}/fixtures
GET /fixtures/{fixture}
```

OpenAPI 文档简介还提到单独的 `/odds/{fixture}`，虽然当前规范没有正式列出该 path，但本次请求返回 HTTP 200 和同样的 fixture/market 结构；`/fixtures/{fixture}` 同样返回赔率。接入时优先使用有 schema 的 `/fixtures/{fixture}`，同时记录 `/odds/{fixture}` 为“实测可用但文档未正式定义”的兼容端点。

关键字段：

| 层级 | 字段 | 说明 |
| --- | --- | --- |
| Sport | `slug`, `type`, `provider`, `enabled` | `type` 可区分 `sport/esport`；provider 当前见 `oddin/betradar` |
| Fixture | `id`, `slug`, `name`, `startTime`, `status`, `updatedAt` | `status` 见 `inactive/active/live/ended`；时间为毫秒 epoch |
| Market | `id`, `name`, `status`, `specifiers`, `updatedAt` | `specifiers` 保存 map、handicap、threshold、side 等盘口条件 |
| Outcome | `id`, `name`, `odds`, `active`, `voidFactor` | `odds` 是十进制赔率；不能当 Polymarket 的 0-1 概率价格直接混存 |

实际响应里 `groups[].markets` 是 **数组套数组**。同一 market 可能同时出现在 main/maps/players 等不同分组视图里，因此适配器需要按 market ID、specifier 和状态去重，不能按响应行数直接统计市场数。

## 4. 代表性赔率快照

以下仅用于验证结构与覆盖，不是下注建议。

| 项目 | Fixture | 主要市场快照 | 结果 |
| --- | --- | --- | --- |
| LoL | Solary - Galions（EMEA Masters，2026-10-23 20:00 UTC） | Match Winner：Solary 1.95 / Galions 1.75；Map 1-5 Winner 均可读取 | 可读取整场与逐局独赢 |
| CS2 | Aurora Gaming - The MongolZ（PGL Masters，2026-10-24 07:00 UTC） | Match Winner：Aurora 1.22 / The MongolZ 3.80；另有逐图 Winner、Round Handicap、Total Rounds | 可读取整场、小图、让分与总分 |
| Dota 2 | Team Yandex - GamerLegion（2026-10-22 08:00 UTC） | Match Winner：Team Yandex 1.05 / GamerLegion 7.50；另有 Map Handicap、Total Maps、Total Kills | 可读取整场、地图与击杀盘 |
| NBA | New York Knicks - San Antonio Spurs | Winner：Knicks 1.84 / Spurs 1.94；另有 Handicap、Total | 可读取篮球主市场 |

LoL fixture 响应含 482 个 market 视图、459 个唯一 market ID；CS2 sample 为 314/300；Dota 2 sample 为 424/383。重复主要来自不同页面分组视图，不代表真实独立盘口数量。

## 5. 关键限制

### 5.1 没有已验证的历史序列

OpenAPI 没有价格历史、历史快照或回放端点；只返回当前 fixture/market 状态和最后一次 `updatedAt`。因此：

- 不能假定可以像 Polymarket 一样回补过去几个月的 60 秒序列；
- 要从现在开始自己定时采样并落盘；
- 无法验证“更新更快”时，不能只比较一个当前价格，必须同步记录时间戳并跑多场对照。

### 5.2 没有已验证的推送接口

规范只描述 REST GET，没有 WebSocket/SSE/webhook 路径。当前可确认的是轮询模型；轮询频率需要平台明确授权。

### 5.3 赔率不是可成交价

Stake 返回的是博彩公司十进制赔率，没有 Polymarket 式订单簿、盘口深度、可成交数量或手续费结构。它可以回答“博彩公司如何定价”，不能回答“在 Polymarket 这笔数量能以什么价格成交”。

### 5.4 暂停会导致大量缺口

本次检查的两场 live fixture 中：

- CS2 Fluxo W7M - Galorys：119 个市场视图全部为 `suspended`，赔率均为 0 且 outcome 不可用；
- Dota 2 Team DK - New Growth：5 个市场视图全部为 `suspended`。

因此不能把暂停状态填成前一个赔率，也不能把 0 当成真实价格；这些必须作为行情缺口记录。

### 5.5 不提供完整比赛上下文

fixture 的 `feedStartTime/feedEndTime` 在本次样本中为 `null`，响应没有地图/小局比分、经济差、回合或选手事件。形态对齐仍要依赖项目现有官方赛事源、Liquipedia/HLTV、弹幕和其他比分源。

## 6. 建议接入方式

建议把 Stake 定位为 **B 级交叉验证源**：

| 用途 | 是否适合 | 说明 |
| --- | --- | --- |
| Polymarket 分钟级形态主数据 | 否 | 无已验证历史；保留 Polymarket 为主源 |
| 赛前跨市场共识 | 是 | 对比 Stake 去水后隐含概率与 Polymarket 价格 |
| 局中快照/暂停/恢复事件 | 是，低权重 | 需要自建时间序列，并处理 suspended |
| 检测定价背离 | 是 | 仅在联赛、对阵、市场、盘口线完全一致时比较 |
| 直接触发自动交易 | 暂不 | 无历史、授权和深度信息，先积累样本 |

建议第一阶段只做 60 秒只读快照，覆盖项目已登记的一级 LoL/CS2/Dota2 场次；连续积累 5-10 场后，再与 Polymarket 对照“更新延迟、有效报价覆盖率、暂停时长、背离后的结果”。在拿到明确 API 配额前不提高轮询频率。

每条快照至少保存：

```text
observed_at_utc
http_status
sport_slug
fixture_id
fixture_slug
fixture_start_at_utc
fixture_status
market_id
market_name
market_status
specifiers
market_updated_at_utc
outcome_id
outcome_name
decimal_odds
outcome_active
void_factor
provider
source_url
```

价格转换只作为派生字段保留：`raw_implied = 1 / decimal_odds`。同一双边市场的去水概率可用 `p_i = (1/d_i) / sum(1/d_j)`，但它仍是市场参考，不是真实胜率。原始十进制赔率、盘口线、暂停状态和采集时间不能丢。

## 7. 最终判断

**可以纳入，但先做只读快照与跨平台对照，不做主源替换，也不直接做自动交易。**

Stake 的增量价值是：可能比 Polymarket 更早反映传统博彩市场的赛前定价，并提供更多盘口类型。它的缺口是：历史、推送、可成交深度与授权边界都还没有验证。先把时间序列和覆盖率跑出来，才能判断“更新更快”是否真实、是否稳定，以及是否能形成可验证的交易优势。

## 8. 复现入口

```bash
curl -sS https://odds-data.stake.com/sports
curl -sS https://odds-data.stake.com/sports/league-of-legends/categories
curl -sS https://odds-data.stake.com/sports/league-of-legends/international-1/tournaments
curl -sS https://odds-data.stake.com/fixtures/881874-solary-galions
```

验证时间：2026-10-22 08:33-08:36 Asia/Shanghai（00:33-00:36 UTC）。所有 HTTP 请求均为公开只读 GET。

## 9. 2026-11-23 复核与 GitHub 方案调查

### 9.1 官方入口复核

2026-11-23 再次读取：

- `https://docs-odds-data.stake.com/dist.yaml/dist.yaml` 返回 HTTP 200；
- OpenAPI 仍为 3.1.0，文档版本 1.0.0；
- OpenAPI 的 `last-modified` 为 2026-11-22 02:10:02 GMT；
- `securitySchemes.apiKey` 仍声明 `X-API-KEY` header；
- 正式 path 仍包括 `/sports`、categories、tournaments、fixtures 与
  `/fixtures/{fixture}`；文档简介另提到 `/odds/{fixture}`。

当前 `/sports` 已启用：

- 电竞：League of Legends、CS2、Dota 2、Valorant；
- 传统体育：Soccer、Basketball 等。

足球可按国家/区域目录读取；本次确认可用：

- England / Premier League；
- Spain / La Liga；
- Italy / Serie A；
- Germany / Bundesliga；
- France / Ligue 1；
- International Clubs / UEFA Champions League；
- International Clubs / UEFA Europa League。

Basketball / USA 目录包含 NBA。

### 9.2 网页与内嵌组件边界

`https://stake.com/robots.txt` 的 Sportsbook Rules 限制多个 sportsbook
页面路径，包括 esports 子路径和部分赛事组合路径。生产前仍需复核条款与
频率。当前实现只读取公开比赛页下发的非账户数据：

- 足球 / NBA：公开 Sportradar LMT Plus widget licensing 与 feed；
- 电竞：公开比赛页 SSR 中的 Oddin iframe 参数，再读取 Oddin GraphQL。

不登录、不读取账户 Token、不调用下注/余额/充值/提现接口，也不抓取
登录态专属 DOM。赛程与赔率仍以 `odds-data.stake.com` 为主入口。

### 9.3 GitHub 可用项目

| 项目 | 数据路径 | 许可 | 对本项目的结论 |
| --- | --- | --- | --- |
| [liunian7077/stake-worldcup-odds-monitor](https://github.com/liunian7077/stake-worldcup-odds-monitor) | 官方 Odds Data API；按比赛状态调度、SQLite 变化历史、SSE | 未声明许可证 | 架构参考；不直接复制代码 |
| [LordsStar/X](https://github.com/LordsStar/X) | 官方 Odds Data API；赛前查询与市场筛选 | 未声明许可证 | 调用方式参考；不直接复制代码 |
| [ChipaDevTeam/StakeAPI](https://github.com/ChipaDevTeam/StakeAPI) | 非官方 `/_api/graphql`，需要登录 access token，含账户/下注能力 | MIT | 不符合只读边界；不接入 |

截至本次检索，没有发现 Stake 官方维护并发布的第三方 SDK。GitHub 对
`api-disir.oddin.gg`、`csgoTeamsHistoricalStatistics`、
`dota2TeamsHistoricalStatistics` 均为 0 命中；`disir.oddin.gg` 只有
iframe 集成示例。因此不复制第三方爬虫，项目自建只读适配器：

```text
官方 OpenAPI 契约
  -> X-API-KEY 环境变量
  -> 限速、重试、失败保留旧页
  -> 统一 fixture / team / market / outcome schema
  -> LMT / Oddin 比赛详情深包
  -> 短时缓存 + 明确缺口
  -> 静态 JSON + HTML
```

### 9.4 已落地接入

本地新增：

- `tools/build_stake_prematch_site.py`；
- `tools/stake_lmt.py`（足球 / NBA）；
- `tools/stake_oddin.py`（CS2 / Dota2 / LoL）；
- `config/stake_prematch.json`；
- `reports/intel_prematch.html`；
- `reports/intel_prematch.json`；
- 网站导航入口“赛前情报”；
- VPS 每 10 分钟刷新服务与 timer 定义。

2026-11-23 真实只读验收：72 小时窗口内 43 场，CS2 8、Dota2 4、
足球 21、NBA 10，43 场主市场均有效。完整深包 43/43：
LMT 31/31、Oddin 12/12。英雄联盟当前窗口 0 场，按无场次显示，
不生成虚构结果。
