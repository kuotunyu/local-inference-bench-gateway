"""OpenAI-compatible unified gateway.

Routes each alias to its backend chain (registry.py) with request-time failover
(failover.py), logs handled completions and failover events to SQLite (db.py), and enforces
optional API key auth (middleware.py).

Run: uvicorn gateway.app:app --host 127.0.0.1 --port 9000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from gateway import backends, db, errors, failover
from gateway.concurrency import ConcurrencyLimiter
from gateway.middleware import verify_api_key
from gateway.registry import load_registry

load_dotenv()
logger = logging.getLogger(__name__)


def _db_path() -> Path:
    return Path(os.environ.get("GATEWAY_DB_PATH", "data/gateway.db"))


async def _log_request_safely(path: Path, **fields) -> None:
    try:
        await db.log_request(path, **fields)
    except db.LogWriteError:
        logger.warning("request log write failed")


async def _log_failover_safely(path: Path, **fields) -> None:
    try:
        await db.log_failover_event(path, **fields)
    except db.LogWriteError:
        logger.warning("failover log write failed")


async def _cleanup_shielded(cleanup: Awaitable[None]) -> None:
    """Runs a cleanup coroutine to completion even when the awaiting request task is itself
    being cancelled.

    A bare `await` in a `finally` is not enough: releasing a slot takes the limiter lock, and if
    that lock is contended the await suspends, so a pending CancelledError fires there and the
    slot is never returned. shield() keeps the cleanup alive on the loop while still letting the
    CancelledError reach the caller -- cancellation is propagated, never swallowed.
    """
    await asyncio.shield(asyncio.ensure_future(cleanup))


class _StreamOwnership:
    """Owns the limiter slot and the upstream stream handle for one streaming request.

    The slot is acquired before the upstream connection exists, but on success it has to outlive
    the route handler: the stream is consumed by StreamingResponse long after the handler
    returns, so a route-level `finally` must NOT release it. Only one of the two owners releases:
    the handler while it is still deciding, or the response generator once the stream is handed
    off. Both call release() here, which is idempotent, so the slot is returned exactly once and
    the upstream response is closed exactly once.
    """

    def __init__(self, limiter: ConcurrencyLimiter):
        self._limiter = limiter
        self._handle: backends.StreamHandle | None = None
        self._released = False
        self.handed_off = False

    def attach(self, handle: backends.StreamHandle) -> None:
        self._handle = handle

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            if self._handle is not None:
                await self._handle.close()
        except Exception:
            # A broken upstream socket must never strand capacity; the slot is freed below.
            # Deliberately not BaseException: cancellation stays propagating.
            logger.warning("upstream stream close failed")
        finally:
            await self._limiter.release()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # GATEWAY_MODELS_PATH lets a containerized gateway point at a docker-specific registry
    # (backends addressed via host.docker.internal instead of 127.0.0.1) without touching code.
    models_path = os.environ.get("GATEWAY_MODELS_PATH", "gateway/models.yaml")
    app.state.registry = load_registry(models_path)
    app.state.limiters = {
        alias: ConcurrencyLimiter(model_alias.max_concurrent)
        for alias, model_alias in app.state.registry.items()
    }
    app.state.http_client = httpx.AsyncClient()
    health_checker = None
    try:
        app.state.db_path = _db_path()
        db.init_db(app.state.db_path)
        health_checker = failover.HealthChecker(
            app.state.http_client, app.state.registry.list_backend_urls()
        )
        app.state.health_checker = health_checker
        health_checker.start()
        yield
    finally:
        try:
            if health_checker is not None:
                await health_checker.stop()
        finally:
            await app.state.http_client.aclose()


app = FastAPI(title="Local Inference Gateway", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def openai_shaped_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail:
        return JSONResponse(status_code=exc.status_code, content={"error": detail})
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"message": str(detail), "type": "api_error", "param": None, "code": None}
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/backends", dependencies=[Depends(verify_api_key)])
async def health_backends(request: Request):
    return request.app.state.health_checker.snapshot()


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models(request: Request):
    registry = request.app.state.registry
    return {
        "object": "list",
        "data": [
            {"id": alias, "object": "model", "created": 0, "owned_by": "gateway"}
            for alias in registry.list_aliases()
        ],
    }


@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return errors.invalid_json()
    if not isinstance(body, dict):
        return errors.invalid_request_body()

    alias = body.get("model")
    if alias is None:
        return errors.missing_field("model")
    if not isinstance(alias, str) or not alias.strip():
        return errors.invalid_field("model", "a non-empty string")

    stream_options = body.get("stream_options")
    if stream_options is not None and not isinstance(stream_options, dict):
        return errors.invalid_field("stream_options", "a JSON object")

    registry = request.app.state.registry
    model_alias = registry.get(alias)
    if model_alias is None:
        return errors.model_not_found(alias)

    limiter: ConcurrencyLimiter = request.app.state.limiters[alias]
    if not await limiter.try_acquire():
        return errors.too_many_requests(alias, limiter.max_concurrent)

    client: httpx.AsyncClient = request.app.state.http_client
    db_path: Path = request.app.state.db_path
    t_start = time.perf_counter()

    async def on_failover(failed_backend: str, next_backend: str | None, reason: str) -> None:
        await _log_failover_safely(
            db_path,
            alias=alias,
            failed_backend=failed_backend,
            next_backend=next_backend,
            reason=reason,
        )

    if body.get("stream"):
        client_wants_usage = bool((stream_options or {}).get("include_usage"))
        ownership = _StreamOwnership(limiter)
        try:
            try:
                backend, handle = await failover.open_stream_with_failover(
                    client, model_alias.backends, body, on_failover=on_failover
                )
            except failover.AllBackendsFailedError as e:
                await _log_request_safely(
                    db_path,
                    alias=alias,
                    backend_name=None,
                    model=None,
                    stream=True,
                    status_code=None,
                    success=False,
                    total_latency_ms=(time.perf_counter() - t_start) * 1000,
                    error_message=e.last_reason,
                )
                return errors.upstream_unavailable(alias)
            ownership.attach(handle)

            if handle.response.status_code != 200:
                try:
                    raw = await handle.response.aread()
                except httpx.TransportError:
                    # A 4xx is not a failover trigger, so this is the client's final answer:
                    # keep the upstream status and fall through to the controlled envelope
                    # below. The finally still closes the response and frees the slot.
                    raw = b""
                try:
                    content = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    content = errors.upstream_protocol_error_content()
                if not isinstance(content, dict):
                    content = errors.upstream_protocol_error_content()
                await _log_request_safely(
                    db_path,
                    alias=alias,
                    backend_name=backend.name,
                    model=backend.model,
                    stream=True,
                    status_code=handle.response.status_code,
                    success=False,
                    total_latency_ms=(time.perf_counter() - t_start) * 1000,
                    error_message=f"HTTP {handle.response.status_code}",
                )
                return JSONResponse(status_code=handle.response.status_code, content=content)

            usage_holder: dict = {}

            async def logged_stream():
                try:
                    t_first_byte = None
                    async for chunk in backends.forward_stream_chunks(
                        handle, client_wants_usage, usage_callback=usage_holder.update
                    ):
                        if t_first_byte is None:
                            t_first_byte = time.perf_counter()
                        yield chunk
                    total_ms = (time.perf_counter() - t_start) * 1000
                    ttft_ms = (t_first_byte - t_start) * 1000 if t_first_byte else None
                    await _log_request_safely(
                        db_path,
                        alias=alias,
                        backend_name=backend.name,
                        model=backend.model,
                        stream=True,
                        status_code=200,
                        success=True,
                        prompt_tokens=usage_holder.get("prompt_tokens"),
                        completion_tokens=usage_holder.get("completion_tokens"),
                        ttft_ms=ttft_ms,
                        total_latency_ms=total_ms,
                    )
                except httpx.HTTPError:
                    # Mid-stream failure: bytes already went downstream, so this stream ends
                    # here. It is never retried on another backend.
                    await _log_request_safely(
                        db_path,
                        alias=alias,
                        backend_name=backend.name,
                        model=backend.model,
                        stream=True,
                        status_code=200,
                        success=False,
                        prompt_tokens=usage_holder.get("prompt_tokens"),
                        completion_tokens=usage_holder.get("completion_tokens"),
                        total_latency_ms=(time.perf_counter() - t_start) * 1000,
                        error_message="stream_read_error",
                    )
                finally:
                    await ownership.release()

            response = StreamingResponse(logged_stream(), media_type="text/event-stream")
            # Ownership of the slot and the upstream response now belongs to the generator
            # above, for the whole lifetime of the streaming response.
            ownership.handed_off = True
            return response
        finally:
            if not ownership.handed_off:
                await _cleanup_shielded(ownership.release())

    try:
        try:
            backend, status_code, content = await failover.forward_non_streaming_with_failover(
                client, model_alias.backends, body, on_failover=on_failover
            )
        except failover.AllBackendsFailedError as e:
            await _log_request_safely(
                db_path,
                alias=alias,
                backend_name=None,
                model=None,
                stream=False,
                status_code=None,
                success=False,
                total_latency_ms=(time.perf_counter() - t_start) * 1000,
                error_message=e.last_reason,
            )
            return errors.upstream_unavailable(alias)

        total_ms = (time.perf_counter() - t_start) * 1000
        usage = content.get("usage") or {} if isinstance(content, dict) else {}
        success = 200 <= status_code < 300
        await _log_request_safely(
            db_path,
            alias=alias,
            backend_name=backend.name,
            model=backend.model,
            stream=False,
            status_code=status_code,
            success=success,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_latency_ms=total_ms,
            error_message=None if success else f"HTTP {status_code}",
        )
        return JSONResponse(status_code=status_code, content=content)
    finally:
        # Non-streaming responses are fully buffered before returning, so there is nothing to
        # hand off: the slot is always released here, cancellation included.
        await _cleanup_shielded(limiter.release())
