"""Chat-completions routing: non-streaming and streaming success paths against a mocked backend."""

from __future__ import annotations

import json

import httpx
import respx

NON_STREAM_UPSTREAM_RESPONSE = {
    "id": "chatcmpl-abc",
    "object": "chat.completion",
    "created": 0,
    "model": "model-a",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
}


@respx.mock
async def test_non_streaming_forwards_backend_response(gateway_client):
    route = respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=NON_STREAM_UPSTREAM_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert route.called
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "hello"
    assert body["usage"]["completion_tokens"] == 2

    # the request forwarded to the backend must carry the backend's own model id, not the alias
    sent_body = json.loads(route.calls[0].request.content)
    assert sent_body["model"] == "model-a"


def _sse_body(*data_lines: str) -> bytes:
    return ("\n\n".join(f"data: {line}" for line in data_lines) + "\n\ndata: [DONE]\n\n").encode()


STREAM_CONTENT_CHUNKS = [
    json.dumps({"choices": [{"index": 0, "delta": {"role": "assistant", "content": None}}]}),
    json.dumps({"choices": [{"index": 0, "delta": {"content": "hel"}}]}),
    json.dumps({"choices": [{"index": 0, "delta": {"content": "lo"}}]}),
    json.dumps({"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}),
]
STREAM_USAGE_CHUNK = json.dumps(
    {"choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}
)


@respx.mock
async def test_streaming_without_client_usage_request_strips_usage_chunk(gateway_client):
    upstream_body = _sse_body(*STREAM_CONTENT_CHUNKS, STREAM_USAGE_CHUNK)
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=upstream_body, headers={"Content-Type": "text/event-stream"}
        )
    )

    async with gateway_client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "test-alias",
            "stream": True,
            "messages": [{"role": "user", "content": "hi"}],
        },
    ) as resp:
        assert resp.status_code == 200
        lines = [line async for line in resp.aiter_lines() if line]

    data_lines = [line[len("data:") :].strip() for line in lines if line.startswith("data:")]
    assert data_lines[-1] == "[DONE]"
    # the usage-only chunk (empty choices) must NOT appear -- client never asked for it
    assert not any(json.loads(d).get("usage") for d in data_lines if d != "[DONE]")
    # but all real content chunks must still be present
    joined = "".join(
        (json.loads(d)["choices"][0].get("delta", {}).get("content") or "")
        for d in data_lines
        if d != "[DONE]" and json.loads(d).get("choices")
    )
    assert joined == "hello"


@respx.mock
async def test_streaming_with_client_usage_request_forwards_usage_chunk(gateway_client):
    upstream_body = _sse_body(*STREAM_CONTENT_CHUNKS, STREAM_USAGE_CHUNK)
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=upstream_body, headers={"Content-Type": "text/event-stream"}
        )
    )

    async with gateway_client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "test-alias",
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [{"role": "user", "content": "hi"}],
        },
    ) as resp:
        assert resp.status_code == 200
        lines = [line async for line in resp.aiter_lines() if line]

    data_lines = [line[len("data:") :].strip() for line in lines if line.startswith("data:")]
    usage_chunks = [
        json.loads(d) for d in data_lines if d != "[DONE]" and json.loads(d).get("usage")
    ]
    assert len(usage_chunks) == 1
    assert usage_chunks[0]["usage"]["completion_tokens"] == 2


@respx.mock
async def test_upstream_request_always_asks_for_usage_regardless_of_client(gateway_client):
    upstream_body = _sse_body(*STREAM_CONTENT_CHUNKS, STREAM_USAGE_CHUNK)
    route = respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=upstream_body, headers={"Content-Type": "text/event-stream"}
        )
    )

    async with gateway_client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "test-alias",
            "stream": True,
            "messages": [{"role": "user", "content": "hi"}],
        },
    ) as resp:
        async for _ in resp.aiter_lines():
            pass

    sent_body = json.loads(route.calls[0].request.content)
    assert sent_body["stream_options"] == {"include_usage": True}


@respx.mock
async def test_streaming_non_object_json_chunk_is_forwarded_without_crashing(gateway_client):
    upstream_body = _sse_body('["unexpected", "chunk"]')
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, content=upstream_body, headers={"Content-Type": "text/event-stream"}
        )
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "stream": True, "messages": []},
    )

    assert resp.status_code == 200
    assert 'data: ["unexpected", "chunk"]' in resp.text
    assert "data: [DONE]" in resp.text
