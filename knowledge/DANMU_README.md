# 弹幕情报体系总索引（情报库平台 · 主观数据源）

最后更新：2026-08-24

定位：虎牙/SOOP/Twitch/KICK 直播弹幕是情报库平台（TASK6）的**主观情报数据源**——
与解说信号、评论数据并列，提供"观众集体智慧"层。本文件是弹幕情报的
总入口，把所有工作串成一条链：抓取 → 监控 → 分析 → 画像 → 复盘 → 平台。
SOOP（前 AfreecaTV，sooplive.com）为韩语平台，LCK_CL 频道直播 LCK 二线
联赛（LCK CL），2026-08-18 已打通实时弹幕与 VOD 历史弹幕回捞两条链路。
Twitch（2026-08-24）匿名 IRC 直连英文/多语官方流与高流量二路（Caedrel）。
KICK（2026-08-24）Pusher WS 匿名直连 CS2 赛事（IEM/ECL/EWC 官方 + Gaules 二路）。

## 完整链路

```text
直播弹幕（虎牙 / SOOP / Twitch / KICK）
  -> tools/fetch_huya_danmu.py 抓取（JSONL 落盘 docs/data/danmu/<博主>/）
  -> tools/fetch_twitch_danmu.py Twitch 匿名 IRC 实时弹幕（零依赖）
  -> tools/fetch_kick_danmu.py KICK Pusher WS 实时弹幕（匿名直连）
  -> tools/run_danmu_session.py 多房间持续会话（健康检查/告警/自动重启/聚合情报）
  -> tools/fetch_soop_danmu.py SOOP 实时弹幕（含自动重连）
  -> tools/fetch_soop_vod_chat.py SOOP 回放历史弹幕回捞（VOD 生成后）
  -> tools/danmu_live_monitor.py 实时监控（5 分钟刷新 HTML，页面自动刷新）
  -> tools/danmu_intel.py 情报提炼（队伍/选手/盘口/局势/灰信号/密度峰值）
  -> tools/slice_danmu_by_match.py 比赛维度切片（一场比赛=处理单元，可含多小局）
  -> tools/danmu_report.py HTML 简报 / 整场复盘
  -> tools/record_prediction.py 观众预测落库（matches.json predictions[]，闭环 v2）
  -> tools/build_closed_loop.py 闭环页生成（预测 -> 结果 -> 命中/落空，自动流水线）
  -> 画像沉淀：TEAM_PROFILES.md（队伍）/ DANMU_USERS.md（高价值用户）
  -> 知识库：DANMU_INTEL.md（情报汇总）/ DANMU_CAPTURE_RULES.md（规则）
  -> 平台衔接：TASK6 情报库（弹幕为数据源，集体智慧信号为功能点）
  -> 交易衔接：DANMU_POLYMARKET_ROADMAP.md（弹幕×行情对照，分阶段推进）
```

## 标准工作流（SOP · 最高优先级成果项）

```text
任何会话接手弹幕任务，先读 knowledge/DANMU_WORKFLOW.md（五阶段 SOP）：
  阶段0 开赛前准备（读档/登记直播间/词表）
  -> 阶段1 启动会话（run_danmu_session.py，每房独立落盘+健康+自动重启）
  -> 阶段2 运行监控（intel.json 健康检查，灰信号纪律）
  -> 阶段3 情报输出（聚合 HTML：队伍/选手/BP/盘口/灰信号/高价值用户）
  -> 阶段4 复盘入库（整场复盘 + docs/data/intel/ 结构化库同步）
  -> 阶段5 交接接力（session.json / intel.json）
```

## 文件地图

### 数据

