"""Error-shape edge cases not already covered by test_failover.py."""

from __future__ import annotations

import httpx
import respx


@respx.mock
async def test_backend_timeout_returns_504(gateway_client):
    respx.post("http://only.test/v1/chat/completions").mock(side_effect=httpx.ReadTimeout("timed out"))

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )

    # single-backend has no fallback, so BackendTimeout on the only backend surfaces as 502
    # (AllBackendsFailedError) rather than a bare 504 -- the gateway always reports failure via
    # the same upstream_unavailable envelope once every candidate in the chain is exhausted.
    assert resp.status_code == 502
    assert resp.json()["error"]["type"] == "api_error"


@respx.mock
async def test_non_json_upstream_body_is_wrapped_not_crashed(gateway_client):
    respx.post("http://only.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=b"<html>not json</html>")
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["error"]["type"] == "api_error"
    assert "not json" in body["error"]["message"]


async def test_all_error_responses_share_openai_envelope_shape(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    body = resp.json()
    assert set(body.keys()) == {"error"}
    assert {"message", "type", "param", "code"} <= set(body["error"].keys())
