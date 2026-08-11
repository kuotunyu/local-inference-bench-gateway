"""Forwards chat-completion requests to a single upstream backend.

Streaming design: the gateway always asks the upstream for stream_options.include_usage=true
(regardless of what the client requested) so a future request-logging layer can capture token
counts from every request. The trailing usage-only chunk (choices=[] + usage) is then only
forwarded to the client if THEY asked for it -- otherwise it's swallowed before [DONE], keeping
the gateway transparent to clients that didn't opt in. Every other chunk is forwarded as the
exact raw SSE line the backend sent (re-framed with a trailing blank line, not re-serialized),
so response formatting quirks are preserved rather than risk being altered by a decode/re-encode
round trip.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Callable

import httpx

from gateway.registry import Backend

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


class BackendUnavailable(Exception):
    """Connection-level failure reaching a backend (connection refused, DNS failure, etc.)."""


class BackendTimeout(Exception):
    """Backend did not respond within the configured timeout."""


class BackendProtocolError(Exception):
    """Backend returned a response that is not a usable OpenAI JSON object."""


def _build_upstream_request(backend: Backend, client_body: dict) -> tuple[str, dict, dict]:
    url = f"{backend.base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if backend.api_key:
        headers["Authorization"] = f"Bearer {backend.api_key}"
    upstream_body = dict(client_body)
    upstream_body["model"] = backend.model
    return url, headers, upstream_body


async def forward_non_streaming(
    client: httpx.AsyncClient,
    backend: Backend,
    client_body: dict,
    timeout: httpx.Timeout = DEFAULT_TIMEOUT,
) -> tuple[int, dict]:
    url, headers, upstream_body = _build_upstream_request(backend, client_body)
    upstream_body["stream"] = False
    try:
        resp = await client.post(url, json=upstream_body, headers=headers, timeout=timeout)
    except httpx.ConnectError as e:
        raise BackendUnavailable(str(e)) from e
    except httpx.TimeoutException as e:
        raise BackendTimeout(str(e)) from e
    try:
        content = resp.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BackendProtocolError("non_json_response") from exc
    if not isinstance(content, dict):
        raise BackendProtocolError("non_object_response")
    return resp.status_code, content


class StreamHandle:
    """An opened upstream SSE connection. app.py inspects `.response.status_code` before
    committing to a StreamingResponse, then hands this back to forward_stream_chunks()."""

    def __init__(self, ctx, response: httpx.Response):
        self._ctx = ctx
        self.response = response
        self._closed = False

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._ctx.__aexit__(None, None, None)


async def open_stream(
    client: httpx.AsyncClient,
    backend: Backend,
    client_body: dict,
    timeout: httpx.Timeout = DEFAULT_TIMEOUT,
) -> StreamHandle:
    url, headers, upstream_body = _build_upstream_request(backend, client_body)
    upstream_body["stream"] = True
    upstream_body["stream_options"] = {"include_usage": True}
    ctx = client.stream("POST", url, json=upstream_body, headers=headers, timeout=timeout)
    try:
        response = await ctx.__aenter__()
    except httpx.ConnectError as e:
        raise BackendUnavailable(str(e)) from e
    except httpx.TimeoutException as e:
        raise BackendTimeout(str(e)) from e
    return StreamHandle(ctx, response)


async def forward_stream_chunks(
    handle: StreamHandle,
    client_wants_usage: bool,
    usage_callback: Callable[[dict], None] | None = None,
) -> AsyncIterator[bytes]:
    try:
        async for raw_line in handle.response.aiter_lines():
            if not raw_line:
                continue
            if raw_line.startswith("data:"):
                data = raw_line[len("data:") :].strip()
                if data == "[DONE]":
                    yield b"data: [DONE]\n\n"
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    chunk = None
                if isinstance(chunk, dict):
                    usage = chunk.get("usage")
                    choices = chunk.get("choices")
                    if usage:
                        if usage_callback:
                            usage_callback(usage)
                        if not choices and not client_wants_usage:
                            continue
            yield (raw_line + "\n\n").encode("utf-8")
    finally:
        await handle.close()
