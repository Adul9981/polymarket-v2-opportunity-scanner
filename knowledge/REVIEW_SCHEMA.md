# 整局完整复盘标准（章节结构 + 字段 Schema）

最后更新：2026-08-19

定位：**比赛结束后的整局完整复盘**是弹幕情报的"终态沉淀"，与盘中实时情报
（`intel_danmu_live_<session>.html`，60s 快照、供盘中判断）**明确分工**：

```text
实时情报库（进行中）  -> 每 60s 快照：队伍/选手/BP/盘口/灰信号/健康状态
                       用途：盘中观察、仓位纪律触发（如局内异常信号）
整局完整复盘（结束后） -> 比赛结束按本文件章节结构沉淀：逐局复盘/人员画像/
                       灰信号汇总/规律验证/预测验证
                       用途：跨场知识积累、画像更新、模式验证
关联：复盘必须引用实时情报页 + 原始 JSONL，是实时情报的终态版本；
      实时情报是复盘的原始素材，不复盘则数据只停在"过程"层。
```

## 一、复盘 HTML 章节结构（每场必出，SAP/Apple 风格）

```text
0. 头部信息：日期 / 联赛 / 对阵 / 总比分（推断+待确认状态）/ 数据源（直播间+SOOP）
   / 数据量（弹幕条数、活跃用户）/ 数据窗口
1. 结果总览：系列赛概况、每局比分、MVP/关键选手（弹幕口径）、官方确认状态
2. 逐局复盘（每局一节，字段见下）：
   - 局结果 + 时长（弹幕推断）
   - BP/阵容：双方英雄与关键 pick（含"二队杰斯"类负面符号）
   - 局内时间线：一血/龙/先锋/团战/翻盘/结束 + 弹幕密度峰值时刻
   - 局势走向：领先方、如何被翻/滚雪球、资源控制异常（如"优势不控龙"）
   - 局内异常信号（灰数据四类：表情互动/队伍内讧/节奏异常/选手分裂）
   - 该局观众预测与验证（共识/分歧命中情况）
3. 队伍画像（逐队）：风格 / BP 特征 / 核心选手 / 问题点 / 盘面倾向 / 信任等级
4. 人员画像（逐选手）：ID（+音译）/ 队伍 / 角色 / 焦点英雄 / 本场表现（正负面）
   / 待确认项（官方名单）
5. 灰信号汇总：每局条数 / 关键词（译）/ 触发点 / 盘口对照 /
   **预警等级（低/中/高）** / **市场含义（被质疑方向 = 价格失真候选）** / 纪律声明
6. 联赛规律验证：本场对已知规律的命中/证伪（如 LCK CL 少 2:0）
7. 预测验证：观众共识 vs 分歧派 vs 结果，命中统计
8. 盘口讨论：数字盘（总人头/让分/时长）/ 方向 / 结果对照
9. 情报含义与后续观察点：画像更新、预期差、跨场可复用信号
10. 数据与溯源：原始 JSONL 路径 / 实时情报页链接 / 待官方确认项
```

## 二、结构化字段 Schema（matches.json 扩展，复盘时同步写入）

