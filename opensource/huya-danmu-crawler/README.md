# 虎牙直播弹幕采集器（Huya Live Danmaku Crawler）

一个轻量的虎牙直播间实时弹幕采集工具：无需浏览器、不下载视频流，
只通过 WebSocket 收取弹幕文本，边抓边写 JSONL，Ctrl-C 中断不丢数据。

> 中文文档为主；English summary below.

## 功能

- 实时抓取单个虎牙直播间弹幕（昵称 / uid / 文本 / 时间戳）
- JSONL 逐条落盘，中断安全，可追加续写
- 只收用户弹幕（过滤礼物、进场等系统消息）
- 无浏览器、无视频流，占用极小，可多直播间并行

## 依赖

- Python 3.10+
- `aiohttp`、`requests`、`pycryptodome`（见 `requirements.txt`）
- 实时协议实现依赖开源项目 [wbt5/real-url](https://github.com/wbt5/real-url)
  （GPL-2.0，作为**外部运行时依赖**安装，不包含在本仓库内）

## 相关链接

- 预测市场 · 电竞板块：[Polymarket Esports](https://polymarket.com/esports?via=serene77mc-g6kj)
  （邀请码 `serene77mc-g6kj`）——弹幕数据可服务于电竞预测市场的集体智慧分析

## 安装

```bash
git clone https://github.com/wbt5/real-url /tmp/real-url
pip install -r requirements.txt
```

若 real-url 不在 `/tmp/real-url`，通过环境变量指定：

```bash
export DANMU_LIB=/path/to/real-url/danmu
```

## 用法

抓取 60 秒：

```bash
python3 fetch_huya_danmu.py --url https://www.huya.com/323444 --seconds 60
```

持续抓取并落盘（Ctrl-C 停止，数据逐条追加写入）：

```bash
python3 fetch_huya_danmu.py --url https://www.huya.com/323444 \
    --out ./danmu/2026-08-18_323444.jsonl
```

同时开多个直播间：每个进程独立运行即可，互不影响。

## 输出格式（JSONL）

```json
{"ts": 1787043336.74, "nick": "昵称", "uid": 1336520926, "text": "弹幕内容"}
{"ts": 1787043340.22, "nick": "昵称2", "uid": 1607219343, "text": "666"}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `ts` | 接收时间戳（Unix 秒） |
| `nick` | 用户昵称 |
| `uid` | 虎牙用户 ID |
| `text` | 弹幕文本 |

## 参数

| 参数 | 说明 |
| --- | --- |
| `--url` | 直播间链接，必填，如 `https://www.huya.com/323444` |
| `--seconds` | 抓取时长（秒）；`0`（默认）= 持续到 Ctrl-C |
| `--out` | JSONL 输出路径；省略则仅打印到终端 |

## 许可与声明

- 本仓库代码以 MIT 许可发布；
- 实时协议实现来自 [wbt5/real-url](https://github.com/wbt5/real-url)（GPL-2.0），
  使用前请遵守其许可条款；
- 本项目仅供学习与技术研究，请遵守虎牙平台及当地法律法规。

---

## English Summary

`fetch_huya_danmu.py` is a lightweight real-time danmaku (live chat) crawler
for Huya (虎牙) live rooms. It connects to the room's WebSocket chat channel
via the [wbt5/real-url](https://github.com/wbt5/real-url) (GPL-2.0) library,
and writes each user message to a JSONL file immediately.

```bash
python3 fetch_huya_danmu.py --url https://www.huya.com/323444 --seconds 60
```

License: MIT (this repo only; real-url dependency is GPL-2.0).
