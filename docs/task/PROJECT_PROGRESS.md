# 预测市场网格交易项目进度库

最后更新：2026-11-08

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
任务 8：形态结构重审与决策重构                      进行中 · P0 审计完成
任务 9：政治选举叙事幻觉雷达（中选/以色列/加拿大）   进行中 · 重划选区账本已加入
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
任务 8（2026-10-22 启动）：形态结构重审独立立项。P0 审计确认当前问题不是 1 分钟原始数据不足，而是候选未来固定压成 9 点、主图降采样到 72 点、历史观察点仅取 7 个固定进度，以及整段终局启发式标签折叠多形态。P1 已确认小局/整场必须分开统计和决策，并把内部英文代码与用户界面的纯中文展示名解耦；下一步先完成形态字典 V2，再重建分钟级样本、重做候选图与回测。详见 docs/task/PATTERN_STRUCTURE_REWORK.md。
任务 9（2026-10-23 启动，经用户校正）：政治选举叙事幻觉雷达。民调不做核心信号；页面改为“市场信念 x 盘口厚度 x 报价自洽 x 制度/选区结构”的只读观察框架，扫描联邦两院、54 个国会选区委、州长、州检察长、州务卿、州参议院、以色列与阿尔伯塔事件。2026-10-27 新增众议院重划选区账本，把已生效地图、被挡地图、党派目标优势与 218 席多数线分开呈现。详见 docs/task/ELECTION_INTELLIGENCE_WATCH.md。
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
7. 新增长期跟踪关注账号（2026-09-07）：0x82882d761b0d7f18b2cc286117d10cd8a15a5519
   （马斯克市场专项，用户观察收益平滑）；已建档 + 链上自检（pUSD $5,650.65），
   新增工具 tools/account_snapshot.py；首份 data-api 快照因当前网络到
   data-api/gamma 超时待补（工具已就绪，网络恢复即跑）。
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

  进度（2026-10-18）：已推进"触发/刷新及时性"部分（④ 把等待压短）——
  规则层实时页刷新 5 分钟 -> 30 秒、本地流水线触发 60 秒 -> 10 秒；
  又推进"AI 生成耗时"部分（① 模板化生成·治本）——AI 只填 JSON 字段、
  本地模板渲染 HTML，砍掉排版 token（max_tokens 8000->4000），对应方向 a
  的"摘要版必须结构清晰"落为本地模板保结构（非混乱快照）；
  再推进方向 c"并行强化"的跨场部分（③）——多场比赛并行生成互不排队
  （ThreadPoolExecutor，MAX_MATCH_WORKERS=3）。同场跨节点并行
  （G1 复盘 + G2 BP 同时）因 G2 BP 切片窗口锚定 G1 结束时间（数据依赖），
  用户已定"先不做"，单列为待办。详见文末三个 2026-10-18 归档段。

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

## 2026-08-30 胜负胜模式回测（用户假设验证，数据支撑）

```text
用户假设：BO3/BO5 中"G1 强队赢、G2 弱队扳平"后，G2 买强队整场有价格优势
（基于 Falcons/NAVI/T1 三场观察）。
回测（20 个有效样本，含胜负负反样本消除幸存者偏差）：
  全样本：命中 50%（10/20）、平均收益 -11% —— 假设整体不成立；
  决定性过滤：G2 结束强队整场价 >=0.5 -> 命中 80%（8/10）、平均 +28%；
              G2 结束强整 <0.5  -> 命中 20%（2/10）、平均 -51%；
  赛前强队 0.5-0.65（中等热门）-> 命中 100%（仅 4 场样本，幅度待验证）。
候选规则：G1 强赢 + G2 弱扳平 + G2 结束强整 >=0.5 才买强队整场，
  止损 = 强整跌破 0.35（G3 早期破位）；<0.5 为反指标（市场已转向）。
报告：reports/win_lose_win_backtest_2026-08-30.html
数据：/tmp/wlw_bt.json（20 场，可复用继续扩样本）
下一步：扩大样本（统计"胜负胜 vs 胜负负"占比、赛前强弱区间 x G2 结束价分层）。
```

## 2026-09-10 形态库批量入库（price_paths 47 -> 75）

```text
把 2026-08-30 ~ 09-09 复盘的 28 场赔率形态追加进 docs/data/intel/price_paths.json：
  - LCK/LPL/LEC 17 场（09-01~09-08）+ LCK CL 1 场（09-09 假赛质疑场）
  - CS2 FISSURE S3 7 场（09-09）+ G2-AUR1/FNC-GX/NSEA-DNSC 3 场（08-30/31）
形态来源：每场快照自动分类 classification.jsonl（A/B/C 家族标签 + 高低点），
  按 game1..game5 + series 逐侧登记（team:标签(低->高)）。
数据：price_paths.json 累计 75 条，updated 2026-09-10；source 指向对应复盘文档。
注意：旧 reviews 条目 schema 用 key_points，EWC/新增条目用 price_shape，两者并存可接受。
```

## 2026-08-30 弹幕采集会话切片防错（工具修复）

```text
事故：DK vs KT（08-30 16:00）聚合页 intel_danmu_live_lck_dk_kt_2026-08-30.html
  混入昨晚 LPL/LEC 弹幕（队伍情报出现 KC/GX/WE/TES 等），页面"数据源 2026-08-29 16:29 起"。
根因：
  1. 数据文件按日期命名（2026-08-30_huya_remember.jsonl），同一天多场会话共用，
     昨晚会话从 00:29 起写入，今天会话 append，danmu_live_monitor.py 读全文件未切片；
  2. 今天 Remember(528222) 采集进程死亡（16:19 后停更）未自动恢复；
  3. 昨天 lck_bfx_t1 遗留会话（launchd KeepAlive）占用 957 源，与今天会话归属混乱。
修复（已固化）：
  1. danmu_live_monitor.py 新增 --since <epoch> 参数，load_rows 只统计 ts>=since；
     run_danmu_session.py 启动 monitor 时自动传会话启动时刻 → 每场会话只统计本场弹幕；
  2. 停掉过期会话（launchctl bootout com.ad.danmu-lck-bfx-t1），重启 lck_dk_kt_2026-08-30
     （we957 + remember 双源），Remember 采集恢复、文件持续增长；
  3. 页面窗口修正为 2026-08-30 08:28 UTC 起，队伍情报恢复 DK/KT 本场内容。
防错规则（一次错误原则）：
  - 聚合监控必须按会话/比赛时间切片，禁止读整文件统计（同一天多场共用文件时必现混源）；
  - 新会话启动前先检查同 source 是否已有存活进程（防双写/归属混乱）；
  - 比赛日检查 Remember 等二路源采集心跳，停更即告警恢复。
```

## 2026-08-30 节点不生成根因修复（VPS 流水线 bug，用户持续反馈）

```text
用户症状：DK vs KT（08-30 16:00）比赛已开打 1 小时+，时间轴壳节点始终"暂未采集"，
多次排查未定位。本次从头到尾追到根因：
  1. 今日比赛清单 runtime/matches_today.json 停留在 08-25，未含 DK vs KT
     -> 重新 market_scanner.py --live 扫描 + export_today_matches.py 刷新
     （14 场含 lol-dk-kt-2026-08-30），scp 同步 VPS /opt/danmu-intel/data/；
  2. VPS 流水线 vps_intel_pipeline.py 在规则直出（USE_LLM=False）分支缺少
     rc/so/se 初始化，generate_game_node 写状态时 UnboundLocalError:
     cannot access local variable 'rc' -> 每次跑到节点生成即崩溃退出，
     节点永不产出（journalctl 有完整报错，此前未查看日志）。
     -> 补 rc=0; so=se=""（VPS 已 patch + py_compile 通过）；
  3. 修复后手动 systemctl start vps-intel-pipeline.service，
     lol-dk-kt-2026-08-30_g1_end.json + intel_danmu_Dplus KIA-KT Rolster_*
     _g1_end.html 生成，线上 match 壳出现 G1·REVIEW 入口，节点页 200 可访问。
防错规则（一次错误原则，全项目）：
  - 节点/情报"没更新"先查 VPS journalctl -u vps-intel-pipeline（崩溃/跳过有完整日志），
    禁止只查本地 reports 就说"正常"；
  - 每日清单（matches_today.json）是流水线输入，每日扫描后必须确认含当日场次，
    且 VPS 端存在（scp 同步成功 + grep 验证）；
  - 代码修复必须同步到 VPS（本地改 + VPS patch 双写），流水线跑的是服务器副本。
```

## 2026-08-31 云端成本对齐（任务 6 · 生成端配置交接）

```text
背景：云端"每页深度版"成本远高于本地实测量级。
实测基准（直连 DeepSeek API）：单页 ≈0.04–0.06 元（full≈3.3k in/7.9k out），
一场 BO3 ≈0.25–0.45 元。根因：云端仍走 Codex 全量生成（读 skill+模板+统计
再逐段写），本地走"固定提示词 + API"程序化生成，成本差一个量级以上。
产出：
  - docs/task/CLOUD_COST_CONFIG_CHECKLIST.md（8 项核对 + 同步步骤 + 降本可选）；
  - dist/intel_server_pkg/ 刷新为 2026-08-31 成本对齐版（34 文件，
    含时间戳修复后的 generate_intel_report.py 与 prompts/report_full.md），
    打 zip dist/intel_server_pkg_2026-08-31.zip 已可直发云端；
  - knowledge/DANMU_INTEL.md 追加批次记录。
防错规则（一次错误原则）：生成端代码/提示词每次变更后必须同步刷新部署包；
云端成本异常优先核对生成路径/模型/输入样本量/重试次数，验证以 API usage 为准。
```

## 2026-08-31 产品框架复跑（grill 收尾 · 任务 6 设计定稿）

```text
背景：8-23 grill 之后产品实际演化（官方数据成事实层、CS2 上线、VPS+DeepSeek 直连、
订阅付费墙上线），重新拷问产品框架与弹幕加工引擎，明确"核"= 弹幕加工。
产出：docs/task/INTEL_PRODUCT_FRAMEWORK_2026-08-31.md（A 产品框架 / B 弹幕加工引擎 /
C 情报输出模板 / D 四类失效模式防错 / E 执行待办），取代 8-23 产品决策记录。
关键拍板：
  - 定位：弹幕情报为内核（A）、综合情报台为形态（B），官方数据只校准不喧宾夺主；
  - 付费用户=决策者，普通观众=免费漏斗；免费=赛后复盘+验证闭环+画像摘要，Pro=进行中节点+完整画像；
  - 模板：弃 12 段"速览卡/方向板"，回归旧 10 段框架（INTEL_TEMPLATE_OLD_2026-08-31.md
    为唯一标准，样页 intel_danmu_LCKCL-NS-DNSC_full_old_2026-08-31.html），
    speedcard_consistency 不再作为发布门禁；
  - 引擎：采集→规则统计底料→LLM 自由提炼（保留特殊情报不过度过滤）→校验，不设独立归并层；
  - 节点：BP 后+局中先出快报（≤2min 硬统计，同 URL 升级完整版），局末直接完整版；
  - SLA：快报≤2min / 完整版≤10min / 复盘≤15min（北京时间）；事件驱动触发+四段时间戳；
  - 方向表达：只罗列证据（正锚/负锚/群体共识），不下"看好X"结论；
  - 覆盖：全量已登记联赛，缺数据显式标"无"，每场至少赛后复盘兜底。
防错规则（一次错误原则）：模板/生成端变更先改文档再动代码；执行顺序见
INTEL_PRODUCT_FRAMEWORK_2026-08-31.md 第 E 节（prompts 重写→生成器门禁→发布摘速览卡
门禁→G5 清理修复→同步云端→样页对照验证→发布）。
```

## 2026-08-31 云服务器 Python 项目 PRD 定稿（任务 6）

```text
产出：docs/task/DANMU_INTEL_SERVER_PRD_2026-08-31.md（v1.0，16 节）——
把弹幕情报库设计为可部署到 VPS 的标准 Python 工程：采集→切片→规则统计→
LLM 提炼→校验→输出（旧 10 段模板）→发布→订阅→情报库沉淀→监控。
关键设计：
  - 情报库沉淀层 = 知识资产：每场提炼本场情报资产，按 选手/队伍/英雄/联赛 四维
    幂等合并 + 趋势延伸 + 验证回填（不是自动合并弹幕统计）；
  - 核心定位（两份文档开头一致）：把电竞直播弹幕变成可溯源、可支持决策的情报，
    并且越攒越值钱；
  - 技术选型：Python 3.11、SQLite+JSONL、DeepSeek API 直连、systemd、静态站点；
  - SLA：快报≤2min / 完整版≤10min / 复盘≤15min（北京时间）。
关联：INTEL_PRODUCT_FRAMEWORK_2026-08-31.md（产品框架）已同步四维知识资产口径
并新增第 0 节核心定位。PRD 为设计定稿，代码未动。
```

## 2026-09-02 网站架构调整方案定稿（任务 6）

```text
决策：在现有架构基础上细化优化，不推倒重建；唯一必动=发布链路。
产出：docs/task/SITE_ARCHITECTURE_UPGRADE_2026-09-02.md（v1.0，三层升级）：
  - M1 发布层：nginx 直出 /var/www/danmu-pulse（发布≤10秒，满足快报≤2min SLA），
    GitHub Pages 降级为镜像备份；vps_publish 增加 --serve-local/--mirror-pages；
    DNS danmupulse.com → VPS + certbot 证书；
  - M2 页面骨架：5 个一级入口（今日/历史库/四维画像库/灰信号·验证闭环/订阅），
    Pro 墙收敛两处，10 段模板统一，时间轴壳强一致，G5 误删修复；
  - M3 数据服务：SLA 四段时间戳（触发→快报→完整→发布）、成本统计、
    自检扩展、TG 告警、局中节点机制恢复（GAME_NODE_MID_MIN）；
  - M4 验证上线：全站审计 + 回归全绿 + 灰度切 DNS + SLA 日报。
实施：分阶段独立交付可回退；M1 先行（发布变快），M2/M3 并行。
```

## 2026-09-02 网站架构升级 · M1 发布层 + M2 页面骨架完成（任务 6）

```text
M1 发布层（nginx 直出）：
  - VPS 安装 nginx 1.24 + /var/www/danmu-pulse webroot + danmupulse.com server 块
    （HTML no-cache、静态资源长缓存、gzip）；
  - vps_publish.py 增加 --serve-local/--no-mirror：发布=审计后同步 webroot（秒级）+ 推 Pages 镜像；
  - 实测：首页/今日页/局中页 nginx 直出 HTTP 200，HTML no-cache 头正确；
  - 待办：DNS danmupulse.com → 158.247.214.175 + certbot HTTPS（等用户切 DNS）。
M2 页面骨架：
  - 导航 5 一级入口：今日情报 / 历史情报库 / 四维画像库(intel_profiles_index) /
    灰信号·验证闭环(intel_gray_verification_stats) / 订阅；
  - Pro 墙收敛：PRO_RE 增加 intel_profile_*（完整画像），节点页仅未结束时付费；
  - 10 段模板切换：prompts 四份按 INTEL_TEMPLATE_OLD 重写（A 型 0-10/B 型 0-11/赛前 0-8），
    generate_intel_report.py 门禁按节点类型校验、重试提示语同步；
    实测 GEN-KT g1_mid 新格式页：0-11 段齐全、无速览卡/方向板残留；
  - 发布端摘除 speedcard 门禁（import/审计/--fix）；
  - G5 误删修复：保留依据改 runtime/vps_intel g5 状态文件；
    实测 NSEA-DNSC / KT.C-DRX.C G5 真页面已重新上线 webroot。
全部改动已同步 VPS 并编译通过；发布（webroot + Pages 镜像）执行成功。
```

## 2026-09-02 网站架构升级 · M3 数据服务层完成（任务 6）

```text
M3 数据服务层：
  - 局中节点自动生成：恢复 GAME_NODE_MID_MIN（小局开始 16 分钟后自动
    generate_game_node mid），gstatus 与兜底两条分支都已接入；
  - SLA 四段时间戳：管线状态文件记录 trigger_at / quick_at / full_at，
    vps_publish serve_webroot 时补 published_at；
  - 成本统计：generate_intel_report 每次调用写 runtime/llm_usage.jsonl
    （in/out tokens + 估算成本，路径修正为部署根 runtime/，非包目录）；
    实测 pre 页 cost≈0.037 元；
  - 自检扩展：vps_self_check 增加 sla_check（完整版≤10min/发布≤15min 达标率）
    与 cost_check（当日聚合，超 ¥10 阈值告警）；
  - TG 告警：runtime/alert_config.json（bot_token+chat_id 已部署，凭据不外显），
    SLA 超时 / 成本超限自动推送；
  - 修复自检付费墙误报：复用 vps_publish finished_slugs/finished_keys，
    site_issues 336 → 0；
  - 验证：pre 新框架 9 段 / game B 型 12 段生成通过；自检 sla=100% cost=0.04 元。
待办：局中机制在下一场进行中比赛实弹验证（今日 HLE-T1 16:00 / CS 14:00-20:00 北京）。
```

## 2026-09-02 时效性改造：事件驱动 + 快报先行（任务 6）

```text
背景：用户确认"单局 30-40 分钟，BP/局中情报推迟 20 分钟就失去价值"——
时效是产品价值命门。旧链路 BP 节点 4-20 分钟时间窗 + 10 分钟轮询 + 全量生成
+ 5 分钟发布 ≈ 20 分钟才上线。
改造（vps_intel_pipeline.py + systemd）：
  1. 快报先行：BP/局中节点先出"规则直出速览版"（硬统计：提及量/灰信号数/密度，
     render_fast_intel，秒级），完整版写临时文件、成功才同 URL 覆盖；
     深度失败保留速览版（source=fast）；
  2. 事件驱动 BP：官方局状态 inProgress（=开局/BP 结束）立即触发 BP 节点，
     不再等时间窗（GAME_NODE_BP_MIN 门控废弃，主分支改用官方事件）；
  3. 定时器加密：vps-intel-pipeline.timer 10min→2min；
     vps-publish.timer 5min→1min（nginx 秒级发布配合）；
  4. SLA 时间戳：quick_at（速览版上线）/ full_at（完整版覆盖）正确落状态文件。
预期效果：BP 快报 事件后 1-3 分钟上线（2 分钟轮询 + 秒级生成 + 1 分钟发布），
完整版 5-10 分钟同 URL 升级。
待验证：今日 14:00 CS / 16:00 HLE-T1 开赛后实测"事件→快报→完整版"三段耗时。
```

## 2026-09-02 实弹验证 + 两个准确性修复（任务 6）

```text
实测（16:00 HLE vs T1，官方 window 阵容）：
  - BP 快报：16:00:13 触发、速览版 +1s、完整版 +36s（秒级达标）；
    但切片仅 8 行 → LoL inProgress 含 BP 阶段，触发点在 BP 开始而非结束；
  - 局中触发提速：GAME_NODE_MID_MIN 16→10（BP 结束后 10 分钟）；
  - LoL BP 门控：等 g_start（估计 BP 结束）再出，覆盖 BP 讨论窗口。
准确性重大修复（历史库过期阵容冒充现状，踩"事实层只信官方"红线）：
  - 赛前页曾写 HLE ADC=Viper、T1 ADC=Gumayusi；官方 window 实测：
    HLE=Zeus/Kanavi/Zeka/Gumayusi/Delight（ADC=Gumayusi）、
    T1=Doran/Oner/Faker/Peyz/Keria（ADC=Peyz）；
  - 已用官方阵容重生成 HLE-T1 赛前页并发布；
  - prompts（pre/full/game）固化：首发/阵容只信官方，官方未确认标
    "首发待官方确认"，禁止历史库过期阵容断言现状；提及量只来自本场弹幕，
    引用历史库须标"跨场累计"+日期；
  - 根因：players.json 库队伍归属未随转会更新（Viper/Gumayusi/Peyz），
    待官方 roster 同步机制补上（M4+）。
CS 场次实测（14:10 RA1-LVG 等）：BP 快报触发+2-4s、完整版 40s-1.5min、
发布 40s（published_at 修复后实测）；发布字段覆盖 bug 已修（只记首次）。
```

## 2026-09-02 局势层准确性修复（用户实弹指出 · 最高教训）