```json
{
  "id": "2026-08-19_xxx",
  "date": "YYYY-MM-DD",
  "league": "LCK/LPL/...",
  "teams": ["A", "B"],
  "streamers": ["房间1", "房间2"],
  "result_inferred": "A 2:1 B（弹幕推断，待官方确认）",
  "danmu_count": 0,
  "gray_signals_count": 0,
  "games": [
    {
      "game_no": 1,
      "result": "A 胜",
      "duration_min": 0,
      "bp": {"A": ["英雄1", "英雄2"], "B": ["英雄3"]},
      "bp_intel": {
        "evaluation": "阵容评价/观众共识与分歧",
        "proficiency_doubts": ["选手X英雄Y熟练度质疑"],
        "abnormal_picks": ["反直觉选角"],
        "coach_responsibility": "教练 BP 信号（低/中/高）",
        "bp_verdict": {"prediction": "判负/判胜", "result": "应验/未应验/部分"}
      },
      "timeline": [
        {"minute": 5, "event": "一血", "danmu_peak": false},
        {"minute": 28, "event": "翻盘团战", "danmu_peak": true}
      ],
      "turning_points": ["优势不控龙被翻"],
      "abnormal_signals": ["弱爆暗号", "选手分裂"],
      "prediction_validation": {"consensus": "A 胜", "hit": true}
    }
  ],
  "teams_intel": [
    {"team": "A", "style": "", "bp_notes": "", "core_players": [], "problems": [], "trust": "中"}
  ],
  "players_intel": [
    {"id": "", "nicknames": [], "team": "", "role": "", "focus_champions": [], "tone": "正/负/分歧", "notes": "", "pending": ""}
  ],
  "gray_signals": {
    "total": 0,
    "per_game": [{"game_no": 1, "count": 0, "keywords": []}],
    "correlated_markets": [],
    "alert_level": "低/中/高",
    "market_implication": "被质疑方向与对应盘口观察点",
    "discipline": "观众质疑，非结论"
  },
  "league_patterns": [{"pattern": "LCK CL 少 2:0", "validation": "命中/证伪/待验证"}],
  "prediction_validation": [{"prediction": "", "result": "", "hit": true}],
  "odds_discussion": [{"line": "", "direction": "", "result": ""}],
  "implications": [],
  "data": {"files": [], "reports": [], "live_page": "", "pending": []}
}
```

## 三、字段划分原则

```text
1. games[] 是核心：逐局独立（BP/时间线/转折/异常/预测验证），不复盘整场一锅粥；
2. teams_intel 与 players_intel 独立于 games：跨场累计画像，本场只更新证据样本；
3. gray_signals / league_patterns / prediction_validation 是"可验证资产"：
   每个都要可对照（盘口/官方数据/后续场次），不许只堆描述；
4. 所有结果类字段标注来源（弹幕推断/待官方确认），不许把推断当事实；
5. prediction_validation 的来源 = matches.json 每场 predictions[]（闭环 v2）：
   局中用 tools/record_prediction.py 记录（status=pending），赛后回填 hit/miss，
   再由 tools/build_closed_loop.py 生成闭环页；复盘只做汇总与画像沉淀，不重复记录。
5. 复盘落盘 = HTML（人读）+ matches.json 对应记录（机读）双轨，缺一不可。
```

## 三.5 比赛维度边界（2026-08-19）

```text
1. 复盘/情报的处理单元 = 比赛（一场 BO 系列）；一场比赛一个复盘、一个 matches.json 记录。
2. 比赛内含小局：games[] 每局一个对象；局间切换（G1->G2）只换局标签，
   不新建比赛/复盘/报告（同场比赛的局间小结可合并进整场复盘或单独存档）。
3. 边界判定：新比赛 = 对阵变化或系列重置（如上一场 2:1 结束、下一场新 BP）；
   小局切换 = 同一对阵内比分变化（GG 信号 + 重新 BP/选人）。
4. 无小局数据（断档/未抓段）时 games[] 对应局写"样本不足/断档"，不得跳过该局。
5. 比赛窗口与切片规范见 DANMU_CAPTURE_RULES.md 第 11 节。
```

## 四、产出流程（复盘怎么做）

```text
1. 比赛结束 -> 停会话（session.json state=stopped）；
2. 按第一节章节结构写 HTML（数据来自本场 JSONL + intel.json + 逐局弹幕切片）；
3. 同步 matches.json（按第二节 schema 填充 games/teams_intel/players_intel 等）；
4. 联动更新 teams.json / players.json / users.json / gray_signals.json / leagues.json；
5. 更新 reports/intel_danmu_index.html 与 DANMU_INTEL.md；
6. 有官方结果后回来确认 result_inferred（pending -> confirmed）。
```
