# 形态库巡检（2026-08-11）

快照序列：136 条；快照组：30 组（较上次新增 4 组：dota2-mouz-re-2026-08-11, lol-drxc-foxy-2026-08-11, lol-hle1-dnf-2026-08-11, lol-nsea-dkc-2026-08-11）

## 1. 已知形态复验计数

| 形态 | 累计样本 | 上次 | 本周期新增验证 |
| --- | --- | --- | --- |
| B4_直线阴跌 | 49 | 47 | +2 |
| A2_中位U型反转 | 31 | 24 | +7 |
| A3_折价修复 | 15 | 15 | +0 |
| A1_V型极值反转 | 14 | 11 | +3 |
| 热门全程压制 | 12 | 12 | +0 |
| C2_五五开开局碾压 | 10 | 10 | +0 |
| 未知 | 9 | 8 | +1 |
| A4_下狗整场反转 | 8 | 7 | +1 |
| A6_反弹确认 | 7 | 5 | +2 |
| B2_死亡螺旋 | 6 | 6 | +0 |
| A5_W型双底 | 6 | 4 | +2 |
| B4_低开阴跌 | 6 | 6 | +0 |
| A7_强强对话错杀 | 4 | 3 | +1 |
| C2_早期缩距/热门确立 | 1 | 1 | +0 |
| B1_尾盘崩塌 | 1 | 1 | +0 |

## 2. 新形态发现（未知序列聚类）

无候选新形态（未知序列未达 3 个相似图形，继续观察）。

未知序列清单（9 条）：
- 2026-08-07_lol-hle-drxc/moneyline_hle_price_1m（pre 0.285 / end 0.395 / low 0.055 / x50 2）
- cs2-eye-pha-2026-08-08/moneyline_eyeballers_price_1m（pre 0.715 / end 0.495 / low 0.47 / x50 3）
- cs2-shu1-nrg-2026-08-07/cs2-shu1-nrg-2026-08-07_nrg_price_1min（pre 0.93 / end 0.513 / low 0.513 / x50 0）
- cs2-shu1-nrg-2026-08-07/cs2-shu1-nrg-2026-08-07_spirit_hu_price_1min（pre 0.07 / end 0.486 / low 0.0005 / x50 0）
- dota2-pr1-mouz-2026-08-10/moneyline_mouz_price_1m（pre 0.59 / end 0.835 / low 0.11 / x50 6）
- lol-drxc-foxy-2026-08-11/moneyline_drxc_price_1m（pre 0.605 / end 0.565 / low 0.495 / x50 2）
- lol-sk-navi-2026-08-08/moneyline_natus_vincere_price_1m（pre 0.635 / end 0.585 / low 0.585 / x50 0）
- lol-sk-navi-2026-08-08/moneyline_sk_gaming_price_1m（pre 0.365 / end 0.415 / low 0.105 / x50 0）
- lol-t1-hle1-2026-08-08/moneyline_t1_price_1m（pre 0.455 / end 0.475 / low 0.385 / x50 6）

## 3. 结论与建议

- 样本仍不足以对单形态下统计结论（目标 >=10/形态），继续每 2-3 天巡检累计。
- 新形态候选按 REVERSAL_PATTERN_LIBRARY 三.6 流程登记（图形 -> 观察池 -> 回测 -> 入库）。
