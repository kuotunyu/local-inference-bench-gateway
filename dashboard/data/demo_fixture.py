"""Deterministic, explicitly illustrative telemetry for first-run Demo Mode."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from dashboard.data.sqlite_repository import inspect_schema
from gateway.db import init_db


def ensure_demo_database(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "demo-gateway-v1.db"
    if inspect_schema(target).compatible:
        return target
    temporary = directory / "demo-gateway-v1.tmp.db"
    if temporary.exists():
        temporary.unlink()
    init_db(temporary)
    start = datetime(2026, 8, 12, 16, 45, tzinfo=timezone.utc)
    request_rows = []
    for index in range(60):
        alias = "fast" if index % 3 else "smart"
        backend = (
            "ollama-smart" if alias == "smart" else ("ollama" if index in {17, 41} else "llamacpp")
        )
        status, success, error = 200, 1, None
        if index == 11:
            status, success, error = None, 0, "connection_error"
        elif index == 23:
            status, success, error = 503, 0, "HTTP 503"
        elif index == 37:
            status, success, error = 429, 0, "HTTP 429"
        elif index == 49:
            status, success, error = None, 0, "timeout"
        timestamp = (start + timedelta(minutes=index)).isoformat()
        request_rows.append(
            (
                timestamp,
                alias,
                backend if success else None,
                "bench-model" if alias == "fast" else "qwen3:8b",
                index % 2,
                status,
                success,
                None if index % 10 == 0 else 120 + index,
                None if index % 12 == 0 else 40 + index,
                None if index % 5 == 0 else 65.0 + index * 2.8,
                150.0 + index * 9.3,
                error,
            )
        )
    with closing(sqlite3.connect(temporary)) as conn:
        conn.executemany(
            """INSERT INTO requests
            (timestamp, alias, backend_name, model, stream, status_code, success,
             prompt_tokens, completion_tokens, ttft_ms, total_latency_ms, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            request_rows,
        )
        conn.executemany(
            """INSERT INTO failover_events
            (timestamp, alias, failed_backend, next_backend, reason) VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    (start + timedelta(minutes=17)).isoformat(),
                    "fast",
                    "llamacpp",
                    "ollama",
                    "HTTP 503",
                ),
                (
                    (start + timedelta(minutes=41)).isoformat(),
                    "fast",
                    "llamacpp",
                    "ollama",
                    "timeout",
                ),
                (
                    (start + timedelta(minutes=49)).isoformat(),
                    "smart",
                    "ollama-smart",
                    None,
                    "connection_error",
                ),
            ],
        )
        conn.commit()
    temporary.replace(target)
    return target


def select_default_mode(live_path: Path) -> Literal["live", "demo"]:
    return "live" if inspect_schema(live_path).compatible else "demo"
