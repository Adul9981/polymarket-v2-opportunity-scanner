# 弹幕情报标准工作流（SOP · 最高优先级成果项）

最后更新：2026-08-24

定位：虎牙/SOOP 弹幕「监控 → 情报 → 复盘 → 入库」的**标准操作手册**。
任何会话接手弹幕任务，先读本文件 + `knowledge/DANMU_README.md`（总索引）+
`knowledge/DANMU_CAPTURE_RULES.md`（规则红线），再按本 SOP 执行。
本工作流是 TASK6 情报库的 A 级成果项：可标准化、可接力、可复盘验证。

> 阶段 3（实时情报）与阶段 4（完整复盘）分工见 knowledge/REVIEW_SCHEMA.md：
> 实时情报是盘中 60s 快照（供判断），完整复盘是赛后终态沉淀（供积累）；
> 复盘必须按 REVIEW_SCHEMA 的章节结构 + matches.json 字段产出，不复盘则数据停在过程层。
> 局中情报按 knowledge/LIVE_INTEL_SCHEMA.md 的章节 + 比赛阶段（S0 选人/S1 对线/
> S2 资源/S3 中期/S4 终局）递进输出，并引用选手/队伍/联赛的隐性画像数据。

## 工作流总览（五阶段）

```text
阶段0 开赛前准备   -> 阶段1 启动会话   -> 阶段2 运行监控
                   -> 阶段3 情报输出   -> 阶段4 复盘入库
                   -> 阶段5 交接接力（跨会话）
```

## 阶段 0：开赛前准备（每次比赛前必做）

```text
1. 读档：knowledge/DANMU_README.md、DANMU_CAPTURE_RULES.md、DANMU_WORKFLOW.md（本文）；
   跨会话先 diff 最近文件（find runtime/danmu_sessions docs/data/danmu -mtime -2）。
2. 登记直播间：新直播间先写入 docs/data/danmu/streamer_registry.json（平台/房间号/uid/
   关注赛事/采集状态），并同步 knowledge/STREAMER_PROFILES.md；未登记不启用。
3. 确认赛事与词表：联赛先登记 LEAGUE_PROFILES/watchlist 词表（防静默漏抓）；
   新增队伍/选手补词表并回归。
4. 检查房间状态：curl 房间页确认 isOn/introduction（识别当前比赛与转播计划）。
5. **多路同抓（2026-08-24 固化，最高优先级）**：任何比赛一旦确认开播，
   必须把"该联赛/赛事已登记的所有直播间"全部加入采集会话，禁止只抓
   发现比赛的单一平台/单一房间。弹幕越多越全，交叉验证越可靠。
   参考口径：联赛级默认采集集合见 docs/data/intel/leagues.json 的
   platforms/streamers 字段（如 LEC = Twitch caedrel/lec + 虎牙 毛毛/Remember/硕硕）。
```

## 阶段 1 补充：多路同抓清单（2026-08-24）

```text
比赛确认后，按联赛查 leagues.json 的 streamers 清单，全部 isOn 的直播间
一次性加入 run_danmu_session --room（跨平台可混用：huya/soop/twitch/kick）。
已登记默认集合（2026-08-24）：
  LEC    -> twitch: caedrel, lec ; huya: 毛毛(149346), Remember(528222), 硕硕(323444)
  LCK    -> huya: 957(890001), 毛毛(149346), 米勒(149361), Remember(528222), 硕硕(323444)
  LCK CL -> soop: afchall(296450537)
  CS2    -> huya: CSBOY(123321), CSBOY-Mo(321123) ; kick: eslcs, gaules, esportsworldcup
  LPL    -> huya: 官方(660000), 957(890001), 毛毛(149346), 米勒(149361), Remember(528222), 硕硕(323444)
监控会话按比赛组织：同一场比赛的所有房间放同一 session（intel.json 聚合），
便于交叉验证与赛后复盘；勿按平台拆 session（教训：FNC-NAVI G1 曾只抓 Twitch）。
```

## 阶段 1：启动会话（首选 run_danmu_session.py）

```text
命令：
  /tmp/intel-whisper-venv/bin/python tools/run_danmu_session.py \
      --session <赛事日期标识> --title "<标题>" \
      --room <源名>=<房间URL> [--room ...]
产出（自动）：
  - 每房独立 JSONL：docs/data/danmu/huya/<日期>_<源>.jsonl
  - 每房健康状态：runtime/danmu_sessions/<session>/<源>.status.json
  - 聚合情报：reports/intel_danmu_live_<session>.html（60s 刷新）
  - 机器可读情报：runtime/danmu_sessions/<session>/intel.json
  - 会话清单：runtime/danmu_sessions/<session>/session.json（接力用）
自检：启动后 60s 内确认各房弹幕 >0 且 intel.json 的 sources 全绿；
  0 条/假死必须告警排查（先怀疑工具，见 CAPTURE_RULES 防错）。
```

