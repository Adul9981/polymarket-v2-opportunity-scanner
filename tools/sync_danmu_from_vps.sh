#!/bin/bash
# 每日从 VPS 增量同步弹幕数据到本地（过渡方案：服务器采集、本地分析）。
# 由 launchd 每天 07:00 触发（com.danmu-intel.sync），也可手动执行。
set -euo pipefail

VPS="root@158.247.214.175"
SRC="/opt/danmu-intel/docs/data/danmu/"
DST="/Users/ad/Documents/polymarket/docs/data/danmu/"
LOG="/Users/ad/Documents/polymarket/runtime/logs/danmu_sync.log"
SSH_KEY="/Users/ad/.ssh/id_ed25519"

mkdir -p "$(dirname "$LOG")"
echo "[$(date '+%F %T')] sync start" >> "$LOG"

rsync -av --ignore-existing \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20" \
  "$VPS:$SRC" "$DST" >> "$LOG" 2>&1 \
  || { echo "[$(date '+%F %T')] sync FAILED" >> "$LOG"; exit 1; }

echo "[$(date '+%F %T')] sync done" >> "$LOG"
