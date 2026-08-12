"""Read-only SQLite access for gateway telemetry."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd

from dashboard.models import SchemaStatus, TelemetrySnapshot

SCHEMA_VERSION = 1
REQUEST_COLUMNS = [
    "id",
    "timestamp",
    "alias",
    "backend_name",
    "model",
    "stream",
    "status_code",
    "success",
    "prompt_tokens",
    "completion_tokens",
    "ttft_ms",
    "total_latency_ms",
    "error_message",
]
FAILOVER_COLUMNS = [
    "id",
    "timestamp",
    "alias",
    "failed_backend",
    "next_backend",
    "reason",
]


class TelemetryUnavailable(RuntimeError):
    """The configured live telemetry source cannot be read."""


class IncompatibleSchema(RuntimeError):
    """The database does not match the supported gateway schema."""


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise TelemetryUnavailable(f"找不到 Live telemetry：{path}")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True, timeout=2.0)
    except sqlite3.Error as exc:
        raise TelemetryUnavailable("Live telemetry 暫時無法讀取") from exc


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def inspect_schema(path: Path) -> SchemaStatus:
    if not path.is_file():
        return SchemaStatus(False, None, "database_missing")
    try:
        with closing(_connect_read_only(path)) as conn:
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            requests_ok = set(REQUEST_COLUMNS) <= _table_columns(conn, "requests")
            failovers_ok = set(FAILOVER_COLUMNS) <= _table_columns(conn, "failover_events")
    except (sqlite3.Error, TelemetryUnavailable):
        return SchemaStatus(False, None, "database_unreadable")
    compatible = version == SCHEMA_VERSION and requests_ok and failovers_ok
    return SchemaStatus(
        compatible,
        version,
        None if compatible else "schema_incompatible",
    )


def load_snapshot(path: Path) -> TelemetrySnapshot:
    status = inspect_schema(path)
    if status.detected_version is None and not path.is_file():
        raise TelemetryUnavailable(f"找不到 Live telemetry：{path}")
    if status.reason == "database_unreadable":
        raise TelemetryUnavailable("Live telemetry 暫時無法讀取")
    if not status.compatible:
        version = "unknown" if status.detected_version is None else status.detected_version
        raise IncompatibleSchema(f"不支援的 telemetry schema version {version}；預期為 1")
    try:
        with closing(_connect_read_only(path)) as conn:
            requests = pd.read_sql_query("SELECT * FROM requests ORDER BY id DESC", conn).reindex(
                columns=REQUEST_COLUMNS
            )
            failovers = pd.read_sql_query(
                "SELECT * FROM failover_events ORDER BY id DESC", conn
            ).reindex(columns=FAILOVER_COLUMNS)
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        raise TelemetryUnavailable("Live telemetry 暫時無法讀取") from exc
    return TelemetrySnapshot(requests, failovers, SCHEMA_VERSION, path)
