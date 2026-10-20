#!/usr/bin/env bash
# 回退服务器代码到某次同步前的快照。
# 快照由 tools/sync_rules_to_vps.sh 在每次真实同步前自动生成，存放在服务器
# /opt/danmu-intel/.rollback/code_<时间戳>.tar.gz。
#
# 用法：
#   bash tools/rollback_vps.sh              # 列出服务器上的快照（新 -> 旧）
#   bash tools/rollback_vps.sh <时间戳>      # 回退到该时间戳（只填文件名里的时间戳部分）
set -euo pipefail

VPS="root@158.247.214.175"
REMOTE="/opt/danmu-intel"
ROLLBACK="$REMOTE/.rollback"
KEY="$HOME/.ssh/id_ed25519"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -f "$KEY" ] && SSH_OPTS=(-i "$KEY" -o StrictHostKeyChecking=accept-new)

STAMP="${1:-}"

if [ -z "$STAMP" ]; then
  echo "[rollback] 服务器上的快照（新 -> 旧）："
  ssh "${SSH_OPTS[@]}" "$VPS" "ls -1t $ROLLBACK/code_*.tar.gz 2>/dev/null || true" \
    | sed 's#.*/code_##; s#\.tar\.gz$##' | sed 's/^/    /'
  echo
  echo "回退用法：bash tools/rollback_vps.sh <时间戳>"
  exit 0
fi

TAR="$ROLLBACK/code_${STAMP}.tar.gz"
echo "[rollback] 目标快照：$TAR"

# 1) 确认快照存在
if ! ssh "${SSH_OPTS[@]}" "$VPS" "test -f $TAR"; then
  echo "  !! 快照不存在（无参数运行可列出全部快照）"
  exit 1
fi

# 2) 解包覆盖 tools/ knowledge/ AGENTS.md（恢复被改坏的文件；不删除快照之后新增的文件）
ssh "${SSH_OPTS[@]}" "$VPS" "tar -xzf $TAR -C $REMOTE"
echo "  ok: 已恢复 tools/ knowledge/ AGENTS.md"

# 3) 重启长驻采集服务（定时任务下次运行会自动加载回退后的代码）
ssh "${SSH_OPTS[@]}" "$VPS" "systemctl restart danmu-session" \
  && echo "  ok: 已重启 danmu-session" \
  || echo "  !! danmu-session 重启失败，请手动 systemctl restart danmu-session"

echo "[rollback] 完成"
