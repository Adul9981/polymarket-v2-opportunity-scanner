#!/usr/bin/env python3
"""Backfill SOOP (ex-AfreecaTV) VOD chat history as JSONL.

SOOP keeps the full chat log of a broadcast in its VOD. Once a broadcast
ends and the VOD is published, this tool pages through the chat split API
(every 300 seconds) and writes each message with its offset-in-VOD time.

Verified 2026-08-18 against [CC] NS vs DK | 2026 LCK CL ROUND 4 VOD.

Usage:
  /tmp/intel-whisper-venv/bin/python tools/fetch_soop_vod_chat.py \
      --bj afchall --title-no 204038307 \
      --out docs/data/danmu/soop/vod_20260811_NS-DK.jsonl
  # latest VOD of the BJ if --title-no omitted:
  /tmp/intel-whisper-venv/bin/python tools/fetch_soop_vod_chat.py \
      --bj afchall --out docs/data/danmu/soop/vod_latest.jsonl

Dependencies (intel venv): requests, xml.etree (stdlib)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from requests.exceptions import RequestException

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
VOD_API = "https://bjapi.afreecatv.com/api/{bj}/vods/all"
CHAT_API = "https://videoimg.sooplive.com/php/ChatLoadSplit.php"
CHUNK = 300  # seconds per ChatLoadSplit page


def http_get(url: str, retries: int = 4, **kw) -> requests.Response:
    s = requests.Session()
    s.trust_env = False
    last: RequestException | None = None
    for attempt in range(retries):
        try:
            r = s.get(url, headers={"User-Agent": UA}, timeout=30, **kw)
            r.raise_for_status()
            return r
        except RequestException as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def list_vods(bj: str, limit: int = 60) -> list[dict]:
    out: list[dict] = []
    page = 1
    while page <= 5 and len(out) < limit:
        r = http_get(VOD_API.format(bj=bj), params={"page": page, "per_page": 60})
        data = r.json().get("data") or []
        if not data:
            break
        out.extend(data)
        page += 1
    return out[:limit]


def row_key_from_vod(vod: dict) -> str | None:
    thumb = (vod.get("ucc") or {}).get("thumb") or ""
    m = re.search(r"rowKey=([0-9A-Za-z_]+)_r", thumb)
    return m.group(1) if m else None


def fetch_chunk(row_key: str, start_sec: int) -> list[dict]:
    r = http_get(
        CHAT_API,
        params={"rowKey": f"{row_key}_c", "startTime": start_sec},
    )
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return []
    chats = []
    for c in root.findall("chat"):
        def g(tag: str) -> str:
            e = c.find(tag)
            return e.text if e is not None and e.text is not None else ""

        try:
            t = float(g("t"))
        except ValueError:
            continue
        msg = g("m")
        if not msg:
            continue
        chats.append(
            {
                "time_sec": round(t, 3),
                "user_id": g("u"),
                "nickname": g("n"),
                "message": msg,
                "flag": g("p"),
                "flag2": g("p2"),
                "lang": g("l"),
                "msg_type": g("mt"),
            }
        )
    return chats


def backfill(bj: str, title_no: int | None, out_path: Path, max_sec: int | None) -> int:
    vods = list_vods(bj)
    if not vods:
        raise RuntimeError(f"no VODs found for {bj}")
    vod = next((v for v in vods if v.get("title_no") == title_no), None) if title_no else vods[0]
    if not vod:
        raise RuntimeError(f"title_no {title_no} not found for {bj}")

    row_key = row_key_from_vod(vod)
    if not row_key:
        raise RuntimeError("cannot extract chat rowKey from VOD record")
    total_ms = int((vod.get("ucc") or {}).get("total_file_duration") or 0)
    total_sec = min(total_ms // 1000, max_sec or 10 ** 9)

    print(
        f"[soop-vod] {vod.get('title_name')} title_no={vod.get('title_no')} "
        f"rowKey={row_key} duration={total_sec}s",
        flush=True,
    )

    fh = open(out_path, "w", encoding="utf-8")
    count = 0
    start = 0
    while start <= total_sec:
        for rec in fetch_chunk(row_key, start):
            rec["platform"] = "soop_vod"
            rec["bj_id"] = bj
            rec["title_no"] = vod.get("title_no")
            rec["title"] = vod.get("title_name")
            rec["vod_time_sec"] = rec.pop("time_sec")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
        start += CHUNK
        if start % 1500 == 0:
            print(f"[soop-vod] ... {start}s / {total_sec}s, {count} lines", flush=True)
        time.sleep(0.2)  # be gentle with the split API
    fh.close()
    print(f"[soop-vod] done, {count} chat lines", flush=True)
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="SOOP VOD chat backfill")
    ap.add_argument("--bj", required=True, help="SOOP BJ id, e.g. afchall")
    ap.add_argument("--title-no", type=int, default=None, help="VOD title_no (broad no); default latest")
    ap.add_argument("--max-sec", type=int, default=None, help="only first N seconds (debug)")
    ap.add_argument("--out", required=True, help="JSONL output path")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    backfill(args.bj, args.title_no, out, args.max_sec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
