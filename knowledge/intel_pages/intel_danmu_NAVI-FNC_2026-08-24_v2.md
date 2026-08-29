NAVI vs FNC 弹幕情报页 · 2026-08-24（A 型骨架 · 局中快照）（v2 决策导向版）

## 0核心情报速览

    5:0
    弹幕口径 · 官方待回填
    灰信号见 §2
    锚点见 §3
    盘口见 §4

    风险本窗口灰信号 0 条（规则层）；仅覆盖 G1 开局，后续监控 → 详 §2
    锚点Vladi 5000+ LP 压制（正锚）+ Locke 高风险 pick（负锚），当前待定 → 详 §3
    盘口本窗口无有效数字盘（样本均为表情）/人头/独赢/时长类数字弹幕。 样本不足，不硬造。 （VPS 聚合页 76 条盘… → 详 §4
    共识赛前/BP 期预测全部待定（系列未结束，赛后回填）填。 预测（弹幕口径） 时间 验证状态 FN… → 详 §5/§10

  **决策落点：**LONG/SHORT：FNC（候选） ：Vladi 5,000 LP 中路压制 + Upset Ezreal 状态 + Soboro 换人红利 → FNC 独赢/2-0 口径偏多（lec 官方频道弹幕方…

## 1比赛信息与结果总览 / 状态核验

### header

NAVI vs FNC 弹幕情报页 · 2026-08-24（A 型骨架 · 局中快照）

    局中 · 非终局（数据口径）
    弹幕口径 · 官方待回填
    A 型整场骨架 · 赛后自动升级终态

# NAVI vs FNC · 弹幕情报页

Natus Vincere vs Fnatic · 2026-08-24 · LEC（slug: lol-navi-fnc-2026-08-24）· SAP/Apple 风格 · 局中快照（A 型骨架）

    5,916原始弹幕条数（切片窗口）
    1,879活跃用户（规则层口径）
    269/分平均密度（行级）
    547密度峰值 14:52 UTC
    235FNC 提及（行级计数）
    69NAVI 提及（行级计数）

### 0比赛信息
**对阵**　Natus Vincere（NAVI）vs Fnatic（FNC）· 事件 slug：lol-navi-fnc-2026-08-24
  **联赛**　LEC（弹幕口径：官方频道 twitch_lec 同播；常规赛末段，涉及 top4/季后赛与 KOI（MKOI）出线命运）—— 联赛与赛制待官方确认
  **赛制**　BO3（弹幕口径：「Navi 2 0」「FNC 2-0 is my guess」「slight edge to Fnatic 2-1」等系列比分预测）
  **当前进度（数据口径）**　第一局 BP 后开局（约 15:08 UTC 起），局内阶段约 S1 对线期；**未见任何终局信号** —— 详见第 1 节状态核验
  **用户提示口径**　「比赛已结束（弹幕多信号确认，结果待官方核对）」 —— 与当前数据窗口不符，已按防错规则核验，暂以数据口径为准（见第 1 节）
  **数据源**　caedrel 4,977 条 / otplol_ 518 条 / lec 官方 214 条 / kamet0 52 条（LoL 相关合计 5,761）；另有 gaules 151 条、eslcs 4 条为 CS2 跨场噪音（155 条，不计入本场口径）
  **数据窗口**　2026-08-24 14:49:57 – 15:11:01（UTC），切片文件 + 规则层 intel.json 同窗口
  **Polymarket**　事件 slug 已登记于本报告；市场链接/结算价待联网后回填（沙箱无外网）
  **页面生成**　2026-08-24 15:14 UTC 附近，基于当前快照；采集会话仍在运行（state=running）

### 1结果总览 / 状态核验（弹幕口径 · 未结束 · 官方待回填）

结论先行：**本窗口数据无法支持「比赛已结束」**。所有可得信号均指向第一局进行中。按「宁可保守不放大」原则，本页不输出任何终局结果。

### 结束判定四类信号核对（VERIFICATION_METHODOLOGY 框架）

