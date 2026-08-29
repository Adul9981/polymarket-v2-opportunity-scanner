# 弹幕情报库·系统分类设计（2026-08-24 定稿 v1）

定位：把"每场比赛/每小局/局中"积累的弹幕情报，沉淀为**可跨场复用的专业情报库**。
核心原则：**实体化 + 关系化 + 验证化**——每一条情报都要能归到"谁/什么 × 什么时候 × 结果如何"，
并且可追溯（来源 + 时间戳 + 回填验证）。延续 memory_tier（LONG/SHORT/TRANSIENT）与
"凡走过必有痕迹"（再犯升级）机制。

## 一、总分类（四大域 + 跨切面）

```text
A 实体域（"谁/什么"——跨场复用，LONG）
  1. 联赛 leagues.json        赛事格式/爆冷传统/卡时间文化/灰风险/版本规律
  2. 队伍 teams.json          风格/核心/纪律/信任等级/灰信号历史
  3. 选手 players.json        英雄池焦点/状态/正负锚/灰留痕
  4. 英雄/角色 champions.json  ★新增 版本符号/正负锚/搭配需求/对位/样本
  5. 阵容/体系 compositions.json ★新增 体系类型/关键组合/克制/适用队伍/样本
  6. 地图 maps.json（CS 同构） ★新增 图池强弱/队伍×地图锚（或并入 bp）

B 事件域（"发生了什么"——单场事实，终态转 LONG）
  7. 比赛 matches.json + node_data（局级 bp/pre/review 节点）

C 信号域（"观众共识/异常"——可验证资产）
  8. BP 信号 bp_signals.json + bp_entities.json（选手×英雄锚、教练留痕）
  9. 灰信号 gray_signals.json + gray_entities.json（假赛/剧本/卡盘）
  10. 预测/共识 predictions（match 内嵌，赛后回填）

D 市场域（"盘口对照"）
  11. 盘口/价格（match 内嵌 + snapshots）：让分/人头/时长线与弹幕共识对照

跨切面：
  - 记忆分层：LONG / SHORT / TRANSIENT（knowledge/MEMORY_TIERS.md）
  - 验证回填：应验率 / 兑现率 / BP 判负验证（已入库统计）
  - 版本/时间：patch / 赛季 / 日期窗口
```

## 二、新增两层的数据模型

### 2.1 英雄层 champions.json（LoL）/ maps.json（CS）

```json
{
  "id": "jayce",
  "name": "杰斯",
  "game": "lol",
  "roles": ["上单", "中单"],
  "version_sign": {
    "label": "负锚（弱队判负）",
    "period": "2026-08",
    "evidence": "各大赛区杰斯十几连跪；'弱队杰斯=团队落后'；Zeus 例外（正锚）",
    "samples": 12
  },
  "anchors": [
    {"polarity": "负", "player_id": "th_blackman", "match_id": "2026-08-23_th_gx_g1",
     "quote": "炮没中过/0输出/团战一秒死", "ts": "2026-08-23T23:30+08:00", "verified": "应验"},
    {"polarity": "正", "player_id": "zeus", "match_id": "2026-08-23_t1_hle_g1",
     "quote": "宙斯的杰斯今年没输过", "verified": "应验"}
  ],
  "pairing_needs": [
    {"champion": "lucian", "with": "milio|nami", "note": "卢锡安必须配米利欧/娜美，否则判负"}
  ],
  "counters": [
    {"vs": "cassiopeia", "note": "能打蛇女的只有高手冰鸟（熟练度英雄）"}
  ],
  "team_fit": [{"team_id": "kc", "note": "弱队三负锚之一"}],
  "memory_tier": "LONG",
  "updated_at": ""
}
```

### 2.2 阵容/体系层 compositions.json

```json
{
  "id": "lucian_milio_bot",
  "name": "卢锡安+米利欧 下路体系",
  "game": "lol",
  "type": ["下路强度线"],
  "core": ["lucian", "milio"],
  "synergy": "卢锡安被动触发米利欧附加伤害",
  "requires": "米利欧/娜美必选其一；无体系=负锚",
  "countered_by": ["锁头组合", "双锁头后期"],
  "teams": [{"team_id": "gx", "note": "Flakked 绝活", "wins": 1, "losses": 0}],
  "samples": [
    {"match_id": "2026-08-23_th_gx_g2", "verdict": "未配米利欧→判负应验（TH 输）"}
  ],
  "memory_tier": "LONG",
  "updated_at": ""
}
```

