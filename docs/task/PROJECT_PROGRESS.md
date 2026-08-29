# 预测市场网格交易项目进度库

最后更新：2026-08-19

## 1. 使用方式

这个文件用于管理项目分阶段推进，不承载完整策略细节。

状态定义：

```text
未开始：还没有正式实施。
进行中：已经开始开发或验证，但还没有稳定闭环。
待验收：核心功能已完成，等待真实案例验证。
已完成：通过验收标准，可以进入下一阶段。
暂停：方向暂不推进，保留记录。
```

推进原则：

```text
每完成一个阶段，先更新本文件。
只有验收标准通过后，才进入下一阶段。
实盘相关能力优先本地运行，不把私钥交给网页托管服务。
产品设计和交易执行分会话管理：本会话负责策略和产品，执行专用会话负责低上下文交易操作。
新策略按成熟度推进：观察 -> 建议 -> 模拟 -> 小额实盘 -> 稳定实盘。
分类体系按两层管理：先记录市场现象，再构建交易策略；执行管理模块单独管理。
```

## 2. 当前总览

```text
任务 1：手动输入链接，系统生成交易计划并执行        已完成
任务 2：自动扫描比赛列表，给出机会排名              待验收
任务 3：纠缠指数上线，自动标记主策略和辅助标签        未开始
任务 4：半自动交易台，用户点确认后执行              未开始
任务 5：全自动小金额试运行，带风控和复盘            未开始
任务 6：电竞交易情报库（订阅制网站）                进行中 · 高优先级
任务 7：交易者拆解与可复制策略沉淀（e46m3）          进行中
V2 执行闭环：一分钟信号驱动捕捉（bar 引擎）         已实现 · 待真实比赛 live 验收
任务 4/5 前置：海外 VPS 执行环境（Tailscale 桥接）   重要不紧急
```

当前重点：

```text
扫描可靠性（防漏抓/防空结果误报）为全项目最高优先级（2026-08-16 用户要求），
所有自动化功能上线前必须过回归测试 tests/test_scan_regression.py；
监控联赛已扩至 LCP（LEC 上一轮已加入），白名单见 config/market_watchlist.json。
任务 1 已经形成可用闭环。
任务 2 已进入待验收：代码与本地离线验证完成，等待稳定网络环境下完成 live watchlist 验证。
任务 2 的主线是先识别市场现象，再路由到成熟策略。
当前稳定策略是 S1 / S2，对应旧 A / B；旧 E 已归类为 P5 整场反转现象标签，不能替代策略。
任务 2 的自动化候选流程设计已定稿：docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md。整个自动化以三层框架为核心——触发条件（什么时候看）-> 决策规则（怎么判断）-> 输出与投递（结果写哪里、谁去用），等待 live 验证通过后接入定时调度。
开发接力（2026-08-06 记录，由另一会话继续开发）：案例入库 -> 扫描器验收 -> 一分钟流小额测试 -> 深反彩票管线（环节 4，排在策略 A/B 定稿之后）；环节 6 为典型案例教科书级入库与结算跟进，详见第 10 节。
任务 6（高优先级，2026-08-07 启动）：面向外部的 Polymarket 电竞订阅制情报平台，分两大板块——实时情报台（今天：每场比赛一张情报卡：盘口 / 现象 / 翻盘画像 / 近期状态 / 事件情报 + 风险提示）与历史档案库（过去：队伍战绩胜/负、翻盘率/被翻盘率、历史对局、复盘案例；现有本地约 15+ 场 LoL 样本可直接算第一批画像）。页面定为 6 页：为什么订阅、今天有什么机会、比赛情况、比赛档案、情报库、策略实验室。详见第 11 节与 docs/task/TASK6_INTELLIGENCE_LIBRARY_PRODUCT.md；高保真原型待框架确认后制作。
V2 执行闭环（2026-08-09 建）：代码已实现并离线验证 + 预挂盘 live 冒烟通过；尚未完成真实比赛全链路 live 验收与小额实盘，autopilot 需用户显式开启——按成熟度纪律，验收通过前不算"完成"。定义见 docs/task/V2_EXECUTION_LOOP.md。
```

任务 1 当前判断：

```text
基础能力已经具备，V1 判定为已完成。
现有市场解析、配置生成、实盘挂单、成交后止盈、monitor-only、状态检查已经跑通过部分真实案例。
当前缺口主要不是策略能力，而是统一入口、关闭订单验证、状态摘要和复盘沉淀。
策略模式会持续扩展：S1/S2 当前小额实盘，S3 已支持实验性小额试单计划，S4 先建议和复盘。
新文档 docs/framework/PHENOMENON_STRATEGY_FRAMEWORK.md 已建立，作为后续分类总规则。
```

## 3. 任务 1：手动输入链接，生成计划并执行

目标：

```text
用户最小输入，系统完成市场解析、方向判断、固定金额网格配置、实盘挂单、成交后止盈挂单和监控。
```

最小输入：

```text
市场链接
Game / Map / 小局编号
策略 S1 或 S2，或旧 A/B，或自然语言描述比赛形态
可选：方向
可选：固定金额
确认执行
```

核心交付物：

```text
tools/grid_config_generator.py
tools/grid_plan_runner.py
tools/check_grid_status.py
tools/create_trade_launcher.py
tools/cancel_grid_orders.py
runtime/*.json
runtime/*.command
runtime/logs/*.log
```

已完成内容：

```text
固定金额制交易配置。
S1/S2 策略模板，代码内仍兼容旧 A/B。
S3/S4 策略模式已登记；S3 可在 --allow-experimental 下生成小额试单，S4 不进入当前自动实盘执行。
P 模块已登记：赛前小底仓 / pre-position，作为执行层通用模块，不是独立策略。
D2 模块已登记：浮盈保护 / 自动锁盈，作为 V1.1 最高优先级执行保护。
P5_BO_SERIES_COMEBACK 已登记：BO3/BO5 整场反转现象标签，底层兼容旧 E 命名，进入任务 2 规律探索层。
自然语言策略初判：auto 可把描述路由到 S1/S2/S3/S4。
auto 路由中，S1/S2 进入执行准备；S3 默认建议，可用实验开关生成小额计划；S4 只生成建议。
按 market_slug + side 解析 token。
支持直接从 Polymarket URL 解析事件 slug。
支持展开 event 下的多个 Game / Map 子市场。
统一交易准备器 tools/prepare_grid_trade.py。
Game / Map 默认优先选择 Winner 子市场。
生成首次执行、只监控、查状态、关闭订单、生成复盘五个本地入口。
多档买入。
买单成交后按成本金额挂止盈卖单。
彩票仓成本金额保留。
monitor-only 监控模式。
只读状态检查。
中文状态摘要。
状态摘要已新增 D2 区块：剩余成本、当前市值、已锁利润、归零风险、彩票仓是否超标。
部分买单成功、后续买单失败时，已支持保留已成功订单状态并进入监控。
执行专用会话模板。
docs/runbook/V1_RUNBOOK.md 已创建，可用于新会话专门运行任务 1。
关闭订单前先停监控的流程约定。
交易复盘模板生成器。
```

待完成内容：

```text
1. 方向判断：
   用户指定方向时直接使用。
   用户不指定方向时，已支持根据策略和描述倾向选择高价热门侧或低价反转侧。
   下一步需要在更多真实比赛中验证是否符合直觉。

2. 后续增强：
   C型还需要继续小额真实验证。
   D2 还需要在一次低位买入后高位浮盈案例中验证锁盈状态摘要和自动补挂锁盈单。

3. 关闭订单：
   撤单工具已经写好，但还需要完成一次真实 live 订单验证。
   “关闭订单”只撤未成交挂单，不卖已成交仓位。

4. 状态摘要：
   中文摘要已完成，需要在外部网络可用时验证订单查询输出。

5. 复盘记录：
   复盘模板已完成，需要每次真实交易后补齐实际成交、问题和下一次调整。
```

验收标准：

```text
1. 用户只发链接 + Game/Map + 策略，即可生成清晰交易计划。
2. 实盘执行前能展示买入方向、买入档位、卖出档位、彩票仓。
3. 确认后能成功挂买单。
4. 买单成交后能自动挂止盈卖单。
5. 重启后不会重复挂同一批买单。
6. monitor-only 不会新增买单，只处理成交后的卖单覆盖。
7. “关闭订单”能停止监控并撤掉未成交挂单。
8. “平仓”和“关闭订单”严格区分。
```

进入任务 2 的门槛：

```text
已满足任务 1 进入后续任务的条件。
后续真实交易继续保留状态文件、日志和复盘摘要，但不再阻塞任务 2。
```

## 4. 任务 2：自动扫描比赛列表，给出机会排名

目标：

```text
从手动找比赛，升级为系统自动扫描候选比赛，并输出机会排序。
```

第一版范围：

```text
只做机会发现，不自动下单。
优先扫描电竞中正在进行或即将开始的 Winner / Moneyline 市场。
Game / Map Winner 和 Match / Series Winner 都要扫，不能只扫单局，也不能只扫整场。
入口筛选不按赛前成交量剔除，因为很多电竞盘在比赛开始后才积累成交量。
优先时间窗口：未来 2 天内即将开始，或最近 2 天内已开始但未关闭。
筛选后的赛事按比赛时间排序：正在进行 / 最近开始优先，其次按未来开赛时间从近到远。
赛事优先级和机会分只作为同一时间附近的辅助排序，不打乱时间线。
单局 Game / Map Winner 继续保留，但不再是唯一重点。
建议策略优先输出 S1 / S2；P5 只作为 Match / Series Winner 上可叠加的现象标签。
输出候选列表和推荐观察理由。
```

候选池指标：

```text
赛事白名单
比赛开始时间 / 是否正在进行
盘口 spread
盘口深度
价格是否在 0.25-0.75
价格更新时间
成交量只做加分/参考，不做赛前硬过滤
是否热门赛事 / 热门队伍
是否 BO3 / BO5 关键局、决胜局、第四节等高波动阶段
是否符合 P1/P2/P3/P4/P5/P6 现象
是否可以路由到 S1：低价反转网格
是否可以路由到 S2：热门回撤网格
是否叠加 P5_BO_SERIES_COMEBACK：首局失利 / 前半段落后 / 整场赔率折价修复
```

当前 watchlist：

```text
LoL：LCK、LPL、LCK Challengers League、KeSPA Cup。
CS2：IEM、BLAST。
Dota2：The International、ESL One。
```

交付物：

```text
tools/market_scanner.py
config/discovery_patterns.json
config/market_watchlist.json
schemas/opportunity_candidate.schema.json
docs/task/V2_VALIDATION_HANDOFF.md
docs/task/TASK2_AUTOMATION_CANDIDATE_FLOW.md
runtime/opportunity_candidates.json
runtime/watchlist_events.json
reports/opportunity_scan_YYYY-MM-DD.md
```

已完成内容：

```text
P5_BO_SERIES_COMEBACK 现象标签已完成，底层兼容旧 E 配置。
离线扫描器已完成：可读取本地回测 JSON，建议策略输出 S1/S2 兼容旧 A/B，P5 作为现象标签叠加。
实时只读扫描器已完成第一版：可读取 Polymarket 公共活跃事件和价格历史。
实时模式默认不下单，只生成 runtime/opportunity_candidates*.json 和 reports/opportunity_scan*.md。
实时模式已加入终局过滤：当前价格接近 0 或 1 的市场不作为可交易机会输出。
实时模式已容错：单个 token 价格历史接口失败时跳过，不中断整次扫描。
流动性检查已完成第一版：实时候选会读取 order book，输出 best bid / ask、spread、3c 深度、流动性分。
候选输出已新增建议动作：review_only / observe_only_liquidity_too_thin / manual_review_before_plan / can_prepare_trade_plan。
新增 config/market_watchlist.json：按赛事白名单和 2 天时间窗口筛候选，不再用赛前成交量做入口过滤。
实时扫描入口已改为按 startDate 拉取事件，再本地做 watchlist/time window 过滤。
实时扫描输出已改为按比赛时间排序，而不是按成交量或机会分优先排序。
实时扫描新增赛事时间线输出：runtime/watchlist_events.json，按时间展示所有白名单赛事，即使暂时没有 P5 现象机会也保留观察。
扫描报告新增“赛事时间线”区块，先看比赛日程，再看候选机会。
实时事件获取已支持分页：默认扫描多页 active events 后再做 watchlist/time window 过滤，避免第一页没有目标赛事就误判为空。
实时扫描器已从旧 E-only 校正为 S1/S2 策略扫描：Game / Map Winner 与 Match / Series Winner 都进入候选池，P5 只在 BO3/BO5 整场反转时叠加。
候选 JSON 输出已新增产品层字段：phenomenon_tags、recommended_strategy、recommended_strategy_detail、route_strategy、strategy_maturity。
新增 schemas/opportunity_candidate.schema.json，固定任务 2 输出结构，方便后续网页和执行层读取。
实时扫描已新增空结果诊断：抓取事件数、标题过滤后数量、时间窗口内数量、watchlist 匹配数量、最终赛事数量、候选数量。
诊断信息会同时写入 runtime/opportunity_candidates*.json、runtime/watchlist_events*.json 和 reports/opportunity_scan*.md。
新增 tools/summarize_scan_diagnostics.py，用于读取 live scan 产物并输出中文诊断摘要。
新增 runtime/run_task2_live_scan.command，作为任务 2 live 只读扫描的一键本地入口。
完成一次 live 诊断：Gamma startDate 正序返回大量 2024/2025 长期 active 事件，导致最近两天赛事没有进入时间窗口。
实时事件入口已修正为 startDate 正序 + 倒序双向抓取并去重，下一次 live scan 应优先验证 within_time_window 和 watchlist_matches 是否恢复。
新增 docs/task/V2_VALIDATION_HANDOFF.md，可交给外部网络环境验证任务 2。
```

待完成内容：

```text
0. 反弹检测（由点到面的第一个点）：
   单市场盯盘模式，1 分钟粒度采样；目标方 <10c 后短时拉升 >=15c 触发 P5+P1 候选。
   以 2026-08-06 IG vs NIP 为回放验收样本，验收产出候选 JSON + 动作队列 + 报告三件套。
   铺开方向：市场面（单场 -> 白名单全部）-> 形态面（P5+P1 -> P5+P2）-> 深度面（发现 -> 模拟 -> 小额实盘）。
1. 候选池增强：
   验证 watchlist 是否能稳定覆盖目标赛事。
   后续可按用户复盘继续增减赛事关键词。
   需要进一步确认 Gamma active events 是否会漏掉未开赛赛事；若会漏，需要增加按联赛关键词的搜索/补扫入口。
   下一次 live 验证优先看诊断块：如果 fetched_events > 0 但 watchlist_matches = 0，说明关键词要调；如果 fetched_events = 0 或目标赛事不存在，说明要补另一个事件源。

2. 机会分增强：
   当前机会分已经包含价格形态和盘口质量。
   下一步加入成交量、价格更新时间、是否接近终局等扣分，但成交量不做赛前硬过滤。

3. 输出增强：
   候选列表需要进一步区分：
   观察 / 可生成计划 / 暂不执行 / 跳过 / 可回测验证。
   下一步可以把赛事时间线和候选机会拆成两个本地网页视图。
```

验收标准：

```text
1. 能自动输出候选市场列表。
2. 每个候选市场有机会分、流动性分、风险提示。
3. 至少能从候选列表中筛出 3-5 个值得人工查看的市场。
4. 不触发实盘下单。
```

## 5. 任务 3：纠缠指数上线，自动标记主策略和辅助标签

目标：

```text
让系统更早识别“可网格交易”的价格形态，并自动判断更像主策略 S1 / S2 / S3 / S4 中的哪一种；P5 这类只作为辅助现象标签叠加。
```

第一版纠缠指数：

```text
50% 穿越次数
短期累计波动
弱势方快速缩距
价格停留中位区间的时间
盘口活跃度
流动性质量
终局风险扣分
数据停滞扣分
```

策略标记规则：

```text
A 型：深度反转 / 彩票型，常见于 0.10-0.35 区间。
B 型：强队临时低估，常见于热门方从高位回落到 0.55-0.75 区间。
C 型：强势碾压 / 理财局，常见于优势方 0.70-0.90 区间的小回撤。
D 型：已有持仓救援 / 成本管理，先识别旧仓，再决定减仓、补仓或保留彩票仓。
E 标签：BO3/BO5 Match Winner / Series Winner 的整场反转发现标签，路由到 A / A2 / B2。
跳过：价格单边、过于接近终局、spread 过大、数据停滞。
```

交付物：

```text
tools/entanglement_score.py
schemas/opportunity_score.schema.json
reports/entanglement_examples.md
```

验收标准：

```text
1. 能对历史案例输出纠缠指数。
2. 能解释为什么标记为 S1 / S2 / S3 / S4 / P5 / 跳过。
3. 对用户已提供的典型截图案例，能给出符合直觉的分类。
4. 不追求全自动准确，先追求可解释和可调参。
```

## 6. 任务 4：半自动交易台，用户点确认后执行

目标：

```text
把命令行和会话执行，升级成一个本地网页交易台。
```

前置条件（基础设施，重要不紧急，任务 4 启动前解决）：

```text
把执行层（挂单/监控/撤单脚本与机器人）迁移到海外 VPS（美西或东京），
24/7 稳定运行，不依赖本地 VPN；通过 Tailscale 桥接本地对话与服务器。
安全底线：私钥仅存 VPS，SSH 密钥登录、关闭密码、开防火墙；本地保留备份控制台。
来源：用户提出（2026-08-04），因中国大陆 VPN 访问不稳定导致下单卡顿。
```

产品形态：

```text
机会列表
市场详情
策略 S1/S2 建议
固定金额输入
买入/卖出网格预览
一键确认执行
订单状态
关闭订单
平仓
复盘记录
```

安全边界：

```text
网页优先本地运行。
私钥仍由本机已有执行项目管理。
网页只调用本地接口，不把私钥发到第三方托管平台。
```

交付物：

```text
local_trading_console/
本地 Web UI
本地 API 封装
执行日志页面
订单状态页面
```

验收标准：

```text
1. 本地网页能展示任务 2/3 的机会列表。
2. 用户能在网页确认策略和金额。
3. 点击确认后调用任务 1 的执行能力。
4. 页面能显示买单、卖单、监控状态。
5. 支持关闭订单和平仓两个明确动作。
```

## 7. 任务 5：全自动小金额试运行，带风控和复盘

目标：

```text
在非常小金额和严格风控下，让系统自动发现机会、自动执行、自动复盘。
```

自动化边界：

```text
仅使用小金额。
仅允许白名单市场类型。
仅在流动性达标时执行。
每日最大交易次数。
每日最大投入金额。
单市场最大投入金额。
连续失败自动暂停。
异常网络 / 异常盘口自动暂停。
```

风控规则：

```text
价格过高不追。
价格过低不无限补。
临近终局不新开。
spread 过大不交易。
订单状态不明不重复下单。
数据长时间不更新不交易。
```

交付物：

```text
tools/auto_runner.py
config/risk_limits.json
reports/daily_trading_review_YYYY-MM-DD.md
runtime/risk_state.json
```

验收标准：

```text
1. 连续运行小金额测试时，不出现重复下单。
2. 每日自动生成交易复盘。
3. 风控触发时能暂停而不是继续执行。
4. 用户可以一键停机。
5. 私钥不离开本机。
```

## 8. 复盘记录模板

每一笔交易结束后补充：

```text
日期：
市场：
Game / Map：
策略：
方向：
计划投入：
实际成交：
止盈卖出：
彩票仓：
最终结果：
是否符合预期：
问题：
下一次调整：
```

## 9. 最近决策记录

