# 弹幕情报 Skills 拆分规划

最后更新：2026-08-21

定位：把弹幕情报工作流拆成**多个职责独立的 Skill**，每个 Skill 可自动触发、
可独立维护，避免"一个弹幕 skill 什么都管"导致规范失控。

## 一、拆分原则

```text
1. 按职责生命周期切，不按比赛类型切：
   LoL/CS/DOTA 是词表差异（assets/词表），不是 Skill 差异；
2. 每个 Skill = SKILL.md（触发条件+规范）+ assets（脚本/模板/词表）；
3. 依赖链单向：capture -> intel -> report -> verification -> library-sync；
   gray-tracking 横切（各环节都要喂数据给它）；
4. 触发条件用自然语言描述，运行时自动加载对应 Skill。
```

## 二、Skill 地图（6 个）

```text
1. danmu-capture（采集与监控）
   触发：启动/检查/恢复直播间弹幕采集
   输入：直播间 URL / session 名
   输出：JSONL 落盘 + session 健康状态 + 完整性记录
   资产：run_danmu_session.py / fetch_huya|soop / streamer_registry
   规范：DANMU_CAPTURE_RULES（开停/断线/完整性）

2. danmu-intel（弹幕情报分析）
   触发：需要对原始弹幕做提炼（队伍/选手/BP/盘口/灰信号/密度）
   输入：JSONL 切片
   输出：结构化 intel（词表命中/情绪/密度/灰信号）
   资产：danmu_intel.py / 词表 / BP_INTEL.md / LIVE_INTEL_SCHEMA

3. intel-report（情报 HTML 输出）
   触发："输出情报"/局中/整场复盘
   输入：intel + 画像库
   输出：A/B/C 三类 HTML（SAP 样式 + LONG/SHORT 分层 + 溯源）
   资产：INTEL_HTML_TEMPLATE.md / HTML 骨架模板

4. result-verification（结果校验）
   触发：比赛结束候选/用户提供结果/比分确认
   输入：弹幕窗口 + 候选结束时刻
   输出：多信号判定（确认/待确认/未确认）+ 误判修正
   资产：verify_match_end.py / VERIFICATION_METHODOLOGY.md

5. intel-library-sync（情报库同步）
   触发：任何情报/结果/画像更新后
   输入：新数据 + 现有 JSON 库
   输出：matches/teams/players/gray/bp/leagues 同步 + memory_tier +
         报告索引 + DANMU_INTEL
   规范：数据同步约定 / MEMORY_TIERS

6. gray-tracking（灰信号与留痕管理，横切）
   触发：灰信号出现/实体再犯/统计查询
   输入：灰信号记录 + 实体库
   输出：gray_entities/bp_entities 升级 + 统计页刷新 + 兑现率
   资产：gray_signals_stats 生成逻辑 / CAPTURE_RULES 13/15bis
```

## 三、与现有文档的关系

```text
AGENTS.md = 项目级共识（每次会话必读，含最高优先级规则）
knowledge/*.md = 各 Skill 的规范正文（SKILL.md 引用它们，不重复内容）
docs/task/SKILLS_PLAN.md = 本规划（Skill 地图 + 边界）
```

## 四、落地顺序（可选）

```text
1. 先做 intel-report（模板已定稿，最直接收益）；
2. 再做 result-verification 与 gray-tracking（可靠性/价值最高）；
3. danmu-capture / danmu-intel / intel-library-sync 紧随。
```