## 阶段 2：运行监控

```text
1. 定期（60s）检查 intel.json：total 增长、sources 状态、capture_health；
   断线自动重启由会话托管，完整性受影响要记录。
2. 关键节点（BP 落定/团战/翻盘/灰信号爆发）出局间小结（可复用复盘模板）。
3. 灰信号：只作聚合风险标注与盘口对照素材，不作假赛结论（纪律红线）。
4. 按比赛维度组织：一场比赛（含多小局）是处理单元；小局切换（G1->G2）不换比赛，
   只换局标签；新对阵才开新比赛切片（见 CAPTURE_RULES 第 11 节）。
```

## 阶段 3：情报输出

```text
聚合页（intel_danmu_live_<session>.html）必须覆盖：
  队伍情报 / 选手状态 / BP 与局势 / 盘口讨论 / 灰信号 / 高价值用户 / 弹幕密度峰值；
并按 knowledge/LIVE_INTEL_SCHEMA.md 组织：头部标当前阶段（S0-S4）+ 阶段进度，
选手章节引用近期画像（players.json），BP 章节含阵容评价与版本符号，
局势按阶段标签递进；未知项写"待观察/样本不足"。
无样本不硬撑（显示"样本不足"），无信号不硬造（显示"今日无信号"）。
如需逐房深挖，用 danmu_intel.py / danmu_report.py 补逐房报告。
比赛维度切片：tools/slice_danmu_by_match.py --manifest docs/data/danmu/slices/manifest.json，
一场比赛一个切片目录（all.jsonl + 可选 game_N.jsonl），窗口见清单；
会话跨多场时按比赛逐个挂切片，不清空会话级原始 JSONL。
5. 观众预测记录（闭环 v2，2026-08-23）：出现明确观众预测（胜负共识 / BP 判负 /
   盘口方向）时，立即 tools/record_prediction.py --match-id <id> --text "<预测>"
   --category result|bp|odds --status pending 落库 matches.json predictions[]
   （字段契约见 knowledge/INTEL_OUTPUT_TIMELINE.md 五）；灰信号 / 盘口锚点同步记录。
```

## 情报输出节点规范（Node Spec · 2026-08-22 定稿，最高优先级）

> 定位：比赛情报不是"一条线"，而是**系列层（BO3 整场）× 局层（每一小局）**的双层结构。
> 系列层负责"方向"（谁赢/打几局/有没有剧本），局层负责"时机"（BP 锚点/事件/灰信号在哪一刻爆发）。
> 每个节点自动触发，用户不必每次提醒；用户在旁只是补充/修正。

### 一、双层结构

```text
系列层（BO3 整场）
├── S0｜赛前｜PRE-MATCH         开赛前 30-15 分钟（整场只做一次）
├── 局层循环 ×3（每一局都有一套完整节点）
│    ├── PRE｜局前｜PRE-GAME     承接上一局结束的系列状态（G1 复用 S0）
│    ├── BP｜BP 锁定｜BP-LOCK    选人落定后 1-3 分钟（每局必做，黄金窗口）
│    ├── OPEN｜开局｜OPENING     开局 5-10 分钟验证
│    ├── LIVE｜局中｜IN-GAME     关键事件/灰信号爆发
│    └── END｜局结束｜GAME-END   归入系列层局间节点
└── FINAL｜系列复盘｜SERIES-REVIEW  整场结束 15 分钟内
```

> 命名约定（全项目统一）：每个节点 = **简码｜中文名｜英文名**，
> 例如 `G1-BP｜BP 锁定｜BP-LOCK`。情报页标题、速报开头、库字段统一带中英文，
> 读起来一目了然，维护成本不增加。

### 二、系列层节点（方向层，4 个）

