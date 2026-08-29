# 项目问题教训台账（Lessons Log · 全项目唯一问题记录）

> 目的：把所有已发生问题的"教训 → 根因 → 防线"集中记录，防止重复犯错、
> 防止新优化改坏老界面。新错误流程：记录 → 定位根因 → 固化 → 回归。
> 本文件为索引台账，细则见各引用文档/测试；新问题先在此登记再补防线。

## A. 数据 / 状态 / 时间（最高频，2026-08-25 大排查）

| # | 问题 | 根因 | 防线 / 记录位置 |
| --- | --- | --- | --- |
| A1 | 未开始比赛被误判"已结束"，生成假复盘页 | 结束检测无"已开始≥30 分钟"门槛 | AGENTS 12d；流水线门槛；E1 |
| A2 | 已结束比赛显示"进行中" | 状态判断优先扫描快照 time_status | 真实时间优先；match_status 公共函数；E2 + 测试 |
| A3 | 已开始比赛显示"未开始" | 今日页不刷新、状态旧 | 每日自动刷新；真实时间；E3 |
| A4 | 跨时区日期误判（UTC vs 北京） | UTC 日期与北京时间比较 | 禁止 UTC 日期直接比较；12d；E4 + 测试 |
| A5 | 时间显示格式错误（"08-24 08-25 00:00"） | 日期+时间拼接 bug | fmt_time 统一北京输出；E6 |
| A6 | 历史库漏关联节点报告（_BP_/_G1_/_full_ 后缀） | 索引正则不支持后缀 | 15ter；索引支持后缀 + 回归测试 |
| A7 | 详情壳文件名关联错误（WE-LGD→WELGD） | 文件名拼接错 | AGENTS 12a；存在性校验 + 回归测试 |
| A8 | 今日页/首页情报入口缺失（有页无链接） | 只认 matches.json 元数据 | 扫站点文件按对阵匹配 + slug 直连壳；E9 |
| A9 | 时间轴壳引用不存在的节点页（404） | 壳探测包含已删节点 | 壳只生成真实存在的节点；E10 |
| A10 | 扫描数据过期导致赛程/状态失真 | watchlist 旧快照未刷新 | 每日流水线重扫+export+同步；E11 |
| A11 | 联赛分类未知（CS2 IEM 队伍显示"-"） | 队伍集未覆盖新赛事 | TEAM_LEAGUE 扩充 + 回归测试 |
| A12 | 服务器产出未写结构化库（matches.json 等） | 流水线缺 V2 沉淀步骤 | INTEL_LIBRARY_SEDIMENTATION（后续） |

## B. 采集 / 部署 / 工具

| # | 问题 | 根因 | 防线 / 记录位置 |
| --- | --- | --- | --- |
| B1 | 部署包缺依赖（aiohttp）虎牙采集失败 | requirements 不全 | 部署包 v3 补齐 + 自检 |
| B2 | 虎牙 danmaku 库缺失（real-url） | 外部库未打包 | vendor 化 + DANMU_LIB 多路径 |
| B3 | Crypto/protobuf 版本不兼容 | protobuf 新版不兼容 _pb2 | 锁 protobuf==3.20.3 + 纯 Python 模式 |
| B4 | SOOP 弹幕字段（message）与虎牙（text）不兼容 | 字段命名不一致 | analyze 层统一兼容（text/message） |
| B5 | 监控 ts 排序 str/float 崩溃 | 混合时间类型 | 排序统一 str() 兼容 |
| B6 | 本地定时同步被 macOS TCC 拦截 | Documents 权限 | 弃用 launchd，改按需同步（PROGRESS） |
| B7 | 服务器清理进程 pkill 匹配自身 | 通配符匹配命令行 | 用精确 PID（经验，待固化脚本） |
| B8 | 弹幕抓取 0 条误报"无弹幕" | 连接假死未区分 | first-message-timeout/心跳告警（防错 7） |
| B9 | deploy.sh 重复解压目录 cp: same file 中断 | 源=目标 | deploy.sh 判断 pwd==APP 跳过复制（已修） |
| B10 | Vercel CLI 更新中断导致命令丢失/ENOTEMPTY | npm 残留目录 | 清理残留后重装（经验，已固化运维步骤） |

## C. 站点 / 导航 / 发布

