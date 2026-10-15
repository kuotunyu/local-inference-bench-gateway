"""Slot and upstream-response ownership across the streaming request lifecycle.

Three deterministic pre-response failures used to leak the limiter slot acquired in
chat_completions(), permanently shrinking an alias's capacity for the life of the process:

  1. the request task is cancelled while the upstream stream is being opened,
  2. an upstream transport error (backend accepts the connection, then closes it without
     replying) escapes the failover chain,
  3. a non-retryable 4xx arrives with a truncated body, so reading it raises.

The streaming branch owns a slot that must outlive the handler on success (StreamingResponse
consumes the body long after the route returns), so these tests pin both halves of that
contract: nothing is released early on the success path, and nothing is stranded on the
failure paths. The non-streaming branch is asserted alongside as the control.

All upstream I/O is mocked at the httpx transport layer (respx) and the gateway is driven over
httpx.ASGITransport, so no socket, backend engine, model or GPU is involved.
"""

from __future__ import annotations

import asyncio
import sqlite3

import httpx
import pytest
import pytest_asyncio
import respx

from gateway import db as db_module
from gateway.app import app
from gateway.concurrency import ConcurrencyLimiter
from gateway.failover import HealthChecker
from gateway.registry import build_registry

# max_concurrent=1 makes a single leaked slot immediately observable as a wedged alias, and
# two backends show whether the ordered failover chain is actually walked.
OWNERSHIP_REGISTRY_DATA = {
    "models": {
        "chain-1": {
            "max_concurrent": 1,
            "backends": [
                {"name": "primary", "base_url": "http://primary.test/v1", "model": "model-a"},
                {"name": "fallback", "base_url": "http://fallback.test/v1", "model": "model-b"},
            ],
        }
    }
}

ALIAS = "chain-1"
PRIMARY = "http://primary.test/v1/chat/completions"
FALLBACK = "http://fallback.test/v1/chat/completions"

SSE_OK = (
    b'data: {"choices":[{"index":0,"delta":{"content":"ok"}}]}\n\n'
    b'data: {"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}\n\n'
    b"data: [DONE]\n\n"
)

NON_STREAM_OK = {
    "id": "chatcmpl-x",
    "object": "chat.completion",
    "created": 0,
    "model": "model-b",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


@pytest_asyncio.fixture
async def ownership_client(tmp_path, monkeypatch):
    """Same app.state wiring as conftest.gateway_client, with the capacity-1 chain above."""
    monkeypatch.delenv("GATEWAY_API_KEY", raising=False)
    db_path = tmp_path / "ownership.db"
    db_module.init_db(db_path)

    app.state.registry = build_registry(OWNERSHIP_REGISTRY_DATA)
    app.state.limiters = {
        alias: ConcurrencyLimiter(ma.max_concurrent) for alias, ma in app.state.registry.items()
    }
    app.state.db_path = db_path

    async with httpx.AsyncClient() as upstream:
        app.state.http_client = upstream
        app.state.health_checker = HealthChecker(upstream, [])
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


def _payload(stream: bool) -> dict:
    body = {"model": ALIAS, "messages": [{"role": "user", "content": "hi"}]}
    if stream:
        body["stream"] = True
    return body


def _limiter() -> ConcurrencyLimiter:
    return app.state.limiters[ALIAS]


async def _cancel_while_opening_upstream(client, *, stream: bool) -> None:
    """Park the handler inside the upstream open, then cancel the in-flight request."""
    upstream_reached = asyncio.Event()
    never = asyncio.Event()

    async def hang(request):
        upstream_reached.set()
        await never.wait()
        return httpx.Response(200)

    respx.post(PRIMARY).mock(side_effect=hang)

    task = asyncio.create_task(client.post("/v1/chat/completions", json=_payload(stream)))
    await asyncio.wait_for(upstream_reached.wait(), timeout=5)
    assert _limiter().active == 1, "precondition: the in-flight request holds exactly one slot"

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.05)  # let the shielded cleanup finish


@respx.mock
async def test_streaming_cancelled_before_response_releases_slot(ownership_client):
    await _cancel_while_opening_upstream(ownership_client, stream=True)
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_non_streaming_cancelled_before_response_releases_slot(ownership_client):
    await _cancel_while_opening_upstream(ownership_client, stream=False)
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_capacity_survives_cancellation(ownership_client):
    """The capacity consequence: with max_concurrent=1 a single leak wedges the alias at 429."""
    await _cancel_while_opening_upstream(ownership_client, stream=True)

    respx.post(PRIMARY).mock(return_value=httpx.Response(200, json=NON_STREAM_OK))
    resp = await ownership_client.post("/v1/chat/completions", json=_payload(False))
    assert resp.status_code == 200, f"alias still at capacity after cancellation: {resp.text}"


