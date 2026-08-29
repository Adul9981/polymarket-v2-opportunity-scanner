#!/bin/bash
set -euo pipefail
# Danmu Intel VPS deploy (Ubuntu 22.04 / 24.04) —— 临时过渡方案：VPS 只做弹幕采集
APP=/opt/danmu-intel
sudo mkdir -p "$APP"/{data,reports,site,logs}
# 若 zip 已解压到 $APP 内直接运行，跳过复制（避免 cp: same file 报错退出）
if [ "$(pwd)" != "$APP" ]; then
  sudo cp -r tools config schemas knowledge "$APP/"
fi
sudo cp runtime/systemd/*.service runtime/systemd/*.timer /etc/systemd/system/
sudo mkdir -p /tmp/intel-whisper-venv/bin
sudo ln -sf "$APP/.venv/bin/python" /tmp/intel-whisper-venv/bin/python
cd "$APP"
# 虚拟环境组件（Ubuntu 24.04 必需，幂等）
sudo apt-get install -y -qq python3-venv >/dev/null 2>&1 || true
python3 -m venv .venv
.venv/bin/pip install -q -r "$APP/requirements.txt"
sudo systemctl daemon-reload
# 过渡方案：只启用采集常驻；分析/情报/发布全部在本地
sudo systemctl enable --now danmu-session.service
echo "deployed（过渡方案：仅采集常驻）。检查：systemctl status danmu-session.service"
