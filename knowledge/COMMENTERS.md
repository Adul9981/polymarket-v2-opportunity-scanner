# 评论者画像（Commenter Profiles）

> 定位：跟踪 Polymarket 评论区活跃发言者，按规则库
> （knowledge/COMMENT_ANALYSIS_RULES.md）做"方向性发言 -> 后续价格"的
> lead-lag 检验，样本累计后给出可信度标签。
> 原则：画像只用于观察名单与情绪参考，不直接作为交易依据；
> 同方向样本 >=5 才给可信度标签（规则 S5）。

## EurekaWTI（Euphoric-Piano）

```text
资料：
  评论主地址（baseAddress）：0x572130ed8e0513c45454c2dd8eba905b25cb15ac
  代理钱包（proxyWallet，profile 页展示地址）：
    0xb797402993a52d55a1b405549062e0267910e779
  账号创建：2026-03-06
  累计评论：175 条（抓取至 2026-08-17，含政治/体育/电竞/杂项）
  原始数据：docs/data/snapshots/lol-t1-dnf-2026-08-17/comments/eurekawti_comments_raw.json
风格初判：
  1. 逆向/嘲讽型："bagholders REKT"、"TOLD YOU IDIOTS"、讽刺多头；
  2. 名单/阵容敏感：多次提示"等名单公布再下注"（08-11 与 08-17 同主题）；
  3. 事件驱动：暂停、回滚、规则变化时发言最密集；
  4. 覆盖广：政治（MAGA/以色列）、足球、电竞都发，电竞评论占比约 16%。
```

## 电竞相关发言时间线（已映射到比赛）

| 时间（北京） | 比赛（按时间窗口映射） | 原文摘录 | 备注 |
| --- | --- | --- | --- |
| 08-11 16:12-16:58 | HLE vs DNS（KeSPA Cup，HLE 二队 vs DNS 一队） | "fake roster vs real roster" / "the official lineup has been announced it is challengers for HLE vs Starting Roster for DNS Soopers dummy" / "i wonder what the people buying challengers are smoking right now" / "or just wait until roster is announced" / "HLE bettors deserved this for the lucky scam they pulled last night vs geng" | 与用户 08-11 复盘吻合：名单公布后 DNS 赔率 20c->70c 信息差；他明确喊"等名单" |
| 08-12 17:26 | DNS vs NS（LCK） | "Definitely Needed Sharvel"（DNS 选手 Sharvel） | 选手级观察 |
| 08-12 18:55 | （LPL 场次，EDG 相关） | "Congratulations to gamblers that won on EDG last game..." | 结果后评论 |
| 08-17 17:05 | T1 vs DNS G2 赛前 | "T1 challengers should be favorites imo" | G1 T1 赢（部分应验） |
| 08-17 18:58-19:15 | T1 vs DNS G2 暂停段 | "T1 cheats getting their glitch miracle reversed" / "sell your overvalued T1 shares ... after chronobreak" / "its going sub 60 minimum the second they restart" / "TOLD YOU IDIOTS" | 全部看跌 T1 高位，后续全部应验 |
| 08-17 19:21 | T1 vs DNS G2 崩盘段 | "match fixing" | 指控类（只记录） |
| 08-17 19:40-20:16 | T1 vs DNS G2 后 | "challengers team ... elite starting pros" / "so many idiots on t1" / "are we still sure T1 challengers are super good?" | 事后嘲讽 |

## 08-17 G2 lead-lag 检验（发言 vs 后续 T1 价格，game2 市场）

| 发言（UTC） | 北京 | 内容 | P0 | +5m | +15m | +60m | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 09:05:20 | 17:05 | T1 challengers should be favorites imo | 39.0c | 38.0c | 40.0c | 43.5c | 方向温和（G1 应验） |
| 10:58:08 | 18:58 | glitch miracle reversed（看跌） | 71.0c | 70.5c | 68.5c | 0.5c | 命中 |
| 11:00:35 | 19:00 | sell overvalued T1, sub 50 after chronobreak | 70.0c | 71.5c | 35.5c | 0.5c | 命中（+15m 破 50） |
| 11:08:37 | 19:08 | bagholders, sub 60 on restart | 66.0c | 43.0c | 36.5c | 0.5c | 命中（重启后破 60） |
| 11:12:57 | 19:12 | TOLD YOU IDIOTS | 68.5c | 34.0c | 45.0c | 0.5c | 命中 |
| 11:21:49 | 19:21 | match fixing（指控） | 43.0c | 53.5c | 0.5c | 0.5c | 方向最终一致（先反抽） |

结论：08-17 单日方向性发言 5 条（看跌 T1），5 条全部在 60 分钟内命中；
1 条赛前"favorites"发言部分应验（G1）。属强单日样本，但跨场样本仍不足。

## 系列赛终局验证（08-17 故事闭环）

```text
终局：DNS 3:1 赢下系列赛（G1 T1，G2/G3/G4 DNS；整场 DNS 99.95c）。
EurekaWTI 全链路：
  08-17 16:12 前（HLE/DNS 名单日）已站"等名单公布"；
  08-17 17:05 "T1 challengers should be favorites imo"（G1 前，T1 二队被看衰）
  -> G1 T1 赢（部分验证）；
  08-17 18:58-19:15 G2 暂停段 5 条看跌 T1，全部命中（70c -> 0.5c）；
  08-17 19:40-20:16 赛后嘲讽（"are we still sure T1 challengers are super good?"），
  最终 DNS 3:1 赢下，他站的方向完整兑现。
故事价值（用户反馈 2026-08-17）：
  一个评论者在评论区公开站队（看空 T1/看多 DNS），从赛前名单、暂停预警
  到系列赛结束全程验证——是"评论区方向性发言 + 事件信息"可用的完整案例。
注意：故事成立 ≠ 可直接跟随。他 08-17 的判断依赖名单信息差与暂停事件
两重信息，普通比赛无此类事件时参考价值下降；仍按观察名单处理，
累计 >=5 个跨场方向样本后才评估可信度标签。
```

## 评估与跟踪

```text
可信度标签：观察名单（单日 5/5 命中，跨场样本待积累；尚未达到 S5 的
  >=5 跨场样本门槛，不给高可信度标签）。
价值点：
  1. "名单/阵容敏感 + 事件驱动"组合在 HLE/DNS（08-11）与 T1/DNS（08-17）
     两场信息差/暂停事件中都踩对了方向；
  2. 发言习惯集中在暂停/回滚等事件窗口——这类窗口恰好是价格最危险的时段，
     他的发言可作为"事件窗口情绪确认"的参考信号之一。
跟踪规则：
  1. 后续比赛自动抓取 series 评论，命中 EurekaWTI 发言即并入本表；
  2. 每场按规则库 T4 做 lead-lag，累计 >=5 个跨场方向样本后升级/降级标签；
  3. 用途边界不变：只作警示/情绪参考，不作反手/方向依据。
```