```text
docs/data/danmu/shuoshuo/2026-08-17_323444.jsonl  （TH vs Navi 场，2262 条）
docs/data/danmu/shuoshuo/2026-08-18_323444.jsonl  （KC vs GX 场，1903 条）
docs/data/danmu/soop/2026-08-18_afchall_296450537.jsonl
                     （SOOP LCK_CL DNS vs NS 实时弹幕，174 条，断连后已加自动重连）
docs/data/danmu/soop/vod_20260811_NS-DK_sample.jsonl
                     （SOOP 回放历史弹幕样例：NS vs DK 第 1 小时，1109 条）
docs/data/danmu/huya/2026-08-18_890001.jsonl
                     （957 直播间实测样本，8 条含 uid）
docs/data/danmu/huya/2026-08-19_official_660000.jsonl
                     （08-19 官方赛事流全天，约 12,500 条，WBG-LNG/TES-AL 段）
docs/data/danmu/huya/2026-08-19_mile_149361.jsonl
                     （08-19 米勒直播间，约 5,900 条，GEN-KT/TES-AL 段）
docs/data/danmu/huya/2026-08-19_remember_528222.jsonl
                     （08-19 记得直播间，约 2,900 条）
docs/data/danmu/soop/2026-08-18_296450537.jsonl
                     （并发工具 15s 实测样本，与 174 条主文件互补）
docs/data/danmu/soop/2026-08-19_carrylck_296474407.jsonl
                     （08-19 DNS vs BRO 场，20 条，采集中断样本不足）
docs/data/danmu/streamer_registry.json
                     （直播间注册表：虎牙 4 房 + SOOP LCK_CL，数据库留档）
docs/data/intel/
                     （结构化情报库：leagues/teams/players/matches/users/gray_signals，
                       gray_entities（灰信号主体留痕库：凡走过必有痕迹，涉事队伍/选手
                       重点标记，再犯自动升级；teams/players 同步 gray_history），
                       bp_signals（BP 异常信号留痕：单场 BP 判负/判胜+赛后验证）、
                       bp_entities（BP 环节主体留痕：教练优先，再犯升级），
                       每场分析后同步更新，长期积累的集体智慧数据层）
```

### 工具

```text
tools/fetch_huya_danmu.py    实时弹幕抓取（WebSocket，断线重连，持续模式）
tools/fetch_soop_danmu.py    SOOP 实时弹幕抓取（二进制聊天协议，自动重连）
tools/fetch_twitch_danmu.py  Twitch 匿名 IRC 实时弹幕（零鉴权、零依赖、标准库）
tools/fetch_kick_danmu.py    KICK Pusher WS 实时弹幕（匿名直连；key 会轮换，见 KICK 文档）
tools/fetch_soop_vod_chat.py SOOP 回放历史弹幕回捞（ChatLoadSplit 分片翻页）
tools/fetch_danmu_multi.py   多直播间并发抓取（虎牙 + SOOP + Twitch + KICK 统一入口）
tools/run_danmu_session.py   生产级多房间持续监控（推荐入口，含健康状态与聚合输出）
tools/danmu_intel.py         情报提炼（含 analyze_deep 深度主题分析）
tools/danmu_live_monitor.py  实时监控（每 5 分钟刷新 HTML）
tools/danmu_report.py        弹幕数据 -> HTML 简报
```

### 文档（知识库 + 规划）

```text
knowledge/DANMU_CAPTURE_RULES.md   抓取规则与交易模式（新会话必读）
knowledge/DANMU_WORKFLOW.md        标准工作流 SOP（五阶段，最高优先级成果项）
knowledge/REVIEW_SCHEMA.md         整局完整复盘标准（章节结构 + 字段 Schema）
knowledge/LIVE_INTEL_SCHEMA.md     局中实时情报标准（章节 + 比赛阶段 Schema）
knowledge/DANMU_INTEL.md           弹幕情报汇总（每场记录）
knowledge/DANMU_USERS.md           高价值弹幕用户档案
knowledge/STREAMER_PROFILES.md     虎牙博主档案（957/毛毛/米勒/硕硕）
knowledge/TEAM_PROFILES.md         队伍画像（弹幕情报沉淀处）
knowledge/SOOP_NOTES.md            SOOP 平台抓取说明（协议/接口/已验证样例）
knowledge/TWITCH_CAPTURE_RESEARCH.md  Twitch 平台调研（IRC 实测/频道清单/采集方式）
knowledge/KICK_CAPTURE_RESEARCH.md    KICK 平台调研（Pusher WS 实测/CS2 频道清单）
knowledge/PLATFORM_ONBOARDING_METHODOLOGY.md  新平台接入六步法（通用 SOP）
docs/task/DANMU_POLYMARKET_ROADMAP.md  弹幕×Polymarket 对接路线图
docs/task/INTEL_SIGNAL_LIBRARY_PLAN.md 主观情报库建设方案
docs/task/TASK6_INTELLIGENCE_LIBRARY_PRODUCT.md  情报库平台框架
knowledge/VERIFICATION_METHODOLOGY.md 结果校验自主化方法论（默认自主不反问）
knowledge/BP_INTEL.md BP 情报方法论（选人即情报：熟练度/教练责任/假赛视角/闭环）
knowledge/MEMORY_TIERS.md 情报分层机制（长期/短期/瞬时：价值时效管理）
knowledge/INTEL_HTML_TEMPLATE.md 情报 HTML 标准模板（整场复盘/局中深度/画像三类，标杆示例）
knowledge/INTEL_TEMPLATE_HANDOFF.md 模板移交规格（供线上情报库工具参考实现：12 段结构/层级/多语言/门禁）
docs/task/SKILLS_PLAN.md Skills 拆分规划（capture/intel/report/verification/library-sync/gray-tracking）
```

