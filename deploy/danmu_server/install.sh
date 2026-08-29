#!/usr/bin/env bash
set -euo pipefail

# 弹幕采集服务器一键安装：环境 + 依赖 + real-url 协议库 + 目录
APP=/opt/danmu
PKG="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] 创建目录 $APP"
mkdir -p "$APP/tools" "$APP/docs/data/danmu/huya" "$APP/docs/data/danmu/soop" \
         "$APP/runtime/danmu_sessions"

echo "[2/4] 复制采集脚本"
cp "$PKG/fetch_huya_danmu.py" "$PKG/fetch_soop_danmu.py" "$PKG/capture_server.py" "$APP/tools/"
chmod +x "$APP/tools/"*.py

echo "[3/4] 安装 Python 依赖（venv: $APP/venv）"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --upgrade pip -q
"$APP/venv/bin/pip" install -r "$PKG/requirements.txt" -q

echo "[4/4] 拉取 real-url 协议库（/tmp/real-url）"
if [ ! -d /tmp/real-url/.git ]; then
  git clone --depth 1 https://github.com/wbt5/real-url /tmp/real-url
else
  git -C /tmp/real-url pull -q || true
fi

echo "完成。下一步：cp rooms.env.example rooms.env 并编辑 ROOMS，然后装 systemd 服务。"
