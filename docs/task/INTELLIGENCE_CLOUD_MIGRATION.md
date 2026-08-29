# 弹幕情报能力云端迁移评估（2026-08-24）

> 背景：弹幕采集已上云（Vultr 首尔 158.247.214.175，7×24 常驻）。
> 目标：把"弹幕 → 情报输出"也搬到云服务器，实现全自动。
> 本文件评估本地情报生成能力可迁移性，供用户与朋友落地参考。

## 1. 现状拆解：本地三层能力

```text
第一层 采集层（已上云）：虎牙/SOOP WebSocket 抓取、JSONL 落盘、断线重连、
  跨天滚动、健康自检（tools/fetch_huya_danmu.py、fetch_soop_danmu.py、
  run_danmu_session.py、danmu_live_monitor.py、vps_capture.py）。

第二层 规则层（纯代码，可任意环境运行）：
  - danmu_intel.py        词表命中/弹幕密度峰值/灰信号关键词/情绪计数/
                          活跃用户/队伍选手提及 -> intel JSON
  - verify_match_end.py   比赛结束检测（弹幕 GG + Polymarket 价格确认）
  - slice_danmu_by_match.py 按比赛时间窗切片（防"弹幕对错比赛"）
  - build_match_page.py / build_node_page.py / build_intel_*.py
                          HTML/结构化库/索引/画像/灰信号统计生成
  - build_history_index.py 历史库索引 + 联赛分类标准

第三层 AI 层（目前依赖 Codex 桌面版 + 项目上下文）：
  - 韩文弹幕中文化、BP 负锚价值判断（如"烬 7 连败"）、同构规律识别
    （如"진필패 vs 바필패"）、LONG/SHORT 分层判断、按模板写情报页
  - 依赖 skill 体系：danmu-intel / intel-report / result-verification /
    gray-tracking / intel-library-sync / danmu-capture
  - 依赖长期记忆库：docs/data/intel/*.json（matches/teams/players/
    gray_signals/bp_signals/leagues/entities）+ knowledge/ 知识文档
```

## 2. 可迁移性结论

```text
第一层、第二层：可直接迁移（已是独立 Python 脚本，无环境绑定），
  部署包 v3 已包含采集与监控；分析/报告工具补齐后即完整。
第三层：可迁移，但必须整体搬运"上下文"（skill + 模板 + 知识库 + 结构化库），
  不能只搬一个 prompt。项目优势：这套上下文已高度显式化
  （INTEL_HTML_TEMPLATE / REVIEW_SCHEMA / LIVE_INTEL_SCHEMA /
   CAPTURE_RULES / VERIFICATION_METHODOLOGY / AGENTS.md），
  迁移质量上限远高于"仅调 API"。
```

## 3. 云端两种做法

```text
方案 A：无头 Agent（质量最接近本地，推荐先做）
  服务器装 Codex CLI（或同类 agent runtime）+ 复制 skills/AGENTS.md +
  项目仓库 + 结构化库；事件触发（BP 锁定 / 局间 / 比赛结束）后
  Agent 自动：拉切片 -> 规则层 -> LLM 提炼 -> 写结构化库 + HTML ->
  推送站点。用户不在线也能跑（触发不再依赖对话）。

方案 B：规则层 + LLM API 轻量流水线（更便宜、更快、判断力打折）
  cron/watcher 触发 -> 规则层出统计 + 精选样本 -> 拼 prompt 调 LLM API
  （结构化输出）-> 模板渲染 HTML。丢软判断：跨场规律识别、
  灰信号再犯升级等需长期记忆的推理。

建议：A 先保质量，跑顺后 B 收敛成本；日常 B 出初稿、
关键场次/异常信号升级 A 深审（A+B 混合）。
```

## 4. 关键风险与对策

```text
1. 长期记忆一致（最高风险）：matches/teams/players/gray 等是单机 JSON，
   双端同时写会冲突。第一版"写权限单端"（服务器写、本地读/审），
   或 git 仓库共享 + 拉取前 diff（项目已有 git 惯例与 match_index）。
2. 事件触发：本地靠对话驱动；上云必须事件驱动。
   已有基础：verify_match_end（GG + 价格）、run_danmu_session 的
   session.json/intel.json 健康信号；补一个 watcher/cron 即可。
3. 切片关联：服务器端必须按比赛时间窗切片（schedule/时间窗），
   否则"弹幕对错比赛"导致分析全废（CAPTURE_RULES 防错第 1 条精神）。
4. 质量兜底：闭环（弹幕 -> 结果 -> 验证回填）、灰信号纪律、
   "犯过一次就固化"必须变成服务器自动化检查，否则质量悄悄下滑。
5. 成本控制：只喂统计结果 + 代表样本（BP 窗口/局末/灰信号命中窗口），
   不喂整场 1.5 万条弹幕；一场 BO5 成本可控。
6. 红线：钱包/私钥绝不上服务器；情报流水线不需要交易密钥。
7. 发布出口：站点已是 GitHub Pages（静态），服务器生成 HTML 直接
   git push 到 danmu-intel 仓库即可，无需另起 nginx。
```

## 5. 分阶段路线

```text
阶段 1（已完成）：采集上云 + 本地分析（按需同步，tools/sync_danmu_from_vps.sh）。
阶段 2（下一步）：服务器分析工具齐全（补齐 report 类脚本到部署包），
  无头 Agent 试点一场比赛（本地审一篇，比对质量）。
阶段 3（跑稳后）：事件触发全自动（watcher + verify_match_end +
  定时任务），本地只做抽查复核与规则迭代。
阶段 4（可选）：方案 B 流水线接入，A/B 混合降本。
```

## 6. 结论

```text
可以迁移，且迁移质量取决于"上下文完整性"而非"模型调用方式"。
项目已有 skills + 模板 + 知识库 + 结构化库，具备迁移基础；
建议按"A 无头 Agent 保质量 -> B 流水线降本"路线分阶段推进，
先试点一场比赛验证质量，再全自动。
```