```text
现象：HLE-T1 G1 局中页把"谁领先/对线优劣势"写反（用户实测：Zeus 领先多兰、
Peyz 领先 Gumayusi，情报相反）。
根因：阵容/比分走了官方源，但"局势/领先/经济/对线"事实层判断退化成了弹幕推断；
  HLE-T1 弹幕大量反讽与玩梗（"多兰牛逼/多兰专打宙斯"），LLM 把情绪当局势写反。
  叠加：Riot livestats window feed 对这场停滞（卡 16:11、26 分钟未更新），
  官方实时经济当时不可得。
修复：
  1. prompts（game/live）固化"局势纪律"：谁领先/经济/对线优劣势只允许写官方实时数据；
     官方滞后/缺失 → 写「官方实时数据滞后，局势待确认」，禁止用弹幕推断领先；
     弹幕只作情绪层且必须与局势分开呈现；反讽先语气判定，无法判定降级"未确认"；
  2. HLE-T1 G1 mid 页按新规则重生成并上线（3 处"待确认"，无领先断言）；
  3. 阵容纪律保持：HLE=Zeus/Kanavi/Zeka/Gumayusi/Delight，
     T1=Doran/Oner/Faker/Peyz/Keria（官方 window 双重确认）。
教训固化：事实层三件事（阵容/比分/局势领先）全部只信官方；弹幕永不作局势结论。
```

## 2026-09-08 全公开模式（会员系统暂时关闭 · 用户定）

```text
背景：产品运营调整——暂时关闭会员/付费墙，全站全员公开。
实现（可逆开关）：
  - runtime/free_mode.flag 存在 = free 模式（vps_publish/add_paywall/vps_self_check 读取）；
  - add_paywall.inject_all(free=True)：只清除所有付费墙脚本、不重注入；
  - vps_publish/vps_self_check 在 free 模式下跳过"缺付费墙"审计；
  - 恢复方法：删除 runtime/free_mode.flag → 下轮发布自动按规则重新注入付费墙。
验证：webroot 全站含 danmu_member_v1 页面 = 0；进行中节点页/画像页均公开可访问。
```

## 2026-09-02 情报评判标准定稿（用户确认 · 最高）

```text
用户明确评判标准（结合官方真实数据确认情报输出，三点缺一不可）：
  1. 及时性：以官方真实比赛时间为基准，快报≤2min / 完整版≤10min / 复盘≤15min；
  2. 准确性/有价值性：阵容比分结果只信官方源，弹幕只作情绪层；可溯源、带置信；
     有价值=能支持决策（灰信号/BP锚点/共识/盘口），非空结构；
  3. 复盘与长期积累：赛后复盘闭环（共识vs结果/灰信号兑现/BP锚点应验）+ 四维知识资产沉淀。
已写入 INTEL_PRODUCT_FRAMEWORK_2026-08-31.md 第 F 节；进入自检与 SLA 日报。
```

## 2026-09-08 虎扑热门赛事接口接入「今日比赛」补漏（用户需求 · 已上线）

```text
背景：今日比赛清单只来自 Polymarket 市场扫描；无 Polymarket 市场的 CS2
（IEM/EWC/裂变天地等）被系统性漏掉，今日页只有 LoL。
方案：接入虎扑公共赛事接口作为第二输入源（2026-09-08 逆向首页赛程 H5 验证）：
  GET https://match-api.hupu.com/1/8.2.10/matchallapi/bff/standard/
      getScheduleListByTagForH5?businessType=common&datasource=navigation&businessId=lol|cs2
  返回：日分组赛程（时间戳/状态/对阵/比分/赛事名/liveRoomLink），实测实时可用。
落地：
  - tools/fetch_hupu_esports.py：抓取并归一化到 data/hupu_esports_schedule.json
    （网络失败保留旧缓存，update_site_today 自动按 >5 分钟刷新）；
  - tools/update_site_today.py / build_home_today.py：按对阵去重合并虎扑场次，
    直接用虎扑状态（进行中/已结束/未开始）与比分展示，不覆盖 Polymarket 行；
  - 去重按对阵双方而非联赛字段（Polymarket LoL 标 LPL / 虎扑标 LoL）；
    回归测试 tests/test_today_page.py::test_split_teams_handles_*；
  - 已同步 VPS 并发布，danmupulse.com/intel/today.html 当日即出现 CS2 场次
    （FURIA vs GL / G2 vs Astralis 等，含明日预告 4 场）。
边界：虎扑只用于「热门比赛覆盖/展示」，比分与终局仍走官方源交叉仲裁。
```

## 2026-09-26 danmupulse.com 打不开 · 根因排查（域名被注册商暂停）

```text
现象：用户报 http://danmupulse.com/ 打不开。
排查结论：不是服务器/站点故障，是【域名被 Namecheap 暂停】：
  - whois 显示 Name Server 已被替换为
    FAILED-WHOIS-VERIFICATION.NAMECHEAP.COM / VERIFY-CONTACT-DETAILS.NAMECHEAP.COM
    （Namecheap 的"WHOIS/联系人验证未通过"占位域名服务器）；
  - 域名 2026-08-24 注册，2026-09-08 被替换 NS（正好 15 天 ICANN 验证期截止）；
  - Domain Status: clientTransferProhibited（未删，仅暂停解析）；
  - 解析到 198.18.x（本机代理 fake-ip）+ registrar 验证页，非原站。
源站健康（排除服务器问题）：
  - VPS nginx active，唯一 server 块 danmupulse.com → root /var/www/danmu-pulse；
  - 本机 curl http://127.0.0.1/ 首页 200（标题"弹幕情报库 · Danmu Intel"），
    /intel/today.html 200；
  - 直连 IP http://158.247.214.175/ 可作临时入口（HTTP/IP，无证书）。
历史口径：09-02 记录托管为 GitHub Pages（danmupulse.com → 185.199.x.x），
  DNS 切 VPS + certbot 仍在待办；VPS 目前只监听 80，无 443/证书。
修复动作（需域名所有者）：
  1) 登录 Namecheap → Domain List → danmupulse.com → "Verify Contacts"，
     向 registrant 邮箱重发验证邮件并点击验证链接；
  2) 若 registrant 邮箱失效，先在 Contacts 改邮箱再验证；
  3) 验证通过后 Namecheap 恢复原 NS，DNS 生效即可重新访问；
  4) 长期按时完成 ICANN 验证，避免再次被暂停。
可选临时缓解：临时移除 site_repo 的 CNAME 文件 → GitHub Pages 走
  https://adul9981.github.io/danmu-intel/（恢复域名后再加回）。
```

### 2026-09-26 已执行的修复（当次会话）

```text
1) 临时摘除自定义域名，站点立刻恢复公网 HTTPS 访问：
   - 删除仓库 CNAME（原值备份 runtime/domain_backup/CNAME.danmupulse.com.backup）；
   - GitHub Pages 自定义域名置空（gh api -X PUT .../pages -f cname=""）；
   - 验证：https://adul9981.github.io/danmu-intel/ 首页/今日页 200，
     09-09 整场复盘页 200；过了一个自动发布周期仍正常（CNAME 未被推回）。
2) 域名根因未解（需所有者验证）→ 恢复步骤已写进交接包 03 号文件。
3) 采集/生成/发布链路体检：nginx active、danmu-session active、
   stats-server active、三个 timer 正常；发现 UFW 未放行 80/443，
   VPS 直出对外不可用（文档已记录，需确认后再放行 + certbot）。
4) 产出服务器交接包（配置 + 说明），本机与服务器各一份：
   docs/task/server_handover_2026-09-26/（00-06 说明 + config_files 原文）
   docs/task/server_handover_2026-09-26.zip
   服务器：/opt/danmu-intel/handover_2026-09-26/ 与 /opt/danmu-intel/server_handover_2026-09-26.zip
5) 敏感信息纪律：交接包只写密钥"位置/用途/轮换方法"，不含任何明文密钥。
```

## 2026-09-08 CS2 队伍×地图战绩库 + 可见出口（用户反馈 · 已上线）

```text
背景：用户反馈"哪里能看到每个队伍对每张图的胜利情况"——此前 maps.json 只有
强图/弱图等弹幕锚点，无结构化官方 W/L；用户也要求这是情报库长期资产。
落地：
  1. docs/data/intel/map_records.json（新库，官方事实层）：
     records = 逐场逐图（match_id/date/map/双方/比分/胜者/来源）；
     team_map_stats = 队伍×地图聚合（场次/W-L/胜率/最近日期）；
  2. tools/sync_map_records.py：只收"可确认胜者"的官方记录（official_matches
     maps + 台账横扫/显式胜者），2:1 无显式胜者的分数串待官方逐图源回填——
     宁可少、不可错；VPS 发布流水线已接入，CS 结算后自动重跑；
  3. 可见出口：队伍画像页新增「CS2 地图战绩（官方累计）」卡；
     reports/intel_map_records.html 提供 队伍×地图矩阵 + 逐场明细；
     画像库总览已加入口；线上 danmupulse.com/intel/intel_map_records.html 已发布；
  4. 纪律：官方战绩与弹幕"强图/弱图"anchors 分文件/分栏，不混为事实；
     样本少慎用、当日状态 > 历史图池（沿用 08-30 教训）。
```

## 2026-09-09/10 LCK CL NS.EA vs DNS.C 整场复盘 + 模板两新卡 + LCK CL 自动入清单（用户确认"都做吧"）

```text
A. NS.EA vs DNS.C 整场复盘（已上线）
   - 官方口径：DNS.C 3:2 NS.EA（Riot event 116889604984222987，gameWins NS=2/DNS=3，
     让二追三：G1/G2 NS.EA、G3-G5 DNS.C；Polymarket lol-dnsc-nsea-2026-09-09
     20:35 结算 DNS 100c）；
   - 数据：SOOP LCK_CL 官方房 15,631 条（15:36–20:51 北京）+ Riot window G1-G5 阵容；
   - 灰信号核查：全系列 44 条灰词（패작8/일부러10/던지58/고의6），G3-G5 密集
     "故意送/教练指使"质疑，双向（DNS Lancer + NS 中野）；用户口径"标准假赛"记
     allegation-pending，官方无操纵结论（观众质疑·非结论）；
   - 关键盘口：G3 DNS 0.2c→100c（18:21→18:28 七分钟 V 型）；整场 20:35 定 DNS 100c；
   - 产物：reports/intel_danmu_LCKCL-NS-DNSC_full_2026-09-09.html（35KB，含
     关键变量卡 + 阵容裁决卡）+ knowledge/intel_pages 同名 MD 镜像；
     matches.json / gray_signals / gray_entities 已登记；线上 danmupulse.com
     整场页 200，时间轴壳入口已挂通。

B. 模板新卡固化（2026-09-10）
   - knowledge/INTEL_HTML_TEMPLATE.md 新增「〇.0 关键变量卡 + 阵容裁决卡」：
     关键变量卡 = 变量|角色|作用机制|提及量|方向置信（谁左右战局）；
     阵容裁决卡 = 局|官方阵容|BP后弹幕裁决|应验/背离（BP 后优劣闭环）；
   - 本场为首批试产样例（reports/intel_danmu_LCKCL-NS-DNSC_full_2026-09-09.html）。

C. LCK CL / 非 Polymarket 场次自动进今日清单与管线（2026-09-10 修复）
   - 根因：今日清单与 vps 管线只吃 Polymarket market_scanner 输出
     （watchlist_events.json），LCK CL 等官方场次在 Polymarket 无市场时
     系统性漏掉（09-09 NS vs DNS 需用户口播才补）；
   - 修复：
     1) 新增 tools/fetch_official_lol_schedule.py（Riot getSchedule 拉
        LCK CL/LCK/LPL/LEC/LCP 今日+明日官方场次，归一为 watchlist 同构）；
     2) export_today_matches.py 支持 --official 合并（队名归一化去重，
        同场保留 Polymarket 条目并补官方比赛 id + LCK CL 联赛名）；
     3) update_site_today.py 增加第三输入源（官方场次行、无市场时不给
        市场链接、状态按官方 state），并自动刷新官方缓存；
     4) runtime/run_daily_polymarket.command 每日流程加入官方赛程拉取；
     5) 时间轴壳前缀表补 "lckcl-"（根因：此前所有 LCKCL- 前缀情报页
        都进不了壳，故 09-09 整场页入口显示"暂未采集"）；
     6) 回归：tests/test_official_schedule_merge.py 新增；相关测试全绿；
   - 验证：09-10 今日清单正确输出 LCK CL（T1A vs DKC · LCK CL 标签）
     + 明日 DNS vs KT / GX vs NAVI，且与 Polymarket 行去重不重复。
```

## 2026-10-01 假赛（剧本）情报库立项 + 价格事实层首跑（用户定稿 · 任务 6）

```text
用户定稿想法：
  1. 电竞假赛多，队伍犯过一次一定会再犯 → 必须重点标记、再犯升级；
  2. 想知道过去三个月有多少队伍出现「赛前高胜率、最后时刻直接反转」（LoL/Dota/CS 都要看）；
  3. 假赛情报库两个层次成果：① 识别准确率（现在做）② 跟着下单的收益率（后置）。

A. 设计文档（新增）
   - docs/task/MATCH_FIX_INTEL_LIBRARY.md：两年成果定义、识别口径（价格事实层/
     弹幕共识层/外部证据层）、再犯升级与降档规则、数据缺口、纪律红线、路线 P0-P3。
   - 与 gray_entities / gray_signals / FIXED_MATCH_SUSPECT_CASES 的关系写清：
     本库 = 灰信号库的价格事实层补强 + 两层成果指标化，不覆盖既有口径。

B. 价格事实层扫描工具（新增，零 token、只读）
   - tools/analyze_favorite_reversal.py：从归档快照算「赛前平台价 / 盘中峰值 /
     峰值位置 / 终局」，判定 A 赛前热门输盘 / B 大热输盘 / C 末段反转 /
     D 单局高位崩盘 / E 热门单局崩盘；输出 JSON + MD + SAP 风格 HTML。
   - 赛前平台价的取法用 15 场有官方开赛时间的比赛校准，误差 ≤2c
     （NAVI 0.815 vs 实际 0.805；DNS.C/NS.EA 0.575 vs 0.575）。

C. 首跑基线（2026-08-05 ~ 09-09，126 场，全部已结算）
   - A=5（AL、BLG、NS、WE×2）/ B=2（WE、NS）/ C=3（AL、WE×2）
   - D=24（快速崩 17）/ E=8（全部 LoL：AL、BLG、BRO.C、KC、NS、MKOI、T1A、WE）
   - 队伍榜前列：WE（整场 2 次末段反转 + 1 次热门单局崩盘）
   - 外部证据交叉：WE vs EDG（08-19）弹幕"WE 打假赛" + 价格事实层同向 = 两路共振
   - 事后上界收益率（仅参照，非可执行）：E 类中位 +1169.8%、C 类中位 +325.5%
   - 产物：reports/favorite_reversal_scan_2026-10-01.{json,md,html}

D. 待办
   - P1：回迁 2026-07 与 09-10 之后的价格快照，跑满「三个月」口径；
        价格事实层 × 灰信号库自动交叉，生成分层疑似名单；
   - P2：名单再犯升级自动化 + 比赛页/统计页展示 + 识别准确率月度滚动；
   - P3：可执行进场时点的收益率回测（禁止用事后最优价当业绩）。

纪律：价格异动 ≠ 假赛；疑似 ≠ 认定；对外统一"观众质疑·非结论"，
      识别结果不得直接作为实盘下单依据。
```

## 2026-10-03 假赛情报库 P1：三个月价格快照补齐 + 扫描口径修正（任务 6）

```text
A. 取数通道（韩国出口被 451）
   - 现象：本机（Shadowrocket 韩国节点）与云服务器（首尔 Vultr）读 Polymarket
     均 451 / Cloudflare 1026；日本/美国公共出口 200。
   - 结论：不是脚本问题，是出口地区被拒。取数层增加出口池兜底
     （tools/pm_proxy_pool.py / pm_http.py），大批量回补改走 GitHub Actions
     托管跑批（美国出口稳定）：3384 市场切 23 块并行 → artifact → 回灌本地。
   - 结果：2026-07-01~08-04 覆盖 1821/1829；2026-09-10~10-01 覆盖 1554/1555；
     9 条缺口经逐条核对均为无成交/无行情真空档（非抓取失败）。
   - 文档：docs/task/PM_DATA_ACCESS_2026-10-02.md（含两条防错教训：
     请求失败≠没有数据；ISO 时间字段解析必须兼容带偏移量）。

B. 扫描口径修正（tools/analyze_favorite_reversal.py）
   1) 收益两层口径，禁止混用：
      † 可执行 = 赛前按对手价买弱侧持有到结算（下单时点明确）；
      ‡ 参照上界 = 热门峰值处进场（事后最优），对手价 <2c 标"不可执行"不进统计。
      教训：cs2-bsta-youren-2026-09-14 峰值 0.9995 → 上界 199900%，曾当业绩展示。
   2) 「赛前价可靠」门禁：平台起点必须在价格窗口前 25% 内（pre_is_prematch），
      否则可能是局中平盘；54/190 条 A 类已标注，并另出"赛前确认组"。
      教训：不做这一步，LoL 基线跟单收益从 -3.1% 虚高成 +9.4%。
   3) 一级分类按 slug 前缀分游戏（lol-/cs2-/dota2-/val-），不再用子串匹配。
   4) 区间按 slug 内日期严格裁剪（--since/--until），外溢 22 条已剔除。
   5) 新增基线对照：赛前 ≥0.70 全部整场侧 1101 条、输盘率 17.3%、
      无差别跟单期望收益 -15.0%（赛前确认组 -17.5%，分游戏全为负）
      → 证明「赛前高胜率」单独不是信号，必须叠加筛选。
   6) 默认三个月口径：不给 --since/--until 时自动取 --date 往前 92 天，
      裸跑命令与文档基线一致，避免多口径混用。

C. 三个月基线（窗口 2026-07-03 ~ 10-01，3226 场）
   A=190（赛前确认 136）/ B=110 / C=129 / D=24（快速崩 17）/ E=8（全 LoL）
   分游戏：CS2 1793 场 A=79/C=55；LoL 733 场 A=71/C=44/D=19/E=8；
          Valorant 331 场 A=24/C=17；Dota2 369 场 A=16/C=13
   队伍榜前列（三个月）：Bushido Wildcats、HOTU、ECSTATIC、Nuclear TigeRES、T1、
     Conviction、Forsaken、G2 NORD、Barça eSports、WE、KT、LYON、Gentle Mates GC、
     Team Falcons VEGA、1win、Nemiga、VIT、Keyd、Marsborne、TDK、9z
   产物：reports/favorite_reversal_scan_2026-10-03.{json,md,html}

D. 已知缺口 / 待办
   - CS2 / Dota2 / Valorant 队伍未登记 docs/data/intel/team_names.json，
     报告暂用原始写法；需扩充登记表后重跑归一。
   - 价格事实层 × 灰信号库自动交叉（P1 剩余）、分层疑似名单（P1 剩余）。
   - 口径 A（信号时点可执行 ROI）需盘口深度数据，当前快照不含，暂不实现。
   - 临时私有仓库 Adul9981/pm-price-backfill 已完成使命，可删（未推业务代码）。

纪律不变：价格异动 ≠ 假赛；疑似 ≠ 认定；对外统一"观众质疑·非结论"，
      识别结果不得直接作为实盘下单依据。
```

## 2026-10-04 清理：历史情报库联赛标签 + 本地站点副本刷新（任务 6）

