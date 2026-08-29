# 评论区情报抓取与分析规则库（Comment Intel Rules）

> 定位：把 Polymarket 评论区 / 直播弹幕等"社区主观信息"变成可复用的复盘与
> 情绪信号来源。本文件是抓取方法 + 时间线对照 + 信号判定的统一规则。
> 上游：knowledge/INTEL_SIGNALS.md（信号登记）、docs/task/INTEL_SIGNAL_LIBRARY_PLAN.md。
> 生效：2026-08-17（T1 vs DNS G2 暂停舆情首例）。

## 0) 核心事实（必须知道，否则会误判"无评论"）

```text
1. 电竞事件的评论挂在 series 层，不挂在 event 层：
   /events/{id} 的 commentCount 可能为 0，但 /series/{id}/comments/count
   可能是几千条（例：lol-t1-dnf-2026-08-17 事件 0 条，league-of-legends
   series 9316 条）。判"无评论"前必须先查 series。
2. 地址关系：profile 链接展示的地址是 proxyWallet，评论作者字段
   userAddress = baseAddress（主地址）。查历史评论必须用 baseAddress，
   查 profile 两个地址都可（/profiles/user_address/{base} 优先）。
3. 评论接口只读、无需登录；带 limit/offset 与 keyset 两种分页。
```

## 1) 抓取方法（执行规则）

```text
R1. 定位实体：
    GET /events?slug=<比赛slug> -> 取 event.id
    GET /events?id=<event.id> -> markets[].series[].id（评论归属层）
R2. 抓评论（推荐 keyset 反序）：
    GET /comments/keyset?parent_entity_type=Series&parent_entity_id=<series.id>
        &limit=100&order=createdAt&ascending=false
    用 next_cursor 翻页直到覆盖目标时间窗口；单页 100 条封顶。
R3. 按窗口过滤：目标窗口 = 比赛时段 ±10 分钟；
    暂停/异常事件单独切窗口（如 G2 暂停段 18:51-19:15 北京）。
R4. 原样保留字段：id / body / createdAt / userAddress / profile
    (name/pseudonym/proxyWallet/baseAddress) / reactionCount / reportCount。
    落地 docs/data/snapshots/<slug>/comments/*.json（原文 + 过滤视图）。
R5. 空结果自检（对齐项目最高优先级防错规则）：
    event 层 0 条 -> 必须查 series 层；series 也 0 条 -> 查 count 接口
    交叉验证；确认无数据才允许输出"该时段无评论"，否则报工具限制。
R6. 抓评论者历史：
    GET /comments/user_address/<baseAddress>?limit=100&offset=N（翻页至上限）
    GET /profiles/user_address/<baseAddress>（画像）。
R7. 批量抓取（工具 tools/fetch_series_comments.py，情报采集链只读）：
    fetch：按 series 抓最近 N 天评论 -> docs/data/snapshots/comments_batch/<series>_comments_raw.json
    slice：按比赛窗口 [startTime-10min, endDate+30min] 切分 ->
      docs/data/snapshots/<slug>/comments/ + 关键词标记摘要。
    已知 series id：lol=10311、cs2=10310、dota=10309。
R8. 并行比赛窗口重叠处理：同一时刻多场比赛时，时间窗口归属不唯一；
    必须用正文关键词（队伍名/选手名）二次归因，不能只靠时间。
    例：08-17 18:00-19:40 同时有 T1 vs DNS 与 DRXC vs HLE C，
    EurekaWTI 的"T1 challengers/chronobreak"评论按内容归 T1 场。
R9. 赛前/赛中自动提示（已接入 task2_pipeline --watch 循环）：
    tools/comment_intel.py 读取扫描输出 runtime/watchlist_events.json，
    对开赛前 90 分钟内的比赛与进行中比赛抓 series 评论，输出
    runtime/comment_intel.json + reports/comment_intel_<date>.md；
    名单/暂停/回滚/假赛/50-50 关键词命中即打印 ⚠ 提示（含原帖样本）。
    每轮 pipeline 刷新一次（--interval 默认 900 秒，可调）；
    --no-comment-intel 可关闭；离线 fixture 模式自动跳过。
```