```text
2026-08-16：
- 任务 2 扫描器 live 复扫发现严重漏抓，根因三处并已修复：
  1) 时间字段错误：真实开赛时间在 market 层 gameStartTime，事件级 startDate 是挂牌时间；
     扫描器原逻辑退回 startDate，导致 2 天窗口判断失真。已改为优先 market gameStartTime（取最早值）。
  2) 抓取策略漏洞：原来按 startDate 最老+最新各翻 8 页，漏掉中间段的今天/明天赛事；
     已接入 Gamma Esports 标签（tag_id=64）全量抓取（config/market_watchlist.json 新增 esports 配置）。
  3) 白名单缺失 LEC 与 Esports World Cup（EWC），已补入 config/market_watchlist.json。
- 修复后 live 复扫：抓取 2322 事件 / 白名单匹配 75 / 窗口内赛事 24 / 候选 14（修复前 0）。
  今天实盘验证命中：LCK T1 vs Gen.G、LPL 3 场、LEC 2 场（G2 vs Fnatic / Movistar KOI vs NaVi）、
  Dota2 The International 淘汰赛、CS2 Esports World Cup 小组赛。
- 防复发（2026-08-16 加入）：task2_pipeline 新增"空结果自检"——抓取为 0 / 电竞标签为 0 /
  白名单 0 匹配 / 时间窗口异常时输出告警并禁止报"暂无白名单比赛"；
  正常空结果也在报告尾部写明"自检通过"，避免未来会话把静默失败当"今日无信号"。
- 监控联赛扩增（2026-08-16 用户指定）：新增 LCP（League Championship Pacific）；
  LEC 已于修复轮加入。白名单 LoL 现含 LCK/LPL/LCP/LEC/KeSPA Cup。
- 回归测试落地（2026-08-16）：tests/test_scan_regression.py（14 条）锁死时间字段、
  电竞标签抓取、白名单联赛覆盖、空结果自检四类防错点；根 AGENTS.md 新增
  "最高优先级防错规则"，全项目通用。
- 定时扫描已启用（2026-08-16，用户确认）：本会话常驻运行
  tools/task2_pipeline.py --watch --interval 900（每 15 分钟一次，
  仅 Codex 运行期间生效；全程 dry-run，不下单）。
  重启启动器：runtime/run_task2_watch.command；
  若需 24/7 后台扫描，可用 runtime/launchd/com.polymarket.task2-pipeline.plist。
- 任务 2 "真实赛事进入 2 天窗口后重验 watchlist 匹配与 live 候选" 验收项已通过实盘验证；
  任务 2 整体是否转"已完成"待用户确认后更新。
2026-08-12：
- 每日形态复盘（自动化巡检）：136 序列 / 30 组快照，今日无新快照/复盘/交易/EDGE
  （08-11 晚间 4 组快照 + 复盘/交易已由前会话入索引与进度库，本轮补齐形态库同步）。
- 复验计数（详见 reports/pattern_audit_2026-08-12.md）：B4 直线阴跌 49 / A2 中位U型反转 31 /
  A3 折价修复 15 / 热门全程压制 12 / A1 V型极值反转 14 / C2 五五开开局碾压 10 / 未知 9 /
  A4 下狗整场反转 8 / A6 反弹确认 7 / B2 死亡螺旋 6 / A5 W型双底 6 / B4 低开阴跌 6 /
  A7 强强对话错杀 4 / C2 早期缩距 1 / B1 尾盘崩塌 1；候选新形态 0（未知未达 3 相似图形，仅观察）。
- 已同步：REVERSAL_PATTERN_LIBRARY.md（数据基础 +4 组、频率块 136/30、A1/A2/A3/B4 样本行、
  未知观察池 9 条、让一追二样本组 +NSEA/DKC）、STRATEGY_PATTERN_LIBRARY.md（P5 样本 +4：
  MOUZ/RE、YES/LevelUP、NSEA/DKC 正样本 + DRXC/FOXY 陷阱样本）、
  reversal_patterns.html 与 strategy_library.html 对应区块。
- 无 3/5/7 天预警（last_input=2026-08-11，no_content_days=1，仅巡检记录）。
2026-08-11：
- 每日形态复盘（自动化巡检）：119 序列 / 25 组快照（新增 6 组：cs2-fnc-k271-2026-08-09、
  dota2-pr1-mouz-2026-08-10、lol-fnc-kc-2026-08-09、lol-dnf-drx-2026-08-10、
  lol-gen-dnf-2026-08-10、lol-hle1-gen-2026-08-10）+ 08-10 复盘/交易/EDGE 新内容。
- 复验计数更新（详见 reports/pattern_audit_2026-08-11.md）：A2 中位U型反转 15 -> 23
  （首次越过单形态 >=10 统计门槛）、A1 V型极值反转 6 -> 10、A3 折价修复 12 -> 15、
  热门全程压制 9 -> 12、B4 直线阴跌 42 -> 46、A4 5 -> 7、A5 3 -> 4、A7 1 -> 3、
  未知 7 -> 8；候选新形态 0（未知未达 3 相似图形，仅观察）。
- 新样本要点：K27（CS2 整场 6c->100c / Map2 11c->100c，让一追二）、MOUZ（Dota2
  G2 18.5c->100c）、KC（LEC 热门全程压制 2:0，A3×3）、DNS（DNF 让一追二整场 11.5c->100c、
  GEN 5.5c->92.5c 弱克强）、HLE（让一追二整场 11.5c->100c + Over 22.5c->99.5c）。
- 08-10 复盘已由复盘会话入索引（Dota2 小仓滚仓 +300 正面 vs 08-09 全仓归零反面），
  本轮只做形态结构归位，不重复录入；无 3/5/7 天预警（last_input=2026-08-10）。
- 已同步 REVERSAL_PATTERN_LIBRARY.md 与 reversal_patterns.html（A1/A2/A3/A4/A5/A7/B2/B4
  样本行、频率块、未知通道）；strategy_library.html 证据区补 A1/A2/A7 新样本。
2026-08-10：
- 让一追二特征分析登记为策略研究未决问题（STRATEGY_RESEARCH_HANDOFF 第 9 项），
  并入四阶段回测 v2 分层（赛制 x 赛前强弱区间 x 游戏）；定价逻辑确认：
  整场 12-20c 买入命中率约 30%（>盈亏平衡 12-20%）-> +EV（中胜率高赔率 5-9x），
  执行按彩票预算 + 启动确认。
- 预测市场方向一致性研究登记为最高优先级知识库研究项
  （knowledge/MARKET_DIRECTION_CONSISTENCY.md）：到期前 30d/15d/48h/24h 等时间口径的
  D(t) 一致性 + 延续概率 C(T1→end)，按板块分层。可行性探测：旧市场公开接口无历史
  （全部 EMPTY）→ 30d/15d 需从现在持续采集；近期市场可先做 48h/24h/12h/6h 短期限分析。
- 四阶段执行框架登记为待验证研究项（模式研究 / 策略研究 / 数据积累 / 情报库四线共用）：
  0-10 小仓方向判断、10-20 方向确定+决策（反转主窗口）、20-30 方向确定+决策
  （顺势/减仓，彩票 25+）、30+ 基本确定结果（锁盈/止损，尾盘反转是主要风险源）。
  详见 docs/task/THREE_WINDOW_EXECUTION_FRAMEWORK.md。
- 框架与任务 6 情报卡"比赛时间线"对接：局内事件（一血/单杀/团战）时间戳
  对照 1 分钟赔率，作为情报卡的内容源；未验证前仅作观察/研究，不下单依据。
- K27（CS2 整场 6c->100c）、FNC vs KC（LEC 热门全程压制）等新样本已入黄金样本集，
  为三窗口假设验证提供数据。
2026-08-03：
- 项目分为机会发现层和执行管理层。
- 第一版执行采用固定金额制，不按总资产比例。
- 用户输入尽量简化为链接 + 小局 + 策略。
- 执行入口和监控入口必须分开。
- 关闭订单表示撤未成交挂单；平仓表示卖出已有持仓。
- 网页端可以做产品台，但私钥暂不交给第三方一键部署服务。
- 增加 C/D 两类策略模式：C=强势碾压/理财局，D=已有持仓救援/成本管理。
- 旧 A/B 继续作为任务 1 当前实盘执行重点，后续统一映射为 S1/S2；旧 C 增加实验性小额试单模板，后续统一映射为 S3；旧 D 先做识别、建议和复盘，后续统一映射为 S4。
- 长期产品目标是支持自然语言/语音输入：用户说市场和想法，系统完成现象识别、策略判断、挂单、监控、复盘。
- 新增 docs/framework/STRATEGY_PATTERN_LIBRARY.md，用成熟度管理 S1/S2/S3/S4 和未来新策略。
- 原则调整：C/D 未来可以自动化交易，但必须先经过建议、模拟和小额实盘验证。
- BRO/FOXY 整场 B 型实盘暴露余额不足导致状态未保存问题；已修复为每成功一档买单立即保存状态，后续失败也进入 monitor-only 管理。
- 新增 docs/runbook/V1_RUNBOOK.md，支持单独开交易执行专用会话运行任务 1。
- 新增 P 模块：赛前小底仓。默认 5-10 USDC，只有用户明确表达时执行，赛中再用 S1/S2/S3/S4 网格管理。
- 新增 docs/runbook/V1_1_PROFIT_LOCK.md，将 D2 自动锁盈提升为 V1.1 核心能力。
- S1/S2/S3 交易计划默认附带 profit_lock_plan。
- 状态摘要新增 D2 暴露检查，优先显示是否已经超过彩票仓上限。

2026-08-04：
- V1 判定为已完成，项目进入任务 2：自动扫描比赛列表，给出机会排名。
- 新增 P5_BO_SERIES_COMEBACK 作为任务 2 的 BO3/BO5 整场反转现象标签，底层兼容旧 E 命名。
- 任务 2 主线明确为先识别现象，再路由成熟策略：P1/P5 -> S1，P2/P5 -> S2。
- 扫描范围明确为 Winner / Moneyline 市场，Game / Map Winner 与 Match / Series Winner 都要覆盖。
- P5 不直接下单，先识别折价区间，再路由到 S1 / S2 或进入中位反转观察。
- P5 + P1：低价深度反转，路由 S1；P5 + P3：30c-45c 中位反转，先建议/模拟；P5 + P2：强队折价修复，路由 S2。
- P5 叠加交易成交后必须接入 D2 自动锁盈，第一档成交后不能只挂普通止盈。
- 三个回测样本已作为 P5 样本库第一批：Dota2 VG/YB、CS2 SPARTA/ex-Young Ninjas、LoL NAVI/Shifters。
- 任务 2 第一版扫描器已跑通：离线样本从旧 E-only 校正为 S1/S2 建议策略 + P5 现象标签，实时只读扫描输出过可观察候选。
- 实时扫描器加入终局过滤和接口失败容错，避免把已封顶/归零市场当作机会。
- 实时扫描器加入盘口流动性检查，spread 过大或深度偏薄会降低机会分并提示只观察/人工复核。
- 实时扫描器的候选输出按比赛时间排序，符合先看当前/最近/即将开始比赛的工作流。
- 实时扫描器新增 watchlist_events.json，先输出按时间排序的赛事时间线，再在其中识别机会候选。
- 实时扫描器新增分页获取 active events，减少漏掉低成交量/非热门赛事的概率。
- 用户确认单笔交易可承受 50-70 USDC，风控限额放宽：单市场上限 30→70、单日上限 75→200、A/B 默认轮次预算 25→50（config/risk_limits.json）。
- 市场结构规律沉淀：BO3/BO5 第三局没有独立 Winner 小市场，第三局输赢直接体现在整场 Moneyline（docs/framework/STRATEGY_PATTERN_LIBRARY.md 第 9 节）。
- 记录系统目标（2026-08-04）：10 个交易日内单事件胜率 ≥70%、累计净盈利 ≥+300 USDC、单笔最大回撤 ≤-30；自动化目标含低吸成交自动补止盈、比赛结束自动撤死单、自动发现并推荐比赛（衔接任务 2 扫描器）；执行环境迁移到海外 VPS 进入评估。
- 海外 VPS 执行环境已登记为任务 4 前置基础设施（重要不紧急）：美西/东京 VPS + Tailscale 桥接，解决本地 VPN 不稳定导致的下单卡顿；任务 4 启动前解决。
- BRO vs DRX 第三局复盘五错入库（2026-08-04）：赛前仓比例不足、低吸 42-48c 接飞刀、79/80c 追高、首波止盈过早、34c 市价割肉；已固化为「执行模板按比赛类型路由」（docs/framework/STRATEGY_PATTERN_LIBRARY.md 第 10 节：高信心局 A / 标准局 B / 小仓试局 C）。

2026-08-06：
- IG vs NIP（LPL BO3）案例验证并入库：G1 IG 获胜后 NIP 被判死，G2 局内翻盘；Moneyline 从 <5c（采样 6.5c）拉到 34.5c、G2 Winner 从约 13c 拉到 79.5c（10 分钟采样），归入 P5+P1 -> S1 实时样本（docs/framework/STRATEGY_PATTERN_LIBRARY.md）。
- 记录三环节开发接力：案例入库 -> 扫描器验收（任务 2）-> 一分钟流小额测试；由另一会话继续开发，详见本文件第 10 节。
- 新增工具升级项：1 分钟级价格流 + 反弹检测（<10c 区间单根拉升 >15c 触发 P5+P1 候选）；极低价候选强制彩票仓 + D3 保护。

2026-08-07：
- 文档体系重构：根目录只留 AGENTS.md + README.md，全部文档迁入 docs/（framework / runbook / task / data / research），新增 docs/AGENTS.md 文档管理规范（顶层结构、类型归属、会话->文档映射、阶段映射、命名规范、迁移对照）。
- 数据采集方案定稿：波动分析以成交价为主、订单簿为辅；朋友日志为纳秒级全量订单簿且不可改，改用打点程序按比赛/小局窗口切片。
- 新增打点程序 tools/event_marker.py v1：轮询 Gamma，记录 event_start / game_start / game_end / event_end，输出 runtime/markers/*.jsonl + state.json，重启自动去重；已通过离线三段快照回放验证（6 个点全部正确、无重复）。
- 新增离线回放夹具 tests/fixtures/marker_fixture_events.json，供打点程序验收复用。
- 情报库产品立项为高优先级任务 6：订阅制电竞交易情报平台，复用现有盘口采集、现象标签、策略库与复盘知识库。
- 翻盘情报引擎想法确认：统计各队"被翻盘率 / 翻盘率 / 领先稳定性 / 落后反弹力"，直接服务 S2 热门回撤——被翻盘少的强队回撤可放心买，被翻盘多的队伍（尤其 LPL）收紧档位并打"假赛风险观察"标。
- 平台框架简化定稿（2026-08-07 续）：确定为"一开始就面向对外"、只做 Polymarket；页面定为 6 页（为什么订阅 / 今天有什么机会 / 比赛情况 / 比赛档案 / 情报库 / 策略实验室）。
- 新增情报维度：近期状态（连续低迷的队伍暂时领先时标记"被反弹风险"，作为 S2 收紧依据）、事件情报（内讧、人员更换、教练/赛程变动，标注来源与时效）。与翻盘画像一样纳入每场比赛的情报卡。
- 平台框架文档：docs/task/TASK6_INTELLIGENCE_LIBRARY_PRODUCT.md（情报卡 + 6 页 + 数据来源 + 订阅简表 + 红线）；高保真原型待框架确认后按 6 页制作。
- 情报口径拍板：平台只给情报与统计（"这类形态出现过 N 次、反转成功率 X%"），不给交易建议；策略路由只留在内部交易系统。
- 近期状态 / 事件情报：人工 + 半自动录入，可从朋友聊天记录沉淀建库，标注来源与时效。
- 档案库批量数据源：朋友已在抓取历史数据，接入后回填战绩与翻盘画像；本地 15+ 场样本先验证口径。
- 订阅改为一开始就付费：注册后试用 1-2 天，无长期免费档（Pro / Pro+ 分档，定价待定）。
- 战绩口径拍板：档案库小局（Game）与整场（Match）双口径都展示、都算，都有独立统计与价值；付费分档非核心，后定。
- 情报库功能补充定稿：翻盘案例三阶段数据模式（翻盘前 / 翻盘中 / 翻盘后），客观盘口与主观参考分层，每字段带来源与可信度；虎牙解说信号作为主观参考层（固定名单：957、毛毛、记得、米勒；转写 + 人工标注）；外部电竞比赛数据（局内事件、比分、阵容）列为待获取数据源。
- 档案库定位为可查询数据库：按比赛 / 联赛 / 战队 / 现象 / 画像区间 / 事件与风险组合查询，可选按解说主观信号筛选。
- 形态 / 策略成果六点全部映射进情报库功能点（REVERSAL_PATTERN_LIBRARY、TEAM_PROFILES、LOTTERY_MACHINE、D3 均已落地）；
  重点功能：形态气候（点 1，今日反转/崩塌占比预警）、赛前情报层（点 3，"预期情形"= 假说层，仓位放大须等盘中形态确认）；
  待办：形态标签自动化接入 bar 监控、TEAM_PROFILES 与"预期情形"标签对接。
- 情报维度补充七项全部采纳（2026-08-08）：同场多市场联动 / 背离、终局时间衰减、对手强度加权画像 + 交锋记录、
  大单与主动成交方向、陷阱 / 反面样本检索、数据可信度层、触发式预警；重点：同场联动、终局衰减、反面样本、触发式预警。
- 机会卡片规则定稿（"今天有什么机会"页）：值得看 = 形态/现象信号 或 画像/事件信号 + 可成交性达标；
  卡片 5 块（对阵时间 / 信号+同形态统计 / 关键情报一句 / 风险提示一个 / 详情入口）；
  进行中优先、双信号优先，每天最多 8 张，不含任何交易建议。
- 设计基调确认（2026-08-08）：苹果 / SAP 式简洁高效风格——留白充足、层级清晰、功能优先、配色克制；
  作为高保真原型与页面实现的设计原则。
- 比赛情况页组件定稿（V1）：6 块从上到下——比赛头 / 盘口走势（含同场联动）/ 预期情形（假说层）/
  双方情报对比 / 终局时间衰减（仅临近终局）/ 风险提示（最多 2 条）；含未开赛、已结束、低流动性隐藏规则。
- V1 瘦身定稿：只做 3 个核心页（今天有什么机会 / 比赛情况 / 比赛档案 + 情报库查询）+ 简单落地页；
  策略实验室、触发式预警、导出 / API 后置；所有补充维度作为页面区块，不新增页面。
- 触发式预警确认做、排第二期（不在 V1 页内）；预警触发维度：形态触发 / 画像预警 / 解说信号 / 关注队伍与联赛。
- 比赛档案 / 情报库四维查询定稿（V1）：联赛位 / 比赛队伍位 / 形态位 / 策略位，一个库两种视角
  （队伍视图 / 案例视图），交叉统计为核心价值；结果列表 8 列内；联赛级统计先上，队伍级画像样本 >=10 才出。
- 情报库数据补充（2026-08-08 直播弹幕）：LEC BO3 打满结构——G1 强队（热门）赢 -> G2 弱队赢，
  可在第二局做彩票仓小翻倍；已登记 INTEL_SIGNALS（n=2 初步验证：SK/NAVI、T1/HLE），
  待 LEC 历史统计 >=20 样本验证；同源叠加"LEC 假赛/明眼"弹幕情绪分析；弹幕列为低置信度主观来源。
- 经验清单 v1 建立（2026-08-11，knowledge/EXPERIENCE_INSIGHTS.md）：收编已确认经验 30+ 条，
  分联赛 / 队伍 / 形态 / 执行风控 / 信息差五类，每条带来源、样本量与验证状态（已确认 / 待验证 / 观察中）；
  附验证任务清单 8 项（LEC G1->G2、让一追二、EDGE 分组、尾盘反转率等跑量目标）。
- V1 功能框架页 HTML 落库（2026-08-11，docs/task/v1_framework_preview.html）：
  五页签交互预览（为什么订阅 / 今天有什么机会 / 比赛情况 / 比赛档案·情报库 / 预警第二期），
  按项目最高优先级视觉规范改为 SAP/Apple 浅色风格。
- 产品定位确认（2026-08-11）：现阶段更偏向历史档案库——为今日辅助决策提供数据支持，
  输出"赛前档案卡"（近期赛果/碾压情况/价格走势/情况梳理/类型占比/小局 vs 整场），不给买卖建议；
  分析内容三层（策略 / 图形 / 分阶段）进档案库；示例 T1 vs Gen.G 已入框架页（v1_framework_preview.html 新增页签）。
- V1 框架页简化（2026-08-11）：页签 6 -> 5——赛前档案卡并入"比赛情况"未开赛状态（页面状态驱动，不单独成页）；
  新增数据底座行（122 序列 / 黄金样本 95 / 反事实 47 / LEC BO3 65 场 / LoL BO3 393 场）；
  文档 4.5-4.8 标注为功能点候选库，V1 兑现以 5.2 版本分层为准。
- 反转统计视图入档案库（2026-08-11，黄金样本 95 序列口径）：家族占比 反转 A 46% / 崩塌 B 35% /
  压制 9% / 未知 8% / 震荡 C 2%；高频形态 B4 直线阴跌 30% / A2 中位U型 15% / A3 折价修复 11% / A1 极值反转 11%；
  联赛分布 LPL 反转 16 / LCK 14 / CS2 崩塌 19（最多）；队伍倾向 BLG→崩塌、WE/TES/BRO→深反、
  TT/HLE→中位、Liquid/NAVI→折价修复、KC→压制。四阶段回测数据（0-10 噪声 57%、10-20 成形 68%、30+ 定局 81%）
  与反转统计视图已入框架页。
- 情报库最高原则确认（2026-08-11）：网站清清爽爽提供情报分析——界面简洁、只给事实与统计、可溯源；
  无样本显示"样本不足"、无信号显示"今日无信号"、陈旧结论自动降级；
  页面固定注明"不构成任何投资建议"。已写入 TASK6 文档、AGENTS.md 与框架页。
- 分工清单定稿（2026-08-11，TASK6 第 9 节）：现在就能做——反转统计 / 赛前档案卡 / 形态气候 /
  四阶段窗口 / 画像 / 信号采集 / 本地只读控制台 / 框架页（均已具备数据或工具）；
  等合作伙伴——全量历史数据抓取与清洗、历史数据回测策略开发、外部局内事件数据、
  产品化工程（数据库 / API / 订阅支付 / 海外部署）、弹幕解说采集规模化。
- 数据采集目标清单定稿（2026-08-11，docs/data/COLLECTION_TARGETS.md）：赛事清单
  （LPL / LCK / LCK CL / LEC / CS2 / Dota2，近 2-3 个月起步、目标 200+ 场）、队伍清单
  （本仓库已见样本 ✓ 标记、slug 待确认项列出）、抓取规格（Game + Match、1 分钟优先、结算复核）、
  避坑清单（低成交量降级 / 队伍别名 / 结算异常 / 采样漏极值 / 时间窗口）。可直接转交数据合作伙伴。
- 形态气候展示与比赛情况页结构调整（2026-08-11）：形态气候改"昨日定稿 + 今日滚动"双显
  （今日每场结算后自动补标签、标注"进行中 x/y 场"、盘中临时标签可能修正、最终以结算为准）；
  比赛情况页改为"今日重点比赛列表 -> 选中场次按状态展示"
  （未开赛 = 赛前档案卡 + 观察情况 / 进行中 = 6 块组件 / 已结束 = 结算 + 形态标签）。
- 情报库数据刷新（2026-08-14）：快照 26 -> 41 组 / 序列 122 -> 167 / 黄金样本 95 -> 137；
  反转统计更新——家族 反转 A 48% / 崩塌 B 32% / 压制 12% / 未知 6%；
  高频形态 B4 直线阴跌 27% / A2 中位U型 18% / A1 极值反转 15%；
  联赛分布 LPL / LCK 反转各 22、CS2 崩塌 20（仍最多）；
  队伍倾向新增 DNS→深反×4、K27→深反、FOKUS / Liquid→折价修复、NRG→开局碾压等；
  已同步框架页数据底座与反转统计视图、TASK6 文档。
- 假赛分析与假赛库定稿（2026-08-15，融入风险观察、不单独成页）：
  特征库（假赛疑似通用信号 5 条，命中 >=2 锁盈/减仓不反手）、
  案例层（疑似案例 + 获胜者拆解模板：局内路径 / 价格路径 / 市场资金 / 异常点 / 定性状态）、
  关注名单（重点关注队伍 -> TEAM_PROFILES / LEAGUE_PROFILES；
  特别关注假赛队伍 -> 疑似标注；重点关注账户 / 假赛高盈利账号 -> docs/forensics 交易者拆解域：
  e46m3、fkigedgjdgwbg、拉盘钱包待同源排查）；
  产品呈现为档案库"风险观察"快捷视图 + 队伍档案风险区块；红线保持"只给信号 + 依据，不断言"。
- 情报库持续建设升级为最高优先级 A 级（2026-08-18）：AGENTS.md 新增"最高优先级任务（A 级）"，
  与数据可靠性防错同级；弹幕情报子线落地（阶段 0 完成：抓取 / 监控 / 分析 / 复盘全链路，
  总入口 knowledge/DANMU_README.md；与行情对照见 DANMU_POLYMARKET_ROADMAP.md，阶段 1 验证中）。
- 多直播间弹幕持续会话升级（2026-08-19）：新增 tools/run_danmu_session.py，统一启动独立采集、
  健康状态、开播无数据告警、异常退出自动重启、聚合 HTML 与结构化 JSON；660000 官方赛事房、
  米勒 149361、Remember/记得 528222 已登记并用于当日 LPL/LCK 实时监控。新会话先读
  runtime/danmu_sessions/<session>/session.json 判断是否仍在运行，0 条只能报“样本不足/采集异常”，
  禁止报“无信号”。
- 情报库数据底座刷新（2026-08-18）：快照 187 条序列 / 49 组、黄金样本 156、
  弹幕 2 场 4165 条（TH vs Navi 2262 / KC vs GX 1903）；
  反转统计更新——家族 反转 A 47% / 崩塌 B 34% / 压制 13%；
  高频形态 B4 26% / A2 19% / A1 14%；联赛 LCK 反转 26（最多）、CS2 崩塌 18（最多）；
  已同步框架页数据底座与反转统计视图、TASK6 文档。
- 情报库新功能框架与发布就绪度更新（2026-08-18）：框架页新增"当前已有能力"清单
  （反转统计 / 赛前档案卡 / 形态气候 / 四阶段 / 弹幕情报 / 假赛特征库 / 经验清单）与
  "弹幕集体智慧"快捷入口；发布评估——内容侧可发内部预览版，
  对外订阅站门禁 4 项（全量历史数据 / 网站工程 / 管道自动化 / 合规落地），已写入 TASK6 8.1。
- 内部预览版上线（2026-08-18，docs/task/intel_library_preview.html）：真实数据接入——
  今日比赛列表（08-17 扫描：T1 vs DNF 等 6 场）、赛前档案卡（T1 vs DNF 真实快照：
  G1 33c→100c、G2 78.5c→0.05c、Moneyline 73.5c→0.05c，DNF 3:1，T1 系列赛领先被翻二次先例）、
  反转统计视图（黄金样本 156）、形态气候（巡检 08-15）、弹幕摘要（TH vs Navi 信息差信号 / KC vs GX）；
  数据截至标注 + 页脚免责；08-18 需重扫刷新比赛列表。
- 弹幕情报库框架 v2 定稿（2026-08-22，docs/task/DANMU_INTEL_FRAMEWORK.md）：
  框架重新梳理为"采集 -> 提炼 -> 输出 -> 验证 -> 沉淀"五层；
  三大原则——①弹幕情报页可直接发布（静态站 MVP）；②发布必须带佐证闭环
  （弹幕情报 -> 比赛结果 -> 验证回填：预测命中率 / 灰信号兑现率 / BP 判负验证）；
  ③闭环是产品钩子。已写入 AGENTS.md A 级任务第 7 条与 TASK6 4.7.1。
  下一步：做发布 MVP（静态站 + 自动发布流水线 + 首个闭环佐证样例）。
- 弹幕情报库产品上线（2026-08-22，GitHub Pages）：https://adul9981.github.io/danmu-intel/
  仓库 Adul9981/danmu-intel（公开）；站点 = 产品首页（价值 / 数据底座 / 闭环钩子）+
  intel/（弹幕情报页 60 份 + 灰信号统计）+ preview/（产品框架预览 + 情报台内部预览）+
  docs/（弹幕情报库框架）；HTTP 200 验证通过。
  边界：聚合展示、灰信号"观众质疑，非结论"、页脚免责、不含原始弹幕身份。
- 弹幕情报库产品定位重梳（2026-08-22）：最高优先级规则 = 清清爽爽、定位清晰、三问三答
  （做什么 = 一场比赛一页情报；信息价值 = 观众集体智慧浓缩，可溯源；
   用户获得 = 预测 + 闭环验证，只给情报与统计不给买卖建议）；
  站点首页按三问重写，新增"今日比赛情报（08-22 Polymarket 场次 5 场：LPL WE-LGD /
  JDG-TES / IG-NIP，LCK GEN-DK / DNS-KRX）"入口与队伍 / 选手画像页入口；
  已推送 danmu-intel Pages（main e1fe127）；框架文档新增 1.5 产品三问规则。
- 首个闭环佐证样例上线（2026-08-23，danmu-intel Pages main 942103a）：
  WE vs LGD（08-22 LPL）——弹幕预测验证表（"资本告诉你1:1"/"让一追二"/"打满"命中 3，
  "第三把WE捡钱了"落空 1 = 75%）、Monki 灰信号跨场兑现 2/3、6 倍盘兑现（观众口径）；
  页面 intel/closed_loop_WE-LGD_2026-08-22.html，首页新增闭环样例入口；
  结果状态标"待官方确认"，官方回填后自动更新判定。
- 弹幕情报产品核心收敛（2026-08-23，danmu-intel Pages main 0ddab47）：
  站点只保留弹幕情报核心（首页 + 情报页 + 闭环样例 + 灰信号统计 + 画像），
  移除平台预览页与无关功能；专注"弹幕情报 + 共识层"输出；
  对外文案删除"只给情报与统计，不给买卖建议 / 不构成投资建议"字样（用户指定）；
  已写入 DANMU_INTEL_FRAMEWORK 1.6 产品收敛。
- 情报输出时间轴框架 + 闭环流水线 v1（2026-08-23）：
  新增 knowledge/INTEL_OUTPUT_TIMELINE.md——赛前 / S0-S4 / 局间 / 赛后 / 长期
  各时间点输出内容矩阵 + 页面类型（A/B/C）+ 完整性铁律；
  新增 tools/build_closed_loop.py（读报告预测验证 + matches.json -> 闭环页，v1 需人工复核）；
  闭环样例更新为报告口径 4 命中 / 1 落空 = 80%（WE vs LGD，site main c0640ce）。
- 闭环流水线 v2 落地（2026-08-23）：结构化预测字段（matches.json 每场 predictions[]：
  text / time / category / status / note）；
  新增 tools/record_prediction.py（局中记录 pending / 赛后回填 hit·miss）；
  build_closed_loop.py 优先读 predictions（无歧义），无则回退 HTML 解析（v1）；
  WE vs LGD 已回填 5 条（4 hit + 1 miss）并验证 v2 自动生成闭环页。
- 闭环发布脚本落地（2026-08-23）：tools/publish_closed_loop.py --match-id <id> --push
  一键生成闭环页并推送 danmu-intel 站点（已验证生成）；SOP 阶段 3/4 已写入
  预测记录（pending）与回填发布（hit/miss + push）步骤；REVIEW_SCHEMA 明确
  prediction_validation 来源 = matches.json predictions[]；DANMU_README 工具链同步。
- 历史场次预测回填 + 闭环统计上线（2026-08-23）：
  tools/backfill_predictions.py 批量回填 8 场 20 条预测（累计 25 条：
  17 命中 / 2 落空 / 6 待确认，已判定命中率 89% 17/19）；
  站点首页新增"闭环统计"卡（site main 0416db3）；
  Node Spec FINAL 节点接入自动闭环（回填 + publish_closed_loop --push）。
- 预测清理 + 每日检查 + 联盟代码（2026-08-23）：清理误回填的 6 条 pending
  （信号/观察非预测，predictions[] 只保留可判定预测；现 5 场 / 19 条：
  17 命中 / 2 落空 = 89%）；backfill 脚本跳过"待确认"行；
  首页闭环统计更新并新增 Monki 灰信号兑现 2/3（site main ed6c6b8）；
  新增 tools/daily_intel_check.py + runtime/run_daily_intel_check.command
  （每日看 Polymarket 电竞比赛，空结果必须过自检）；
  INTEL_HTML_TEMPLATE 头部加 Polymarket 市场链接约定
  （事件 slug + 联盟代码见 docs/data/intel/leagues.json id）。
- 灰信号兑现率全量统计 + 市场链接 slug + 每日扫描钩子（2026-08-23）：
  新增 reports/intel_gray_verification_stats.html（23 主体 / 2698 信号 /
  22 场次记录 / Monki 2/3 已判定，其余标"待积累"），已上线站点并加入口
  （site main c1ba46f）；
  matches.json 5 场补 event_slug（报告提取，市场链接可构建）；
  tools/daily_intel_check.py 新增 --scan（先跑 market_scanner --live 再出每日清单）。
- LoL 市场链接上线（2026-08-23，site main 333a76f）：11 场英雄联盟比赛
  （LPL / LCK / LEC）确认 event_slug 并生成 Polymarket 市场链接，首页新增
  "LoL 比赛 → Polymarket 市场"区块；08-22 场次与 CS / Dota 链接待补（后置）；
  build_closed_loop.py 闭环页增加市场链接行（有 slug 则带链接，无则"待补"）。
- 08-22 slug 校验 + 今日比赛更新（2026-08-23，site main 0270cac）：
  Gamma 校验确认 lol-we-lgd-2026-08-22（LPL Group Ascend）；其余 08-22 场次
  按防错规则不猜、标"待补"（后续扫描/公开索引补）；实时扫描（08-23 02:12 UTC）
  今日 Polymarket 白名单 = Dota2 TI 两场（BoomBoys / Team Yandex vs Team Spirit），
  LoL 今日暂无白名单场次；首页今日比赛卡已更新。
- 每日自动跑上线（2026-08-23）：
  站点工作副本迁移到项目内 .danmu_intel_site（已 gitignore）；
  tools/update_site_today.py 生成"近期比赛（自动生成）"页 intel/today.html
  （扫描窗口场次 + Polymarket 市场链接）；
  runtime/run_daily_polymarket.command = 扫描 -> 每日报告 -> 今日页 -> 推送站点；
  launchd 定时 com.adul9981.danmu-intel-daily（每天 12:00）已安装并加载；
  端到端验证通过（site main 4b9c993，today.html HTTP 200）。
- 弹幕情报输出全链路完成（2026-08-23，site main 944b126）：
  tools/publish_intel_pages.py 同步 168 个情报页（61 比赛页 + 105 画像页 +
  2 灰信号统计）到站点并自动生成索引页 intel/index.html（按日期分组 +
  画像 / 灰信号分区）；每日任务已纳入 publish 步骤；
  索引页 HTTP 200 验证通过。核心 = 直播平台弹幕情报输出，闭环成功率不再更新。
- 产品首页重建（2026-08-23，site main 840fb7d，HTTP 200 验证）：
  顶部导航（今日比赛 / 弹幕情报 / 市场链接 / 灰信号统计）+
  Hero 三问定位（做什么 / 信息价值 / 你获得什么）+
  数据底座（168 情报页 / 61 比赛页 / 23 灰信号主体 / 6 联赛）+
  今日比赛（自动扫描 + 市场链接）+ 弹幕情报入口（索引 / 灰信号 / 闭环样例 / 复盘示例）+
  LoL 市场链接 12 场 + 发布佐证闭环说明 + 边界页脚。
- 扫描修复 + 时间 + 时间轴页（2026-08-23，site main cae4dfc）：
  根因：白名单缺 LCS / 扫描 --live-limit 限页导致漏抓，只出 Dota；
  已补 LCS 关键词 + 恢复全量页数 -> 今日抓到 16 场（LPL 3 / LCK 2 / LCP /
  LEC 2 / LCS / Dota2 TI / CS2 EWC），带北京时间；
  update_site_today 显示比赛时间；新增 tools/build_match_page.py
  （比赛详情页：赛前 / S0-S4 / 局间 / 赛后时间轴 + 情报页链接，WE vs LGD 示例已生成）。
- 产品决策记录定稿（2026-08-23，docs/task/DANMU_INTEL_PRODUCT_DECISIONS.md）：
  grill 收尾共享理解——定位（只做直播弹幕情报输出、对外订阅）、$59/月 + 阶梯涨价（新用户生效、
  老用户锁价、早鸟 $39 年度锁定 10 名额验证）、免费=赛后复盘即时开放 / 付费=实时+节点情报、
  8 节点双层时间轴（系列×局）、节点情报卡 schema + 状态分级、访问码付费墙、
  中文+韩文、VPS 必须上线（朋友部署）、信任=可验证情报痕迹、合规=服务条款"数据仅供参考"一行。
- VPS 接手清单定稿（2026-08-23，docs/task/VPS_HANDOFF.md）：
  给朋友的交接文档——分工边界 / VPS 选购（香港/东京优先）/ 环境准备 /
  systemd 三件套（采集常驻 / 每日扫描 / 站点发布）/ 健康检查 / 交接检查单；
  目标 3-5 天内核心上线；部署包（tools+config+启动脚本）由 Agent 下一步打包交付。
- 比赛详情时间轴原型上线（2026-08-23，site main 9a7920b，HTTP 200 验证）：
  DNS vs NS K杯决赛（BO5 · 2026-08-18）——系列 × 局双层时间轴原型：
  G1/G2/G3 各含 BP / 局中情报 / 复盘 + 系列复盘；真实数据（shavel 盲僧天秀、
  Kinggen 一抢杰斯判死刑应验、G2 暂停灰信号、人头盘 39.5、DNS 3:0）；
  空缺节点标"待补充"不硬凑；局中情报为"每局一份"，
  关键节点（BP/10/20/30/末段）下一步补全展开。
  "节点情报卡"术语作废，统一为"时间点情报页"（对齐 LIVE_INTEL_SCHEMA / REVIEW_SCHEMA）。
- 统一模板 + 全站链路定稿（2026-08-23）：
  新增 docs/task/MATCH_DETAIL_TEMPLATE.md——两级选择器壳（局 -> 时间点 -> 完整情报页）、
  节点页约定（局中=中韩合并 / 复盘=10 段 / 系列=完整页）、网站主页结构、全站交互链路；
  tools/build_match_page.py 升级为通用生成器（自动探测节点页，缺失标"暂无"不 404）；
  已生成 WE-LGD / GEN-DK 两级壳并上线（site main 1934978，HTTP 200 验证）；
  交互链路：主页今日比赛 -> 比赛详情（局->时间点）-> 完整情报页 -> 画像/统计/市场链接。
- 一次错误原则固化（2026-08-23）：AGENTS.md 最高优先级防错规则新增第 12 条
  "情报关联防错 + 一次错误原则"——引用情报页必须做真实文件名存在性校验，
  任何"显示暂无"先验证关联逻辑；全项目情报过程错误犯过一次即固化防错规则/回归，
  绝不再犯。配套回归测试 tests/test_match_page_regression.py（6 项全绿，
  覆盖报告名连字符关联 + 详情壳引用页存在性）。
- 产品链路修正（2026-08-23，site main 698fe38）：① 英雄联盟只看 LCK / LPL / LEC，
  移除 LCS（白名单 + 今日页 + 首页）；② 列表不再直接跳市场——点击先进情报页/详情壳，
  市场链接放在情报页内（详情壳已带，未确认 slug 的标"待补"）；
  ③ 今日页为"赛程 + 情报入口"，不再是无价值清单；首页市场区块改为"已产出情报的场次"入口；
  自测通过：白名单无 LCS / today 无 LCS 且无直跳市场 / 详情壳含市场链接 / 回归测试 6 项全绿。
- 生成模板结合定稿（2026-08-23）：时间轴壳（局 -> 时间点）与既有
  INTEL_HTML_TEMPLATE（A/B/C + 10 段）结合为统一标准——每个节点 =
  按模板生成的完整页（赛前=A 骨架 / BP=B+BP 后战绩情报必抓 / 局中=B 递进 /
  复盘=B->A 升级 / 系列=A 全集 / 画像=C）；硬性门槛 6 条写入
  MATCH_DETAIL_TEMPLATE.md 第 5 节；DNS vs NS G3 页为样板。
- 联赛分类最高标准固化（2026-08-24）：两级分类（游戏 -> 联赛/赛事），
  LCK CL 独立、KeSPA Cup 独立、LoL 其他归并、CS2 / Dota2 统一；
  判定优先级（标题 -> 元数据 -> 队伍反推 -> 不硬猜）；已写入 AGENTS.md 通用约定，
  实现于 tools/build_history_index.py normalize_league（32 场 0 未知）；
  后续优化（如 CS2 细分赛事）须先改本标准再实现。
- 历史情报库纳入每日流水线（2026-08-24）：run_daily_polymarket.command
  新增 build_history_index 步骤（扫描 -> 每日报告 -> 今日页 -> 历史库重建 -> 发布推送），
  新比赛情报入库后历史筛选页每日自动更新；也可手动跑：
  python3 tools/build_history_index.py && （站点 git push）。
- B/C 项落地（2026-08-24，site main f62914e）：历史库顶部统计卡
  （场次 / 覆盖联赛 / 结果已回填 / 完整度）+ 无情报 LoL 场次说明；
  新增画像速查页 intel/profiles.html（109 个队伍/选手/联赛画像）+ 404 页；
  首页弹幕情报区新增画像速查入口。A 项（结果回填 + 可验证痕迹页）后置。
- C7 灰信号主体验证状态表 + B-SEO（2026-08-24，site main 5ad0818）：
  tools/build_gray_stats.py 自动生成灰信号统计页（26 主体 / 信号量 / 严重度 /
  覆盖场次 / 验证状态：Monki 2/3 已判定、其余"待积累"），随数据自动更新；
  历史库 / 画像速查 / 今日页 / 灰信号页统一补 meta description。
- A 项完成（2026-08-24，site main beb2671）：历史库结果回填 0 待回填
  （28 场全部官方 / Polymarket 结算 / 多源确认；汇总页剔除 + 队伍别名归一化
  fox=bfx / juhua=Legacy / mkoi=koi 等）；
  新增「可验证情报痕迹」页 intel/verification_traces.html（BP 锚点应验 /
  灰信号兑现 / 观众预测命中，单条可溯源）+ 首页入口；
  界面链路完整可分享：首页 -> 历史情报库 -> 比赛详情 / 痕迹页 / 画像 / 灰信号。
- 市场链接入口调整（2026-08-24，site main 2d4c796）：新增「最新市场链接」自动页
  intel/market_links.html（今日 + 本周，随每日流水线更新，14 场有确认 slug）；
  首页市场区只留"最新"入口，过往历史链接全部收进历史情报库。
- 临时过渡方案确定（2026-08-24）：VPS 只做 7×24 弹幕采集，分析/情报/发布留本地。
  docs/task/VPS_HANDOFF.md 重写为过渡方案版（部署只启用 danmu-session.service；
  数据回传 tailscale/rsync -> docs/data/danmu/；检查单）；部署包 v2 已重新打包
  deliverables/danmu_intel_vps_deploy.zip：新增 tools/vps_capture.py（读直播间
  注册表自动启动 11 房间采集 + 跨天滚动 + 异常重启），修复 danmu-session.service
  缺 --room 必失败问题（INTEL_PY 可配置解释器 + systemd 改 vps_capture 入口），
  deploy.sh 过渡期只启用采集服务。
- 历史库漏关联修复（2026-08-24，site main 455295c）：build_history_index 原只
  解析无后缀报告名，带 _BP_/_G1_/_G2_/_full_/_S0_ 后缀的节点报告全漏
  （KC-SHFT 4 节点 / T1-HLE / KC-GX 曾不可见）；现支持后缀+中文队名+特殊文件
  映射（CS-绿龙-Legacy = Spirit vs Legacy），官方日期与采集日期 ±1 天自动合并；
  历史库 20 -> 33 场全结果回填；新增回归测试（每个可解析情报页必须进历史库），
  40 项全绿；教训固化于 DANMU_CAPTURE_RULES 15ter。
- 服务器 Codex 方案讨论（2026-08-24，docs/task/SERVER_CODEX_PLAN.md）：
  用户拟自租云服务器 + 朋友安装 Codex CLI，实现弹幕采集与情报输出 7×24 上云；
  评估：可行，分两步（先采集脚本上云，再 Codex 分析上云）；硬件建议
  2 核 / 4GB / 80GB（Codex 官方要求 RAM 4GB 最低、Ubuntu 20.04+、无需 GPU），
  节点定为香港（用户指定；DigitalOcean 无香港，平台定为 Vultr HKG），
  约 $18-24/月；手把手步骤 docs/task/SERVER_SETUP_STEP_BY_STEP.md；待购买 + 部署。
- 服务器部署完成（2026-08-24）：Vultr 首尔节点（用户实际购买为韩国，非香港）
  158.247.214.175 / Ubuntu 24.04 / 2C4G80G；danmu-session.service 已启用并稳定运行，
  虎牙多直播间（官方流/毛毛/米勒/硕硕等）+ SOOP LCK CL 实测采集成功；
  部署踩坑已修复并重新打包部署包 v3（deliverables/danmu_intel_vps_deploy.zip）：
  aiohttp 依赖缺失、real-url danmaku 库 vendor 化（含 Crypto/protobuf==3.20.3）、
  danmu_live_monitor 对 SOOP message 字段与 ts 类型兼容、deploy.sh 重复解压跳过复制 +
  python3-venv 自动安装；本地 41 项回归测试全绿。
  ⚠️ 韩国节点实测 Polymarket 全站返回 HTTP 451（地区限制）：当前过渡方案不受影响
  （采集仅需虎牙，Polymarket 扫描在本地）；未来需服务器读 Polymarket 时须换香港
  或加代理（见 SERVER_CODEX_PLAN.md）。
- 弹幕数据同步方式定稿（2026-08-24）：**按需同步**——用户对话时由 Agent 执行
  tools/sync_danmu_from_vps.sh 把服务器 docs/data/danmu/ 增量拉回本地后分析；
  launchd 每日自动同步方案因 macOS TCC（完全磁盘访问）拦截 Documents 写入而弃用
  （根因已记录，勿再尝试；已卸载清理）。
- 情报栈全量上云（2026-08-24，阶段 2 主体完成）：本地情报能力已整体部署到
  158.247.214.175 /opt/danmu-intel——tools/ 82 脚本、knowledge/ 38 文件、
  docs/data/intel/ 17 JSON、config/schemas、AGENTS.md、6 个情报 skill
  （路径已改 /opt/danmu-intel）、Codex CLI 0.149.1；规则层自检全通
  （danmu_intel 真实弹幕出情报 / gray stats / verify_match_end / history index）；
  Codex CLI 已配 DeepSeek（deepseek-v4-flash，OpenAI 兼容接口）并实测跑通
  （codex exec 读文档出准确总结，tokens 12,879）——无需 ChatGPT 登录，
  服务器无头 Agent 可用；key 存 /root/.codex/config.toml（600）。
  详见 docs/task/SERVER_INTEL_STACK.md。
- 服务器情报流水线已部署（2026-08-24，阶段 3 事件触发全自动）：
  vps-intel-pipeline.timer 每 5 分钟跑 tools/vps_intel_pipeline.py——
  读今日比赛清单（本地 export_today_matches.py 导出同步）-> verify_match_end
  弹幕多信号检测结束 -> 切片 + danmu_intel 规则层 -> codex exec（DeepSeek）
  按 intel-report 技能生成整场情报页 HTML；幂等状态 runtime/vps_intel/；
  实测 15 场全部正确检查（未结束=未确认等待）；今晚 LEC 比赛结束将自动产出首篇。
- 云端情报产出实测成功（2026-08-24）：HLE-BFX（硕硕）、DNS-KRX（SOOP）局中
  情报页由服务器 Codex+DeepSeek 独立生成，质量达本地水平（对阵/进度/联赛口径
  推断、韩文中文化、密度时间线、灰信号纪律、结果待定标注）；自动流水线已自动
  产出 DN SOOPers-Kiwoom DRX（需人工确认）与 BFX.Y-HLE.C（确认结束）两篇整场
  情报页。方向性情报结构（正锚/负锚/群体共识/灰信号条件预测）已固化进
  INTEL_HTML_TEMPLATE 二.8 与流水线 prompt。
- 正式产品上线推进（2026-08-24）：新增订阅页 subscribe.html（免费=赛后复盘 /
  Pro=$59 月·季 9 折·年 8 折·早鸟 $39 限 10 名、QQ/TG 登记 + 访问码发放、
  每满 20 人涨价 10-20% 老用户锁价），首页导航 + hero CTA 加订阅入口；
  服务器自动产出情报页已发布到站点（239 页同步、索引重建、GitHub Pages 推送）。
- 站点展示优化 + 全站角标（2026-08-24）：历史情报库结果列截断（悬停看全文）、
  新增关键词搜索框、无结果空状态、移动端上下排列；favicon.svg（SAP 蓝渐变
  弹幕气泡图标）注入全部 462 页（tools/add_favicon.py 幂等工具 +
  build_history_index/publish 生成器内置），线上验证 200。
- 情报规则 V2 起草（2026-08-24，docs/task/INTEL_RULES_V2.md）：① 信息源扩展
  Twitch/Kick（注册表 platform 扩展、落盘/字段/中文化/词表要求，采集器待开发）；
  ② 情报输出双格式 HTML+MD（MD 为入库核心、HTML 为站点展示，章节规范已并入
  INTEL_HTML_TEMPLATE 二.9）；③ 新 MD 情报库 docs/data/intel_md/（按比赛组织 +
  自动索引）；规则已同步云服务器；待用户补充具体要求文本（频道清单/MD 模板/
  组织偏好）后校准并开发。
- 情报规则 V2 与项目库对齐并全量上云（2026-08-24）：项目库已含 Twitch/KICK
  实测接入（PLATFORM_ONBOARDING_METHODOLOGY.md 六步法 + TWITCH/KICK_CAPTURE_
  RESEARCH.md + fetch_twitch/kick_danmu.py + 注册表 12 个新频道）+ MD 情报库
  knowledge/intel_pages/（250 个 MD：比赛/画像/索引/intel_library_taxonomy v1）；
  已同步云服务器：采集器、4 平台 23 房间注册表、MD 情报库、INTEL_RULES_V2.md；
  重启 danmu-session.service 后 Twitch 8 频道 + Kick 4 频道已开始采集并落盘
  （实时验证：Twitch 231 条、Kick gaules 4 条）；SOOP 连接偶发重启观察中。
- 页面功能逐项检查 + 订阅配置（2026-08-24）：主页今日分区、今日页赛程/详情分组
  （未开始/进行中/已结束 + 结果待回填标注）、本周未开始重点、历史库搜索/待定标注、
  全站导航逐页验证通过；订阅配置参考马斯克工具同款实现——
  api/verify-member.js（会员验证：TG 用户名/QQ 号 × 名单 + expires）+
  api/lead.js（登记推送站长 TG）+ 名单模板 data/members.example.json +
  订阅页会员验证/订阅登记表单；API 已部署 Vercel（danmu-intel-api.vercel.app，
  已关闭部署保护，verify-member 实测可用）；待配置：TELEGRAM_BOT_TOKEN/
  TELEGRAM_CHAT_ID（lead 推送）、MEMBERS_GIST_RAW_URL（会员名单）。
- 订阅登记 + 网站实时更新打通（2026-08-24）：订阅登记 API 已配 TG 凭据
  （来自 musk-tweet-quant-v2/.env），登记提交实时推送站长 Telegram（实测 success）；
  服务器 GitHub Deploy Key（~/.ssh/github_deploy）已加入 danmu-intel 仓库，
  vps-publish.timer 每 5 分钟自动把 reports/ 情报页推送站点
  （实测 pushed 13 files，Navi-FNC 情报页服务器自动上线 200）；
  数据端完备性原则（AGENTS.md 第 13 条 + CAPTURE_RULES 第 17 节默认采集集）
  已确认并同步云服务器。
- 网站轻量统计上线（2026-08-24，免第三方账号）：页面打点 -> Vercel
  /api/track 中转 -> VPS stats-server（systemd 常驻 8080，events.jsonl 记录），
  统计页 stats.html（累计 PV / 今日 PV / 页面浏览排行，调 /api/stats）；
  全站 469 页注入打点脚本（tools/add_stats_track.py）；端到端实测通过；
  待优化：vps_publish 自动推送的新页面补打点、Cloudflare 更全数据可选后续。
- 订阅付费墙上线（2026-08-24 晚）：Pro 层（局中/节点情报：_live/_pre/_BP_/
  _G1_/_G2_/_G3_ 与 match_* 时间轴壳，共 38 页）加载时会员校验（localStorage
  24h 缓存 + 验证输入框 -> /api/verify-member），通过解锁；免费层（赛后整场
  复盘）保持公开；会员名单存服务器 members.json（VPS /members 接口，
  优先于 Gist），朋友开通 = 名单加 TG 用户名或 QQ 号（含 expires），
  免费期今晚结束（FREE_UNTIL=2026-08-24）；实测：friend_demo（TG）与
  100001（QQ）均解锁、陌生人拒绝、Pro/免费页分层正确。
- 多时间点情报 + 时间轴壳实现（2026-08-25）：服务器流水线按节点产出——
  赛前（开赛前 60 分钟内 _pre）、局中快照（每 30 分钟 _live_<HHMM>，不再覆盖）、
  赛后整场；每场自动生成时间轴壳 match_<mid>.html（赛前/局中多点/赛后 iframe
  切换，tools/vps_intel_pipeline.build_timeline_shell）；vps_publish 发布
  match_*.html；今日页"情报"入口优先指向时间轴壳；多节点切换实测通过
  （赛前/局中 23:00/赛后 三按钮）。
- 情报要求刷新 + 精细化情报库沉淀计划（2026-08-25）：读齐权威要求
  （DANMU_README / WORKFLOW Node Spec（系列×局双层）/ CAPTURE_RULES 17 /
  INTEL_HTML_TEMPLATE 二.8/二.9）；服务器流水线同步差距——情报页加
  "实际/预期/缺口"完整性三栏、节点命名对齐规范（S0 赛前 / IN-GAME /
  FINAL 系列复盘）、每场必给长期沉淀点；沉淀路线图落文档
  INTEL_LIBRARY_SEDIMENTATION.md（后续：BP 黄金窗口/OPEN/局间、V2 结构化
  库同步、MD 双格式、画像沉淀、闭环 v2）。
- 比赛状态与结束检测大排查（2026-08-25）：发现并修复——① 服务器流水线曾把
  未开始/刚开赛比赛误判"已结束"并生成假复盘页（GX-G2、CS2 10 场、Navi-FNC
  共 10 个，已删除服务器+站点误判产物）；② 页面状态用扫描快照导致已结束
  比赛显示"进行中"（BLG-AL/BoomBoys 等）；③ 跨时区 UTC 日期误判；
  修复：结束检测加"已开始≥30 分钟"门槛、状态判断真实时间优先 + 完整情报页
  权威信号、今日清单/今日页按 08-25 重新扫描生成；机制固化 AGENTS.md 12d。
- 数据正确性防错清单 + 防线补齐（2026-08-25）：新增
  docs/task/DATA_INTEGRITY_CHECKLIST.md（E1-E24 全类别：状态/时间/关联/
  数据源/真实性/站点/权限 + 已修与待补防线）；状态判断抽公共函数
  tools/match_status.py + 6 项回归测试（未开始/已结束/closed/full 权威信号/
  跨时区/进行中，47 项全绿）；每日流水线加入 export_today_matches + 首页/
  统计重建 + 服务器清单同步（run_daily_polymarket.command）。
- 网站框架统一重建（2026-08-25）：参考 Polymarket/Apple/SAP 制定
  SITE_FRAMEWORK_STANDARD.md——全站统一顶栏导航（品牌+5 链接，sticky 不跑位）、
  二级页面包屑、favicon 全站、统一卡片布局；add_site_nav.py 重写为统一
  nav/面包屑替换式注入（修掉 intel 子页 ../intel/ 路径错误 276 处）、
  add_favicon.py 支持批量注入；vps_publish 集成 nav+favicon（服务器自动
  产出页同框架）；LEC 数据问题修复：今日清单保留跨日进行中比赛（GX-G2 恢复
  局中产出）、Navi-FNC 正确复盘重生成；CS2 IEM 预选队伍补联赛映射。
- 网站框架幂等化 + 回归锁定（2026-08-25）：修复注入脚本不幂等导致的
  重复面包屑（曾堆叠 7 条）；add_site_nav.py 重写为"先清理旧 nav/面包屑、
  再注入唯一一份"，每页 1 导航 + 1 面包屑 + 1 favicon、无 ../intel/ 残留；
  新增 tests/test_site_framework.py（导航/面包屑/角标/幂等 5 项），
  52 项测试全绿；服务器产出页经 vps_publish 自动套用。
- 导航重复/字体/发布修复（2026-08-25）：清理全部旧顶栏 div.top
  （27 个比赛壳 + 情报页，导航曾出现 2 套）；统一导航链接固定字号
  （13px，修复各页字号忽大忽小）；修复 add_favicon 路径写死导致
  vps_publish 一直崩溃未推送（GX-G2 整场情报 18:09 已生成但未上线，
  现已推送，今日页有入口、情报页 200）；说明：Navi-FNC/GX-G2 只有
  赛后复盘是历史数据缺口（比赛发生在多节点功能完善前），后续比赛
  按标准产出赛前/局中/赛后节点。
- 导航样式统一 + 双端发布冲突根治（2026-08-25）：导航链接补全完整内联样式
  （text-decoration:none + font-size 固定 13px/品牌 14px + font-weight 固定，
  当前页才加粗），全站统一（首页/订阅/今日/历史线上验证一致）；
  记录防错清单 E25（导航样式）/ E26（双端发布冲突）；vps_publish 改为
  以远端为基线（fetch+reset --hard origin/main）后复制/注入/推送，
  解决服务器与本地持续冲突导致情报推不上去的问题（实测 rc=0）；
  框架回归测试增至 6 项，全量 53 项通过。
- 问题教训台账建立（2026-08-25）：docs/task/LESSONS_LOG.md 集中记录
  全部已发生问题（A 数据/状态 12 条、B 采集/部署 10 条、C 站点/导航/发布
  11 条、D 内容/订阅 5 条），每条含根因、防线、记录位置；新错误流程 =
  先登记台账 -> 定位根因 -> 固化 -> 回归测试；与 DATA_INTEGRITY_CHECKLIST
  （E1-E26）和 AGENTS.md 防错 1-13 对齐，防"修一个漏一类"。
- 结果自动回填 + 今日页/历史节点优化（2026-08-25）：新增
  tools/backfill_results.py——从 Polymarket 结算自动拉取赢家回填
  matches.json（覆盖服务器产出场次），已回填 13 场、待回填 0；
  已加入每日流水线（run_daily）；今日页情报详情区简化（只留比赛+入口，
  详细见比赛页）；21 场历史比赛壳重建为多局（G1/G2/G3）×节点
  （BP/局中/复盘）可切换。
- 免费/付费边界调整（2026-08-25）：免费开放赛后复盘、历史库、画像、
  灰信号统计、可验证情报痕迹、灰信号兑现率；付费锁定实时局中、赛前节点、
  方向性情报（40 个实时/赛前节点页）；比赛时间轴壳免费进、节点按需锁；
  订阅页说明更新；回归测试锁定边界（63 项全绿）。
- "有节点即可见"原则固化（2026-08-25）：多节点比赛端到端核对——7 场
  全部 壳+历史库入口+节点页可访问 OK；回补机制改为每生成一个节点立即
  重建壳（节点生成即进壳，不等整场完成）；核对逻辑（扫描"多节点比赛
  -> 壳 -> 历史库入口 -> 节点存在"）作为防漏校验。
- 剩余待办：VPS 过渡方案部署（等朋友，部署包 v2 已发）、付费墙（后置）、
  每日流水线端到端验证（本机 08-24 已跑通，VPS 上线后复核）。
- GitHub 项目创建并推送（2026-08-18）：https://github.com/Adul9981/esports-intel-library（私有）。
  内容：README / 产品框架 / 成果清单 / 合作伙伴待办 / 数据说明+采集目标 / 经验清单 / 假赛库 /
  弹幕情报（聚合） / data（反转统计 CSV、联赛分布、黄金样本、T1 vs DNF 摘要）/ preview（两个 HTML 预览页）。
  边界：不含私钥、不含裸弹幕流与用户身份、假赛内容为疑似标注；如需公开或添加朋友为协作者可后续调整。
- GitHub 仓库补充完整内容（2026-08-18，main eda33cb）：弹幕脚本（fetch_huya_danmu / danmu_intel /
  danmu_live_monitor / danmu_report 等 13 个 tools）、完整框架文档（framework / runbook / task /
  forensics 子目录）、知识画像（队伍 / 联赛 / 英雄 / 主播 / INTEL_SIGNALS / DANMU 规则 / EDGE LOG /
  DO_DONT）、数据报告（弹幕简报 HTML / 回测 / 扫描 / 形态巡检 / LEC 统计）、schemas；
  README 更新目录树与脚本说明；原始弹幕 JSONL（含用户身份）不进入公开仓库。
- GitHub 仓库清理（2026-08-18，main 19dc2e0f）：只展示 Polymarket 电竞情报库核心内容——
  交易者拆解域（archive/forensics，含温度/足球/棒球等非电竞案例）与执行手册（archive/runbook）
  移入 archive/（保留在 git 历史，可恢复）；README 与相关引用同步更新；
  当前顶层：README / archive / data / docs / preview / schemas / tools。
- 数据采集协作收尾：朋友自行爬取数据，本仓库不再对接其纳秒级订单簿日志；打点程序 v1 保留在 tools/ 作为参考（任务 6 里程碑 M0 的翻盘画像可复用打点数据思路），暂不推进 v2（打点 + 记录）开发；临时打包文件 event_marker_v1.zip 已删除，需要时可从仓库重新打包。
- 策略 A/B 模板定稿（用户拍板完成）：S1 拆两档（S1-深反彩票：15c->2c 七档、金额随价格下降递增，止盈 50/70/85 + 20% 彩票；
  S1-标准中位：40/32/25/20c，止盈 55/70/82 + 15% 彩票，默认保守版）；
  S2 修正为热门深回撤（赛中 50/45/40c 接，止盈 62/75/88 + 10% 彩票）。
  已落地 docs/framework/STRATEGY_PATTERN_LIBRARY.md 与 config/strategy_templates.json（D2 增加深反版变体）。
  S1-深反/S1-标准/S2 上线前需 dry-run 验证生成器兼容（新增 A_STANDARD_MID_REVERSAL key、档位数变化）。
- A/B 第二版细化（2026-08-07）：S1-深反金额表定稿为均衡权重 1/√价格（15c:$5.5 -> 2c:$15，总 $60）；
  止盈改为"卖高留低"按档位归属（50c 卖 15/12、70c 卖 10/8、85c 卖 6、彩票 4/2）；
  WE G1/G2 1 分钟真实数据回测完成（reports/deep_reversal_ladder_backtest_2026-08-07.md）：
  先卖 15/12/10 三档在 50c 即回本并锁利（G2 回款 131% 成本、G1 回款 301% 成本）。
- 新增 P-早建仓模块（五五开开局 -> 全局领先场景；50-60c 分三档早买 + 回撤补，>60c 不追；属于 P 模块子类，避免与现象标签 P2 混淆）。
- 新增核心纪律"价格优势线 60c"；风险三池分离原则（彩票池占总资金 10-20%，稳定池 + D6 熔断）。
- 工具升级项：sell plan 按档位归属执行（lot-based selling，先卖高成本档留低档），当前 sell_cost_basis 按平均成本混合，需升级。
- 中位入场定为首期主攻（2026-08-07）：S1-标准 + S2 + P-早建仓，统一"买80回收"模式
  （中位 30c 入场 -> 60-70c 卖 80% 成本回本锁利 -> 剩 20% 彩票；算例保底 +60%）。
  S1-深反与环节 4（彩票机器）一并暂缓，设计/模板/回测保留不删；中位模式补 D3 止损线
  （跌破成本一半或末段未反弹 -> 主动离场）。
- 执行管线定稿（2026-08-07）：发现 -> 路由 -> 计划生成（半自动，用户确认）-> 执行（D4 进场三件套）
  -> 监控（D3 状态机，10-30s 轮询 + 最新成交价）-> 退出（交易所休息挂单为主 + D2 锁盈）-> 复盘闭环。
  架构原则：监控管状态、挂单管退出；自动化可行性评估记为第 10 节环节 5 待办。
- 半自动确认边界定稿（2026-08-07）：开赛前定下策略后，买入 + 监控 + 挂止盈全部自动、无需再确认；
  中位止损确认：跌破成本一半离场 + 末段（最后 5 分钟）未反弹离场；
  单场预算默认 <=70，全仓需显式指定并触发风控提示（昨日赛前 50-50 全仓标记为高风险手动样本）。
- 新增策略体系总览文档 docs/framework/STRATEGY_SYSTEM_OVERVIEW.md：把现象/策略/执行模块/管线/
  半自动边界/止损/风控整合为执行入口级总览（策略梳理的核心交付）。
- 单场预算定为 80 USDC（2026-08-07 用户确认推荐档）：config/risk_limits.json 单市场上限 70->80，
  A/B max_cycle 同步 80；验证后可升 100（届时单日 200 下并发最多 2 场）。
- "赛前买一部分"确认不建独立策略：= P-早建仓模块 + 主策略（S1-标准/S2）组合；
  底仓 <=30% 预算拿入场资格，赛中按价格区间接力，pre-position 与策略新仓分开记账，D2 统一锁盈。
- 案例样本 +1（2026-08-07，HLE Challengers vs DRX Challengers）：P5+P1 复合样本入库，
  Moneyline 5.5c -> 86.5c（约 16 倍窗口），G1 领先被翻盘 + G2 接近判死后翻盘 + G3 尾盘崩塌；
  快照 docs/data/snapshots/2026-08-07_lol-hle-drxc/；P5+P1 案例累计推进。
- 中位组合回测完成（2026-08-07，reports/midband_backtest_2026-08-07.md）：
  21 个市场 1 分钟真实价格，买80回收 + 跌破成本一半止损。
  保底收益率符合公式（30c 入场 70c 卖 +87%、80c 卖 +113%）；
  无方向过滤时止损触发率 68-93%（样本以 08-05 亏损日为主）——结论：中位规则必须叠加方向选择，
  止损只负责把 -100% 压到 -50%；Liquid G1 / YB1 G1 反例显示系统性低吸可把手动亏损变盈利。
- 止损触发率修正回测（2026-08-07）：此前全 100% 为数据假象（08-05/08-06 市场公开接口仅
  5-13 分钟粗粒度 + 窗口裁剪把赛后平台段算入）。修正为穿越入场 + 电竞市场 + 用户方向后：
  S2 45c->62c 止损率 50%、P-早建仓 55c->70c 55%、S1-标准深位 70-91%。
  数据粒度限制确认环节 5"数据粒度评估"的必要性（需 1 分钟/事件级数据源）。
- 策略收益率与可实现性评估定稿（2026-08-07，见 STRATEGY_SYSTEM_OVERVIEW.md 第 10 节）：
  定稿策略 3 个（S1-标准 / S2 / P-早建仓）。收益率：深位 25c->70c 保底 +124%，
  S2 45c->75c 保底 +33%，P-早建仓 55c->70c 保底 +2%；触发率 45c 档最高（71%）。
  主攻 S2 45c 档 + P-早建仓；S1-标准深位小仓；止损率回测不再做（用户判定无意义）。
- 中位80（Mid80）命名与快速优化（2026-08-07）：统一名称"中位80"；S2 权重向 45c 集中
  （48/45/42，$24/$32/$24），止盈 62/75/88 + 10% 彩票；S1-标准预算扩到 80（$24/$24/$16/$16）；
  早买模块去掉 56-60c 档（55c->70c 保底仅 +2%）。配置已更新 config/strategy_templates.json。
  执行前需 dry-run 验证生成器兼容（S1-标准 key、档位变化），再按 V1 流程下单。
- 自动化脚本调整完成（2026-08-07）：tools/grid_config_generator.py 增加模板加载器，
  A/B 计划优先读取 config/strategy_templates.json（A->中位80-S1、B->中位80-S2），模板缺失才回退旧逻辑。
  dry-run 验证通过：B 生成 48/45/42 + 62/75/88 + 彩票8 + stop35；A 生成 40/32/25/20 + 55/70/82 + 彩票12 + stop18。
  效果：执行对话只需说"链接 + Game + 方向 + 策略名"，即可自动生成正确计划，无需手动改档位。
- KT vs Gen.G Game 1 实盘（2026-08-07，中位80-S2）：Gen.G 方向，48/45/42c 三档买单已挂出
  （$24/$32/$24，订单 live），监控运行中；等待回撤成交，成交后自动补 62/75/88 止盈。
  结果：Gen.G 赢下 Game 1，价格全程未回撤到 45c 档，三档买单零成交；
  小局结束后 resting 订单被交易所标为 INVALID（零成交、零风险），已停止监控。
  这是"没跌到那个位置就不买"的正常结果；首次执行曾因余额不足失败，充值后重跑成功。
  后续可选：给 Game 2（GenG 66.5c，1-0 领先中）挂同样 Mid80-S2 计划。
- 余额预检上线（2026-08-07）：grid_plan_runner.py 下单前调用认证 CLOB balance-allowance
  （asset_type=COLLATERAL），可用余额 < 计划所需 x1.05 时直接终止，不挂任何订单；
  支持 --skip-balance-check 跳过；monitor-only / dry-run 不检查。
  已验证：钱包余额解析正确（约 148.37 USDC），今天的"下单时才报余额不足"问题被前置拦截。
- 策略研究工作交接文档建立（2026-08-07）：docs/task/STRATEGY_RESEARCH_HANDOFF.md，
  汇总策略全量清单、材料位置、已定稿结论与未决问题；新的策略研究会话从该文件开始。
- WE vs TT 复盘入库（2026-08-07）：TT 2:1 赢系列赛（Moneyline 29.5c -> 99.95c）；
  用户观点（TT 下狗反转）正确但执行错位——买 WE 10-15c 接刀 $70，抢救回 $20 亏约 $50；
  1 分钟快照 docs/data/snapshots/2026-08-07_lol-we-tt/；P5 下狗反转 + 领先被翻盘复合样本。
- FOX(BFX) vs BRO 复盘入库（2026-08-07）：BRO 2:0 赢系列赛；G1 BFX 98.5c -> 0.05c 仅 1 分钟
  （BRO 1.5c -> 99.95c），Moneyline BFX 75.5c -> 0.05c 死亡螺旋；用户 50-65c All in 未止盈，
  亏损但不后悔（考验运气/状态）；1 分钟快照 docs/data/snapshots/2026-08-07_lol-fox1-bro2/；
  尾盘极限反转 + 下狗反转 + 热门被翻盘复合样本。
- BLG vs TES 复盘入库 + 队伍画像建立（2026-08-07）：TES 2:0 赢系列赛；G1 BLG 93-94.5c 约 8 分钟
  （约 1 万经济领先）后 15 分钟被反超归零，Moneyline 84.5c -> 0.05c；
  1 分钟快照 docs/data/snapshots/2026-08-07_lol-blg-tes/；
  新增 knowledge/TEAM_PROFILES.md 队伍画像（BLG 领先会浪/送、TES、WE 打野核心、T1 下路+辅助）。
- 1 分钟快照取数工具化（2026-08-08）：新增 tools/fetch_price_snapshot.py（发现回测链，只读），
  取数逻辑与坑位写入 docs/data/DATA_COLLECTION_GUIDE.md 第 9 节；
  现有 5 场快照统一由该工具口径生成。
- 1 分钟 bar 监控可行性确认（2026-08-08）：活跃市场实测 prices-history 窄窗口返回 60s 间隔、
  最后一条延迟约 40-60s——比赛过程中可用；已作为下一个开发项写入
  STRATEGY_RESEARCH_HANDOFF.md 第 7 节（bar 监控 + 挂单决策程序，止损保护仍用实时中间价）。
- CS Liquid vs fnatic 数据修正（2026-08-08）：复核后确认 Liquid 2:0 赢系列赛；
  G1 Liquid 深跌至 16.5c 后翻回 99.95c（下盘极限反转），G2 55c -> 99.95c，
  Moneyline 50.5c -> 99.95c；08-05 日复盘"数据源混乱"修正为"深反翻盘，接刀后拿住即大赢"；
  快照 docs/data/snapshots/2026-08-05_cs2-tl1-fnc/（5 分钟粒度，该市场 API 无 1 分钟数据）。
- 融入新策略库（2026-08-08）：REVERSAL_PATTERN_LIBRARY.md 新增"深蹲判别器"
  （快速反弹 vs 死亡螺旋的 4 条可观测信号 + 躲开清单）与"分辨率容错/深跌基准率"；
  LOTTERY_MACHINE.md 新增"数据分辨率容错"（低成交量市场触发降级规则）与深跌基准率
  （43% 反弹到 50c，中位 16 分钟）。
- 2026-08-07 全量 10 场比赛分析（2026-08-08）：批量 1 分钟数据已与单跑存档校验一致
  （共同时间戳价差全 0）；新入库 6 场快照（JDG/EDG + 5 场 CS2 EWC）；
  已验证形态大面积复现（A1/A2/A4/B1/B2），CS2 深反首次正式赛验证（FOKUS G1 9c）；
  新空白：热门无回撤=低交易价值、五五开开局碾压反面样本；
  报告 reports/lastnight_analysis_2026-08-07.md。
- 框架六点落地（2026-08-08）：形态频率/形态气候、双边形态、赛前情报层、可成交性参数化、
  未知形态通道、D3 重新进场触发条件——全部写入对应文档；
  术语统一（下狗=赛前低赔率方；落后侧/下盘=盘中暂时落后方）已入形态库；
  情报库功能点 1/3/4 已登记（TASK6 4.5 节）。
- 六点执行落地（2026-08-08）：tools/classify_pattern.py 形态分类工具（启发式 v1.1）
  已对全快照产出频率统计（B4 28 / A3 11 / A2 8 / A1 5 / A4 4 / B2 4 等）；
  TEAM_PROFILES 结构化为队伍画像表；可成交性参数入 config/risk_limits.json；
  形态库/情报库/交接文档同步更新。待办：形态标签自动化接入 bar 监控程序、D3 重新进场落地执行器。
- SHU/NRG Moneyline 异常复核（2026-08-08）：G1/G2 均已结算 NRG 99.95（NRG 2:0 确定）；
  Moneyline 末条 19:46 出现互补报价（NRG 0.513 / SHU 0.486，价和≈1.0），与 17:44 的 99.95 冲突，
  判定为疑似结算前尾部重定价或抓取窗口异常——保留原始数据、标"结算待确认"，网络恢复后复核最终结算。
- 形态分类器校准 v1.2（2026-08-08）：C2 五五开开局碾压阈值放宽（0.35-0.62 开盘、低点 ≥33c），
  新增 B4_低开阴跌变体；全库 61 序列重跑：未知 10 -> 3（仅 SHU/NRG Moneyline×2 + HLE Moneyline，
  均为异常/未结算序列，正确进观察池）；C2 2->8、B4 低开 6。
- HTML 页面同步（2026-08-08）：反转形态库页新增"深蹲判别器/深跌基准率/形态气候/分辨率容错/未知通道"区块，
  补 FOKUS（CS2 深反首证）、Liquid 修正、PAR 尾盘崩塌、开局碾压变体样本；策略页补 S2 低交易价值说明。
- 补充建议处置（2026-08-08，用户逐项拍板）：
  - 做：① 边际信息登记（EDGE LOG，knowledge/EDGE_LOG.md，并入情报库）；
    ② 预期情形盘中验证闭环（knowledge/EXPECTATION_VERIFICATION.md）；
    ⑧ 结算历史回填（先联赛级翻盘率，登记为情报库功能点 7）。
  - 后台化：④ 统计层分析（形态频率/期望值矩阵/EDGE 统计 = 内部后台，前台只出结论，已写入 TASK6）。
  - 归档：③ 期望值矩阵口径入形态库（三.7 统计层），D-EDGE 入策略库执行模块。
  - 低优先/暂缓：⑤ 盘口回测（手续费存在、滑点可接受，不专门做）、⑥ 尾盘退出成交率
    （所选比赛多为高成交量）、⑨ 战局快照（用户想做但暂抓不到 Livestats，登记为数据缺口）、
    ⑩ 预盘数据（有价值暂不可得，登记为数据缺口）。
  - 有异议：⑦ 相关敞口合并（用户有异议，暂不推进）。
  - 转执行层：⑪ bar 监控程序、⑫ 分类器 golden set（人工复核标准集）。
- 三层分工确认（2026-08-08）：复盘层（案例/样本/纪律沉淀，已有成果）-> 策略层（本会话：
  形态库/策略库/彩票机器/EDGE LOG/预期验证）-> 执行层（bar 监控、golden set、扫描器 live 验收、
  D3 重进场落地，后续会话）。
- EDGE LOG 结构化落地（2026-08-08）：knowledge/edges.json + tools/edge_stats.py；
  首批回填 6 条，统计可出（有信息差 n=3 平均 +250 vs 纯信心 n=3 平均 -51.7），
  但样本 <15-20/组且含口述估值、未归一化——仅登记与方向观察，结论待自动累计。
- 今日作战速查建立（2026-08-08）：docs/runbook/TRADING_PLAYBOOK.md，
  赛前 5 问 + 盘中速查表（情形→策略→价格区间→仓位→保护）+ 不做清单 + D4 三件套；
  策略 HTML 导航已挂"⚡ 今日作战速查"入口，交易时可直接对照。
- 新数据入库（2026-08-08）：T1 vs HLE（G2 深反失败= B3 新样本 16.5->78.5->0.05；
  单局 vs 整局结构实证）与 EYE vs PHA（CS2 强强对话价值买入正例 PHA 13.5c）；
  形态库新增 A7 强强对话错杀反转（MD 已有，本会话补：B3 样本、HTML 同步、作战手册条目、
  分类器 A7 规则 v1.3、EDGE 补记 2 笔、Moneyline 快照截断说明）。
- 形态库巡检工具建立（2026-08-08）：tools/pattern_audit.py + runtime/run_pattern_audit.command，
  回答两个问题：① 已知形态复验计数（累计 + 较上次增量，基线 reports/pattern_audit_baseline.json）；
  ② 新形态发现（未知序列按图形聚类，>=3 个相似才登记候选）。
  首次运行：76 条序列 / 14 组快照；未知 5 条（多为数据截断/未结算异常），候选新形态 0；
  观察到 EYE/PHA Moneyline"反复翻超"（86.5->48.5->84.5->48.5）为潜在新形态，样本 1 待累计。
  建议每 2-3 天跑一次（本会话无 automation 工具，定时需在应用自动化界面挂
  `python3 tools/pattern_audit.py` 或直接运行 .command 启动器）。
- 每日形态复盘自动化（2026-08-08）：tools/daily_pattern_review.py + runtime/run_daily_review.command，
  覆盖三条需求：① 每天跑形态巡检（复验计数 + 新形态候选）；
  ② 连续无输入预警（3/5/7 天分级：判断暂时不玩/放弃/特殊情况）；
  ③ 每天扫描新内容（有新内容提示更新；连续无内容 >=3 天提醒）。
  状态文件 runtime/pattern_review_state.json；本会话无 automation 工具，
  定时任务需在应用自动化界面创建：每日执行 `python3 tools/daily_pattern_review.py`，
  并在触发后读取输出（有新内容则按流程更新形态库/策略库/HTML；出现预警则询问用户）。
- 每日形态复盘自动化已注册（2026-08-08）：应用自动化任务「每日形态复盘与策略生成」
  已写入 ~/.codex/automations/polymarket-daily-pattern-review/automation.toml（cron，每日 09:00，
  gpt-5.6-luna / medium，通知策略=仅失败时通知）；触发后自动运行 run_daily_review.command，
  读当日 pattern_audit 报告并按流程更新形态库/策略库/HTML/进度库，出现 3/5/7 天预警时询问用户。
- 今日新数据入库（2026-08-08）：NS vs DNF（G1 被翻盘 + 止损/翻转正面样本：
  NS 97.5c->0.05c 为 B1 新样本、DNF 2.5c->99.95c 为 A1 同场互证；G2 all-in 溃败反面）；
  新增 Handicap 让分盘（-1.5）脆弱性规律（市场结构规律）+ 作战手册"止损+翻转"条目。
- 08-09 巡检与 SK/NAVI 入库：SK vs NAVI（LEC，G1 NAVI 赢 / G2 SK 30.5c->99.95c 中位反转、
  NAVI 69.5c->0.05c 干净翻转）；新增 LEC 联赛信誉边界（常打满 + 明眼假赛疑似，无法从赔率证伪，
  需弹幕/主播信号交叉验证，与 LPL 同级降级）；形态气候补"反转日"规则
  （连亏 2 笔强制减半、D6 到线只看不开、90c+ 不追）；当日形态分析报告
  reports/2026-08-08_pattern_analysis.md（强反转日：A2 x4 最高频）。
  巡检最新：89 条序列 / 16 组快照，B4 38 / A2 12 / A3 12 / 未知 7（异常为主），候选新形态 0。
- 情报信号管线（另一会话 08-09 建）：tools/fetch_huya_replay.py + transcribe_audio.py +
  record_intel_signal.py + intel_stats.py + schemas/intel_signal.schema.json +
  knowledge/intel_signals.json（3 条）+ STREAMER_PROFILES.md（957 首选/解说毛毛）。
- 对战形态预判页（2026-08-09）：docs/framework/matchup_forecast.html，
  输入两队 + 赛前赔率（实力差）-> 输出预期形态清单（置信度/触发条件/验证信号/建议动作），
  规则引擎 = 队伍形态倾向频率（89 序列聚合）× 联赛信誉（LCK/CS2 可信，LPL/LEC 降级）×
  情报信号（HLE 上单核心、BLG 大优 B1 等）；定位为赛前假说，盘中用 classify_pattern 验证，
  每场后回填队伍频率使预判自学习；策略/形态 HTML 已挂"⚔️ 对战形态预判"入口。
- 08-09 新数据入库（巡检 96 序列 / 19 组快照，B4 42 / A2 14 / A3 12 / C2 10）：
  - DK vs KT 让一追二（整场 23.5c -> 98.5c、G2 37c -> 100c 双低点）-> A2/A4/A7 样本 +1，
    强队 G1 输后联赛先验入形态库（LCK 12.5% / LPL 42.9% / LEC G2 赢回 83%，锚点 ~49c）；
  - CFO vs GZ 阿卡丽单杀熟练度信号（50c 加仓 95c 止盈 +90%）-> 英雄画像 CHAMPION_PROFILES + 作战手册"信号加仓"；
  - BFX vs DRX 横扫（DRX G2/整场/让分 ×3 归零）-> B4 样本 +3 + "让分不是保险"（74.5c 按归零预算）
    + "信息自检"纪律（群聊噪音覆盖第一判断，D-CHECK）；
  - 其他会话同日产出：LEC 打满率统计（49.2%，G1/G2 相反⟺打满 65/65 验证）、path 阈值分析、
    反事实批量复盘、bar 监控回放、分类器 golden set、机会扫描 08-09。
- 每日形态复盘（2026-08-10，自动化巡检）：97 序列 / 19 组快照；本周期新增内容 3 项
  （lol-cfo-gz game2 快照 + 08-09 / 08-10 两份日复盘）；A2 中位U型反转复验计数 14 -> 15
  （新样本 CFO G2 24.5c -> 100c：72c 追高 -> 28c 深跌 -> 翻回，G3 35c -> 92.5c 阿卡丽信号止盈一并入样本行）；
  候选新形态 0（未知 7 条 = 数据截断 3 + Moneyline 边界 4，未达 3 样本门槛，仅观察）；
  无连续无输入/无内容预警（last_input=2026-08-10）。已同步 REVERSAL_PATTERN_LIBRARY.md 与
  reversal_patterns.html 的 A2 样本、频率块、未知通道；strategy_library.html 无受影响条目。
  08-09 复盘（尾盘 all-in 归零反面）与 08-10 复盘（Dota2 小仓滚仓 +300 正面）已入复盘索引与心理库。
- 赛前预期情景机制（2026-08-09，用户提出"不打无准备的交易"）：
  - 新建 docs/runbook/PREDICT_SCENARIOS.md：标准情景集 S1-S5（压制不做/回撤 45c/深蹲反转/尾盘 D2/
    开局碾压不早买）+ 填写模板 + CFO vs GZ 示例 + 复盘闭环（情景 vs 实际回填，校准权重）。
  - 新建 knowledge/LEAGUE_PROFILES.md：联赛画像（波动/打满/假赛/反转可信/仓位修正）——
    LCP 高波动观察入库（CFO vs GZ G3 50->35->92.5 大摆动、BO5 常打满）：单局快进快出、95c 止盈优先。
  - 作战手册升级为"赛前 6 问"（新增预期情景）；对战预判页加 LCP（信誉 0.6 + 波动提示）；
    TEAM_PROFILES 联赛信誉补 LCP。
- 大热门躺赢策略立项（2026-08-10，用户 LCP 两场大资金正例）：
  - "热门全程压制"语义拆分：网格视角 = 低交易价值（S2 挂单不触发）；
    赛前持有视角 = 新候选策略"大热门躺赢"（赛前 >=80c + 实力差悬殊 + 状态确认，持有到结算，
    90c+ D2 锁盈不裸奔；固定金额非全仓；LPL/LEC 假赛降级）。
  - 已入：STRATEGY_MASTER_LIST（通用策略新条目）、REVERSAL_PATTERN_LIBRARY（语义拆分）、
    TRADING_PLAYBOOK（赛前 6 问 + 盘中速查行）、matchup_forecast.html（强弱对话输出躺赢候选）、
    EDGE_LOG/edges.json（LCP 两场样本，口述待补细节）。
  - 与"三七开买7 负期望"的边界：买7 = 70% 定价 77c 无信息差（负期望）；
    躺赢 = >=80c + 画像/状态确认（真实碾压概率 > 盘口定价时才为正期望）。
- CS2 FNC vs K27 让一追二入库（2026-08-10，用户复盘会话整理）：
  - 整场 6c->100c（16 倍）/ Map2 11c->100c（9 倍）= A1 极值反转 ×2（黄金样本）；
    CS2 深反样本累计 4（Liquid 16.5c / FOKUS 9c / K27 6c+11c）。
  - 新增"深水区反转启动确认"信号（BO3 落后方 Map2 中段 <=15c（整场 <=8c），
    5-10 分钟内单局上穿 0.3/0.5 = 启动；等启动再进，不接最低点）；
    CS2 下狗让一追二 = 打满（O/U Over）。
  - 策略资金分层定稿（稳定池 vs 高赔率池）：稳定池占 70-80%（S2/S1-标准/躺赢/P5/信号加仓），
    高赔率池 10-20%（深反/彩票机器/A7/CS 深水区/事件小注），高赔率池纪律入作战手册。
- 08-11 新数据入库（巡检 136 序列 / 30 组快照，B4 49 / A2 31 / A1 14 / A4 8）：
  - DNS vs HLE（K杯）信息差：阵容公布 DNS 18.5c->66.5c 一分钟 3 倍，杯赛首发核对列为赛前固定检查项；
    大热门躺赢样本 +1（DNS 70c 三局横扫 +100）；"全仓赢不改变全仓风险"入加仓纪律。
  - Dota MOUZ vs RE 让一追二：RE 整场 17.5c 深水区低买 +70-80 正样本；让一追二样本组 +1
    （RE/PR1-MOUZ/YES-LevelUP，12-20c 买入命中率约 30% +EV，待 >=30 样本）。
  - NSEA vs DKC Over 2.5：O/U 结构位策略入列（G1 输家赢 G2 则打满，Over 28-30 深水区=结构位，
    分批止盈、锁定后不赌 G3）。
  - DRXC vs FOXY G2：高位加仓反面（70c 逐笔加到 300+ 后归零 -200~400）-> 加仓纪律强化
    （现价高于成本即停）；EXPERIENCE_INSIGHTS 已确认经验清单建立（联赛/队伍/形态/执行/情报 5 类）。
- 正/负面清单建立（2026-08-11，用户提出"明确做对做错、不断强化"）：
  - knowledge/DO_DONT_LISTS.md：正面 DO 13 项（D01 躺赢/D02 O/U 结构位/D04 彩票机器/D06 止损+翻转
    /D07 信号加仓/D09 提现/D11 休息等）+ 负面 DON'T 17 项（N01 追高/N02 高位加仓/N04 让分当保险
    /N05 全仓/N09 裸奔/N14 亏损不卖/N15 群聊噪音等），每项带关键样本与强化/拦截方式；
  - 复盘模板新增"正负面清单对照"勾选步骤（DO/DON'T 计数回填；同一 DON'T 连续 >=2 次当日降级）；
  - 与 EXPERIENCE_INSIGHTS（结论库）、PSYCHOLOGY_NOTES（原因库）、TRADING_PLAYBOOK（执行表）四表联动；
    计数脚本待复盘开始勾选后建立。
- 08-14 数据更新（巡检 167 序列，B4 57 / A2 42 / A3 16 / A1 15 / C2 15 / A4 11）：
  - 08-12/08-13 新样本入库：A2 +GEN G1 34.5->100、LGD G1 19.5->100；A1 +LGD G2 深水区翻盘；
    B4 +TT G1/G2（BLG 完全碾压）、KT G1 43.5->0；C1 +BB3 vs FaZe BO1 极端摆幅（5c->95c->回拉）；
    让一追二样本组 +JDG/DNS/NIP。
  - 新洞察：LPL 信誉降级再验证（TT 下狗反转未兑现）；信息差正例 ×3
    （LGD 辅助补强横扫、GEN 下路回暖 2:0、KT 新射手弱点）入 DO_DONT D13；
    DON'T 新增 N18 离场/不盯盘被动扛（WB/NIP 开车案例）；N01/N09/N14 补新样本。
  - 任务 7（交易者拆解 e46m3）由其他会话推进：docs/forensics/ 知识库/策略库/拆解指南/
    案例跟踪 + 原始链上数据已建。
- 08-15 数据更新（巡检 187 序列，B4 66 / A2 44 / C2 21 / A3 16 / A1 15 / A4 12）：
  - 新样本：B1 +VIT G2 94c->0.1c（LEC 假赛疑似，领先 1 万经济不打团）；B4 +MOUZ G1 37c->0.7c
    （全仓接刀反面）；让一追二 +HLE 2:1（08-15）、DK 2:1（08-14）。
  - 新洞察：定价失真买强队（LEC 强弱分明但赔率五五开，SHFT/SK 赛前 150->500+；
    NS/BRO +200）入策略库通用策略；假赛疑似案例库 knowledge/leagues/FIXED_MATCH_SUSPECT_CASES.md
    建立（VIT 高度疑似，含核查清单，只记疑似不下结论）。
  - DO/DON'T 补样本：N03 +FUT/MOUZ 接刀、N05 +350 全仓、N07 +VIT 假赛疑似（含 G3 反手过度外推全亏）、
    N09 +HLE G1 77.5c 未锁盈归零 -377。
  - 任务 7 同日推进：forensics 拆解数据（NS/BRO、SHFT/SK 逐场交易/价格/标签）+ 合约套利扫描
    （arb_cycle schema、forensics_arb_scanner、sigma_p 扫描）+ 假赛疑似案例库。
- 08-18 数据更新 + 漏抓修复：
  - 修复 pattern_audit 快照命名兼容：新增格式 slug__N__Team.jsonl（08-16/17 快照）
    之前被漏统计（187 序列），修复后 **187 -> 283 序列**（B4 113 / A2 65 / C2 36 / A3 24 / A5 19 / A1 17）。
  - 08-16/17 复盘入库：让一追二 +LGD 2:1（整场 6.5c->93.5c）、BRO 2:1；新品类 Valorant 首个案例
    （C9 vs EG2）入 LEAGUE_PROFILES（待观察，小仓起步）；定价失真买强队 +NAVI/TH 正例、
    SK/FNC 全仓反面；DO/DON'T 补 N19 恐慌卖飞（LGD 9% 卖飞）+ N02/N05/N07 新样本。
  - AGENTS.md 新增"数据同步约定"（2026-08-18）：快照命名兼容、数据到达即同步
    （巡检基线/形态库/策略库/DO-DONT/HTML/进度）、新品类登记、跨会话产出同步、
    滞后自检（快照/复盘日期晚于基线 = 告警补跑）。
- 未知优先落地为数据流水线（2026-08-08）："现象层第一/未知优先/不硬套"写入
  PHENOMENON_STRATEGY_FRAMEWORK 第 0 节第一原则；fetch_price_snapshot.py 取数后自动跑形态分类
  并输出未知清单（classification.jsonl）；全快照回填完成，未知观察池 10 个样本
  （真异常 3 + 边界漏标 7，见 REVERSAL_PATTERN_LIBRARY 三.6）。
- 反事实复盘 + 数据校验落地（2026-08-08）：tools/counterfactual_review.py（规则化执行 vs 实际，
  FOX/BRO 演示差值 106.68）；fetch_price_snapshot.py 内置完整性校验（时间戳/双方和/结算），
  回填发现时间戳重复与两处未结算异常；期望值追踪定"每 10 笔或每周刷新"规则；
  赛前预期价归属执行层 TODO；心理规则进执行器列为待办（交接文档第 9 节）。
- 主观情报库立项（2026-08-08）：主播/解说/弹幕信号 -> 结构化赛前/赛中情报；
  方案 docs/task/INTEL_SIGNAL_LIBRARY_PLAN.md；已填充 INTEL_SIGNALS（WB/LNG 中单熟练度、
  T1/HLE 上单核心+状态低迷）与 TEAM_PROFILES（HLE 行）；情报库功能点 TASK6 4.7；
  由单独会话继续开发（交接文档第 10 节）。
- T1 vs HLE（08-08）复盘完成（含 G3）：HLE 2:1 赢系列赛；
  G2 = B3 假反弹新样本（16.5c->78.5c->0.05c）+ 单局vs整局案例
  （Moneyline 72.5c->47.5c，用户买 G2 赢 50 归零共亏约 80）；
  G3 = 用户赛前买 T1 全程浮亏未卖归零（损失厌恶样本，PSYCHOLOGY_NOTES 已记）；
  快照 docs/data/snapshots/lol-t1-hle1-2026-08-08/；复盘文件已入库；
  INTEL_SIGNALS 应验终评：HLE 上单核心信号方向应验、状态低迷部分应验。
- CS2 EYE vs PHA 整局复盘（2026-08-08）：5:5 开 -> Map2 EYE 86.5c/PHA 13.5c ->
  PHA 逆转 -> 五五开回归（1:1，G3 进行中）；PHA 13.5c = 强强对话价值买入正例（CS2），
  86.5c 侧为近胜高危区；快照 docs/data/snapshots/cs2-eye-pha-2026-08-08/；G3 终局待补。
- NS vs DNF G1 复盘（2026-08-08）：DNF 赢（NS 97.5c->0.05c 约 4 分钟被翻，DNF 2.5c->99.95c）；
  用户 NS -1.5 快速止损 + 翻转 DNF 10-20c $30 翻到 100+ 美金（正面执行样本，
  与 T1 G3 死扛对照组）；快照 docs/data/snapshots/lol-ns-dnf-2026-08-08/。
- NS vs DNF G2 日终复盘（2026-08-08）：DNF 2:0 赢系列赛；
  用户 G2 all-in NS（44c）溃败归零（conviction + 无止损 + 情绪崩溃，
  与"小仓位代替止损"策略矛盾的反面样本）；今日整体亏损约 400-600；
  自动化核心目标映射完成（队伍/实力识别、当日形态、形态->预设操作、自动执行），
  下一步开发 bar 监控程序（交接文档第 7 节）；快照已补 G2/Moneyline。
- 08-08 全天日终复盘建立（knowledge/reviews/2026-08-08_day_review.md）：
  四场分笔汇总、今日形态气候（高波动混合日）、心理正反面样本、自动化目标状态。
- SK vs NAVI（LEC 08-08）复盘：G1 NAVI 完全碾压、G2 SK 翻盘
  （NAVI 69.5c->0.05c 22 分钟，翻转干净得可疑）；Moneyline 83.5c->58.5c（1:1，G3 待补）；
  LEC 弹幕情报（常打满/明眼）+ 弹幕主观情绪分析用例登记
  （INTEL_SIGNAL_LIBRARY_PLAN：假赛/剧本/状态三分类）；快照 docs/data/snapshots/lol-sk-navi-2026-08-08/。
- 08-08 崩溃日记录：三场连亏同一结构（领先被翻 -> 连续追单 -> 情绪接管），
  今日估算 -600~900（含 SK/NAVI -200~300）；已写入 PSYCHOLOGY_NOTES 与日终复盘；
  规则重申：连续 2 笔亏损强制减半、D6 熔断、all-in 强制小仓。
- 08-08 今日形态分析完成（reports/2026-08-08_pattern_analysis.md）：
  形态气候 = 强反转日（A2 中位反转 x4 最高频）；四场逐局形态标签已打；
  指导：反转日低错杀位买、高位不追、连续亏损降档。
- LEC 弹幕信号入库（2026-08-08）：打满结构 -> G1 强队赢后 G2 弱队小翻倍
  （INTEL_SIGNALS + TEAM_PROFILES）；初验 1/1（SK/NAVI；T1/HLE 为强强对话不计入）；
  待办：统计 LEC 历史 G1 强队赢 -> G2 弱队赢频率（>=20 样本定仓位倍数）。
- 深反彩票管线（环节 4）前置已满足，下一步启动反弹确认层历史回测（WE G1/G2、IG/NIP、NS vs T1）。
- 策略清单按市场层级分层（2026-08-07）：新建 docs/framework/STRATEGY_MASTER_LIST.md，
  明确小局（Game/Map Winner）与整局（Match/Series Winner·Moneyline）定义，策略分通用 / 小局专属 /
  整局专属三类，不混用；config/strategy_templates.json 增加 market_scope 字段；模板 S3 并入 S2（热门回撤接）。
- 结构化交易补充（2026-08-07）：新增 knowledge/trades/2026-08-07_trades.json（2 笔手动交易，
  WE vs TT G1、BFX vs BRO G1，金额为口述估值），知识库索引与最近复盘已同步。
- 彩票机器（环节 4）反弹确认层历史回测完成（2026-08-08）：全量 1 分钟数据（5 组 LoL 快照 +
  Dota/NS/T1 历史序列），层 1 深反彩票反转场次平均 8.3x；层 2 主触发定为"单根 +10c"，
  4 触发平均 +13.7/笔（ROI +91%）；设计文档 docs/framework/LOTTERY_MACHINE.md，
  回测报告 reports/lottery_machine_backtest_2026-08-08.md，工具 tools/lottery_machine_backtest.py；
  下一步小额实测 20-30 个触发样本。
- 策略三档颜色定位（2026-08-08）：🟢 常规做 / 🟡 谨慎做 / 🔴 不做或先验证，已标入
  docs/framework/STRATEGY_MASTER_LIST.md；反弹确认加仓经回测由红转黄。
- 反转形态库建立（2026-08-08）：docs/framework/REVERSAL_PATTERN_LIBRARY.md，
  三大类 13 种形态（反转类 A1-A6 / 崩塌类 B1-B4 / 震荡类 C1-C3），全部带正反样本与路由策略。
- 主观情报库基础设施完成（2026-08-08）：schemas/intel_signal.schema.json（信号字段契约）、
  knowledge/intel_signals.json（结构化库，迁移 4 条信号、回填 3 条）、
  knowledge/INTEL_SIGNAL_TEMPLATE.md（手动采集模板）、tools/record_intel_signal.py（录入/赛后回填）、
  tools/intel_stats.py（来源 x 标签 x 应验率统计，--json 供 TASK6 UI）；
  转录工具选型（通义听悟 + 本地 faster-whisper，关键窗口转录优先）与弹幕抓取方案
  （barrage-fly / 浏览器自动化 + 合规边界）已写入 INTEL_SIGNAL_LIBRARY_PLAN 第 10 节；
  下一步：每场赛后回填应验结果，样本累计到每组 >=15-20 条后再出统计结论。

2026-08-09：
- bar 监控程序 v1 落地（交接文档第 7 节，执行层）：tools/bar_monitor_runner.py。
  每 60 秒拉最近 15 分钟窄窗口 1 分钟 bar + /book 实时中间价，策略状态引擎
  （S1 深反 / 中位80 / S2 热门回撤）输出 resting 限价单动作队列；默认 dry-run 不下单，
  唯一下单入口仍是 grid_plan_runner；状态 runtime/bar_monitor_state/<slug>.json，
  动作 runtime/bar_monitor_actions.jsonl；离线四场景验收通过（入区挂单 / 穿档估算成交 /
  破止损切 S1 评估 / S1 多档挂单），成交档位不重复推荐。
  待办：--execute 钩子（人工确认后调 grid_plan_runner）、形态标签接入（classify_pattern）。
- 任务 2 候选动作队列落地：market_scanner 新增 --output-action-queue，
  输出 runtime/candidate_action_queue.json（只含 can_prepare_trade_plan /
  manual_review_before_plan 两类）。
- 任务 2 自动化流水线 v1：tools/task2_pipeline.py（扫描 -> 动作队列 -> bar 盯盘单轮接线，
  默认 dry-run）+ runtime/run_task2_pipeline.command + launchd plist 模板
  （runtime/launchd/com.polymarket.task2-pipeline.plist，每 15 分钟）。
  离线接线验证通过：S2 候选自动喂 bar 产生挂单动作，S3 实验策略正确跳过。
- 就绪度清单写入 TASK2_AUTOMATION_CANDIDATE_FLOW.md 第 7 节；
  剩余唯一关键关卡 = live 扫描验收（需要稳定网络环境）。
- 任务 2 live 验收跑通（2026-08-09）：正式流水线 tools/task2_pipeline.py 实测
  1600 抓取 / 771 时间窗口内 / 5 watchlist 匹配 / 4 场真实 LCK BO3 进入 watchlist
  （HLE vs KT、BNK FEARX vs DN SOOPers、T1 vs Gen.G、DRX vs BRION）；
  当前形态未触发候选（0 项，数据面正常），动作队列/报告/诊断块全部产出，全流程不下单；
  V2 关键卡点（时间窗口内赛事抓不到）已解除，待首个 live 候选触发案例后
  可由用户确认任务 2 转"已完成"。
- 空窗期行为落地（2026-08-09）：流水线自适应调度——有比赛正常 15 分钟一轮、
  临近开赛加密、窗口内无白名单比赛降为每小时保活检查；每轮输出"下一场白名单比赛"
  预告；明确"没有机会 ≠ 没有比赛"（比赛进行中但形态未触发候选属正常）。
- 发现并修复 startDate/startTime 语义 bug（2026-08-09）：Gamma 事件 startDate=挂牌时间、
  startTime=真实开赛时间；扫描器原先优先 startDate，把 08-15/16 的 4 场 LCK 预挂盘
  误判为"进行中"（量仅 $5、价格 0.5/0.5 佐证）。已改为优先 startTime/gameStartTime，
  market_scanner.py 与 event_marker.py 同步修复；修复后 watchlist 归零，与"当前无比赛"一致。
  教训：live 验证必须核对原始字段语义 + 成交量/价格佐证，不能只看 time_status。
- bar 监控 v2 完成（2026-08-09，A 组）：--execute（生成 pending trade_config + 调
  grid_plan_runner dry-run）与 --execute-live（真实挂单，需显式确认）；D3 跟踪止损状态机
  （d2_trailing_active / d3_stop_triggered / re_entry_eval）；形态标签接入
  （classify_pattern --market-type -> pattern_labels 写入动作与状态）。
  离线验证：S2 入区挂单 + dry-run 计划输出、破止损切 S1、D3 四轮状态机
  （挂单->成交->保护->触发止损）、S1 深反序列出 B4 形态标签。
- 历史回放验证完成（2026-08-09，B 组）：tools/replay_bar_monitor.py 对 47 条 1 分钟序列
  滚动窗口回放（bar 监控新增 --replay-series 模式）；已知案例全部对上——TES/WE 深反序列
  触发 single_bar_rally/rebound_confirmed，BLG/FOX 崩盘序列触发 d3_stop/stop_new_entry；
  报告 reports/bar_monitor_replay_2026-08-09.md。
- 反事实复盘批量完成（B 组）：tools/batch_counterfactual.py 全量 47 序列两套参数；
  S2（entry 45c/TP 62c/止损 35c）36 止损 8 止盈，平均 -12.6（印证方向过滤必要性）；
  S1 深反（entry 8c/TP 50c/彩票止损）20 止损 5 止盈，平均 +51.9（彩票型正期望）；
  报告 reports/counterfactual_batch_2026-08-09.md。
- 彩票机器触发样本盘点（B 组）：当前 single_15=5、single_10=7、cum_15=12 个触发；
  距小额实测目标 20-30 样本还差，优先用 cum_15 模式（12 个）或继续积累快照。
- 分类器 golden set 建立（C 组）：tools/export_golden_set.py 汇总 64 条已分类序列
  （reports/classifier_golden_set_2026-08-09.md + docs/data/classifier_golden_set.json，
  全部标"待复核"）；pattern_audit 巡检 89 条序列（B4 38 最高，未知 7，候选新形态 0）。
- 策略命名与框架收尾（D 组）："策略 C 极端低价彩票"归并为 S1-深反极值子类（旧报告已标注），
  S3 保留"已并入 S2"标注；S2 方向过滤形式化为强制入场条件
  （config/strategy_templates.json B_FAVORITE_DIP 新增 entry_requires_direction_evidence）；
  LEC G1 强队赢->G2 弱队赢统计登记（knowledge/leagues/lec_g1_g2_stats.json，1/20 样本）。
- V2 一分钟信号驱动捕捉闭环 v1 落地（2026-08-09，用户确认行为契约后实施）：
  定义与验收协议 docs/task/V2_EXECUTION_LOOP.md。
  - --autopilot：信号 -> 计划 -> grid_plan_runner dry-run -> 待确认（pending_plan），不自动下单；
  - --execute-live：仅待确认计划 + autopilot 开启时执行，执行后自动拉起 monitor
    （成交 -> 自动配止盈 + 交易所级止损卖单，trade_config.stop_loss，D3 落地）；
  - 风控闸前置：autopilot 开关 / 策略白名单 / 预算 / 并发上限 / 计划去重；
  - 离线验证：门禁、计划含止损单（SELL 50.0 @ 0.35 (stop)）、去重、无待确认拒绝执行；
  - live 冒烟（预挂盘 T1 vs Gen.G）：6 个目标全部因 spread 80c+ 超限被流动性闸拦截，
    无任何下单，形态标签正常（C1 中位震荡 / 未知）——盘口不合格自动跳过。
  - 真实资金路径明确：--execute-live 为唯一真实下单入口（走 grid_plan_runner），
    新增交互确认（输入 yes 才下单，非交互环境须 --yes）；实盘流程手册
    docs/runbook/V2_LIVE_RUNBOOK.md + 启动器 runtime/run_v2_live.command。
  - V2 升级为多策略框架（V2-S1 盘中信号 / V2-S2 赛前预测挂单）。
    V2-S2 v1：tools/prematch_predictor.py——赛前赔率 + 形态气候（golden set A34/B32）
    + 队伍画像 + 情报 + 联赛信誉（LPL/LEC 降档 0.5）-> 预测形态 + 置信度 + 依据
    -> 策略模板预挂单计划（含止损单）；离线验证：T1 72% 热门 -> S2 推荐、
    计划 0.48/0.45/0.42 + 0.35 止损，LCK 系数 1.0。
  - 比赛管理目录（2026-08-09 晚）：runtime/match_management/ 每场一张状态卡
    （系列赛进度 + 挂单状态标识：没给机会/计划取消/已挂单/已成交等）+ 工具
    tools/match_manager.py（init/record/series/show/list）；V2 盯盘会话结束即回填，
    已记录 08-09 三场（IG 2-0 LNG 已结束 / DK-KT G3 待确认 / CS2 Sinners-EYEBALLERS
    未开赛，流动性不足未交易）。
  - 08-09 晚间 live 演练收获：真实比赛 dry-run 全链路多次跑通（IG G1/G2、DK G1/G2）；
    CS2 为预挂盘（未开赛），G1 spread 27c 被流动性闸拦截，未交易；首次触达真实挂单路径
    发现并修复 grid_plan_runner 余额预检字段 bug
    （layer.amount_usd -> layer["usdc"]）；钱包实际可用现金约 0.37 USDC（资金大多在
    持仓中），余额预检正确拦截；KT 整场仓位按用户指示平仓 @0.59。
  待真实比赛 live 验收：08-13/14 LCK 进窗口或指定真实比赛，dry-run 全链路后小额实盘。
```

