LEC 2026 Summer · FNC vs NAVI G1 局后情报（修正版）· 2026-08-24

# FNC vs NAVI · G1 局后情报（修正版）

*
    LEC 2026 Summer · 常规赛第 5 周 · BO3 第 1 局 **已结束**

    结果：NAVI 1-0 FNC（官方比分源 + 用户确认）
    修正：本页初版误标 FNC 1-0，2026-08-25 已更正

## 0. 修正声明（一次错误原则）

    **错误：**初版将 G1 归属判定为 FNC 胜（"弹幕口径"）。

    **根因：**把英文 Twitch 弹幕的**反讽/玩梗**（"FNC ARE BACK / HOLY FNC / FNC is playing well.. mhm" =
    嘲讽 FNC 老毛病、笑 FNC 送）误读为 FNC 庆祝，并用单方弹幕情绪覆盖了比分机器人
    （NAVI 1-0）与官方比分源（Sheep Esports NAVI 1-0）的结构性证据。

    **防错规则已固化（AGENTS.md 第 14 条）：**赛果判定优先级 =
    官方/比分机器/权威比分站/用户确认 > 弹幕情绪；英文弹幕必须先做反讽语气判定，
    与结构源冲突时禁止用弹幕覆盖结构源。

## 1. G1 结果总览（官方口径）

- **NAVI 1-0 FNC**：G1 NAVI 获胜（比分机器人 Moobot "NAVI 1-0 / GAME 1 NAVI WINS" + Sheep Esports + 用户确认三方一致）；

- G1 过程（弹幕口径）：Rhilech 23:14 一度 int 被击杀，但 NAVI 仍赢下首局；FNC 侧 SamD 对位压制下路未兑现（SamD 属于 NAVI）；

- 修正后 G1 锚点验证：**Rhilech 三绝正锚应验**（NAVI 胜）、**FNC Locke 负锚应验**（FNC 输）。

## 2. BP 锚点验证（修正后）

| 锚点 | 方向 | 终局验证（修正后） |
| --- | --- | --- |
| NAVI·Rhilech·Aatrox（三绝之一） | 正锚 | **应验**（NAVI 胜 G1；虽 Rhilech 局中 int 仍赢） |
| FNC·英雄 Locke | 负锚 | **应验**（FNC 输 G1，Locke 选角负面方向兑现） |
| Viktor 今日禁用 | 版本情报 | 确认：昨日取消比赛触发 bug，Viktor 禁用（弹幕口径） |

## 3. 灰信号（G1，8 条 · 预警中）

    G1 收官窗口（23:32–23:34）集中质疑：**"明着假赛"（×3）/ "演戏" / "故意放资源" / "避战" / "只有菠菜的人看"**。
    主要来自硕硕 323444 房。

    **指向对象待复核**：初版记录为"NAVI 侧"，但随 G1 赛果修正（NAVI 胜），质疑对象需重新核对
    （可能指向 FNC 侧崩盘或整局观感）；已标注待复核，不硬下结论。

    纪律声明：观众质疑非结论；若兑现方向成立，对应侧价格可能失真（反手参考需盘口验证）。

## 4. 选手归属（官方 rosters，修正）

| 队 | 上 | 野 | 中 | 下 | 辅 |
| --- | --- | --- | --- | --- | --- |
| FNC | Soboro | Razork | **Vladi** | Upset | Lospa |
| NAVI | Maynter | **Rhilech** | **Poby** | SamD | Parus |

## 5. 数据与溯源

| 源 | 状态 |
| --- | --- |
| 比分机器人 Moobot（LEC 官方 Twitch） | NAVI 1-0 / GAME 1 NAVI WINS |
| Sheep Esports（官方比分页） | NAVI 1 : FNC 0（Aug 24 · 17:15 CEST） |
| 用户确认 | G1 NAVI 1:0 获胜 |
| 弹幕 5 路 JSONL | 作为过程佐证（情绪侧不可单独定胜负） |

bp_signals 已同步修正（rhilech_aatrox / locke_pick 判定翻转）；matches.json 已记录修正日志。

  修正版 2026-08-25 · 灰信号仅为观众质疑非结论 · 过程数据以官方结算为准