## 2) 时间线对照规则（评论 ↔ 赔率）

```text
T1. 时间统一：评论 createdAt 是 UTC；赔率快照转北京（UTC+8）后对齐，
    输出统一用北京时间并标注。
T2. 对齐输出格式（表格）：
    时间（北京）| 评论者 | 正文（原文摘录）| 当时价格 | 方向含义
T3. 事件窗口划分：
    - 常态窗口：正常比赛推进，评论与价格双向印证；
    - 事件窗口（暂停/回滚/规则变更/选手变动）：单独切窗，
      窗口内价格行为（急变/阴跌/冻结）+ 评论共识并列展示；
    - 结算窗口：终局前后 10 分钟，评论多为结果宣泄，信息量低。
T4. 发帖时间与赔率的关联检验（lead-lag）：
    对每条"方向性评论"，记录：
      发言时刻价格 P0 -> P0+5min / P0+15min / P0+60min 价格变动。
    判定口径：
      - 一致（评论方向与后续价格同向）＝正向样本；
      - 相反或不变＝反向/无效样本；
      - 单条评论不计数，同作者累计样本 >=3 才开始评估可信度。
T5. 暂停/规则类评论优先于情绪类评论做对齐
    （规则引用类如"50-50 结算"直接可操作，情绪类只作氛围参考）。
```

## 3) 情绪/信号判定规则

```text
S1. 关键词分级：
    L1 事实/规则类：暂停、technical issue、chronobreak、结算条款、50-50
    L2 方向断言类：会跌/会涨、sell/buy、bagholders、short
    L3 情绪/指控类：scam、match fixing、shady、cheat
    权重：L1 > L2 > L3；L3 只记录不单独构成信号。
S2. 共识判定：同一事件窗口内，>=2 个独立账号发布同向可操作内容 = 共识；
    单一大 V 或重复账号不计入共识。
S3. 用途边界（与弹幕共识信号一致）：
    评论区信号只作"警示/减仓参考"，不作反手/方向依据；
    只有"暂停事件 + L1 规则类共识 + 高位持仓"组合才升级为可操作警示。
S4. 每条信号入 knowledge/intel_signals.json（工具 record_intel_signal.py），
    必须可追溯：作者、时间（UTC）、price_before/price_after、原文摘录。
S5. 评论者画像：新建 knowledge/COMMENTERS.md，逐人累计
    "方向性发言次数 / 命中次数 / 覆盖比赛"，样本 >=5 才给可信度标签；
    画像只用于观察名单，不直接作为交易依据。
```

## 4) 落地位置

```text
原始数据：docs/data/snapshots/<slug>/comments/
规则库：本文件 knowledge/COMMENT_ANALYSIS_RULES.md
信号登记：knowledge/intel_signals.json + knowledge/INTEL_SIGNALS.md
评论者画像：knowledge/COMMENTERS.md
疑似假赛：knowledge/leagues/FIXED_MATCH_SUSPECT_CASES.md
复盘引用：knowledge/reviews/*.md（舆情段标注来源与抓取方式）
```

## 5) 待办

```text
1. 虎牙弹幕抓取：需房间/录播链接（vid），接口 cxt.huya.com/open/danmu/scrollList.do
   已验证可用；用户确认弹幕可抓（2026-08-17 NAVI vs TH），待提供
   房间/录播链接后做"弹幕共识 -> 送局/假赛归因"分析（目标：
   弹幕情绪 + 关键词 -> 该场是否"带着任务"的可观察依据）。
2. 评论者历史批量验证：对 COMMENTERS.md 名单逐人跑 lead-lag 检验。
3. 平台提示：若后续出现评论延迟/删除（reportCount 变化），回查抓取时间戳，
   避免把"删除后"误判为"无讨论"。
```
