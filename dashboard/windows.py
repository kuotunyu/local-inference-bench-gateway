"""Pure telemetry observation-window transformations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd

from dashboard.models import TelemetrySnapshot


def slice_observation_window(
    snapshot: TelemetrySnapshot,
    minutes: int | None,
    source_kind: Literal["demo", "live"],
) -> TelemetrySnapshot:
    """Return observations inside the requested rolling window."""
    if minutes is None or snapshot.requests.empty:
        return snapshot
    request_times = pd.to_datetime(snapshot.requests["timestamp"], utc=True, errors="coerce")
    if source_kind == "demo" and request_times.notna().any():
        reference = request_times.max().to_pydatetime()
    else:
        reference = datetime.now(timezone.utc)
    cutoff = reference - timedelta(minutes=minutes)
    requests = snapshot.requests.loc[request_times >= cutoff].copy()
    failover_times = pd.to_datetime(snapshot.failovers["timestamp"], utc=True, errors="coerce")
    failovers = snapshot.failovers.loc[failover_times >= cutoff].copy()
    return TelemetrySnapshot(
        requests=requests,
        failovers=failovers,
        schema_version=snapshot.schema_version,
        source_path=snapshot.source_path,
    )
