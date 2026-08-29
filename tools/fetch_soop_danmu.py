#!/usr/bin/env python3
"""Fetch live chat (danmaku) from a SOOP (ex-AfreecaTV) broadcast room.

Lightweight collector: no browser. It reuses the protocol the official
player uses:
  1. POST live.sooplive.com/afreeca/player_live_api.php -> chat IP/port/no
  2. Connect wss://chat-<HEXIP>.sooplive.com:<port+1>/Websocket/<bjid>
  3. Binary login (SVC 1) + join channel (SVC 2), then collect SVC 5 chat
     messages (message / user id / nickname) as JSONL.

Dependencies (intel venv /tmp/intel-whisper-venv): websockets, requests

Usage:
  /tmp/intel-whisper-venv/bin/python tools/fetch_soop_danmu.py \
      --url https://play.sooplive.com/afchall/296450537 --seconds 60 \
      --out docs/data/danmu/soop/2026-08-18_afchall.jsonl

--seconds 0 (default) means run until Ctrl-C; every chat line is appended
to --out immediately (safe on interrupt). Only user chat (SVC 5) is kept.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
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
DEBUG = False

# ---- binary chat protocol (from official LivePlayer.js) ----
SEP = b"\x0c"  # R: field separator
HEAD_1 = b"\x1d"  # I
HEAD_2 = b"\t"  # L
UUID = b"00000000-0000-0000-0000-000000000000"

SVC_KEEPALIVE = 0
SVC_LOGIN = 1
SVC_JOINCH = 2
SVC_CHATMESG = 5
GUEST_FLAG = 16


def make_packet(service_code: int, body: bytes) -> bytes:
    header = (
        HEAD_1
        + HEAD_2
        + str(service_code).zfill(4).encode()
        + str(len(body)).zfill(6).encode()
        + b"00"
        + UUID
    )
    return header + body


def login_body(ticket: str = "", nickname: str = "", flag: int = GUEST_FLAG) -> bytes:
    return (
        SEP
        + ticket.encode()
        + SEP
        + nickname.encode("utf-8")
        + SEP
        + str(flag).encode()
        + SEP
    )


def build_log_string(quality: str = "HD", geo_cc: str = "HK", geo_rc: str = "01") -> str:
    """Replicate the official player's getLog()+getAddInfo() join payload."""
    e = "\x06&\x06"
    i = "\x06=\x06"
    log = "log\x11"
    pairs = {
        "set_bps": "8000",
        "view_bps": "8000",
        "quality": quality,
        "uuid": "00000000-0000-0000-0000-000000000000",
        "geo_cc": geo_cc,
        "geo_rc": geo_rc,
        "svc_lang": "ko_KR",
        "subscribe": "0",
        "lowlatency": "0",
    }
    for k, v in pairs.items():
        log += e + k + i + v
    log += "\x12"
    add = ""
    for k, v in {
        "pwd": "",
        "auth_info": "",
        "pver": "2",
        "access_system": "html5",
        "nation_lang": "ko_KR",
    }.items():
        add += k + "\x11" + v + "\x12"
    return log + add


def join_body(
    chat_no: int,
    fan_ticket: str = "",
    ticket: int = 0,
    extra: str = "",
    log: str = "",
) -> bytes:
    return (
        SEP
        + str(chat_no).encode()
        + SEP
        + fan_ticket.encode()
        + SEP
        + str(ticket).encode()
        + SEP
        + extra.encode("utf-8")
        + SEP
        + log.encode()
        + SEP
    )


def keepalive_body() -> bytes:
    return SEP


def decode_utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def parse_message(data: bytes) -> tuple[int, int, str, list[str]]:
    header = data[:50]
    body = data[50:]
    service_code = int(header[2:6])
    ret_code = int(header[12:14])
    chat_unique_id = header[14:50].decode("ascii", errors="replace")
    fields = [decode_utf8(f) for f in body[1:-1].split(SEP)] if body else []
    return service_code, ret_code, chat_unique_id, fields


# ---- room info ----


