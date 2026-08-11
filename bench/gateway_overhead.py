"""Micro-benchmark: same backend, same request, direct-to-llama-server vs via-gateway.

Isolates the gateway's own added latency (JSON parse/rewrite, failover-chain bookkeeping, SSE
re-framing, SQLite logging) from the backend's own inference time -- both paths hit the exact
same llama-server instance, so any difference is overhead the gateway itself introduces.
Produces data for DESIGN.md's TTFT/throughput tradeoff discussion.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
from pathlib import Path

import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from bench.client import build_messages, stream_chat_completion

WARMUP = 3
TIMED = 10
MESSAGE = "台灣最高的山是哪一座？請只回答山名。"
SYSTEM_PROMPT = "You are a helpful, concise assistant."


async def run_repeated(base_url: str, model: str, label: str) -> dict:
    async with httpx.AsyncClient() as client:
        for _ in range(WARMUP):
            await stream_chat_completion(
                client,
                base_url,
                model,
                build_messages(SYSTEM_PROMPT, MESSAGE),
                temperature=0,
                max_tokens=16,
                engine_label=label,
            )
        ttfts, totals = [], []
        for _ in range(TIMED):
            r = await stream_chat_completion(
                client,
                base_url,
                model,
                build_messages(SYSTEM_PROMPT, MESSAGE),
                temperature=0,
                max_tokens=16,
                engine_label=label,
            )
            if not r.success:
                raise RuntimeError(f"{label} request failed: {r.error}")
            ttfts.append(r.ttft_s)
            totals.append(r.total_time_s)
    return {
        "label": label,
        "ttft_median_ms": statistics.median(ttfts) * 1000,
        "ttft_p95_ms": (sorted(ttfts)[int(len(ttfts) * 0.95)] if len(ttfts) > 1 else ttfts[0])
        * 1000,
        "total_median_ms": statistics.median(totals) * 1000,
    }


async def main():
    direct = await run_repeated("http://127.0.0.1:8080/v1", "bench-model", "direct")
    via_gateway = await run_repeated("http://127.0.0.1:9000/v1", "fast", "via-gateway")

    print(f"{'':12s} {'TTFT median':>14s} {'TTFT p95':>12s} {'total median':>14s}")
    for r in (direct, via_gateway):
        print(
            f"{r['label']:12s} {r['ttft_median_ms']:12.1f}ms {r['ttft_p95_ms']:10.1f}ms {r['total_median_ms']:12.1f}ms"
        )

    overhead_ms = via_gateway["ttft_median_ms"] - direct["ttft_median_ms"]
    print(f"\nGateway-added TTFT overhead (median): {overhead_ms:+.1f}ms")

    out_dir = Path("bench/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gateway_overhead.json").write_text(
        json.dumps(
            {"direct": direct, "via_gateway": via_gateway, "overhead_ms": overhead_ms}, indent=2
        ),
        encoding="utf-8",
    )
    print(f"Saved -> {out_dir / 'gateway_overhead.json'}")


if __name__ == "__main__":
    asyncio.run(main())
