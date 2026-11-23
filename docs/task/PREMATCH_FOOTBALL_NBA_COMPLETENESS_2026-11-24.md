# 足球 / NBA 本地赛前数据链路与完整性（2026-11-24）

## 结论

足球和 NBA 已走同一套 Sportradar LMT Plus 客户端，但积分榜 feed 不同：

- 足球：`season_livetable/{seasonId}`；
- NBA：`season_dynamictable/{seasonId}`，读取响应中的
  `season.tables`。

2026-11-24 本地 72 小时窗口：

- 足球 21 场，深包 21/21；
- NBA 10 场，深包 10/10；
- LMT 总候选 31 场，成功 31 场；
- 43 个单场详情 HTML / JSON / CSV 全部生成；
- 1 场足球 fixture detail 端点持续返回 HTTP 500，页面保留该场并标
  “主市场缺失”，没有伪造赔率，也没有丢弃整场。

## 数据链路

```text
Stake 比赛页
  -> 公开 LMT licensing
  -> AES-256-CBC 解密
  -> Fishnet 短时 token
  -> lt-fn-cdn001 feed
  -> match_info
  -> 球队历史/近期/H2H
  -> squads / injuries / lineup
  -> league table
  -> normalize
  -> 单场 JSON + 详情 HTML + 指标 CSV
```

已使用 feed：

```text
match_info/{matchId}
stats_match_form/{matchId}
match_squads/{matchId}
stats_team_lastx/{teamUid}
stats_team_versusrecent/{homeTeamUid}/{awayTeamUid}
stats_team_squad/{teamUid}
season_livetable/{seasonId}
season_dynamictable/{seasonId}
stats_season_uniqueteamstats/{seasonId}
stats_season_injuries/{seasonId}
stats_season_topgoals/{seasonId}
```

## 足球字段

每支球队当前可取：

- 联赛排名、场次、胜平负、进失球、净胜球、积分；
- 近 10 场战绩、当前连胜/连续不胜；
- 对手、比分、主客场、赛事轮次；
- 18 项赛季统计：射正、射偏、角球、封堵、犯规、越位、
  门框、黄牌、红牌、进球、失球、控球率、点球成功/失败、零封等；
- 伤停球员、位置、状态、说明和起止日期；
- 主教练；
- 已公布/最近可用首发、阵型、号码和位置；
- 完整报名名单，包括全名、国籍、年龄、身高、体重、惯用脚、
  身价和入队时间；
- 队内射手和联赛射手榜；
- 完整联赛积分榜；
- 最近 10 场 H2H。

## NBA 字段

每支球队当前可取：

- 总体、联盟和分区排名；
- 场次、胜、负、胜率、games behind；
- 近 10 场胜/负；
- 主客场胜/负；
- 当前连续走势；
- 分区和联盟内胜负；
- 近 10 场对手、比分、主客场；
- 20 项赛季统计；
- 伤停；
- 当前/最近可用五人首发；
- 17–18 人报名名单；
- 最近 10 场 H2H。

NBA `season_livetable` 会返回空 `tables`，不能据此判断“没有排名”。
正确做法是继续请求 `season_dynamictable`。该 feed 当前已验证返回
总体榜、东西部榜和多个分区榜，例如 76 人总体第 1、胜率 82.4%，
开拓者第 11、胜率 62.5%。

## 本地出口

总览：

```text
reports/intel_prematch.html
reports/intel_prematch.json
```

单场：

```text
reports/intel_prematch_detail_<sport>_<fixture>.html
reports/intel_prematch_detail_<sport>_<fixture>.json
reports/intel_prematch_detail_<sport>_<fixture>.csv
```

详情页提供：

- 数据覆盖与缺口；
- 市场去水概率；
- 两队全部赛季统计；
- 完整名单、伤停、首发；
- 近期比赛和 H2H；
- 联赛积分榜和射手榜；
- 表头排序、打印/PDF、JSON/CSV 下载。

## 缺口纪律

- `usual_lineup.lineup_status=confirmed` 才是本场已公布首发；
- `latest_available` 表示最近一场官方首发，不是本场阵容；
- 伤停为空表示源返回空列表，不等于官方确认全员健康；
- fixture detail 500 时保留比赛卡，市场状态标 `missing`；
- 不用上一轮赔率、旧画像或其他来源补齐；
- 公开页面不展示平台品牌，内部 JSON 保留来源和抓取时间。
