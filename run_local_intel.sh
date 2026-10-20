#!/usr/bin/env bash
# 本地一键实时情报流水线：查询今日比赛 -> 弹幕采集 -> 实时生成情报页 -> 打开页面
#
# 用法：
#   ./run_local_intel.sh                 # 跑今天全部比赛的全流程
#   INTEL_INTERVAL=120 ./run_local_intel.sh   # 自定义流水线轮询间隔（秒，默认 10）
#
# 关闭：Ctrl-C 退出脚本，自动停掉弹幕采集守护、所有采集会话与流水线。
#
# 前提：
#   1. DeepSeek key 在 ~/Deepseek API key.txt（流水线自动读取，见 vps_intel_pipeline.py）
#   2. 有图形桌面时自动用默认浏览器打开实时情报页（每 30 秒自动刷新）；无桌面只打印路径

set -uo pipefail

# 定位项目根目录（脚本就在根目录，不写死路径）
cd "$(dirname "$0")"
ROOT_DIR="$(pwd)"

# Python 解释器（优先用环境变量 INTEL_PY，否则用默认 venv）
PYTHON="${INTEL_PY:-$HOME/venvs/intel-whisper/bin/python}"

# 流水线轮询间隔（秒）
INTERVAL="${INTEL_INTERVAL:-10}"

CAPTURE_PID=""
CAPTURE_LOG="$ROOT_DIR/runtime/vps_capture.log"
_CLEANED=""

# 关闭所有子程序（幂等：Ctrl-C 与退出都会触发，只执行一次）
cleanup() {
    [[ -n "$_CLEANED" ]] && return
    _CLEANED=1
    echo ""
    echo "=== 正在关闭所有子程序 ==="
    # 1) 先停采集守护（vps_capture.py），避免它把会话重新拉起
    if [[ -n "$CAPTURE_PID" ]] && kill -0 "$CAPTURE_PID" 2>/dev/null; then
        kill -TERM "$CAPTURE_PID" 2>/dev/null || true
    fi
    # 2) 优雅停掉采集会话与抓取子进程（SIGTERM 会写会话状态再退出）
    pkill -TERM -f "run_danmu_session.py" 2>/dev/null || true
    pkill -TERM -f "fetch_huya_danmu.py" 2>/dev/null || true
    pkill -TERM -f "fetch_soop_danmu.py" 2>/dev/null || true
    sleep 3
    # 3) 兜底强杀（个别子进程可能卡在重连/重试）
    pkill -KILL -f "run_danmu_session.py" 2>/dev/null || true
    pkill -KILL -f "fetch_huya_danmu.py" 2>/dev/null || true
    pkill -KILL -f "fetch_soop_danmu.py" 2>/dev/null || true
    [[ -n "$CAPTURE_PID" ]] && kill -KILL "$CAPTURE_PID" 2>/dev/null || true
    echo "已全部关闭。"
}

# Ctrl-C / kill / 关闭终端：先清理再退出；正常退出也会走 cleanup
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM
trap 'cleanup; exit 129' HUP
trap 'cleanup' EXIT

echo "=== 本地实时情报流水线 ==="
echo "项目目录 : $ROOT_DIR"
echo "Python   : $PYTHON"
echo "轮询间隔 : ${INTERVAL}s"
echo ""

# ── 1. 查询今日比赛 ─────────────────────────────────────────────
# export_today_matches.py 内部会刷新虎扑（fetch_hupu_esports.py）与官方赛程缓存，
# 合并监控清单 -> data/matches_today.json（vps_intel_pipeline 的规范输入）。
echo "=== [1/3] 查询今日比赛（hupu / 官方 / 监控清单）==="
if "$PYTHON" tools/export_today_matches.py; then
    echo "（今日比赛清单已更新 -> data/matches_today.json）"
else
    echo "（查询失败，沿用已有 data/matches_today.json）"
fi
echo ""

# ── 2. 启动弹幕采集（后台守护） ─────────────────────────────────
# vps_capture.py 按 streamer_registry.json 拉起各游戏 run_danmu_session，
# 跨天自动滚动文件、异常自动重启；日志落 runtime/vps_capture.log。
echo "=== [2/3] 启动弹幕采集（vps_capture.py，后台）==="
mkdir -p "$ROOT_DIR/runtime"
INTEL_PY="$PYTHON" "$PYTHON" tools/vps_capture.py > "$CAPTURE_LOG" 2>&1 &
CAPTURE_PID=$!
echo "弹幕采集守护已启动（pid $CAPTURE_PID，日志 $CAPTURE_LOG）"
echo ""

# ── 3. 打开实时情报页 ───────────────────────────────────────────
# run_danmu_session 的聚合监控会持续重写 reports/intel_danmu_live_<游戏>_<日期>.html，
# 页面自带 30 秒自动刷新。等它生成后交给默认浏览器打开。
echo "=== [3/3] 打开实时情报页 ==="
LIVE_PAGE=""
for ((i = 0; i < 12; i++)); do
    LIVE_PAGE=$(ls -t "$ROOT_DIR"/reports/intel_danmu_live_*_$(date +%F).html 2>/dev/null | head -1)
    [[ -n "$LIVE_PAGE" ]] && break
    sleep 5
done
if [[ -n "$LIVE_PAGE" ]]; then
    echo "实时情报页：$LIVE_PAGE（页面每 30 秒自动刷新）"
    (xdg-open "$LIVE_PAGE" >/dev/null 2>&1 \
        || open "$LIVE_PAGE" >/dev/null 2>&1 \
        || true) &
else
    echo "（暂未生成 live 页；稍后可在 reports/ 目录手动打开 intel_danmu_live_*.html）"
fi
echo ""

# ── 4. 实时情报流水线循环 ───────────────────────────────────────
# 每 INTERVAL 秒跑一轮 vps_intel_pipeline.py --once，按节点时间生成 DeepSeek 深度页；
# 内部有锁（pipeline.lock），已有实例在跑时本轮自动跳过，不会重叠。
echo "=== 实时情报流水线循环（每 ${INTERVAL}s 一轮，Ctrl-C 退出）==="
echo "关闭本脚本会自动停掉弹幕采集与流水线。"
echo ""
while true; do
    DANMU_INTEL_ROOT="$ROOT_DIR" \
    INTEL_PY="$PYTHON" \
    DANMU_INTEL_AI=deepseek \
        "$PYTHON" tools/vps_intel_pipeline.py --once || true
    sleep "$INTERVAL"
done