| 信号类别 | 本场情况 | 判定 |
| --- | --- | --- |
| 结束语高密度（GG/恭喜/拿下 ≥2 分钟、≥5 用户） | 「gg」「1-0 navi」（15:03 caedrel）与「1-0 fnc」（15:03 lec）出现在 BP 期，与比分牌 0-0 及后续 BP 讨论矛盾；同刻另有 LPL 场（Gala/Ruler Penta）与 CS2 场次信号混入 —— 判为预测/玩梗，非结果陈述 | 未通过 |
| 比分/局数核对 | 比分牌弹幕 14:53 / 15:02 / 15:05 均为「FNC 0-0 NAVI // GX 0-0 G2」；15:03–15:08 为 BP 过程，第一局 15:08 前后才开局 | 未通过 |
| 流量骤降（峰值 <10% 持续 ≥5 分钟） | 15:04–15:10 密度稳定在 195–264 条/分；15:11 的 7 条/分为**切片窗口截断**（采集继续运行），非骤降 | 未通过 |
| 官方/第三方源 | 本地 official_matches.json 无本场记录；沙箱无外网，Polymarket 结算/战报站不可达 —— 待联网核对 | 缺源 |

工具校验：python3 tools/verify_match_end.py --end 2026-08-24T15:03:00Z --teams NAVI,FNC → **评分 2/4 · 需人工确认**（未达 ≥3 结束门槛）。
  结论：弹幕口径「NAVI vs FNC 第一局进行中（约 S1 对线期）」，系列比分 0-0 未变；**比赛未结束，结果待官方确认后回填**。若用户侧另有来源支持「已结束」，请提供口径，我们将按误判修正流程回退/更正。

## 2灰信号汇总（风险 · 观众质疑非结论）

### 6灰信号汇总（0 条）
今日无灰信号：本窗口（14:49–15:11）未检出假赛/剧本/卡盘/演员类集中质疑（规则层 gray_signals.count=0）。**纪律声明：观众质疑不作假赛结论**；本场仅覆盖第一局开局，后续窗口继续监控，若出现灰信号将显著展示并进入统计页。

### 7方向性情报（锚点 × 群体共识 × 灰信号）

三块独立、可交叉印证；赛后统一回填验证。当前均为「待定」状态。

### 7.1 正锚点（看好 → 谁赢）

| 对象 | 锚点内容 | 依据 | 出现时间 | 多路共振 | 赛后验证 |
| --- | --- | --- | --- | --- | --- |
| Vladi（FNC 中单） | 5,000+ LP（5289）soloQ 压制叙事；Locke 高风险 pick 承载 FNC 胜负预期 | 熟练度锚点（soloQ 排名）＋ BP 讨论 | 15:00–15:10 | 是（lec + otplol + caedrel） | 待定 |
| Rhilech（NAVI 单人线） | 绝活英雄 → 「it's a NAVI win」 | 观众熟练度锚点（one-trick / aatrox-zaahen-qiyana） | 15:05–15:06 | 是（lec + otplol 相关） | 待定 |
| Upset（FNC 下路） | 「欧洲最强 Ez」；近况数据优于 Carzzy | 近况/数据讨论 | 15:06–15:10 | otplol 为主 + lec 转述 | 待定 |
| Soboro 换人（FNC 上单） | 换人后 FNC「不一样了」「最近有点猛」 | 阵容/换血动态 | 15:08–15:13 | 是（huya remember + 硕硕） | 待定 |

### 7.2 负锚点（看衰 → 谁输）

| 对象 | 锚点内容 | 依据 | 出现时间 | 多路共振 | 赛后验证 |
| --- | --- | --- | --- | --- | --- |
| Poby（NAVI 中单） | 「出不了大师（EUW）」；「真让人失望」；NAVI「没中单」 | soloQ 段位叙事＋近况评价 | 14:58–15:11 | 是（lec + otplol） | 待定 |
| SamD（NAVI 下路） | 「吃满 Seraphine 技能」；与 Poby 并列下滑 | 局内表现 + 近况 | 14:59–15:10 | otplol 为主 | 待定 |
| Soboro（FNC 上单） | 「会被点菜 / int」 | 单用户预测（与「LEC 最强上单」反向） | 15:06 | 单条（caedrel） | 待定 |
| Canna（NAVI 上单？待确认） | 「被 Oscarinin 世界赛资格赛 gap」历史对照 | 历史交手叙事 | 14:55 | 单条（lec） | 待定 |

### 7.3 群体共识（弹幕情绪）

