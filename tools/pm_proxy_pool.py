#!/usr/bin/env python3
"""免费公共出口池（只读行情用）。

背景（2026-10-01）：Polymarket 对韩国出口返回 Cloudflare 1026 / HTTP 451，
而本机与云服务器当前出口都在韩国（本机经 Shadowrocket 韩国节点、VPS 在首尔）。
实测同为公共出口的日本 / 美国 / 德国等地址可正常访问，因此这里维护一个小型
出口池：定期从公开列表抓取候选、逐个探测 gamma-api，保留能用的。

安全边界：只发 GET，只访问公开行情接口；HTTPS 目标走 CONNECT 隧道，
TLS 端到端校验，代理无法篡改内容；不携带任何凭据。

用法：
  python3 tools/pm_proxy_pool.py --refresh          # 重测并写 runtime/pm_backfill/proxies.json
  python3 tools/pm_proxy_pool.py --show             # 打印当前池
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
POOL_PATH = "runtime/pm_backfill/proxies.json"
PROBE_URL = "https://gamma-api.polymarket.com/markets?limit=1"
MAX_AGE = 25 * 60  # 池超过 25 分钟视为过期

LIST_SOURCES = (
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text&timeout=5000",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text&timeout=5000&country=jp",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text&timeout=5000&country=sg",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text&timeout=5000&country=de",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=ipport&format=text&timeout=5000&country=us",
)


def _get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def gather_candidates() -> list[str]:
    found: list[str] = []
    for src in LIST_SOURCES:
        try:
            text = _get(src)
        except Exception:  # noqa: BLE001
            continue
        for line in text.splitlines():
            line = line.strip()
            if ":" in line and len(line) < 40 and line.count(".") == 3:
                found.append(line)
    return list(dict.fromkeys(found))


def probe(proxy: str, timeout: int = 8) -> tuple[str, bool, float]:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": f"http://{proxy}", "https": f"http://{proxy}"})
    )
    t0 = time.time()
    try:
        req = urllib.request.Request(PROBE_URL, headers={"accept": "application/json", "user-agent": UA})
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read()
        data = json.loads(body)
        if isinstance(data, list) and data:
            return proxy, True, round(time.time() - t0, 2)
    except Exception:  # noqa: BLE001
        pass
    return proxy, False, round(time.time() - t0, 2)


def refresh(workers: int = 80, keep: int = 80) -> dict:
    candidates = gather_candidates()
    print(f"候选出口 {len(candidates)} 个，开始探测…", flush=True)
    good: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for proxy, ok, latency in pool.map(probe, candidates):
            if ok:
                good.append({"proxy": proxy, "latency": latency})
    good.sort(key=lambda item: item["latency"])
    payload = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "working": good[:keep]}
    os.makedirs(os.path.dirname(POOL_PATH), exist_ok=True)
    with open(POOL_PATH, "w") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"可用出口 {len(good)} 个（保留前 {min(len(good), keep)}），已写入 {POOL_PATH}", flush=True)
    return payload


def load(allow_stale: bool = False) -> list[str]:
    try:
        with open(POOL_PATH) as fh:
            payload = json.load(fh)
    except Exception:  # noqa: BLE001
        return []
    checked = payload.get("checked_at") or ""
    fresh = True
    try:
        ts = time.mktime(time.strptime(checked[:19], "%Y-%m-%dT%H:%M:%S"))
        fresh = (time.time() - ts) < MAX_AGE
    except Exception:  # noqa: BLE001
        fresh = False
    if not fresh and not allow_stale:
        return []
    return [item["proxy"] for item in payload.get("working", [])]


def ensure(force: bool = False) -> list[str]:
    pool = [] if force else load()
    if not pool:
        pool = [item["proxy"] for item in refresh()["working"]]
    return pool


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--keep", type=int, default=80, help="保留的最快出口数量")
    args = ap.parse_args()
    if args.refresh:
        refresh(keep=args.keep)
    if args.show or not args.refresh:
        pool = load(allow_stale=True)
        print(f"池内出口 {len(pool)} 个：{pool[:12]}{' …' if len(pool) > 12 else ''}")
