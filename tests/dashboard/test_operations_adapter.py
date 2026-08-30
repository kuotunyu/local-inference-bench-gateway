from datetime import datetime, timezone

from dashboard.data.live_status import GatewayStatus
from dashboard.data.operations_adapter import operations_display_from_runtime
from dashboard.data.public_demo import build_demo_operations
from gateway.registry import build_registry


def _registry():
    return build_registry(
        {
            "models": {
                "fast": {
                    "max_concurrent": 4,
                    "backends": [
                        {
                            "name": "llamacpp",
                            "base_url": "http://127.0.0.1:8080/v1",
                            "model": "bench-model",
                        },
                        {
                            "name": "ollama",
                            "base_url": "http://127.0.0.1:11434/v1",
                            "model": "bench-model-c",
                        },
                    ],
                },
                "smart": {
                    "backends": [
                        {
                            "name": "ollama-smart",
                            "base_url": "http://127.0.0.1:11434/v1",
                            "model": "qwen3:8b",
                        }
                    ]
                },
            }
        }
    )


def _checked_at() -> datetime:
    return datetime(2026, 8, 12, 17, 45, tzinfo=timezone.utc)


def test_public_demo_operations_have_no_urls_or_current_health_copy() -> None:
    """Fails if public fixture presentation exposes local-health semantics or URLs."""
    display = build_demo_operations()

    assert display.mode == "public-demo"
    assert display.backend_heading == "Fixture backend state"
    assert display.backend_state == "fixture"
    assert [route.alias for route in display.routes] == ["fast", "smart"]
    assert display.routes[0].backend_names == ("llamacpp", "ollama")
    assert display.routes[0].models == ("bench-model", "bench-model-c")
    assert display.routes[0].max_concurrent == 4
    assert display.routes[1].backend_names == ("ollama-smart",)
    assert all("http" not in backend.name for backend in display.backends)
    assert "目前觀測" not in display.backend_heading


def test_runtime_adapter_maps_reachable_backend_rows() -> None:
    """Fails if runtime health rows no longer preserve the local host labels or flags."""
    status = GatewayStatus(
        True,
        _checked_at(),
        {
            "http://127.0.0.1:8080/v1": {"healthy": True, "last_checked": "first"},
            "http://127.0.0.1:11434/v1": {"healthy": False, "last_checked": "second"},
        },
    )

    display = operations_display_from_runtime(status, _registry(), source_kind="demo")

    assert display.backend_state == "rows"
    assert display.backends[0].name == "127.0.0.1:8080"
    assert display.backends[0].healthy is True
    assert display.backends[0].last_checked == "first"
    assert display.backends[1].name == "127.0.0.1:11434"
    assert display.backends[1].healthy is False
    assert display.backends[1].last_checked == "second"


def test_runtime_adapter_maps_offline_status() -> None:
    """Fails if an offline gateway is shown as a backend-detail failure."""
    status = GatewayStatus(False, _checked_at(), {}, "offline")

    display = operations_display_from_runtime(status, _registry(), source_kind="demo")

    assert display.backend_state == "offline"
    assert display.backend_message == (
        "仍可閱讀已寫入的 Telemetry；離線不代表歷史 Backend Health 或 SLA。"
    )


def test_runtime_adapter_maps_unavailable_detail_without_exposing_a_url() -> None:
    """Fails if unavailable detail leaks an endpoint or is mistaken for an offline gateway."""
    status = GatewayStatus(True, _checked_at(), {}, "backend_health_unauthorized")

    display = operations_display_from_runtime(status, _registry(), source_kind="demo")

    assert display.backend_state == "unavailable"
    assert display.backend_message == "backend_health_unauthorized"
    assert all("http" not in backend.name for backend in display.backends)


def test_runtime_adapter_marks_live_source() -> None:
    """Fails if a live runtime loses its existing source-note disclosure."""
    status = GatewayStatus(True, _checked_at(), {})

    display = operations_display_from_runtime(status, _registry(), source_kind="live")

    assert display.mode == "live"
    assert display.source_note == "SQLite Telemetry + models.yaml"


def test_runtime_adapter_marks_local_demo_source() -> None:
    """Fails if a local fixture runtime is presented as live data."""
    status = GatewayStatus(True, _checked_at(), {})

    display = operations_display_from_runtime(status, _registry(), source_kind="demo")

    assert display.mode == "local-demo"
    assert display.source_note == "SQLite Telemetry + models.yaml · 示範 fixture"