- **看好 FNC 方向**（约 10 条显式口径，含预测/玩梗）：「Fnatic 2-0」「FNC 2-0 is my guess」「FNC going 2-0 this series」「FNC 2-0 … guarantee playoffs」（lec 15:00–15:10）；「FNC wins right」「FNC EZ」（caedrel 14:53）；「无脑FNC」「梭哈fnc」（硕硕 14:50/15:08）；「slight edge to Fnatic 2-1」（lec 14:59）

- **看好 NAVI 方向**（约 13 条显式口径，含预测/玩梗）：「Navi 2 0」「o7 NAVI 2-0」「NAVI WIN TODAY」（caedrel 14:50–14:57）；「This is easy series for Navi」（caedrel 15:06）；「it's a NAVI win」「Should be Navi win」（lec 15:05/15:10）；「梭哈navi」「navi拿下了」（硕硕 15:08）；「Allez GO NAVI」（otplol 15:01）

- **分歧点**：双方 2-0 预测并存（2-0 vs 2-1 打满：「slight edge to Fnatic 2-1」）；BP 评价三方不一（FNC 更好 / NAVI 更好 / 五五开并存）

  结论：**共识不足**（FNC 方向约 10 条 vs NAVI 方向约 13 条，均为预测/玩梗、无过去式结果陈述；样本仅覆盖赛前+BP+第一局开局）。锚点方向与群体共识呈「分歧」状态 —— 多源共振尚未形成，本场方向性情报置信度低，不宜直接作决策依据。

### 7.4 灰信号条件预测

  今日无灰信号（0 条）—— 无「若兑现则指向 X 输/赢」的条件预测可输出；若后续窗口出现灰信号，将按「观众质疑，非结论」标注并给出条件方向。

## 3BP 锚点与选人情报

### 2逐局复盘（第一局 BP–开局快照）· 弹幕规模、密度峰值与时间线

当前仅有第一局（进行中，约 S1 对线期）：BP 15:02–15:08、开局 15:08 前后、本窗口止于 15:11。第二局/第三局未发生 —— 待观察。逐局复盘将随切片补充升级为终态（A 型）。

### 密度峰值（原始文件逐分钟，LoL 相关频道为主）

| 时间（UTC） | 条数/分 | 弹幕主题（代表样句） |
| --- | --- | --- |
| 14:52 | 547 | 赛前 hype/版聊峰值（caedrel 520 条）：FNC/NAVI 讨论、KOI 出局剧本（「Of navi wins koi out of playoffs」）；含 gaules CS2 广告噪音 |
| 14:57 | 444 | 赛前演播室 + 预测刷屏（「o7 NAVI 2-0」「NAVI WIN TODAY」）+ 场外玩梗（Odo 领带/内裤梗） |
| 15:01 | 382 | Viktor 禁用（LCS bug）讨论高潮 + BP 临近（「pas de Viktor」「rip vladi」「Viktor lock?」） |
| 15:02–15:03 | 371 / 349 | BP 开始：Vladi 锁 Locke、Nocturne 锁定、「they took rumble from vladi gg」；「1-0 fnc / 1-0 navi」预测混入（甄别：非比分） |
| 15:08–15:10 | 195–264 | 第一局开局稳定区间：「Navi ont 0 front」「who won draft」「Should be Navi win」 |
| 15:11 | 7 | 切片窗口截断（采集继续运行，非流量骤降） |

注：14:52 峰值含大量场外版聊与广告（gaules 频道 promo 刷屏），密度数字仅作规模参考；本场局内事件峰值（如首杀/团战/终结）尚未进入本窗口，待后续切片补充。

### 关键事件时间线（本窗口，UTC）

- 14:50–14:53赛前：FNC/NAVI 讨论、「Navi 2 0」预测（14:50）、「NAVI over VIt」（14:51）；比分牌弹幕「FNC 0-0 NAVI // GX 0-0 G2」（14:53）

- 14:54–14:59演播室段：Viktor 因 LCS Palafox bug 被禁用成为讨论焦点（「Viktor disabled?」「Chronobrake 没修好」）；「NAVI WIN TODAY」等预测刷屏；「Both teams have been struggling, slight edge to Fnatic 2-1」（14:59）

- 15:00–15:01「Is Vladi gonna 5k lp all over navi?」（15:00）；「Fnatic 2-0」（15:00）；「Who also think NAVI can win this?」（15:01）

