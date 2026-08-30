"""Shared, presentation-independent dashboard data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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


@dataclass(frozen=True)
class BackendDisplay:
    name: str
    healthy: bool | None
    last_checked: str | None


@dataclass(frozen=True)
class RouteDisplay:
    alias: str
    backend_names: tuple[str, ...]
    models: tuple[str, ...]
    max_concurrent: int | None


@dataclass(frozen=True)
class OperationsDisplay:
    mode: Literal["local-demo", "live", "public-demo"]
    source_note: str
    overview_lede: str
    reliability_lede: str
    backend_heading: str
    backend_state: Literal["rows", "offline", "unavailable", "fixture"]
    backend_message: str | None
    backends: tuple[BackendDisplay, ...]
    routes: tuple[RouteDisplay, ...]