```text
A. 触发
   - 用户："WSCI 要加入（监控白名单），顺手清理掉（既有失败测试）"；
   - 清理由 DANMU_GAME_SCOPING_MIGRATION_2026-09-26 第 5 节记录的三项"既有失败"
     （本地 .danmu_intel_site 为 09-10 副本、match_index.json 为 08-29 产物）。

B. 刷新后暴露的真实缺陷（并已修复）
   1. 联赛标签 "-"：同一场比赛多页（G1/G2/full/live）扫描顺序不定，先扫到无联赛
      信息的页就把整行写成 "-"；CS2 页还被误标 LEC（NAVI/G2 跨游戏队误判）。
      → tools/build_history_index.py：
        · 联赛判定补"文件名联赛前缀"一级（CS2-/DOTA-/LCKCL-…，生成器既有约定）；
        · league_by_teams 改读注册表 team_names.json 的 league 字段，跨游戏队
          （NAVI/G2/Legacy/Spirit/VIT）一律不猜；"Challengers"=LCK CL（LFL/LVP 除外）；
        · CS2 赛事写法（EWC CS2 / ESL Pro League / BLAST / IEM）纳入 normalize_league；
        · 多页合并时联赛可回填；"情报"入口按节点优先级确定性选页（不再由扫描顺序决定）；
        · matches.json 只给"LoL 其他"而标题能定二级联赛时，以标题为准。
   2. 市场链接页空壳：本地无当日/当周扫描数据时三张卡全空，页面变死链页。
      → 回退展示最近 12 场已确认市场链接（真实历史 slug）。
   3. 无情报占位行 result 为空 → 历史页显示"待确认"；改为显式标注"暂无情报（未采集）"。
   4. 站点导航注入要跑两遍才收敛（test_nav_injection_is_idempotent 偶发红）：
      add_site_nav 清除旧面包屑时多删了后面的换行 → 修正正则（一次性收敛）。
   5. 队伍命名：新增别名 lgc→legacy、fal2→flc；删除重复条目 dendele
      （与 dendelecs 同名别名冲突，曾把 Spirit 一场拆成两行）；
      HLE-BFX 裸缩写页按仓库内跨源说明映射回同一场 LCK CL（BFX.Y vs HLE.C）。

C. 结果与验证
   - pytest tests/：127 → 132 passed / 0 failed（新增 4 条回归锁联赛判定与重复行）；
   - 历史库 134 场：联赛标签 0 个 "-"、0 个未知、0 行空结果、0 组重复行；
   - 站点副本：build_history_index → publish_intel_pages（不带 --push）刷新完成，
     history.html / market_links.html 已上线到本地副本；**未推送远端**。

D. 未做（需用户决策）
   - 监控白名单仅加了 WSCI（config/market_watchlist.json）；实测 Gamma 300 个
     电竞事件里白名单只命中 3 个，EMEA Masters / Demacia Cup / ESL Pro League /
     Asian Games 等 138 场未覆盖 —— 是否扩白名单待定。
   - → 2026-10-05 已补（EMEA Masters / Demacia Cup / Asian Games / LCS /
     ESL Pro League / BLAST Slam），见「2026-10-05 监控白名单补齐」。
```

## 2026-10-04 待办：直播间中途切场（主播换台）的识别与切片隔离（任务 6）

```text
A. 现象（当天真实发生，用户标记为待办，待一起定方案）
   - 虎牙 123321（CSBOY 官方）在 EPL S24 同日两场并行时来回切台：
     20:20–20:26 9z-TYLOO → 20:27–20:46 Falcons-Aurora →
     20:47–20:50 9z-TYLOO → 20:51 起 Falcons-Aurora（用户 20:52 反馈"又切回来了"）；
     房间标题全程未更新（仍写"绿龙 VS PV"）→ 标题/房号/一房一场三类判据全失效。
   - 现行后果：按时间窗切出的弹幕会串场，污染灰信号/共识/密度/盘口对照，
     且同联赛跨场混源的危害与规则 19（禁跨联赛混源）同类。

B. 现有资产（规则有、工具在，但未接通）
   - 规则：knowledge/DANMU_CAPTURE_RULES.md §19bis「主播切赛识别」三信号（时间窗+内容提及+主播画像）；
   - 工具：tools/check_stream_match.py（已实现三信号打分）；
   - 实测结论（当日）：**暂不可用**——matches.json 无当日 CS2 场次（最后一条 09-09）
     导致工具直接报错；即便补上队伍信息，按同算法模拟仍会把 9z-TYLOO 时段判成
     "匹配本场"（假阴性），因为 TYLOO 未登记且 ≤2 字符 ASCII 关键词（如 "9z"）被主动排除。

C. 结论 / 硬前置
   - 缺的不是判定逻辑，是前置数据：**当日场次登记 + 联赛全量队伍/选手词表**；
   - 多房间同场采集本身即是天然交叉校验（今天 321123 全程稳定在 TYLOO-9Z）。

D. 产物与留痕
   - 方案待议文档：docs/task/STREAM_SWITCH_HANDLING.md（含候选方案 A–E、待决策 8 问）；
   - 切场日志：runtime/danmu_sessions/cs2_epl_s24_2026-10-04/switch_log.jsonl；
   - 欠账：reports/intel_danmu_CS2-FLC-AUR_G1_2026-10-04.html 完整性栏未标注
     20:47–20:50 串场时段，下一节点生成时一并补（剔除 + 标注）。

纪律：方案未定稿前不改采集/切片代码；不擅自上线；先攒样本再固化规则。
```

## 2026-10-05 监控白名单补齐：顶级赛事漏抓（任务 2 / 任务 6）

```text
A. 缺口实测（Gamma 电竞标签全量，635 事件）
   - 改前：白名单只命中 3 个（KeSPA Cup ×2 + LCK Challengers ×1）；
     其余 632 个未命中，其中"比赛类"覆盖明显缺失的有：
       LoL：Demacia Cup（3 场，单场 24h 成交 98 万/115 万/13 万）、
            Asian Games（11 场）、EMEA Masters（2 场）、LCS Promotion（2 场）；
       CS2：ESL Pro League（8 场，单场 24h 成交 4-8 万）；
       Dota2：BLAST Slam（3 场，3.5k-5.9k）、PARI Universe 资格赛（4 场，最高 7 万）。
   - 结论：不是"今天没比赛"，是白名单没登记（违反防错规则 1/4 的口径）。

B. 本次登记（config/market_watchlist.json）
   - LoL += EMEA Masters / Demacia Cup / Asian Games / LCS；
   - CS2 += ESL Pro League；
   - Dota2 += BLAST Slam。

C. live 验证（规则 4 强制，2026-10-05 08:49 UTC）
   - python3 tools/market_scanner.py --live --live-limit 100 --live-pages 3
   - 抓取 900 事件 / 电竞标签 300 / watchlist 命中 32（改前 3）/ 窗口内 13 场；
   - 今日实到：Demacia Cup 3 场、ESL Pro League 8 场、LCS Promotion 1 场，
     产出候选 4 个（reports/opportunity_scan_2026-10-05.md）；
   - 回归：tests/test_scan_regression.py 新增 6 条联赛标题（含 WSCI），
     全量 pytest 139 passed / 0 failed。

D. 已知缺口（未纳入，待用户决策）
   - CS2 三线赛事约 365 场（Exort 127 / European Pro League 57 / United21 52 /
     ESEA 43 / Gamers Club 36 / CCT 29 / 1win 8 / Dust2.dk 7 / NODWIN 4 /
     DACH 2）：多无 24h 成交或 <1k，登记会把扫描面从 13 场推到 300+ 场，
     建议不纳入（宁缺毋滥）；如要纳入，建议只按"有成交量"过滤后登记。
   - 其他一级游戏外的项目：R6 Siege 14 / MLBB 16 / Honor of Kings 9 /
     Overwatch 5 / StarCraft II 2 —— 超出当前一级分类（LoL/CS2/Dota2），暂不纳入。
   - Valorant 40 场（VCT Champions 4 场，成交 0.3k-5.3k）：一级标准里是"预留"，
     纳入需同步定采集源与情报口径，待决策。
   - 采集侧未登记：EMEA Masters / Demacia Cup / Asian Games / LCS /
     ESL Pro League / BLAST Slam 在 docs/data/intel/leagues.json 还没有默认采集集
     （平台/直播间），即"扫描到但没弹幕源"——下一步按 17ter 流程补源。
```

## 2026-10-11 GitHub 失败邮件修复（任务 6 · 基础设施）

```text
A. 现象：邮箱持续收到 GitHub Actions 失败提醒（约 2 封/天），来自两个工作流：
   - game-status（auto publish intel pages）：占约 8/10；
   - pages build and deployment：占约 2/10。

B. 根因（两个不同问题，勿混为一谈）
   1) game-status = 我们自己的脚本问题：.github/scripts/game_status_fetch.py
      用裸 urllib，Polymarket gamma 偶发 500 直接抛异常 -> 整个 job 失败 -> 邮件。
      （日志：urllib.error.HTTPError: HTTP Error 500 at get()）
   2) pages build = GitHub 侧基础设施偶发：runner 拉 jekyll 构建镜像超时
      （docker pull ghcr.io/actions/jekyll-build-pages 时 context deadline exceeded），
      与我们仓库无关；但被"每分钟一次推送"放大（每次推送都触发一次 Pages 构建）。

C. 修复（已上线并验证）
   1) game_status_fetch.py（提交到 data + main 两个分支，data 才是实际执行副本）：
      - get() 加退避重试：5 次、1/2/4/8s + 抖动，只重试 5xx/429/超时，4xx 立即失败；
      - 上游整体不可用 -> 打印 ::warning:: 并保留上一份数据（不覆盖、不失败），
        数据自愈只需 5 分钟——避免"上游抖一下 = 一封失败邮件"；
      - 单场详情抓取失败不再静默跳过，累积后写 ::warning:: 留痕。
      本地已用桩函数验证：5xx 重试后可恢复、4xx 快速失败、断网时退出码 0 且不写文件。
   2) 消除整站每分钟 churn（tools/build_intel_profiles.py）：
      画像页脚"生成：%Y-%m-%d %H:%M" -> 只到日；此前每轮重写 159 个 HTML
      （155 个只有时间戳变化），现已降到 1 个（实时页）。
   3) 镜像推送节流（tools/vps_publish.py）：
      仅"实时页/心跳"变化时，最多每 600s 推一次；含真实内容变更（新情报页、
      今日页、历史库）立即推送。nginx 直出不受影响（仍每分钟最新）。
      状态文件 runtime/vps_mirror_last_push.txt；已在服务器观察到
      "镜像推送节流：仅实时页变化"日志，15:38 新节点页发布时仍按真实变更即时推送。

D. 预期效果：Pages 构建从 ~1440 次/天降到 ~144 次/天，叠加脚本重试后，
   失败邮件应趋近于 0（Pages 剩余风险为 GitHub 自身容器拉取超时）。

E. 回滚：服务器备份 /opt/danmu-intel/runtime/backup_20261011/
   （vps_publish.py / build_intel_profiles.py 原版）。
```

## 2026-10-15 形态结构库批量入库：最近一批 LoL 比赛（price_paths 114 -> 371）

```text
A. 需求（用户）：最近很多场 LoL 比赛，把"每个小局 + 整局"的 K 线走势形态结构记录进形态库
   （形态库此前已积累 114 条）。

B. 范围界定（重要）：10-02 起（含德玛西亚杯 DCGI 场次）按用户 2026-10-12 指令不接入
   Polymarket，无价格序列 -> 无法出形态；因此本批覆盖"最后一批有价格数据"的区间
   2026-09-10 ~ 2026-10-01，共 260 场 LoL（全量，未挑选）。
   联赛构成：EMEA Masters 97 / 国际赛 71（WSCI 38 + Asian Games 14 + …）/ 其他赛区 46 /
   VCS 16 / LCS 8 / LPL 7 / LCK CL 6 / LEC 5 / LCK 2（LCK/LPL/LEC 正赛 9 月中旬已收官）。

C. 数据补全（原本只有"整场"序列）
   1) 新增 tools/index_game_markets.py：逐事件拉 gamma /events，索引 Match Winner +
      Game N Winner 市场 -> runtime/pm_backfill/index_lol_games_2026-09-10_2026-10-01.json
      （260 场 / 692 个市场；其中 133 场有逐局盘）。
   2) 新增 tools/fetch_game_market_series.py：公共出口池已失效（backfill_price_fast 会
      ZeroDivisionError），改走 pm_http.get_json 的公共只读 CORS 兜底 + 分片并行
      （4 分片 5.3 分钟，ok=427 / fail=0 / empty=0），写入 docs/data/snapshots/<event>/。
   3) 粒度真相（2026-10-18 更正：以下结论错误，根因是固定传了 interval）：
      历史市场只有 10 分钟采样（fidelity=1 返回 0 点，1 分钟不可回溯），
      小局约 45 分钟 => 4-6 个点，已在页面显式标注"小局形态为粗粒度方向参考"。

D. 入库（新增 tools/build_pattern_library.py）
   - 逐场解析 整场 <slug>__i__Team.jsonl + 小局 <slug>-gameN__i__Team.jsonl；
   - 用 tools/classify_pattern.py（A/B/C + 热门压制）分别打标，生成
     price_shape = "game1:… | game2:… | series:…"（低/高按该侧全窗口 min/max）；
   - 结果与比分：整场以结算价定胜者，比分由逐局归属统计，决胜局无独立市场时按整场归属补足
     （39 场，已在 result 里注明）；未结算/无整场定价的 3 场不入库（缺口）；
   - 已存在条目默认不覆盖（--update 只刷新本工具产出的条目，避免动到人工复盘条目）。

E. 产物
   - docs/data/intel/price_paths.json：114 -> 371 条（新增 257，全部标注 600s 粒度）；
   - reports/pattern_shapes_lol_2026-0910_1001.html（SAP/Apple 风格：形态频次 + 按联赛逐场
     明细 + 缺口说明），明细 JSON 同名 .json；
   - 抽查校验：LCK 09-12 HLE 3:1 T1、LCK 09-13 GEN 3:1 HLE、LPL 09-13 AL 3:1 BLG、
     LEC 09-11 NAVI 3:2 GX、LCS 09-12 C9 3:0 SR 均与官方 gameWins 一致。

F. 形态频次（本批，逐局 260 场中 133 场有小局盘 = 约 460 个市场侧）
   小局：B4 直线阴跌 379 / C2 五五开开局碾压 208 / A2 中位 U 型反转 127 / A5 W 型双底 69 /
        C1 中位震荡 52 / A3 折价修复 41 / 热门全程压制 29 / B2 死亡螺旋 26 / A7 19 / A1 12；
   整局：B4 直线阴跌 214 / A3 折价修复 102 / 热门全程压制 76 / C2 70 / B4 低开阴跌 67 /
        A2 60 / A4 下狗整场反转 35 / B2 23 / A1 12。
   备注：10 分钟粒度会放大"B4 直线阴跌"与"未知"（C1/细形态识别需要 1 分钟数据）。

G. 未做 / 待办
   - 10-02 之后（含 DCGI 德杯）无价格数据，若要继续沉淀需重新接入 Polymarket 或改用
     官方/第三方赔率源；
   - 本批 127 场无逐局盘（仅整场形态），如需小局形态只能等以后有新数据源；
   - 形态频次已可直接支撑"形态频率"功能点，下一步可做 A1/A2/A4 分口径期望矩阵。
```

## 2026-10-15 追加：10 月 LoL（含德杯 DCGI）形态入库（price_paths 371 -> 427）

```text
A. 背景：用户要"最近 LoL 比赛"的形态。原以为 10-02 起无价格数据（德杯期间按指令未接入
   Polymarket）；实测 Polymarket 历史市场仍可回补（gamma 事件存在、逐局盘齐全），
   因此把 2026-10-02 ~ 10-14 的 56 场 LoL 一并补入。

B. 枚举：gamma /events?tag_id=64&closed=true（order=startDate desc 翻页到 10-02）
   -> 10-02~10-14 共 56 场 LoL 事件（德杯 DCGI 19 / EMEA Masters 16 / 其他赛区 8 / LCS 6 / LCP 6 / VCS 1）。
   索引：runtime/pm_backfill/index_lol_games_2026-10-02_2026-10-14.json（244 个市场，56 场全部有逐局盘）。
   抓取：4 分片 3 分钟，ok=244 / fail=0 / empty=0。

C. 校验（Polymarket 结算 vs 官方/在库结果）：德杯 BFX 3:2 JDG、KT 3:2 VIT、WE 3:2 FLY、
   BRO 3:1 LGD、NAVI 2:0 FLY、JDG 2:0 SR、VIT 2:0 RED、LGD 2:0 JDG 全部一致；
   LCS 10-04 TL 3:1 LYON 与官方 gameWins 一致。

D. 产物：price_paths.json 427 条；reports/pattern_shapes_lol_2026-1002_1014.html（+明细 JSON）。
   德杯 19 场结果与比分全部为 Polymarket 结算推导，官方逐局阵容未回填。
```



## 2026-10-15 追加：形态结构库补 CS2 逐图 + 大联赛漏接（ESL Pro League S24）

```text
A. 需求（用户）："把这些形态都放到知识库里；先做 LoL 的形态，再做 CS 的形态，
   包括每个小局和整局的 CS。最近有几个大的联赛赛事我们都没接。"

B. 缺口定位（关键发现）：用 gamma tag_id=64 closed 事件清单（09-24~10-14 共 1,600 场）
   与 docs/data/snapshots 对比：
   - ESL Pro League S24（10-03~10-11，41 场）**一场都没接**；Thunderpick 组赛（10-10 起）同样全缺；
   - 存量 cs2-* 快照目录 1,971 个 **全部只有整场序列、没有任何逐图序列**（-gameN 文件为 0）；
   - 09-24~10-14 区间 CS2 事件 888 场，其中 617 场未入库（多为三级赛事：ESEA/CCT/Dust2.dk/United21 等，
     属 AGENTS 规则 4 的已知缺口）；LoL 同区间 0 场（9 月中旬各赛区收官后无 LoL 赛事）。

C. 工具改造（可复用）
   1) tools/index_game_markets.py：WINNER_GROUPS 增加 CS2 的 "Map N Winner"；
      新增 --league-keywords（按事件标题过滤一级赛事）与 --titles-out（事件标题缓存）。
   2) tools/build_pattern_library.py：新增 --slugs-file（按清单构建，避免扫全量三级赛事）；
      联赛归一对 CS2 统一为 "CS2"；页面文案随游戏切换（逐小局/逐图）。
   3) 新增 tools/pattern_library_stats.py：胜方/负方分开的形态统计 + 深水占比 + 让一追二基准率 + 低点买入倍数。
   4) 新增 tools/build_pattern_index.py：形态库总览页生成器（LoL + CS2 统一口径 + 期望值表）。

D. CS2 批次（2026-08-01 ~ 10-15，63 场：ESL Pro League 41 / EWC 12 / BLAST 10）
   - 索引 runtime/pm_backfill/index_cs2_tier1_2026-08_2026-10-15.json（189 个市场）；
     抓取 6 分片 1.3 分钟，ok=156 / fail=0 / empty=0（33 个整场序列已存在，跳过）。
   - price_paths.json：427 -> 472（+45；18 场为既有复盘条目，不覆盖）。
   - 页面 reports/pattern_shapes_cs2_2026-08_2026-10.html；总览页改为生成器产出 reports/pattern_shapes_index.html。

E. CS2 结论（样本 63 场，方向性可信）
   - 逐图主流形态与 LoL 一致：C2 五五开开局碾压 47% / A2 中位 U 型 28%；
   - **CS2 BO3 让一追二基准率 24%（14/59）> LoL BO3 17%（11/66）**——地图制下"输一图后整场折价"更常有回归；
   - 机械抄底（首次触及阈值价买入、持有到结算）在 CS2 **全阈值负期望**：
     逐图 0.35 -0.15 / 0.25 -0.25 / 0.10 -1.00（46 笔全错）；整局 0.35 -0.47；
   - 结构限制：Polymarket 的 CS2 BO3 只开 Map 1/Map 2 胜者盘（Map 3 仅 Rounds 盘），
     决胜图按整场结算归属补足（已在条目 result 注明）；BO5 开 Map 1-4。

F. 知识库落点（"形态进知识库"）
   - 新建 knowledge/PATTERN_STRUCTURE_LIBRARY.md（形态结构库·统计口径）：LoL 316 场 + CS2 63 场，
     口径/频次/深水/让一追二/期望值/形态→策略映射/复现命令/缺口；
   - knowledge/README.md 登记；docs/framework/REVERSAL_PATTERN_LIBRARY.md 加交叉引用；
   - 复盘索引新增 3 条批量入库记录（2 条 LoL + 1 条 CS2）；
   - 顺手修复：tools/append_knowledge_review.py 的索引重建会清空人工补写的"结果"列
     （一次重建清空 78 行），已改为保留已有非空结果（本次已从 git HEAD 与 .external 副本回填，
     refilled 102/115 行）。

G. 缺口（待办，勿静默跳过）
   - Thunderpick World Championship / PGL Bucharest 资格赛：不在登记一级赛事口径内，待用户确认是否登记；
   - CS2 三级赛事（ESEA/CCT/Dust2.dk/United21 等约 617 场 09-24~10-14 未接）仍未纳入；
   - Liquipedia/HLTV 二次交叉未完成（沙箱直连 TLS 失败、公共代理不支持非 Polymarket 域名），
     CS2 结果目前只以 Polymarket 结算价仲裁；
   - 10-15 及之后的比赛待赛后回补。
```

## 2026-10-15 追加：用户四点指令落地（登记 / 不接三级 / Liquipedia 通道 / 分钟级窗口）

