# 弹幕采集服务器部署（简版）

目标：服务器 24 小时连续抓弹幕，本地定期拉回分析。服务器只做“在场”，不分析。

## 你需要准备的

1. 一台能访问虎牙/SOOP 的 Linux 云服务器（Debian/Ubuntu 最省事，香港/东京轻量机即可）。
2. 一个 SSH 登录方式（密码或密钥）。

## 步骤（照着做，10 分钟）

```bash
# 1) 登录服务器
ssh root@你的服务器IP

# 2) 装 Python 3.11+（Debian/Ubuntu）
apt update && apt install -y python3 python3-venv git rsync

# 3) 把本目录（deploy/danmu_server/）整个上传到服务器
#    在你本地电脑执行：
#    scp -r deploy/danmu_server root@你的服务器IP:/opt/danmu-pkg

# 4) 执行安装脚本（装依赖 + 拉 real-url 协议库 + 建目录）
cd /opt/danmu-pkg && bash install.sh

# 5) 配置要抓的直播间（把模板复制成正式配置再改）
cp rooms.env.example rooms.env
#    编辑 rooms.env，把 ROOMS 改成你要抓的房间，例如：
#    ROOMS="official_660000=https://www.huya.com/660000 we957_890001=https://www.huya.com/890001 shuoshuo_323444=https://www.huya.com/323444"

# 6) 安装并启动服务
cp danmu-capture.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now danmu-capture

# 7) 验证
systemctl status danmu-capture
ls /opt/danmu/docs/data/danmu/huya/          # 应出现 YYYY-MM-DD_来源.jsonl
tail -3 /opt/danmu/docs/data/danmu/huya/$(date +%F)_official_660000.jsonl
```

## 数据落盘位置（固定，别改）

```text
/opt/danmu/docs/data/danmu/huya/YYYY-MM-DD_来源.jsonl   # 虎牙
/opt/danmu/docs/data/danmu/soop/YYYY-MM-DD_来源.jsonl   # SOOP
/opt/danmu/runtime/danmu_sessions/<session>/*.status.json  # 健康状态
```

文件名里的日期固定用**北京时间**（脚本自动换算），保证和本地命名一致，不会错位。

## 常见问题

- 断线：`capture_server.py` 会自动重启每个采集器（10 秒退避），无需人工干预。
- 换房间：改 `rooms.env` 后 `systemctl restart danmu-capture`。
- 升级脚本：重新 scp 三个脚本到 `/opt/danmu/tools/` 后 `systemctl restart danmu-capture`。
- 看日志：`journalctl -u danmu-capture -f`

## 本地拉数据（同步端在你本地电脑上配置，见 deploy/danmu_sync_local/README.md）

```bash
rsync -avz --timeout=30 root@服务器IP:/opt/danmu/docs/data/danmu/huya/ docs/data/danmu/huya/
rsync -avz --timeout=30 root@服务器IP:/opt/danmu/docs/data/danmu/soop/ docs/data/danmu/soop/
```
