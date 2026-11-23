# SETUP.md — 从零克隆到跑起来

> 本文件回答一个问题：别人 `git clone` 之后，怎么跑到和服务器（VPS）一样的效果。
> 结论先说：**代码是同一份，但有三样东西不在 git 里**——新鲜比赛数据、弹幕数据、AI 凭据。
> 本文一步步补齐，最后给出手动运行命令与服务器定时器对照表。

## 0. 前置条件

- Python 3.11（推荐 venv）
- 能联网（拉虎扑评分、抓弹幕、读 Polymarket 公开数据）
- 只跑「独立比赛局势页」不需要任何 AI 凭据；跑「情报节点页」才需要（见 §3.3）

## 1. 装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r deliverables/danmu_intel_vps_deploy/requirements.txt
# 抓弹幕时另需（protobuf 老版本 + 显式实现位）
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

依赖清单：`websockets` `requests` `python-dateutil` `tzdata` `aiohttp` `pycryptodome` `protobuf==3.20.3`。

## 2. 设环境变量

代码用 `DANMU_INTEL_ROOT` 定位工作目录，**默认是 `/opt/danmu-intel`（VPS 路径）**，
本地必须覆盖。写进你的 shell 或 `.env`：

```bash
export DANMU_INTEL_ROOT=/你的/clone/路径          # 必设，否则按 /opt/danmu-intel 找文件
export INTEL_PY="$DANMU_INTEL_ROOT/.venv/bin/python"   # 可选，默认就是它
export DANMU_INTEL_AI=codex                        # codex（默认）| deepseek（直连，本地无需 codex CLI）
export CODEX=/root/.local/bin/codex                # 仅 codex 后端用到，指向你的 codex 二进制
export DEEPSEEK_API_KEY=sk-...                     # 仅 deepseek 后端用到
```

## 3. 补齐 git 之外的三样东西

### 3.1 比赛数据 `data/matches_today.json`（必）

git 里这份是**快照，可能已过期**（本地最新一场 2026-10-25）。权威来源是云扫：

- `.github/workflows/push-game-status.yml`：每 5 分钟拉 Polymarket 小局结算状态，
  需要仓库 Secrets 里的 `DANMU_SERVER_SSH_KEY`（指向某台采集服务器的私钥）——
  这是**耦合到具体服务器**的，别人 clone 后要自己换成自己的服务器，或改用本地生成。

本地生成（不依赖那台服务器，但要多源）：

```bash
python3 tools/fetch_hupu_esports.py          # 虎扑赛程 -> data/hupu_esports_schedule.json
python3 tools/fetch_official_lol_schedule.py # Riot 官方赛程 -> runtime/official_lol_today.json
# 还需要 Polymarket esports tag 扫描产出 runtime/watchlist_events.json（见 docs/data/DATA_COLLECTION_GUIDE.md）
python3 tools/export_today_matches.py \
  --input runtime/watchlist_events.json \
  --official runtime/official_lol_today.json \
  --hupu data/hupu_esports_schedule.json \
  --out data/matches_today.json
```

> 提示：只想先看「独立局势页」长什么样，可临时手工造一个最小 `data/matches_today.json`
> （字段见 `schemas/` 与 `tools/build_situation_page.py` 的 `live_matches()` 读取项：
> `id / teams / start_time / league / closed`），再补虎扑评分 key 即可。

### 3.2 弹幕数据（胜率「弹幕档」必）

弹幕文件在 `docs/data/danmu/<game>/`，**不在 git 里**（0 个 tracked 文件）。胜率三档里
「有胜负弹幕 → 真实比例」这一档依赖它；没有弹幕就只会回退到「评分 70/30」或「50:50」。

抓取入口（直播进行中才抓得到）：

```bash
python3 tools/run_danmu_session.py \
  --room official_660000=https://www.huya.com/660000 \
  --room mile_149361=https://www.huya.com/149361 \
  --game lol --teams KC,MKOI \
  --hupu-out-biz-no <虎扑 match key> --hupu-out-biz-type lol_match
```

直播间/联赛采集集登记在 `config/market_watchlist.json`、`docs/data/intel/leagues.json`、
`knowledge/streamer_registry.json`；完整采集 SOP 见 `knowledge/DANMU_README.md`。

### 3.3 AI 凭据（只有「情报节点页」需要）

- 生成整场情报页（`vps_intel_pipeline.py`）会调 **Codex / DeepSeek**，二者都不在 git。
- Codex：`curl -fsSL https://chatgpt.com/codex/install.sh | sh` 装好、登录授权后，
  把路径写进 `CODEX`。