### 2.3 关系模型（实体之间如何连接）

```text
league ──< team ──< player
player ──(proficiency/锚)── champion
champion ──(搭配)── champion   （如 卢锡安×米利欧）
champion ──(克制)── champion   （如 冰鸟>蛇女、发条<蛇女）
composition = core champions + style + countered_by
team ──(惯用体系)── composition
match ──(局级 BP)── champion set → bp_signals（选手×英雄锚）
gray_entities / bp_entities = team|player 再犯升级
```

## 三、与既有层的衔接（不推翻，只扩展）

```text
1. bp_signals.json 现有"选手×英雄"锚 → 上卷到 champions.json.anchors（去重）；
2. teams.json 风格标签 → 提取惯用体系 → compositions.json.teams；
3. leagues.json 版本规律（"杰斯判负/永恩连胜"）→ 同步到 champions.json.version_sign；
4. matches.games 的 pick 信息 → 每局结束后自动更新 champions/compositions 样本计数；
5. CS：bp_signals 图池情报（"FUT Nuke 零胜率"）→ maps.json 队伍×地图锚；
6. 画像页 intel_profiles_*.html 扩展 champion/composition 两类 C 型画像。
```

## 四、构建路线（增量落地）

```text
阶段 1（本次）：schema + 初版数据（从既有 47 场 / 17 条 BP 信号迁移首批
  英雄锚与体系样本）+ 框架页 reports/intel_library_taxonomy.html
阶段 2：BP 锁定自动记录 pick 组合 → 入库 champions/compositions；
  局中情报 B 型页补"本局体系"段
阶段 3：赛后自动回填应验（锚点/体系胜率统计）+ 画像页 + 统计页
阶段 4：检索/交叉查询（英雄×队伍×版本）+ 平台展示
```

## 五、纪律（沿用）

```text
- 无样本不硬撑、无信号不硬造；样本 <3 不登记为规律，只入观察池；
- 灰信号只作风险标注；版本符号=观众共识（非官方 meta），需标注口径；
- 所有锚点必须带时间戳 + 比赛 ID + 回填验证（应验/未应验/待验证）；
- memory_tier 默认 LONG（实体层），单场信号走 bp_signals/gray_signals。
```

## 六、前置考量定稿（2026-08-24 用户确认）

```text
1. 官方名册/昵称映射（aliases.json + rosters.json）：✅ 做——地基层，已建 v1
2. patch/版本时效（patches.json）：✅ 做——锚点必须带版本窗口，已建 v1
3. 官方基线胜率对照（幸存者偏差）：❌ 不做（用户判定无必要）
4. 应验/反例双轨（validation_samples.json）：✅ 做——已建 v1（11 条）
5. 客观层/官方数据关联（docs/data/intel/official/）：✅ 做——已建 v1
6. 阵容变动追踪（rosters.json.changes）：✅ 做——已建 v1（TH Sheo→Daglas 等）
7. 检索与自动触发（tools/intel_query.py）：✅ 做——CLI 已建；BP 自动检索推送待阶段2
8. 产品/合规边界：⚠️ 只加提醒——灰信号纪律 + 对外聚合口径，不单独建模块
9. 多路直播间交叉验证：✅ 核心方法——信号记录必须带 routes 字段
   （如 routes:["shuoshuo","official"]），单路=低置信、两路共振=升置信；
   采集阶段即并路，入库前统计共振（tools/route_resonance.py 检测；
   已完成 gray_signals 14/27 + bp_signals 7/17 的 routes 回填，其余标待核实）。
```

## 七、新增字段约定（v1 起强制）

```text
- 所有信号/锚点记录：routes（来源路数）+ patch（版本窗口）+ as_of（阵容/画像生效日）
- 验证双轨：verified ∈ {应验, 未应验, 部分, 待验证}；反例必须入库（validation_samples）
- 实体 ID：优先官方 ID；未核实的用 null + confidence=待核实，禁止编造
- 客观层与主观层通过 match_id 关联（official/official_matches.json ↔ matches.json）
```