```text
A. 背景：上一轮遗留四项待用户拍板事项。用户回复"第一个要登记；第二个不要；
   第三个再想想办法；第四个我还是 1 分钟级别的——最近几天结束的能做到 1 分钟级吗？"

B. ① 登记（已完成，上一轮已落）
   config/market_watchlist.json 的 cs2.league_keywords 扩登记 Thunderpick / PGL Bucharest /
   PGL Major / PGL Cluj / PGL，并加 tier_note（一级口径）；AGENTS 规则 4 同步更新。

C. ② 三级赛事（已完成，上一轮已落）
   CS2 三线赛事（Exort/ESEA/United21/Gamers Club/European Pro League/CCT/Dust2.dk/DACH/
   NODWIN/1win）明确"不接"，写入 AGENTS 规则 4 的未纳入清单。

D. ③ Liquipedia 交叉核对（本轮完成，"另想办法"= 换通道）
   1) 通道：python urllib 直连 liquipedia.net 在本机 TLS 失败，但 curl 直连正常
      → tools/fetch_cs2_liquipedia.py 的 fetch() 加 curl 回退（--compressed + UA），打通；
      并加 --raw-file（离线复算）与 --json（结构化输出）。
   2) 修两个解析 bug：
      - `{{Matchlist|...}}` 被前缀匹配当成 `{{Match}}` 整块吞掉 → 41 场只解析出 17 场；
        修：模板名后必须紧跟非标识符字符；
      - 加时比分在 `o1t1t/o1t1ct/o1t2t/o1t2ct`，只读常规时间会把 16:12 读成 "12:12"
        伪平局（曾把 vit-mouz 决赛 G3、lgc-prv G3 误判为"与 Polymarket 不一致"）。
   3) 新增 tools/crosscheck_cs2_liquipedia.py：按「队伍对 + 日期 ±1 天」配对，
      输出 agree/mismatch/单边独有清单 + markdown。
   4) 结果：ESL Pro League S24 **41 场 41/41 胜方一致（0 冲突）**；
      产物 runtime/pm_backfill/liquipedia_epl_s24.{wikitext,json}、
      runtime/pm_backfill/crosscheck_epl_s24.md。
   5) 仍待做：HLTV 层（阵容 / 地图禁选 / 排名），Cloudflare 反爬需人工或封装。

E. ④ 分钟级窗口 —— 实测结论：**只有最近约 24 小时可做，过期不可回溯**
   （2026-10-18 更正：该结论不成立。不传 interval 时 2 个月前的老比赛仍返回 60s，
   7 天窗口 9981 点；见本文件末尾“2026-10-18 分钟级可回溯修正”一节。）
   1) 实测（2026-10-15，CLOB prices-history，只读）：
      - 15.8h 前的市场 `interval=1d&fidelity=1` → 691-702 点/侧、中位间隔 60s、跨度 11.5h；
      - 32.8h / 37.9h 前的市场 → 同一参数 0 点；
      - 32.8h 前用 `interval=max&fidelity=1` → 459 点、中位间隔 600s（即历史库 600s 的来源，
        是服务端保留策略，不是参数选错）；
      - `interval=1m&fidelity=1` → 一律 0 点（无效口径）。
   2) 结论：**"最近几天结束的"做不到分钟级**；要分钟级必须赛后 ~24h 内归档。
   3) 改造（防覆盖）：fetch_game_market_series.py 新增 --hires-only / --hires-suffix，
      分钟级写 `<slug>__<idx>__<side>.hires.jsonl`，不覆盖赛前 36h 的 600s 序列；
      build_pattern_library.py 让 `.hires.jsonl` 优先，spacing_s 反映真实粒度。
   4) 首跑验证：lol-fox1-kt-2026-10-14（唯一落在 24h 窗口内、BO5）
      → 5 市场/10 文件 ok=5 fail=0，逐局+整局均 60s；重建 10-02~10-14 LoL 分段
      （刷新 56 条，price_paths 累计 472 不变），条目 source 标注"60s 粒度"。
   4bis) 窗口内还发现 2 场 CS2（cs2-9z-aur1 / cs2-fal2-nip，10-14 **Thunderpick 正赛**，
      属刚扩登记的一级赛事）→ 一并归档 6 市场 12 文件（600s 全量 + 60s hires）；
      把 09-01~10-15 新关键词索引并入主索引（189→346 市场 / 63→114 事件），
      CS2 形态批重建 63→65 场（price_paths 累计 **474**），总览页同步重建。
      新增 tools/build_hires_index.py：离线从既有索引筛出「最近 N 小时」市场，一条命令生成归档索引。
   4ter) 口径待定：新关键词索引的 114 场事件里 56 场是**资格赛**（PGL 各洲资格赛 /
      Thunderpick Closed Qualifier / PGL Open Qualifier），**未纳入统计**——是否按一级统计
      待用户确认（宁缺毋滥：未确认前不计入）。
   5) 新增 tools/probe_clob_granularity.py（粒度×年龄探测器，--no-pool 跳过空出口池）。
   6) 知识库落点：knowledge/PATTERN_STRUCTURE_LIBRARY.md 第一节口径改为"两档粒度"、
      新增 4.7 节（CS2 交叉核对结果）、第六节限制更新；AGENTS 新增规则 26（粒度与赛后
      24h 归档纪律）、规则 27（CS2 交叉核对通道 + 解析红线）。

F. 回归测试（AGENTS 规则 5 门禁）
   - tests/test_scan_regression.py：新增 CS2 一级赛事（Thunderpick / PGL）受理用例 +
     三级赛事（ESEA / CCT / United21）拒收用例，26 passed；
   - 新增 tests/test_pattern_granularity.py：锁定 `.hires.jsonl` 优先且不污染队伍名、
     只有 600s 序列时行为不变，2 passed。

G. 缺口（待办）
   - 分钟级归档仍是**手动/按需**、无赛后自动钩子 → 隔夜未跑即永久损失，
     属当前最大一条数据资产风险（已写入 AGENTS 规则 26b 与形态库第六节）；
   - Thunderpick / PGL 场次待补抓（登记已落，索引未重建）；
   - 存量 600s 条目无法提升粒度，只对"未来 24h 内"的场次生效。
```

## 2026-10-15 追加：粒度贯穿数据层与页面层（60s / 600s 严格分层）

```text
背景（用户指令）："这些数据要注意区分，通过 10 分钟颗粒度和 1 分钟颗粒度获取的数据
质量是不一样的。" 上一轮只做到"另存 .hires 并优先读取"，本轮把粒度做成
**数据层一等字段 + 页面/统计/回测强制分层**。

A. 数据层
   1) tools/build_pattern_library.py 新增 granularity_label(spacings)：
      按实际采样间隔归桶（<=120s -> 60s；>=240s -> 600s；两种并存 -> mixed；
      无样本 -> unknown）。有 ±1s 抖动（599/601），所以先归桶再输出，禁止原样输秒数。
   2) build_match() 返回值新增 `granularity`；写入 price_paths.json 时把它作为独立字段
      （此前粒度只写在 source 文本里，机器不可读）。
   3) 【关键修正】粒度判定**按实际采样间隔，不看文件名**：
      主序列里已有多场真实 60s 数据（赛后不久抓取时 `interval=1d&fidelity=1`
      本身就返回分钟级），并非只有 `.hires.jsonl` 才是 60s。
      实测分布（381 场）：CS2 53×600s + 12×60s；LoL 315×600s + 1×60s（fox1-kt 10-14）。
      -> 旧文档"CS2 只有 2 场 60s"是错的，本轮已全量修正。
   4) 三个报告全部重建（含此前无该字段的 LoL 09-10~10-01 260 场）；
      price_paths.json 仍为 **474** 条（只加字段，不增条数）。

B. 页面层
   1) 分段页 reports/pattern_shapes_*.html：卡片"粒度"由硬编码 10m 改为
      "600s + 60s · 600s 53 场 · 60s 12 场"；逐场明细每行加粒度角标（60s 高亮）；
      口径段改成两档说明（分辨率 + 窗口都不同，60s 更细但更短）。
   2) 总览页 reports/pattern_shapes_index.html：卡片显示粒度构成；
      每个游戏块加"数据粒度构成"行；期望值回测表加"粒度"列并按 600s / 60s 分层出表；
      口径段新增"两档不得互相推证"的显式说明与归档窗口条目
      （“不可回溯”措辞已于 2026-10-18 更正）。
   3) 期望值回测 dip_buy 改为按**实际间隔**分层（原先靠文件名，会把 10 场真实
      60s 的场次算进 600s 组）。修正后 CS2 600s 组 n 由 39 -> 30（整局 0.35 阈值）。

C. 统计层
   tools/pattern_library_stats.py 新增 --by-granularity：按粒度分组各出一份完整统计
   （胜方/负方频次、深水、让一追二、低点买入倍数），最后附一份全量对照并标注
   "两档混算，仅作对照"。输出里固定打印粒度构成。

D. 关键数字（分层后）
   CS2 让一追二（BO3）：600s 11/49 = 22% | 60s 3/12 = 25% | 合计 14/61 = 23%
     -> 该指标两档一致，不被粒度扭曲（结论沿用）。
   CS2 赢家侧曾 ≤0.30：整局 600s 12/53 = 23% / 60s 4/12 = 33%；逐图 600s 24/105 = 23% /
     60s 11/24 = 46% -> 深水口径**明显受粒度影响**，只能解读为采样精度，不是机会变多。
   CS2 机械抄底：600s 组 0.10 阈值逐图 35 笔全错、整局 20 笔全错（结论不变）；
     60s 组因 n 仅 7-20 笔且含"窗口更短 + 选择性偏差"，**只看不引用**。

E. 纪律固化
   AGENTS 规则 26c 改写：粒度以 `granularity` 字段为准、按实际间隔归桶、
   禁止靠文件名判断，并写明两档差异的三重来源（精度 / 窗口 / 选择性偏差）不得互相推证。

F. 回归测试
   tests/test_pattern_granularity.py 由 2 个用例扩到 5 个：
   新增 granularity_label 抖动归桶（599/601 -> 600s）、
   load_sides 按实际间隔分层且 60s/600s 去重（不因文件名误判）、
   dip_buy 分层（同一场 600s 看不到的深水只能在 60s 组计入）。
   tests/test_scan_regression.py 26 passed 不变；全量 147 passed / 3 failed
   （3 个失败仍是既存的站点构建产物问题：intel_gray_verification_stats.html 缺 favicon、
   两个 match 页关联断言，与本次改动无关）。

G. 事故与回滚（记录）
   首次重建 CS2 分段页时误用 `--range 2026-08-01:2026-10-15 --prefix cs2-` 全量扫描，
   把快照目录里 1243 个 cs2-* 目录当成比赛写进 price_paths.json（474 -> 1573）。
   已定位并按「slug 白名单」精确回滚至 474，同时把正确的 65 场 slug 清单固化到
   runtime/pm_backfill/cs2_pattern_slugs_2026-10-15.txt，后续重建一律用 --slugs-file。
   教训：形态库重建必须显式给 slugs-file，禁止用 range/prefix 全扫（磁盘上存在大量
   非比赛目录）。
```

## 2026-10-15 追加：粒度对照页 + 总览页补齐 LoL 全量（用户要求"画到 HTML 里"）

```text
1) 新增 tools/build_pattern_granularity_page.py -> reports/pattern_shapes_granularity.html
   回答"多少情报来自 1 分钟级 / 多少来自 10 分钟级"，四段结构：
   - 粒度普查：381 场里 60s 仅 13 场（3%）、600s 368 场；小局维度 752 个市场里
     60s 只有 28 个（4%）；并写明 60s 场次偏近期/受关注 = 选择性偏差；
   - 形态样本 × 粒度：11 个实际出现的标签逐条拆 60s / 600s（几乎全在 600s 组，
     60s 组每形态个位数），合计 <20 的标"样本不足"（A1/A5/A6/A7/C2 早期缩距）；
   - 关键结论来源分层：让一追二 BO3（60s 3/12=25% vs 600s 22/115=19%，合计 25/127=20%）、
     整局/逐局深水 ≤0.30 与 ≤0.20、机械抄底 0.35/0.25/0.10 的 n/命中/ROI，全部两档并列；
     明确"右列（600s）可当基线，左列（60s）只能当观察，两档不构成互推证据"；
   - 口径与限制：多标签、B 类是负方侧恒等式产物、定义 15 个标签仅 11 个出现、
     粒度按实际采样间隔归桶（不看文件名）。
2) 总览页 reports/pattern_shapes_index.html 补齐 LoL 09-10~10-01 的 260 场
   （此前只挂了 LoL 10-02~10-14 + CS2，与知识库"LoL 316 场"口径不一致）：
   现在卡片为"本批比赛 381（LoL 316 + CS2 65）/ 含逐局 252 / 粒度 600s 368 + 60s 13"，
   与粒度对照页、knowledge/PATTERN_STRUCTURE_LIBRARY.md 三处口径统一；
   并新增指向粒度对照页的入口。
3) 顺带修一处重复计数：同一市场同时有 600s 与 .hires 时，机械抄底回测此前两条都算，
   LoL 侧多算 1-2 笔（0.35 阈值 173->172 笔、命中 28%->27%、ROI +0.10->+0.09），
   去重后与知识库表格同步更新；结论方向不变。
4) 测试：tests/ 147 passed / 3 failed（3 个仍为既存站点构建产物问题，与本次无关）。
```

## 2026-10-15 追加：形态曲线图页（把标签还原成图形）+ 粒度筛选

```text
背景（用户要求）："我要能够看到那个形态变化……两根线、两个队伍，他们赔率交叉那个形态变化，
就是图形……首先分比赛，然后再分颗粒度，然后能够看到那个形态。" 此前只有文字标签
（如 "A2_中位U型反转 0.21->1.00"），看不到形状本身。

1) 新增 tools/build_pattern_charts.py（纯 SVG，无外部依赖）
   - 结构：先按比赛分卡片，卡片内 = 整局 + 每个小局/地图 各一张小图（330x118）；
   - 每张图两条线 = 两支队伍的代币价格（side 0 蓝 #0071e3 / side 1 橙 #ff9f0a），
     50c 虚线为领先权分界 => 两线交叉即"优势翻转"，翻转过程就是形态；
     粗实线 = 赢家侧、细淡线 = 输家侧；实心圆 = 该侧窗口低点，空心圆 = 终点；
   - 图下标注：队伍名 + 形态标签 + 低→高 + 终点 + 原始采样点数 + 粒度；
   - 顶部粒度筛选按钮（全部 / 只看 1 分钟级 / 只看 10 分钟级），按 data-gran 前端过滤；
   - 曲线用 LTTB 降采样（默认 180 点/线，保尖峰保形状），页面注明"绘图降采样、统计用全量"。
2) 产物（3 页 + 与总览/粒度页互链）
   - reports/pattern_charts_cs2_2026-08_2026-10.html（65 场 / 194 张图 / 0.86 MB）
   - reports/pattern_charts_lol_2026-1002_1014.html（56 场 / 230 张图 / 1.12 MB）
   - reports/pattern_charts_lol_2026-0910_1001.html（260 场 / 655 张图 / 3.16 MB）
   - build_pattern_index.py 与 build_pattern_granularity_page.py 自动按
     pattern_shapes_X -> pattern_charts_X 命名规则探测并挂入口（存在才挂）。
3) 校验：194 张图全部两条线、坐标无越界；50c 参考线 y=61（=8+106*0.5）；
   抽样 cs2-ast10-mouz-2026-08-01：1WIN 侧 0.00→0.38、Aurora 侧 0.62→1.00，
   与形态库记录的 low/high/end 完全一致，终点位置贴顶/贴底符合 y 轴反转。
4) 修正一处实现 bug：整局曲线最初只取了 side 0（单个市场两条序列），
   渲染成"单线图"（194 张里有 65 张）；改为按 side 索引分别取序列后双线正常。
```

## 2026-10-15 追加：形态分级体系页（用户问"一共能搞出多少种形态、该怎么分级"）

```text
背景（用户要求）："现在你看出来我们一共总结出多少种形态了吗？这里边有 CS 的，有英雄联盟的吗？
我希望两个赛事其实是分开的，然后小局、整局也是分开的，1 分钟、5 分钟也是分开的。
你考虑一下这个分级到底怎么分，看看我们一定可以搞出多少种形态。"

1) 定稿分级口径（写入页面 + knowledge/PATTERN_STRUCTURE_LIBRARY.md 新增"一·补"节）
   第 1 层 游戏 LoL / CS2 —— 必须拆（地图制 vs 小局制，市场结构不同）；
   第 2 层 范围 整局 / 逐局 —— 必须拆（LoL 逐局由 C2 开局碾压主导 298/569 ≈ 52%）；
   第 3 层 侧 胜方 / 负方 —— 分开统计，负方侧只作对照（B 类是恒等式衰减）；
   第 4 层 粒度 60s / 600s —— **暂不拆**，只当格内"数据质量档"
     （四主格 60s 仅 1 / 4 / 12 / 24 例，单独成表每格会掉到个位数；≥20 例再升格）；
   不拆 联赛（属策略层筛选参数，切碎样本）。
   => 有效主格 = 2 × 2 = 4。

2) 结论数字（胜方侧样本 1076 例）
   - 上限 = 分类器定义 16 个；C3「中位震荡后突破」手册有定义、classify_pattern.py 未实现，
     **不计入 16**（待决：补分类器 or 从手册撤下）。
   - 已观测 15 个（胜方侧 10 + 负方侧 5 个 B 类）；唯一未出现 = C1 中位震荡。
   - 四主格：LoL 整局 313 例/9 种/可用 5；LoL 逐局 569/9/5；CS2 整局 65/7/2；CS2 逐局 129/9/3。
   - 判断：形态种类够用，缺的是"每格 × 每种形态"的样本密度；CS2 两格需扩 3-5 倍。

3) 新增 tools/build_pattern_taxonomy_page.py -> reports/pattern_taxonomy.html
   （SAP/Apple 风格、移动端优先、favicon data URI）；
   页面数字全部由数据生成（样本量、粒度构成、可用形态数、关键结论句），
   并修掉三处自相矛盾口径：
     a) "已观测"卡片误算 16（把负方侧非 B 类噪声与"未知"也算进去）-> 改为 15（10 + 5 B 类）；
     b) 粒度句写"1 / 4 / 18 / 30 例"与第三节 1 / 4 / 12 / 24 不一致 -> 统一由数据生成；
     c) 结论段引用的样本基数（448/662、81/118）与第三节口径不同源 -> 统一为 313/569/65/129。

4) 入口串联：reports/pattern_shapes_index.html 增加"形态分级体系"入口；
   reports/pattern_shapes_granularity.html 的"形态标签 11 / 15"口径修正为
   "胜方侧 10 / 分类器定义 16"，与分级页对齐（一次错误原则：口径不一致即修）。
   tools/INDEX.md 补 build_pattern_taxonomy_page.py 条目。

5) 校验：写入重跑后正则抽检四个主格表 + 结论段，数字自洽（可用 5 / 5 / 2 / 3，种数 9/9/7/9）。
   待办（仍待用户拍板）：① 56 场资格赛（PGL 各洲资格赛 / Thunderpick Closed Qualifier）
   是否按一级统计；② 是否做赛后分钟级自动归档钩子（当前最大数据资产风险）。
```

## 2026-10-15 追加：赛事分级 + 关键比赛过滤（用户："把一些不关键的比赛筛选过滤掉"）

