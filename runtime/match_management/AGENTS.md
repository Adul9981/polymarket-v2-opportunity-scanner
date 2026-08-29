# runtime/match_management/ 模块规则

职责：每场比赛一张状态卡（runtime/match_management/<slug>.json），记录系列赛进度与
本会话对该场比赛的挂单状态标识，供复盘、验收和新会话快速对齐。

## 状态标识（简单枚举）

game_status（单局）：
- not_started 未开始
- live 进行中
- finished 已结束

order_status（本会话对这场比赛的挂单/交易状态）：
- none 未关注/未操作
- no_opportunity 没给机会（全程无信号/未进入场区）
- planned 已生成待确认计划（dry-run，未碰钱）
- cancelled 计划已取消
- placed 已挂单（未成交）
- filled 已成交
- closed 挂单/仓位已结束

## 约定

- 一律用 tools/match_manager.py 读写，不手改 JSON。
- 一场比赛结束后（或会话结束时）补记：进行到第几局、系列赛比分、各局挂单状态。
- 状态卡是轻量标识，不替代 runtime/bar_monitor_state/ 的引擎状态与 actions 日志；
  需要细节时去查对应状态文件和日志。
- 比赛结果以盘口结算为准，未知时 series_finished 保持 false 并注明"待确认"。

用法：

```bash
python3 tools/match_manager.py init --slug <slug> --title "..." --league LPL --bo 3 --date 2026-08-09
python3 tools/match_manager.py record --slug <slug> --game 1 --game-status finished --winner IG --order-status no_opportunity --note "..."
python3 tools/match_manager.py series --slug <slug> --score "IG 2-0 LNG" --finished
python3 tools/match_manager.py show --slug <slug>
python3 tools/match_manager.py list
```
