"""Nonfatal application-state assembly and observation-window slicing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.sqlite_repository import (
    IncompatibleSchema,
    TelemetryUnavailable,
    load_snapshot,
)
from dashboard.models import TelemetrySnapshot


@dataclass(frozen=True)
class AppTelemetryState:
    snapshot: TelemetrySnapshot
    source_kind: Literal["demo", "live"]
    notice: str | None = None


def load_telemetry_state(
    requested_mode: Literal["demo", "live"], live_path: Path, demo_directory: Path
) -> AppTelemetryState:
    if requested_mode == "live":
        try:
            return AppTelemetryState(load_snapshot(live_path), "live")
        except (TelemetryUnavailable, IncompatibleSchema) as exc:
            snapshot = load_snapshot(ensure_demo_database(demo_directory))
            return AppTelemetryState(
                snapshot,
                "demo",
                f"Live Mode 暫時無法使用，已安全切換 Demo Mode。{exc}",
            )
    return AppTelemetryState(load_snapshot(ensure_demo_database(demo_directory)), "demo")


def slice_observation_window(
    snapshot: TelemetrySnapshot,
    minutes: int | None,
    source_kind: Literal["demo", "live"],
) -> TelemetrySnapshot:
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