```text
背景（用户原话）："这些比赛可能还要区分一下，把一些不关键的比赛筛选过滤掉"。
触发：形态分级体系做完后，用户意识到库里混着大量次级赛事，形态占比不代表关键比赛。

1) 新增分级口径（配置 + 判定 + 回归，三件套）
   - config/esports_tiers.json：三级规则（一级 / 二级 / 其他），按 league_raw 关键字匹配；
   - tools/esports_tier.py：tier_of(league_raw, game)，**判定顺序 其他 -> 一级 -> 二级**
     （必须先判"其他"：'Esports World Cup Open Qualifier' 含一级关键词
     'Esports World Cup'，顺序反了就把资格赛算成一级）；
   - tests/test_esports_tier.py：18 条映射 + 资格赛不得升级 两条用例锁定。

2) 实测发现（这是本轮最重要的结论）
   - LoL 316 场里**只有 40 场（13%）是一级赛事**（LCK/LPL/LEC/LCP/LCS/KeSPA/德杯/国际赛）；
     其余 245 场二级（EMEA Masters 居首、VCS/CBLOL/区域联赛/LCK CL）+ 31 场资格赛/升降级赛。
   - CS2 65 场里 58 场（89%）是一级——因为 CS2 回填时只接了
     ESL Pro League / IEM / BLAST / EWC / Thunderpick。
   - **只算一级赛事时**：LoL 整局 40 例 → 可用形态 0 种（最厚的 A3 仅 17 例）；
     LoL 逐局 126 例 → 可用 3（C2 59 / A2 40 / A3 21）；
     CS2 整局 58 例 → 可用 2（A3 30 / 热门 24）；CS2 逐局 → 可用 3（C2 50 / A2 35 / A3 25）。
   ⇒ 此前所有"形态占比"主体是次级赛事形状，不能直接套到 LCK/LPL/LEC；
     LoL 侧必须先补一级赛事样本（这正是"最近几个大联赛没接"的直接后果）。

3) 页面出口（数字全部由数据生成，不手写）
   - reports/pattern_taxonomy.html 新增第零节：分级表（场次/占比）+ 一级明细 +
     "零·二 只算一级赛事时的四个主格"（cell_table 支持独立样本源，
     一级视图下"要扩多少倍"改成如实提示缺口，不再套 20 倍算式算荒诞数字）；
   - reports/pattern_playbook.html 一览表新增「一级（关键）」列（高亮），
     每张形态卡的统计行末尾附"其中一级赛事 N 例"；
   - reports/pattern_shapes_index.html 口径节新增"赛事分级"条目 + 补 favicon；
   - 修复：分级表最初按**赛事名去重计数**（LoL 显示 7/33/10）而非按场次（应为 40/245/31），
     已改为按场次统计；一级过滤视图的"样本 0 例"是样本量取自全量源，已改为独立样本源。

4) 新增工具：tools/build_pattern_playbook.py（形态速查页，交易决策用）
   每个形态 = 示意线条（canonical SVG）+ 真实样本曲线（库里最接近中位的那一场）+
   线条特征 / 机器判定 / 买点 / 卖点 / 失效反例 + 实测统计（n、起点/低点/穿越50c/到99.5c 中位、
   低点买入到结算倍数）；负方侧 B 类单独统计并按"风控视角"呈现（B 类只活在负方侧，
   与胜方侧混算会全是 0）。页面顶部有幸存者偏差警示（标签按事后赢家侧标注，≠胜率）。

5) 回归：tests/ 147 passed / 3 failed（3 个为既存站点产物问题，与本轮无关）+
   新增 tests/test_esports_tier.py 2 passed。

待办（仍需用户拍板）：① 一级赛事样本补采排期（LoL 整局缺口最大）；
② 56 场资格赛是否入统计（分级口径已可判定为"其他"，随时可并入或排除）。
```

## 2026-10-15 追加：库口径收紧为"只收一级" + 回补 72 场一级样本

```text
背景（用户原话）："emea 和小区域联赛的数据不要了"。

1) 口径落地：形态库只统计一级（关键）赛事
   - 剔除：LoL −276 场（二级 245 + 资格赛/升降级 31）、CS2 −7 场；
   - 原始快照仍留 docs/data/snapshots（不可再生的分钟级数据不删），
     旧全分级明细 JSON 留在 reports/ 作存档、不参与出数；
   - 分级判定修一处误判：Thunderpick 洲际系列赛（European/South American Series #N）
     是资格赛路径，此前被"Thunderpick World Championship"关键词误判成一级 ->
     config 的"其他"档补 Series # / European Series / South American Series 等，
     并补回归用例（tests/test_esports_tier.py 现 3 passed）。

2) 顺带回补 72 场一级样本（这是本轮最大的实际收益）
   扫全部 gamma 索引发现 72 场一级比赛有快照但从未入形态库：
   KeSPA Cup 25 / MSI 14 / LEC 常规赛 14 / LCS 常规赛 8 / LCP 小组赛 7 / CS2 BLAST Bounty 4。
   合并索引（index_tier1_merged_2026-10-15.json）+ 显式 slug 清单重建：
     reports/pattern_shapes_lol_tier1_2026-07_2026-10.json —— 108 场（整局 108 / 逐局 40）
     reports/pattern_shapes_cs2_tier1_2026-07_2026-10.json ——  62 场（整局 62 / 逐局 56）
   ⇒ LoL 整局一级样本 40 -> 107，可用形态 0 种 -> 4 种（A3 46 / 热门 35 / A4 28 / A2 27）；
     CS2 逐局可用 3 种（C2 50 / A2 35 / A3 25）。

3) 工具改动（默认值变化，均带开关可回退）
   - build_pattern_taxonomy_page.py：新增 --tiers（默认"一级"，"all"=全分级混算）
     + --archive（读旧全分级 JSON，用于显示"已剔除多少场"）；非混算模式下省略重复的对照节；
   - build_pattern_playbook.py / build_pattern_index.py / build_pattern_granularity_page.py：
     输入切到 tier1 库；修正粒度页写死的"381 场"（改为按数据生成）；
   - 页面互链全部改指 tier1 曲线图/速查页，已校验无死链。
   - 产物：pattern_charts_lol_tier1（108 场 / 234 图）、pattern_charts_cs2_tier1（62 场 / 177 图）。

4) 校验：tests/ 149 passed / 3 failed（3 个为既存站点产物问题，与本轮无关）。

缺口（下一步）：① 7-8 月与 MSI/KeSPA 那批快照只有整场序列，逐局要联网回补
（index_game_markets + fetch_game_market_series）；② LCK 在本区间只有 2 场；
③ 一级样本 170 场，要让每种形态都 ≥20 例仍需继续累积。
```

### 2026-10-15（续）赛事分级口径修正 + 8 月窗口回补 + 逐局回补

```text
背景：用户确认"EMEA 和小区域联赛的数据不要了"（库口径 = 只收一级）。
收尾时发现上一轮重建有一个**覆盖级错误**：8/5–9/9 这段本地快照没有赛事标题索引
（league_raw 在 7 月与 9-10 月有、8 月整段缺失），该窗口整批被判"其他"挡在库外——
用户实际交易的 8 月 LCK/LPL 常规赛（T1-GEN 08-16、DK-HLE 08-20、BRO-FOX 08-21…）一场都没进库。
另发现分级关键词只写了 LCK/LPL 的 Playoffs/Regular，而 2026 赛季真实命名是
'LCK Round 3-4 Legend/Rise Group'、'LCK Play-In'、'LPL Group Ascend/Nirvana'、
'LCP Swiss Stage'、LoL 侧 'Esports World Cup Group X' —— 全被判成"其他"。

1) 分级规则修正（config/esports_tiers.json + tools/esports_tier.py）
   - 一级补：LCK Round / LCK Play-In / LPL Group / LCP Swiss / EWC / Esports World Cup；
   - 其他档去掉过宽的 'Play-In'（LCK、MSI 的 Play-In 是一级赛程阶段；
     TCL、LCK CL 的 Play-In 由二级关键词接住）；
   - 回归用例补齐（tests/test_esports_tier.py 现 12 条 CASE + 自检 23 例）。

2) 8/5–9/9 窗口回补（联网 gamma）
   - 137 场快照补赛事标题 -> runtime/pm_backfill/titles_gap_2026-08-05_2026-09-09.json；
   - 合并全量 league_raw -> runtime/pm_backfill/league_raw_v2_2026-10-15.json；
   - 一级 slug 清单重算：LoL 108 -> 256（本地全部有快照）/ CS2 62；
     重建后可入库：LoL 231 场、CS2 62 场。

3) 逐局回补（联网 CLOB）
   - 索引缺逐局的 137 场 Game N Winner 市场（371 条，其中逐局 234 条）；
   - 分 4 片抓 600s 序列：ok=234 / fail=0
     （当时判断“赛后 >24h，1 分钟级已永久关闭”；该判断已于 2026-10-18 推翻，
     见本文件末尾“分钟级可回溯”一节）；
   - LoL 逐局从 94 场 -> 194 场（493 个小局样本）。

4) 重建后的库与页面
   LoL 一级 231 场：整局 225 例（可用 5 种）/ 逐局 493 例（可用 5 种）
   CS2 一级  62 场：整局  62 例（可用 2 种）/ 逐局 115 例（可用 3 种）
   联赛分布：LPL 50 / 国际赛 43 / LEC 33 / LCK 31 / KeSPA Cup 26 / 德杯 19 / LCS 17 / LCP 12
   页面：taxonomy（新增 --tier-map 全量剔除量：LoL −557 / CS2 −1965）、playbook、
        charts_lol_tier1（231 场 / 722 图）、charts_cs2_tier1、index、granularity，
        全部只含一级；taxonomy/playbook 的写死数字改为按数据生成。

5) 工程侧顺带修掉 3 个既存红测试
   - match_index.json 重建（08-29 的旧索引 -> 10-15，133 -> 159 场；补 TEAMS-BB-PV 同场并表）；
   - intel_gray_verification_stats.html 生成器补 favicon（站点相对路径 / reports 用 data URI）；
   - 站点 nav/面包屑/padding 注入链路随重建重跑。
   ⇒ tests/ 153 passed / 0 failed（此前 3 failed）。

关键教训（已写进 AGENTS 规则 28f/28g）：
   ① 一级关键词必须覆盖赛季真实命名，改规则必须补回归用例；
   ② 区间 league_raw 覆盖率要先自查——"本地有快照"不等于"能进库"，
      缺标题索引的窗口会整批静默漏收。

缺口（下一步）：① 37 场无逐局数据（Polymarket 未开逐局盘）；
② CS2 一级只有 62 场，要和 LoL 同权需扩 3-5 倍；
③ 60s 分钟级 LoL 逐局 87 / 整局 34，仍需常态归档。
```

### 2026-10-18 分钟级可回溯修正 + 形态库平滑 + 外部数据源调查

```text
背景：用户要求（a）增加真实 1 分钟数据、（b）形态曲线更平滑、（c）调查除
Polymarket 外是否有更好的分钟级赔率源。

1) 结论修正（最重要）
   - 2026-10-15 的“分钟级只能赛后 24 小时内归档、过期不可回溯”是**误判**。
     根因：旧工具固定传 `interval=1d`，请求进入服务端聚合路径。
   - 正确请求：`/prices-history?market=<TOKEN>&startTs=..&endTs=..&fidelity=1`
     **不传 interval**。实测 2026-08-16 老比赛：
       12h 625 点/侧、24h 1345 点、7 天 9981 点，中位间隔全部 60s；
       60s 与 600s 在 63 个重叠时间戳上最大价差 0.0000。
   - LoL / CS2 / Dota2 均已实测可回溯；AGENTS 规则 26 已同步改写。

2) 回填结果
   - 一级 LoL 231/231 场、CS2 62/62 场全部为真实 60s；
     世界赛入围赛 4 场也完成回填。
   - 297 个事件 / 1,914 个 `.hires.jsonl` / 1,183,045 点，中位采样间隔 60s。
   - 工具：tools/backfill_minute_snapshots.py（只写 .hires，不覆盖原 600s）；
     fetch_price_snapshot.py / fetch_game_market_series.py 改为优先不传 interval。

3) 曲线平滑（不伪造数据）
   - tools/path_series.py 分三层：raw（原始观测）/ filled（仅补 ≤3 倍中位间隔
     的小缺口）/ display（3 点中值 + EMA，仅用于画图）。
   - 600s 路径不做分钟级插值，保持原始折线并标低置信度；
     形态分类与统计只用 raw；图下标“原始点数 / 插值比例 / 置信度”。

4) 外部数据源（详见 knowledge/ODDS_DATA_SOURCES.md）
   - 主源仍是 Polymarket：覆盖最好、可交易、60s 可回溯。
   - Kalshi 有官方 1 分钟 K 线，但电竞盘极薄（单市场几十张）；
   - The Odds API 历史快照为 5 分钟；Betfair/Abios/Bayes 为付费或合同制；
   - 公开全历史数据集：HF `SII-WANGZJ/Polymarket_data`（12.7 亿笔成交，约 280GB）、
     `TrevorJS/kalshi-trades`（1.545 亿笔）。

5) 验证
   - 新增 tests/test_path_series.py、tests/test_fetch_price_history.py；
     更新 tests/test_pattern_granularity.py 的旧口径说明。
   - 页面：pattern_shapes_index / granularity / taxonomy / playbook / charts 全量重建。

6) 用户盘感假设库（knowledge/PATTERN_HYPOTHESES.md）
   - H1 强打弱 BO3 输 G2 后买强队：n=13，命中 8（62%），均价 0.685，EV −0.12，
     初步不支持无脑抄底；G2 后守住 50c 的 7 场全赢、跌破 50c 的 6 场仅 1 胜。
   - H2 G1 碾压后的后续小局：n=13，系列赛 13/13 赢，但干净横扫仅 10/13；
     G2 单局 12/13（均价 0.812，EV +0.15）——只支持“G2”，不支持“必 3:0”。
   - H3 BO5 G3/G4 弱队深水抄底：≤0.20 共 42 场、命中 12%、按 0.20 成交 EV −0.41；
     仅 G3 前 1-1 且 ≤0.10（17 场、命中 17.6%、EV@0.10 +0.77）有正期望迹象，
     0-2 落后时（24 场、8.3%）是陷阱。
   - H4 整场基本盘 + 小局极值卫星仓：盲买 0.01 阈值 308 个小局、命中 1.0%、
     EV −0.03；0.05 阈值 473 个、命中 3.6%、EV −0.28；反弹到 0.10 卖出 EV −0.68。
     追加“等确认反转”（≤0.05 后重新站上确认位才买，剔除结算跳价）：
     0.20 档 n=34、命中 44.1%、实际价 EV +0.60（95% 区间 −0.02~+1.25）；
     0.30 档 n=25、命中 52.0%、EV +0.29（−0.20~+0.80）；0.50 档 n=16、
     EV −0.01（太晚）。473 个极值里只有 34 个（7.2%）给出 0.20 确认，
     策略常态是不出手。所有档位 EV 区间跨零，只能算方向性迹象。
     稳健性：要求触价前曾站上 0.20（真崩塌而非一直便宜），0.30 档 n=21、
     命中 57.1%、EV +0.43（95% 区间 −0.11~+0.97），方向一致但样本更小。
     结论：极值本身不是 edge，“反转确认 + 本场上下文”才可能是；盲买不升级，
     只把 0.30 确认列为 L0 观察候选，卫星仓 1–2%、不补仓、待样本外验证。
   - 页面 reports/pattern_hypotheses.html；生成器 tools/build_pattern_hypotheses.py；
     回归 tests/test_pattern_hypotheses.py。全部 L0 观察，不自动执行。
```

### 2026-10-22 形态决策台 V1 上线

```text
目的：把“赛后看形态”升级成随时可打开的只读决策页面：当前观察点 -> 同游戏/同层级近邻样本
-> Top 3 候选形态 -> 条件方向 -> 买入区 -> 分批止盈 -> 失效位。

交付：
- 生成器 tools/build_pattern_decision_site.py；模板 pattern_decision_workspace.template.html；
- 本地页 reports/pattern_decision_workspace.html；
- 公网页 http://158.247.214.175/intel/pattern_decision_workspace.html（VPS nginx，已验证 200）；
- 页面可筛选 LoL / CS2 / Dota2、比赛、整场/逐局，并拖动历史观察点回放；
- 候选卡显示相似权重、去重比赛数、观察点数、方向率、买入区、两档止盈、触达率、失效位；
- 方向率按比赛去重并使用 Beta(2,2) 平滑；少于 8 场显示“样本不足”；
- 买入区最多约 10c，并区分现价附近/回踩区/等待回踩；行情超 15 分钟标“数据陈旧”。

当前数据：12,852 个训练观察点 / 297 场去重训练比赛 / 318 个历史可回放盘面。
验证：tests/test_pattern_decision_site.py 通过；本地和公网页面均完成浏览器渲染检查。

边界与缺口：
- 只读分析，不接自动下单，不主动平仓；
- V1.1 已接入 VPS 云端实时刷新（每 5 分钟）：Gamma 扫描正式 Winner 市场，CLOB 取
  1 分钟线，与预训练数据集合并后原子发布；失败不覆盖旧页；
- 候选有效性尚未完成严格时间切分回测，页面所有概率均为历史条件统计，不是胜率承诺；
- 下一步：接入扫描器实时快照、滚动 backtest（Brier/方向命中/区间触达/扣滑点期望）。
```

### 2026-10-22 形态决策台 V1.2：未来赛程 + Stake 交叉源

```text
目标：让页面不只显示当前一两场，而是提前看到未来赛程，并把 Stake 的传统市场赛前定价
作为独立参考源接入；Polymarket 仍是分钟级形态、可成交价格和买卖点的主源。

交付：
- Polymarket 扫描窗口改读 config/market_watchlist.json 的 time_window；
- 远端未来场次使用 Gamma 赛前快照，临近 90 分钟或已开赛才请求 CLOB 分钟历史；
- 新增“未来赛程”横向卡片：默认覆盖 3 天，显示北京时间、游戏、赛事、对阵、赛制、Stake 十进制赔率、去水概率；
- 赛程卡标记“PM 已接入 / PM 待开盘”，已接入场次可直达形态盘面；
- Stake live 盘暂停时只记“盘口暂停/缺口”，不沿用旧赔率、不把 0 当价格；
- Stake 与 Polymarket 两套价格语义严格分开展示。
- 候选图恢复历史复盘式双线结构：观察方粗蓝实线、对手方浅橙细线、带文字的 50:50 灰色中枢虚线；候选延续降为底层彩色虚线，确保不盖住真实路径；
- 三张候选卡缩略图同步保留双方路径、50c 中枢与候选延续，切换观察方时图例和线色同步更新。

真实验收（2026-10-22 11:00 CST）：
- Gamma 扫描 634 个电竞事件 / 456 个正式对阵盘；
- 两天窗口识别 9 场 Polymarket 赛前盘、13 个市场；
- Stake 读取 18 个赛事目录、9 场有效未来对阵，9 场均有独赢赔率；
- 9 场全部与 Polymarket 对齐，行情错误 0，Stake 错误 0；
- 回归测试 tests/test_pattern_decision_live.py + page/site + scan 共 58 项通过；已用 CS2 Aurora Gaming vs Vitality 历史 1 分钟盘面完成浏览器双线与候选卡渲染验证。

边界：Stake 没有已验证历史序列与推送，live 常整盘暂停；当前只作赛前共识参考，
不接入自动下单，不替代 Polymarket 1 分钟形态主数据。
```

### 2026-10-22 任务 8 立项：形态结构重审与决策重构

```text
状态：进行中 · P0 现状审计完成
目标：先重新定义“什么形态算同一种”，再重建分钟级样本、重做图形与决策回测；
      不继续在旧启发式标签上叠加候选解释层。

审计结论：
- 当前并非缺少 1 分钟数据：可回放 1,042 个盘面中 993 个为 1 分钟级；
- 候选未来路径 MAX_FUTURE_POINTS=9，12,852 个训练点中 12,099 个（94.1%）未来仅有 9 点；
- 主图 MAX_PUBLIC_POINTS=72；Aurora Gaming vs Vitality 整场原始一侧 174 点，页面仅展示 72 点；
- 历史观察点仅用 7 个固定进度检查点，不是分钟滑窗；
- 现有分类器基于整段低点/高点/终点做启发式标签，primary_label 折叠多标签，候选主标签高度集中，
  A5/A6/C1/B3 等结构难以呈现。

下一步：完成 P1 形态字典 V2 第一版，优先复核 B4/A3/A2/C2/A1/B1 六类，
补齐结构骨架、正反例、失效边界和最小样本门槛。
首批审阅页：reports/pattern_structure_audit_2026-10-22.html（LoL 233 场 / CS2 64 场，
6 类形态共 1,770 个命中侧）；已发现 B4 定义“全程未站上 50c”与实际“高位先到 75c 后回落归零”
案例不一致，进入分类描述与识别条件同步修订。
交付文档：docs/task/PATTERN_STRUCTURE_REWORK.md
```

### 2026-10-22 形态决策台 V1.3：接入新版形态规范

```text
状态：已上线
目标：把新版形态审计中的中文命名、市场层级和观察边界搬进已有形态决策台，不另建重复页面。

交付：
- 新增 tools/pattern_display.py，统一形态中文展示名、结构族和层级文案；
- 决策台候选卡、KPI、结构解释全部使用纯中文形态名，界面不再显示内部标签代码；
- 状态栏明确区分“小局预测 / 整场预测”，候选卡可直达新版形态审计页对应案例；
- 保留观察方粗蓝线、对手方浅橙线、50c 中线和候选延续；
- 顶部统一标注“P1 观察版”，相似度与方向率不再被描述为已验证胜率；
- 历史回放、当前盘面和未来 Stake 赛程继续在同一页面切换查看。

验收：
- tests/test_pattern_decision_site.py、tests/test_pattern_decision_live.py、
  tests/test_pattern_structure_audit.py 共 24 项通过；
- 本地全页与公网页面均完成浏览器视觉核验；
- 公网 16 场未来赛程、中文候选卡和历史案例链接均可见；
- pattern-decision-live.service 手动触发成功，仍由 timer 每 5 分钟自动刷新。

边界：当前仍是 P1 观察版；P2 分钟滑窗样本、P3 候选区间带和 P4 时间切分回测完成前，
不把候选卡当作可执行概率或自动下单依据。
```

