#!/usr/bin/env python3
"""Minimal site traffic stats server for danmu-intel (VPS side).

HTTP 服务（默认 8080）：
  POST /track  body {"page": "...", "ref": "...", "visitor": "...", "site": "danmu|musk|..."}
              + header X-Stats-Secret
        -> 追加一行到 runtime/stats/events.jsonl
  POST /lead   body {"name","contact","plan","note"} + header X-Stats-Secret
        -> 追加一行到 runtime/leads.jsonl（订阅登记留痕，2026-08-26 新增）
  GET  /stats?secret=...&site=...  -> 按站点聚合统计 JSON（今日 / 本周(近7天) /
                             累计 的 PV 与去重访客数 + 近14天逐日 + 页面排行）
       不传 site = 全部站点合并（兼容旧调用）。
  GET  /leads?secret=...  -> 订阅登记明细（按时间倒序，供对账/待处理查询）

由 systemd 常驻（stats-server.service）。密钥见环境变量 STATS_SECRET
（systemd 单元内配置，与 Vercel api/track 共享）。
"""

from __future__ import annotations

import datetime
import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/opt/danmu-intel")
EVENTS = ROOT / "runtime" / "stats" / "events.jsonl"
LEADS = ROOT / "runtime" / "leads.jsonl"
SECRET = os.environ.get("STATS_SECRET", "")


def record(page: str, ref: str = "", visitor: str = "", site: str = "") -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds"),
        "page": (page or "/")[:200],
        "ref": (ref or "")[:200],
        "visitor": (visitor or "")[:64],
        "site": (site or "")[:32],
    }
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_lead(name: str, contact: str, plan: str, note: str) -> None:
    """订阅登记留痕（2026-08-26：表单只推 TG 无记录，漏通知即丢；现在落盘可审计）。"""
    LEADS.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds"),
        "name": (name or "")[:100],
        "contact": (contact or "")[:100],
        "plan": (plan or "")[:60],
        "note": (note or "")[:200],
    }
    with open(LEADS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def leads() -> dict:
    out: list[dict] = []
    if LEADS.exists():
        for line in LEADS.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    out.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return {"leads": out, "total": len(out)}


def stats(site: str = "") -> dict:
    pages = Counter()
    total = 0
    today = datetime.date.today().isoformat()
    today_count = 0
    visitors: set[str] = set()
    today_visitors: set[str] = set()
    week_count = 0
    week_visitors: set[str] = set()
    week_start = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()
    days: dict[str, dict] = {}
    if EVENTS.exists():
        for line in EVENTS.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if site and str(r.get("site") or "") != site:
                continue
            total += 1
            pages[r.get("page", "/")] += 1
            day = (r.get("ts") or "")[:10]
            is_today = day == today
            if is_today:
                today_count += 1
            if day >= week_start:
                week_count += 1
            v = str(r.get("visitor") or "").strip()
            if v:
                visitors.add(v)
                if is_today:
                    today_visitors.add(v)
                if day >= week_start:
                    week_visitors.add(v)
            if day:
                d = days.setdefault(day, {"views": 0, "visitors": set()})
                d["views"] += 1
                if v:
                    d["visitors"].add(v)
    day_rows = [
        {"date": day, "views": d["views"], "visitors": len(d["visitors"])}
        for day, d in sorted(days.items())[-14:]
    ]
    return {
        "date": today,
        "site": site or None,
        "total_views": total,
        "today_views": today_count,
        "total_visitors": len(visitors),
        "today_visitors": len(today_visitors),
        "week_views": week_count,
        "week_visitors": len(week_visitors),
        "days": day_rows,
        "top_pages": pages.most_common(15),
    }


def members() -> dict:
    path = ROOT / "members.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"members": []}


class Handler(BaseHTTPRequestHandler):
    def _auth(self) -> bool:
        return SECRET and self.headers.get("X-Stats-Secret", "") == SECRET

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        if self.path not in ("/track", "/lead") or not self._auth():
            self._json(401, {"error": "unauthorized"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}
        if self.path == "/lead":
            record_lead(
                data.get("name", ""),
                data.get("contact", ""),
                data.get("plan", ""),
                data.get("note", ""),
            )
            self._json(200, {"ok": True})
            return
        record(
            data.get("page", ""),
            data.get("ref", ""),
            data.get("visitor", ""),
            data.get("site", ""),
        )
        self._json(200, {"ok": True})

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/members"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            if params.get("secret") != SECRET:
                self._json(401, {"error": "unauthorized"})
                return
            self._json(200, members())
            return
        if self.path.startswith("/stats"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            if params.get("secret") != SECRET:
                self._json(401, {"error": "unauthorized"})
                return
            self._json(200, stats(params.get("site", "")))
            return
        if self.path.startswith("/leads"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            if params.get("secret") != SECRET:
                self._json(401, {"error": "unauthorized"})
                return
            self._json(200, leads())
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *args):  # noqa: D102
        pass


def main() -> None:
    port = int(os.environ.get("STATS_PORT", "8080"))
    if not SECRET:
        print("STATS_SECRET not set")
        raise SystemExit(1)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
