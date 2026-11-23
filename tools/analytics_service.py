#!/usr/bin/env python3
"""First-party anonymous analytics service for the Danmu Intel site.

Stores an anonymous browser visitor ID, a tab-scoped session ID and aggregate
activity. Raw IP addresses are never stored; only a salted hash is retained for
basic abuse controls. The public stats endpoint returns aggregates only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo


HOST = "127.0.0.1"
PORT = int(os.environ.get("DANMU_ANALYTICS_PORT", "8772"))
DB_PATH = Path(
    os.environ.get(
        "DANMU_ANALYTICS_DB", "/var/lib/danmu-analytics/analytics.sqlite3"
    )
)
CST = ZoneInfo("Asia/Shanghai")
BOT_RE = re.compile(
    r"bot|crawler|spider|headless|uptime|monitor|curl|wget|python-requests|"
    r"go-http-client|scrapy|facebookexternalhit|slackbot|bingpreview",
    re.IGNORECASE,
)
ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,100}$")
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:[-_][A-Za-z0-9]{1,8})*$")
TIMEZONE_RE = re.compile(r"^[A-Za-z0-9_+\-/]{1,80}$")
ALLOWED_LINKS = {"polymarket_market", "telegram", "youtube", "github"}
RATE_LOCK = threading.Lock()
RATE_BUCKETS: dict[str, tuple[int, int]] = {}


def utc_iso(value: datetime | None = None) -> str:
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def local_day(value: datetime | None = None) -> str:
    value = value or datetime.now(timezone.utc)
    return value.astimezone(CST).date().isoformat()


def is_allowed_path(path: str) -> bool:
    """Only count pages served by this site, never arbitrary external paths."""
    return (
        path in {"/", "/index.html"}
        or path.startswith("/intel/")
        or path.startswith("/preview/")
    )


def load_or_create_secret() -> str:
    secret_path = DB_PATH.parent / "salt"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if not secret_path.exists():
        secret_path.write_text(os.urandom(32).hex(), encoding="utf-8")
        secret_path.chmod(0o600)
    return secret_path.read_text(encoding="utf-8").strip()


SALT = load_or_create_secret()


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def ensure_column(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    columns = {
        row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
    if column not in columns:
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


def init_db() -> None:
    with connect_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                first_path TEXT NOT NULL,
                first_referrer TEXT NOT NULL DEFAULT '',
                is_bot INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                visitor_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                page_views INTEGER NOT NULL DEFAULT 0,
                max_scroll_pct INTEGER NOT NULL DEFAULT 0,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                ip_hash TEXT NOT NULL,
                is_bot INTEGER NOT NULL DEFAULT 0,
                language TEXT NOT NULL DEFAULT '',
                timezone TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS visitor_days (
                day TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                PRIMARY KEY (day, visitor_id)
            );
            CREATE TABLE IF NOT EXISTS session_days (
                day TEXT NOT NULL,
                session_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                page_views INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, session_id)
            );
            CREATE TABLE IF NOT EXISTS page_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                day TEXT NOT NULL,
                path TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                referrer_host TEXT NOT NULL DEFAULT '',
                is_bot INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS outbound_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                day TEXT NOT NULL,
                link_id TEXT NOT NULL,
                path TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                is_bot INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_visitor_days_day ON visitor_days(day, visitor_id);
            CREATE INDEX IF NOT EXISTS idx_session_days_day ON session_days(day);
            CREATE INDEX IF NOT EXISTS idx_sessions_last_seen ON sessions(last_seen);
            CREATE INDEX IF NOT EXISTS idx_page_views_day ON page_views(day, path);
            CREATE INDEX IF NOT EXISTS idx_outbound_day ON outbound_clicks(day, link_id);
            """
        )
        # Existing installations predate the language/timezone columns.
        ensure_column(conn, "sessions", "language", "TEXT NOT NULL DEFAULT ''")
        ensure_column(conn, "sessions", "timezone", "TEXT NOT NULL DEFAULT ''")
    try:
        DB_PATH.chmod(0o640)
    except OSError:
        pass