```text
S0｜赛前｜PRE-MATCH：
  触发：开赛前 30-15 分钟；版本：V0 速报 + V1 简页。
  必含：首发/换人、队伍状态、排名博弈、历史对战、初盘对照、灰信号先验。
  价值：提前埋伏（如"GEN 锁第一后的无意义局风险""IG 控分动机"）。

G1-END｜第一局结束｜GAME1-END：
  触发：G1 结算后 5 分钟内；版本：V0 速报（必）+ V1 局间页（必）。
  必含：G1 结果与关键进程、灰信号验证（被疑方输了没？）、"横扫/给一盘/
  让一追二"判断、G2 前瞻（变阵/BP 调整预期）。
  价值：系列盘重定价窗口（全系列第二高）。

G2-END｜第二局结束｜GAME2-END：
  触发：G2 结算后 5 分钟内；版本：V0 速报（必）+ V1 局间页（必）。
  必含：系列状态（2:0 或 1:1）、横扫 vs 决胜局预期、控分/剧本叙事升级、
  决胜局 BP 前瞻。
  价值：决胜局预期成形。

FINAL｜系列复盘｜SERIES-REVIEW：
  触发：整场结束 15 分钟内；版本：V1 A 型复盘 + V2 库沉淀。
  必含：逐局复盘、预测验证、灰信号兑现率回填、队伍/选手/联赛画像更新、
  情报库同步（matches/gray/entities/teams/players/leagues + 索引 + 知识库）。
  自动闭环（闭环 v2，2026-08-23）：回填 predictions hit/miss ->
   tools/publish_closed_loop.py --match-id <id> --push 自动生成并发布闭环页。
  价值：学习价值（价格已结算），供下一场做先验。
```

### 三、局层节点（时机层，每局 5 个，共 15 个触发点）

```text
每局节点命名：<局号>-<节点名>｜中文名｜英文名，
如 G1-BP｜BP 锁定｜BP-LOCK / G2-PRE｜局前｜PRE-GAME / G3-LIVE｜局中｜IN-GAME /
G1-END｜第一局结束｜GAME1-END（局末归系列层）。

PRE｜局前｜PRE-GAME：
  触发：本局 BP 前（G1 复用 S0；G2/G3 为局间前瞻）；版本：并入局间 V1。
  必含：上一局复盘要点、变阵/换人预期、本局方向判断。

BP｜BP 锁定｜BP-LOCK：
  触发：选人落定后 1-3 分钟（黄金窗口）；版本：V0 速报（≤3 分钟，必）。
  必含：双方阵容、BP 后战绩情报（选手×英雄历史战绩/胜率，正负锚点）、
  BP 判负/判胜共识、异常选角与 ban、BP 灰信号。
  价值：全系列最高（市场尚未重定价）。

OPEN｜开局验证｜OPENING：
  触发：开局 5-10 分钟；版本：V0 增量速报（只报变化）。
  必含：BP 锚点应验/打脸（如"掘墓打杰斯是否真压不住"）、对线/初节奏。

LIVE｜局中事件｜IN-GAME：
  触发：密度峰值/关键节点（大龙团、翻盘、灰信号爆发、盘口词）；版本：V0 事件速报。
  必含：事件类型、灰信号（做局质疑/穿盘/收米/水位不动）、翻盘信号、密度峰值。
  价值：反转交易（N3 只给风险标注，不下结论）。

END｜局结束｜GAME-END：
  触发：本局结算；处理：归入系列层 G1-END / G2-END / FINAL，不单独出页。
```

### 四、三局侧重（同节点、不同权重）

```text
G1：BP 信息增量最大（首次暴露阵容，战绩情报最重要）；局中灰信号初现。
G2：局前看"调整与反制"（谁变阵谁头铁，"第二局给一盘"剧本观察）；
    BP 带 1:0/0:1 背景（横扫预期 vs 扳平预期）；灰信号延续/转向。
G3：局前看"决胜局前瞻"（心态/底牌/控分与让一追二叙事验证）；
    BP 为灰信号最高浓度节点（决胜局做局/控盘叙事最密集）；事件密度最高。
```

### 五、输出版本（3 层）

```text
V0 速报（≤2 分钟，≤5 条，可直接交易）："BP 已锁：X 选 Y，历史 7-0，观众判负"；
  "G1 结束：X 拿下，'2-0没悬念'共识"；"灰信号爆发：XX 被指剧本+低水"。
V1 结构化情报页（B 型局中/A 型复盘，10 段标准模板）：决策存档与深挖。
V2 情报库沉淀：matches/gray/entities/teams/players/leagues + 兑现率统计，供先验。
用户说"快速输出"= V0；说"输出情报/复盘"= V1；比赛结束自动 V2。
```

### 六、SLA 与纪律

```text
SLA：BP 锁定速报 ≤3 分钟；G1/G2 结束局间页 ≤5 分钟；系列复盘 ≤15 分钟；
  局中事件速报在峰值出现后 2 分钟内。
纪律：每个节点带置信标注（结果类尤其，低样本标"待确认"）；灰信号只标注不下结论；
  数据断档（采集中断/未录制）必须显式记录，不因自动而省略。
```

### 七、阶段自适应输出（用户中途要情报时）

