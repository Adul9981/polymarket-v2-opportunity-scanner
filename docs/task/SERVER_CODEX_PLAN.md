# 服务器 Codex 方案（2026-08-24 讨论中）

## 背景

用户与朋友讨论：自己租一台云服务器，朋友帮忙把 Codex 安装到服务器上，
本地 Codex 与服务器 Codex 协作，完成"弹幕收集 + 情报输出"的 7×24 迁移
（本地不再需要长期开机）。

## 评估结论

**可行，建议分两步走：**

```text
第一步（过渡，当前已具备）：服务器只跑采集脚本（vps_capture + danmu-session），
  本地 Codex 拉数据做分析 / 情报 / 发布。
第二步（跑稳后）：服务器安装 Codex CLI，把分析 + 情报输出 + 发布逐步自动化上云。
```

理由：

```text
1. 弹幕采集是纯脚本任务（WebSocket + JSONL），不依赖 Codex/LLM，
   脚本常驻更稳、更省；服务器 Codex 的价值在"自动化深度分析"。
2. 服务器 Codex 上云前需要解决三件事：
   a. 账号登录：首次运行需本人用 ChatGPT 账号做一次 OAuth 登录（朋友无法代替）；
   b. 额度 / 并发：同一 ChatGPT 账号在桌面端与服务器端同时使用时注意速率限制与额度；
   c. 网络：节点必须能访问 OpenAI（香港 / 东京 / 美西均可，国内节点需代理，不推荐）。
3. 双 Codex 协作推荐"共享目录 + SSH/Tailscale + 定时任务"，不依赖实时对话：
   服务器 Codex 按定时任务产出（弹幕 JSONL / 情报页 / 结构化 JSON），
   本地 Codex 通过 rsync / git 取用；约定目录与命名即可（见 VPS_HANDOFF.md 数据流）。
```

## 硬件需求（官方依据）

来源：OpenAI 官方仓库 openai/codex 的 docs/install.md。

```text
系统：Ubuntu 20.04+ / Debian 10+（Codex CLI 官方支持 Linux，x86_64 / arm64）
内存：4GB 最低，8GB 推荐（Codex CLI 是远程 API 客户端，不做本地推理，无需 GPU）
磁盘：40GB 起，推荐 80GB（弹幕 JSONL 每天约几十 MB，11 个直播间长期积累）
```

## 购买建议

```text
规格：2 核 / 4GB / 80GB SSD（一步到位：采集脚本 + Codex CLI + 分析工具）
节点：香港（访问虎牙 + OpenAI + Polymarket 均通畅；用户 2026-08-24 指定）
平台：Vultr（有香港 HKG 节点，操作简单，优先）；DigitalOcean 无香港节点
  （亚太仅新加坡/班加罗尔）；AWS Lightsail 香港需启用 opt-in 区域，较复杂
预算：约 $18-24 / 月
```

## 部署注意

```text
1. Codex CLI 安装：
   curl -fsSL https://chatgpt.com/codex/install.sh | sh
   或 npm install -g @openai/codex
2. 登录：首次运行 codex，选 "Sign in with ChatGPT"，OAuth 需用户本人完成。
3. 安全：给朋友的 SSH 访问用密钥优先；若用密码，用一次性强密码，
   部署完成后改密并关密码登录；root 权限最小化。
4. 采集部分沿用现有部署包：deploy.sh + danmu-session.service（vps_capture），
   见 docs/task/VPS_HANDOFF.md。
5. 双 Codex 交接协议（数据 / 任务 / 产出的目录与命名）：
   服务器就绪后由本地 Agent 细化并落文档，两边 Codex 共同遵守。
```

## 状态

```text
2026-08-24：方案讨论中；硬件建议已给用户；待购买云服务器 + 朋友部署。
2026-08-24 补充：用户指定香港节点；平台定为 Vultr（香港）；手把手步骤见
  docs/task/SERVER_SETUP_STEP_BY_STEP.md。
```
