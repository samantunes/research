"""SQLite persistence: cache, quota ledger, audit logs and seen-results registry."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key         TEXT PRIMARY KEY,
    response    TEXT NOT NULL,
    created_at  REAL NOT NULL,
    expires_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);

CREATE TABLE IF NOT EXISTS quota_ledger (
    provider    TEXT NOT NULL,
    period      TEXT NOT NULL,          -- YYYY-MM (UTC)
    used        REAL NOT NULL DEFAULT 0, -- units counted locally (reserved before each call)
    reported    REAL,                    -- units reported by the provider, when available
    calls       INTEGER NOT NULL DEFAULT 0,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (provider, period)
);

CREATE TABLE IF NOT EXISTS requests (
    id          TEXT PRIMARY KEY,
    ts          REAL NOT NULL,
    query       TEXT NOT NULL,
    category    TEXT NOT NULL,
    depth       TEXT NOT NULL,
    cache_hit   INTEGER NOT NULL,
    paid_calls  INTEGER NOT NULL,
    n_results   INTEGER NOT NULL,
    latency_ms  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_calls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id   TEXT NOT NULL,
    ts           REAL NOT NULL,
    provider     TEXT NOT NULL,
    status       TEXT NOT NULL,
    latency_ms   INTEGER NOT NULL,
    count        INTEGER NOT NULL,
    units        REAL NOT NULL,
    detail       TEXT,
    unresponsive TEXT
);
CREATE INDEX IF NOT EXISTS idx_pc_provider_ts ON provider_calls(provider, ts);

CREATE TABLE IF NOT EXISTS results_seen (
    canonical_url TEXT PRIMARY KEY,
    url           TEXT NOT NULL,
    title         TEXT,
    first_seen    REAL NOT NULL,
    last_seen     REAL NOT NULL,
    hits          INTEGER NOT NULL DEFAULT 1,
    providers     TEXT NOT NULL
);
"""


class Database:
    """Thin thread-safe wrapper. Writes are short; a single lock is enough at this scale."""

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """Serialised write transaction (BEGIN IMMEDIATE)."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params))

    # --- audit -----------------------------------------------------------------
    def log_request(self, *, request_id: str, query: str, category: str, depth: str, cache_hit: bool,
                    paid_calls: int, n_results: int, latency_ms: int, provider_reports: list[dict]) -> None:
        now = time.time()
        with self.tx() as c:
            c.execute(
                "INSERT OR REPLACE INTO requests VALUES (?,?,?,?,?,?,?,?,?)",
                (request_id, now, query, category, depth, int(cache_hit), paid_calls, n_results, latency_ms),
            )
            for r in provider_reports:
                c.execute(
                    "INSERT INTO provider_calls (request_id, ts, provider, status, latency_ms, count, units,"
                    " detail, unresponsive) VALUES (?,?,?,?,?,?,?,?,?)",
                    (request_id, now, r["name"], r["status"], r["latency_ms"], r["count"], r["units"],
                     r.get("detail"), json.dumps(r.get("unresponsive_engines") or [])),
                )

    def record_seen(self, results: list[dict]) -> None:
        now = time.time()
        with self.tx() as c:
            for r in results:
                c.execute(
                    "INSERT INTO results_seen (canonical_url, url, title, first_seen, last_seen, hits, providers)"
                    " VALUES (?,?,?,?,?,1,?)"
                    " ON CONFLICT(canonical_url) DO UPDATE SET last_seen=excluded.last_seen, hits=hits+1",
                    (r["canonical_url"], r["url"], r.get("title"), now, now, json.dumps(r.get("providers", []))),
                )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