### 2026-10-23 形态决策台 V1.4：候选真实分钟路径与断轴证据图

```text
状态：已实现，待发布验收
目标：解决候选形态摘要点过少、图上看不出方向和买卖位的问题；不再用人造平滑线替代真实路径。

交付：
- 候选区改为“候选切换 + 证据大图 + 决策侧栏 + 横向比较表”；
- 左段显示已发生的双方真实赔率走势，右段展开观察后的历史剩余时间，避免 80%+ 观察点只剩窄条；
- 候选大图同时显示历史中位路径、25%–75% 区间、3–5 条真实历史分钟案例、50c 中线、买入带、两档止盈和失效线；
- 训练记录新增真实盘面引用、局号、观察进度和价格粒度；浏览器直接回读历史盘面分钟路径；
- 主图单侧路径保留上限从 72 点提升到 240 点；
- 训练近邻池强制按游戏、小局/整场、粒度隔离，1 分钟与 10 分钟不混算；
- 12,852 条训练记录全部可回连真实盘面，相关回归 53 项通过。

边界：仍是 P1 观察版；真实路径增加可读性，不等于完成 P2 分钟滑窗、结构多标签和 P4 时间切分回测。
```

### 2026-10-23 形态决策台 V1.5：完整平滑曲线 + 赛前先验修复

```text
状态：已上线并完成赛前/历史双路径验收
目标：去掉候选形态的粗泛摘要感，并修复赛前盘面被粒度过滤成 0 场的问题。

交付：
- 候选历史中位路径提升到最多 180 个插值步点；代表性案例直接回读真实盘面分钟路径；
- 双方真实路径、历史中位与代表性路径统一采用 Catmull-Rom 平滑连接，不删原始点、不改点值；
- 候选大图 viewBox 调整为 920×500，1360px 以下把决策栏移到图下方，1280px 笔记本可见面积更大；
- 赛前单点快照的当前行情仍标记“数据不足”，但历史先验单独匹配 1 分钟层，页面显示“历史 1 分钟级先验”；
- 数据体检拆分“当前行情粒度”和“历史匹配粒度”，避免混淆事实层。

验收：
- tests/test_pattern_decision_site.py、test_pattern_decision_live.py、
  test_pattern_structure_audit.py、test_scan_regression.py 共 55 项通过；
- 赛前单点夹具实际渲染出 3 个候选、双方路径、买入区、两档止盈和失效位；
- 回归锁定平滑函数、180 步分布、桌面断点与赛前先验回退逻辑。

边界：P1 观察版；平滑只改善阅读，不是概率校准，也不改变原始分钟数据。
```

### 2026-10-23 形态决策台 V1.5.1：候选终结坐标修正

```text
状态：已上线并完成本地、云端验收
问题：候选图末端多条线看起来都接近 100c，像是双方价格同时到 100c。

根因：
- 训练记录保存的是被采样队伍自己的价格路径；
- 当前观察点也按所选观察方计算，近邻记录已经是同侧类比；
- 旧实现又按候选方向做了一次反转，导致看空候选被画到错误坐标，多个方向叠图后视觉上都靠近 100c；
- 原始行情并非双方同时到 100c：当前 1,042 组双方终点中，双方同时 >=99c 为 0 组。

修复：
- 候选历史中位与代表性路径统一使用匹配记录的同侧价格坐标，不再按候选方向/队名二次反转；
- 看多候选终结约 100c，看空候选终结约 0c；
- 图例、断轴图标题与图下说明明确“观察方价格坐标”，并提示不是双方同时到 100c；
- 新增回归测试锁定 futureDistribution(g.records,false) 与 representativePaths(g.records,false,5)。
- 修复本地预览与云端发布目录缺少关联页面、相对链接 404 的问题；顶部直接提供新版形态审计、形态总库、形态速查、形态分类、分类图表、粒度对照与频率排行入口；
- “力度分析”暂无独立同名页面，现有相关内容分散于形态审计、形态速查和频率排行，暂不伪造独立入口。

验收：
- pattern_decision_site / pattern_decision_live / pattern_structure_audit / scan_regression 共 57 项通过；
- 本地静态页和 reports/pattern_decision_workspace.html 已重建；
- 公网页面已确认加载修正代码；
- 公网发布目录已同步 20 个 pattern 页面，17 个页面逐一返回 HTTP 200；
- VPS pattern-decision-live.service 手工运行成功，Result=success、ExecMainStatus=0；
- timer 继续每 5 分钟刷新后台数据；浏览器页面目前仍需重新加载后才显示最新计算，后续可按需增加进行中盘面的低频自动刷新。

边界：P1 观察版；候选形态会随新增分钟价格重算，但当前输出仍不是胜率或自动下单信号。
```

### 2026-10-23 政治选举叙事幻觉雷达 v1：180+ 活跃事件

```text
状态：第一版已生成，进入事件覆盖与结构校验阶段
用户校正：民调不作为核心信号，页面改为“市场叙事是否被误认成事实”的只读雷达。

交付：
- reports/intel_elections_hallucination_2026-10-23.html；
- 当前扫描 182 个活跃 Polymarket 事件：
  众议院选区 54、联邦参议院（含县级切片）47、州长 28、
  海外选举 27、州检察长 12、州务卿 7、州参议院 6、联邦众议院控制权 1；
- 页面包含高信念 × 薄盘口散点图、翻盘窗口队列、州议会席位门槛、
  10 个核心叙事卡、8 个重划/退休风险众议院席、可筛选全事件雷达、美国州级地图；
- 数据快照：docs/data/elections/election_hallucination_snapshot_2026-10-23.json；
- 配置：config/election_hallucination_2026.json；
- 生成器：tools/build_election_hallucination.py；探针：tools/probe_election_markets.py；
- 方法文档：docs/task/ELECTION_INTELLIGENCE_WATCH.md；
- 官方日期与制度事实底稿：docs/task/ELECTION_WATCH_EVIDENCE_2026-10-23.md
  （其中民调部分仅保留为历史背景，不参与当前评分）。

方法：
- 幻觉压力 = 信念强度 + 薄盘口 + 多档报价不自洽 + 叙事热度；
- 翻盘窗口 = 幻觉压力 × 距离 100c 的空间 × 信念修正；
- 两者均为启发式排序，不是胜率、收益率或实盘信号；
- 多档 YES 只在同一事件的有效互斥范围内合计，县/投票率等不强行归一。

结构校验：
- 2026 州议会：88 chamber / 46 州 / 6,064 个州议席改选；
- 当前 chamber control：R 57 / D 39 / coalition 2；
- 关键州参议院席位门槛与改选比例已写入页面；
- AL-02、FL-09、CA-06、CA-48、NE-02、IA-02、AZ-01、MI-10
  已标注重划/退休导致“历史高胜幅不可继承”的案例。

验收：
- `pytest -q tests/test_election_hallucination.py tests/test_scan_regression.py`
  共 30 项通过；
- `--refresh` 成功扫描 182 个活跃事件、errors=0；
- `--offline` 可逐字节重建同一页面；
- 页面在桌面与移动端完成视觉检查。

下一步：
1. 增加 CLOB 订单簿深度与近 24h 主动成交方向，替代单看 liquidity 字段；
2. 为更多州级 chamber 和县级切片建立正式的事件分组，避免把不同县的二选一市场混算；
3. 做每日快照差异，观察“薄叙事高价格是否向厚盘收敛”；
4. 只读观察，不接入自动下单。
```

### 2026-10-24 选举全景清单 + 现任席位 + 操纵假设监察

```text
状态：已生成，第一版可直接使用

新增：
- reports/intel_elections_events_2026-10-24.html：
  182 个活跃事件的全景表，直接显示成交量/流动性、市场正反比例、
  当前席位党派、认知状态、翻盘窗口与幻觉压力；
- reports/intel_elections_hallucination_2026-10-24.html：
  分析页同步加入全部事件清单入口和“操纵假设监察”板块；
- 众议院 54 个选区委已补齐当前众议员党派；
- 参议院席位、州长、州检察长、州务卿、州参议院 chamber 当前控制均已映射；
- 用户提出的“贿赂官员/操纵中期选举”明确标为待证假设，
  不写成事实，并列出官方调查/起诉、资金证据、法院文件、计票审计、
  多源独立报道五类硬证据门槛。

验证：
- 182 个事件，无抓取错误；
- 所有分类的 current-control 映射无缺口；
- tests/test_election_hallucination.py + test_scan_regression.py 共 31 项通过；
- --offline 可重建分析页与清单页。

边界：
- “市场正反比例”是有效 YES 聚合或前两名；报价不自洽时可以超过 100%；
- 当前席位是现任者/当前 chamber 控制，重划州可能不完全等同 2026 新边界；
- 翻盘窗口不是胜率；操纵假设没有证据前不升级为结论。
```

### 2026-10-24 Worlds Swiss R1 一分钟赔率复盘与历史形态入口恢复

```text
状态：已完成

交付：
- reports/intel_worlds_swiss_r1_odds_2026-10-24.html；
- knowledge/intel_pages/intel_worlds_swiss_r1_odds_2026-10-24.md；
- reports/pattern_shapes_lol_worlds_r1_2026-10-24.json；
- docs/data/intel/price_paths.json 新增/替换 8 个 Worlds R1 market slug；
- tools/build_worlds_r1_odds_review.py（可重建页面、JSON、MD 与形态库）；
- patterns 旧地址 reports/pattern_decision_static_v14.html 兼容跳转到统一形态总库。

数据：
- Riot 官方 8 场全部 completed，Polymarket 结算与官方胜方一致；
- 全部为 BO1，每方 50–97 个真实 60 秒点；
- 窗口为市场 gameStartTime→closedTime；
- 胜方中位 U 型反转 4、折价修复 3、五五开开局后单向压制 1；
- BO1 无独立 G2/G3 市场，不伪造逐局曲线。

历史库：
- training_samples=12,852；training_matches=297；历史记录=318；
- price_paths 由 627 增至 635；
- pattern_library.html 与 pattern_decision_workspace.html 增加 Worlds R1 入口。

边界：公开价格点不等于完整可成交深度；形态是统计描述，不是自动下单信号。
```

### 2026-10-25 CS2 G2 vs Aurora 局中主仓 + 对冲观察

```text
状态：局中记录完成，待赛后回填

快照：2026-10-25 23:15 CST；Aurora 1–0，Map 2 进行中
- G2 整场 37c / Aurora 64c；
- G2 Map 2 72c / Aurora 29c；
- Under 2.5 31c（用户记录曾低至 4c，后回到约 30–31c）。

交易记录：
- 用户口述第一图期间买入 G2 35c；当前 37c 更接近整场 Moneyline，暂按整场记录，
  但仓位金额与“整场 / Map 1 Winner”归属待确认，不算实际盈亏。

结构判断：
- 主仓 G2 + Under 2.5 只覆盖“Aurora 赢 Map 2 并 2–0”分支；
- G2 赢 Map 2、但输 Map 3 时，主仓和 Under 同时归零，仍是裸风险；
- 页面显示互补价合计不等于 100c，不能用点击价直接宣称套利。

交付：
- reports/intel_trade_observation_CS2-G2-AUR1_live_2026-10-25.html
- knowledge/intel_pages/intel_trade_observation_CS2-G2-AUR1_live_2026-10-25.md
- runtime/intel/cs2-g2-aur1-2026-10-25.json

后续：确认持仓市场与 size；比赛结束后回填 G2/G3、整场形态和实际盈亏，
并将“主仓 + 对冲”纳入分支覆盖回测，禁止在任一终态亏损时标注 risk-free。
```

### 2026-10-24/25 Worlds R2 + PGL 布加勒斯特赔率复盘

```text
状态：已完成

范围：
- 已做过的 Worlds R1 跳过；本轮补齐 Worlds R2 八场 BO1。
- 新增 PGL Masters Bucharest 十二场 BO3，共 12 个整场 + 24 个已上市小局市场。
- 只使用比赛内窗口；请求 fidelity=1，双方 outcome token 分别抓取，不用 1-p 镜像。

交付：
- reports/intel_worlds_swiss_r2_odds_2026-10-25.html
  + knowledge/intel_pages/intel_worlds_swiss_r2_odds_2026-10-25.md
- reports/intel_cs2_pgl_bucharest_odds_2026-10-24_25.html
  + knowledge/intel_pages/intel_cs2_pgl_bucharest_odds_2026-10-24_25.md
- reports/pattern_shapes_lol_worlds_r2_2026-10-24.json
- reports/pattern_shapes_cs2_pgl_bucharest_2026-10-24_25.json
- tools/build_recent_odds_reviews_2026_10_24.py

库与入口：
- LoL 一级形态库新增 8 场，总数 241；CS2 一级形态库新增 12 场，总数 76；
- docs/data/intel/price_paths.json 由 635 增至 655 条；
- docs/data/intel/matches.json 新增 8 场 Worlds R2 + 12 场 PGL，合计 20 条终态记录；
- The MongolZ（MGLZ）已登记 team_names / teams，避免新赛事裸用别名；
- 重建 pattern_shapes_index / granularity / taxonomy / playbook / frequency /
  LoL+CS2 一级曲线、两个本批曲线页与 pattern_decision_workspace；
- intel_danmu_index.html、intel_pages/README.md、intel_danmu_index.md、
  DANMU_INTEL.md 已挂新页。

关键观察：
- LoL 三场整场下狗反转：TES-AL、DK-T1、LYON-KC；其余五场以热门折价修复、
  热门全程压制或五五开后单向确立为主。
- CS2 三场 G1 后让一追二：AUR-MGLZ、MOUZ-TL、TS-BB。整场赢家低点分别约
  12.5c / 3.5c / 7.5c，跨 50c 时间约 65 / 87.7 / 71 分钟。
- 三场打满 BO3 的比赛没有独立 G3 Winner 市场；页面显式标缺口，不用整场曲线冒充。

数据质量：
- 已修复 fetch_event_market_pack 对结算后异常尾点的逐市场裁切；原始价格图不以
  1-p 补线。G2-LOS 实际采样间隔为 mixed，其余中位间隔约 60 秒。

验证：
- pytest tests/test_recent_odds_reviews_2026_10_24.py tests/test_path_series.py
  tests/test_pattern_granularity.py tests/test_scan_regression.py -> 40 passed；
- pytest tests/test_pattern_decision_site.py tests/test_worlds_r1_odds_review.py
  -> 11 passed；
- price_paths 655 条 slug 唯一；matches 新增记录 20 条 id 唯一；新增 20 场均在
  对应一级形态库中。

边界：形态仍为历史归纳；“让一追二深水反转”只作观察样本，不升级自动下单信号。
```

### 2026-10-26 政治选举雷达：低量过滤 + 州议会简化 + 四字段清单

```text
状态：已更新，当前版本可直接使用

用户修正：
- 州议会章节过于抽象，需要改成“现在谁控制、差几席、本轮改选几席”的人话；
- 几百到几千美元成交的单区盘没有参考价值，应从排名和赔率分析中移除。

执行：
- 新增质量门槛：成交量 ≥ $50k 且流动性 ≥ $20k；
- 当前原始扫描 184 个事件，58 个进入可参考层，126 个低量事件仅留原始快照；
- 主分析页、散点图、翻盘队列、州地图和明细表均只用可参考事件；
- CA-06、AL-02、FL-09 等低量众议院 margin 盘不再进入赔率卡片或排名；
- 众议院重划/退休只保留“结构事实”，不展示低量概率；
- 州议会改用“现在归属 / 多席过半 / 翻盘需净增几席 / 本轮改选几席”表达；
- 每个可参考事件新增：成交量/流动性、市场正反比例、当前席位、认知状态。

交付：
- reports/intel_elections_hallucination_2026-10-26.html；
- reports/intel_elections_events_2026-10-26.html；
- docs/data/elections/election_hallucination_snapshot_2026-10-26.json；
- tools/build_election_hallucination.py 同步生成分析页与可参考事件清单。

验证：
- 184 个原始事件，errors=0；
- 58 个可参考事件的 current-control 映射无缺口；
- pytest tests/test_election_hallucination.py tests/test_scan_regression.py
  共 33 项通过；
- 离线重建两份页面一致。

边界：
- 被剔除事件仍完整保存在 snapshot，可在后续提高成交量后重新进入；
- “当前席位”是当前议员/当前 chamber 控制；重划州的新旧选区边界可能不完全同域；
- 州议会市场全部因低于质量门槛而不参与价格判断，只保留制度结构。
```

### 2026-10-27 政治选举雷达：众议院重划选区账本

```text
状态：已更新，当前版本可直接使用

用户补充：
- 用户提供 BBC 2025-11-04 报道，指出特朗普阵营通过重划选区改变共和党
  众议院路径；
- 要求把“哪些调整对特朗普有利”作为独立分析维度，而不是背景注释。

执行：
- 新增 redistricting_watch 配置，按“已用于 2026 / 2026 被挡下 /
  未改变”拆分 18 个相关州；
- 2026 已生效 9 州：得州、佛州、俄亥俄、北卡、阿拉巴马、路易斯安那、
  田纳西偏 R；加州、犹他偏 D；
- 页面明确列出各州法庭/公投状态，不把被挡地图算进 2026 席位账本；
- 使用当前众议院 R 218 / D 214 / I 1，说明民主党仍需净增 4 席；
- 单列州级目标账：已生效地图直接相加为 R +15 / D +6，净共和党 +9 席，
  并明确它不是九席已经翻转；
- 列出重点目标选区：TX-09/28/32/34/35、CA-01/03/22/41/48、
  OH-01/09、NC-01、TN-09、LA-06、AL-02、FL-09/14/22/25、UT-01；
- 新增“这些选区现在能买什么”表：逐区显示结构受益党、对应市场、
  成交/流动性、当前报价、执行建议和条件买入方向；
- 当前 21 个目标选区没有一个单区盘同时达到 $50k 成交/$20k 流动性；
  TX-34 只可观察 R 方向，AL-02 报价裂解禁止交易，其余多数无盘；
- 唯一达标表达为众议院控制权：仅把 Republican Party — Yes 作为
  小仓逆向仓，不把当前 8.5% 写成高概率结论；
- 汇总口径区分“地图目标优势”与“实际胜选”，并标注 12 个席位更稳固偏 R、
  1 个更偏 D、13 个竞争席消失；该席位分类账与州级净 +9 不重复相加；
- 页面把 BBC 报道定位为 2025-11-04 的重划战起点，不把当时的估计当作
  2026-10 最终状态。

交付：
- reports/intel_elections_hallucination_2026-10-27.html；
- reports/intel_elections_events_2026-10-27.html；
- config/election_hallucination_2026.json 的 redistricting_watch；
- tools/build_election_hallucination.py 的重划账本渲染；
- docs/task/ELECTION_INTELLIGENCE_WATCH.md 方法同步。

验证：
- pytest tests/test_election_hallucination.py -> 14 项通过；
- Python 编译与 JSON 解析通过；
- 页面桌面与 390px 宽移动端可视检查通过；
- 市场数据仍使用 2026-10-26 快照；制度状态更新日期为 2026-10-26/27，
  不与实时行情混淆。

边界：
- 重划设计目标不等于已赢席位；
- 党派偏向不自动等于违法；
- 不把每张共和党方向州图都归因于特朗普个人；
- 地图优势可能被全国浪潮覆盖，不能单独当作守住众议院的结论。
```

### 2026-10-28 选举事件雷达：标记筛选、排序与重划关联

```text
状态：已完成，主分析页与完整事件清单同步

新增：
- 风险标记单选/取消：强信念 ≥80%、高信念 ≥85%、高换手 ≥5x、
  薄盘 <$50k、报价裂解、高信念·厚共识；
- 排序：翻盘窗口、幻觉压力、成交量、流动性、当前信念、换手率；
  支持升序/降序切换；
- 新增“重划关联”列：直接目标选区 / 聚合影响 / 另套地图 /
  无直接·仅间接 / 无直接影响 / 非目标选区 / 无关。

口径：
- 州长、州检察长、州务卿是全州选举，国会选区边界没有直接影响；
  只能通过资源、候选人、turnout、全国政治环境产生间接影响；
- 州参议院通常使用另一套州议会地图；
- 联邦参议院不由众议院选区制决定；
- 只有目标国会选区和全国众议院控制权属于直接/聚合重划链条。

验证：
- 主页面 58 行、完整清单 58 行；
- 高换手筛选后为 8 行，高信念筛选后为 32 行；
- 成交量升序排序实测通过；
- pytest tests/test_election_hallucination.py tests/test_scan_regression.py
  共 43 项通过。
```

