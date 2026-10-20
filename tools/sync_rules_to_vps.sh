#!/usr/bin/env bash
# 同步本地权威标准到云服务器（2026-08-27 固化：规则变更必须两端一致，
# 弹幕采集与情报生成在 VPS 执行，Codex 生成时读取 VPS 上的规则文件）。
#
# 用法：bash tools/sync_rules_to_vps.sh [--dry-run]
set -euo pipefail

VPS="root@158.247.214.175"
REMOTE="/opt/danmu-intel"
KEY="$HOME/.ssh/id_ed25519"   # 本地 SSH 私钥（Linux 默认路径；已授权到 VPS，缺失时回退 ssh-agent 默认 key）
LOCAL="$(cd "$(dirname "$0")/.." && pwd)"

# 若 KEY 文件不存在，则去掉 -i 走 ssh-agent / 默认 key（更稳）
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -f "$KEY" ] && SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=accept-new)

FILES=(
  # 规则与知识库
  "AGENTS.md"
  "knowledge/INTEL_HTML_TEMPLATE.md"
  "knowledge/DANMU_CAPTURE_RULES.md"
  "knowledge/OFFICIAL_DATA_SOURCES.md"
  "knowledge/VERIFICATION_METHODOLOGY.md"
  "knowledge/LIVE_INTEL_SCHEMA.md"
  "knowledge/INTEL_MD_MIRROR.md"
  "knowledge/streamer_registry.json"
  # 弹幕采集层（2026-09 优化：game 字段区分比赛类型）
  "tools/fetch_huya_danmu.py"
  "tools/fetch_soop_danmu.py"
  "tools/fetch_kick_danmu.py"
  "tools/fetch_twitch_danmu.py"
  "tools/fetch_danmu_multi.py"
  "tools/run_danmu_session.py"
  "tools/streamer_game.py"
  "tools/vps_capture.py"
  "tools/danmu_live_monitor.py"
  # 情报生成层（弹幕提炼 + AI 生成 + 发布）
  "tools/danmu_intel.py"
  "tools/vps_intel_pipeline.py"
  "tools/render_node_page.py"
  "tools/refresh_situation.py"
  "tools/fetch_hupu_player_ratings.py"
  "tools/intel_html.py"
  "tools/fetch_official_game_data.py"
  "tools/fetch_official_lol_schedule.py"
  "tools/fetch_hupu_esports.py"
  "tools/vps_publish.py"
  "tools/vps_self_check.py"
  "tools/update_site_today.py"
  "tools/build_history_index.py"
  "tools/match_status.py"
  "tools/speedcard_consistency.py"
  # 服务器侧回填/重建脚本（glob 三级目录适配 game/ 层）
  "tools/regen_g34.py"
  "tools/regen_kt_nodes.py"
  "tools/vps_backfill_nodes.py"
  # 弹幕目录迁移（旧两级 -> 三级 game/ 层，正式迁移时先停采集再 --apply）
  "tools/migrate_danmu_games.py"
)

echo "[sync-rules] 同步 $((${#FILES[@]})) 个标准/工具文件到 $VPS:$REMOTE"

# 同步前在服务器做一次快照（仅真实同步时），出 bug 后可用 tools/rollback_vps.sh 一键回退
if [ "${1:-}" != "--dry-run" ]; then
  STAMP=$(date +%Y%m%d_%H%M%S)
  echo "[sync-rules] 同步前快照 -> $REMOTE/.rollback/code_$STAMP.tar.gz"
  ssh "${SSH_OPTS[@]}" "$VPS" \
    "mkdir -p $REMOTE/.rollback && tar -czf $REMOTE/.rollback/code_$STAMP.tar.gz -C $REMOTE tools knowledge AGENTS.md" \
    || echo "  !! 快照失败，继续同步（回退将不可用）"
fi

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
  scp "${SSH_OPTS[@]}" "$src" "$VPS:$REMOTE/$f"
  echo "  ok: $f"
done

echo "[sync-rules] 完成"
