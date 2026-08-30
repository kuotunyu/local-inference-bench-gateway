"""Map local gateway runtime objects into dashboard-owned presentation contracts."""

from __future__ import annotations

from typing import Literal

from dashboard.data.live_status import GatewayStatus
from dashboard.models import BackendDisplay, OperationsDisplay, RouteDisplay
from gateway.registry import Registry

_OVERVIEW_LEDE = (
    "彙整 Request throughput、latency、routing、Failover 與 Backend Health，"
    "呈現所選觀測時間範圍內可追溯的運行狀態。"
)
_RELIABILITY_LEDE = (
    "對照 Alias Routing、Request-time Failover、Backend Health 與 Backpressure，"
    "檢視路由決策及失效處理。"
)
_OFFLINE_MESSAGE = "仍可閱讀已寫入的 Telemetry；離線不代表歷史 Backend Health 或 SLA。"


def _display_host(url: str) -> str:
    return url.split("//")[-1].split("/")[0]


def operations_display_from_runtime(
    status: GatewayStatus, registry: Registry, *, source_kind: Literal["demo", "live"]
) -> OperationsDisplay:
    """Adapt local health and registry state without exposing endpoint URLs to views."""
    mode = "local-demo" if source_kind == "demo" else "live"
    source_note = "SQLite Telemetry + models.yaml"
    if source_kind == "demo":
        source_note += " · 示範 fixture"

    routes = tuple(
        RouteDisplay(
            alias=alias,
            backend_names=tuple(backend.name for backend in config.backends),
            models=tuple(backend.model for backend in config.backends),
            max_concurrent=config.max_concurrent,
        )
        for alias, config in registry.items()
    )
    if not status.reachable:
        backend_state = "offline"
        backend_message = _OFFLINE_MESSAGE
        backends = ()
    elif not status.backends:
        backend_state = "unavailable"
        backend_message = status.reason
        backends = ()
    else:
        backend_state = "rows"
        backend_message = None
        backends = tuple(
            BackendDisplay(
                name=_display_host(url),
                healthy=bool(entry.get("healthy")),
                last_checked=entry.get("last_checked"),
            )
            for url, entry in status.backends.items()
        )

    return OperationsDisplay(
        mode=mode,
        source_note=source_note,
        overview_lede=_OVERVIEW_LEDE,
        reliability_lede=_RELIABILITY_LEDE,
        backend_heading="Backend Health · 目前觀測",
        backend_state=backend_state,
        backend_message=backend_message,
        backends=backends,
        routes=routes,
    )