### 2026-10-27 以色列：看守总理与组阁规则核对

```text
状态：已完成证据核对，待选举结果与正式组阁进程更新

核心：
- 新 Knesset 选出后，卸任政府继续履职，已辞职总理继续履行角色，直到新政府成立；
  看守延续不等于自动连任；
- 正式组阁路径：总统 7 天内授权、第一轮 28+14 天、第二轮 28 天、
  必要时 61 名议员指定授权 14 天，失败则 Knesset 视为解散并再次选举；
- 以色列全国比例代表制，没有美国式地理国会选区重划；
  最接近的制度工程是 3.25% 门槛、名单合并/拆分、剩余票协议与 61 席联盟算术；
- 本地 2026-10-26 市场：下一任总理 Eizenkot 50.25c / Netanyahu 26.5c；
  Yashar 最大党 69.0c / Likud 30.5c；市场不是最终概率，选举当日不据此定结果。

交付：
- docs/task/ISRAEL_CARETAKER_ANALYSIS_2026-10-27.md

边界：
- 《政府基本法》英文合并文本为非官方翻译，法律效力以希伯来文 Reshumot 为准；
- 当前未核到 2026-10-27 前存在触发基本法第 18 条的最终道德败坏判决；
- 看守角色、正式出任总理、监票争议是三种不同问题，禁止混写；
- 规则工程与原证实作弊严格分开。
```

### 2026-10-26 比赛日：CS2 + LoL 十场赔率复盘与幻觉审计

```text
状态：已完成并入库

范围：
- Worlds 2026 Swiss R3 八场 LoL；
- PGL Masters Bucharest 两场 CS2；
- 保留逐小局/逐图、整场、双方真实 token、低高点、终值、形态、缺口与溯源；
- 在原有赔率复盘维度上叠加事实 / 投影 / 叙事 / 剧本假设四层幻觉审计。

交付：
- reports/intel_daily_esports_hallucination_2026-10-26.html
  + knowledge/intel_pages/intel_daily_esports_hallucination_2026-10-26.md；
- docs/data/intel/daily_esports_2026_10_26.json；
- reports/pattern_shapes_lol_daily_2026-10-26.json/html；
- reports/pattern_shapes_cs2_pgl_2026-10-26.json/html；
- tools/build_daily_esports_hallucination_2026_10_26.py。

事实：
- CS2：FUT 2:1 Vitality、TYLOO 2:1 9z，均为 G1 后让一追二；
- LoL：IG、TES、DK、GEN、T1、BLG、LOS、TL 取胜；
- 两场高先验方 0:2 出局：TL 2:0 AL、LOS 2:0 TSW；
- AL 已由用户直接指认；第二场按“同为 0-2 BO3 强先验方直接出局”锁定 TSW–LOS。

灰信号：
- gray_signals 新增两条用户口述记录；
- gray_entities 更新 AL，并新增 TSW / TL / LOS；
- 全部状态为 pending / 仅留痕·非结论；
- 没有本场弹幕原文、VOD 逐回合、异常成交或官方调查，不升级为操纵结论。

形态库：
- LoL 一级形态库 241 -> 249；
- CS2 一级形态库 76 -> 78；
- docs/data/intel/price_paths.json 655 -> 665；
- matches 更新 10 场，全部 finished / settled；
- 两份 9z–TYLOO 报告均已从“图三进行中”修正为 TYLOO 2:1 已结算。

边界：
- 实力评分、地图胜率、外推赔率只作带误差投影；
- 两场 CS2 的 G3 无独立 Winner 市场，不用整场曲线伪造第三图；
- 价格路径与赛果不能单独证明假赛或赛前剧本。
```

### 2026-10-29 Worlds Swiss R4 一分钟赔率增量复盘

```text
状态：已完成并入库

范围：
- T1 2:0 Movistar KOI；
- Invictus Gaming 2:1 LYON；
- 双方真实 outcome token，约 60 秒比赛内路径；Riot 官方系列比分交叉校验。

关键观察：
- T1：85.5c → 低 75.5c → 98.5c；
- IG：66.5c → 低 56.5c → 99.5c；
- 两场胜方均为 A3 折价修复 / 热门全程压制，均未跌穿 50c；
- IG-LYON 打满 BO3，但整场价格从未翻到 LYON 一侧，证明“打满”不等于“领先权翻转”。

A3 子形态：
- 当前 Worlds R1-R4 整场赢家 26 场：A3 13 / A2 8 / A4 3 / C2 2；
- A3 n=13，低点范围 42.5-86.5c，中位 63.5c；
- 起点到低点中位回撤 10pp、最大 47pp；低点 <60c 为 5/13，<50c 为 2/13；
- 后续不能只用 A3 名称路由，必须拆回撤深度、低点时长、恢复速度与 50c 穿越。

交付：
- reports/intel_worlds_swiss_r4_odds_2026-10-29.html
  + knowledge/intel_pages/intel_worlds_swiss_r4_odds_2026-10-29.md；
- reports/pattern_shapes_lol_worlds_r4_2026-10-29.json/html；
- docs/data/snapshots/lol-mkoi-t1-2026-10-29/；
- docs/data/snapshots/lol-ig1-ly-2026-10-28/；
- tools/build_worlds_r4_odds_review.py；
- tools/pm_public_search.py；
- tools/fetch_official_game_data.py 补充官方系列比分输出；
- tools/pm_http.py 修复公共出口池为空时 fanout 除零。

入库与验证：
- price_paths 665 -> 667；
- LoL 一级形态库 249 -> 251；
- matches / match_index / 情报索引 / DANMU_INTEL 已同步；
- 重建 LoL 曲线、playbook、形态总览、粒度对照、频率榜；
- 21 项相关回归通过。

缺口：
- 两场均只有 Match Winner，无独立逐局 Winner 市场；
- 因此本轮只做整场形态，不生成 G1/G2/G3 价格路径；
- 下一批 CFO-KC、BLG-TES 待赛后补入；CS2 PGL 淘汰赛待赛果/赛程源可用后补入。
```

### 2026-11-03 美国选举日最新快照与延期剧本

```text
状态：已生成当日快照，选举结果尚未产生

最新核心赔率（Polymarket Gamma API，API updatedAt 2026-11-03T13:14:06Z）：
- 众议院控制权：D 94.5c / R 5.5c；成交 $43.42m、流动性 $12.16m；
  10/26 为 D 91.5c / R 8.5c；
- 参议院控制权：D 77.5c / R 22.5c；成交 $18.82m、流动性 $2.04m；
  10/26 为 D 64.5c / R 35.5c。

关键州重估：
- 得州参议院 D 63.5 -> 74.5；
- 俄亥俄参议院 D 66.5 -> 71.5；
- 缅因参议院 D 59.5 -> 72.5；
- 密歇根参议院 D 68.5 -> 80.5；
- 内华达州长 D 67.0 -> 76.5；
- 佐治亚州长 D 62.5 -> 70.5；
- 佛州州长 R 81.5 -> 64.5。

延期判断：
- 全国选举日改期：极低；2 U.S.C. §7 固定偶数年 11 月第一个星期一后的星期二，
  没有总统单方面推迟通道；
- 结果认证延后：仍可能出现，来自邮寄票统计、重新计票、诉讼和县认证争议；
- 局部站点/时段异常：低但非零，属于州/地方应急和司法处理；
- 本次查询未发现明确、高流动性的“2026 全国选举延期”市场；
  众参两院主市场仍以 2026-11-04 04:59 UTC 为结算截止。

交付：
- reports/intel_elections_latest_2026-11-03.html；
- docs/data/elections/election_current_snapshot_2026-11-03.json；
- tools/build_election_latest_2026_11_03.py；
- docs/task/ELECTION_DAY_UPDATE_2026-11-03.md；
- tests/test_election_latest_2026_11_03.py。

边界：
- 赔率不是官方结果或真实概率；
- 结果晚出 ≠ 投票日期被取消；
- 不把没有专门延期市场解释成绝对不可能，只表示未发现可交易的全国延期主线。
```

### 2026-11-03 形态决策台赛程发现、开赛判定与本地刷新修复

```text
状态：已修复并完成实时验证

现象：
- 本地形态决策台长时间未出现正在进行的 IEM Beijing 比赛；
- 开赛/结束节点和比赛数量在部分 CS2 场次上不稳定；
- 同一场 BO3 的前一图尚未结束时，后续图可能被提前标成“进行中”。

根因：
- 本地 reports/pattern_decision_workspace.html 最后生成于 2026-10-29，没有本地定时刷新；
- 实时刷新器只走 Polymarket 直连，遇到超时/TLS reset 会漏掉整轮候选；
- Liquipedia CS2 脚本把所有赛程都当成 CEST 再加 6 小时，IEM Beijing（CST）整体错后 6 小时；
- 比赛级 started 状态被错误套用到所有未关闭的子市场，导致未来小局被提前当作当前局。

修复：
- 新增 LaunchAgent com.ad.pattern-decision-live，每 10 分钟刷新本地页面；
- http_json 增加 tools/pm_http.py 公共只读代理兜底；
- 开赛时间优先 gameStartTime，缺失回退 eventStartTime，禁止回退 startDate；
- 扫描诊断新增 unregistered_league / missing_start / outside_window 计数及样例；
- 多个小局市场同时打开时，仅最低未结算局为当前局，后续小局保持赛前；
- Liquipedia 按 Abbr 时区转换，CST 不再被当作 CEST。

实时核验（2026-11-03 15:21 CST）：
- Gamma 开放电竞事件 597，match-shaped 429；
- 已登记联赛且落在两天窗口内 8 场，构建市场 27 个，行情错误 0；
- IEM Beijing 6 场：FaZe-Falcons、MOUZ-BetBoom 在盘；其余 4 场待开赛；
- FaZe G1 在盘时 G2 正确显示赛前待走势；MOUZ G1 已结束后当前局切换到 G2；
- 形态训练集仍为 329 场 / 13,587 个观察点，新增实时盘面只用于当前决策，不冒充已结算历史样本。
- 当日形态巡检写入 reports/pattern_audit_2026-11-03.md：11,894 条快照序列、3,647 个快照组；
  435 条未知序列与 40 组候选结构只进入待审队列，未满足验证门槛前不新增正式形态。

验证：
- tests/test_pattern_decision_live.py、tests/test_fetch_cs2_liquipedia.py、
  tests/test_pattern_decision_site.py、tests/test_pattern_structure_audit.py 共 36 项通过。
```

### 2026-11-08 LoL + CS2 最新赔率同步与双线形态图谱

```text
状态：已完成并入库

新增比赛：
- Worlds 淘汰赛 4 场：GEN 3:0 LYON、BLG 3:0 DK、
  T1 3:1 KC、GEN 3:0 IG；
- IEM Beijing 9 场；
- 共 13 场、45 个 Winner 市场、90 条双方真实 token 序列。

数据：
- 比赛内单侧分钟点 6,545，约 60 秒，未使用 1-p 镜像；
- LoL 由 Riot matchId、gameWins、逐局阵容交叉；
- CS2 使用 Polymarket Match/Map Winner 结算；
- Dota2 本窗口无已登记一级赛事，未混入 DreamLeague Division 2 /
  1win Play-in。

库更新：
- price_paths 704 -> 717；
- LoL 一级库 259 -> 263；CS2 一级库 101 -> 110；
- 统一训练 366 -> 379 场；观察点 15,405 -> 16,050。

形态与聚类：
- 正式形态 16 种，当前实际命中 14 种；B3/C1 仍为零样本；
- 5 个游戏×层级、16 个细分聚类组；
- 16 个细分簇聚合为 4 个高层结构族，降低阅读复杂度；
- 每张正式形态/聚类卡展示观察方+对手方两条真实价格线。

交付：
- reports/intel_lol_cs2_odds_2026_11_08.html
  + knowledge/intel_pages/intel_lol_cs2_odds_2026_11_08.md；
- reports/pattern_morphology_catalog_2026-11-08.html
  + knowledge/intel_pages/pattern_morphology_catalog_2026-11-08.md；
- reports/pattern_clusters_2026-11-08.json；
- docs/data/intel/lol_cs2_review_2026_11_08.json；
- tools/build_latest_lol_cs2_review_2026_11_08.py；
- tools/build_pattern_clusters_2026_11_08.py；
- tools/list_settled_esports.py。
```

### 2026-11-04 Worlds 淘汰赛与 IEM Beijing 一分钟赔率、形态库与聚类增量

```text
状态：已完成并入库

范围：
- IEM Beijing 11-03/04 已结算 5 场、15 个 Winner 市场；
  Team Falcons 2:0 Heroic、TheMongolz 2:1 FURIA、
  Natus Vincere 2:1 Team Falcons、BetBoom 2:1 Liquid、Liquid 2:0 TYLOO；
- Worlds Playoffs 已结算 1 场、5 个 Winner 市场：
  IG 3:1 TES（G1 IG / G2 TES / G3 IG / G4 IG，G5 unneeded）。

数据：
- 双方真实 outcome token，Polymarket CLOB prices-history fidelity=1；
- 比赛内约 60 秒；IEM 2,448 个、Worlds 905 个单侧分钟点；
- Worlds 由 Riot matchId 115660540726095109 核对 series gameWins
  与 G1–G4 阵容；
- 三场 2:1 的 G3 无独立 Map Winner 市场，只按整场结算归属，
  不生成虚假第三图曲线，不使用 1-p 镜像。

库更新：
- price_paths 698 -> 704；
- LoL 一级形态库 258 -> 259；
- CS2 一级形态库 96 -> 101；
- 统一训练 360 -> 366 场，观察点 14,532 -> 15,405。

形态与聚类：
- 正式命名保持 16 个有效标签 + 暂未归类；
- 聚类域仍为 5 个：LoL 整场 259 / 小局 510、CS2 整场 101 /
  单图 201、Dota2 整场 6；
- 共 16 个具体聚类组；聚类为 L0 观察，不新增正式第 17 种形态。

交付：
- reports/intel_cs2_iem_beijing_2026_11_03_04.html
  + knowledge/intel_pages/intel_cs2_iem_beijing_2026_11_03_04.md；
- reports/intel_lol_worlds_qf_2026_11_04.html
  + knowledge/intel_pages/intel_lol_worlds_qf_2026_11_04.md；
- reports/pattern_shapes_lol_worlds_qf_2026_11_04.json/html；
- reports/pattern_shapes_cs2_iem_beijing_2026_11_03_04.json/html；
- reports/pattern_cluster_2026-11-04.html；
- reports/pattern_clusters_2026-11-04.json；
- docs/data/intel/cs2_iem_beijing_review_2026_11_03_04.json；
- docs/data/intel/lol_worlds_qf_review_2026_11_04.json；
- tools/build_cs2_iem_beijing_2026_11_04.py；
- tools/build_lol_worlds_qf_2026_11_04.py；
- tests/test_cs2_iem_beijing_2026_11_04.py、
  tests/test_lol_worlds_qf_2026_11_04.py。
```

### 2026-11-03 多赛事一分钟赔率、形态库与聚类更新

```text
状态：已完成并入库

范围：
- LoL：Worlds 7 场；
- CS2：PGL Bucharest Playoffs 5 场 + IEM Beijing Group Stage 13 场；
- Dota2：PARI Universe Playoffs 6 场；
- 合计 31 场、67 个 Winner 市场。

数据：
- 双方真实 outcome token，约 60 秒，游戏与赛事分层。
- Worlds / Dota2 本次无独立逐局 Winner 市场。
- PGL Nemiga-FURIA 2:3 的 G1/G2 单边分钟价格缺失、G5 无独立市场；
  整场样本保留，小局缺口显式记录。
- 精确赛制比分取 Polymarket Gamma event score，并与 Riot/官方赛果交叉。

库更新：
- price_paths 667 -> 698；
- LoL 一级形态库 251 -> 258；
- CS2 一级形态库 78 -> 96；
- 统一训练 329 -> 360 场，观察点 13,587 -> 14,532；
- Dota2 首次进入统一训练，独立样本 6 场。

命名：
- 正式展示名固定为 16 个有效形态 + 暂未归类。
- A3=高位回撤修复、A4=整场逆袭反转、B4=持续阴跌/低位持续阴跌；
  旧赔率生成器同步消除旧称。

聚类：
- 5 个游戏×层级组：LoL 整场 258 / LoL 小局 506 / CS2 整场 96 /
  CS2 逐图 191 / Dota2 整场 6；
- 巡检 12,029 条序列、436 条未知、40 组签名候选；
- 37 组进入观察池，3 组中位停滞判为数据质量/未完成；
- 聚类仍为 L0，不升级自动策略。

交付：
- reports/intel_multi_game_odds_2026_11_03.html
  + knowledge/intel_pages/intel_multi_game_odds_2026_11_03.md；
- reports/pattern_cluster_2026-11-03.html；
- reports/pattern_clusters_2026-11-03.json；
- reports/pattern_audit_2026-11-03.md；
- docs/data/intel/multi_game_review_2026_11_03.json；
- tools/build_multi_game_odds_review_2026_11_03.py；
- tools/fetch_event_meta.py；
- tests/test_multi_game_odds_2026_11_03.py、
  tests/test_pattern_library_missing_map_prices.py。

验证：
- 80 项相关回归通过；
- 目标 31 场在 matches / match_index / price_paths 无重复；
- 全部 JSON 可解析；
- 用户可见赔率、形态、频率、粒度页面已消除内部 A/B/C 代码直出。
```

### 2026-11-23 弹幕情报台新增“赛前情报”独立模块

```text
状态：本地已实现并完成真实只读验收；待 VPS 部署/线上验收

数据源：
- Stake 官方 Sports Data API（赛程 / 市场）；
- 足球 / NBA：Stake 页面公开嵌入的 Sportradar LMT Plus；
- CS2 / Dota2 / LoL：Stake 页面公开嵌入的 Oddin iframe + GraphQL；
- 足球首批 7 个热门赛事目录，NBA 1 个目录；
- 电竞继续使用 LoL / CS2 / Dota2 联赛白名单；
- 不登录、不使用账户 Token、不调用下注或账户接口。

交付：
- config/stake_prematch.json；
- tools/build_stake_prematch_site.py；
- tools/stake_lmt.py；
- tools/stake_oddin.py；
- reports/intel_prematch.html；
- reports/intel_prematch.json；
- 导航新增“赛前情报”；
- deploy/prematch-intel/prematch-intel.service / .timer（每 10 分钟）；
- docs/task/PREMATCH_INTEL_MODULE.md；
- tests/test_stake_prematch.py。

真实只读验收（2026-11-23，72 小时窗口）：
- 43 场未来比赛；
- CS2 8、Dota2 4、足球 21、NBA 10；
- 42 场有效主市场报价，1 场 fixture detail 500 缺口；
- 43 场完整深包：LMT 31/31、Oddin 12/12；
- CS2 深包含双方约 10 人、地图池、T/CT 与逐选手统计；
- Dota2 深包含双方约 10 人、近 5 场、H2H、127 项赛事英雄池；
- 足球 / NBA 深包含排名/近况、伤停、名单、首发与 H2H；
- 页面不再读取旧队伍/选手画像库；
- 英雄联盟当前窗口 0 场，按无场次显示；
- NBA 当前近况/伤停/名单/近场五人/总体与分区积分榜可用；
- 请求错误 1（Atletico Madrid - Viking fixture detail；详情深包仍保留）。

边界：
- 十进制赔率与去水概率只作赛前市场共识；
- 不混入 Polymarket 0–1 分钟价格；
- 不触发自动交易；
- GitHub 是站点产物版本仓库/Pages 镜像，生产实时展示仍由 VPS nginx 承担。

## 2026-10-18 情报库实时性优化（④ 把等待压短）

```text
背景：用户提"先做第四点"（便宜、零 AI 成本的即时优化，把等待压短），
对应"待办：情报库优化"优化点 1 的触发/刷新及时性部分（非 Codex 生成耗时）。

完成（本地 run_local_intel.sh 一键流 + 规则层实时页）：
1. 规则层实时页刷新 5 分钟 -> 60 秒（tools/danmu_live_monitor.py）：
   监控本每 60 秒重写页面，但 HTML 里 meta refresh 写死 300 秒，浏览器 5 分钟才重载。
   改为 meta refresh 与监控间隔一致（--interval 默认 300->60，动态渲染 content 与
   "每 N 秒自动刷新"标签）。效果：浏览器每 60 秒自动重载，无 AI 成本。
