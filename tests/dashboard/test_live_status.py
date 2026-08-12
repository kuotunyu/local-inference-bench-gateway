import httpx
import respx

from dashboard.data.live_status import fetch_gateway_status


@respx.mock
def test_gateway_status_reads_public_and_backend_health() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://127.0.0.1:9000/health/backends").mock(
        return_value=httpx.Response(200, json={"http://127.0.0.1:8080/v1": {"healthy": True}})
    )
    status = fetch_gateway_status("http://127.0.0.1:9000", "secret")
    assert status.reachable is True
    assert status.backends


@respx.mock
def test_auth_disabled_gateway_still_exposes_backend_health() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    route = respx.get("http://127.0.0.1:9000/health/backends").mock(
        return_value=httpx.Response(200, json={"backend": {"healthy": True}})
    )

    status = fetch_gateway_status("http://127.0.0.1:9000", None)

    assert status.reachable is True
    assert status.backends["backend"]["healthy"] is True
    assert "Authorization" not in route.calls[0].request.headers


@respx.mock
def test_invalid_backend_health_does_not_mark_public_gateway_offline() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://127.0.0.1:9000/health/backends").mock(
        return_value=httpx.Response(200, content=b"not-json")
    )

    status = fetch_gateway_status("http://127.0.0.1:9000", None)

    assert status.reachable is True
    assert status.backends == {}
    assert status.reason == "backend_health_unavailable"


@respx.mock
def test_invalid_backend_entry_is_quarantined() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get("http://127.0.0.1:9000/health/backends").mock(
        return_value=httpx.Response(200, json={"good": {"healthy": True}, "bad": "oops"})
    )

    status = fetch_gateway_status("http://127.0.0.1:9000", None)

    assert status.backends == {"good": {"healthy": True}}
    assert status.reason == "backend_health_protocol_error"


@respx.mock
def test_gateway_timeout_is_sanitized() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(side_effect=httpx.ReadTimeout("private"))
    status = fetch_gateway_status("http://127.0.0.1:9000", None)
    assert status.reachable is False
    assert status.reason == "timeout"
