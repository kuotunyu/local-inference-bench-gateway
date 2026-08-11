"""Demonstrates the gateway's per-alias concurrency limiter (gateway/concurrency.py) against a
LIVE gateway + backend -- fires more concurrent requests than the alias's max_concurrent allows
and shows the resulting mix of 200s and 429s, confirming the limiter behaves the same way under
real network/asyncio scheduling as it does in tests/test_concurrency.py's mocked version.

Usage: start the gateway (uv run uvicorn gateway.app:app --port 9000) with a real backend for the
"fast" alias up first, then: uv run python scripts/load_test_backpressure.py [n_concurrent]
"""

from __future__ import annotations

import asyncio
import sys
import time

import httpx

GATEWAY_URL = "http://127.0.0.1:9000/v1/chat/completions"


async def one_request(client: httpx.AsyncClient, i: int) -> tuple[int, float, str | None]:
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            GATEWAY_URL,
            json={
                "model": "fast",
                "messages": [{"role": "user", "content": f"[req:{i}] Say 'ok'."}],
                "max_tokens": 8,
            },
            timeout=60.0,
        )
        elapsed = time.perf_counter() - t0
        retry_after = resp.headers.get("Retry-After")
        return resp.status_code, elapsed, retry_after
    except httpx.HTTPError as e:
        return -1, time.perf_counter() - t0, str(e)


async def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12

    async with httpx.AsyncClient() as client:
        try:
            await client.get("http://127.0.0.1:9000/health", timeout=3.0)
        except httpx.HTTPError:
            print("Gateway not reachable at http://127.0.0.1:9000 -- start it first.")
            return

        print(
            f"Firing {n} concurrent requests at alias 'fast' (max_concurrent=4 in models.yaml)..."
        )
        t0 = time.perf_counter()
        results = await asyncio.gather(*(one_request(client, i) for i in range(n)))
        total_s = time.perf_counter() - t0

    n_200 = sum(1 for status, _, _ in results if status == 200)
    n_429 = sum(1 for status, _, _ in results if status == 429)
    n_other = n - n_200 - n_429

    print(
        f"\nCompleted in {total_s:.2f}s: {n_200} succeeded (200), {n_429} rejected (429), {n_other} other"
    )
    for i, (status, elapsed, extra) in enumerate(results):
        tag = f"Retry-After={extra}" if status == 429 else (extra or "")
        print(f"  req {i:2d}: status={status:4d}  {elapsed * 1000:7.1f}ms  {tag}")

    if n_429 > 0:
        print(
            f"\nBackpressure confirmed: {n_429}/{n} requests were rejected immediately instead of "
            "queueing once the alias hit its configured cap."
        )
    else:
        print(
            "\nNo requests were rejected -- either n <= max_concurrent, or all requests completed "
            "faster than they could overlap. Try a higher n or a slower backend/longer response."
        )


if __name__ == "__main__":
    asyncio.run(main())