## 10. 开发接力清单（案例入库 -> 扫描器验收 -> 一分钟流小额测试）

来源：2026-08-06 会话。三环节顺序推进，每环节有明确验收标准，全部通过前不进入下一环节；由用户在另一会话继续开发。

### 环节 1：案例入库（主体已完成）

目标：

```text
把 IG vs NIP（2026-08-06）这类 P5+P1 深反案例沉淀进策略库与复盘库。
```

现状：

```text
- 已入库：docs/framework/STRATEGY_PATTERN_LIBRARY.md P5 已沉淀样本（NIP <5c -> Moneyline 34.5c / G2 Winner 79.5c）。
- 工具升级项已登记：1 分钟级价格流 + 反弹检测（<10c 单根拉升 >15c）。
- 行情数据：Polymarket CLOB 10 分钟采样。
- WE vs AL（08-06 晚间）点位已精准化：CLOB 1 分钟粒度核验，G1 低点 6.5c@13:58、G2 低点 0.65c@15:16；
  快照落盘 docs/data/snapshots/2026-08-06_lol-we-al/（game1/game2/moneyline 三个市场）。
```

待办（承接会话）：

```text
- 补充实际成交/订单明细（如有）。
- 持续把新案例追加到 P5 样本表，目标 5-10 个。
```

