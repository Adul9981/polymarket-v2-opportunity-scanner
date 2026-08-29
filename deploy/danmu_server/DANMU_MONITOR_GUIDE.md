# 弹幕监控 7×24 服务器 · 部署与维护说明

> 给服务器运维/朋友的使用手册。软件和脚本已经给你了，这份文档补齐"监控哪些直播间、
> 比赛怎么对应、脚本怎么用、出问题怎么查"的完整说明。
> 项目根目录：`/Users/ad/Documents/polymarket`（本地）；服务器部署包：`deploy/danmu_server/`。

## 一、这套东西在做什么

```
服务器（7×24）               本地电脑（分析）
虎牙/SOOP 弹幕抓取   ──同步──▶  弹幕 JSONL → 情报分析 → HTML 情报页
只采集、只落盘，不分析           比赛登记 / 结果校验 / 情报库沉淀
```

- 服务器只负责"在场"：7×24 抓弹幕、按北京时间命名落盘、断线自动重连。
- 分析全部在本地做（Agent 情报流水线），服务器不跑分析，省资源、省心。
- 弹幕是原始语料，不对外裸展示用户身份；只做聚合情报与统计。

## 二、已经给你的东西

| 文件 | 作用 |
| --- | --- |
| `deploy/danmu_server/install.sh` | 一键装依赖 + 建目录 + 拉协议库 |
| `deploy/danmu_server/capture_server.py` | 7×24 采集主程序（自动重启每个房间采集器） |
| `deploy/danmu_server/danmu-capture.service` | systemd 服务（开机自启） |
| `deploy/danmu_server/rooms.env.example` | 直播间配置模板（SOURCE=URL） |
| `deploy/danmu_server/README.md` | 服务器端 10 分钟部署步骤 |
| `tools/sync_danmu_from_server.py` | 本地拉取服务器数据的同步脚本（rsync 增量） |
| `config/danmu_sync.json` | 同步配置（host 填服务器 IP 即启用） |

## 三、脚本怎么用

### 3.1 服务器端（推荐，7×24 常驻）

```bash
# 1) 上传部署包到服务器
scp -r deploy/danmu_server root@你的服务器IP:/opt/danmu-pkg

# 2) 登录服务器，安装
ssh root@你的服务器IP
cd /opt/danmu-pkg && bash install.sh

# 3) 配置直播间（重点，见第四节）
cp rooms.env.example rooms.env
vim rooms.env     # 把 ROOMS 改成你要抓的房间

# 4) 启动常驻服务
cp danmu-capture.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now danmu-capture

# 5) 验证
systemctl status danmu-capture
ls /opt/danmu/docs/data/danmu/huya/          # 应出现 YYYY-MM-DD_来源.jsonl
tail -3 /opt/danmu/docs/data/danmu/huya/$(date +%F)_official_660000.jsonl
```

换直播间：改 `rooms.env` 后 `systemctl restart danmu-capture`。
看日志：`journalctl -u danmu-capture -f`。

### 3.2 本地临时采集（调试/开发用）

```bash
python3 tools/run_danmu_session.py \
  --session lpl_2026-08-25 \
  --room official_660000=https://www.huya.com/660000 \
  --room shuoshuo_323444=https://www.huya.com/323444
```

- `--room` 可重复，格式 `来源=URL`；`--seconds 0` = 一直抓到 Ctrl-C。
- 会话状态在 `runtime/danmu_sessions/<session>/`（session.json + 每房 status.json），自动重启断线采集器。
- 本地落盘：`docs/data/danmu/huya/YYYY-MM-DD_来源.jsonl`。

### 3.3 比赛登记与校验（本地分析端）

```bash
# 登记一场比赛的时间窗（采集与赛后切片都靠它对齐）
python3 tools/register_match.py --match-id 2026-08-25_th_gx \
  --date 2026-08-25 --teams TH,GX --start 00:00 --league LEC \
  --streams shuoshuo_323444

# 赛后结果校验（多信号 + Polymarket 结算优先）
python3 tools/verify_match_result.py --match-id <id> [--apply]
```

## 四、监控哪些直播间（重点）

所有虎牙直播间共用同一套弹幕协议，`SOURCE` 会出现在文件名里，用英文/数字/下划线。