@respx.mock
async def test_streaming_transport_error_fails_over_and_releases_slot(ownership_client):
    """A backend that closes the connection without replying raises RemoteProtocolError, which
    is now mapped into the failover contract instead of escaping the handler."""
    primary = respx.post(PRIMARY).mock(
        side_effect=httpx.RemoteProtocolError("Server disconnected without sending a response")
    )
    fallback = respx.post(FALLBACK).mock(
        return_value=httpx.Response(
            200, content=SSE_OK, headers={"Content-Type": "text/event-stream"}
        )
    )

    resp = await ownership_client.post("/v1/chat/completions", json=_payload(True))
    await asyncio.sleep(0.05)

    assert primary.called
    assert fallback.called, "ordered failover chain was not walked on a transport error"
    assert resp.status_code == 200
    assert b"data: [DONE]" in resp.content
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_non_streaming_transport_error_fails_over_and_releases_slot(ownership_client):
    primary = respx.post(PRIMARY).mock(
        side_effect=httpx.RemoteProtocolError("Server disconnected without sending a response")
    )
    fallback = respx.post(FALLBACK).mock(return_value=httpx.Response(200, json=NON_STREAM_OK))

    resp = await ownership_client.post("/v1/chat/completions", json=_payload(False))

    assert primary.called and fallback.called
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "ok"
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_streaming_truncated_4xx_body_releases_slot_and_response(ownership_client):
    """A 4xx is deliberately not a failover trigger, so a truncated 4xx body is the client's
    final answer. Reading it raises; the slot and the upstream response must still be freed."""

    class _BrokenBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"error": "parti'
            raise httpx.RemoteProtocolError("peer closed connection mid-body")

    primary = respx.post(PRIMARY).mock(
        return_value=httpx.Response(
            400, stream=_BrokenBody(), headers={"Content-Type": "application/json"}
        )
    )
    fallback = respx.post(FALLBACK).mock(return_value=httpx.Response(200, json=NON_STREAM_OK))

    resp = await ownership_client.post("/v1/chat/completions", json=_payload(True))
    await asyncio.sleep(0.05)

    assert primary.called
    assert not fallback.called, "a 4xx must not be retried on the next backend"
    assert resp.status_code == 400, "the upstream status must survive a truncated body"
    assert resp.json()["error"]["code"] == "upstream_protocol_error"
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_successful_stream_holds_slot_until_consumed(ownership_client):
    """The other half of the contract: the route-level cleanup must NOT release a stream that
    was handed to StreamingResponse, or the slot is free while the stream is still running."""
    first_chunk_sent = asyncio.Event()
    finish = asyncio.Event()

    class _GatedBody(httpx.AsyncByteStream):
        """Holds the upstream stream open after the first chunk, so the gateway's response
        generator is observably mid-flight. (httpx.ASGITransport buffers the whole downstream
        body, so the test client itself can never see a partially consumed stream.)"""

        async def __aiter__(self):
            yield b'data: {"choices":[{"index":0,"delta":{"content":"ok"}}]}\n\n'
            first_chunk_sent.set()
            await finish.wait()
            yield b"data: [DONE]\n\n"

    respx.post(PRIMARY).mock(
        return_value=httpx.Response(
            200, stream=_GatedBody(), headers={"Content-Type": "text/event-stream"}
        )
    )

    task = asyncio.create_task(ownership_client.post("/v1/chat/completions", json=_payload(True)))
    await asyncio.wait_for(first_chunk_sent.wait(), timeout=5)
    await asyncio.sleep(0.05)
    assert _limiter().active == 1, "slot released while the stream was still being consumed"

    finish.set()
    resp = await task
    assert resp.status_code == 200
    assert b"data: [DONE]" in resp.content

    await asyncio.sleep(0.05)
    assert _limiter().active == 0, f"slot not returned after consumption: {_limiter().active}"


@respx.mock
async def test_repeated_streaming_requests_do_not_double_release(ownership_client):
    """A double release would drive the counter negative and silently raise the alias's real
    capacity above max_concurrent."""
    respx.post(PRIMARY).mock(
        return_value=httpx.Response(
            200, content=SSE_OK, headers={"Content-Type": "text/event-stream"}
        )
    )

    for _ in range(3):
        resp = await ownership_client.post("/v1/chat/completions", json=_payload(True))
        assert resp.status_code == 200
        assert b"data: [DONE]" in resp.content

    await asyncio.sleep(0.05)
    assert _limiter().active == 0, f"counter drifted: active={_limiter().active}"

    # a leaked-negative counter would let a second concurrent request through
    release = asyncio.Event()

    async def slow(request):
        await release.wait()
        return httpx.Response(200, content=SSE_OK, headers={"Content-Type": "text/event-stream"})

    respx.post(PRIMARY).mock(side_effect=slow)
    first = asyncio.create_task(ownership_client.post("/v1/chat/completions", json=_payload(True)))
    await asyncio.sleep(0.05)
    second = await ownership_client.post("/v1/chat/completions", json=_payload(True))
    assert second.status_code == 429, "max_concurrent=1 was not enforced"

    release.set()
    assert (await first).status_code == 200


@respx.mock
async def test_all_backends_transport_error_reports_upstream_unavailable(ownership_client):
    """Whole chain failing with transport errors stays a controlled 502, and frees the slot."""
    respx.post(PRIMARY).mock(side_effect=httpx.RemoteProtocolError("closed"))
    respx.post(FALLBACK).mock(side_effect=httpx.ReadError("socket died"))

    resp = await ownership_client.post("/v1/chat/completions", json=_payload(True))

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_unavailable"
    assert _limiter().active == 0, f"slot leaked: active={_limiter().active}"


@respx.mock
async def test_timeout_classification_survives_transport_mapping(ownership_client, db_path):
    """Timeouts must still be recorded as `timeout`, not collapsed into connection_error."""
    respx.post(PRIMARY).mock(side_effect=httpx.ReadTimeout("too slow"))
    respx.post(FALLBACK).mock(return_value=httpx.Response(200, json=NON_STREAM_OK))

    resp = await ownership_client.post("/v1/chat/completions", json=_payload(False))
    assert resp.status_code == 200

    with sqlite3.connect(db_path()) as conn:
        reasons = [r[0] for r in conn.execute("SELECT reason FROM failover_events").fetchall()]
    assert "timeout" in reasons, f"timeout classification lost: {reasons}"
