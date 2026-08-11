"""Per-alias concurrency limiting: reject over capacity instead of queueing.

A real backend (llama-server -np 16, for example) has a fixed number of parallel slots -- once
they're all busy, requests queue and TTFT degrades for everyone already in flight (see
EVAL_REPORT.md/DESIGN.md's TTFT-vs-throughput discussion). Queueing indefinitely at the gateway
just moves the problem: callers get no signal that they should back off, and TTFT for requests
already being served keeps getting worse as the queue grows unbounded. Rejecting immediately with
429 + Retry-After lets callers make their own choice (retry later, fail fast, load-shed) instead
of the gateway making it for them by making everyone wait.

This is intentionally simple (a counter + lock, not asyncio.Semaphore) so try_acquire() can be
non-blocking -- Semaphore has no public non-blocking "try" API without timeout hacks.
"""

from __future__ import annotations

import asyncio


class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int | None):
        self.max_concurrent = max_concurrent
        self._active = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        if self.max_concurrent is None:
            return True
        async with self._lock:
            if self._active >= self.max_concurrent:
                return False
            self._active += 1
            return True

    async def release(self) -> None:
        if self.max_concurrent is None:
            return
        async with self._lock:
            self._active -= 1

    @property
    def active(self) -> int:
        return self._active
