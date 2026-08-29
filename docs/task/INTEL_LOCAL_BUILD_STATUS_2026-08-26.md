# 弹幕情报本地项目建设情况说明（2026-08-26）

## 一、建设状态总览

本地 Polymarket 电竞情报库（任务 6 弹幕子线）已建设到**可迁移状态**：
全量回归测试 **93/93 通过**，采集/分析/情报/复盘/入库全链路可用。

## 二、本地已建成模块

### 1. 采集层（4 平台，多路同抓）
```text
tools/run_danmu_session.py    多房间持续会话（健康/告警/自动重启/聚合情报页）
tools/fetch_huya_danmu.py     虎牙弹幕（当前主源：LCK/LPL/LEC/CS2/Dota2 中文弹幕）
tools/fetch_soop_danmu.py     SOOP 韩文弹幕（LCK CL 官方流 + VOD 回捞）
tools/fetch_twitch_danmu.py   Twitch 匿名 IRC（2026-08-26 用户决定暂停：连接假死问题，
                              已修复静默超时重连，注册表标记"暂停可恢复"）
tools/fetch_kick_danmu.py     KICK Pusher WS（CS2：IEM/ECL/EWC 官方 + Gaules）
docs/data/danmu/streamer_registry.json  直播间注册表（19 源）
```

### 2. 情报分析层
```text
tools/danmu_intel.py          情报提炼（队伍/选手/BP/盘口/灰信号/密度）
tools/danmu_live_monitor.py   实时监控聚合页（60s 刷新）
tools/slice_danmu_by_match.py 比赛维度切片
```

### 3. 结果校验与防错层（最高优先级）
```text
tools/verify_match_end.py     弹幕结束信号多信号打分
tools/match_state_guard.py    结果判定门禁（四道闸：时间门槛/结构源优先/反讽识别/比分源滞后）
tools/speedcard_consistency.py 速览卡一致性审计（发布前 --check）
tests/test_match_state_guard.py / test_speedcard_consistency.py 等回归锁定
```

### 4. 情报输出层（v2 决策导向模板）
```text
12 段结构：0 速览卡 / 1 结果 / 2 灰信号 / 3 BP锚点 / 4 盘口 / 5 方向板 /
           6 含义 / 7 逐局 / 8 画像 / 9 规律 / 10 预测验证 / 11 溯源
速览卡 = BLUF × Key Judgment × So-What（每条可溯源 → 详 §N）
多语言规范：信号层全中文意译、原文折叠、黑话双语（야필패=亚索必败）
来源分层标签：本场弹幕 / 前局延续 / 历史库 / 推测（外推三型，条件化）
tools/reformat_intel_template.py  旧页 → 新模板重排（保留全部内容）
tools/html_to_intel_md.py         HTML → MD 全文镜像（双格式必出）
```

### 5. 结构化情报库（docs/data/intel/）
```text
matches.json / teams.json / players.json / gray_signals.json / bp_signals.json /
leagues.json / team_names.json（队伍命名唯一权威）/ aliases.json / users.json
tools/build_history_index.py      历史库索引（联赛/队伍/日期过滤 + 结果回填）
tools/build_intel_bp_stats.py     BP 兑现率统计页
tools/build_intel_champion_lookup.py  选手×英雄锚点速查页
tools/build_gray_stats.py         灰信号统计页
```

## 三、今日修复与沉淀（2026-08-26）

```text
1. 历史索引 4 个回归修复：
   - 文件名正则支持联赛前缀（LCK-KT-BRO / LCKCL-KRXC-BFXY / LEC-FNC-NAVI）；
   - 特殊文件（CS-绿龙-Legacy）优先匹配，防前缀正则误解析；
   - normalize_league 补 The International/TI → Dota2；
   - matches.json 补 result_inferred 字段（索引结果回填源）；
   - 测试改为从工具导入正则/别名/特殊表（单一来源防漂移）。
2. 防错规则新增：规则 16 队名歧义防误、规则 17 情报来源分层原则
   （外推三型 + 置信度标签 + 冲突优先级 + 推理闭环 + 生成端审计）。
3. 模板规范新增：12 段决策导向、速览卡硬门槛、多语言规范、
   收敛不丢硬信息、证据引用要求、来源分层标签。
4. Twitch 采集器修复静默超时重连（60s 无数据主动重连），
   按用户决定注册表标记暂停采集（只采虎牙）。
```

## 四、迁移就绪状态

```text
✅ 全量测试 93/93 通过
✅ 工具链完整（采集 4 平台 + 分析 + 校验门禁 + 输出 + 入库 + 索引）
✅ 数据层 10 个 JSON 齐备
✅ 模板规范 + 移交规格（INTEL_TEMPLATE_HANDOFF.md）已定稿
✅ 线上适配建议（三层：整场/小局/局内节点；字段映射）已写入移交文档
待线上工具接入后：按 INTEL_MIGRATION_PACKAGE 清单迁移配置与数据文件。
```
