from pathlib import Path

import pytest

from dashboard.data.sqlite_repository import (
    FAILOVER_COLUMNS,
    REQUEST_COLUMNS,
    IncompatibleSchema,
    TelemetryUnavailable,
    inspect_schema,
    load_snapshot,
)
from gateway.db import init_db


def test_missing_database_is_unavailable_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.db"
    with pytest.raises(TelemetryUnavailable, match="找不到 Live telemetry"):
        load_snapshot(path)
    assert not path.exists()


def test_load_snapshot_reads_empty_gateway_schema(tmp_path: Path) -> None:
    path = tmp_path / "gateway.db"
    init_db(path)

    snapshot = load_snapshot(path)

    assert snapshot.schema_version == 1
    assert list(snapshot.requests.columns) == REQUEST_COLUMNS
    assert list(snapshot.failovers.columns) == FAILOVER_COLUMNS
    assert snapshot.source_path == path


def test_incompatible_schema_is_reported_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    path.write_bytes(b"")

    status = inspect_schema(path)

    assert status.compatible is False
    assert status.detected_version == 0
    with pytest.raises(IncompatibleSchema, match="schema version 0"):
        load_snapshot(path)
