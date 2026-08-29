# 情报规则刷新 V2（2026-08-24 · 与项目库现状对齐）

> 状态：已落地。项目库已完成：Twitch/KICK 实测接入（研究方法论
> knowledge/PLATFORM_ONBOARDING_METHODOLOGY.md + 各平台专属调研文档）、
> 采集器（fetch_twitch_danmu.py / fetch_kick_danmu.py）、MD 情报库
> knowledge/intel_pages/（200+ MD：比赛/画像/索引/分类框架）。
> 本文件为总则，细节以各文档为准。

## 一、信息源扩展：Twitch / Kick

```text
1. 平台注册表 streamer_registry.json 增加 platform 支持：twitch / kick；
   新频道必须先登记（频道名 / 平台 / 语言 / 关注赛事 / 采集状态），
   未登记不启用（沿用"未登记不启用"原则）。
   ✅ 已登记 12 个频道：Twitch（lec / lck / lck_korea / caedrel / kameto /
   otplol_ / lolesports / lolpacifictw）+ KICK（eslcs / gaules / cs2_maincast /
   esportsworldcup）。
2. 直播链接格式：
   - Twitch：https://www.twitch.tv/<channel>
   - Kick：https://kick.com/<channel>
3. 采集要求（✅ 工具已实现并实测）：
   - Twitch：匿名 IRC 直连（stdlib 零依赖，tools/fetch_twitch_danmu.py）；
     官方流常见 slow/emote-only 限速，高流量二路（Caedrel 等）为主源；
   - Kick：Pusher WebSocket 匿名直连（tools/fetch_kick_danmu.py，
     需 requests+websockets；Pusher app key 会轮换，文档已记失效排查路径）；
   - 落盘 JSONL（字段与虎牙/SOOP 对齐：text/message、nickname、ts、platform、
     nickname、ts、platform、source）；
   - 落盘路径：docs/data/danmu/{twitch,kick}/<日期>_<频道>.jsonl；
   - 跨天滚动、断线重连、健康状态与现有采集器一致。
4. 语言/时区：记录弹幕语言（en/ko/zh/其他）与统一 UTC 时间戳；
   非中文弹幕在情报输出时中文化（沿用韩文处理方式）。
5. 词表与队伍画像：新平台出现的新队伍/选手先补词表再分析（防静默漏抓）。
6. 数据一致性（最高优先级）：弹幕必须与比赛准确对应；无法判定归属时记
   "待归属"，禁止硬套（研究方法论通用注意点 5）。
```

## 二、情报输出双格式：HTML + MD

```text
1. 每场比赛/节点的情报产出 = 两份文件：
   - 完整 MD 文档：入库核心（结构化 + 可读，作为情报库的标准载体）；
   - HTML 展示页：站点呈现（SAP/Apple 风格），内容与 MD 同源。
   ✅ 项目库已建立 MD 情报库 knowledge/intel_pages/（比赛情报 MD + 画像 MD +
   索引 + intel_library_taxonomy.md 分类框架 v1）。
2. MD 文档规范（对齐 REVIEW_SCHEMA / LIVE_INTEL_SCHEMA / INTEL_HTML_TEMPLATE）：
   - front matter：match_id / 对阵 / 联赛 / 节点 / 时间(UTC+北京) /
     数据源 / 状态（局中/复盘/待确认）；
   - 正文章节：结果总览（弹幕口径·待官方确认）→ 逐局 → 队伍画像 →
     选手画像（带量）→ BP/图池 → 方向性情报（正锚/负锚/群体共识/
     灰信号条件预测）→ 密度时间线 → 预测验证 → 盘口 → 溯源；
   - 无样本写"样本不足"，无信号写"今日无信号"（沿用纪律）。
3. 生成方式：服务器流水线同时输出 MD + HTML（codex 一次任务双产物，
   或 MD 为主、HTML 由模板渲染派生）。
```

## 三、新的 MD 情报库

```text
1. 目录：knowledge/intel_pages/（MD 情报库，✅ 已建）
2. 组织方式：按类型 + 实体命名——
   intel_danmu_<A>-<B>[_节点]_<日期>.md（比赛/节点情报）、
   intel_profile_{team|player|champion|composition|league}_*.md（画像）、
   intel_library_taxonomy.md（分类框架）、intel_profiles_index.md /
   intel_danmu_index.md（索引）、intel_quick_lookup.md / intel_relational.md。
3. 索引：knowledge/intel_pages/intel_danmu_index.md（按日期倒序）+ 画像索引。
4. 与现有 JSON 结构化库的关系：
   - JSON（matches/teams/players/gray/bp）= 机器可读，供规则层/统计/联动；
   - MD = 完整人类可读情报（最终产出标准），HTML = 展示派生；
   - 两者 match_id 一一对应，MD 引用 JSON 数据与溯源。
5. 双格式同步：生成 MD 即生成 HTML；站点发布时 MD 入库、
   HTML 进 intel/（沿用现有发布流程）。
```

## 四、剩余待办（继续推进）

```text
1. Twitch/KICK 采集接入云服务器（vps_capture 自动读取注册表新频道；
   本文件同步后重启 danmu-session.service 生效）；
2. 服务器流水线双格式输出改造（MD + HTML 并行生成）；
3. MD 情报库同步云服务器（knowledge/intel_pages/ 全量）。
```
