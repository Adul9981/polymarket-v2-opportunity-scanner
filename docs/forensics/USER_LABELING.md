# 电竞用户行为标签库（试点规范）

最后更新：2026-08-15 · 状态：一周试点（从 2026-08-14 数据回填起算）

## 1. 目标

对 Polymarket 电竞 BO3 比赛（Game 1 / Game 2 / 整场胜负三个胜负盘）中出现的
所有用户账户，按公开成交行为打标签，沉淀为常驻标签库，用于：

```text
1. 假赛嫌疑场快速筛查：同一批老面孔（深水机器/全剧本/尘埃簇）跨场一致性。
2. 外部玩家画像反哺项目策略（对照 S1 低价反转等）。
3. 后续链上资金溯源的候选名单。
```

重要声明：**标签是行为推断（证据等级 3），不是事实**；新号判断有滞后，
链上来源仍是盲区。标签只用于研究和风险提示，不下单、不指控。

## 2. 标签体系

| 标签 | 定义（试点阈值） | 来源 |
| --- | --- | --- |
| A_深水机器 | 历史活动 ≤0.15 深水买入 ≥100 次 或 ≥$10k | enrich（拉活动） |
| B_全剧本 | 定局前买中 G1+G2+整场三个赢家，每腿 ≥$100 | label（事件内） |
| B1_赛前三腿 | 开赛前把三腿全部买齐（B 的子集） | label（事件内） |
| C_尘埃簇 | ≥2 个市场买双方、3 个市场都有买入、单场总成本 <$150 | label（事件级代理，enrich 复核） |
| D_盘后流 | 结果确定后买入 ≥$500 且最高价 ≥0.98 | label（事件内） |
| E_恐慌割肉 | G2 定局前买入 ≥$500 且均价 ≥0.30，局中 ≤0.20 卖出 ≥500 份 | label（事件内） |
| F_活跃双向 | G2 双方各买 ≥$100 | label（事件内） |
| G_低历史 | 活动记录 <1000 条 | enrich |
| H_局中深水 | G2 局中 ≤0.20 买入成本 ≥$300 | label（事件内） |
| I_赛前大额 | 单市场赛前赢家侧买入 ≥$3000 | label（事件内） |

标签可叠加；标签库按"标签出现次数"累计（同一账户 5 场都命中 B 与只命中 1 场不同）。

## 3. 口径说明（重要）

```text
1. "定局前" = 分钟级价格首次稳定在赢家侧（≥0.95 且之后不再跌破）之前；
   比手工拆解用的"价格起飞点"（G2 的 18:18）略宽，会把 0.6-0.9 追涨者计入 B。
2. "开赛时间"取市场的 gameStartTime（顶层 startTime 可能是市场创建时间，勿用）。
3. 整场市场在单局大比分领先时价格可能短暂到 0.95+（如 AL-JDG 的 17:57 假穿越），
   必须用"稳定在赢家侧"而不是首次穿越。
4. C_尘埃簇为事件级代理，机器簇确认需 enrich 的历史活动（A/G 标签）。
```

## 4. 数据流与运行

```text
label（事件级打标）:
  python3 tools/label_esports_users.py label <event_slug> [--data-dir DIR] [--db PATH]

enrich（重点账户历史画像）:
  python3 tools/label_esports_users.py enrich <event_slug> --top 30
```

每场输出（docs/forensics/data/<slug>/）：

```text
event.json / game1_trades.json / game2_trades.json / match_trades.json
prices_g1_winner_1m.json / prices_g2_winner_1m.json / prices_match_winner_1m.json
labels_report.json    # 全账户 + 标签 + 逐腿统计（机器可读）
labels_summary.md     # 标签统计 + Top 20 摘要
activity/<addr>.json  # enrich 产生的账户活动
```

标签库：`docs/forensics/data/accounts/esports_user_labels.db`（SQLite）

```text
events        事件主表（slug、开赛、定局时间）
users         用户累计表（address、首末次出现、事件数、标签计数、enriched）
event_labels  每事件每用户的标签与统计
```

## 5. 一周试点计划

```text
1. 每天比赛结束后对当天 LPL/LCK/LEC BO3 跑 label（每场约 1-3 分钟）。
2. 试点首日（2026-08-14）已回填 5 场：gx-vit、al-jdg（对照）、edg-lgd、ns-bro2、shft-sk。
3. 每 2-3 天跑一次 enrich --top 30，补 A/G 标签。
4. 一周后评估：标签稳定性（同一账户跨场命中率）、阈值是否合理、误标率。
5. 评估产出：cases/SUMMARY.md 或本文件"试点结论"小节。
```

## 6. 修正记录

```text
2026-08-15：早期稿误算对照组 AL-JDG 开赛时间为 13:15（实际 11:15 UTC），
曾得"赛前三腿全买 20 个"；按正确开赛时间重算为 1 个（antec），已修正全部文档。
教训：对照组的时间基准必须从市场 gameStartTime 取，不能手算。
```
