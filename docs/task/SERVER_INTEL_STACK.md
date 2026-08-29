# 服务器情报栈部署记录（2026-08-24）

> 服务器：158.247.214.175（Vultr 首尔，Ubuntu 24.04，2 核 / 4GB / 80GB）
> 目标：弹幕采集 + 情报输出全链路在云上运行，本地只做审阅与规则迭代。

## 1. 已配置内容

```text
采集（7×24 常驻）：vps_capture.py + run_danmu_session.py + 11 直播间
  （虎牙官方 / 957 / 毛毛 / 米勒 / 记得 / 硕硕 + SOOP LCK CL + CSBOY×2 + TI×2）
  systemd: danmu-session.service（开机自启 / 断线重连 / 跨天滚动）

情报工具链：tools/ 82 个脚本（规则层 + 报告/索引/画像/灰信号生成器，
  已从本地全量同步，含 vendor/real-url 虎牙库）
知识库：knowledge/ 38 个文件（SOP / 模板 / 验证方法论 / 主播档案 / 防错规则）
结构化情报库：docs/data/intel/ 17 个 JSON（matches/teams/players/gray/bp/leagues）
配置与契约：config/（词表白名单）+ schemas/
项目共识：AGENTS.md（含最高优先级任务与防错规则）

AI 能力：Codex CLI 0.149.1（/root/.local/bin/codex）
  模型提供商：DeepSeek（deepseek-v4-flash，OpenAI 兼容 Responses 接口）
  配置：/root/.codex/config.toml（权限 600，API key 存于 model_providers.deepseek）
  6 个情报 skill 已安装：/root/.codex/skills/
  （danmu-capture / danmu-intel / intel-report / result-verification /
   gray-tracking / intel-library-sync，项目根路径已改为 /opt/danmu-intel）
```

## 2. 自检结果（2026-08-24）

```text
✓ danmu_intel.py 对真实弹幕（硕硕 08-24）输出情报 JSON（密度峰值/灰信号等）
✓ build_gray_stats.py 输出灰信号统计页（26 主体）
✓ verify_match_end.py 比赛结束检测可用
✓ build_history_index.py / build_node_page.py / build_match_page.py 可用
✓ 采集服务 7×24 运行中，弹幕持续落盘
✓ Codex CLI + DeepSeek 实测跑通（codex exec 读取 README_SERVER.md 并给出
  准确总结，tokens 12,879）——无头 Agent 可直接执行情报任务，无需 ChatGPT 登录
```

## 3. AI 调用（DeepSeek，已配置）

```bash
# 服务器上运行无头 Codex（DeepSeek）：
export PATH=$HOME/.local/bin:$PATH
cd /opt/danmu-intel
codex exec --skip-git-repo-check "任务描述"
```

> API key 存放：/root/.codex/config.toml（chmod 600）；如需轮换直接改
> model_providers.deepseek.experimental_bearer_token 后重启任务即可。

## 4. 下一步（阶段 3：事件触发全自动）

```text
（已配置 2026-08-24）
1. 定时流水线 vps-intel-pipeline.timer（每 5 分钟）：
   读 data/matches_today.json（本地 export_today_matches.py 生成后同步）
   -> verify_match_end 弹幕多信号检测结束 -> 切片 -> danmu_intel 规则层
   -> codex exec（DeepSeek）按 intel-report 技能生成整场情报页 HTML；
   状态 runtime/vps_intel/<match>.json，已完成跳过（幂等）。
2. 产出回传：服务器 reports/ 的 HTML 与 runtime/vps_intel/ 的 JSON
   同步回本地审阅；站点（GitHub Pages）由本地或服务器 git push 更新；
3. 本地保留审阅/规则迭代角色，服务器负责 7×24 自动产出。
```

## 5. 数据同步约定（沿用）

```text
弹幕：服务器采集 docs/data/danmu/，本地按需拉取（tools/sync_danmu_from_vps.sh）。
情报：服务器产出后回传本地入库；长期记忆库两端一致（写权限单端优先）。
```

## 6. 今日比赛清单同步（每日一次）

```bash
# 本地（Polymarket 可访问）：扫描后导出并同步到服务器
python3 tools/export_today_matches.py
scp runtime/matches_today.json root@158.247.214.175:/opt/danmu-intel/data/matches_today.json
```

> 待优化：队伍长名归一化（如 "DN SOOPers Challengers" -> DNS），
> 以及按联赛过滤（默认全量，LoL/CS2/Dota2 均覆盖）。