验收标准：

```text
- P5+P1 案例 ≥5 个，每个含：赛前价格、极低点、反弹后价格、时间跨度、结果。
```

### 环节 2：扫描器验收（任务 2）

目标：

```text
自动扫描能稳定发现 IG vs NIP 这类候选，输出机会分与路由建议。
```

现状：

```text
- 任务 2 代码与离线验证完成，状态"待验收"。
- docs/task/V2_VALIDATION_HANDOFF.md 已准备，等待稳定网络环境 live watchlist 验证。
- 已知待验证点：within_time_window / watchlist_matches 诊断块是否恢复。
```

验收标准（引用任务 2，另加一条）：

```text
1. 能自动输出候选市场列表。
2. 每个候选市场有机会分、流动性分、风险提示。
3. 至少能从候选列表中筛出 3-5 个值得人工查看的市场。
4. 不触发实盘下单。
5. 能发现"极低价深反 + 局内翻盘"类候选（P5+P1 标签正确叠加）。
```

### 环节 3：一分钟流小额测试（新能力）

目标：

```text
1 分钟级价格流捕获极值（<5c）与反弹瞬间，配合彩票仓 + D3 保护做小额实测。
```

前置条件：

```text
- 环节 1 案例 ≥5 个、环节 2 扫描器验收通过。
- D3（止损状态机）/ D4（进场三件套）与交易所级止盈止损挂单已落地（BRO 脚本崩溃教训）。
```

