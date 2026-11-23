# CS2 / Dota2 赛前数据完整性审计（2026-11-23）

## 结论

当前实现不是“完整数据”，更准确地说是：

> 已拿到右侧组件的大部分结构化原始字段，但归一化时截断了一部分，
> 页面又只展示其中一小部分摘要。

因此用户看到的内容明显弱于 Stake 比赛页右侧组件。问题分三类：

1. **接口已提供、本地已保存、页面没展示**；
2. **接口已提供，但本地归一化时被截断或丢掉元数据**；
3. **当前赛事/选手阶段本来就没有样本，必须显式标缺口**。

## 审计对象

- CS2：9z Team vs Lynn Vision
  `https://stake.com/zh/sports/counter-strike/international-3/pgl-major-singapore-2026-t3/1795510800000-9z-team-lynn-vision`
- Dota2：Aurora Gaming vs LGD Gaming
  `https://stake.com/zh/sports/dota-2/international-2/blast-slam-ix-t1/1795453200000-aurora-gaming-lgd-gaming`
- Oddin GraphQL 主接口：`https://api-disir.oddin.gg/main/disir/query`
- 本地数据：`reports/intel_prematch.json`
- 归一化：`tools/stake_oddin.py`
- 页面渲染：`tools/build_stake_prematch_site.py`

## 当前数据覆盖

### CS2

当前 8 场 CS2 全部成功取得深包。

- roster：80 人次；
- 有近三个月个人统计：70 人次，覆盖率 87.5%；
- 每场双方共 10 人 roster；
- 9z vs Lynn Vision：
  - 9z Team：5 人全部有个人统计；
  - Lynn Vision：5 人 roster 完整，但近三个月个人统计为 0/5；
  - 双方地图池合并 17 行；
  - 选手每人已存 15 个分项指标；
  - 赛事检索到 32 队、8 场；
  - `csgoTournamentStatistics` 当前比赛返回 `null`，所以赛事地图池、赛事最佳队伍/选手为空。

### Dota2

当前 4 场 Dota2 全部成功取得深包。

- roster：41 人次；
- 有近三个月个人统计：40 人次，覆盖率 97.6%；
- 每场通常双方 10 人；Team Liquid 当前 roster 为 6 人，多出一名替补/名单成员；
- 每名有统计的选手保存 13 个分项指标；
- 每队原始英雄池 127 项；当前 JSON 只保留前 15 项；
- 每名选手保存 3 个常用英雄；
- BLAST SLAM IX 赛事：
  - 18 队；
  - 20 场赛事赛程；
  - 赛事英雄池 127 项；
  - Radiant / Dire 胜率可用；
  - 赛事最佳队伍/选手各 5 项；
  - 赛事积分榜和 bracket 当前为空。

## 明确的数据损失

### P0：抓到后主动截断

| 项目 | 原始能力 | 当前处理 | 影响 |
| --- | --- | --- | --- |
| Dota 队伍英雄池 | 每队 127 项 | `_team_package` 截成 `favorites[:15]` | 大部分英雄取舍样本被隐藏 |
| Dota roster | Team Liquid 当前 6 人 | 页面渲染 `players[:5]` | 第 6 人完全不显示 |
| CS 选手指标 | 每人 15 个指标 | 页面仅显示 K/D/A、ADR、HS%、首杀 | 击杀总数、多杀、残局、AWP、道具伤害、闪白、存活等不可见 |
| Dota 选手指标 | 每人 13 个指标 | 页面仅显示 KDA、参团、金币、英雄伤害 | 补刀、反补、治疗、建筑伤害、真假眼、堆野、控制时长不可见 |
| CS/Dota 百分位 | 每个指标都有 `percentile` | 页面主要展示 `avg` | 无法判断指标在同项目里的相对强弱 |
| CS 队伍分项 | 24 个队伍指标 | 页面仅显示 6 个 | 手枪局转化、首 3/6/9/12 回合、T/CT 分边、elimination/objective 等丢失 |
| Dota 队伍分项 | 18 个队伍指标 | 页面仅显示 6 个 | 一塔、首肉、兵营、10/15/20 杀、时长等丢失 |

### P0：抓到了但完全未展示

CS2：

- 选手常用武器及每把武器的击杀/爆头；
- 选手 AWP kills、utility damage、enemies flashed、multi-kill、
  clutch rounds、lurk kills、grenades used；
- 队伍 opening conversion / opening death conversion；
- 队伍 first-to-win 3/6/9/12 rounds；
- 队伍 elimination winrate、objective winrate、rounds lost；
- 队伍整体 T/CT 拆分；
- 赛事 32 队名单及每队 roster；
- 赛事 bracket（有数据时）；
- 赛事 best teams / best players（有数据时）。

Dota2：

- 每名选手的 127 英雄原始候选池，目前前端不展示个人英雄池；
- 队伍英雄池只展示前 15 项；
- 赛事 best teams / best players 只显示每类前 5 个，且未做指标中文映射；
- 赛事 bracket（有数据时）未渲染；
- Team Liquid 第 6 名 roster 成员未渲染；
- 赛事 18 队 roster 只保存、不展示。

