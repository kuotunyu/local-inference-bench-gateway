"""Deterministic, explicitly illustrative telemetry for first-run Demo Mode."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal

from dashboard.data.public_demo import build_demo_snapshot
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
    snapshot = build_demo_snapshot()
    request_rows = snapshot.requests.drop(columns=["id"]).itertuples(index=False, name=None)
    failover_rows = snapshot.failovers.drop(columns=["id"]).itertuples(index=False, name=None)
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
            failover_rows,
        )
        conn.commit()
    temporary.replace(target)
    return target


def select_default_mode(live_path: Path) -> Literal["live", "demo"]:
    return "live" if inspect_schema(live_path).compatible else "demo"