开发项：

```text
- 1 分钟级价格流采集（CLOB prices-history fidelity=1 或事件驱动轮询）。
- 反弹检测：<10c 区间单根拉升 >15c 触发 P5+P1 候选。
- 极低价候选强制彩票仓（单档 ≤10-20 USDC）与 D3 保护。
- 模拟先行，再小额实盘（S1 已 L3 小额实盘）。
```

验收标准：

```text
- 能稳定捕获极值低点与反弹时间点（误差 ≤2 分钟）。
- 小额实测 5-10 笔，P5+P1 样本胜率与盈亏比达到策略库 L3 门槛，再评估放开额度。
```

### 环节 4：深反彩票管线（彩票机器）— 待办，排在策略 A/B 定稿之后

来源：2026-08-07 会话（用户确认"先理清策略 A/B，再做这一个"）。

定位：

```text
不是预测哪场会发生奇迹，而是"全程覆盖 + 价格触发 + 自动执行"；
识别 = 奇迹正在发生的几分钟内刚好在场、单子已挂好。
本质是一台彩票机器：多触发、小仓位、高赔率、统计期望，不追求每把都赢。
```

数据现实（为什么是小仓位）：

```text
深跌里大部分是死的（08-05 九连负），<10c 深跌的反弹概率约 10-20%；
只有靠"反弹确认"提高命中率 + 低档位倍数，才有正期望。
```