2. 流水线触发频率 60 秒 -> 20 秒（run_local_intel.sh INTERVAL 默认值）：
   vps_intel_pipeline --once 循环从 60s 改 20s（有 pipeline.lock，重叠自动跳过，安全），
   节点到期检测更及时。服务器 systemd 1 分钟轮询不变。
3. 小局结束检测加价格信号：核对后确认已实现（vps_intel_pipeline 的
   ended = closed or winner 已置位 or 任一 outcomePrice >= 0.99，防错规则第 20 条），
   未新增改动；兜底"保守时间窗"（CS2 55 分钟）为 10-16 加时 / Aurora-9z 误判教训
   专门调保守，不放松。

验证：两个文件过语法检查（ast.parse + bash -n），关键行逐条确认落地。
文件：tools/danmu_live_monitor.py、run_local_intel.sh。
```


## 2026-10-18 情报节点模板化生成（① 治本提速）

```text
背景：用户提"做优化点 1 最大杠杆：模板化生成，AI 只填字段、不写整页 HTML（治本）"。
单节点 8-9 分钟的最大来源是 AI 整页写 HTML+CSS；而规则层 danmu_intel.analyze
其实已产出结构化数据（teams/players/gray_signals/density_bursts/narrative），
只是又被压成散文再让 AI 重新排版。目标：AI 只输出结构化 JSON，本地模板渲染。

完成（本地 DANMU_INTEL_AI=deepseek 快节点路径）：
1. 新建 tools/intel_html.py：共享 SAP/Apple 渲染助手（CSS 站点壳同族 --accent:#0071e3
   + esc/card/sig/src_box/speed_block/page）。
2. 新建 tools/render_node_page.py：模板渲染器，输入 AI JSON 字段 + 规则层 stats，
   本地拼 12 段（0 速览卡 / 0.5 关键变量卡+阵容裁决卡 / 1-11）。速览卡由渲染器按
   "信号 → 价值（置信） → 详 §N"固定格式拼装，生成即满足 speedcard_consistency 门禁
   （从"事后 --fix"变成"生成即合规"）。
3. 改 tools/vps_intel_pipeline.py 的 fast_intel_node 走 JSON 优先 + HTML 兜底：
   - 新增 NODE_JSON_SCHEMA（内联进 prompt）、_strip_json / _deepseek_call /
     _finalize_html 助手；新 json_prompt 令模型只输出一个 JSON 对象，max_tokens
     8000 -> 4000；
   - 解析成功 -> render_node_page.render() 本地渲染；解析/渲染失败 -> 回退旧 HTML
     prompt 重试一次（不产生空窗）；Codex 路径完全不动（独立兜底）。
4. 修一个生成 bug：速览卡 value 置信重复（schema 让 AI 把置信写进 value，渲染器又拼一次，
   显示"（单源待验证）（单源待验证）"）——渲染器剥掉 value 尾部置信词再统一由 confidence
   字段补，schema/prompt 同步写明"置信别写进 value"。

验证（全绿）：
- py_compile 三个文件通过；
- 回归测试 13/13（speedcard_consistency + match_state_guard，最小 runner 直跑 test_*）；
- 离线 dry-run（模拟 AI JSON）12 段齐全、速览卡 signal→value（置信）→详 §N、空态合规；
- speedcard_consistency --check 问题页 0；vps_intel_pipeline 运行时 import 正常。

未做（留待真实比赛）：计划第 5 步"真实切片 + 真 AI JSON 对比"需进行中比赛 + DeepSeek key，
下次跑 ./run_local_intel.sh（DANMU_INTEL_AI=deepseek 已指向新路径）自然验证。

回退：Codex 路径与 HTML 兜底都在；临时恢复只需把 DANMU_INTEL_AI 路径切回 HTML 版或依赖兜底。
文件：tools/intel_html.py（新建）、tools/render_node_page.py（新建）、
      tools/vps_intel_pipeline.py（改 fast_intel_node）。
```


## 2026-10-18 情报库并行度再升（③ 跨场并行）+ 等待再压短（④ 二轮）

```text
背景：用户提"③ 并行度再加（当前只做到同局 BP/局中并行）④ 便宜的即时优化：
把等待压短"，在 ①④ 首轮基础上继续优化（对应"待办：情报库优化"优化点 1
方向 c 跨场部分 + 触发/刷新及时性二轮）。

完成（本地 DANMU_INTEL_AI=deepseek 快节点路径 + 规则层实时页）：
1. ③ 跨场并行：tools/vps_intel_pipeline.py 把串行 for m in matches 循环抽成
   process_match(m, all_files)，主循环改 ThreadPoolExecutor 并发跑多场比赛，
   MAX_MATCH_WORKERS 默认 3（可经 INTEL_MAX_MATCH_WORKERS 覆盖）。多场比赛
   生成互不排队；已核对无共享文件写竞争（fetch_game_markets / read_game_status
   只读，build_timeline_shell 只写本场文件）。
2. ④ 等待再压短（二轮）：
   - 规则层实时页刷新 60 秒 -> 30 秒（tools/danmu_live_monitor.py --interval
     默认 300->60->30，render_page 动态写 meta refresh 与"每 N 秒"标签；
     tools/run_danmu_session.py --monitor-interval 默认同步 30）；
   - 本地流水线触发 20 秒 -> 10 秒（run_local_intel.sh INTERVAL 默认，
     有 pipeline.lock 重叠自动跳过，安全）。
   小局结束检测已含 Polymarket 结算价信号（outcomePrice >= 0.99，防错规则
   第 20 条），本轮无改动。

验证（全绿）：
- py_compile（vps_intel_pipeline / danmu_live_monitor / run_danmu_session）+
  bash -n run_local_intel.sh 通过；运行时 import 正常；
- 回归测试 13/13（speedcard_consistency + match_state_guard）。

未做（用户明确"先不做"）：同场跨节点并行（G1 复盘 + G2 BP 同时出）。原因：
G2 BP 切片窗口锚定 G1 结束时间（g_start = game_t + 8min，game_t 来自 G1 end
状态文件 generated_at，需等 G1 复盘生成完才写），是数据依赖而非单纯并发；
若提前用 now_utc 切窗口会回到 2026-08-25 滑动锚点教训（G2+ 节点窗口追不上、
全部缺失）。要做需先解耦"G1 结束锚点"（改用 Polymarket 结算信号时刻/检测时刻
作固定锚点并持久化）+ 补回归，单列为下一项独立设计。

文件：tools/vps_intel_pipeline.py（跨场并行）、tools/danmu_live_monitor.py、
      tools/run_danmu_session.py、run_local_intel.sh（④ 二轮）。
```

## 2026-10-18 情报页新增【比赛局势】栏（两队胜率 + 虎扑队员评分）

```text
需求：在情报页 0–12 栏基础上加一栏【比赛局势】——① 按观众弹幕实时总结两队
胜率、相加=100%、队1 蓝 / 队2 红；② 每队队员评分用虎扑数据、实时变动。
用户确认：节点页 + 实时监控页两处都加；胜率算法 = 显式胜负弹幕计数。

实现（纯规则层，AI 不产胜率/评分，杜绝幻觉）：
1. 胜率信号 tools/danmu_intel.py 新增 win_signal(rows, teams, threshold=10)：
   同弹幕"队伍名 + 胜/负方向词"才计一次；负向词（输了/寄了/被零封/抬走）记给
   另一队；总样本 <10 或 =0 时 pct=None + sample_status=insufficient，不硬算。
   方向词表修正（防错）：去掉"冠军"（DK冠军=头衔易误判，换"夺冠"）；
   "抬走"从正向移负向（把X抬走=X输）；"被零封/被碾压/被血洗"含正向子串，负向优先判负。
   analyze() 加 teams 参数与 win_signal 字段；CLI 加 --teams。
2. 虎扑评分链路：fetch_hupu_esports.py + export_today_matches.py 保留
   scoreItemKey(outBizNo/outBizType) 与两队 memberId -> matches_today.json 的
   hupu_score_out_biz_no/type；新建 tools/fetch_hupu_player_ratings.py 三级下钻
   （lol_match -> lol_bo 各小局 -> lol_item 选手），strict_game=True 时该局评分
   未生成则返回空、不回退上一局（禁止串局）。
3. 节点页 tools/render_node_page.py 加 _situation() 栏（编号 1.5，蓝=队1/红=队2
   胜率双条 + 两列选手评分），render() 加 ratings 参数；vps_intel_pipeline 的
   danmu_intel 调用加 --teams、generate_game_node 拉评分传入 render（deepseek 路径）
   / 后置注入 situation_card（codex 路径）。
4. 实时监控页 tools/danmu_live_monitor.py 加 --teams/--hupu-out-biz-no，
   analyze 传 teams、评分 60s 节流拉取，render_page 加【比赛局势】块；
   tools/run_danmu_session.py 透传 --teams/--hupu-out-biz-no。

验证（全绿）：
- py_compile 8 文件通过；新增 tests/test_win_signal.py 12/12（相加=100、样本不足
  阈值、负向记对方、冠军头衔/抬走方向、双队同现/俚语不计、蓝红对齐）；
  既有 speedcard_consistency 5/5 + match_state_guard 8/8 直跑全绿；
- 离线 dry-run：真实切片 lol-dk-dns_g1_bp（win_signal 样本不足 2 条 <10 正确）+ 
  真实评分 JSON 渲染节点页，14 卡齐全、1.5 栏蓝红对齐正确。

文件：tools/danmu_intel.py、render_node_page.py、vps_intel_pipeline.py、
      danmu_live_monitor.py、run_danmu_session.py、fetch_hupu_esports.py、
      export_today_matches.py、fetch_hupu_player_ratings.py（新建）、
      tests/test_win_signal.py（新建）。
```

## 2026-10-19 【比赛局势】栏改按小局：局内实时、局末冻结 + 评分赛后回填

```text
需求（用户逐条确认）：① 每小局节点页显示"本小局"胜率 + "本小局"评分（不累积、不串局）；
② 局内实时更新、局结束后冻结；③ 局结束后评分仍需回填（虎扑评分赛后才陆续上线）。

关键发现（数据源事实）：虎扑"选手小局评分"是赛后投票制、非局内实时——接口返回的
scoreAvg + scorePersonCount 是观众打分计数，局内 players 基本为空；评分赛后 5-30 分钟
才爬升、数小时仍缓慢累积。故"局内刷新评分"基本拉不到数据，真正入口是赛后回填；
回填窗口抓的是主力投票潮，非最终定格值。

实现：
1. tools/render_node_page.py 胜率/评分两块各包 BEGIN/END 注释标记
   (_WIN_BEGIN/_WIN_END/_RAT_BEGIN/_RAT_END)，供刷新器就地替换、不重跑 AI 文本；
   标记是 render_node_page 与 refresh_situation 之间的契约，改块结构须同步。
2. vps_intel_pipeline.generate_game_node 状态写 slice_from（mid 节点=本局 g_start，
   作为本局切片起点）；fetch_ratings 保持本小局 strict_game 防串局。
3. 新建 tools/refresh_situation.py（--once / --interval）：逐小局处理——
   进行中局（end 未生成）胜率+评分实时刷 bp/mid 页；
   已结束局胜率严格冻结，评分在 end 生成后 30 分钟内回填 bp/mid/end 页
   （RATINGS_BACKFILL_MIN=30），超时全冻结；空评分返回 None 不回写（避免用空覆盖已有评分）；
   只改 reports/ 本地 HTML、不 git，发布仍由 vps_publish 负责。
4. 部署 deploy/danmu_intel/refresh-situation.{service,timer}：每 60s oneshot；
   docs/task/SERVER_INTEL_STACK.md 第 7 节同步为"局内实时、局末冻结 + 评分赛后回填"。

验证（全绿）：py_compile 5 文件通过；新增 tests/test_situation_refresh.py 11/11
（标记替换幂等、无标记返回 None 不误写旧页、fetch_ratings 本小局 strict、回填窗口
30min、空评分不回写、mid 节点优先定本局起点）；test_win_signal 12/12 无回归；
离线 dry-run 回填：bp/mid/end 页评分补上、胜率块保持冻结不被动。

文件：tools/render_node_page.py、vps_intel_pipeline.py、refresh_situation.py（新建）、
      deploy/danmu_intel/refresh-situation.{service,timer}（新建）、
      tests/test_situation_refresh.py（新建）、docs/task/SERVER_INTEL_STACK.md。
```

## 2026-10-19 【比赛局势】胜率把选手表态折算进队伍（选手名 → 队伍映射）

```text
背景：win_signal 只认"队名 + 胜负方向词"，观众大量用选手名表态（"Faker要赢了"）不进胜率，
导致队名口径样本偏少、常"样本不足"。用户要求加选手→队伍折算。

实现：
1. tools/danmu_intel.py 新增 PLAYER_TEAM（选手 → TEAMS 规范 key）——只登记阵容稳定、
   无歧义的归属；新增 _canon_team（队名归一，处理 "Spirit" vs "Team Spirit" 别名）、
   _team_player_keywords（把某队名下选手关键词并入该队匹配词表，按 game 过滤防跨联赛）。
2. win_signal 加 game 参数（默认 None 向后兼容）；analyze() 传 game（未显式给则从弹幕
   game 字段自动推断）；refresh_situation.py 传 vp._match_game(m)。
3. 跨游戏防串：donk（CS2 Spirit）在 Dota2 场不得折算进 Spirit；Yatoro（Dota2 Spirit）才折算。

已登记映射（9 人，阵容稳定）：Faker/Guma→T1、Chovy→GEN、Zywoo/Apex→Vitality、
donk→Spirit、Yatoro/Larl/Collapse→Spirit。
未登记（18 人，阵容/转会不确定，宁可漏计不误配）：Canna/Oscar/Poby/Hype/Mithy/Zeus、
Niko/m0NESY/Twistzz/ropz/sh1ro、Pure/bzm/33/Ari/Whitemon/not me/rue——待用户确认当前
阵容后补 PLAYER_TEAM 并回归。

验证（全绿）：py_compile 通过；test_win_signal 12→18（新增选手折算 6 条：选手胜/负、
跨游戏不折算、双队选手歧义、无关队伍选手不计、队名+选手不重复计）；
test_situation_refresh 11/11、test_speedcard_consistency 5/5 无回归；
端到端 analyze() 自动推断 game 后 "Faker赢了×3+Chovy寄了" → T1 count=4 正确。

文件：tools/danmu_intel.py、refresh_situation.py、tests/test_win_signal.py。
```

## 2026-10-19 【比赛局势】选手→队伍映射改动态（虎扑每小局首发阵容，替代静态硬编码）

```text
背景：上一版 PLAYER_TEAM 是静态硬编码 9 人，18 名选手因"转会/阵容不确定"漏计。
用户定稿：选手名应按"虎扑推送的比赛 + 每小局首发阵容"动态填充，不再手工登记。

实现（主源动态、静态兜底）：
1. tools/fetch_hupu_player_ratings.py 新增 fetch_lineup(obn, obt)：复用评分树三级下钻，
   返回 {选手名: 队伍名}（只保留有归属的选手；教练/替补/多英雄已由评分接口过滤）。
2. tools/danmu_intel.py：
   - win_signal 新增 player_teams 参数（动态阵容），内部 eff = 静态 PLAYER_TEAM + 动态
     （动态优先，转会/换队覆盖静态）；
   - 新增 _player_entry（选手名 -> PLAYERS 反向解析）：虎扑官方名 Gumayusi 命中
     PLAYERS["Guma"] 别名后，昵称弹幕"姑妈"也能折算进 T1；PLAYERS 未登记的选手用官方名
     本身作关键词；
   - _team_player_keywords 改接 player_teams（静态+动态合并），game 过滤保留；
   - analyze 加 player_teams 参数；CLI 加 --players <json>。
3. tools/vps_intel_pipeline.py 新增 fetch_lineup(mid)（不 strict_game，取最新一局 roster），
   generate_game_node 在 danmu_intel 子进程前拉阵容、写 lineup.json、追加 --players 参数。
4. tools/refresh_situation.py _win_block、tools/danmu_live_monitor.py analyze 均注入动态阵容
   （监控页直接复用已拉的评分 players[name/team]，不额外请求）。

语义：阵容同系列固定，取最新一局即可；比赛未开/拉取失败时 player_teams 为空，
自动降级静态 PLAYER_TEAM（Faker/Guma→T1 等 9 人仍可折算），不因动态化而回归。

验证（全绿）：py_compile 通过；test_win_signal 18→24（新增动态阵容 6 条：新选手折算、
官方名反查别名、动态覆盖静态、空阵容回退静态、未登记官方名、全称队名归一）；
端到端 CLI --players（Burdol->HLE 12 条全计 HLE）；fetch_lineup 抽取逻辑单测通过。

文件：tools/fetch_hupu_player_ratings.py、danmu_intel.py、vps_intel_pipeline.py、
refresh_situation.py、danmu_live_monitor.py、tests/test_win_signal.py。
```

## 2026-10-19 【比赛局势】胜率改近窗口口径（防"前期优势累积盖过末段被翻盘"）

```text
背景（用户发现的口径缺陷）：胜率原来对整个时间窗做纯计数、无时间概念，前 8 分钟
优势方攒下的"稳了/拿下/必胜"永不过期，末段被翻盘时"寄了/输了"只能加到对手头上、
无法抵消输家前期正向分——实测模拟：前 8 分钟 Alpha 优势 + 最后 2 分钟被翻盘，
累积口径仍显示 Alpha 62% / Beta 38%（实际 Alpha 输了），失真。

实现（近窗口，默认 5 分钟）：
1. tools/danmu_intel.py win_signal 新增 window_seconds=300 参数 + 抽出 _count_signal
   （计数逻辑复用）：window_seconds>0 时只统计「最新窗口秒内」的胜负弹幕，反转立即反映；
   近窗口样本 < threshold 时回退整段累积；window_seconds<=0/None 或行无时间戳时退化
   为整段累积（向后兼容）。输出加 basis（recent/cumulative）标记实际口径供审计/渲染。
2. analyze 透传 window_seconds（默认 300，调用方无需改动）。
3. tools/render_node_page.py situation_win_block 按 basis 标注口径：recent 显示
   "近 N 分钟胜负弹幕"，cumulative 显示"整场胜负弹幕（近 N 分钟样本不足回退累积）"。

语义变化：胜率从"整场累积观众表态"变为"当前局势/近期动能"，更贴合"比赛局势"栏；
局末冻结值 = 终局前 5 分钟口径，末段被翻盘的一方会正确显示为落后。

验证（全绿）：py_compile 通过；test_win_signal 24→28（新增近窗口 4 条：反转反映、
样本不足回退累积、显式关闭窗口、无时间戳退化累积）；test_situation_refresh 11/11、
test_speedcard_consistency 5/5、test_match_state_guard 8/8 无回归；反转场景实测
近窗口 Beta 100% / Alpha 0%（正确）、累积口径 Alpha 62%（原缺陷对照）。

文件：tools/danmu_intel.py、render_node_page.py、tests/test_win_signal.py。
```

## 2026-11-24 网站问答助手与使用指南（任务 6）

```text
需求：新增问答助手和 FAQ，覆盖比赛基本情况、幻觉核心识别、常见问题、
个人介绍，以及站内、TG 频道和 TG 个人号导流，并兼容手机与桌面。

实现：
- 新建 intel_help.html：比赛字段说明、幻觉五问、FAQ、个人介绍和开始使用入口；
- 全站注入可收起问答助手：固定知识库匹配，不开放自由生成，避免二次幻觉；
- 覆盖比赛状态、阵容/首发、市场概率、数据缺口、证据分层、风险和联系方式；
- 桌面右侧悬浮窗，手机底部全宽面板，支持快捷问题、Enter 发送和 Escape 关闭；
- 主导航新增“问答 FAQ”，发布流程自动复制帮助页与助手资产并注入所有页面。

安全与口径：
- 公开页不展示底层平台名称，统一使用 AI 综合赛前情报/结构化数据表述；
- 名单不等于本场官方首发；市场百分比不等于真实胜率；无样本明确标缺口；
- 助手不保存聊天记录，不承诺盈利，不构成投注建议。

验证：相关测试 83 项通过；JS node --check、Python 编译通过；
桌面 1280px 与手机 390px 实机截图检查通过。

文件：tools/build_intel_help.py、tools/add_assistant.py、
tools/add_site_nav.py、tools/vps_publish.py、tools/sync_rules_to_vps.sh、
reports/intel_help.html、reports/assistant.css、reports/assistant.js、
tests/test_intel_help.py、tests/test_add_site_nav.py。
```