- 15:02–15:03BP 开始：FNC 中单 Vladi 锁 Locke（「Wow Vladi sur Locke」「this locke pick is either going to be what wins this game or completely loses it for Fnatic」）；NAVI 侧 Nocturne 锁定；「they took rumble from vladi gg」；「1-0 fnc / 1-0 navi」出现（甄别为预测）

- 15:04–15:07BP 讨论：Zaahen 位置疑问（「zaahen jgl ?」「zaheen en top ?」）、Rell/Alistar 下路组合、Upset Ezreal 讨论（「peut-être le meilleur Ez d'Europe」）、Rhilech 绝活锚点（「it's a NAVI win rhilech is on his one-trick」）；BP 评价分歧（「La draft Fnatic est nulle non ?」vs「giga winning pick for FNC」）

- 15:08第一局开局：「Navi ont 0 front」「who won draft」「way better draft」；中文二路（硕硕）「梭哈fnc」「梭哈navi」「navi拿下了」（预测/玩梗，非结果）

- 15:09–15:11局内早期：Nocturne/Zaheen 打野组合讨论（「funny they ended up with noc and zaheen over the usual jungle picks」）、「vi was banned anyway」、「Should be Navi win」（15:10）、「poby le forceur」（15:11）；窗口截断

- 15:13（窗口外）中文二路仍在第一局：「这把FNC赢不了」—— 局内，非终局

### 3阵容与 BP / 英雄讨论（弹幕口径 · 待官方名单）

归属按弹幕上下文推断（如「Locke pick … loses it for Fnatic」「Vladi 5k LP 对阵 NAVI」），位置/名单未与官方核对，禁止当作正式阵容。

#### Fnatic（推定，弹幕口径）

- 上单 Soboro（骚菠萝）：「换了个骚菠萝之后fnc不一样了」（huya remember 15:13）；「SOBORO IS THE BEST TOP IN THE LEC」（caedrel 15:02，单条吹捧）

- 打野 Razork（旧 BO 参照）：「Vladi a mieux engagé avec son Ryze que Razork et son Wukong lors du dernier BO」（otplol 14:57）

- 中单 Vladi：Locke 锁定（15:03）；5,000+ LP soloQ 叙事（「5289 Vladi」otplol 15:06）

- 下路 Upset：Ezreal 讨论（「Upset sur Ezreal, peut-être le meilleur Ez d'Europe」otplol 15:06）；「Upset dash in au mid et mourir à la 18ème min」（otplol 15:08 玩梗）

- 辅助：未具名（Rell/Alistar/Karma 为英雄讨论）—— 样本不足

#### NAVI（推定，弹幕口径）

- 单人线 Rhilech：绝活锚点（Aatrox/Qiyana 等，位置上/中有歧义）：「it's a NAVI win rhilech is on his one-trick」（lec 15:05）

- 打野 Zaahen：Nocturne 组合讨论（「funny they ended up with noc and zaheen over the usual jungle picks」lec 15:09；draft 期观众还在问位置「zaahen jgl ?」15:04）

- 中单 Poby：「poby can't even get out of masters in EUW」（lec 15:10）；「C'est surtout Poby que je trouve vraiment decevent」（otplol 14:59）

- 下路 SamD：「il préfère Kai Sa SamD」（otplol 15:06）；「Poby et SamD sont vraiment en dessous dernièrement」（otplol 14:59）

- 上单 Canna：3 次提及、无直接归属句（含「canna got turbogapped by oscarinin」历史对照 lec 14:55）—— 角色/所属待确认

- 辅助：未具名 —— 样本不足

### BP 关键情报

- 15:03「they took rumble from vladi gg」—— Vladi 的 Rumble 被 NAVI 拿走/封锁，观众即时判「gg」（BP 针对信号）

- 15:03FNC 锁 Locke（Vladi）：「Wow Vladi sur Locke」「Locke lock」「C'est flex Locke?」；官方频道评价「Locke is 50/50 champ」「this locke pick is either going to be what wins this game or completely loses it for Fnatic」—— 高风险 pick 信号

- 15:04–15:06NAVI 下路组合讨论：「Rell ca donne jhin alistar en face」「miss fortune rell for free win」「KaiSa Alistar c'est bien ici」；Upset 的 Kai'Sa/Ezreal 均为讨论焦点