两层触发：

```text
第一层 极低价彩票挂单：
  BO3 Game/Moneyline 市场，价格曾 >=25c、现跌入 <10c 且非终局
  -> 预挂 8/6/4/2c 极小单（每档 $5-10），只有真跌到才成交，归零预算内可接受
  -> 解决 0.5-1c 级深跌（WE G2：0.65c -> 100c）

第二层 反弹确认加仓：
  从 <10c 低点单根拉升 >=10-15c（如 1 分钟内 5c -> 20c），且盘口仍有流动性
  -> 追加 $10-20 确认仓，立即挂止盈（50/70/85 + 彩票）与止损
  -> 不接刀，等第一下反弹确认才上车；解决"接刀 vs 深反"（NS/T1、08-05 教训）
  -> 代价：买不到最低点；收益：躲过大部分归零（WE G2 在 13c 上车仍约 7 倍）
```

过滤条件：

```text
1. 流动性：盘口深度足够，防 1c/99c 假数据。
2. 时间剩余：接近终局不触发。
3. P5 上下文：BO3 落后方、系列赛仍有翻盘时间。
```

执行保护：

```text
- 所有成交单立即挂交易所级止盈/止损（BRO 脚本崩溃教训：脚本会崩，挂单不会）。
- 状态文件记录 + 赛后自动复盘入库。
```

