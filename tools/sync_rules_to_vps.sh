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
  "knowledge/STAKE_ODDS_DATA_SOURCE.md"
  "requirements.txt"
  "config/stake_prematch.json"
  "tools/build_stake_prematch_site.py"
  "tools/prematch_detail.py"
  "tools/stake_lmt.py"
  "tools/stake_oddin.py"
  "tools/add_site_nav.py"
  "tools/fetch_official_game_data.py"
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
  "tools/verify_match_end.py"
  "tools/vps_intel_pipeline.py"
  "tools/render_node_page.py"
  "tools/refresh_situation.py"
  "tools/build_situation_page.py"
  "tools/templates/match_situation.html"
  "tools/fetch_hupu_player_ratings.py"
  "tools/intel_html.py"
  "tools/fetch_official_game_data.py"
  "tools/fetch_official_lol_schedule.py"
  # 赛前页历史数据（1 队伍交手情况 + 2 队伍比赛近况）：数据拉取 + 规则层渲染，pipeline pre 分支 import
  "tools/fetch_team_history.py"
  "tools/render_pregame.py"
  "tools/fetch_hupu_esports.py"
  "tools/export_today_matches.py"
  "tools/vps_publish.py"
  "tools/add_site_nav.py"
  "tools/add_favicon.py"
  "tools/add_paywall.py"
  "tools/add_stats_track.py"
  "tools/inject_pattern_nav.py"
  "tools/vps_self_check.py"
  "tools/update_site_today.py"
  "tools/build_home_today.py"
  "tools/export_today_matches.py"
  "tools/fetch_official_lol_schedule.py"
  "tools/build_history_index.py"
  "tools/match_status.py"
  "tools/speedcard_consistency.py"
  # 服务器侧回填/重建脚本（glob 三级目录适配 game/ 层）
  "tools/regen_g34.py"
  "tools/regen_kt_nodes.py"
  "tools/vps_backfill_nodes.py"
  # 弹幕目录迁移（旧两级 -> 三级 game/ 层，正式迁移时先停采集再 --apply）
  "tools/migrate_danmu_games.py"
  # CS2 静态阵容表 + 队伍统一清单（fetch_cs2_rosters 生成阵容表；
  #   fetch_hupu_player_ratings / build_history_index 读取，必须随代码同步防分叉）
  "tools/fetch_cs2_rosters.py"
  "docs/data/intel/team_names.json"
  "docs/data/intel/cs2_rosters.json"
  # 站点功能层（原 VPS 独有，2026-11-12 补进清单防分叉）
  #   访问统计：analytics_service = systemd 服务后端（danmu-analytics/alpha-analytics），
  #     analytics_publish = vps_publish 的 import 依赖（必须随 vps_publish 同步）
  "tools/analytics_service.py"
  "tools/analytics_publish.py"
  #   地图战绩台账
  "tools/sync_map_records.py"
  #   深度情报页三件套（规则直出 + 直连 DeepSeek；key 走 DEEPSEEK_API_KEY/config.toml，无硬编码）
  "tools/gen_deep_intel.py"
  "tools/llm_client.py"
  "tools/render_fast_intel.py"
  #   形态图谱桥：import build_pattern_decision_site / build_pattern_library，
  #   二者在 /opt/danmu-intel/pattern-decision/live/tools/（形态决策台，不在本清单）——
  #   跨套文件，单推不能本地跑通，依赖由形态决策台自管
  "tools/build_pattern_atlas.py"
  #   一次性脚本（硬编码 KT-BRO 场次，保留同步防分叉）
  "tools/regen_kt_all.py"
)

echo "[sync-rules] 同步 $((${#FILES[@]})) 个标准/工具文件到 $VPS:$REMOTE"

# 同步前在服务器做一次快照（仅真实同步时），出 bug 后可用 tools/rollback_vps.sh 一键回退
if [ "${1:-}" != "--dry-run" ]; then
  STAMP=$(date +%Y%m%d_%H%M%S)
  echo "[sync-rules] 同步前快照 -> $REMOTE/.rollback/code_$STAMP.tar.gz"
  ssh "${SSH_OPTS[@]}" "$VPS" \
    "mkdir -p $REMOTE/.rollback && tar -czf $REMOTE/.rollback/code_$STAMP.tar.gz -C $REMOTE tools knowledge AGENTS.md docs/data/intel" \
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
