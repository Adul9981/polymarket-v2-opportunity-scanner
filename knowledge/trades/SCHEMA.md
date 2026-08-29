# 结构化交易数据 Schema

每个文件 = 一个交易日的一组交易记录（JSON 数组）。

## 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| date | string | 交易日期 YYYY-MM-DD |
| event_slug | string | Polymarket 事件 slug |
| market_type | string | game1 / game2 / game3 / match |
| side | string | 买入方向（正式 outcome 名称） |
| strategy | string | S1/A、S2/B、S3/C、swing、hedge、conviction、legacy_manual 等 |
| template | string | 执行模板：A / B / C / none |
| total_invested_usd | number | 总投入（已成交部分） |
| realized_pnl_usd | number | 已实现盈亏 |
| final_pnl_usd | number | 最终盈亏（含结算） |
| outcome | string | win / loss / breakeven |
| exit_executed | boolean | 是否按计划执行了止盈/止损退出 |
| lesson_tags | array | 教训标签（见下） |
| notes | string | 备注；含「估值」字样表示数字为近似值 |

## 教训标签词表

```text
direction_miss        方向选错（应选另一侧深反）
grid_ok               网格执行正确
insurance_cost        对冲保险费
conviction_ok         高信心判断正确
tp_ladder_ok          分档止盈执行正确
dip_add_ok            低吸补仓正确
comeback_ok           翻盘行情吃满
no_lottery            止盈覆盖 100% 未留彩票仓
pre_position_ok       赛前小仓正确
roll_down_ok          高位卖出低位接回降成本
small_high_tp_ok      小仓高止盈正确
moneyline_ok          系列胜者市场操作正确
chased_high           高位追买
caught_falling_knife  低吸档接飞刀
cut_bottom            急跌市价割在最低点
tp_early              止盈过早丢大肉
cut_loss_executed     止损执行（正面纪律）
heavy_pre             赛前重仓（偏激进）
first_game_overfit    基于前一场表现过度外推
partial_tp_then_zero  部分止盈后剩余归零
market_mismatch       市场理解错误（Game 1 vs 整场）
data_source_issue     行情数据源滞后/异常
legacy_unprotected    老仓无保护
high_cost_entry       高成本入场
```

## 使用

后续进化分析（胜率、按模板/策略分组、亏损模式）建议用脚本读 JSON，例如：

```text
python3 -c "import json; d=json.load(open('knowledge/trades/2026-08-04_trades.json')); print(sum(1 for x in d if x['outcome']=='win'), len(d))"
```