仓位原则（份额经济学）：

```text
- 归零是预算内可接受的；买入阶梯金额随价格下降递增（15c:$5 -> 10c:$8 -> 6c:$12 -> 4c:$18 -> 2c:$30）。
- 同样 10 美金：15c 买 66 股（到 100c = 6.7 倍），2c 买 500 股（到 100c = 50 倍）；
  低档位金额占比越高，整个彩票仓的期望倍数越高。
- 彩票仓"允许归零"不等于"裸奔"：成交即挂止盈，奇迹发生时有人替系统兑现。
```

人机分工：

```text
- 系统：发现 + 机械执行 + 统计。
- 用户：比赛阅读（假赛感/阵容/节奏）作为可选人工信号叠加。
- 先半自动（系统推荐候选 + 用户一键确认 + 系统执行），
  验证后由用户显式开启 autopilot，仅小金额（S1-深反彩票类）。
```

前置条件与验收：

```text
前置：策略 A/B 模板定稿（2026-08-07 完成：S1-深反 / S1-标准 / S2 修正，
  见 docs/framework/STRATEGY_PATTERN_LIBRARY.md 与 config/strategy_templates.json）。
第一步回测：用 WE G1/G2、IG/NIP、NS vs T1 的 1 分钟历史数据回测"反弹确认层"，
  统计触发次数、平均成本、命中率。
后续：小额实测 20-30 个触发样本，期望为正后再评估放开额度。
```

状态：暂缓（2026-08-07 用户决定先做中位入场，彩票机器延后；前置仍满足，随时可启）。

### 环节 5：执行层自动化可行性评估（待办，2026-08-07 记录）

背景：用户要求整体评估"策略怎么执行"，并把自动化方案的可行性评估记为待办。
当前主攻中位（S1-标准 / S2 / P-早建仓），S1-深反与环节 4 暂缓。

执行管线（定稿版）：

```text
发现（任务 2 扫描器，待验收）-> 路由（方向 + 价格区间 -> 模板）-> 计划生成（半自动，用户确认）
-> 执行（D4 进场三件套：先挂止盈/止损/彩票上限，再买入）
-> 监控（D3 状态机，10-30s 轮询 + CLOB 最新成交价）
-> 退出（交易所休息挂单为主 + D2 锁盈 + 回撤保护；主动平仓需用户明确，计划内自动止盈除外）
-> 复盘闭环（knowledge/reviews + trades JSON 结构化落库）。
```

架构原则：

```text
1. 监控管状态、挂单管退出：脚本会崩，挂单不会（BRO 教训）。
2. 数据用 CLOB 最新价/盘口（10-30s），不用 gamma 滞后价，不用 1-2 分钟轮询做退出。
3. 半自动优先：系统发现 + 生成计划 + 执行挂单，关键动作用户一键确认；
   autopilot 全自动需用户显式开启，且仅限 S1-标准/S2（深反暂缓期间不参与）。
```

可行性评估待办（要做的事情）：

```text
1. 状态切换状态机验证：
   - 35c 停 S2 加仓 / 18c 止损评估 / D3 止损线（跌破成本一半或末段未反弹 -> 主动离场）。
   - 验证监控循环 10-30s 轮询 + 最新成交价在快速行情下能否正确切换状态。
   - 回放样本：WE G2（0.65c -> 100c 约 6 分钟）、NS vs T1（79.5c -> 0.5c 约 6 分钟）。
2. 退出执行评估：
   - 休息限价单在快速下跌/跳空下的成交率；止损触发后补市价单的滑点预算。
   - 产出：止盈 60/75/80 与止损线在回放中的实际成交价 vs 期望价差值。
3. 数据粒度评估：1 分钟价格流 vs 10-30s 盘口/最新价对触发时间的影响（误差预算 <=2 分钟）。
4. 切换语义确认：停加仓 != 平仓（红线）；"切 S1" = 新仓 + 新预算（D3 C->重评估）；
   深反暂缓期间不自动切彩票，转止损评估。
5. 定性信号边界：假赛感/比赛阅读不可自动化，只作为人工叠加信号；
   自动化只做价格 / 流动性 / 时间规则。
6. 中位模板历史回测：用 08-05 亏损单 + 08-06 盈利单的 1 分钟数据回测
   "买80回收 + D3 止损"，统计保底收益率、止损触发次数、净期望。
```

验收：

```text
产出可行性评估报告（含回放成交率、滑点、状态切换正确性、中位模板回测结果），
通过后进入执行器开发（S1-标准 key 接入、P-早建仓接入、按档位卖 lot-based selling、D3 状态机落地）。
```

状态：待办。

### 环节 6：典型案例教科书级入库 + 结算跟进（2026-08-07 记录）

待办 1：HLE vs DRX Challengers 结算跟进

```text
- 状态：待办（等 G3 结算，不用现在拉）。
- 触发：比赛结算后（Moneyline 封顶或归零）。
- 动作：拉最新数据，确认 36.5c 之后的路径与最终结果（继续崩 or 回升）。
- 更新：docs/data/snapshots/2026-08-07_lol-hle-drxc/README.md、
  STRATEGY_PATTERN_LIBRARY.md P5 样本结局、复盘结论。
```

待办 2：典型案例入库标准（教科书级别）

```text
- 要求：每个入库案例必须包含——赛前价格、关键转折点（时间+价格）、低点/高点、
  反弹或崩塌路径、流动性情况、最终结果、归因、教训。
- 附 1 分钟快照 + 时间线表（可复现数据）。
- 存量案例按标准补全：WE vs AL（已达标）、IG vs NIP（补结局/快照）、
  HLE Challengers（待结算）、BRO vs DRX、NS vs T1、BRION G1（补 1 分钟数据）。
```

待办 3：策略库样本化（用于构建策略）

```text
- 目标：典型案例 -> STRATEGY_PATTERN_LIBRARY.md 样本（P5+P1 深反、P5+P2 热门回撤、
  尾盘崩塌等标签），用于构建与验证策略（买80回收、反弹确认层、D2 锁盈）。
- 当前 P5+P1 样本：WE G1/G2、IG/NIP、HLE Challengers + 历史 HLE 12c、BRION G1、NS vs T1 复盘。
- 推进：每个样本补齐教科书级字段；累计到 5-10 个即达环节 1 验收标准。
```

状态：待办（待办 1 等结算触发；待办 2/3 与环节 1 案例入库并行推进）。

## 11. 任务 6：电竞交易情报平台（订阅制 · 高优先级）

状态：进行中（2026-08-07 立项，框架已简化定稿：面向对外、只做 Polymarket；高保真原型待框架确认后按 6 页制作）。

目标：

```text
面向外部的订阅制情报网站，只做 Polymarket 电竞市场。
用户打开页面就知道：今天该看哪场、这场能不能做、这两队可不可信、历史上有没有同样剧本。
网站不下单、不持有私钥。
```

核心情报（每场比赛一张情报卡）：

```text
盘口：现价、走势、深度 / spread、机会分。
现象：P1-P6 标签 + 同形态历史统计（出现次数、反转成功率）。
翻盘画像：被翻盘率、翻盘率、领先稳定性、落后反弹力。
近期状态：连胜 / 连败趋势；连续低迷的队伍暂时领先时，标记"被反弹风险"。
事件情报：内讧、人员更换、教练 / 赛程变动；人工 + 半自动录入（可从朋友聊天记录沉淀），标注来源与时效。
风险提示：假赛风险观察（LPL 高发，只给信号 + 依据，不给结论）、终局风险、流动性不足。
平台只给情报与统计，不给交易建议；策略路由只存在于内部交易系统，不对外展示。
机会卡片规则（"今天有什么机会"）：值得看 = 形态/现象信号 或 画像/事件信号 + 可成交性达标；
  卡片 5 块（对阵时间 / 信号 + 同形态统计 / 关键情报一句 / 风险提示一个 / 详情入口）；
  进行中优先、双信号优先，每天最多 8 张；不含交易建议。
```

历史档案库（板块二）：

```text
队伍战绩：赢了多少场、输了多少场（按联赛 / 赛季 / 对手强度分层）。
翻盘画像：翻盘率、被翻盘率、领先稳定性、落后反弹力。
历史对局：价格走势、现象标签、策略路由、结算结果。
复盘案例：回测与真实交易的结论与教训。
翻盘案例（功能补充）：统一三阶段数据模式——翻盘前（市场怎么看死它）/ 翻盘中（反转怎么发生）/ 翻盘后（怎么收场）；
  客观盘口与主观参考（虎牙解说信号、聊天记录、用户观察）分层存储，每字段带来源与可信度。
档案库查询（数据库）：按比赛 / 联赛 / 战队 / 现象 / 画像区间 / 事件与风险组合查询，
  结果进比赛档案或比赛情况页；（可选）支持按解说主观信号筛选。
情报库功能点（形态 / 策略成果六点，2026-08-08 全部落地）：
  形态气候（今日反转/崩塌占比预警，重点）、双边形态刻画、赛前情报层（预期情形=假说层，重点）、
  可成交性评分、未知形态通道（观察池）、D3 重新进场（内部机制，对外只展示形态标签）；
  术语统一：下狗=赛前低赔率方，落后侧/下盘=盘中暂时落后方。
情报维度补充（七项全部采纳，2026-08-08）：同场多市场联动 / 背离、终局时间衰减曲线、
  对手强度加权画像 + 交锋记录、大单与主动成交方向、陷阱 / 反面样本检索、数据可信度层、触发式预警。
数据分级：本地约 15+ 场 LoL 样本先验证口径；
朋友历史数据集（抓取中）接入后回填战绩与翻盘画像；
盘中 1 分钟流持续积累翻盘率样本。
```

页面（6 页，一页一职责）：