- 15:07–15:09「rumble support shen top」；「ezreal sera kills ashe sera for next game」（下一局展望）；「vi was banned anyway」；Nocturne + Zaahen 非常规打野组合

- 15:08–15:09BP 评价分歧（重要）：「Navi ont 0 front」（otplol，看衰 NAVI 阵容）vs「way better draft / giga winning pick for FNC」（lec/caedrel，看多 FNC 阵容）vs「fnc阵容不如nv啊感觉」（huya 硕硕，看多 NAVI 阵容）—— 三方口径不一

### BP 后战绩情报（硬性检查项）

  **无战绩情报提及**：无「选手 × 英雄」历史战绩/胜率数字弹幕（无 X胜Y负/胜率/没输过/没赢过类）。仅存在熟练度锚点：Rhilech「one-trick / aatrox-zaahen-qiyana=win」与 Vladi「5,000+ LP」soloQ 叙事 —— 属熟练度锚点，非战绩数字，赛后一并回填验证。

## 4盘口与市场讨论

### 10盘口讨论（样本不足）
本窗口无有效数字盘讨论：本窗口无有效数字盘（样本均为表情）/人头/独赢/时长类数字弹幕。**样本不足，不硬造。**（VPS 聚合页 76 条盘口讨论为全天多场混计，不并入本场口径。）

## 5方向性情报板（锚点×共识×灰信号）

今日无方向板章节

## 6情报含义与决策落点（LONG/SHORT）

### 11情报含义与后续观察点（LONG/SHORT 分层 · 弹幕口径，非结论）

- **LONG NAVI（候选）**：若 Rhilech 绝活兑现 + FNC 上单/BP 被针对（「they took rumble from vladi」后观众判 gg），NAVI 中上节奏可能主导；且 NAVI 胜 → KOI 出局剧本（场外排名联动，可作跨场验证锚点）

- **LONG FNC（候选）**：Vladi 5,000 LP 中路压制 + Upset Ezreal 状态 + Soboro 换人红利 → FNC 独赢/2-0 口径偏多（lec 官方频道弹幕方向）

- **风险提示**：当前为「分歧」信号（锚点与共识背离、BP 评价三方不一），且无盘口价格数据可交叉验证价格失真 —— 本场暂不作为方向性操作依据；需等局内兑现 + 盘口/价格对照 + 官方结果三重确认

- **后续观察点**：①Vladi Locke 兑现度；②Poby/SamD 中下短板是否被 FNC 打穿；③NAVI 无前排问题的团战表现；④首杀/一塔/龙魂节奏（S1–S4 事件补录）；⑤赛后自动回填结果 + 预测验证 + 灰信号扫描

## 7逐局复盘（证据层）

## 8队伍 / 人员画像（证据层）

### 4队伍画像（本窗口 + 跨场沉淀）

#### Fnatic · 弹幕画像

- **换血动态（最高价值）**：换上单 Soboro（「之前ig的上单」huya 硕硕 14:58；「换了个骚菠萝之后fnc不一样了」remember 15:13）—— 换人红利叙事

- **状态**：近况被认可（「fnc最近有点猛」remember 15:08；「Les dernières perf d'Upset m'ont convaincu」otplol 15:07）；但常规赛被批「fraud/曲队伍」（「fnc就是曲队伍」硕硕 15:10；「I hope Fnatic don't make it, they have been frauds」caedrel 14:51）

- **核心位**：Vladi 5,000+ LP 中路（法国观众「notre ancien poulain」「comeback de l'année」）＋ Upset 下路数据优于 Carzzy（otplol 15:10）

- **梗文化**：「FnaticGPT」「FNC 剧本/Worlds 觉醒」叙事反复出现 —— 观众口径，非事实

#### NAVI · 弹幕画像

- **短板（本窗口共识度较高）**：「navi n'as pas de mid, ni de bot」（otplol 14:58）；「Navi ont 0 front」（otplol 15:08）；「Navi这个队打团蛆的一批」（硕硕 15:02）—— 中下/前排被点名

- **选手状态**：Poby 与 SamD 被并列为近期下滑（「Poby et SamD sont vraiment en dessous」otplol 14:59）；Rhilech 绝活是主要正面锚点

