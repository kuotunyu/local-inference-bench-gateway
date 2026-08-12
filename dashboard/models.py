"""Shared, presentation-independent dashboard data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


@dataclass(frozen=True)
class BenchmarkEvidence:
    concurrency: pd.DataFrame
    prefill: pd.DataFrame
    overhead: dict[str, Any]
    provenance: dict[str, Any]
    claims: dict[str, Any]
    kv_cache_off: list[dict[str, Any]]
    kv_cache_on: list[dict[str, Any]]
    warnings: dict[str, str]
