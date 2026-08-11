"""Async OpenAI-compatible chat-completions client with client-side TTFT / throughput timing.

All timing is measured on the client side (wall clock around SSE chunks), not from
engine-reported fields, so numbers are directly comparable across llama.cpp / Ollama / LM Studio
regardless of what each engine's response payload happens to include.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx


def build_messages(system_prompt: str, user_content: str) -> list[dict]:
    """Always includes an explicit system message -- see config.yaml's system_prompt comment
    for why (Ministral injects a non-reproducible, date-stamped default system message otherwise)."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


@dataclass
class RequestResult:
    engine: str
    model: str
    success: bool
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    completion_tokens_source: str | None = (
        None  # "usage" or "chunk_count" -- see stream_chat_completion
    )
    ttft_s: float | None = None
    total_time_s: float | None = None
    tokens_per_sec: float | None = None
    finish_reason: str | None = None
    response_text: str = ""
    error: str | None = None
    status_code: int | None = None


async def stream_chat_completion(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    messages: list[dict],
    *,
    api_key: str | None = None,
    temperature: float = 0.0,
    top_p: float = 1.0,
    max_tokens: int = 256,
    seed: int | None = None,
    engine_label: str = "",
    timeout_s: float = 120.0,
) -> RequestResult:
    """Send one streaming chat-completion request and measure TTFT / decode throughput.

    Requests stream_options.include_usage so the final SSE chunk carries prompt/completion
    token counts -- this is the source of truth for the cross-engine parity check.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if seed is not None:
        payload["seed"] = seed

    t_start = time.perf_counter()
    t_first_token: float | None = None
    t_last_token: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    text_parts: list[str] = []
    n_content_chunks = 0

    try:
        async with client.stream(
            "POST", url, headers=headers, json=payload, timeout=timeout_s
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                return RequestResult(
                    engine=engine_label,
                    model=model,
                    success=False,
                    status_code=response.status_code,
                    error=body.decode(errors="replace")[:500],
                )

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                now = time.perf_counter()
                usage = chunk.get("usage")
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                    completion_tokens = usage.get("completion_tokens", completion_tokens)

                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        if t_first_token is None:
                            t_first_token = now
                        t_last_token = now
                        text_parts.append(content)
                        n_content_chunks += 1
                    fr = choices[0].get("finish_reason")
                    if fr:
                        finish_reason = fr

    except httpx.TimeoutException as e:
        return RequestResult(engine=engine_label, model=model, success=False, error=f"timeout: {e}")
    except httpx.HTTPError as e:
        return RequestResult(
            engine=engine_label, model=model, success=False, error=f"http_error: {e}"
        )

    if t_first_token is None:
        return RequestResult(
            engine=engine_label,
            model=model,
            success=False,
            error="no content tokens received",
        )

    ttft_s = t_first_token - t_start
    decode_span_s = (t_last_token - t_first_token) if t_last_token else 0.0
    total_time_s = (t_last_token or t_first_token) - t_start

    # LM Studio has been observed to drop the closing usage chunk under high concurrency
    # (finish_reason/usage both missing even though all content arrived) -- fall back to
    # counting content-carrying SSE chunks, which is a 1-token-per-chunk convention shared by
    # all three engines' streaming APIs (verified against usage.completion_tokens when present).
    completion_tokens_source = None
    if completion_tokens is not None:
        completion_tokens_source = "usage"
    elif n_content_chunks > 0:
        completion_tokens = n_content_chunks
        completion_tokens_source = "chunk_count"

    # tokens/sec measures DECODE throughput after the first token, matching how TTFT and
    # generation speed are conventionally reported separately (see DESIGN.md).
    if completion_tokens and completion_tokens > 1 and decode_span_s > 0:
        tokens_per_sec = (completion_tokens - 1) / decode_span_s
    else:
        tokens_per_sec = None

    return RequestResult(
        engine=engine_label,
        model=model,
        success=True,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        completion_tokens_source=completion_tokens_source,
        ttft_s=ttft_s,
        total_time_s=total_time_s,
        tokens_per_sec=tokens_per_sec,
        finish_reason=finish_reason,
        response_text="".join(text_parts),
    )