```text
1. 为什么订阅（情报演示 + 价值 + 订阅入口）
2. 今天有什么机会（赛事时间线 + 机会卡片）
3. 比赛情况（盘口走势 + 策略建议 + 双方情报对比）
4. 比赛档案（队伍翻盘画像 + 近期状态 + 事件记录 + 历史对局）
5. 情报库（历史案例检索：现象 / 策略 / 队伍）
6. 策略实验室（同形态回测）
版本分层（V1 瘦身，2026-08-08）：V1 只做 3 个核心页（今天有什么机会 / 比赛情况 / 比赛档案 + 情报库查询）
  + 简单落地页；策略实验室、导出 / API 后置（待定），触发式预警已确认做、第二期；补充维度全部作为页面区块。
比赛档案 / 情报库（V1 四维查询）：联赛位 / 比赛队伍位 / 形态位 / 策略位，一个库两种视角
  （队伍视图 / 案例视图），交叉统计为核心价值；联赛级统计先上，队伍级画像样本 >=10 才出。
```

交付物：

```text
docs/task/TASK6_INTELLIGENCE_LIBRARY_PRODUCT.md（平台框架：情报卡 + 6 页 + 数据来源 + 订阅简表 + 红线）
高保真原型：延后（框架确认后按 6 页制作）
```

演进（简）：

```text
第一步：历史档案库 v0——现有 15+ 场样本验证战绩与翻盘画像口径，等朋友历史数据接入后回填。
第二步：实时情报卡跑通（盘口 + 画像 + 近期状态 / 事件记录）。
第三步：6 页只读上线。
第四步：订阅（试用 1-2 天 -> 付费）+ 通知；档案库随时间变厚。
```

验收标准：

```text
1. 一场比赛能在"比赛情况"页看到完整情报卡（五类情报 + 风险提示）。
2. 翻盘画像对已有 8+ 回测 / 复盘案例输出可解释结果。
3. 事件 / 近期状态情报标注来源与更新时间。
4. 网站不下单、不碰私钥；假赛 / 事件只给信号 + 依据 + 来源。
```

下一步：

```text
1. 历史档案库 v0：用现有 15+ 场 LoL 样本算第一批队伍战绩与翻盘画像。
2. 情报卡字段定稿（schemas/）：只展示情报与统计，不含交易建议。
3. ✅ 情报信号采集模板与结构化库已建（knowledge/INTEL_SIGNAL_TEMPLATE.md + intel_signals.json +
   tools/record_intel_signal.py）；近期状态/事件情报沿用同一字段结构，每场赛后回填应验。
4. 翻盘案例三阶段模板定稿（字段定稿）。
5. 对接朋友历史数据集（批量回填战绩与翻盘画像）；虎牙解说信号功能接入（957 / 毛毛 / 记得 / 米勒）；外部电竞比赛数据源登记。
```

## 12. 任务 7：交易者拆解与可复制策略沉淀（e46m3）

状态：进行中（2026-08-12 立项）。目标：一场一场拆解外部交易者 e46m3 的公开交易，
还原"他具体怎么做的"，沉淀为本项目可复制的策略与规则。

已完成：

```text
1. 账号档案建立：e46m3（0x4f1d5ae26fc31472966e951af3183308736d8de2），
   交易过 29,174 个市场；关联地址与关键合约地址已登记（docs/forensics/KNOWLEDGE_BASE.md）。
2. 机制确认（链上解码实证）：负风险组完整集定价 Σp 长期 > $1，
   他的闭环 = 买 NO 组合 -> Convert（现金+补集 YES）-> Merge 配对 -> 循环，叠加返佣。
3. 首份 HTML 报告：reports/trader_analysis_2026-08-12_e46m3_convert.html。
4. 知识库体系建成：基础知识库 + 策略库 + 逐场拆解流程 + 反馈提升机制 + 案例跟踪表。
5. 原始数据落盘：docs/forensics/data/e46m3/（转换/合并/持仓/价格/链上解码）。
6. 首场示范案例：吉达 8/12 温度组（cases/2026-08-12_jeddah_temperature/README.md）。
7. 策略库登记：S-F1 完整集定价套利（L1 建议）、S-F2 返佣叠加（L0）、
   S-F3 尘埃清理（L0）、S-F4 足球比分盘逐场套利（L1，待验证）。
8. 机制原理闭环（2026-08-14 用户确认理解）：必拿 $9 的算术、只花 $8.95 的市场错价、
   标记价 vs 订单簿 ask 的决策口径，均已在图解 HTML 与知识库中定型。
9. 假赛嫌疑场地址分析（2026-08-15，GX vs VIT G2）：赢家侧 425 买家全量画像，
   识别系统性深水抄底机器簇/全剧本型/尘埃簇/盘后 0.999 流四类；未发现一次性组织者账户；
   报告 reports/g2_winner_address_analysis_2026-08-15.html，
   案例卡 docs/forensics/cases/2026-08-15_lol-gx-vit-game2-address/README.md。
10. 电竞用户行为标签库试点启动（2026-08-15）：工具 tools/label_esports_users.py，
    常驻标签库 docs/forensics/data/accounts/esports_user_labels.db，
    规范 docs/forensics/USER_LABELING.md；试点首日已回填 5 场（含对照组），
    计划跑满一周后评估标签稳定性。
11. 视频制作标准 + 假赛视频讲解页（2026-08-15）：最高准则文档
    docs/VIDEO_PRODUCTION_STANDARDS.md（图文并茂/LoL 元素/占比与对比分析/减文字），
    首个模板页 reports/video_gx_vit_fake_match_2026-08-15.html
    （第一视角 -> 假赛信号 -> 时间线 -> 三波占比 -> 对手方对比 -> 对照组 -> 结论 + 旁白脚本）。
12. 账户级崩盘案例（2026-08-20，djdjdjekekek）：从 +$2.37M 峰值到 -$0.72M 的
    完整生命周期拆解（23,118 笔成交/294 事件全量）；结论"edge 真实、风控缺失、
    赛项漂移 + 追损"；深拆结论：盈利引擎 = 0.2-0.4 强队价值买入（ROI +12.9%），
    崩盘 = 同策略跨赛项复制失败 + 仓位失控 + 追损；配套沉淀
    账户级复盘方法论 docs/forensics/ACCOUNT_REVIEW_METHODOLOGY.md（必答三问）；
    报告 reports/trader_analysis_2026-08-20_djdjdjekekek.html，
    案例卡 docs/forensics/cases/2026-08-20_djdjdjekekek/README.md，
    原始数据 docs/forensics/data/djdjdjekekek/。
12. BTC 5 分钟盘深水反转保守复测（2026-08-19）：数据更新至 2,383 窗口、
    3,801,280 笔成交；修正旧路径脚本的时序前视，并以完整限价替代不可保证的
    首笔成交价。20c 首触 + 240 秒内恢复 35c 的候选全样本 EV -0.50c/笔、
    新增样本 -0.51c/笔，24 个参数组合无一通过计 1c 成本后的双样本门槛；
    维持 L2 纸面验证，不实盘。报告 reports/btc5m_deepwater_reversal_backtest_2026-08-19.html。
13. BTC 5 分钟盘深水反转复测追加样本（2026-08-20）：成交明细扩展至
    08-20 06:00 UTC（2,748 窗口 / 2,740 可用，新增样本外 365 窗口）。
    20c 首触 + 240 秒内恢复 35c 候选全样本 EV -0.68c、新增样本 -1.94c，
    观察上界在新增样本仅 +0.00c；32 个组合仍无一通过计 1c 成本门槛，
    维持 L2 纸面验证。报告 reports/btc5m_deepwater_reversal_backtest_2026-08-20.html。
14. 价格路径拆解手册（2026-08-21）：把 S-F5（0.2-0.4 强队价值买入）补成完整闭环——
    7 条价格路径（直通/回踩上行/深V/冲高回落/阴跌/快崩/横盘）× 5 种交易模式
    （持有/回踩管理/冲高锁盈/止损退出/横盘等待），全部挂真实案例与分区参数；
    数据证据 = 77 场已归档比赛 / 664 条可用价格序列（LoL 486 / CS2 146 / Dota2 24 /
    Valorant 8，含 78 个单侧市场互补补全）；0.55-0.65 入场 60.7% 最终上行且 79%
    摸到过 0.75+ 锁盈机会，0.2-0.4 入场 40.4%（CS2 仅 20.6%，印证 S-F5"同模式
    跨赛项结果相反"）；
    配套登记 S-F6（L1 建议）与只读复算工具 tools/forensics_price_path_analysis.py；
    手册 docs/forensics/PRICE_PATH_PLAYBOOK.md。
15. mapread 工具接入 + PEYZ 账户级追踪拆解（2026-08-26）：mapread 公开 JSON 接口
    （market-flow / wallet-activity / wallet-profiles）验证可调，底层为 Polymarket
    Goldsky 链上成交，接口已登记知识库；我方名单 ∩ mapread LoL 池 = 3 账户
    （PEYZ-BIGGEST-FAN / zb8 / MissingJoy）；深潜 PEYZ × KT vs BRO G4：
    52 笔 $17,120 下跌途中摊成本、G4 估算 +$12,692、全系列打平，
    实证"深水低吸靠分散、单场不可复制"（S-F6 外部活案例）；
    配套深潜 HTML + 推文配图方案页 + 原始数据落盘；
    案例卡 docs/forensics/cases/2026-08-26_mapread-peyz-g4/README.md。
15b. mapread 集成工具落地（2026-08-27）：tools/mapread_wallet_tracker.py 封装
     三个公开接口（board / market / watch），内置我方 forensics 名单盯梢，
     原始 JSON 只增不改落盘 docs/forensics/data/mapread/，三命令联网实测通过；
     后续可接入情报页"盘口资金佐证"与定时盯名单监控。
```

进行中 / 下一步：

```text
1. 逐场拆解：P0 = CF Villarreal C vs Levante UD（比分盘 12 次 Convert）；
   P1 = SD Raiders vs Macarthur / Palermo vs Juventus / AZ vs ADO（均比分盘）。
2. S-F1 升 L2 前置：Σp 历史回测（阈值、触发次数、毛利分布），需 >= 3 场同模式案例。
3. 每 5 场生成 cases/SUMMARY.md 提升复盘。
4. 结算场次回填实际盈亏，对照理论毛利。
5. 立即下一步：只读 Σp 扫描器 v0（标记价粗筛 + 订单簿 ask 精筛），
   跑 1-2 周统计错价频率/持续时间/可成交成本，再做模拟回测定净期望；
   通过后才进入执行层（polydata 支持 Convert/Merge）与小额试点。
6. 路径手册分域细化：样本已扩到 77 场/664 序列，下一步按联赛（LCK/LPL/LEC/EWC/TI…）
   与开赛前后细分（tools/forensics_price_path_analysis.py 已支持），校准
   docs/forensics/PRICE_PATH_PLAYBOOK.md 第 3 节分区参数；每笔复盘打路径标签。
```

验收标准：

```text
1. 完成 >= 5 场拆解卡，每场含：动作时间线、Σp 证据、链上账目、盈亏拆解、可复制点。
2. S-F1 完成 Σp 回测并给出阈值与毛利分布（L2）。
3. 每场结论回流策略库与知识库，进度表持续更新。
4. 全程只读公开数据，不触碰私钥、不下单；任何实盘复制前走成熟度与风控。
```

## 2026-08-18 弹幕×复盘联动（任务 6）

```text
Gen.GA vs BRO1（LCK CL）：G1/G2 复盘 + 两路弹幕（虎牙 + SOOP）假赛印证。
核心：G2 BRO1 91c -> 0.5c 三分钟崩盘，弹幕峰值（虎牙 81 条/分、
  SOOP 82 条/分）与崩盘窗口精确重叠，两路共识直指 BRO1 中单瑞兹故意送。
记录：knowledge/reviews/2026-08-18_lol-genga-bro1-2026-08-18_genga.md；
  案例 4（高度疑似）；DANMU_INTEL.md；match_library 待终局回填（1:1，G3 未打）。
方法论确认："弹幕密度峰值 = 价格异动窗口"的事件检测能力再次应验，
  可用于弹幕实时监控的异常事件告警。
```

## 2026-08-19/20 六场复盘批次（任务 6 + 复盘闭环）

```text
LCK 2 场 + LPL 3 场 + EWC CS2 1 场，全部自主抓数据完成复盘：
  LPL：WE vs EDG（EDG 2:0，用户 G2 基于弹幕"WE 假赛"情报买入 EDG 赢，
    灰信号 816 条 severity 高）；AL vs TES（TES 2:1）；LNG vs WBG（WBG 2:1）
  LCK：GEN vs KT（GEN 2:1）；BRO vs DNS（BRO 2:0，DNS K杯夺冠归来被横扫，
    原 dns_bro 待确认条目已自主校验闭环）
  CS2：FUT vs magic（FUT 2:1，用户 G3 赛前基于弹幕"图3 FUT强图"买 FUT 63c
    -> 90/96 兑现；原误判 Magic 胜已修正回退）
规律观察："领先方让一局"当日跨 LPL/LCK 多场出现（样本 +3），与 LCK CL
  "给一盘"规律跨联赛呼应，待累计统计验证。
复盘文件：knowledge/reviews/2026-08-19_*.md（6 份）；同步 match_library、
  reviews/index、docs/data/intel/（matches 12 场、gray_signals 9 条、teams 21 队）。
```

## 2026-08-20 DK vs HLE 复盘（自动流水线）

```text
HLE 2:0 DK；用户 G1 买 DK 100U @~63c 浮盈 55% 未止盈归零全亏（高位未止盈反样本）；
弹幕 11294 条无灰信号；复盘+情报 HTML+结构化库已同步。
```

## 待办：RMD vs PNGA 复盘（lol-rmd-pnga-2026-08-25，BO5）

```text
用户要求复盘第一/第二/第三/第四局 + 整局赔率（circuito-desafiante 联赛，
Bo5 典型赔率趋势样本）。
状态：2026-08-26 拉取受阻——Polymarket gamma/data-api/clob 三 API 连接超时
  （DNS 正常、其他外网可达，判定为 Polymarket 侧/网络路径问题），本地无该场快照。
完成条件：API 恢复后自动执行：
  1. gamma events?slug=lol-rmd-pnga-2026-08-25 -> 结果/市场结构
  2. fetch_price_snapshot（G1-G4 + 整场）-> 逐局赔率表
  3. 队伍命名登记（RMD/PNGA -> docs/data/intel/team_names.json）
  4. 复盘文件 + match_library/reviews/index/matches.json 同步
红线：不编造赔率数据；网络恢复前不产出"复盘"结论。
```

## 待办：2026-08-29/30 LCK + LEC 比赛复盘

```text
逐场结束自动复盘（挂 observe 监控 / 结束后拉快照）：
  - lol-vit-fnc-2026-08-28（LEC，08-29 00:45 开，正在打）——已挂监控
  - lol-t1-fox1-2026-08-29（LCK Playoffs BO5，08-29 16:00）
  - lol-kc-sk-2026-08-29（LEC，08-29 23:00）
  - lol-navi-gx-2026-08-29（LEC，08-30 01:15）
  - lol-dk-kt-2026-08-30（LCK Playoffs BO5，08-30 16:00）
完成动作：fetch_price_snapshot -> 逐局+整场赔率表 -> 复盘文件 ->
  match_library/reviews/index/matches.json 同步。
```

## 待办：情报库优化（2026-08-27 用户提出，比赛结束后统一修改）

```text
优化点 1：局中情报输出不够及时，各节点情报输出也不够及时。
  现状：Codex 全量生成每节点约 5-10 分钟（读 skill/模板 + 生成完整 12 段）。
  思考方向（待统一决策）：
  a. 分层输出：先出规则层"速览摘要版"（秒级、整洁模板），后台 Codex 再补全 12 段
     （分钟级）——吸取快节点教训：摘要版必须结构清晰、非"混乱快照"；
  b. 预计算：BP 节点在开赛前预切片/预统计，BP 一结束立即生成；
  c. 并行强化：同局 BP/局中/局末并行（已有），进一步压 Codex 单节点耗时
     （精简 prompt/限制篇幅）；
  d. 增量更新：局中节点基于上一节点统计增量，避免全量重算。

优化点 2：对阵容选择的判断不够准确——会把 BP 阶段弹幕讨论当实际选人结果。
  现状：BP 窗口弹幕（"选狐狸/ban X/狗头选就输"）可能被当作实际阵容认定。
  实发教训（2026-08-27 NS-BFX G2）：把弹幕"提及/讨论"硬做成选手×英雄配对
  （Scout=狐狸、泰永=EZ、大光=兰博等），用户否决；已撤错版并标注修正记录，
  登记 LESSONS_LOG D8；生成时无确认信号一律"待官方"。
  思考方向（待统一决策）：
  a. 严格区分"弹幕 BP 讨论（预测/热议）"与"实际阵容（确认）"，
     讨论一律标"BP 讨论·非确认"，不得写成结果；
  b. 结果认定需强确认信号（官方 BP/游戏内选人/主播报选+弹幕"锁了"共振），
     否则只输出讨论方向；
  c. BP 段输出拆两栏：弹幕讨论方向 / 实际确认阵容（待官方），缺确认写"待确认"；
  d. 生成门禁：BP 结论必须带确认来源标签，否则视为讨论（同来源分层规则）。

优化点 3：比赛时间轴 / 时间进度展示（2026-08-27 用户提出）。
  需求：希望有一个"比赛时间轴 / 时间进度"——展示比赛进行到哪个阶段/节点、
  各节点（赛前/BP/局中/局末）的时间进度与先后关系，用户能直观看到
  "比赛现在走到哪一步、下一步是什么"。
  思考方向（待统一决策）：
  a. 在比赛详情页（时间轴壳）上方加"比赛进度条/节点时间轴"：
     赛前 → BP → 局中 → 局末（逐局），当前节点高亮，已完成节点打勾，
     未到节点置灰；
  b. 数据来源：比赛 start/end + 各节点生成时间 + 小局结算状态
     （game_status）自动驱动；
  c. 移动端友好，加载即见，不依赖点击。
```

## 2026-08-29 00:40-01:30 · 8-28 五场整场复盘补齐 + 时间轴壳修复（完成）

```text
完成（线上已上线验证）：
1. 8-28 已结束比赛全部补齐整场复盘（12 段决策导向模板，官方源仲裁）：
   CS2 Spirit 2-0 G2（Dust2 13:6 / Cache 13:9）、CS2 Aurora 2-0 DENDELE
   （Cache 13:7 / Mirage 16:12 OT）、CS2 paiN 0-2 NAVI（Nuke 9:13 / Mirage 11:13）、
   LPL IG 3-0 TT、LPL NIP 3-0 EDG（Riot gameWins 官方）；连同已出的
   LCK BFX 3-2 BRO、LEC SHFT 2-0 TH，当日 7 场全部有整场复盘 + MD 镜像。
2. matches.json 台账：合并 LOL-BRO2-FOX1 重复条目、补齐 cs2-aurora-dendele、
   全部 event_slug 对齐 Polymarket 真实 slug（含 LEC lol-shft-th 修正）。
3. 时间轴壳生成器修复（vps_intel_pipeline.build_timeline_shell）：
   a. 队伍别名/全称匹配（team_names.json）：全称节点页对短名 teams 不再丢壳；
   b. 联赛前缀文件名（LCK-/CS2-/LPL-）可入壳；
   c. exact 只做优先级不丢候选：abbr 整场页不再挤掉全称节点页。
   已同步 VPS。
4. vps_publish.merge_settlements 按 event_slug 匹配去重（结算不再重复追加条目）；
   build_history_index 壳匹配支持 event_slug（历史页链接到时间轴壳）。
5. 灰信号库补 7 条 8-28 记录 + 3 个新实体（ZDZ/Leave/Luquetá）；DANMU_INTEL.md
   追加批次；knowledge/intel_pages/README.md 登记 4 份新 MD 镜像。
6. 线上验证：7 个整场页 200、7 个时间轴壳均含整场复盘入口、历史页 86 行无重复、
   8-28 每场均有情报链接。
待办/备注：
- paiN-NAVI 缺 g2_end 节点页（VPS 未产），壳内显示"此节点暂未采集数据"，
  整场复盘已覆盖终局；后续比赛确保 g2_end 触发。
- TH-SHFT/paiN-NAVI 各残留一个旧式壳（match_2026-08-28_xxx），无害但可后续清理。
```


## 2026-08-29 深水区反转统计（数据积累里程碑）

```text
基于 100 场快照批量提取 341 个深水案例（<=30c 后走势），核心结论：
  <=10c 深水反转率仅 4-5%（7c 加仓 = 彩票，非策略）；
  20-30c 深水反转率 45%（LoL）/36%（CS2）= 真正的低吸区间；
  整场深水反转率 14% << 局内 29%（整场深水回避）。
报告：reports/deep_zone_statistics_2026-08-29.html
数据：/tmp/deep_cases.json（341 例，可复用做回测）。
下一步：把近期待交易录入 knowledge/trades/ 结构化数据集，接深水区回测。
```
