# Danmu Intel VPS 部署包（临时过渡方案：只做弹幕采集）

给数据合作伙伴的线上部署包：**7×24 弹幕采集常驻**，分析 / 情报 / 站点发布留在本地。
（第二阶段再把扫描、分析、发布逐步搬上 VPS。）

## 包含

```text
tools/       采集常驻（vps_capture + run_danmu_session）与本地分析工具（16 个）
config/      赛事白名单（LCK/LPL/LCP/LEC/LCS/KeSPA/CS2/Dota2）
schemas/     数据字段契约
knowledge/   采集规则 + 主播档案 + 直播间注册表
runtime/systemd/  常驻服务单元（danmu-session：采集；daily-scan/site-publish 过渡期不启用）
deploy.sh    一键部署脚本
requirements.txt
VPS_HANDOFF.md   接手检查单
```

## 快速开始

```bash
git clone <本包> /tmp/deploy && cd /tmp/deploy
chmod +x deploy.sh && ./deploy.sh
```

## 注意

```text
1. 过渡方案只启用 danmu-session.service（采集常驻）；不要启用 daily-scan /
   site-publish，站点由本地负责发布。
2. 采集脚本连虎牙/SOOP WebSocket；未开播直播间自动重试，不影响其他房间。
3. 弹幕按天落盘 docs/data/danmu/<平台>/<日期>_<直播间>.jsonl；
   跨天自动滚动（00:00 后写新日期文件）。
4. 数据回传、健康检查、检查单见 VPS_HANDOFF.md；日志在 /opt/danmu-intel/logs/。
5. Agent 深度提炼（LLM）不在本包：由本地 Agent 层接 DeepSeek API。
```
