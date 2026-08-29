# 本地自动同步（已配好，只差填服务器地址）

1. 编辑 `config/danmu_sync.json`，把 `host` 填成服务器 IP。
2. 注册定时任务（每 5 分钟同步一次，开机自动跑）：

```bash
cp deploy/danmu_sync_local/com.ad.danmu-sync.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ad.danmu-sync.plist
```

3. 手动同步/排查：

```bash
python3 tools/sync_danmu_from_server.py --dry-run   # 预演
python3 tools/sync_danmu_from_server.py             # 正式同步
tail -20 /tmp/danmu-sync.log                        # 看同步日志
```

说明：
- 同步是 rsync 增量，只拉服务器上新增的部分，数据量很小。
- host 为空时脚本静默退出，不会报错刷日志。
- 服务器上线后，本地电脑那套采集可以停掉（避免同一天两个源写同一个文件）。
