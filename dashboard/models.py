"""Shared, presentation-independent dashboard data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class SchemaStatus:
    compatible: bool
    detected_version: int | None
    reason: str | None = None


@dataclass(frozen=True)
class TelemetrySnapshot:
    requests: pd.DataFrame
    failovers: pd.DataFrame
    schema_version: int
    source_path: Path
