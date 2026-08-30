"""Deterministic, in-memory telemetry used by the public Demo experience."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from dashboard.models import TelemetrySnapshot

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
FAILOVER_COLUMNS = ["id", "timestamp", "alias", "failed_backend", "next_backend", "reason"]


def build_demo_snapshot() -> TelemetrySnapshot:
    """Build the fixed public-demo telemetry without performing I/O."""
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
        request_rows.append(
            (
                index + 1,
                (start + timedelta(minutes=index)).isoformat(),
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
    failover_rows = [
        (
            1,
            (start + timedelta(minutes=17)).isoformat(),
            "fast",
            "llamacpp",
            "ollama",
            "HTTP 503",
        ),
        (
            2,
            (start + timedelta(minutes=41)).isoformat(),
            "fast",
            "llamacpp",
            "ollama",
            "timeout",
        ),
        (
            3,
            (start + timedelta(minutes=49)).isoformat(),
            "smart",
            "ollama-smart",
            None,
            "connection_error",
        ),
    ]
    return TelemetrySnapshot(
        requests=pd.DataFrame(request_rows, columns=REQUEST_COLUMNS),
        failovers=pd.DataFrame(failover_rows, columns=FAILOVER_COLUMNS),
        schema_version=1,
        source_path=Path("deterministic-demo"),
    )


def _canonical_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    normalized = frame.sort_values("id").astype(object)
    normalized = normalized.where(pd.notna(normalized), None)
    return normalized.to_dict(orient="records")


def demo_snapshot_digest(snapshot: TelemetrySnapshot) -> str:
    """Return a stable digest for the public fixture, excluding local file paths."""
    payload = {
        "schema_version": snapshot.schema_version,
        "requests": _canonical_records(snapshot.requests),
        "failovers": _canonical_records(snapshot.failovers),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