| # | 问题 | 根因 | 防线 / 记录位置 |
| --- | --- | --- | --- |
| C1 | 导航重复（一个页面多条面包屑） | 注入脚本不幂等（累积） | add_site_nav 清理+唯一注入；幂等测试 |
| C2 | 旧顶栏（div.top）+ 新导航双套 | 生成器旧顶栏未清 | 统一清理 div.top；框架规范 |
| C3 | 导航字号/下划线/加粗不统一 | 内联样式不完整，继承页面 CSS | 完整内联（text-decoration:none+固定字号）；E25 + 测试 |
| C4 | intel 子页链接路径错误（../intel/xxx） | 相对路径逻辑错误 | 按页面位置生成链接；修复 276 处 + 测试 |
| C5 | favicon 缺失 / 文件丢失 | 注入不全 / apply_patch 异常 | add_favicon 幂等 + 框架测试 |
| C6 | 首页锚点跳转（#markets 滚动） | 锚点式导航 | 改独立页 + 卡片入口 |
| C7 | 服务器与本地双端 push 冲突 | 同一文件两端修改 | vps_publish 以远端为基线（E26） |
| C8 | vps_publish favicon 路径写死崩溃 | add_favicon 未参数化 | 用传入 site 参数；E26 相关 |
| C9 | 跨域 API 缺 OPTIONS 预检 | 只处理 POST | 全 API 处理 OPTIONS + 预检测试（api/README） |
| C10 | 线上验证走错地址（旧地址 301 未跟随） | 未按用户真实路径验证 | AGENTS 12c：跟随重定向 + final URL + 内容关键词 |
| C11 | 服务器产出页无导航/角标 | 发布未注入 | vps_publish 复制后注入 nav+favicon |
| C12 | 今日情报页导航反复变回旧样式 | 生成器自带旧导航 + 发布顺序"先注入后重建"把注入结果覆盖 | 生成器不再自带导航（单一来源）；发布改"先重建后注入"；vps_publish 站点结构审计阻止坏页面上线 |
| C13 | 详情页导航重复（壳 + iframe 内页双导航） | 壳与情报页各带一条导航 | 壳 iframe 加 ?embed=1，情报页嵌入模式自动隐藏自身导航 |
| C14 | 实时情报页缺付费墙（免费可见） | 付费墙未纳入自动发布 | vps_publish 强制注入付费墙 + 审计（Pro 页必须含 danmu_member_v1） |
| C15 | 嵌入脚本重复叠加（一页多份） | 注入不幂等 | add_site_nav 幂等 + 自愈清理；回归测试锁定 embed≤1 |
| C16 | 今日情报页"网站架构与显示"反复出错（总教训） | 多套导航源 / 双端重建覆盖 / 发布无审计 / 测试不全 | 见 E27：单一导航源 + 发布强制审计 + 今日页专项回归测试 + 服务器每 5 分钟自检 |
| C17 | 订阅页登记/验证/统计脚本整段丢失（表单变"死按钮"） | 静态页 subscribe.html 直接 scp 进 site_repo 工作区后，与 vps_publish 的 rebase/reset（或自动 git add -A）竞争，脚本被旧版覆盖 | 静态页改动后**立即** commit+push（在 5 分钟发布窗口内）；订阅页脚本以本地 .danmu_intel_site/subscribe.html 为基准重建；后续把 subscribe/stats 等静态页纳入"源文件 → 发布复制"单一来源（2026-08-26 修复并补回归检查） |
| C18 | 虎牙采集子进程卡死在"未开播"状态（硕硕 06:45 后 checked_at 不再刷新；08:00 直播已开但 1.5 小时不连接） | fetch_huya_danmu 的离线等待循环不重新检测/状态不更新 | 采集健康自检：watchdog 检查每个房间 checked_at 新鲜度，超时自动重启该房间；本次应急 kill 子进程 + 重启 danmu-session 解决（2026-08-26） |
| C19 | fast_intel_node 输出偶发无 </body>/</html> 收尾（页面"截断"→ 付费墙无法注入、发布审计失败） | DeepSeek 输出不写收尾标签，max_tokens=2200 偏小加剧 | 生成后自动补全 </body></html> + max_tokens 2200→4000（2026-08-26 修复） |
| C20 | 虎牙弹幕行 ts 是数值时间戳，slice_rows 只按 ISO 解析 → 虎牙中文弹幕整行被静默丢弃（KT-BRO 节点切片只剩 Twitch/Kick 英文源） | slice_rows 未兼容数值 ts | _ts() 同时支持数值/ISO/unixtime；tests/test_slice_rows_sources.py 回归锁定（2026-08-26 修复） |
| C21 | verify_end 把 G1 结束误判为整场结束（生成假复盘、写整场状态跳过后续节点）；卡死的 Codex 进程还会阻塞流水线数分钟 | 结束语/流量骤降信号过松；显式比分只匹配单队名；无结构确认即终局 | 显式系列比分必须双队名齐全；BO 系列终局需所有小局结算确认；卡死进程可 kill（定时器自动重启）（2026-08-26 修复） |
| D8 | 速览卡修复工具把嵌套结构速览卡破坏成空（KT-BRO G1 BP 重建后 <li> 全丢、审计判 empty） | fix_speedcard 用 `.*?</div>` 局部正则替换，遇嵌套 div 截断 | 整卡重建标准结构：_speedcard_region 定位整卡后整体替换为 card speed + h2 + li（2026-08-26 修复） |

