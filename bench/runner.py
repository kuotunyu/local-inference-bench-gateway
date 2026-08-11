"""Executes the benchmark test matrix against one engine: warmup, then timed repeats, to JSONL.

Two test types (see SETUP.md for the public methodology):
  concurrency -- short prompt, sweep concurrency levels {1,4,8,16}, N concurrent requests per
                 batch, aggregate decode throughput per batch.
  prefill     -- long calibrated prompt (2k/8k tokens), single request at a time, TTFT is the
                 prefill-time measurement.

Each engine's server must already be running with the matching profile (see SETUP.md):
  concurrency test type -> server profile "concurrency" (per_slot_ctx=4096, slots=16)
  prefill test type     -> server profile "prefill" (per_slot_ctx=16384, slots=1)
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from bench.client import RequestResult, build_messages, stream_chat_completion
from bench.vram import VramPoller, check_baseline

# See bench/parity.py for why this is needed on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_model(engine_cfg: dict, test_type: str) -> str:
    """Ollama needs a different model tag per test_type (ctx is baked into the Modelfile);
    llama.cpp/LM Studio use the same model name across profiles (ctx is a server launch flag)."""
    return engine_cfg.get("model_by_test", {}).get(test_type, engine_cfg["model"])


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _uniquify(text: str) -> str:
    """Prepends a fresh nonce so repeated identical prompts don't hit the engine's prompt/KV
    prefix cache (confirmed empirically: llama-server dropped an 8k-token prefill from 1036ms to
    10ms on the second identical request -- cache_n=7879/7880 tokens reused). Causal attention
    means a token difference this early invalidates the cache for everything that follows, so a
    short prefix is enough; the ~5-10 extra tokens are negligible against 2k/8k-token targets."""
    return f"[req:{uuid.uuid4().hex[:8]}] {text}"


async def _run_concurrency_batch(
    client: httpx.AsyncClient,
    engine_name: str,
    engine_cfg: dict,
    model: str,
    sampling: dict,
    system_prompt: str,
    prompt_text: str,
    concurrency: int,
) -> dict:
    async def one():
        messages = build_messages(system_prompt, _uniquify(prompt_text))
        return await stream_chat_completion(
            client,
            engine_cfg["base_url"],
            model,
            messages,
            api_key=engine_cfg.get("api_key"),
            temperature=sampling["temperature"],
            top_p=sampling["top_p"],
            max_tokens=sampling["max_tokens"],
            seed=sampling.get("seed"),
            engine_label=engine_name,
        )

    t0 = time.perf_counter()
    results: list[RequestResult] = await asyncio.gather(*(one() for _ in range(concurrency)))
    wall_time_s = time.perf_counter() - t0

    total_completion_tokens = sum(r.completion_tokens or 0 for r in results if r.success)
    aggregate_tokens_per_sec = total_completion_tokens / wall_time_s if wall_time_s > 0 else None

    return {
        "batch_wall_time_s": wall_time_s,
        "aggregate_tokens_per_sec": aggregate_tokens_per_sec,
        "n_success": sum(1 for r in results if r.success),
        "n_failed": sum(1 for r in results if not r.success),
        "requests": [dataclasses.asdict(r) for r in results],
    }


async def run_concurrency_sweep(engine_name: str, config: dict, out_path: Path) -> None:
    engine_cfg = config["engines"][engine_name]
    model = _resolve_model(engine_cfg, "concurrency")
    sampling = config["sampling"]
    warmup_runs = config["warmup_runs"]
    timed_runs = config["timed_runs"]
    short_prompt = config["short_prompt"]
    system_prompt = config["system_prompt"]
    vram_cfg = config["vram"]

    check_baseline(vram_cfg["baseline_warn_threshold_mb"])

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=64)) as client:
        for concurrency in config["concurrency_levels"]:
            print(f"[{engine_name}] concurrency={concurrency}: warming up ({warmup_runs} batches)...")
            for i in range(warmup_runs):
                await _run_concurrency_batch(
                    client, engine_name, engine_cfg, model, sampling, system_prompt, short_prompt, concurrency
                )

            print(f"[{engine_name}] concurrency={concurrency}: timed runs ({timed_runs} batches)...")
            for i in range(timed_runs):
                async with VramPoller(vram_cfg["poll_interval_sec"]) as poller:
                    batch = await _run_concurrency_batch(
                        client, engine_name, engine_cfg, model, sampling, system_prompt, short_prompt, concurrency
                    )
                vram = poller.summary()

                record = {
                    "engine": engine_name,
                    "test_type": "concurrency",
                    "concurrency": concurrency,
                    "run_index": i,
                    "warmup": False,
                    "timestamp": _now_iso(),
                    "vram_baseline_mb": vram.baseline_mb,
                    "vram_peak_delta_mb": vram.peak_delta_mb,
                    **batch,
                }
                _append_jsonl(out_path, record)
                print(
                    f"  run {i + 1}/{timed_runs}: "
                    f"{batch['n_success']}/{concurrency} ok, "
                    f"agg={batch['aggregate_tokens_per_sec']:.1f} tok/s, "
                    f"vram_delta={vram.peak_delta_mb:.0f}MB"
                )


async def run_prefill_sweep(engine_name: str, config: dict, out_path: Path) -> None:
    engine_cfg = config["engines"][engine_name]
    model = _resolve_model(engine_cfg, "prefill")
    sampling = config["sampling"]
    warmup_runs = config["warmup_runs"]
    timed_runs = config["timed_runs"]
    vram_cfg = config["vram"]
    prompts_dir = Path(config["paths"]["calibrated_prompts_dir"])

    check_baseline(vram_cfg["baseline_warn_threshold_mb"])

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=8)) as client:
        for target_tokens in config["prompt_token_targets"]:
            prompt_file = prompts_dir / f"prompt_{target_tokens}.json"
            if not prompt_file.exists():
                raise FileNotFoundError(
                    f"{prompt_file} missing -- run `python -m bench.prompts` first to calibrate prompts."
                )
            prompt_data = json.loads(prompt_file.read_text(encoding="utf-8"))
            prompt_text = prompt_data["text"]

            print(f"[{engine_name}] prefill target={target_tokens}: warming up ({warmup_runs})...")
            for _ in range(warmup_runs):
                messages = build_messages(config["system_prompt"], _uniquify(prompt_text))
                await stream_chat_completion(
                    client,
                    engine_cfg["base_url"],
                    model,
                    messages,
                    api_key=engine_cfg.get("api_key"),
                    temperature=sampling["temperature"],
                    top_p=sampling["top_p"],
                    max_tokens=sampling["max_tokens"],
                    seed=sampling.get("seed"),
                    engine_label=engine_name,
                    timeout_s=180.0,
                )

            print(f"[{engine_name}] prefill target={target_tokens}: timed runs ({timed_runs})...")
            for i in range(timed_runs):
                messages = build_messages(config["system_prompt"], _uniquify(prompt_text))
                async with VramPoller(vram_cfg["poll_interval_sec"]) as poller:
                    result = await stream_chat_completion(
                        client,
                        engine_cfg["base_url"],
                        model,
                        messages,
                        api_key=engine_cfg.get("api_key"),
                        temperature=sampling["temperature"],
                        top_p=sampling["top_p"],
                        max_tokens=sampling["max_tokens"],
                        seed=sampling.get("seed"),
                        engine_label=engine_name,
                        timeout_s=180.0,
                    )
                vram = poller.summary()

                record = {
                    "engine": engine_name,
                    "test_type": "prefill",
                    "prompt_target_tokens": target_tokens,
                    "prompt_actual_tokens": prompt_data["actual_tokens"],
                    "run_index": i,
                    "warmup": False,
                    "timestamp": _now_iso(),
                    "vram_baseline_mb": vram.baseline_mb,
                    "vram_peak_delta_mb": vram.peak_delta_mb,
                    **dataclasses.asdict(result),
                }
                _append_jsonl(out_path, record)
                print(
                    f"  run {i + 1}/{timed_runs}: success={result.success}, "
                    f"ttft={result.ttft_s and round(result.ttft_s, 3)}s, "
                    f"vram_delta={vram.peak_delta_mb:.0f}MB"
                )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="bench/config.yaml")
    parser.add_argument("--engine", required=True, choices=["llamacpp", "ollama", "lmstudio"])
    parser.add_argument("--test", required=True, choices=["concurrency", "prefill"])
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    raw_dir = Path(config["paths"]["raw_results_dir"])
    out_path = raw_dir / args.engine / f"{args.test}.jsonl"

    if args.test == "concurrency":
        await run_concurrency_sweep(args.engine, config, out_path)
    else:
        await run_prefill_sweep(args.engine, config, out_path)

    print(f"\nDone. Results -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
