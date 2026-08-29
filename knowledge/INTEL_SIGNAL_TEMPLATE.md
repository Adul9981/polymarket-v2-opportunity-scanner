# 情报信号采集模板（手动阶段）

用途：看虎牙直播/录播时，把主播/解说的关键信息按固定格式录入，形成结构化信号。
机器可读权威源：knowledge/intel_signals.json；字段契约：schemas/intel_signal.schema.json。

## 一句话纪律

每条信号必须能回答四个问题：

```text
谁说的？（来源人/来源类型）-> 关于谁？（对象队伍/选手）
-> 说了什么？（原话摘录，短摘录不存全文）-> 利好哪侧？（方向含义）
无法对应到"利好哪侧"的信号只记录、不用于交易（INTEL_SIGNALS 规则 2）。
```

## 字段速查（中文 -> 代码值）

| 中文 | 字段 | 可选值 |
| --- | --- | --- |
| 来源类型 | source_type | caster_co（二路解说·首选）/ caster_official（官方解说）/ streamer（主播）/ official（官方）/ community（社区/朋友）/ danmaku（弹幕）/ user_observation（用户观察） |
| 可信度 | credibility | high / medium / low |
| 信号标签 | tags | style（风格打法）/ form（状态）/ proficiency（熟练度）/ bp（BP阵容）/ tempo（节奏阅读）/ event（事件风险） |
| 对象类型 | object_type | team / player / league / unknown |
| 采集阶段 | timing.phase | pre_match（赛前）/ in_game（赛中）/ post_match（赛后） |
| 应验状态 | verification.status | pending（待验证）/ confirmed（应验）/ partially_confirmed（部分应验）/ refuted（未应验） |
| 信号时效 | timeframe | durable（进长期画像）/ short_lived（近期状态，1-2 周） |

## 推荐录入方式

命令行录入（结构化、防手滑）：

```bash
python3 tools/record_intel_signal.py add \
  --date 2026-08-08 \
  --match lol-wb-lng-2026-08-08 \
  --source-person "957" \
  --source-type caster_co \
  --credibility high \
  --quote "某队中单不会玩这个英雄" \
  --tag proficiency \
  --object "待确认中单" \
  --object-type unknown \
  --direction "中单熟练度低 -> 该队中路劣势 -> 利多对手侧" \
  --phase in_game \
  --minute 12
```

赛后回填应验：

```bash
python3 tools/record_intel_signal.py verify \
  --id IS-2026-08-08-001 \
  --status confirmed \
  --note "应验依据一句话"
```

## 兜底手写模板（会后用工具补录）

```text
- 日期：YYYY-MM-DD
- 比赛：<event_slug>
- 来源人：<谁说的>
- 来源类型：<caster_co / caster_official / streamer / official / community / danmaku / user_observation>
- 可信度：<high / medium / low>
- 原话摘录：<短摘录，不存全文>
- 信号标签：<style / form / proficiency / bp / tempo / event，可多个>
- 对象：<队伍/选手/待确认>
- 对象类型：<team / player / league / unknown>
- 方向含义：<利好哪侧/怎么解读>
- 采集阶段：<赛前 / 赛中（第几分钟）/ 赛后>
- 流偏移分钟（可选）：<直播/录播内分钟>
- 市场验证：<采集前后价差，缺失写"采集前价缺失">
- 应验：<待验证 / 应验 / 部分应验 / 未应验>，赛后回填
- 时效：<durable / short_lived>
- 备注：<自由补充>
```

## 示例（已入库）

```text
IS-2026-08-08-002（二路解说 -> HLE 上单核心，风格标签，应验）
  quote: HLE 主要靠上单选手发挥；上单没声音时打野和辅助表现不好、没有节奏、带不起来
  方向: 看 HLE 比赛先看上单状态；上单被压制时倾向 B4 阴跌
  verification: confirmed（HLE 上单有声音的 G2/G3，HLE 赢下系列赛 2:1）
```
