"""Background health checks (observability only) and request-time failover (the actual
reliability mechanism).

These two are intentionally decoupled: the health checker just polls each unique backend's
/models endpoint on a timer and records status for the dashboard -- it never gates or skips a
request-time attempt. Failover always tries a backend fresh regardless of the last health check,
since a backend can go down (or recover) between poll intervals; relying on a stale health flag
to skip an attempt would risk both false negatives (skip a backend that already recovered) and
false positives (attempt a backend the health checker already knows is down, wasting a timeout).

Request-time failover walks an alias's backend list in order. A connection failure, timeout, or
5xx from a non-final backend triggers a move to the next one; a 4xx is NOT retried (it usually
reflects a malformed request that would fail identically everywhere). Non-final backends use a
shorter read timeout than the last one in the chain, so a hung (not just refused) backend doesn't
stall the whole request for the full generous timeout before the gateway gives up on it and tries
the next candidate.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

import httpx

from gateway import backends as backend_io
from gateway.registry import Backend

FAILOVER_READ_TIMEOUT_S = 15.0
FINAL_READ_TIMEOUT_S = 120.0
HEALTH_CHECK_TIMEOUT_S = 3.0


def safe_failure_reason(exc: Exception) -> str:
    if isinstance(exc, backend_io.BackendTimeout):
        return "timeout"
    if isinstance(exc, backend_io.BackendProtocolError):
        return "protocol_error"
    return "connection_error"


def _timeout_for(is_last: bool) -> httpx.Timeout:
    read = FINAL_READ_TIMEOUT_S if is_last else FAILOVER_READ_TIMEOUT_S
    return httpx.Timeout(connect=5.0, read=read, write=10.0, pool=5.0)


class AllBackendsFailedError(Exception):
    def __init__(self, attempts: list[tuple[str, str]]):
        self.attempts = attempts  # [(backend_name, reason), ...]
        summary = "; ".join(f"{name}: {reason}" for name, reason in attempts)
        super().__init__(f"All backends failed: {summary}")

    @property
    def last_reason(self) -> str:
        return self.attempts[-1][1] if self.attempts else "upstream_unavailable"


OnFailover = Callable[[str, str | None, str], Awaitable[None]]


async def forward_non_streaming_with_failover(
    client: httpx.AsyncClient,
    chain: tuple[Backend, ...],
    client_body: dict,
    on_failover: OnFailover | None = None,
) -> tuple[Backend, int, dict]:
    attempts: list[tuple[str, str]] = []
    for i, backend in enumerate(chain):
        is_last = i == len(chain) - 1
        try:
            status, content = await backend_io.forward_non_streaming(
                client, backend, client_body, timeout=_timeout_for(is_last)
            )
        except (
            backend_io.BackendUnavailable,
            backend_io.BackendTimeout,
            backend_io.BackendProtocolError,
        ) as e:
            reason = safe_failure_reason(e)
            attempts.append((backend.name, reason))
            if is_last:
                raise AllBackendsFailedError(attempts) from e
            next_name = chain[i + 1].name
            if on_failover:
                await on_failover(backend.name, next_name, reason)
            continue

        if status >= 500 and not is_last:
            reason = f"HTTP {status}"
            attempts.append((backend.name, reason))
            next_name = chain[i + 1].name
            if on_failover:
                await on_failover(backend.name, next_name, reason)
            continue

        return backend, status, content

    raise AllBackendsFailedError(attempts)


async def open_stream_with_failover(
    client: httpx.AsyncClient,
    chain: tuple[Backend, ...],
    client_body: dict,
    on_failover: OnFailover | None = None,
) -> tuple[Backend, backend_io.StreamHandle]:
    attempts: list[tuple[str, str]] = []
    for i, backend in enumerate(chain):
        is_last = i == len(chain) - 1
        try:
            handle = await backend_io.open_stream(
                client, backend, client_body, timeout=_timeout_for(is_last)
            )
        except (backend_io.BackendUnavailable, backend_io.BackendTimeout) as e:
            reason = safe_failure_reason(e)
            attempts.append((backend.name, reason))
            if is_last:
                raise AllBackendsFailedError(attempts) from e
            next_name = chain[i + 1].name
            if on_failover:
                await on_failover(backend.name, next_name, reason)
            continue

        if handle.response.status_code >= 500 and not is_last:
            await handle.close()
            reason = f"HTTP {handle.response.status_code}"
            attempts.append((backend.name, reason))
            next_name = chain[i + 1].name
            if on_failover:
                await on_failover(backend.name, next_name, reason)
            continue

        return backend, handle

    raise AllBackendsFailedError(attempts)


@dataclass
class BackendHealth:
    healthy: bool = True
    last_checked: str | None = None
    last_error: str | None = None


class HealthChecker:
    """Polls every unique backend base_url on a timer; read-only status for the dashboard."""

    def __init__(
        self, client: httpx.AsyncClient, backend_urls: list[str], interval_s: float = 10.0
    ):
        self.client = client
        self.backend_urls = backend_urls
        self.interval_s = interval_s
        self.status: dict[str, BackendHealth] = {url: BackendHealth() for url in backend_urls}
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _loop(self) -> None:
        while not self._stop.is_set():
            await asyncio.gather(*(self._check_one(url) for url in self.backend_urls))
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                pass

    async def _check_one(self, url: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            resp = await self.client.get(
                f"{url.rstrip('/')}/models", timeout=httpx.Timeout(HEALTH_CHECK_TIMEOUT_S)
            )
            self.status[url] = BackendHealth(
                healthy=resp.status_code == 200,
                last_checked=now,
                last_error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            )
        except httpx.HTTPError as e:
            self.status[url] = BackendHealth(healthy=False, last_checked=now, last_error=str(e))

    def snapshot(self) -> dict[str, dict]:
        return {
            url: {"healthy": h.healthy, "last_checked": h.last_checked, "last_error": h.last_error}
            for url, h in self.status.items()
        }