def fetch_room_info(url: str) -> dict:
    """Resolve a play.sooplive.com/afchall/296450537 URL to chat parameters."""
    m = re.match(r"https?://[^/]+/([^/]+)/(\d+)", url)
    if not m:
        raise ValueError(f"cannot parse SOOP url: {url}")
    bj_id, broad_no = m.group(1), int(m.group(2))
    api = f"https://live.sooplive.com/afreeca/player_live_api.php?bjid={bj_id}"
    data = {
        "bid": bj_id,
        "bno": broad_no,
        "type": "LIVE",
        "pwd": "",
        "player_type": "html5",
        "stream_type": "common",
        "quality": "HD",
        "mode": "live",
        "from_api": "",
        "is_revive": 0,
    }
    s = requests.Session()
    s.trust_env = False  # sandbox proxy can break direct https to SOOP
    r = s.post(
        api,
        data=data,
        headers={
            "User-Agent": UA,
            "Referer": url,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=20,
    )
    r.raise_for_status()
    ch = r.json().get("CHANNEL") or {}
    if not ch.get("CHIP") or not ch.get("CHPT") or not ch.get("CHATNO"):
        raise RuntimeError(f"room info missing chat config: {ch}")
    return {
        "bj_id": bj_id,
        "broad_no": broad_no,
        "chat_no": int(ch["CHATNO"]),
        "chip": ch["CHIP"],
        "chpt": int(ch["CHPT"]),
        "status": ch.get("BSTATUS", ""),
        "title": ch.get("TITLE", ""),
        "bj_nick": ch.get("BJNICK", ""),
    }


def chat_host(room: dict) -> str:
    ip_hex = "".join(f"{int(p):02x}" for p in room["chip"].split(".")).upper()
    return f"chat-{ip_hex}.sooplive.com"


# ---- collector ----


async def collect(url: str, seconds: int, out_path: Path | None) -> int:
    room = fetch_room_info(url)
    host = chat_host(room)
    port = room["chpt"] + 1
    ws_url = f"wss://{host}:{port}/Websocket/{room['bj_id']}"

    print(
        f"[soop] room={room['bj_nick']} title={room['title']} "
        f"status={room['status']} chat_no={room['chat_no']}",
        flush=True,
    )
    print(f"[soop] connect {ws_url}", flush=True)

    fh = open(out_path, "a", encoding="utf-8") if out_path else None
    count = 0
    t0 = time.time()
    reconnect = 0

    extra_headers = {
        "User-Agent": UA,
        "Origin": "https://play.sooplive.com",
    }

    while True:
        if seconds and time.time() - t0 >= seconds:
            break
        if reconnect:
            # chat server may rotate the IP mid-broadcast; re-fetch room info
            try:
                room = fetch_room_info(url)
                host = chat_host(room)
                port = room["chpt"] + 1
                ws_url = f"wss://{host}:{port}/Websocket/{room['bj_id']}"
                print(f"[soop] reconnect #{reconnect}: {ws_url}", flush=True)
            except Exception as e:
                print(f"[soop] reconnect info fetch failed: {e}", flush=True)
                await asyncio.sleep(5)
                continue

        try:
            async with websockets.connect(
                ws_url,
                subprotocols=["chat"],
                additional_headers=extra_headers,
                max_size=1 << 24,
                open_timeout=20,
                ping_interval=None,
            ) as ws:
                await ws.send(make_packet(SVC_LOGIN, login_body()))
                joined = False
                while True:
                    if seconds and time.time() - t0 >= seconds:
                        break
                    try:
                        data = await asyncio.wait_for(ws.recv(), timeout=60)
                    except asyncio.TimeoutError:
                        await ws.send(make_packet(SVC_KEEPALIVE, keepalive_body()))
                        continue
                    if not isinstance(data, (bytes, bytearray)):
                        continue
                    svc, ret, uid, fields = parse_message(bytes(data))

                    if DEBUG:
                        print(
                            f"[soop] SVC={svc} ret={ret} nfields={len(fields)} "
                            f"first={fields[:8]!r}",
                            flush=True,
                        )

                    if svc == SVC_LOGIN and ret == 0:
                        await ws.send(
                            make_packet(
                                SVC_JOINCH,
                                join_body(room["chat_no"], log=build_log_string()),
                            )
                        )
                        continue
                    if svc == SVC_JOINCH and not joined:
                        joined = True
                        print(
                            f"[soop] joined channel chat_no={room['chat_no']}",
                            flush=True,
                        )
                        continue
                    if svc == SVC_CHATMESG and len(fields) >= 6:
                        message = fields[0].replace("\r", "")
                        user_id = fields[1]
                        nickname = fields[5]
                        if not message:
                            continue
                        rec = {
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            "unixtime": int(time.time()),
                            "platform": "soop",
                            "bj_id": room["bj_id"],
                            "broad_no": room["broad_no"],
                            "chat_no": room["chat_no"],
                            "user_id": user_id,
                            "nickname": nickname,
                            "message": message,
                        }
                        if fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            fh.flush()
                        count += 1
                        if count % 20 == 0:
                            print(f"[soop] {count} chat lines ...", flush=True)
        except Exception as e:
            if seconds and time.time() - t0 >= seconds:
                break
            reconnect += 1
            print(f"[soop] connection lost ({e}); will reconnect", flush=True)
            await asyncio.sleep(3)

    if fh:
        fh.close()
    print(f"[soop] done, {count} chat lines, elapsed={time.time()-t0:.0f}s", flush=True)
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="SOOP live chat collector")
    ap.add_argument("--url", required=True, help="https://play.sooplive.com/<bj>/<broad_no>")
    ap.add_argument("--seconds", type=int, default=0, help="0 = until Ctrl-C")
    ap.add_argument("--out", default="", help="JSONL output path")
    ap.add_argument("--debug", action="store_true", help="print every frame")
    args = ap.parse_args()
    global DEBUG
    DEBUG = args.debug
    out = Path(args.out) if args.out else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(collect(args.url, args.seconds, out))


if __name__ == "__main__":
    sys.exit(main())
