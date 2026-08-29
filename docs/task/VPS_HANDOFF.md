# VPS 弹幕采集交接清单（临时过渡方案）

> 当前阶段（生效中）：VPS 只做 **7×24 弹幕抓取**，分析 / 情报 / 发布全部留在本地。
> 你负责：VPS 购买、环境、采集常驻、数据回传；本地负责：分析、情报、历史库、站点。
> 数据流：VPS 弹幕 JSONL →（同步回本地）→ 本地分析 → 站点发布。

## 0. 过渡方案总览（先看这里）

```text
VPS（7×24）：danmu-session.service 常驻采集
  -> 弹幕按天落盘 /opt/danmu-intel/docs/data/danmu/<平台>/<日期>_<直播间>.jsonl
本地：每日（或比赛日）把 VPS 的 JSONL 拉回来
  -> 放 /Users/ad/Documents/polymarket/docs/data/danmu/（路径与 VPS 一致）
  -> 本地分析链：切片 -> 提炼 -> 情报页 -> 结构化库 -> 历史库 -> 站点发布
```

## 1. 分工边界

```text
你（朋友）：购买 VPS、装环境、解压部署包、启用采集服务、每天把数据同步回本地。
本地（Agent）：弹幕分析、情报页、历史库、市场链接、站点发布。
用户：QQ/TG 登记与收款、推广。
```

## 2. VPS 选购建议

```text
规格：2 核 / 2GB 内存 / 40GB SSD 起步（轻量即可，月费约 $5-10 或国内轻量同档）。
网络：需要访问虎牙（国内）。香港 / 东京轻量 VPS 优先（顺带可访问 Polymarket）。
系统：Ubuntu 22.04 LTS。
安全：SSH 密钥登录、关密码、开防火墙（22 按需）。
```

## 3. 环境准备（一次性）

```bash
# Ubuntu 22.04
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip curl jq
sudo mkdir -p /opt/danmu-intel
cd /opt/danmu-intel
# 把部署包上传并解压到当前目录（或 git clone 部署包仓库）
unzip danmu_intel_vps_deploy.zip
chmod +x deploy.sh
./deploy.sh
```

`deploy.sh` 已按过渡方案配置：装依赖、建常驻服务，**只启用采集**。

## 4. 采集服务（只跑这一个）

```text
服务名：danmu-session.service
入口：tools/vps_capture.py（读 knowledge/streamer_registry.json 直播间清单，自动启动采集）
行为：
  1) 清单内 11 个直播间（虎牙英雄联盟官方 / 957 / 毛毛 / 米勒 / 记得 / 硕硕
     + SOOP LCK CL + CSBOY×2 + TI×2），未开播直播间自动重试不影响其他房间；
  2) 每个直播间独立 JSONL + 断线自动重连；
  3) 跨天自动滚动：每天 00:00 后新弹幕落到新日期文件，不会混到前一天；
  4) systemd 开机自启 + 异常自动重启（Restart=always）。
落盘：/opt/danmu-intel/docs/data/danmu/<平台>/<日期>_<直播间>.jsonl
     例：/opt/danmu-intel/docs/data/danmu/huya/2026-08-24_we957.jsonl
```

检查是否跑起来：

```bash
systemctl status danmu-session.service
tail -20 /opt/danmu-intel/logs/danmu-session.log
find /opt/danmu-intel/docs/data/danmu -name "*.jsonl" | head
```

> 注意：过渡期**不要**启用 daily-scan.timer / site-publish.timer（本地负责发布，
> 避免两边同时写站点冲突）。等第二阶段再启用。

## 5. 数据回传（VPS → 本地，每天一次）

推荐走 Tailscale（两边装好、同一网络后，像局域网一样用）：

```bash
# 本地 Mac 上执行（VPS 已加入 tailnet，假设 VPS 地址为 100.x.x.x）
rsync -av --ignore-existing \
  100.x.x.x:/opt/danmu-intel/docs/data/danmu/ \
  /Users/ad/Documents/polymarket/docs/data/danmu/
```

没有 Tailscale 就用 scp 简单拉取：

```bash
scp -r user@VPS:/opt/danmu-intel/docs/data/danmu/* \
  /Users/ad/Documents/polymarket/docs/data/danmu/
```

要点：

```text
1) 目录与文件名保持和 VPS 一致（docs/data/danmu/<平台>/<日期>_<直播间>.jsonl），
   拉到本地后可直接进分析链，无需改名；
2) --ignore-existing 避免覆盖本地已有文件（弹幕只增不改）；
3) 频率：每天一次即可；比赛日建议比赛结束或次日早上拉一次。
```

## 6. 健康检查（每天瞄一眼）

```bash
# 弹幕在涨吗（条数持续增长 = 正常）
wc -l /opt/danmu-intel/docs/data/danmu/*/*.jsonl
tail -3 /opt/danmu-intel/docs/data/danmu/*/*.jsonl
# 服务活着吗
systemctl --no-pager status danmu-session.service
# 出问题看日志
tail -50 /opt/danmu-intel/logs/danmu-session.err
```

## 7. 交接检查单（过渡方案）

```text
□ VPS 已购买（香港/东京优先），SSH 密钥登录已开
□ 部署包解压到 /opt/danmu-intel，deploy.sh 跑完无报错
□ danmu-session.service 已启用并处于 active (running)
□ 有直播间开播时，docs/data/danmu/ 下 JSONL 条数持续增长
□ Tailscale 已连通（或 scp 可用），本地能拉到数据
□ 出问题知道看 /opt/danmu-intel/logs/danmu-session.{log,err}
```

## 8. 本地分析入口（给 Agent / 用户，朋友不用管）

```text
数据落位：docs/data/danmu/
分析流程：knowledge/DANMU_WORKFLOW.md 五阶段
  （准备 -> 启动/回传 -> 切片 slice_danmu_by_match -> 提炼 danmu_intel
    -> 情报 HTML -> 结构化库 -> 历史库 -> 站点发布）
```

## 9. 第二阶段（后续，第一版跑稳后再做）

```text
1. 采集 + 分析 + 发布逐步全部搬到 VPS（启用 daily-scan / site-publish）；
2. 实时情报页与节点时间轴在线上自动产出；
3. 付费墙（访问码 / QQ / TG 登记）。
```
