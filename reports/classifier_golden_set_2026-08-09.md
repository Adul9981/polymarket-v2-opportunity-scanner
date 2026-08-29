# 形态分类器 Golden Set（人工复核标准集）

生成时间：2026-08-09T15:04:48.150081+00:00

序列数：72。复核流程：逐行确认 labels 是否符合形态定义；确认后把
review_status 改为 已复核，labels 有异议的在 note 里写修正建议。

## 标签频率

- B4_直线阴跌: 32
- A2_中位U型反转: 12
- A3_折价修复: 11
- 未知: 10
- 热门全程压制: 8
- A1_V型极值反转: 5
- A6_反弹确认: 4
- A4_下狗整场反转: 4
- B2_死亡螺旋: 4
- A5_W型双底: 2
- C2_五五开开局碾压: 2

## 逐序列

| 快照 | 序列 | 标签 | 低点 | 高点 | 低点时间 | 复核状态 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-05_cs2-tl1-fnc | game1_fnatic_price_5m.jsonl | B4_直线阴跌 | 0.0005 | 0.83 | 13:50 | 待复核 |  |
| 2026-08-05_cs2-tl1-fnc | game1_liquid_price_5m.jsonl | A2_中位U型反转 | 0.165 | 0.9995 | 13:25 | 待复核 |  |
| 2026-08-05_cs2-tl1-fnc | game2_fnatic_price_5m.jsonl | B4_直线阴跌 | 0.0005 | 0.445 | 14:40 | 待复核 |  |
| 2026-08-05_cs2-tl1-fnc | game2_liquid_price_5m.jsonl | A3_折价修复/热门全程压制 | 0.55 | 0.9995 | 14:05 | 待复核 |  |
| 2026-08-05_cs2-tl1-fnc | moneyline_fnatic_price_5m.jsonl | B4_直线阴跌 | 0.0005 | 0.495 | 14:35 | 待复核 |  |
| 2026-08-05_cs2-tl1-fnc | moneyline_liquid_price_5m.jsonl | A3_折价修复 | 0.505 | 0.9995 | 13:25 | 待复核 |  |
| 2026-08-06_lol-we-al | game1_we_price_1m.jsonl | A1_V型极值反转 | 0.065 | 0.9995 | 13:58 | 待复核 |  |
| 2026-08-06_lol-we-al | game2_we_price_1m.jsonl | A1_V型极值反转/A6_反弹确认 | 0.0065 | 0.9995 | 15:16 | 待复核 |  |
| 2026-08-06_lol-we-al | moneyline_we_price_1m.jsonl | A2_中位U型反转/A4_下狗整场反转 | 0.135 | 0.9995 | 13:57 | 待复核 |  |
| 2026-08-07_lol-blg-tes | game1_blg_price_1m.jsonl | B2_死亡螺旋/B4_直线阴跌 | 0.0005 | 0.955 | 13:32 | 待复核 |  |
| 2026-08-07_lol-blg-tes | game1_tes_price_1m.jsonl | A1_V型极值反转/A6_反弹确认 | 0.045 | 0.9995 | 13:11 | 待复核 |  |
| 2026-08-07_lol-blg-tes | game2_blg_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.655 | 14:18 | 待复核 |  |
| 2026-08-07_lol-blg-tes | game2_tes_price_1m.jsonl | A2_中位U型反转 | 0.345 | 0.9995 | 15:24 | 待复核 |  |
| 2026-08-07_lol-blg-tes | moneyline_blg_price_1m.jsonl | B2_死亡螺旋/B4_直线阴跌 | 0.0005 | 0.855 | 14:18 | 待复核 |  |
| 2026-08-07_lol-blg-tes | moneyline_tes_price_1m.jsonl | A2_中位U型反转/A4_下狗整场反转 | 0.145 | 0.9995 | 13:12 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | game1_bfx_price_1m.jsonl | B2_死亡螺旋/B4_直线阴跌 | 0.0005 | 0.985 | 10:51 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | game1_bro_price_1m.jsonl | A1_V型极值反转/A6_反弹确认 | 0.015 | 0.9995 | 10:49 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | game2_bfx_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.595 | 11:49 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | game2_bro_price_1m.jsonl | 未知 | 0.405 | 0.9995 | 17:09 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | moneyline_bfx_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.785 | 11:49 | 待复核 |  |
| 2026-08-07_lol-fox1-bro2 | moneyline_bro_price_1m.jsonl | A2_中位U型反转/A4_下狗整场反转 | 0.215 | 0.9995 | 10:46 | 待复核 |  |
| 2026-08-07_lol-hle-drxc | game1_hle_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.545 | 05:37 | 待复核 |  |
| 2026-08-07_lol-hle-drxc | game2_hle_price_1m.jsonl | A2_中位U型反转/A5_W型双底 | 0.165 | 0.9995 | 06:01 | 待复核 |  |
| 2026-08-07_lol-hle-drxc | moneyline_hle_price_1m.jsonl | 未知 | 0.055 | 0.865 | 06:14 | 待复核 |  |
| 2026-08-07_lol-we-tt | game1_tt_price_1m.jsonl | A2_中位U型反转 | 0.325 | 0.9995 | 09:31 | 待复核 |  |
| 2026-08-07_lol-we-tt | game1_we_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.675 | 10:11 | 待复核 |  |
| 2026-08-07_lol-we-tt | moneyline_tt_price_1m.jsonl | A2_中位U型反转/A4_下狗整场反转 | 0.275 | 0.9995 | 09:31 | 待复核 |  |
| 2026-08-07_lol-we-tt | moneyline_we_price_1m.jsonl | B4_直线阴跌 | 0.0005 | 0.725 | 12:07 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | cs2-ace1-van1-2026-08-07_acend_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.595 | 0.9995 | 06:29 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | cs2-ace1-van1-2026-08-07_vandulken_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.405 | 17:42 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | game1_acend_price_1min.jsonl | 未知 | 0.465 | 0.9995 | 06:26 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | game1_vandulken_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.535 | 16:59 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | game2_acend_price_1min.jsonl | 未知 | 0.485 | 0.9995 | 06:26 | 待复核 |  |
| cs2-ace1-van1-2026-08-07 | game2_vandulken_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.515 | 17:42 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | cs2-fokus-par3-2026-08-07_fokus_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.695 | 0.9995 | 17:10 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | cs2-fokus-par3-2026-08-07_partizan_esport_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.305 | 18:10 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | game1_fokus_price_1min.jsonl | A1_V型极值反转/A6_反弹确认 | 0.09 | 0.9995 | 17:14 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | game1_partizan_esport_price_1min.jsonl | B2_死亡螺旋/B4_直线阴跌 | 0.0005 | 0.855 | 17:26 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | game2_fokus_price_1min.jsonl | A3_折价修复 | 0.465 | 0.9995 | 16:19 | 待复核 |  |
| cs2-fokus-par3-2026-08-07 | game2_partizan_esport_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.535 | 18:15 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | cs2-lone-pha-2026-08-07_levelone_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.225 | 17:40 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | cs2-lone-pha-2026-08-07_phantom_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.775 | 0.9995 | 06:26 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | game1_levelone_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.44 | 16:51 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | game1_phantom_price_1min.jsonl | 未知 | 0.565 | 0.9995 | 06:26 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | game2_levelone_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.505 | 17:41 | 待复核 |  |
| cs2-lone-pha-2026-08-07 | game2_phantom_price_1min.jsonl | A3_折价修复 | 0.495 | 0.9995 | 16:03 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | cs2-shu1-nrg-2026-08-07_nrg_price_1min.jsonl | 未知 | 0.513 | 0.9995 | 19:46 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | cs2-shu1-nrg-2026-08-07_spirit_hu_price_1min.jsonl | 未知 | 0.0005 | 0.486 | 17:44 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | game1_nrg_price_1min.jsonl | C2_五五开开局碾压 | 0.44 | 0.9995 | 13:54 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | game1_spirit_hu_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.56 | 17:09 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | game2_nrg_price_1min.jsonl | C2_五五开开局碾压/A5_W型双底 | 0.45 | 0.9995 | 16:00 | 待复核 |  |
| cs2-shu1-nrg-2026-08-07 | game2_spirit_hu_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.535 | 17:44 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | cs2-vael-og1-2026-08-07_og_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.775 | 0.9995 | 06:21 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | cs2-vael-og1-2026-08-07_vael_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.225 | 17:44 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | game1_og_price_1min.jsonl | 未知 | 0.49 | 0.9995 | 15:38 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | game1_vael_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.51 | 17:02 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | game2_og_price_1min.jsonl | 未知 | 0.48 | 0.9995 | 15:37 | 待复核 |  |
| cs2-vael-og1-2026-08-07 | game2_vael_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.52 | 17:45 | 待复核 |  |
| lol-cfo-gz-2026-08-09 | game3_cfo_price_1m.jsonl | A2_中位U型反转 | 0.35 | 0.925 | 19:27 | 待复核 |  |
| lol-cfo-gz-2026-08-09 | game2_cfo_price_1m.jsonl | A2_中位U型反转 | 0.245 | 1.0 | 18:54 | 待复核 |  |
| lol-dk-kt-2026-08-09 | game2_dk_price_1m.jsonl | A2_中位U型反转 | 0.37 | 1.0 | 17:13 | 待复核 |  |
| lol-dk-kt-2026-08-09 | moneyline_dk_price_1m.jsonl | A2_中位U型反转 | 0.235 | 0.985 | 17:13 | 待复核 |  |
| lol-dk-kt-2026-08-09 | game1_dk_price_1m.jsonl | B4_直线阴跌 | 0.001 | 0.585 | 16:34 | 待复核 |  |
| lol-fox1-drx-2026-08-09 | game2_drx_price_1m.jsonl | B4_直线阴跌 | 0.001 | 0.615 | 20:36 | 待复核 |  |
| lol-fox1-drx-2026-08-09 | moneyline_drx_price_1m.jsonl | B4_直线阴跌 | 0.001 | 0.565 | 20:36 | 待复核 |  |
| lol-fox1-drx-2026-08-09 | handicap_drx_plus1_5_price_1m.jsonl | B4_直线阴跌 | 0.001 | 0.785 | 20:36 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | game1_edward_gaming_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.285 | 08:08 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | game1_jd_gaming_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.715 | 0.9995 | 06:22 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | game2_edward_gaming_price_1min.jsonl | B4_直线阴跌 | 0.0005 | 0.275 | 09:07 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | game2_jd_gaming_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.725 | 0.9995 | 06:21 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | moneyline_edward_gaming_price_1min.jsonl | 未知 | 0.0005 | 0.18 | 09:03 | 待复核 |  |
| lol-jdg-edg-2026-08-07 | moneyline_jd_gaming_price_1min.jsonl | A3_折价修复/热门全程压制 | 0.82 | 0.9995 | 07:56 | 待复核 |  |
