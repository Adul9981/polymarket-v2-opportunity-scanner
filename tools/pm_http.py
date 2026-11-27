#!/usr/bin/env python3
"""Polymarket HTTP access with public read-only proxy fallback (2026-10-01).

背景：2026-10-01 起 Polymarket 对本地网络（TLS reset）与云服务器（Cloudflare
HTTP 451 / error 1026）均返回拒绝，直连不可用。本项目只读取**公开**行情数据，
因此按下面的顺序依次尝试，拿到 JSON 即返回：

  1. 直连
  2. 公共出口池（tools/pm_proxy_pool.py，HTTPS 走 CONNECT 隧道，端到端校验）
  3. 公共只读 CORS 代理（cors.lol / jina / allorigins …）兜底

2026-10-01 关键背景：Polymarket 对**韩国出口**返回 Cloudflare 1026 / HTTP 451，
本机（Shadowrocket 韩国节点）与首尔 VPS 都在韩国，直连必然失败；而日本/美国等
公共出口实测可用，因此出口池是第一顺位兜底。

只做 GET；不发送任何凭据、不做写操作。CORS 代理阶段共享最小请求间隔，避免触发限流。
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# name -> url template；{u} = 原样 URL，{e} = URL 编码后的 URL，{q} = 仅 query 部分编码
PROXIES: tuple[tuple[str, str], ...] = (
    ("corsproxy.io", "https://corsproxy.io/?url={e}"),
    ("cors.lol", "https://api.cors.lol/?url={e}"),
    ("jina", "https://r.jina.ai/{u}"),
    ("allorigins", "https://api.allorigins.win/raw?url={e}"),
    ("codetabs", "https://api.codetabs.com/v1/proxy?quest={e}"),
    ("corsproxy.org", "https://corsproxy.org/?url={e}"),
)
MIN_INTERVAL = 3.0          # 公共 CORS 代理（jina 免费档 ~20 req/min）安全节奏
COOLDOWN_SECONDS = 90.0
POOL_TRIES = 4              # 每次请求最多尝试几个出口池地址
POOL_PROXY_TIMEOUT = 20     # 单个出口超时（免费出口参差；索引页 ~500KB，太紧会 IncompleteRead）
_last_call = 0.0
_cooldown: dict[str, float] = {}
STATS = {"direct": 0, "proxy": 0, "pool": 0, "fail": 0, "errors": {}}
LAST_ERRORS: list[str] = []
_pool_cache: list[str] = []
_pool_lock = threading.Lock()
_pool_cursor = 0
_pool_hits: dict[str, int] = {}
_pool_fails: dict[str, int] = {}
_pool_refreshed_at = time.time()   # 进程启动即算一次"新鲜"，避免一上来就重测整池
_executor = ThreadPoolExecutor(max_workers=16)  # 用于给单次请求加"硬超时"
_fanout_executor = ThreadPoolExecutor(max_workers=160)


def _hard_deadline(func, timeout: float):
    """Run func in a worker thread and abandon it if it overruns.

    免费出口常见"细水长流"式卡死：socket 超时只管单次读，不限制总时长，
    所以这里用线程 + 硬 deadline 兜底（放弃的线程自行结束，不阻塞主流程）。
    """
    future = _executor.submit(func)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeout as exc:
        raise TimeoutError(f"hard timeout {timeout:.0f}s") from exc


def _pool() -> list[str]:
    """Lazy-load the public egress pool (see tools/pm_proxy_pool.py)."""
    global _pool_cache
    if _pool_cache:
        return _pool_cache
    with _pool_lock:
        if _pool_cache:
            return _pool_cache
        try:
            import pm_proxy_pool  # noqa: PLC0415

            _pool_cache = pm_proxy_pool.ensure()
        except Exception as exc:  # noqa: BLE001
            _note("pool-load", exc)
            _pool_cache = []
    return _pool_cache


def refresh_pool() -> list[str]:
    """强制重测公共出口池，并替换当前缓存。"""
    global _pool_cache, _pool_refreshed_at, _pool_hits, _pool_fails
    import pm_proxy_pool  # noqa: PLC0415

    payload = pm_proxy_pool.refresh()
    _pool_cache = [item["proxy"] for item in payload.get("working", [])]
    _pool_hits, _pool_fails = {}, {}
    _pool_refreshed_at = time.time()
    return _pool_cache


def _rotate_pool(n: int = POOL_TRIES) -> list[str]:
    """Return up to n pool proxies, rotating the start point so we spread load."""
    global _pool_cursor, _pool_refreshed_at, _pool_cache
    pool = _pool()
    if not pool:
        return []
    now = time.time()
    if not _pool_hits and now - _pool_refreshed_at > 180:
        # 池子长期没有成功记录（免费出口失效快）→ 重测一轮
        _pool_refreshed_at = now
        try:
            import pm_proxy_pool  # noqa: PLC0415

            payload = pm_proxy_pool.refresh()
            _pool_cache = [item["proxy"] for item in payload.get("working", [])]
            pool = _pool_cache
        except Exception as exc:  # noqa: BLE001
            _note("pool-refresh", exc)
    ranked = sorted(pool, key=lambda p: (-_pool_hits.get(p, 0), _pool_fails.get(p, 0)))
    picked: list[str] = []
    for offset in range(len(ranked)):
        proxy = ranked[(_pool_cursor + offset) % len(ranked)]
        if _cooldown.get("pool:" + proxy, 0) > now:
            continue
        if _pool_fails.get(proxy, 0) >= 3:
            continue
        picked.append(proxy)
        if len(picked) >= n:
            break
    _pool_cursor = (_pool_cursor + len(picked)) % max(len(ranked), 1)
    return picked


def _via_proxy(url: str, proxy: str, timeout: int):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": f"http://{proxy}", "https": f"http://{proxy}"})
    )

    def once():
        req = urllib.request.Request(
            url,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "identity",
                "user-agent": UA,
            },
        )
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    return once()


def _throttle() -> None:
    global _last_call
    gap = time.time() - _last_call
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call = time.time()


def _raw(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"accept": "application/json, text/plain, */*", "user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def unwrap_reader(text: str) -> str:
    """r.jina.ai wraps payloads with a small header; keep the JSON body only."""
    for token in ("[{", "{"):
        idx = text.find(token)
        if idx >= 0:
            return text[idx:]
    return text


def _note(name: str, exc: Exception) -> None:
    text = f"{name}: {type(exc).__name__}: {str(exc)[:120]}"
    LAST_ERRORS.append(text)
    STATS["errors"][text.split(":")[0]] = STATS["errors"].get(text.split(":")[0], 0) + 1
    if os.environ.get("PM_HTTP_DEBUG"):
        print(f"[pm_http] {text}", flush=True)
    if isinstance(exc, urllib.error.HTTPError) and exc.code in (429, 403, 503):
        _cooldown[name] = time.time() + COOLDOWN_SECONDS


def warmup(url: str, tries: int = 20, timeout: int = 15, workers: int = 24) -> int:
    """并发试探出口池，把能真正取到该 URL 的出口记为热出口（供后续请求优先使用）。

    免费出口失效快、成功率参差；先花十几秒筛一轮，比让每个请求都去踩雷划算。
    """
    from concurrent.futures import as_completed

    pool = _pool()
    if not pool:
        return 0
    sample = pool if len(pool) <= tries else pool[:: max(len(pool) // tries, 1)][:tries]
    hits = 0
    with ThreadPoolExecutor(max_workers=workers) as pool_exec:
        futures = {pool_exec.submit(_via_proxy, url, proxy, timeout): proxy for proxy in sample}
        try:
            for future in as_completed(futures, timeout=timeout * 3 + 10):
                proxy = futures[future]
                try:
                    data = future.result()
                except Exception:  # noqa: BLE001
                    _pool_fails[proxy] = _pool_fails.get(proxy, 0) + 1
                    continue
                if isinstance(data, (dict, list)):
                    _pool_hits[proxy] = _pool_hits.get(proxy, 0) + 3
                    hits += 1
        except FuturesTimeout:
            pass  # 慢出口直接放弃，已命中的热出口照常使用
    return hits


def get_json_fanout(url: str, k: int = 8, timeout: int = 15, budget: float = 60.0):
    """把一个请求同时打给 k 个出口，取最快成功的结果。

    免费的公共出口存活时间只有几分钟，串行重试（每个 20s 超时）代价太高；
    并发扇出后单次成功率可达 90%+，延迟就是最快出口的延迟（通常 2-7s）。
    """
    from concurrent.futures import as_completed

    pool = _pool()
    if not pool:
        pool = refresh_pool()
    ranked = sorted(pool, key=lambda p: (-_pool_hits.get(p, 0), _pool_fails.get(p, 0)))
    now = time.time()
    # 滚动窗口：不能每次都打同一批，否则热出口会被打爆（2026-10-03 教训）
    global _pool_cursor
    usable = [p for p in ranked if _cooldown.get("pool:" + p, 0) <= now and _pool_fails.get(p, 0) < 3]
    if not usable:
        usable = [p for p in ranked if _pool_fails.get(p, 0) < 6] or ranked
    if not usable:
        STATS["fail"] += 1
        return None
    kk = min(max(k, 1), len(usable))
    start = _pool_cursor % len(usable)
    cands = [usable[(start + i) % len(usable)] for i in range(kk)]
    _pool_cursor = (start + kk) % len(usable)
    futures = {_fanout_executor.submit(_via_proxy, url, proxy, timeout): proxy for proxy in cands}
    try:
        for future in as_completed(futures, timeout=budget):
            proxy = futures[future]
            try:
                data = future.result()
            except Exception as exc:  # noqa: BLE001
                _pool_fails[proxy] = _pool_fails.get(proxy, 0) + 1
                _note("fanout:" + proxy.split(":")[0], exc)
                continue
            if isinstance(data, (dict, list)):
                _pool_hits[proxy] = _pool_hits.get(proxy, 0) + 1
                STATS["pool"] += 1
                return data
    except FuturesTimeout:
        pass
    finally:
        for future in futures:
            future.cancel()
    STATS["fail"] += 1
    return None


def get_json(url: str, timeout: int = 60):


    """GET url and parse JSON, with proxy fallback. Returns None on total failure."""
    _throttle()
    try:
        data = json.loads(_raw(url, timeout))
        STATS["direct"] += 1
        return data
    except Exception as exc:  # noqa: BLE001
        _note("direct", exc)
    for proxy in _rotate_pool(2 if _pool_hits else POOL_TRIES):
        try:
            data = _via_proxy(url, proxy, min(int(timeout), POOL_PROXY_TIMEOUT))
            STATS["pool"] += 1
            _pool_hits[proxy] = _pool_hits.get(proxy, 0) + 1
            if not isinstance(data, (dict, list)):
                raise ValueError(f"unexpected payload {type(data).__name__}")
            return data
        except Exception as exc:  # noqa: BLE001
            _pool_fails[proxy] = _pool_fails.get(proxy, 0) + 1
            _note("pool:" + proxy.split(":")[0], exc)
            continue
    now = time.time()
    for name, template in PROXIES:
        if _cooldown.get(name, 0) > now:
            continue
        _throttle()
        target = template.format(u=url, e=urllib.parse.quote(url, safe=""))
        try:
            body = _hard_deadline(lambda t=target: _raw(t, min(timeout, 20)), min(timeout, 20) + 4)
            if name == "jina":
                body = unwrap_reader(body)
            data = json.loads(body)
            STATS["proxy"] += 1
            return data
        except Exception as exc:  # noqa: BLE001
            _note(name, exc)
            continue
    STATS["fail"] += 1
    return None


def get_json_cors(
    url: str,
    timeout: int = 30,
    names: tuple[str, ...] = ("corsproxy.io",),
):
    """Fetch JSON through explicit public CORS readers, skipping direct/pool.

    CLOB history is frequently blocked on the local egress while Gamma still
    works. Callers that are known to need a CORS reader can avoid spending
    minutes on direct and proxy-pool attempts.
    """
    templates = dict(PROXIES)
    for name in names:
        template = templates.get(name)
        if not template:
            continue
        target = template.format(u=url, e=urllib.parse.quote(url, safe=""))
        for attempt in range(3):
            try:
                if name == "corsproxy.io":
                    result = subprocess.run(
                        [
                            "curl", "-sS", "--compressed",
                            "--max-time", str(min(timeout, 25)),
                            "--get", "--data-urlencode", f"url={url}",
                            "https://corsproxy.io/",
                        ],
                        capture_output=True,
                        timeout=min(timeout, 25) + 3,
                    )
                    if result.returncode != 0 or not result.stdout:
                        raise RuntimeError(
                            result.stderr.decode("utf-8", "ignore")[:160]
                            or f"curl rc={result.returncode}"
                        )
                    body = result.stdout.decode("utf-8", "replace")
                else:
                    body = _hard_deadline(
                        lambda t=target: _raw(t, min(timeout, 25)),
                        min(timeout, 25) + 3,
                    )
                if name == "jina":
                    body = unwrap_reader(body)
                if "rate limit exceeded" in body.lower():
                    _note(name, RuntimeError("rate limit exceeded"))
                    time.sleep(4.0 + attempt * 2.0)
                    continue
                data = json.loads(body)
                STATS["proxy"] += 1
                # Public readers throttle aggressively; keep the batch stable.
                time.sleep(1.0)
                return data
            except Exception as exc:  # noqa: BLE001
                _note(name, exc)
                time.sleep(2.0 + attempt * 1.5)
    return None
if __name__ == "__main__":
    import sys

    payload = get_json(sys.argv[1])
    if payload is None:
        print("FAILED")
        for line in LAST_ERRORS[-4:]:
            print("  ", line)
    else:
        print(json.dumps(payload, ensure_ascii=False)[:600])
