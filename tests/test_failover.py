"""Request-time failover across an alias's backend chain, and the failover_events log."""

from __future__ import annotations

import json
import sqlite3

import httpx
import respx

FALLBACK_RESPONSE = {
    "id": "chatcmpl-fallback",
    "object": "chat.completion",
    "created": 0,
    "model": "model-b",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "from fallback"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
}


def _read_failover_events(path):
    conn = sqlite3.connect(str(path))
    try:
        rows = conn.execute(
            "SELECT alias, failed_backend, next_backend, reason FROM failover_events"
        ).fetchall()
    finally:
        conn.close()
    return rows


@respx.mock
async def test_connect_error_on_primary_fails_over_to_fallback(gateway_client, db_path):
    respx.post("http://primary.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
    respx.post("http://fallback.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=FALLBACK_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "from fallback"

    events = _read_failover_events(db_path())
    assert len(events) == 1
    alias, failed, next_, reason = events[0]
    assert (alias, failed, next_) == ("test-alias", "primary", "fallback")
    assert "refused" in reason


@respx.mock
async def test_5xx_on_primary_fails_over_to_fallback(gateway_client, db_path):
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(503, json={"error": {"message": "overloaded", "type": "api_error"}})
    )
    respx.post("http://fallback.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=FALLBACK_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "from fallback"
    events = _read_failover_events(db_path())
    assert len(events) == 1
    assert events[0][3] == "HTTP 503"


@respx.mock
async def test_4xx_on_primary_is_not_retried(gateway_client, db_path):
    primary_route = respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(400, json={"error": {"message": "bad request", "type": "invalid_request_error"}})
    )
    fallback_route = respx.post("http://fallback.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=FALLBACK_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    # a 4xx reflects a malformed request -- would fail identically on any backend, so the
    # gateway passes it through as-is instead of wasting an attempt on the fallback
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "bad request"
    assert primary_route.called
    assert not fallback_route.called
    assert _read_failover_events(db_path()) == []


@respx.mock
async def test_all_backends_failing_returns_502(gateway_client, db_path):
    respx.post("http://primary.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
    respx.post("http://fallback.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 502
    body = resp.json()
    assert body["error"]["type"] == "api_error"
    assert body["error"]["code"] == "upstream_unavailable"


@respx.mock
async def test_single_backend_alias_has_no_fallback_to_try(gateway_client):
    respx.post("http://only.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 502


def _sse_body(*data_lines: str) -> bytes:
    return ("\n\n".join(f"data: {line}" for line in data_lines) + "\n\ndata: [DONE]\n\n").encode()


@respx.mock
async def test_streaming_connect_error_on_primary_fails_over(gateway_client, db_path):
    content_chunks = [
        json.dumps({"choices": [{"index": 0, "delta": {"content": "ok"}}]}),
        json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}),
    ]
    respx.post("http://primary.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
    respx.post("http://fallback.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=_sse_body(*content_chunks), headers={"Content-Type": "text/event-stream"}
        )
    )

    async with gateway_client.stream(
        "POST",
        "/v1/chat/completions",
        json={"model": "test-alias", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
    ) as resp:
        assert resp.status_code == 200
        lines = [line async for line in resp.aiter_lines() if line]

    assert any('"content": "ok"' in l or '"content":"ok"' in l for l in lines)
    events = _read_failover_events(db_path())
    assert len(events) == 1
    assert events[0][1:3] == ("primary", "fallback")
