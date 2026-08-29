# 情报库优化方案（P0 落地 · 2026-08-29）

> 目标（用户 2026-08-29 定稿）：① 从弹幕提炼更多选手/局内/预测信息；② 信息全面丰富；
> ③ 结合价值信息与共识信息辅助预测与下注。本文件为落地基准，所有新数据文件以本文件 schema 为准。

## 0. 现状诊断（2026-08-28/29 三线实战暴露）

1. **选手库缺失**：teams.json 有队伍画像，但没有 players.json——makazze 160 条"吹→批"、
   try 42-22、VicLa 发条三杀等选手级情报只活在 HTML 页，无法跨场复利。
2. **预测库缺失**：弹幕预测（"菊花沙二强图"/"打满"/"剧本论"）散在页面，无登记、无兑现率统计。
3. **局内事件未结构化**：关键回合/高光/失误/方向漂移只有时间线描述，无 per-game 事件记录。
4. **弹幕×盘口无对照**：无价格快照，无法回答"弹幕信号出现时价格如何、之后如何"。
5. **事实层靠人肉**：CS 比分卡滞后 + 时间戳换算错误（本日两次）→ 官方数据应自动快照。
6. **多源完整性弱**：LEC 仅 Remember 单源、LCK 仅硕硕单源——需直播间可用性监控+补源。
7. **线上覆盖本地**：matches.json 被 vps_publish 覆盖/产生重复记录（本日 1 次）→ 需合并防重策略。

## 1. 新增结构化库（P0）

### 1.1 预测库 `docs/data/intel/predictions.json`

```json
{
  "records": [
    {
      "id": "2026-08-28-lck-bro-bfx-g4-vicla-orianna",
      "match_id": "lck-bro-bfx-2026-08-28",
      "league": "LCK",
      "node": "g4_bp",
      "text": "大光发条能赢",
      "direction": "BFX 胜 G4",
      "subject": "player:VicLa",
      "type": "player_anchor",
      "source_rooms": ["huya_shuoshuo"],
      "confidence": "single_source",
      "ts": "2026-08-28T18:43:10+08:00",
      "verdict": "hit",
      "note": "G4 发条三杀逆转，BFX 3-2 晋级"
    }
  ],
  "stats": {"hit": 0, "miss": 0, "pending": 0, "hit_rate": null}
}
```

字段：`match_id`（关联 matches.json）/ `node`（pre/bp/mid/end/series）/
`direction`（结构化方向）/ `subject`（team:xx / player:xx / odds:xx / gray）/
`type`（team_anchor / player_anchor / map_anchor / result_pred / odds_pred / gray_pred）/
`source_rooms` / `confidence`（multi_source / single_source）/ `ts` /
`verdict`（hit / miss / partial / pending）/ `note`。

### 1.2 选手库 `docs/data/intel/players.json`

```json
{
  "players": [
    {
      "id": "lol-vicla",
      "name": "VicLa（大光）",
      "game": "lol",
      "team_id": "bfx",
      "role": "mid",
      "danmu": {
        "mentions_total": 0,
        "anchors": ["大法师能赢（发条三杀·兑现）", "加里奥/刺客执行被质疑"],
        "tone": "分歧（大法师正锚 + 刺客负锚）"
      },
      "official": {"note": "G4 发条三杀（直播吧）"},
      "updated": "2026-08-29"
    }
  ]
}
```

### 1.3 弹幕×盘口价格快照 `docs/data/intel/price_snapshots.jsonl`

每行一条快照：`{"ts":..., "market": "cs2-lgc-fut-2026-08-27", "slug": "...",
"side": "Legacy", "price": 0.59, "source": "chaincatcher/limitless/polymarket",
"danmu_signal_at": "...", "signal": "..."}`

用途：信号出现时价格 vs 之后价格 → 共识/价值/灰信号的定价反应。

## 2. 局内事件记录（P1）`docs/data/intel/game_events.json`

每局：`{match_id, game, event_ts, type: kill_streak/teamfight/turnaround/mistake/map_anchor,
subject, desc(弹幕原文), source_rooms, density}` ——支撑"队伍在 X 情境下怎么走"规律挖掘。

## 3. 事实层自动快照（P1）`runtime/intel_facts/<match>.json`

官方数据（Riot window / BLAST API / Liquipedia）自动落盘：比分、阵容、startedAt/endedAt、
抓取时间。生成情报时直接读快照，禁止人肉换算时间戳（教训：2026-08-28 两次）。

## 4. 直播间可用性监控（P1）

每 5 分钟检查各联赛默认采集集房间 `page_live`；缺口自动告警并标注"离线未采"；
单源场次自动降级"单源待验证"。

## 5. 兑现率统计（P0，随预测库）

按联赛/队伍/信号类型统计：观众预测命中率、灰信号兑现率、BP 锚点兑现率、
LEC 打满规律命中率。发布佐证闭环（AGENTS 规则 7）以此为数据源。

## 6. 落地顺序

- P0（本日）：predictions.json + players.json + price_snapshots.jsonl 建库；
  用 2026-08-28 已结束场次批量回填预测/选手；下一场（VIT vs FNC）实时试跑。
- P1（次日）：game_events.json + 事实层快照 + 直播间监控。
- P2：BP 锚点检索页 + 每场自动流水线。

## 7. 防错规则补充

- 时间戳一律用官方 UTC 快照转北京时间，禁止心算（本日两次教训）。
- matches.json 本地合并需幂等（按 id 去重，防 vps_publish 重复）。
- 预测/选手登记必须带 `source_rooms` + `ts`，无源不登记。