def client_ip(headers) -> str:
    forwarded = headers.get("X-Real-IP", "").strip()
    if forwarded:
        return forwarded
    chain = headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    return chain


def hash_ip(ip: str) -> str:
    return hashlib.sha256((SALT + ip).encode("utf-8")).hexdigest()[:24]


def user_agent(headers) -> str:
    return headers.get("User-Agent", "")[:500]


def classify_bot(agent: str) -> bool:
    return not agent or agent == "-" or bool(BOT_RE.search(agent))


def rate_limited(ip_hash: str) -> bool:
    minute = int(datetime.now(timezone.utc).timestamp()) // 60
    with RATE_LOCK:
        bucket, count = RATE_BUCKETS.get(ip_hash, (minute, 0))
        if bucket != minute:
            bucket, count = minute, 0
        count += 1
        RATE_BUCKETS[ip_hash] = (bucket, count)
        if len(RATE_BUCKETS) > 5000:
            RATE_BUCKETS.clear()
        return count > 180


def normalize_referrer_host(value: str) -> str:
    try:
        return urlsplit(value).hostname or ""
    except ValueError:
        return ""


def normalize_language(value: str) -> str:
    value = value.strip()[:32]
    return value if LANGUAGE_RE.fullmatch(value) else ""


def normalize_timezone(value: str) -> str:
    value = value.strip()[:80]
    return value if TIMEZONE_RE.fullmatch(value) else ""


