#!/usr/bin/env python3
"""Fetch live chat (danmaku) from a Kick.com channel via public APIs.

Two-step pipeline (no auth, no developer app):
  1. GET https://kick.com/api/v2/channels/<slug> -> chatroom.id
  2. Connect Pusher WebSocket (cluster us2, app key rotates occasionally)
     and subscribe chatrooms.<chatroom_id>.v2; parse App\\Events\\ChatMessageEvent
     (data is a JSON string).

Dependencies (intel venv /tmp/intel-whisper-venv): requests, websockets

Usage:
  /tmp/intel-whisper-venv/bin/python tools/fetch_kick_danmu.py \
      --url https://kick.com/eslcs --seconds 60 --out docs/data/danmu/kick/2026-08-24_eslcs.jsonl

--seconds 0 (default) means run until Ctrl-C; each chat line is appended to
--out immediately (safe on interrupt). Only user chat messages are kept.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import websockets

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
# Kick rotates this key occasionally (2024: eb_1d69..., 2026-04+: 32cbd69e...).
# Override with --pusher-key when it rotates again.
PUSHER_KEY = "32cbd69e4b950bf97679"
PUSHER_CLUSTER = "us2"
PUSHER_BASE = f"wss://ws-{PUSHER_CLUSTER}.pusher.com/app/{PUSHER_KEY}"
PUSHER_PARAMS = "?protocol=7&client=js&version=7.4.0&flash=false"


def slug_from_url(url: str) -> str:
    value = url.strip().rstrip("/")
    if "kick.com" in value:
        path = urlparse(value).path.strip("/")
        if path:
            value = path.split("/")[0]
    return value.lower()


def fetch_chatroom(slug: str) -> int:
    resp = requests.get(
        f"https://kick.com/api/v2/channels/{slug}",
        headers={"User-Agent": UA, "Accept": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    chatroom = data.get("chatroom") or {}
    chatroom_id = chatroom.get("id")
    if not chatroom_id:
        raise ValueError(f"chatroom id not found for {slug}")
    return int(chatroom_id)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


def write_status(path: Path | None, payload: dict) -> None:
    if not path:
        return
    payload["recent_msgs"] = list(RECENT[-15:])  # 内容采样：最近 15 条，供切赛感知
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


RECENT: list = []


async def run_capture(
    slug: str,
    seconds: int,
    out: Path,
    status: Path | None = None,
    source: str = "",
    first_message_timeout: int = 120,
    pusher_key: str = PUSHER_KEY,
) -> int:
    import asyncio

    source_id = source or f"kick_{slug}"
    msg_count = 0
    start = time.time()
    deadline = start + seconds if seconds > 0 else None
    out.parent.mkdir(parents=True, exist_ok=True)
    first_msg_alerted = False

    chatroom = fetch_chatroom(slug)
    uri = (
        f"wss://ws-{PUSHER_CLUSTER}.pusher.com/app/{pusher_key}"
        + PUSHER_PARAMS
    )

    with out.open("a", encoding="utf-8") as fh:
        while deadline is None or time.time() < deadline:
            try:
                async with websockets.connect(
                    uri, ssl=ssl.create_default_context(), max_size=2**22, open_timeout=15
                ) as ws:
                    sub = {
                        "event": "pusher:subscribe",
                        "data": {"auth": "", "channel": f"chatrooms.{chatroom}.v2"},
                    }
                    await ws.send(json.dumps(sub))
                    write_status(
                        status,
                        {
                            "channel": slug,
                            "source": source_id,
                            "chatroom_id": chatroom,
                            "connected_at": utc_now(),
                            "messages": msg_count,
                            "state": "connected",
                        },
                    )
                    last_status_at = time.time()
                    while deadline is None or time.time() < deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=30)
                        except asyncio.TimeoutError:
                            continue
                        try:
                            obj = json.loads(raw)
                        except Exception:
                            continue
                        if obj.get("event") != "App\\Events\\ChatMessageEvent":
                            continue
                        payload = obj.get("data")
                        if isinstance(payload, str):
                            try:
                                payload = json.loads(payload)
                            except Exception:
                                continue
                        if not isinstance(payload, dict):
                            continue
                        content = payload.get("content") or ""
                        sender = (payload.get("sender") or {})
                        username = sender.get("username") or sender.get("slug") or ""
                        record = {
                            "platform": "kick",
                            "channel": slug,
                            "source": source_id,
                            "user": username,
                            "nick": username,
                            "text": content,
                            "ts": utc_now(),
                            "message_id": payload.get("id", ""),
                        }
                        if payload.get("created_at"):
                            record["created_at"] = payload["created_at"]
                        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                        fh.flush()
                        RECENT.append({"t": content[:80], "ts": round(time.time(), 2)})
                        del RECENT[:-15]
                        msg_count += 1
                        if not first_msg_alerted:
                            first_msg_alerted = True
                        if time.time() - last_status_at >= 30:
                            last_status_at = time.time()
                            write_status(
                                status,
                                {
                                    "channel": slug,
                                    "source": source_id,
                                    "chatroom_id": chatroom,
                                    "connected_at": utc_now(),
                                    "messages": msg_count,
                                    "state": "connected",
                                },
                            )
                    elapsed = time.time() - start
                    if (
                        not first_msg_alerted
                        and first_message_timeout > 0
                        and elapsed >= first_message_timeout
                    ):
                        first_msg_alerted = True
                        write_status(
                            status,
                            {
                                "channel": slug,
                                "source": source_id,
                                "chatroom_id": chatroom,
                                "connected_at": utc_now(),
                                "messages": msg_count,
                                "state": f"alert: no first message within {first_message_timeout}s",
                            },
                        )
            except Exception as exc:
                write_status(
                    status,
                    {
                        "channel": slug,
                        "source": source_id,
                        "chatroom_id": chatroom,
                        "connected_at": utc_now(),
                        "messages": msg_count,
                        "state": f"reconnecting: {exc}",
                    },
                )
                time.sleep(5)

    write_status(
        status,
        {
            "channel": slug,
            "source": source_id,
            "chatroom_id": chatroom,
            "connected_at": utc_now(),
            "messages": msg_count,
            "state": "finished",
        },
    )
    return msg_count


def main() -> int:
    import asyncio

    ap = argparse.ArgumentParser(description="Kick.com chat collector")
    ap.add_argument("--url", default="", help="https://kick.com/<slug>")
    ap.add_argument("--channel", default="", help="channel slug (alternative to --url)")
    ap.add_argument("--seconds", type=int, default=0, help="0 = run until Ctrl-C")
    ap.add_argument("--out", required=True, help="JSONL output path")
    ap.add_argument("--status", default="", help="optional status JSON path")
    ap.add_argument("--source", default="", help="stable source id written to each record")
    ap.add_argument("--first-message-timeout", type=int, default=120)
    ap.add_argument("--pusher-key", default=PUSHER_KEY)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    slug = slug_from_url(args.url or args.channel)
    if not slug:
        print("error: need --url or --channel", file=sys.stderr)
        return 2
    status = Path(args.status) if args.status else None
    count = asyncio.run(
        run_capture(
            slug,
            args.seconds,
            Path(args.out),
            status=status,
            source=args.source,
            first_message_timeout=args.first_message_timeout,
            pusher_key=args.pusher_key,
        )
    )
    print(f"captured {count} messages from {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
