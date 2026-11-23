# 赛前情报模块（任务 6）

最后更新：2026-11-23

## 1. 目标与边界

“赛前情报”是弹幕情报台的独立入口，汇总赛程、队伍近期表现、选手统计、
地图/英雄池、赛事数据与主市场共识。它不替代弹幕、Polymarket 分钟价格、
官方比分或赛后复盘。

首批覆盖：

- 电竞：英雄联盟、CS2、Dota 2，继续使用 `config/market_watchlist.json`
  的联赛白名单；
- 足球：英超、西甲、意甲、德甲、法甲、欧冠、欧联；
- 篮球：NBA。

Valorant 和其他传统体育保留扩展位，不在第一版自动接入。

边界：

- 只读公开赛程 API 与比赛页内嵌组件数据，不登录 Stake，不读取账户 Token；
- 不调用下注、余额、充值、提现或账户接口；
- 十进制赔率与去水概率只作赛前跨市场参考，不是真实胜率或可成交价；
- 不把 Stake 报价混入 Polymarket 0–1 分钟曲线；
- 不直接触发交易；
- 盘口暂停、outcome 不可用或赔率为 0 时显示缺口，不沿用旧值。

## 2. 数据源结论

赛程与市场主源：

```text
STAKE Sports Data API
base:  https://odds-data.stake.com
docs:  https://docs-odds-data.stake.com/
spec:  https://docs-odds-data.stake.com/dist.yaml/dist.yaml
```

OpenAPI 声明 `X-API-KEY` 鉴权。当前只读 GET 在匿名情况下可访问，
但该现象不能视为长期、商用或高频授权。生产环境通过
`STAKE_ODDS_API_KEY` 环境变量按需提供 Key，并仅在服务器后端起效。

赛前详情源分两套，不能互换：

| 项目 | 详情组件 | 读取方式 |
| --- | --- | --- |
| 足球 / NBA | Sportradar LMT Plus | licensing 解密 -> Fishnet token -> `lt-fn-cdn001` feed |
| CS2 / Dota2 / LoL | Oddin Disir | 比赛页 SSR iframe 参数 -> `api-disir.oddin.gg/main/disir/query` |

Oddin iframe URL 已带 `brandToken`、比赛/队伍/赛事 base64 ID。GraphQL
请求使用 `X-Api-Key: brandToken`、`X-Locale: zh`。brandToken 是公开
页面下发的品牌 token，不是账户凭证；每次任务仍从当页重新解析并短时缓存。

完整接口、字段和实测证据见
[PREMATCH_PLAYER_SOURCE_RESEARCH.md](PREMATCH_PLAYER_SOURCE_RESEARCH.md)。

GitHub 调研：

- `liunian7077/stake-worldcup-odds-monitor`：使用官方 Odds Data API，
  有按比赛状态调度的只读架构，可参考；仓库无许可证，代码不直接复制；
- `LordsStar/X`：同样读取官方 Odds Data API，可作为调用方式参考；
  仓库无许可证，代码不直接复制；
- `ChipaDevTeam/StakeAPI`：MIT 许可的非官方 GraphQL 包装，
  需要用户登录 Token，并包含下注/账户能力；不符合本项目只读边界，不接入；
- 未发现成熟的公开 Oddin GraphQL SDK；GitHub 对
  `api-disir.oddin.gg`、`csgoTeamsHistoricalStatistics`、
  `dota2TeamsHistoricalStatistics` 均为 0 命中，只有 iframe 集成示例。
  因此本模块维护自己的只读适配器，不复制第三方爬虫。

## 3. 采集与标准化

入口：

```bash
python3 tools/build_stake_prematch_site.py
```

配置：

- `config/stake_prematch.json`：时间窗、上限、项目与联赛白名单；
- `config/market_watchlist.json`：LoL / CS2 / Dota 2 联赛白名单。

输出：

- `reports/intel_prematch.html`：用户可见静态页；
- `reports/intel_prematch.json`：同一轮机器可读快照。

核心数据流：

```text
Stake categories / tournaments / fixtures
  -> 时间窗与联赛白名单过滤
  -> fixture detail
  -> 主市场识别（1X2 / Moneyline / Match Winner）
  -> 去重 outcome + 十进制赔率
  -> 去水概率：
       p_i = (1 / decimal_odds_i) / Σ(1 / decimal_odds_j)
  -> JSON 快照 + 独立 HTML

深度数据流：

Stake match page
  -> 足球 / NBA：Sportradar LMT feeds
  -> CS2 / Dota2：Oddin GraphQL（LoL 同 schema，待真实场次验收）
  -> normalize(team / player / maps_or_heroes / form / h2h / tournament)
  -> short-lived cache
  -> 卡片“完整赛前数据”详情层

足球 / NBA 的 LMT 取数补充：

- 足球积分榜使用 `season_livetable/{seasonId}`；
- NBA 积分榜使用 `season_dynamictable/{seasonId}`，读取
  `season.tables` 的总体、分区和分组排名；
- NBA 排名保留胜/负、胜率、近 10 场、主客场拆分、连续走势、
  分区/联盟记录和 games behind；
- `season_livetable` 为空时自动降级到动态表；单个 fixture detail
  返回 500 时保留比赛卡并明确标记市场缺口，不丢弃整场。

奥丁查询拆成 team、tournament core、tournament stats 三组小请求，
避免单个大查询触发 422；缓存默认 15 分钟，页面元数据缓存 30 分钟。
```