## D. 内容 / 订阅 / 其他

| # | 问题 | 根因 | 防线 / 记录位置 |
| --- | --- | --- | --- |
| D1 | 灰信号当假赛结论 | 纪律缺失 | 灰信号只标注不下结论（防错 8/16） |
| D2 | 观众预测/玩梗当比赛结果 | 单信号误判 | verify_match_end 多信号 + 待官方标注（防错 9） |
| D3 | 生成器编造数据（无样本硬撑） | 原则未执行 | "样本不足/今日无信号"硬门槛 |
| D4 | 会员名单不同步/过期 | 手工维护 | 名单存服务器 + expires 校验；T4 到期提醒待补 |
| D5 | 免费期误判 | FREE_UNTIL 配置 | verify-member 免费期逻辑 + 实测 |
| D6 | 速览卡混入章节号/标题碎片且不写价值（如"3 BP 锚点与选人情报"、"灰信号留痕（入 gray_signals…）"、纯时间线） | 提取层把标题/元数据当关键信息；生成端只列事实不写含义；title/h2 文本与正文拼接导致真实信号句被误判丢弃 | 关键情报价值呈现机制（BLUF×Key Judgment×So-What）：每条=信号+价值+置信+溯源；speedcard_consistency --fix+LLM 改写、--check 发布门禁、回归测试锁定（AGENTS 防错 15） |
| D7 | 通知机器人 Token 被劫持（名字被改成赌场推广、webhook 被指向第三方 ssh.inkognit.org） | Token 泄露后被他人接管（可改名/设 webhook 收取发给机器人的消息）；发送侧不受影响，容易长期无感 | 安全流程：BotFather 立即 revoke 换新 Token → 新 Token 无 webhook（旧劫持自动失效）→ 清理改名 → 密钥不在聊天中明文传输；双推登记通知走"群 ID"（-5476758062 电竞情报库登记）方案，无需小助手先私信机器人（2026-08-26 处理） |
| D8 | 弹幕"提及/讨论"被当作实际选人，并硬做选手×英雄配对（NS-BFX G2 2026-08-27：Scout=狐狸、泰永=EZ、大光=兰博、BFX 上单=Clear 等，实为观众讨论/单房提及，无确认信号） | 把 BP 窗口"该选 X/想要 X/应该是 X"与游戏内实际选人混淆；用"弹幕口径"标签包装推断；选手×英雄映射基于上下文拼凑而非强确认（官方 BP/主播报选+弹幕"锁了"共振） | ① 选手×英雄映射无强确认信号一律"待官方"，禁止写入阵容表；② 英雄只列"弹幕提及·非确认"清单；③ 优化点 2（BP 讨论 vs 实际阵容分栏）落地为生成门禁：BP 结论必须带确认来源标签；④ 用户指出即撤错版并标注修正记录（本场 G1/G2 已修正） |
| D9 | 阵容/选手×英雄"待官方"只能靠战报人工回填，慢且易漏 | 缺官方权威数据源的可脚本化接入 | ① Riot 官方赛事 API（esports-api + feed.lolesports.com window）实测可用：赛后任一 gameId 直接给全队选手×英雄；② tools/fetch_official_game_data.py 一键拉取；③ knowledge/OFFICIAL_DATA_SOURCES.md 沉淀 leagueId/用法/CS2 源；④ 校验通道新增 P0.5（VERIFICATION_METHODOLOGY.md 二.5）（2026-08-27 落地） |

## 校验与守护（防止"修一个漏一类"）

```text
1. 回归测试（tests/，当前 53 项全绿）：match_page / history_index /
   match_status / site_framework / scan 等，覆盖 A/C 大类；
2. 防错清单 DATA_INTEGRITY_CHECKLIST.md：E1-E26 全类别 + 待补项；
3. AGENTS.md 防错规则 1-13（含 12a-12d 细则）；
4. 新错误流程：记录到本台账 → 定位根因 → 固化规则/代码 → 补回归测试。
```