- DeepSeek 直连：`DANMU_INTEL_AI=deepseek` + `DEEPSEEK_API_KEY`。
- **「独立比赛局势页」和「比赛局势栏刷新」是规则层零 AI，不需要这一节。**

## 4. 跑起来（服务器定时器 → 本地命令对照）

| 服务器定时器 | 频率 | 干什么 | 本地等价命令 |
| --- | --- | --- | --- |
| `vps-publish.timer` | 每 1min | 重建局势数据 + 发布站点 | `python3 tools/vps_publish.py`（内部调 `build_situation_page.py --once`） |
| `refresh-situation.timer` | 每 60s | 情报节点页比赛局势栏就地刷新 | `python3 tools/refresh_situation.py --once` |
| intel pipeline timer | 每 5min | 检测结束 + 切片 + 生成情报节点页 | `python3 tools/vps_intel_pipeline.py --once` |
| `danmu-session.service` | 常驻 | 弹幕采集 | `python3 tools/run_danmu_session.py --room ...` |
| GitHub Actions 云扫 | 每 5min | 小局结算状态推送 | `.github/workflows/push-game-status.yml` |

### 4.1 最快看到效果：独立「比赛局势」页（零 AI）

```bash
export DANMU_INTEL_ROOT=/你的/clone/路径
python3 tools/build_situation_page.py --once   # 产出 data/situation_live.json
python3 -m http.server 8000 -d .               # 或任意静态服务器
# 浏览器打开 http://localhost:8000/tools/templates/match_situation.html
```

> 注意：`match_situation.html` 默认 fetch 同目录 `situation_live.json`；本地预览时若两者
> 不在一起，把 `situation_live.json` 拷到 `match_situation.html` 旁，或改页面里的 `DATA_URL`。

### 4.2 情报节点页（需要 §3.3 的 AI）

```bash
python3 tools/vps_intel_pipeline.py --once          # 跑所有未完成比赛
python3 tools/vps_intel_pipeline.py --match <id>     # 只跑一场
# 产出 reports/intel_danmu_<...>.html，含「比赛局势」栏（胜率 + 评分）
```

### 4.3 比赛局势栏实时刷新（情报页已生成后）

```bash
python3 tools/refresh_situation.py --once            # 跑一轮
python3 tools/refresh_situation.py --interval 60     # 本地循环，模拟 60s timer
```

### 4.4 发布 / 托管（可选）

服务器把 `reports/` 复制进 `site_repo/` 再推 GitHub Pages、并由 nginx 直出。本地可：

- 直接开 `reports/*.html` 看结果；
- 或配置 `tools/vps_publish.py` 把输出指向你自己的 GitHub Pages 仓库（需要自己的
  发布密钥与仓库，见 `tools/vps_publish.py` 与 `deploy/danmu_intel/README.md`）。

## 5. 数据流总览

```text
【独立比赛局势页（零 AI，~1 分钟实时）】
  matches_today.json ──> build_situation_page.py ──> data/situation_live.json
        └─ 弹幕(胜率弹幕档) + 虎扑评分(实时联网) ──> 每局 win_html / ratings_html
        └─ match_situation.html JS 每 30s 拉 situation_live.json 原地刷新

【情报节点页（需 AI）】
  弹幕切片 + 虎扑评分 ──> vps_intel_pipeline.py（Codex/DeepSeek）──> reports/intel_danmu_*.html
        └─ refresh_situation.py 每 60s 就地刷新「比赛局势」栏（胜率 + 评分）
        └─ vps_publish 复制进 site_repo 发布
```

胜率三档规则（两页共用，`render_node_page.situation_win_block_tiered`）：
①有胜负弹幕 → 真实比例；②无弹幕但有评分 → 评分总和对比 70/30；③都没有 → 50:50。

## 6. 常见坑

1. **路径**：忘设 `DANMU_INTEL_ROOT` 会去读 `/opt/danmu-intel`，本地直接报文件不存在。
2. **空结果 ≠ 无比赛**：`build_situation_page.py` 输出 0 场会打 WARN，先查
   `matches_today.json` 是否已更新（防错规则 1：先怀疑数据没更新，不硬报"无比赛"）。
3. **沙箱联网**：本地运行若在受限沙箱里，拉虎扑/抓弹幕会 DNS 不通，先申请联网授权。
4. **弹幕为 0**：直播没开、房间没登记、或采集进程没跑；不是"今天没信号"（防错规则 7）。
5. **跨时区**：页面统一北京时间；`matches_today.json` 里的 `start_time` 是 UTC ISO，
   别拿 UTC 日期直接和北京时间比较（防错规则 25）。
6. **回归测试**：改动任何工具后，`tests/` 相关用例要全绿再上线（见各 `tests/test_*.py`）。
