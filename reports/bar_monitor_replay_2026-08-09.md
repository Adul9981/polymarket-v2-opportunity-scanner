# Bar 监控历史回放验证

生成时间：2026-08-09T04:45:30.753486+00:00

数据源：/Users/ad/Documents/polymarket/docs/data/snapshots，共 47 条 1 分钟序列，策略 2 组，滚动窗口回放（fills + D3 状态机累计）。

## 信号汇总（按策略）

### A_DEEP_REVERSAL

- single_bar_rally: 4
- rebound_confirmed: 7
- place_buy: 197
- estimated_fill: 50
- d2_trailing_active: 2
- d3_stop_triggered: 6
- stop_new_entry: 19
- re_entry_eval: 4

### B_FAVORITE_DIP

- single_bar_rally: 3
- rebound_confirmed: 5
- place_buy: 438
- estimated_fill: 240
- d2_trailing_active: 16
- d3_stop_triggered: 18
- stop_new_entry: 3271
- switch_to_s1_eval: 3271
- re_entry_eval: 99

## 逐序列明细

| 快照 | 序列 | 策略 | 触发动作 | 形态标签 |
| --- | --- | --- | --- | --- |
| 2026-08-06_lol-we-al | game1_we_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/single_bar_rally/rebound_confirmed/place_take_profit/d2_profit_lock_zone/d2_trailing_active/d3_stop_triggered/no_entry_high | - |
| 2026-08-06_lol-we-al | game1_we_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/single_bar_rally/rebound_confirmed/place_take_profit/d2_profit_lock_zone/d2_trailing_active/place_buy/d3_stop_triggered/re_entry_eval/no_entry_high | - |
| 2026-08-06_lol-we-al | game2_we_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/single_bar_rally/no_entry_high | - |
| 2026-08-06_lol-we-al | game2_we_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy/no_entry_high | - |
| 2026-08-06_lol-we-al | moneyline_we_price_1m | A_DEEP_REVERSAL | place_buy/no_entry_high | - |
| 2026-08-06_lol-we-al | moneyline_we_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy/estimated_fill/no_entry_high | - |
| 2026-08-07_lol-blg-tes | game1_blg_price_1m | A_DEEP_REVERSAL | no_entry_high/stop_new_entry | - |
| 2026-08-07_lol-blg-tes | game1_blg_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-blg-tes | game1_tes_price_1m | A_DEEP_REVERSAL | place_buy/rebound_confirmed/single_bar_rally/no_entry_high | - |
| 2026-08-07_lol-blg-tes | game1_tes_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/single_bar_rally/rebound_confirmed/no_entry_high | - |
| 2026-08-07_lol-blg-tes | game2_blg_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/stop_new_entry | - |
| 2026-08-07_lol-blg-tes | game2_blg_price_1m | B_FAVORITE_DIP | place_take_profit/d2_profit_lock_zone/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-blg-tes | game2_tes_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-blg-tes | game2_tes_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/place_take_profit/d2_profit_lock_zone/d2_trailing_active/no_entry_high | - |
| 2026-08-07_lol-blg-tes | moneyline_blg_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/d3_stop_triggered/stop_new_entry | - |
| 2026-08-07_lol-blg-tes | moneyline_blg_price_1m | B_FAVORITE_DIP | place_take_profit/d2_profit_lock_zone/d2_trailing_active/d3_stop_triggered/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-blg-tes | moneyline_tes_price_1m | A_DEEP_REVERSAL | place_buy/no_entry_high | - |
| 2026-08-07_lol-blg-tes | moneyline_tes_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | game1_bfx_price_1m | A_DEEP_REVERSAL | no_entry_high/stop_new_entry | - |
| 2026-08-07_lol-fox1-bro2 | game1_bfx_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-fox1-bro2 | game1_bro_price_1m | A_DEEP_REVERSAL | place_buy/no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | game1_bro_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval/estimated_fill/no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | game2_bfx_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/stop_new_entry | - |
| 2026-08-07_lol-fox1-bro2 | game2_bfx_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-fox1-bro2 | game2_bro_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | game2_bro_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/place_take_profit/d2_profit_lock_zone/d2_trailing_active/no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | moneyline_bfx_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/stop_new_entry | - |
| 2026-08-07_lol-fox1-bro2 | moneyline_bfx_price_1m | B_FAVORITE_DIP | place_take_profit/d2_profit_lock_zone/d2_trailing_active/d3_stop_triggered/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-fox1-bro2 | moneyline_bro_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-fox1-bro2 | moneyline_bro_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval/estimated_fill/d3_stop_triggered/place_take_profit/d2_profit_lock_zone/d2_trailing_active/no_entry_high | - |
| 2026-08-07_lol-hle-drxc | game1_hle_price_1m | A_DEEP_REVERSAL | stop_new_entry | - |
| 2026-08-07_lol-hle-drxc | game1_hle_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy | - |
| 2026-08-07_lol-hle-drxc | game2_hle_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-hle-drxc | game2_hle_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| 2026-08-07_lol-hle-drxc | moneyline_hle_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/rebound_confirmed/place_take_profit/d2_profit_lock_zone/d2_trailing_active/d3_stop_triggered | - |
| 2026-08-07_lol-hle-drxc | moneyline_hle_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/re_entry_eval/place_take_profit/d2_profit_lock_zone/d2_trailing_active/d3_stop_triggered | - |
| 2026-08-07_lol-we-tt | game1_tt_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-we-tt | game1_tt_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| 2026-08-07_lol-we-tt | game1_we_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/stop_new_entry | - |
| 2026-08-07_lol-we-tt | game1_we_price_1m | B_FAVORITE_DIP | place_take_profit/d2_profit_lock_zone/place_buy/stop_new_entry/switch_to_s1_eval | - |
| 2026-08-07_lol-we-tt | moneyline_tt_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| 2026-08-07_lol-we-tt | moneyline_tt_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy/no_entry_high | - |
| 2026-08-07_lol-we-tt | moneyline_we_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/rebound_confirmed/stop_new_entry | - |
| 2026-08-07_lol-we-tt | moneyline_we_price_1m | B_FAVORITE_DIP | place_take_profit/d2_profit_lock_zone/place_buy/estimated_fill/stop_new_entry/switch_to_s1_eval/rebound_confirmed | - |
| cs2-eye-pha-2026-08-08 | map1_eyeballers_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| cs2-eye-pha-2026-08-08 | map1_eyeballers_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/d2_profit_lock_zone/re_entry_eval/place_take_profit/d2_trailing_active/no_entry_high | - |
| cs2-eye-pha-2026-08-08 | map1_phantom_price_1m | A_DEEP_REVERSAL | place_buy/stop_new_entry | - |
| cs2-eye-pha-2026-08-08 | map1_phantom_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/stop_new_entry/switch_to_s1_eval | - |
| cs2-eye-pha-2026-08-08 | map2_eyeballers_price_1m | A_DEEP_REVERSAL | stop_new_entry | - |
| cs2-eye-pha-2026-08-08 | map2_eyeballers_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/stop_new_entry/switch_to_s1_eval/place_take_profit/d2_profit_lock_zone/d2_trailing_active | - |
| cs2-eye-pha-2026-08-08 | map2_phantom_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| cs2-eye-pha-2026-08-08 | map2_phantom_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/d2_profit_lock_zone/place_take_profit/stop_new_entry/switch_to_s1_eval/d2_trailing_active/no_entry_high | - |
| cs2-eye-pha-2026-08-08 | moneyline_eyeballers_price_1m | A_DEEP_REVERSAL | - | - |
| cs2-eye-pha-2026-08-08 | moneyline_eyeballers_price_1m | B_FAVORITE_DIP | place_buy | - |
| cs2-eye-pha-2026-08-08 | moneyline_phantom_price_1m | A_DEEP_REVERSAL | place_buy | - |
| cs2-eye-pha-2026-08-08 | moneyline_phantom_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/place_buy/estimated_fill | - |
| lol-ns-dnf-2026-08-08 | game1_dn_soopers_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/single_bar_rally/rebound_confirmed/place_take_profit/d2_profit_lock_zone/no_entry_high | - |
| lol-ns-dnf-2026-08-08 | game1_dn_soopers_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/single_bar_rally/rebound_confirmed/place_take_profit/d2_profit_lock_zone/no_entry_high | - |
| lol-ns-dnf-2026-08-08 | game1_nongshim_red_force_price_1m | A_DEEP_REVERSAL | no_entry_high/stop_new_entry | - |
| lol-ns-dnf-2026-08-08 | game1_nongshim_red_force_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval | - |
| lol-ns-dnf-2026-08-08 | game2_dn_soopers_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| lol-ns-dnf-2026-08-08 | game2_dn_soopers_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| lol-ns-dnf-2026-08-08 | game2_nongshim_red_force_price_1m | A_DEEP_REVERSAL | place_buy/stop_new_entry | - |
| lol-ns-dnf-2026-08-08 | game2_nongshim_red_force_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval | - |
| lol-ns-dnf-2026-08-08 | handicap_ns15_nongshim_red_force_price_1m | A_DEEP_REVERSAL | stop_new_entry | - |
| lol-ns-dnf-2026-08-08 | handicap_ns15_nongshim_red_force_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval | - |
| lol-ns-dnf-2026-08-08 | moneyline_dn_soopers_price_1m | A_DEEP_REVERSAL | place_buy/no_entry_high | - |
| lol-ns-dnf-2026-08-08 | moneyline_dn_soopers_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| lol-ns-dnf-2026-08-08 | moneyline_nongshim_red_force_price_1m | A_DEEP_REVERSAL | place_buy/stop_new_entry | - |
| lol-ns-dnf-2026-08-08 | moneyline_nongshim_red_force_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/stop_new_entry/switch_to_s1_eval | - |
| lol-sk-navi-2026-08-08 | game1_natus_vincere_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| lol-sk-navi-2026-08-08 | game1_natus_vincere_price_1m | B_FAVORITE_DIP | no_entry_high | - |
| lol-sk-navi-2026-08-08 | game1_sk_gaming_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/stop_new_entry | - |
| lol-sk-navi-2026-08-08 | game1_sk_gaming_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval | - |
| lol-sk-navi-2026-08-08 | game2_natus_vincere_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/stop_new_entry | - |
| lol-sk-navi-2026-08-08 | game2_natus_vincere_price_1m | B_FAVORITE_DIP | d2_profit_lock_zone/place_take_profit/d2_trailing_active/place_buy/d3_stop_triggered/re_entry_eval/stop_new_entry/switch_to_s1_eval | - |
| lol-sk-navi-2026-08-08 | game2_sk_gaming_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| lol-sk-navi-2026-08-08 | game2_sk_gaming_price_1m | B_FAVORITE_DIP | place_buy/stop_new_entry/switch_to_s1_eval/no_entry_high | - |
| lol-sk-navi-2026-08-08 | moneyline_natus_vincere_price_1m | A_DEEP_REVERSAL | - | - |
| lol-sk-navi-2026-08-08 | moneyline_natus_vincere_price_1m | B_FAVORITE_DIP | - | - |
| lol-sk-navi-2026-08-08 | moneyline_sk_gaming_price_1m | A_DEEP_REVERSAL | place_buy | - |
| lol-sk-navi-2026-08-08 | moneyline_sk_gaming_price_1m | B_FAVORITE_DIP | stop_new_entry/switch_to_s1_eval | - |
| lol-t1-hle1-2026-08-08 | game1_hle_price_1m | A_DEEP_REVERSAL | place_buy/estimated_fill/stop_new_entry | - |
| lol-t1-hle1-2026-08-08 | game1_hle_price_1m | B_FAVORITE_DIP | d2_profit_lock_zone/stop_new_entry/switch_to_s1_eval | - |
| lol-t1-hle1-2026-08-08 | game1_t1_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| lol-t1-hle1-2026-08-08 | game1_t1_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d3_stop_triggered/re_entry_eval/d2_profit_lock_zone/place_take_profit/d2_trailing_active/no_entry_high | - |
| lol-t1-hle1-2026-08-08 | game2_hle_price_1m | A_DEEP_REVERSAL | no_entry_high | - |
| lol-t1-hle1-2026-08-08 | game2_hle_price_1m | B_FAVORITE_DIP | no_entry_high | - |
| lol-t1-hle1-2026-08-08 | game2_t1_price_1m | A_DEEP_REVERSAL | stop_new_entry | - |
| lol-t1-hle1-2026-08-08 | game2_t1_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/stop_new_entry/switch_to_s1_eval | - |
| lol-t1-hle1-2026-08-08 | moneyline_hle_price_1m | A_DEEP_REVERSAL | - | - |
| lol-t1-hle1-2026-08-08 | moneyline_hle_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/stop_new_entry/switch_to_s1_eval | - |
| lol-t1-hle1-2026-08-08 | moneyline_t1_price_1m | A_DEEP_REVERSAL | - | - |
| lol-t1-hle1-2026-08-08 | moneyline_t1_price_1m | B_FAVORITE_DIP | place_buy/estimated_fill/d2_profit_lock_zone/place_take_profit | - |