主市场识别口径：

- 足球只取无 specifier 的 `1x2`，保留主胜/平/客胜；
- NBA 只取整场 `Winner (Incl. Overtime)` 等独赢市场；
- 电竞只取整场 `Match Winner - Twoway`，不把 Map/Game Winner 当整场；
- 半场、单节、让分、总分、正确比分、组合盘、选手/回合盘不进入首页主市场；
- 同一个 market 可能在多个 group 视图重复，按 market ID 去重。

异常处理：

- 所有 fixture-list 请求失败：本轮失败，保留旧页；
- fixture 总量为 0：本轮失败，保留旧页并告警；
- 单项目或单联赛失败：其他项目继续，缺口写入 JSON 与页面；
- 无有效主市场的比赛仍展示，但明确标记“主市场缺失/暂停”。

## 4. 前端页面

页面命名：`intel_prematch.html`。

首屏：

- 生成时间、未来窗口；
- 比赛数、有效报价数、完整深包数、平台识别选手人次、暂停/缺口数；
- LoL / CS2 / Dota2 / 足球 / NBA 覆盖条。

比赛卡：

- 北京时间、项目、联赛、队伍、赛制；
- 去水概率、原始十进制赔率；
- 有效/暂停/缺口；
- 本场平台盘口识别出的选手、槽位与击杀/爆头等基准线；
- 队伍近期战绩、总体/逐地图胜率、样本量；
- CS2 地图 pick/ban、T/CT 回合胜率、逐选手 K/D、ADR、HS%、首杀、
  AWP、道具伤害、多杀和残局；
- Dota2 / LoL 英雄池 pick/ban、选手角色、KDA、参团、经济、伤害、
  视野/控制等分项；
- 赛事 roster、相关赛程、积分榜、赛事地图/英雄池和领先数据；
- 原始 fixture 标识与抓取时间保留在机器审计 JSON。

卡片不再承担“完整数据仓库”的职责。每张卡提供“完整数据页”入口：

- 详情 HTML：`intel_prematch_detail_<sport>_<fixture>.html`；
- 完整 JSON：同名单场 `.json`；
- 指标 CSV：同名单场 `.csv`；
- 详情页支持浏览器打印 / 另存为 PDF。

详情页按“比赛头卡 → 数据覆盖与缺口 → 市场共识 → 两队全部统计 →
地图/英雄池 → 选手全部指标 → 近期/H2H → 赛事名单/赛程/积分/池统计”
展开。首页只保留摘要和入口，避免卡片过长，也不牺牲完整字段。

页面不读取旧队伍/选手画像库，避免把过期或主观画像冒充当前阵容。
选手优先用深包统计；统计为空但赛事 roster 存在时，展示名单并标记
“近期样本不足”，不把 roster 写成官方首发。没有选手盘口时直接留空。
页面只呈现事实与市场共识，不输出自动推荐、仓位或交易指令。

平台选手字段与补充源的边界见
[PREMATCH_PLAYER_SOURCE_RESEARCH.md](PREMATCH_PLAYER_SOURCE_RESEARCH.md)。

## 5. 发布架构

生产链路：

```text
VPS /opt/danmu-intel
  -> prematch-intel.timer 每 10 分钟
  -> build_stake_prematch_site.py
  -> reports/intel_prematch.html + .json
  -> vps_publish.py 复制到 site_repo/intel/
  -> 导航/统计/付费墙注入 + 站点审计
  -> nginx /var/www/danmu-pulse 秒级直出
  -> git commit/push 到 Adul9981/danmu-intel
  -> GitHub Pages 作为镜像/SEO 备份
```

GitHub 不是赛前数据的第一跳。它是站点代码与静态产物的版本仓库和 Pages
镜像；生产实时展示由 VPS nginx 承担。另一个 GitHub Actions 工作流
`push-game-status.yml` 负责每 5 分钟把 Polymarket 小局状态推回 VPS，
也与本模块的 Stake 赛前抓取相互独立。

部署文件：

- `deploy/prematch-intel/prematch-intel.service`
- `deploy/prematch-intel/prematch-intel.timer`

可选环境文件：

```text
/opt/danmu-intel/runtime/stake_prematch.env
STAKE_ODDS_API_KEY=...
```

## 6. 第一版验收

2026-11-23 本地真实只读验收：

- 72 小时窗口；
- 43 场未来比赛；
- 42 场有效主市场报价、1 场 fixture detail provider 500 缺口；
- 43 场完整深包：LMT 31、Oddin 12；
- CS2 8、Dota2 4、足球 21、NBA 10；
- 英雄联盟当前窗口 0 场，保留项目入口并显示无场次；
- 请求错误 0。
- 43 个单场详情页、43 个单场 JSON、43 个指标 CSV 全部生成。

注意：这是结构验收，不是预测准确率验收。下一阶段应先积累 5–10 个比赛日
的 Stake 快照，再与 Polymarket、官方赛果及弹幕结论做时间对齐，评估
覆盖缺口、暂停时长、更新延迟和背离后的结果。

## 7. 后续扩展顺序

1. Valorant；
2. 足球更多联赛与国际赛事；
3. 其他篮球联赛；
4. 逐步添加棒球、网球、冰球等板块；
5. 单场详情页接入争议盘、让分、总分，但必须与主市场分层；
6. 与 Polymarket 同对阵联动，只展示并列共识/分歧，不混画价格。
