# 情报页【比赛局势】实时刷新部署（按小局：局内实时、局末冻结 + 评分赛后回填）

在 VPS（`/opt/danmu-intel`）上每 60s 跑一次 `tools/refresh_situation.py --once`，对
**未结算且已生成小局节点**的比赛，逐小局刷新节点页【比赛局势】栏：

- **当前小局**（进行中，end 尚未生成）：胜率 = 本小局切片 `[本局起点 -> 现在]` 重算
  （近 5 分钟口径，样本不足回退整场累积）；评分 = `fetch_ratings(mid, gi)` 本小局
  `strict_game`，不串局；作用于 bp/mid 页。
- **已结束小局**（end 已生成）：胜率**严格冻结**；评分在 end 生成后 30 分钟内持续
  回填（虎扑评分赛后陆续上线，评分数一出来就补上），作用于 bp/mid/end 页；超时全冻结。

只改 `reports/` 本地 HTML，发布仍由 `vps_publish` 定时器负责（本服务不做 git）。

## 安装

```bash
sudo cp refresh-situation.service refresh-situation.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now refresh-situation.timer
sudo systemctl status refresh-situation.timer
```

## 依赖

- `/opt/danmu-intel/tools/refresh_situation.py`（已随 tools/ 同步）
- 可读 `data/matches_today.json`、`docs/data/danmu/<game>/` 弹幕、`reports/` 节点页
- 联网拉虎扑评分（失败静默沿用旧评分，不覆盖）
