"""Nonfatal application-state assembly and observation-window slicing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.sqlite_repository import (
    IncompatibleSchema,
    TelemetryUnavailable,
    load_snapshot,
)
from dashboard.models import TelemetrySnapshot
from dashboard.windows import slice_observation_window  # noqa: F401


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
                "Live 模式暫時無法使用，已安全切換至 Demo 模式。"
                f"{exc}。請先執行 `uv run uvicorn gateway.app:app --host 127.0.0.1 --port 9000`，"
                "並確認 `GATEWAY_DB_PATH` 指向 Gateway 寫入的 SQLite；"
                "修正後再切回 Live 模式，不需刪除或重建現有資料庫。",
            )
    return AppTelemetryState(load_snapshot(ensure_demo_database(demo_directory)), "demo")