| SOURCE（文件名前缀） | 直播间 | 房间号 / URL | 平台 | 监控赛事 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `official_660000` | 虎牙英雄联盟赛事 | 660000 · huya.com/660000 | 虎牙 | LPL / 官方赛事 | 关键（大样本） |
| `we957_890001` | 957（WE957） | 890001 · huya.com/890001 | 虎牙 | LPL / LCK / MSI / 世界赛 | 首选 |
| `shuoshuo_323444` | 解说硕硕 | 323444 · huya.com/323444 | 虎牙 | LPL / LCK / LEC / T1 主题 | 中 |
| `mile_149361` | 解说米勒 | 149361 · huya.com/149361 | 虎牙 | LPL / LCK / 世界赛 | 高 |
| `maomao_149346` | 解说毛毛 | 149346 · huya.com/149346 | 虎牙 | LPL / LCK / 世界赛 | 高 |
| `remember_528222` | Remember（记得） | 528222 · huya.com/rememberlol | 虎牙 | LPL / LCK / 世界赛 | 高 |
| `csboy_123321` | CSBOY 官方 | 123321 · huya.com/123321 | 虎牙 | CS2：EWC / IEM / BLAST / Major | 关键（CS 大样本） |
| `captainmo` | CSBOY-Mo | 321123 · huya.com/captainmo | 虎牙 | CS2：EWC / IEM / BLAST / Major | 高（二路交叉） |
| `ti_stage1_660118` | TI2026 舞台一 | 660118 · huya.com/660118 | 虎牙 | Dota2：TI2026 | 关键（TI 大样本） |
| `maybeee_211888` | Maybeee111 | 211888 · huya.com/211888 | 虎牙 | Dota2：TI2026 | 高（二路交叉） |
| `lck_cl_soop` | LCK CL 官方 | play.sooplive.com/afchall/296450537 | SOOP | LCK CL（二线） | 关键（韩文流互补） |

### 推荐默认配置（晚间场全开）

```bash
ROOMS="official_660000=https://www.huya.com/660000 \
we957_890001=https://www.huya.com/890001 \
shuoshuo_323444=https://www.huya.com/323444 \
csboy_123321=https://www.huya.com/123321 \
captainmo=https://www.huya.com/captainmo"
```

说明：
- 同一场比赛尽量抓 ≥2 路（官方 + 二路），结论要做交叉验证；
- LEC 夜场一般在硕硕/官方流播（凌晨 0-4 点北京时间），CS 大场在 CSBOY 两路；
- LCK CL 韩文流走 SOOP，抓取协议不同，需要时单独加（见 `tools/fetch_soop_danmu.py`）。

## 五、命名与落盘约定（别改）

```text
/opt/danmu/docs/data/danmu/huya/YYYY-MM-DD_来源.jsonl   # 虎牙，日期=北京时间
/opt/danmu/docs/data/danmu/soop/YYYY-MM-DD_来源.jsonl    # SOOP
/opt/danmu/runtime/danmu_sessions/<session>/             # 健康状态（session.json + *.status.json）
```

- JSONL 每行一条弹幕；虎牙字段 `ts / nick / text`；SOOP 字段 `ts(字符串) / nickname / message`。
- 文件名里的日期固定北京时间，脚本自动换算（服务器时区无所谓）。
- 追加写入，断线重连不丢已抓数据。

## 六、健康监控与故障排查

| 现象 | 处理 |
| --- | --- |
| 某房间弹幕 0 条 / 长时间无新数据 | 先怀疑工具：看 `journalctl -u danmu-capture -f`，确认房间是否开播，再看 status.json 心跳。禁止直接报"无弹幕" |
| 断线 | `capture_server.py` 自动 10 秒退避重启，无需人工；重启次数记录在 status.json |
| 服务器重启 | systemd 已 `enable`，开机自启 |
| 换比赛/换房间 | 改 `rooms.env` → `systemctl restart danmu-capture` |
| 本地拉取失败 | 检查 `config/danmu_sync.json` 的 host、SSH/rsync 权限、`nc -vz 服务器IP 22` |
| 多场比赛同时播 | 按比赛维度切片：`tools/slice_danmu_by_match.py`（配合 register_match 的窗口） |

健康检查建议（cron / 定时任务）：
```bash
# status.json 心跳超过 10 分钟未更新 → 告警
python3 - <<'PY'
import json,time,glob,sys
stale=[]
for f in glob.glob('/opt/danmu/runtime/danmu_sessions/*/*.status.json'):
    s=json.load(open(f))
    if time.time()-s.get('heartbeat_ts',0)>600: stale.append(f)
if stale: print('STALE',stale); sys.exit(1)
PY
```

## 七、数据对接本地（分析端）

1. 本地同步（每 5 分钟一次，已配置 launchd `com.ad.danmu-sync`）：
   `python3 tools/sync_danmu_from_server.py --host <服务器IP>`，或直接 rsync：
   ```bash
   rsync -avz --timeout=30 root@服务器IP:/opt/danmu/docs/data/danmu/huya/ docs/data/danmu/huya/
   ```
2. 同步后本地 Agent 自动：比赛登记 → 弹幕切片 → 情报分析 → HTML 情报页 → 结果校验回填 → 情报库沉淀。

## 八、纪律（一起守住）

- 灰信号（假赛/剧本/卡盘质疑）只作风险标注，不作为结论；对外只展示聚合统计，不裸展示弹幕流和用户身份。
- 比赛结束判定要 ≥3 类信号（结束语密度 + 比分核对 + 官方/比分源），不拿预测/玩梗当结果。
- 同一场结论多源交叉；单源零散只标"待确认"。
- 弹幕 0 条/假死必须告警排查，禁止静默"无弹幕"。

## 九、更新与联系方式

- 直播间清单以 `docs/data/danmu/streamer_registry.json` + `knowledge/STREAMER_PROFILES.md` 为准（本地仓库）。
- 服务器脚本升级：重新 `scp` 三个脚本到 `/opt/danmu/tools/` 后 `systemctl restart danmu-capture`。
- 遇到问题先看本文件第六节，再问。