- **排名联动**：NAVI 胜 → KOI（MKOI）季后赛出局风险（「Of navi wins koi out of playoffs」caedrel 14:55；otplol 15:06/15:10 反复计算 KOI 出线条件）—— 本场场外含义明确

- **长期叙事**：「projet Navi 明年重建」（otplol 14:52 附近，法国观众口径）—— 跨场跟踪点

信任等级：双方画像均来自赛前/BP/第一局开局弹幕，样本窗口短且含大量玩梗 —— 中低置信，仅作方向参考，不作为阵容/状态结论。

### 5人员画像（带提及量，原始文件行级）

| 选手 | 提及量 | 队/角色（弹幕口径） | 主要评价 | 方向 |
| --- | --- | --- | --- | --- |
| Vladi | 53 | FNC 中单（较确凿） | 5,000+ LP（5289）soloQ 压制叙事；Locke 高风险 pick；「comeback of the year」 | 正锚点 |
| Poby | 14 | NAVI 中单（有身份混淆线索） | 「出不了大师」「真让人失望」「le forceur」；与 SamD 并列下滑 | 负锚点 |
| Upset | 13 | FNC 下路 AD | 「欧洲最强 Ez」、数据优于 Carzzy；18 分钟 dash in 玩梗 | 正锚点 |
| Soboro | 5 | FNC 上单（骚菠萝） | 换人后 FNC「不一样了」；「LEC 最强上单」vs「会被点菜/int」分歧 | 分歧 |
| SamD | 5 | NAVI 下路 AD | 「吃满 Seraphine 技能」、与 Poby 并列下滑 | 负锚点 |
| Rhilech | 5 | NAVI 单人线（上/中有歧义） | 绝活锚点：「on his one-trick → NAVI win」「aatrox/zaahen/qiyana=win」 | 正锚点 |
| Zaahen | 4 | NAVI 打野（Nocturne） | 非常规打野组合讨论；draft 期位置仍被观众确认 | 待确认 |
| Canna | 3 | NAVI 上单？（无归属句） | 「被 Oscarinin 世界赛资格赛 gap」历史对照（14:55） | 待确认 |
| Razork | 3 | FNC 打野 | 旧 BO 参照（Wukong 对比 Vladi Ryze） | 参照 |

注：提及量为切片行级计数（含玩梗/转述），角色归属为弹幕推断；FNC/NAVI 辅助位均无具名弹幕 —— 样本不足。

## 9联赛规律与版本（沉淀层）

### 8联赛规律与版本

- **版本/BP 影响（本窗口最有价值发现）**：Viktor 因 LCS Palafox 技能 CD bug 被禁用（otplol 15:00–15:03 多路讨论：「Pas de Viktor, pas de R !」「Même en LEC? Sadge」「Viktor disabled」）—— 直接影响 Vladi 的中路英雄池预期与 BP（「they took rumble from vladi」后观众即时判 gg）

- **LEC 常规赛末段联动**：本场结果直接影响 top4/季后赛与 KOI（MKOI）出线（「Of navi wins koi out of playoffs」caedrel 14:55；「Il faut supporter NAVI si on veut espérer que KOI soit OUT du TOP 6」otplol 15:06）—— 排名博弈是观众讨论主线之一

- **换人叙事**：FNC 换 Soboro 后「不一样了」（remember 15:13）；NAVI「明年重建」叙事（otplol）—— 两条跨场可跟踪的队伍动态

- **观众梗文化**：FNC「剧本/Worlds 觉醒」「FnaticGPT」梗反复出现 —— 玩梗，不计入信号（按甄别纪律）

## 10预测验证回填明细（沉淀层）

### 9预测验证（框架 · 赛后回填）

以下均为赛前/BP 期弹幕预测，当前全部「待定」，赛后按结果逐条回填。

| 预测（弹幕口径） | 时间 | 验证状态 |
| --- | --- | --- |
| FNC 2-0（系列比分） | 15:00–15:10（lec 多条） | 待定 |
| NAVI 2-0（系列比分） | 14:50–14:57（caedrel 多条） | 待定 |
| 打满 2-1（FNC 微弱优势） | 14:59（lec） | 待定 |
| Rhilech 绝活 → NAVI 赢 | 15:05（lec） | 待定 |
| Soboro 被点菜 / int（FNC 输因） | 15:06（caedrel 单条） | 待定 |
| NAVI 无前排 / 中下短板 → 局内劣势 | 14:58–15:08（otplol/硕硕） | 待定 |
| Vladi 5,000 LP 中路压制 | 15:00–15:10 | 待定 |