def track_event(payload: dict, headers) -> tuple[int, dict]:
    visitor_id = str(payload.get("visitorId", ""))
    session_id = str(payload.get("sessionId", ""))
    event_type = str(payload.get("event", ""))
    path = str(payload.get("path", "/"))
    path = path.split("?", 1)[0][:300]
    referrer_host = normalize_referrer_host(str(payload.get("referrer", "")))[:200]
    if not ID_RE.fullmatch(visitor_id) or not ID_RE.fullmatch(session_id):
        return 400, {"ok": False, "error": "invalid visitor or session id"}
    if event_type not in {"page_view", "heartbeat", "page_hide", "outbound_click"}:
        return 400, {"ok": False, "error": "invalid event"}
    if not is_allowed_path(path):
        return 400, {"ok": False, "error": "invalid path"}
    agent = user_agent(headers)
    link_id = str(payload.get("linkId", ""))[:80]
    language = normalize_language(str(payload.get("language", "")))
    timezone_name = normalize_timezone(str(payload.get("timezone", "")))
    if event_type == "outbound_click" and link_id not in ALLOWED_LINKS:
        return 400, {"ok": False, "error": "invalid link id"}
    bot = classify_bot(agent)
    ip_hash = hash_ip(client_ip(headers))
    if rate_limited(ip_hash):
        return 429, {"ok": False, "error": "rate limited"}

    try:
        duration_ms = max(0, min(int(payload.get("durationMs") or 0), 86_400_000))
        max_scroll = max(0, min(int(payload.get("maxScrollPct") or 0), 100))
    except (TypeError, ValueError):
        duration_ms, max_scroll = 0, 0

    now = datetime.now(timezone.utc)
    now_text = utc_iso(now)
    day = local_day(now)
    with connect_db() as conn:
        existing = conn.execute(
            "SELECT first_seen FROM visitors WHERE visitor_id = ?", (visitor_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE visitors SET last_seen = ? WHERE visitor_id = ?",
                (now_text, visitor_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO visitors
                    (visitor_id, first_seen, last_seen, first_path, first_referrer, is_bot)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (visitor_id, now_text, now_text, path, referrer_host, int(bot)),
            )

        session = conn.execute(
            "SELECT started_at, page_views FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        page_view_increment = int(event_type == "page_view")
        if session:
            started = datetime.fromisoformat(session["started_at"])
            duration_seconds = max(int((now - started).total_seconds()), duration_ms // 1000)
            conn.execute(
                """
                UPDATE sessions
                SET last_seen = ?, page_views = page_views + ?,
                    max_scroll_pct = MAX(max_scroll_pct, ?),
                    duration_seconds = MAX(duration_seconds, ?),
                    language = CASE WHEN ? <> '' THEN ? ELSE language END,
                    timezone = CASE WHEN ? <> '' THEN ? ELSE timezone END
                WHERE session_id = ?
                """,
                (
                    now_text,
                    page_view_increment,
                    max_scroll,
                    duration_seconds,
                    language,
                    language,
                    timezone_name,
                    timezone_name,
                    session_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO sessions
                    (session_id, visitor_id, started_at, last_seen, page_views,
                     max_scroll_pct, duration_seconds, ip_hash, is_bot, language, timezone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, visitor_id, now_text, now_text, page_view_increment,
                    max_scroll, duration_ms // 1000, ip_hash, int(bot), language,
                    timezone_name,
                ),
            )

        conn.execute(
            """
            INSERT INTO visitor_days (day, visitor_id, first_seen, last_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(day, visitor_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (day, visitor_id, now_text, now_text),
        )
        conn.execute(
            """
            INSERT INTO session_days
                (day, session_id, visitor_id, first_seen, last_seen, page_views)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(day, session_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                page_views = session_days.page_views + excluded.page_views
            """,
            (day, session_id, visitor_id, now_text, now_text, page_view_increment),
        )
        if event_type == "page_view":
            conn.execute(
                """
                INSERT INTO page_views
                    (occurred_at, day, path, visitor_id, session_id, referrer_host, is_bot)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now_text, day, path, visitor_id, session_id, referrer_host, int(bot)),
            )
        elif event_type == "outbound_click":
            conn.execute(
                """
                INSERT INTO outbound_clicks
                    (occurred_at, day, link_id, path, visitor_id, session_id, is_bot)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now_text, day, link_id, path, visitor_id, session_id, int(bot)),
            )
    return 200, {"ok": True}


def stats_payload(days: int) -> dict:
    days = days if days in {1, 7, 30, 90} else 1
    now_local = datetime.now(CST)
    start_local = datetime.combine(
        (now_local - timedelta(days=days - 1)).date(),
        datetime.min.time(),
        tzinfo=CST,
    )
    end_local = now_local + timedelta(seconds=1)
    start = utc_iso(start_local)
    end = utc_iso(end_local)
    since_5m = utc_iso(datetime.now(timezone.utc) - timedelta(minutes=5))
    start_day = start_local.date().isoformat()
    with connect_db() as conn:
        unique_visitors = conn.execute(
            """
            SELECT COUNT(DISTINCT vd.visitor_id)
            FROM visitor_days vd JOIN visitors v ON v.visitor_id = vd.visitor_id
            WHERE vd.day >= ? AND vd.day <= ? AND v.is_bot = 0
            """,
            (start_day, now_local.date().isoformat()),
        ).fetchone()[0]
        sessions = conn.execute(
            """
            SELECT COUNT(DISTINCT sd.session_id)
            FROM session_days sd JOIN sessions s ON s.session_id = sd.session_id
            WHERE sd.day >= ? AND sd.day <= ? AND s.is_bot = 0
            """,
            (start_day, now_local.date().isoformat()),
        ).fetchone()[0]
        page_views = conn.execute(
            """
            SELECT COUNT(*) FROM page_views
            WHERE occurred_at >= ? AND occurred_at < ? AND is_bot = 0
            """,
            (start, end),
        ).fetchone()[0]
        returning = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT vd.visitor_id
                FROM visitor_days vd JOIN visitors v ON v.visitor_id = vd.visitor_id
                WHERE vd.day >= ? AND vd.day <= ? AND v.is_bot = 0
                  AND v.first_seen < ?
            )
            """,
            (start_day, now_local.date().isoformat(), start),
        ).fetchone()[0]
        active_visitors = conn.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) FROM sessions
            WHERE last_seen >= ? AND is_bot = 0
            """,
            (since_5m,),
        ).fetchone()[0]
        active_sessions = conn.execute(
            """
            SELECT COUNT(*) FROM sessions
            WHERE last_seen >= ? AND is_bot = 0
            """,
            (since_5m,),
        ).fetchone()[0]
        avg_seconds = conn.execute(
            """
            SELECT COALESCE(AVG(MAX(0, duration_seconds)), 0)
            FROM sessions
            WHERE last_seen >= ? AND last_seen < ? AND is_bot = 0
            """,
            (start, end),
        ).fetchone()[0]
        daily_rows = conn.execute(
            """
            SELECT vd.day,
                   COUNT(DISTINCT vd.visitor_id) AS visitors,
                   COUNT(DISTINCT sd.session_id) AS sessions,
                   COALESCE(SUM(sd.page_views), 0) AS page_views
            FROM visitor_days vd
            JOIN visitors v ON v.visitor_id = vd.visitor_id AND v.is_bot = 0
            LEFT JOIN session_days sd ON sd.day = vd.day AND sd.visitor_id = vd.visitor_id
            WHERE vd.day >= ? AND vd.day <= ?
            GROUP BY vd.day ORDER BY vd.day
            """,
            (start_day, now_local.date().isoformat()),
        ).fetchall()
        pages = conn.execute(
            """
            SELECT path, COUNT(*) AS views, COUNT(DISTINCT visitor_id) AS visitors
            FROM page_views
            WHERE occurred_at >= ? AND occurred_at < ? AND is_bot = 0
            GROUP BY path ORDER BY views DESC LIMIT 200
            """,
            (start, end),
        ).fetchall()
        outbound = conn.execute(
            """
            SELECT link_id,
                   COUNT(*) AS clicks,
                   COUNT(DISTINCT visitor_id) AS visitors
            FROM outbound_clicks
            WHERE occurred_at >= ? AND occurred_at < ? AND is_bot = 0
            GROUP BY link_id ORDER BY clicks DESC
            """,
            (start, end),
        ).fetchall()
    return {
        "ok": True,
        "generatedAt": utc_iso(),
        "timezone": "Asia/Shanghai",
        "rangeDays": days,
        "overview": {
            "uniqueVisitors": unique_visitors,
            "sessions": sessions,
            "pageViews": page_views,
            "returningVisitors": returning,
            "activeNow5m": active_visitors,
            "activeVisitors5m": active_visitors,
            "activeSessions5m": active_sessions,
            "avgSessionSeconds": round(float(avg_seconds or 0), 1),
        },
        "daily": [dict(row) for row in daily_rows],
        "pages": [dict(row) for row in pages],
        "outbound": [dict(row) for row in outbound],
        "methodology": {
            "visitor": "浏览器 localStorage 中随机生成的匿名 visitorId",
            "session": "sessionStorage 中的标签页会话 ID，60 秒心跳续期",
            "active": "activeVisitors5m 是最近 5 分钟去重访客；activeSessions5m 是活跃标签页会话",
            "ip": "不保存原始 IP；仅保存加盐哈希用于限流",
            "excluded": "明显自动化 User-Agent 不进入公开统计",
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DanmuIntelAnalytics/1.0"

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/intel/api/health":
            self.send_json(200, {"ok": True, "service": "danmu-intel-analytics"})
            return
        if parsed.path == "/intel/api/stats":
            query = parse_qs(parsed.query)
            try:
                days = int((query.get("days") or ["1"])[0])
            except ValueError:
                days = 1
            self.send_json(200, stats_payload(days))
            return
        self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/intel/api/track":
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 16_384)
        except ValueError:
            length = 0
        if length <= 0:
            self.send_json(400, {"ok": False, "error": "empty body"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("object required")
            status, result = track_event(payload, self.headers)
        except (ValueError, json.JSONDecodeError):
            status, result = 400, {"ok": False, "error": "invalid json"}
        self.send_json(status, result)


def main() -> None:
    init_db()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
