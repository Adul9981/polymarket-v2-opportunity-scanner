#!/usr/bin/env python3
"""Fetch live chat (danmaku) from a Twitch channel via anonymous IRC.

Zero-dependency collector (stdlib only): connects to irc.chat.twitch.tv:6697
with a "justinfan" anonymous nick, JOINs the target channel and appends every
PRIVMSG as JSONL. No token, no developer app, no third-party library.

Usage:
  python3 tools/fetch_twitch_danmu.py \
      --url https://www.twitch.tv/lec --seconds 60 --out /tmp/lec.jsonl
  python3 tools/fetch_twitch_danmu.py \
      --channel lec --out docs/data/danmu/twitch/2026-08-24_lec.jsonl

--seconds 0 (default) means run until Ctrl-C; each chat line is appended to
--out immediately (safe on interrupt). Only PRIVMSG user chat is kept.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import socket
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697


def channel_from_url(url: str) -> str:
    """Accept https://www.twitch.tv/lec or plain channel name -> 'lec'."""
    value = url.strip().rstrip("/")
    if "twitch.tv" in value:
        path = urlparse(value).path.strip("/")
        value = path.split("/")[0] if path else value
    return value.lower().lstrip("#")


def parse_tags(prefix: str) -> dict:
    """Parse the IRCv3 tags block preceding a PRIVMSG (if present)."""
    tags: dict = {}
    if not prefix.startswith("@"):
        return tags
    for part in prefix[1:].split(";"):
        if "=" in part:
            key, _, val = part.partition("=")
            tags[key] = val.replace("\\s", " ").replace("\\:", ";").replace("\\\\", "\\")
        else:
            tags[part] = ""
    return tags


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


def run_capture(
    channel: str,
    seconds: int,
    out: Path,
    status: Path | None = None,
    verbose: bool = False,
    source: str = "",
    first_message_timeout: int = 120,
) -> int:
    nick = "justinfan%d" % random.randint(10000, 99999)
    msg_count = 0
    start = time.time()
    deadline = start + seconds if seconds > 0 else None
    out.parent.mkdir(parents=True, exist_ok=True)
    source_id = source or f"twitch_{channel}"
    first_msg_alerted = False

    with out.open("a", encoding="utf-8") as fh:
        while deadline is None or time.time() < deadline:
            try:
                sock = socket.create_connection((IRC_HOST, IRC_PORT), timeout=15)
                ctx = ssl.create_default_context()
                conn = ctx.wrap_socket(sock, server_hostname=IRC_HOST)
                conn.settimeout(30)
                conn.sendall(b"CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
                conn.sendall(f"PASS SCHMOOPIIE\r\nNICK {nick}\r\n".encode())
                conn.sendall(f"JOIN #{channel}\r\n".encode())
                write_status(
                    status,
                    {
                        "channel": channel,
                        "source": source_id,
                        "connected_at": utc_now(),
                        "messages": msg_count,
                        "state": "connected",
                    },
                )
                if verbose:
                    print(f"[twitch] connected #{channel} as {nick}", flush=True)

                buf = b""
                last_status_at = time.time()
                last_msg_at = time.time()
                while deadline is None or time.time() < deadline:
                    try:
                        chunk = conn.recv(65536)
                    except socket.timeout:
                        # 连接假死检测：超过 60 秒无任何数据即主动重连
                        if time.time() - last_msg_at > 60:
                            write_status(
                                status,
                                {
                                    "channel": channel,
                                    "source": source_id,
                                    "connected_at": utc_now(),
                                    "messages": msg_count,
                                    "state": "alert: silent connection (>60s no data), reconnecting",
                                },
                            )
                            break
                        continue
                    if not chunk:
                        break
                    last_msg_at = time.time()
                    buf += chunk
                    while b"\r\n" in buf:
                        line, buf = buf.split(b"\r\n", 1)
                        text = line.decode("utf-8", "replace")
                        if text.startswith("PING"):
                            conn.sendall(b"PONG :tmi.twitch.tv\r\n")
                            continue
                        if " PRIVMSG " not in text:
                            continue
                        msg_count += 1
                        try:
                            tags_part, _, rest = text.partition(" ")
                            tags = parse_tags(tags_part)
                            user = tags.get("display-name", "")
                            user_id = tags.get("user-id", "")
                            body = text.split(" PRIVMSG ", 1)[1].split(" :", 1)[1]
                            record = {
                                "platform": "twitch",
                                "channel": channel,
                                "source": source_id,
                                "user": user,
                                "nick": user,
                                "user_id": user_id,
                                "text": body,
                                "ts": utc_now(),
                            }
                            if tags.get("tmi-sent-ts"):
                                record["sent_ts_ms"] = tags["tmi-sent-ts"]
                            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                            fh.flush()
                            RECENT.append({"t": body[:80], "ts": round(time.time(), 2)})
                            del RECENT[:-15]
                            if (
                                not first_msg_alerted
                                and first_message_timeout > 0
                                and msg_count == 1
                            ):
                                first_msg_alerted = True
                        except (IndexError, ValueError):
                            continue
                    if time.time() - last_status_at >= 30:
                        last_status_at = time.time()
                        write_status(
                            status,
                            {
                                "channel": channel,
                                "source": source_id,
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
                                "channel": channel,
                                "source": source_id,
                                "connected_at": utc_now(),
                                "messages": msg_count,
                                "state": f"alert: no first message within {first_message_timeout}s",
                            },
                        )
            except (OSError, ssl.SSLError, socket.error) as exc:
                write_status(
                    status,
                    {
                        "channel": channel,
                        "source": source_id,
                        "connected_at": utc_now(),
                        "messages": msg_count,
                        "state": f"reconnecting: {exc}",
                    },
                )
                if verbose:
                    print(f"[twitch] reconnect ({exc})", flush=True)
                time.sleep(5)

    write_status(
        status,
        {
            "channel": channel,
            "source": source_id,
            "connected_at": utc_now(),
            "messages": msg_count,
            "state": "finished",
        },
    )
    return msg_count


def main() -> int:
    ap = argparse.ArgumentParser(description="Twitch anonymous IRC danmaku collector")
    ap.add_argument("--url", default="", help="https://www.twitch.tv/<channel>")
    ap.add_argument("--channel", default="", help="channel name (alternative to --url)")
    ap.add_argument("--seconds", type=int, default=0, help="0 = run until Ctrl-C")
    ap.add_argument("--out", required=True, help="JSONL output path")
    ap.add_argument("--status", default="", help="optional status JSON path")
    ap.add_argument("--source", default="", help="stable source id written to each record")
    ap.add_argument("--first-message-timeout", type=int, default=120)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    channel = channel_from_url(args.url or args.channel)
    if not channel:
        print("error: need --url or --channel", file=sys.stderr)
        return 2
    status = Path(args.status) if args.status else None
    count = run_capture(
        channel,
        args.seconds,
        Path(args.out),
        status=status,
        verbose=args.verbose,
        source=args.source,
        first_message_timeout=args.first_message_timeout,
    )
    print(f"captured {count} messages from #{channel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
