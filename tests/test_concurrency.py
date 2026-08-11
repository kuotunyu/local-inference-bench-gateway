"""Per-alias concurrency limiting: reject over capacity with 429 instead of queueing.

Uses an asyncio.Event to hold mocked backend responses open, so requests can be deterministically
kept "in flight" long enough to test the boundary -- without this, a fast mock would complete
before a competing request could ever observe the alias at capacity.
"""

from __future__ import annotations

import asyncio

import httpx
import respx

SIMPLE_RESPONSE = {
    "id": "chatcmpl-x",
    "object": "chat.completion",
    "created": 0,
    "model": "model-d",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


def _payload():
    return {"model": "limited-alias", "messages": [{"role": "user", "content": "hi"}]}


@respx.mock
async def test_exceeding_max_concurrent_returns_429(gateway_client):
    release_event = asyncio.Event()

    async def slow_response(request):
        await release_event.wait()
        return httpx.Response(200, json=SIMPLE_RESPONSE)

    respx.post("http://limited.test/v1/chat/completions").mock(side_effect=slow_response)

    task1 = asyncio.create_task(gateway_client.post("/v1/chat/completions", json=_payload()))
    task2 = asyncio.create_task(gateway_client.post("/v1/chat/completions", json=_payload()))
    await asyncio.sleep(0.05)  # let both reach the "in-flight, holding a slot" state

    resp3 = await gateway_client.post("/v1/chat/completions", json=_payload())
    assert resp3.status_code == 429
    body = resp3.json()
    assert body["error"]["code"] == "concurrency_limit_exceeded"
    assert body["error"]["type"] == "rate_limit_error"
    assert "Retry-After" in resp3.headers

    release_event.set()
    resp1, resp2 = await task1, await task2
    assert resp1.status_code == 200
    assert resp2.status_code == 200


@respx.mock
async def test_capacity_frees_up_after_requests_complete(gateway_client):
    respx.post("http://limited.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=SIMPLE_RESPONSE)
    )

    # sequential, non-overlapping requests up to and beyond the limit should all succeed --
    # each fully releases its slot before the next one acquires
    for _ in range(5):
        resp = await gateway_client.post("/v1/chat/completions", json=_payload())
        assert resp.status_code == 200


@respx.mock
async def test_unlimited_alias_has_no_cap(gateway_client):
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "c",
                "object": "chat.completion",
                "created": 0,
                "model": "model-a",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )
    )

    payload = {"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]}
    results = await asyncio.gather(*(gateway_client.post("/v1/chat/completions", json=payload) for _ in range(10)))
    assert all(r.status_code == 200 for r in results)