### 报告（HTML）

```text
reports/intel_danmu_index.html                        报告索引页（平台入口）
reports/intel_danmu_live_lpl_lck_2026-08-19.html      08-19 全天实时聚合（3 路并发，运行中）
reports/intel_danmu_TES-AL_2026-08-19.html            08-19 TES vs AL 整场（官方确认 2:1）
reports/intel_danmu_GEN-KT_2026-08-19.html            08-19 GEN vs KT 整场（官方确认 2:1）
reports/intel_danmu_WBG-LNG_2026-08-19.html           08-19 WBG vs LNG 整场（官方确认 2:1）
reports/intel_danmu_alerts_LNG-WBG_2026-08-19.html    08-19 LNG vs WBG 灰信号警报页
reports/intel_danmu_DNS-BRO_2026-08-19.html           08-19 DNS vs BRO（SOOP，样本不足）
reports/intel_danmu_2026-08-17_323444.html            08-17 简报
reports/intel_danmu_full_2026-08-17_323444.html       08-17 TH vs Navi 完整复盘
reports/intel_danmu_live_KC-GX_2026-08-18.html        08-18 实时监控（进行中页面）
reports/intel_danmu_KC-GX_G1_2026-08-18.html          08-18 第一局小结
reports/intel_danmu_KC-GX_full_2026-08-18.html        08-18 KC vs GX 整场复盘
reports/intel_danmu_DNS-NS_G1_2026-08-18.html         08-18 DNS vs NS K杯 G1
reports/intel_danmu_DNS-NS_G2_2026-08-18.html         08-18 DNS vs NS K杯 G2
reports/intel_soop_GGA-BRO_2026-08-18.html            08-18 GGA vs BRO LCK CL 速报
reports/intel_soop_DNS-NS_G1_2026-08-18.html          08-18 SOOP LCK CL DNS vs NS 第一局小结
```

## 标准工作流（每场比赛）

```text
1. 多直播间比赛优先启动 tools/run_danmu_session.py（内部统一拉起采集器和聚合监控）
2. 单直播间调试才分别启动 fetch_huya_danmu.py + danmu_live_monitor.py
3. 局间/关键节点 -> 出局间小结（可选）
4. 比赛结束（弹幕大量 888/88/晚安 + 数据停止增长）-> 停抓、停监控
5. 整场复盘 HTML + 更新 DANMU_INTEL.md / TEAM_PROFILES.md / DANMU_USERS.md
```

## 持续会话接力（新会话先看）

```text
状态中枢：runtime/danmu_sessions/<session>/session.json
实时情报：runtime/danmu_sessions/<session>/intel.json
聚合页面：reports/intel_danmu_live_<session>.html
原始数据：docs/data/danmu/<platform>/<日期>_<source>.jsonl

session.json.state=running 时先检查 updated_at 与各房间 heartbeat_at，禁止重复启动同一 source。
页面开播但超过阈值无弹幕 -> live_no_danmaku_alert；采集器异常退出 -> 自动重启并累计 restart_count。
任何 0 条结果都先看健康状态，只能写“样本不足/采集异常/未开播等待”，不能写“无信号”。
```

## SOOP（LCK CL）工作流

```text
1. 直播中 -> tools/fetch_soop_danmu.py --url https://play.sooplive.com/<bj>/<broad_no>
   （只取弹幕文本/用户 ID/昵称，不碰视频；断线自动重连、续写同一 JSONL）
2. 想回捞比赛开始以来的完整弹幕 -> 等整场直播结束、VOD 生成后，
   tools/fetch_soop_vod_chat.py --bj afchall --title-no <broad_no> --out ...
   （按 5 分钟分片翻页拉取全量历史弹幕，含 VOD 内时间戳，可切出第一局等时段）
3. 韩文弹幕 -> 分析阶段做翻译/词表（韩文队伍选手名，如 농심=NS）
```

## 与情报库平台（TASK6）的衔接

```text
数据源：弹幕数据登记为平台"主观情报"数据源（见 TASK6 文档第 6 节）。
功能点：
  1. 集体智慧信号（灰信号聚合：质疑条数 + 卡盘数字重合度）
  2. 弹幕密度峰值 = 比赛关键时刻（事件时间线）
  3. 高价值用户观点（DANMU_USERS.md 跟踪）
  4. 队伍/选手微观画像（喂 TEAM_PROFILES / 平台画像卡）
对外展示原则：只展示聚合结论与统计，不裸展示弹幕流与用户身份。
```
