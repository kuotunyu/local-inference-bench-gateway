"""SQLite request/failover logging.

Each write opens its own short-lived connection rather than sharing one across the FastAPI
process -- sqlite3 connections aren't safe to share across threads, and log_request()/
log_failover_event() run inside Starlette's threadpool (via run_in_threadpool) so concurrent
requests could otherwise write from different threads at once. A short-lived connection per
write sidesteps that entirely; SQLite's own file locking serializes the actual writes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from starlette.concurrency import run_in_threadpool

DEFAULT_DB_PATH = Path("data/gateway.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alias TEXT NOT NULL,
    backend_name TEXT,
    model TEXT,
    stream INTEGER NOT NULL,
    status_code INTEGER,
    success INTEGER NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    ttft_ms REAL,
    total_latency_ms REAL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS failover_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alias TEXT NOT NULL,
    failed_backend TEXT NOT NULL,
    next_backend TEXT,
    reason TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(path: Path = DEFAULT_DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _write_request(path: Path, fields: dict) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            INSERT INTO requests
                (timestamp, alias, backend_name, model, stream, status_code, success,
                 prompt_tokens, completion_tokens, ttft_ms, total_latency_ms, error_message)
            VALUES (:timestamp, :alias, :backend_name, :model, :stream, :status_code, :success,
                    :prompt_tokens, :completion_tokens, :ttft_ms, :total_latency_ms, :error_message)
            """,
            fields,
        )
        conn.commit()
    finally:
        conn.close()


async def log_request(
    path: Path,
    *,
    alias: str,
    backend_name: str | None,
    model: str | None,
    stream: bool,
    status_code: int | None,
    success: bool,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    ttft_ms: float | None = None,
    total_latency_ms: float | None = None,
    error_message: str | None = None,
) -> None:
    fields = {
        "timestamp": _now_iso(),
        "alias": alias,
        "backend_name": backend_name,
        "model": model,
        "stream": int(stream),
        "status_code": status_code,
        "success": int(success),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "ttft_ms": ttft_ms,
        "total_latency_ms": total_latency_ms,
        "error_message": error_message,
    }
    await run_in_threadpool(_write_request, path, fields)


def _write_failover_event(path: Path, fields: dict) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            INSERT INTO failover_events (timestamp, alias, failed_backend, next_backend, reason)
            VALUES (:timestamp, :alias, :failed_backend, :next_backend, :reason)
            """,
            fields,
        )
        conn.commit()
    finally:
        conn.close()


async def log_failover_event(
    path: Path, *, alias: str, failed_backend: str, next_backend: str | None, reason: str
) -> None:
    fields = {
        "timestamp": _now_iso(),
        "alias": alias,
        "failed_backend": failed_backend,
        "next_backend": next_backend,
        "reason": reason,
    }
    await run_in_threadpool(_write_failover_event, path, fields)