页面渲染位置：

- `tools/build_stake_prematch_site.py` 的 `render_oddin_team()`；
- 选手固定 `[:5]`；
- Dota 队伍英雄池固定 `favorites[:15]`；
- `render_oddin_tournament()` 只取相关赛程前 8 场；
- 页面没有独立详情页，所有数据塞在首页卡片折叠层。

### P1：接口/Schema 提供，但当前实现未抓

CS2：

- `csgoTeamsTournamentStatistics(tournamentId, homeTeamId, awayTeamId)`：
  赛事内队伍统计，和当前使用的三个月总体统计不是一回事；
- `csgoPlayerStatisticsAccordingRole(...)`：
  按 `ENTRY_FRAGGER / AWPER / SUPPORT / LURKER / KILL_LEADER`
  查看角色维度统计；
- `csgoPostMapStatistics(mapId)`：
  已完成地图的双方队伍统计、逐选手地图统计、对位、逐回合结果；
- `csgoScoreboard(matchId)`：
  当前系列比分、当前地图、逐图比分、地图名、上一张地图；
- `csgoMinimap(matchId)`：
  局内选手位置、存活、C4 状态（实时层，不属于赛前）。

本次验证：

- `csgoPostMapStatistics` 的 `map` 和 `rounds` 可以返回；
- 队伍/选手深字段组合在当前样本触发 HTTP 422，说明后端并不稳定；
- `csgoTeamsTournamentStatistics` 的简化查询也触发 422；
- 角色统计查询触发 422。

因此这些字段应作为“可选增强层”，需要单请求降级、缓存和错误隔离，
不能让整场数据失败。

Dota2：

- `dota2Scoreboard(matchId)`：系列比分、上一张地图、当前 BP；
- `dota2Minimap(matchId)`：局内塔/兵营状态；
- `dota2PickAndBan` subscription：实时 BP；
- 这些属于实时/赛后增强，不是赛前默认数据。

本次验证：

- 赛前调用 `dota2Scoreboard` 返回 422 或 deprecated；
- `dota2ScoreboardData` 赛前返回 Not found；
- 不能在赛前硬填 BP 或小局阵容。

### P1：近期比赛缺少地图级事实

当前 `Match.maps` 只保存：

```text
id / order / startTimestamp / endTimestamp / isClosed
```

缺少：

- 地图名；
- 该图比分；
- 胜方；
- 选手地图数据；
- ban/pick 顺序。

CS 可以通过 `csgoPostMapStatistics(mapId)` 或 scoreboard 补充；
Dota 当前 scoreboard 在赛前/历史样本不稳定，不能保证全部可补。

### P2：当前赛事确实没有提供的数据

CS2 PGL 样本：

- `csgoTournamentStatistics = null`；
- standings `[]`；
- brackets `[]`；
- 赛事地图池、赛事领先队伍/选手均为空。

Dota2 BLAST 样本：

- standings `[]`；
- brackets `[]`；
- 赛事 hero statistics 有 127 项，正常。

这些不是抓取失败，不能通过猜排名、补旧积分榜或伪造 bracket 解决。
页面必须显示“当前赛事阶段未提供”。

## 当前页面的结构性问题

### 1. 首页卡片不是详情页

用户需求是“点进比赛看完整队伍、选手、赛事数据”。
一个首页卡片即使有折叠层，也不适合承载：

- 10–11 名选手全指标；
- 两队完整英雄/地图池；
- 20 场赛事赛程；
- 32 队 roster；
- H2H、地图级结果、百分位。

应新增独立详情页：

```text
reports/intel_prematch_match_<fixture>.html
```

首页只保留：

- 开赛时间；
- 双方；
- 市场共识；
- 3–6 条关键赛前结论；
- 数据完整度；
- “进入完整赛前情报”链接。

### 2. 缺少“数据覆盖状态”

当前只显示模块是否存在，不显示：

- 选手 roster 是否完整；
- 近三个月统计覆盖几名；
- 地图/英雄池样本量；
- 赛事 stats 是否 provider null；
- standings/bracket 是否为空；
- H2H 是否有样本；
- 地图级 recent match 是否可核验。

详情页必须逐块显示：

```text
status: available / partial / provider_empty / not_started / api_error
sample_size
source_updated_at
```

## 推荐详情页结构

### CS2 详情页

1. **比赛头卡**
   - 开赛时间、赛事、BO、地图数量；
   - 双方 icon、近 5 场、总体地图胜率、样本。

2. **队伍整体对比**
   - 地图胜率、回合胜率；
   - T/CT 分边；
   - 手枪局、手枪胜转化、手枪负转化；
   - kills、deaths、KD、 assists、flash assists、ADR、HS%；
   - opening kills、opening conversion、opening death conversion；
   - AWP kills、utility damage；
   - elimination/objective win rate；
   - first to 3/6/9/12 rounds；
   - 每项同时显示 avg、percentile、样本量。

