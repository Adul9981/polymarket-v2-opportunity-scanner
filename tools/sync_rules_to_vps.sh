#!/usr/bin/env bash
# 同步本地权威标准到云服务器（2026-08-27 固化：规则变更必须两端一致，
# 弹幕采集与情报生成在 VPS 执行，Codex 生成时读取 VPS 上的规则文件）。
#
# 用法：bash tools/sync_rules_to_vps.sh [--dry-run]
set -euo pipefail

VPS="root@158.247.214.175"
REMOTE="/opt/danmu-intel"
KEY="/Users/ad/.ssh/id_ed25519"
LOCAL="$(cd "$(dirname "$0")/.." && pwd)"

FILES=(
  "AGENTS.md"
  "knowledge/INTEL_HTML_TEMPLATE.md"
  "knowledge/DANMU_CAPTURE_RULES.md"
  "knowledge/OFFICIAL_DATA_SOURCES.md"
  "knowledge/VERIFICATION_METHODOLOGY.md"
  "knowledge/LIVE_INTEL_SCHEMA.md"
  "knowledge/INTEL_MD_MIRROR.md"
  "tools/fetch_official_game_data.py"
  "tools/vps_intel_pipeline.py"
  "tools/vps_publish.py"
  "tools/vps_self_check.py"
  "tools/update_site_today.py"
  "tools/build_history_index.py"
  "tools/match_status.py"
  "tools/speedcard_consistency.py"
)

echo "[sync-rules] 同步 $((${#FILES[@]})) 个标准/工具文件到 $VPS:$REMOTE"
for f in "${FILES[@]}"; do
  src="$LOCAL/$f"
  if [ ! -f "$src" ]; then
    echo "  !! 缺失本地文件: $f（跳过）"
    continue
  fi
  if [ "${1:-}" = "--dry-run" ]; then
    echo "  [dry] $f"
    continue
  fi
  scp -i "$KEY" -o StrictHostKeyChecking=accept-new "$src" "$VPS:$REMOTE/$f"
  echo "  ok: $f"
done

# 生成端技能文件（VPS Codex 读取）
if [ "${1:-}" != "--dry-run" ] && [ -f "$HOME/.codex/skills/intel-report/SKILL.md" ]; then
  scp -i "$KEY" -o StrictHostKeyChecking=accept-new \
    "$HOME/.codex/skills/intel-report/SKILL.md" \
    "$VPS:/root/.codex/skills/intel-report/SKILL.md"
  echo "  ok: intel-report/SKILL.md"
fi

echo "[sync-rules] 完成"