## 11数据与溯源

### 12数据与溯源 / 可验证情报痕迹

### 数据源

- 切片：data/intel_slices/lol-navi-fnc-2026-08-24.jsonl（5,916 条，2026-08-24 14:49:57–15:11:01 UTC）

- 规则层：runtime/vps_intel/lol-navi-fnc-2026-08-24_intel.json（meta.total=5,916、active_users=1,879、gray_signals.count=0）

- 会话：runtime/danmu_sessions/vps_2026-08-24/（state=running，采集 09:45–15:11 持续运行）

- 交叉源：docs/data/danmu/huya/2026-08-24_huya_shuoshuo.jsonl（硕硕）、…_huya_remember.jsonl（窗口外 15:13 仍在第一局）

### 结果来源（为什么写「未结束」）

- 弹幕比分牌 14:53/15:02/15:05 均为「FNC 0-0 NAVI // GX 0-0 G2」—— 系列比分未动

- tools/verify_match_end.py 对 15:03 候选结束评分 **2/4（需人工确认）**，未达 ≥3 结束门槛

- 本地官方库 docs/data/intel/official/official_matches.json 无本场记录；沙箱无外网，Polymarket 结算/战报站待联网回填

- 「gg」「1-0 navi」「1-0 fnc」「FNC赢了」（硕硕 15:09:54）均出现在 BP/第一局开局窗口且与后续口径矛盾（「这把FNC赢不了」15:13）—— 判为预测/玩梗，按语言甄别纪律不计入结果

### 可验证情报痕迹（赛后回填清单）

| 痕迹 | 内容 | 回填项 |
| --- | --- | --- |
| BP 针对信号 | Vladi 的 Rumble 被封锁 → 观众即时判 gg（15:03） | 该局 FNC 胜负/BP 兑现 |
| 高风险 pick | FNC Locke（Vladi）「赢下整局或输掉整局」（15:03–15:04） | Locke 局内表现 |
| 熟练度锚点 | Rhilech one-trick → NAVI win（15:05）；Vladi 5,000+ LP（15:00–15:10） | 两位选手本局表现 |
| 换人叙事 | FNC 换 Soboro 后「不一样了」（15:13） | 跨场队伍画像更新 |
| 排名联动 | NAVI 胜 → KOI/MKOI 出局风险（14:55 起多路） | 赛后积分榜验证 |
| 版本事件 | Viktor 因 LCS bug 被禁用（15:00–15:03 多路共振） | 版本/BP 记录入库 |
| 词表缺口（防错项） | 规则层 intel.json 团队表**无 FNC/Fnatic 键**（NAVI 69 条已捕获），原始行级 FNC 235 条被静默漏计 | 词表补 FNC/Fnatic + 回归测试（防错规则 7） |

### 待确认项

- 比赛终局结果（官方确认后回填）与系列比分；官方首发名单（上单 Canna 归属、Rhilech/Zaahen 位置、双方辅助）

- Polymarket 事件 lol-navi-fnc-2026-08-24 结算价（需联网）

- 灰信号、盘口数字、BP 后战绩情报：当前窗口无数据，继续监控后续切片

> 本页为 A 型整场复盘骨架的局中快照（模板二.5：B=A 的进行中快照）。比赛终局后，请基于完整切片重跑本模板生成终态页（含结果总览、逐局、预测验证回填），并同步结构化库（matches/teams/players/gray/bp/leagues）、报告索引与 DANMU_INTEL 知识库。

> 生成依据：knowledge/INTEL_HTML_TEMPLATE.md（A 型 10 段 + 方向性情报二.8）· knowledge/LIVE_INTEL_SCHEMA.md · knowledge/VERIFICATION_METHODOLOGY.md · skills/intel-report 与 result-verification。样式：SAP/Apple（#f5f5f7 浅底、白卡、单一强调色 #0071e3、系统字体栈）。数据全部可溯源，无样本处标注「样本不足」，未硬造。

v2 决策导向重排 · 弹幕口径 · 灰信号仅为观众质疑非结论 · 由 tools/reformat_intel_template.py 生成
