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
def test_gateway_timeout_is_sanitized() -> None:
    respx.get("http://127.0.0.1:9000/health").mock(side_effect=httpx.ReadTimeout("private"))
    status = fetch_gateway_status("http://127.0.0.1:9000", None)
    assert status.reachable is False
    assert status.reason == "timeout"