```text
规则：用户在任何时刻说"输出情报/看看情况"时，先判断比赛当前到哪个节点/阶段，
再按"当前优先 + 前面补齐"分批交付，不需要等完整流程：
1. 定位：识别当前是第几局、处于哪个阶段（PRE/BP/OPEN/LIVE/局间/终局）；
2. 先出当前阶段情报（V0 速报或对应段）：BP 就出 BP 情报，局中就出局势+密度+
   灰信号，局间就出系列状态；
3. 再补齐前面已发生但重要的情报（分批发）：
   - 本局 BP 与 BP 后战绩情报（正负锚点）——即使比赛已进行一半仍有决策价值；
   - 已发生的局中关键事件（翻盘/大龙/灰信号爆发/盘口词）；
   - 上一局结果与系列状态（若已结束小局）；
4. 输出顺序 = 当前节点 → 前面关键情报 → 后续观察点；每条标时间戳与置信；
5. 若数据断档，明说"该段未采集"，不硬补。
例：比赛进行到 G2 中段时用户要情报 →
  先给 G2-LIVE（当前局势/灰信号），再补 G1-BP 战绩情报与 G1-END 系列状态，
  最后给 G2-END 前瞻观察点。
```

## 阶段 4：复盘入库（比赛结束必做）

```text
0. 自动触发（2026-08-20 最高准则）：检测到比赛结束（多信号校验通过）即自动
   进入本阶段，不等用户指示；用户在旁只是补充/修正，不是触发条件。
1. 停会话（Ctrl-C，自动写 session.json state=stopped）。
2. 整场复盘 HTML（SAP/Apple 风格，reports/intel_*_full_*.html）——
   必须按 knowledge/REVIEW_SCHEMA.md 的章节结构（逐局复盘/队伍画像/人员画像/
   灰信号/联赛规律/预测验证/盘口/情报含义/溯源），含结果推断
   （标注"弹幕推断，待官方确认"）。
   复盘按比赛维度组织：一场比赛一个复盘，games[] 逐局沉淀（BP/时间线/转折/
   异常/预测验证）；局间切换不拆成多个复盘。
3. 同步结构化情报库（docs/data/intel/）：
   matches.json（按 REVIEW_SCHEMA 字段：games/teams_intel/players_intel/
   gray_signals/league_patterns/prediction_validation 等）、teams.json、players.json、
   users.json（高价值用户）、gray_signals.json、gray_entities.json（灰信号主体留痕库，
   先于 gray_signals 更新）、bp_signals.json / bp_entities.json（BP 情报）、
   leagues.json（联赛规律）；所有记录打 memory_tier（LONG/SHORT）。
4. 知识库文档：DANMU_INTEL.md 追加批次、TEAM_PROFILES/USERS 更新。
5. 报告索引 reports/intel_danmu_index.html 挂新报告。
6. 可验证项回填：BP 判负、灰信号、预测、盘口讨论的验证结论写入对应库
   （bp_signals.verdict / gray_signals / prediction_validation），并统计命中率。
7. 预测回填 + 闭环页（闭环 v2，2026-08-23）：
   - tools/record_prediction.py --status hit|miss 逐条回填 predictions[]；
   - tools/publish_closed_loop.py --match-id <id> --push
     一键生成闭环页（读 predictions，无歧义、无需人工复核）并推送到
     danmu-intel 站点（intel/closed_loop_<id>.html）；首页"闭环样例 / 闭环统计"同步更新。
```

## 阶段 5：交接接力（跨会话）

```text
1. 新会话先读 runtime/danmu_sessions/<session>/session.json（state/rooms/报告路径），
   再读 intel.json 续上进度；不要从零重来。
2. 会话目录保留：停止后勿删（历史证据 + 接力依据）。
3. 若有数据缺口（如早期未抓段），用 SOOP VOD 回捞（fetch_soop_vod_chat.py）补。
```

## 常见故障与修复（先怀疑工具）

```text
1. "房间页缺少 profileRoom/lChannelId"（2026-08-19 已修）：
   fetch_room_info 曾抓 m.huya.com 移动页但检查桌面页字段 profileRoom；
   修复：改抓 www 桌面页 + room_id 回退 channel_id。遇同类报错先 curl 页面
   看字段是否存在，再决定改工具还是页面真的失效。
2. 0 条弹幕/连接假死：查 status.json 的 state/warning，禁止直接报"无弹幕"；
   会话托管自动重启，重启后补记完整性。
3. 词表静默漏抓：新增队伍/选手必须补词表并回归（如 KC/GX/Canna）。
```

## 输出规范（通用约定）

```text
- HTML 一律 SAP/Apple 风格（浅底 #f5f5f7、白卡、单一强调色、系统字体栈）。
- 韩文弹幕先中文化再展示；对外只展示聚合结论与统计，不裸展示弹幕流与用户身份。
- 灰信号标注"观众质疑，非结论"。
- git 默认不提交不推送（用户显式要求才做）。
```