3. **地图池矩阵**
   - 全部地图，不只地图胜率非空项；
   - pick rate、ban rate、win rate；
   - 地图样本数；
   - T/CT 回合胜率；
   - 地图 icon/ID；
   - 明确区分“0 样本”和“真实 0%”。

4. **选手数据**
   - 完整 roster，包括替补；
   - 每名选手 15 个指标；
   - percentile 标识强弱；
   - 常用武器 kills/headshots；
   - 最近地图角色（可用时）；
   - roster-only 选手显示“有名单、无近三个月统计”。

5. **近期与 H2H**
   - 5 场近期系列；
   - 对手、比分、赛事、日期；
   - 可补时显示逐图地图名和比分；
   - H2H 系列结果与地图结果。

6. **赛事数据**
   - 32 队 roster；
   - 8/20 场赛程；
   - standings；
   - bracket；
   - 赛事地图 pick/ban、T/CT 胜率；
   - 赛事 best teams/players；
   - 全部为空时显示 provider_empty。

### Dota2 详情页

1. **比赛头卡**
   - 时间、赛事、BO；
   - 双方 icon、近 5 场、地图胜率、样本。

2. **队伍整体对比**
   - map winrate；
   - kills、KD、gold、XP、hero damage；
   - Roshan、tower、barracks；
   - first blood / tower / Roshan / barracks；
   - first 5/10/15/20 kills；
   - duration；
   - 每项 avg、percentile、样本量。

3. **完整英雄池**
   - 全 127 项；
   - hero icon、pick rate、ban rate；
   - 按 pick/ban/样本排序和筛选；
   - 不覆盖原始 127 项，只增加 `display_top`。

4. **选手数据**
   - 全 roster，包括第 6 人；
   - primary role；
   - KDA、参团、gold、XP、补刀、反补；
   - hero damage、healing、building damage；
   - wards、camps、stun；
   - 每人 3 个常用英雄及 pick/win；
   - 无统计成员显示 roster-only。

5. **近期与 H2H**
   - 5 场系列；
   - 对手、比分、赛事、日期；
   - 可补时显示逐局结果；
   - H2H 2/1/0 场等真实覆盖。

6. **赛事数据**
   - 18 队 roster；
   - 20 场赛程；
   - Radiant/Dire win rate；
   - 127 hero pick/ban/win；
   - best teams/players；
   - standings/bracket；为空则明确显示。

## 修复优先级

### P0

1. 新增 CS2 / Dota2 独立详情页；
2. 删除 Dota 队伍英雄池 `[:15]` 截断；
3. 删除选手 `[:5]` 截断；
4. 展示全部已存指标，不再只显示 4–6 个摘要；
5. 展示 avg + percentile + sample size；
6. 显示 roster-only / provider_empty / api_error。

### P1

1. 近 5 场系列补地图名和逐图比分；
2. 赛事 roster/bracket 完整渲染；
3. CS post-map/scoreboard 增强层，单独请求、单独降级；
4. 1 个月 / 3 个月 / 6 个月趋势对照；
5. CS tournament-scope team stats 与 overall 分开展示。

### P2

1. CS 角色维度统计；
2. 局内 scoreboard/minimap/BP 实时层；
3. 赛前到赛后同一详情页持续更新。

## 证据

- 2026-11-23 本地快照：8 场 CS2、4 场 Dota2 全部 Oddin 深包成功。
- CS2 roster 80 人次，70 人次有近三个月统计。
- Dota2 roster 41 人次，40 人次有近三个月统计。
- CS 9z vs Lynn Vision：Lynn Vision 5 人 roster、0 人近期统计。
- Dota Team Liquid：6 人当前 roster，JSON 保存 6 人，页面渲染固定取前 5 人。
- Dota 每队 raw favouriteHeroes 127 项，JSON 截成 15 项。
- `csgoTournamentStatistics` 对 PGL 样本返回 `null`。
- GraphQL introspection 确认：
  - `CsgoTeamStatistics` 31 个字段；
  - `CsgoPlayerStatistics` 17 个字段；
  - `Dota2TeamStatistics` 22 个字段；
  - `Dota2PlayerStatistics` 16 个字段；
  - `CsgoPostMapStatistics` 含队伍、选手、duel、round 数据；
  - `Dota2PickAndBan` 含双方 picks/bans。

## 最终判断

当前数据“有骨架、有真实样本”，但远未达到用户要求的完整可分析程度。
最严重的问题不是数据源不够，而是：

```text
原始 127 项 -> 只存 15 项
选手 15 项 -> 只显示 4 项
队伍 24 项 -> 只显示 6 项
第 6 人 roster -> 被页面截掉
赛事 roster/bracket/地图级 recent -> 未展示
```

在完成独立详情页、取消截断、补数据覆盖状态前，不应把当前版本称为“完整数据”。
