#!/usr/bin/env python3
"""Fetch live danmaku from a Huya room via the real-url WebSocket client.

Lightweight live-danmaku collector (no browser, no protocol reverse-engineering):
reuses the open-source Tars/WebSocket implementation from
https://github.com/wbt5/real-url (clone kept at /tmp/real-url/danmu).

Dependencies (installed in the intel venv /tmp/intel-whisper-venv):
  aiohttp, requests, pycryptodome

Usage:
  /tmp/intel-whisper-venv/bin/python tools/fetch_huya_danmu.py \
      --url https://www.huya.com/323444 --seconds 60 --out /tmp/danmu.json
  /tmp/intel-whisper-venv/bin/python tools/fetch_huya_danmu.py \
      --url https://www.huya.com/323444 --out docs/data/danmu/2026-08-17.jsonl

--seconds 0 (default) means run until Ctrl-C; each danmaku is appended to
--out as JSONL immediately (safe on interrupt). Only user danmaku (text) is
collected; gifts / enters are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

import aiohttp

# real-url's protobuf usage needs the pure-Python implementation on this env
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# 虎牙弹幕实现来自开源 real-url 项目：部署包 vendor 优先，其次本地 /tmp 路径。
VENDOR_DANMU = Path(__file__).resolve().parent.parent / "vendor" / "real-url_danmu"
DANMU_LIB = VENDOR_DANMU if VENDOR_DANMU.exists() else Path("/tmp/real-url/danmu")


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def write_status(path: Path | None, payload: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _json_text(page: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}":"((?:\\.|[^"\\])*)"', page)
    if not match:
        return ""
    try:
        return json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return match.group(1)


async def fetch_room_info(url: str) -> dict:
    """Read the public mobile page so zero messages are not misclassified."""
    room_key = url.rstrip("/").split("/")[-1]
    # desktop page exposes profileRoom/lChannelId reliably; mobile page lacks profileRoom
    page_url = f"https://www.huya.com/{room_key}"
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )
    }
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(page_url) as response:
            response.raise_for_status()
            page = await response.text()
    # Some room pages serialize these ids as quoted strings (e.g. uid 1199652774074),
    # and some pages expose yyid instead of lChannelId (e.g. room 149361), so
    # tolerate optional quotes and fall back to yyid.
    profile = re.search(r'"profileRoom":\s*"?(\d+)"?', page)
    channel = re.search(r'"lChannelId":\s*"?(\d+)"?', page)
    if not channel:
        channel = re.search(r'"yyid":\s*"?(\d+)"?', page)
    live = "liveStatus-on" in page
    if not channel:
        raise RuntimeError("虎牙房间页缺少 profileRoom/lChannelId，可能是房间失效或页面协议变化")
    return {
        "room_id": int(profile.group(1)) if profile else int(channel.group(1)),
        "channel_id": int(channel.group(1)),
        "nickname": _json_text(page, "nick"),
        "introduction": _json_text(page, "introduction"),
        "room_name": _json_text(page, "roomName"),
        "page_live": live,
        "checked_at": utc_now(),
    }


async def collect(
    url: str,
    seconds: int,
    out_path: Path | None,
    status_path: Path | None = None,
    source: str = "",
    first_message_timeout: int = 120,
) -> int:
    sys.path.insert(0, str(DANMU_LIB))
    from danmaku import DanmakuClient  # local import: external lib

    started_at = utc_now()
    status = {
        "schema_version": 1,
        "platform": "huya",
        "source": source or url.rstrip("/").split("/")[-1],
        "url": url,
        "state": "preflight",
        "started_at": started_at,
        "heartbeat_at": started_at,
        "last_message_at": None,
        "message_count": 0,
        "warning": None,
        "error": None,
    }
    write_status(status_path, status)
    room_info = await fetch_room_info(url)
    status.update(room_info)
    status["state"] = "live_waiting_danmaku" if room_info["page_live"] else "offline_waiting"
    status["heartbeat_at"] = utc_now()
    write_status(status_path, status)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(out_path, "a", encoding="utf-8") if out_path else None
    start = time.time()
    count = 0
    if not room_info["page_live"]:
        # offline room: heartbeat + offline_waiting, do not connect (the lib
        # crashes with NoneType.group() on offline pages)
        try:
            while not seconds or time.time() - start < seconds:
                await asyncio.sleep(10)
                status["heartbeat_at"] = utc_now()
                status["state"] = "offline_waiting"
                status["warning"] = "页面显示未开播，继续等待；不得判定为无弹幕"
                write_status(status_path, status)
        except KeyboardInterrupt:
            pass
        return 0

    q: asyncio.Queue = asyncio.Queue()
    dc = DanmakuClient(url, q)

    async def pump() -> None:
        nonlocal count
        while True:
            if seconds and time.time() - start >= seconds:
                break
            try:
                m = await asyncio.wait_for(q.get(), timeout=1)
                if m["msg_type"] == "danmaku":
                    count += 1
                    now = utc_now()
                    rec = {
                        "ts": round(time.time(), 2),
                        "nick": m.get("name", ""),
                        "uid": m.get("uid", 0),
                        "text": m["content"],
                        "source": status["source"],
                        "room_id": room_info["room_id"],
                    }
                    print(f"[{count}] {m['name']}: {m['content']}", flush=True)
                    if fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        fh.flush()
                    status.update(
                        state="capturing",
                        heartbeat_at=now,
                        last_message_at=now,
                        message_count=count,
                        warning=None,
                    )
                    write_status(status_path, status)
            except asyncio.TimeoutError:
                elapsed = time.time() - start
                status["heartbeat_at"] = utc_now()
                if count == 0 and elapsed >= first_message_timeout:
                    if room_info["page_live"]:
                        status["state"] = "live_no_danmaku_alert"
                        status["warning"] = (
                            f"页面显示开播，但 {int(elapsed)} 秒未收到弹幕；"
                            "需检查弹幕连接或直播间活跃度，禁止判定为无信号"
                        )
                    else:
                        status["state"] = "offline_waiting"
                        status["warning"] = "页面显示未开播，继续等待；不得判定为无弹幕"
                write_status(status_path, status)

    pump_task = asyncio.create_task(pump())
    start_task = asyncio.create_task(dc.start())
    try:
        done, _ = await asyncio.wait(
            {pump_task, start_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if start_task in done:
            await start_task
            if not pump_task.done():
                raise RuntimeError("虎牙弹幕连接意外结束")
        await pump_task
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        status.update(state="error", heartbeat_at=utc_now(), error=str(exc))
        write_status(status_path, status)
        raise
    finally:
        for task in (pump_task, start_task):
            if not task.done():
                task.cancel()
        try:
            await dc.stop()
        except Exception:
            pass
        await asyncio.gather(pump_task, start_task, return_exceptions=True)
        if fh:
            fh.close()
    status.update(state="stopped", heartbeat_at=utc_now(), message_count=count)
    write_status(status_path, status)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="虎牙直播间实时弹幕抓取（轻量）")
    parser.add_argument("--url", required=True, help="直播间链接，如 https://www.huya.com/323444")
    parser.add_argument("--seconds", type=int, default=0, help="抓取时长（秒，0=持续到 Ctrl-C）")
    parser.add_argument("--out", default=None, help="JSONL 输出路径（可选，边抓边写）")
    parser.add_argument("--status", default=None, help="健康状态 JSON（原子更新）")
    parser.add_argument("--source", default="", help="稳定来源标识，写入每条弹幕")
    parser.add_argument(
        "--first-message-timeout",
        type=int,
        default=120,
        help="开播后多少秒仍无弹幕则告警（默认 120）",
    )
    args = parser.parse_args()

    try:
        count = asyncio.run(
            collect(
                args.url,
                args.seconds,
                Path(args.out) if args.out else None,
                Path(args.status) if args.status else None,
                args.source,
                args.first_message_timeout,
            )
        )
    except Exception as exc:
        print(f"[ERROR] 虎牙弹幕抓取失败：{exc}", file=sys.stderr, flush=True)
        return 2
    label = f"{args.seconds}s" if args.seconds else "本次会话"
    print(f"\n== {label} 共 {count} 条弹幕 ==")
    if args.out:
        print(f"数据已追加：{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
