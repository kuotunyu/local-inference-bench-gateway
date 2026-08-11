"""Cross-engine parity pre-check -- must pass before any timed benchmark run.

Sends the same message at temperature=0 to all three engines and compares:
  1. usage.prompt_tokens -- proves the chat template rendered identically (same tokenizer,
     same special tokens, same system/user framing) across engines.
  2. response text prefix -- a sanity spot-check that the model is actually producing
     coherent, matching output (not proof of determinism across engines, since sampling
     kernels can still differ bit-for-bit -- see DESIGN.md).

If prompt_tokens mismatch, the most likely cause is Ollama's Modelfile TEMPLATE not matching
the Jinja template llama-server/LM Studio render from the GGUF's embedded chat_template.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Windows consoles default to a legacy codepage (e.g. cp950), not UTF-8, which mangles the
# Chinese test strings printed below -- reconfigure stdout so `python -m bench.parity` prints
# correctly out of the box instead of only working inside UTF-8 terminals.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import httpx
import yaml

from bench.client import build_messages, stream_chat_completion

TEST_MESSAGE = "台灣最高的山是哪一座？請只回答山名。"


async def _probe(engine_name: str, cfg: dict, system_prompt: str) -> dict:
    # Tokenization is independent of which per-slot-context model tag is loaded, so any
    # test_type's model resolves to the same prompt_tokens count -- "concurrency" is just
    # the conventional default here (see runner.py's _resolve_model for why Ollama needs this).
    model = cfg.get("model_by_test", {}).get("concurrency", cfg["model"])
    messages = build_messages(system_prompt, TEST_MESSAGE)
    async with httpx.AsyncClient() as client:
        result = await stream_chat_completion(
            client,
            cfg["base_url"],
            model,
            messages,
            api_key=cfg.get("api_key"),
            temperature=0,
            max_tokens=32,
            engine_label=engine_name,
        )
    return {
        "engine": engine_name,
        "success": result.success,
        "error": result.error,
        "prompt_tokens": result.prompt_tokens,
        "response_text": result.response_text.strip(),
    }


async def run_parity_check(config_path: str = "bench/config.yaml") -> bool:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    engines = config["engines"]
    system_prompt = config["system_prompt"]

    results = await asyncio.gather(
        *(_probe(name, cfg, system_prompt) for name, cfg in engines.items())
    )

    print(f"Test message: {TEST_MESSAGE!r}\n")
    ok = True
    prompt_token_values = {}
    for r in results:
        status = "OK" if r["success"] else f"FAILED ({r['error']})"
        print(f"[{r['engine']}] {status}")
        if r["success"]:
            print(f"  prompt_tokens = {r['prompt_tokens']}")
            print(f"  response      = {r['response_text']!r}")
            prompt_token_values[r["engine"]] = r["prompt_tokens"]
        else:
            ok = False

    if len(set(prompt_token_values.values())) > 1:
        print(
            "\n[FAIL] prompt_tokens mismatch across engines: "
            f"{prompt_token_values} -- chat templates are NOT rendering identically. "
            "Check the Ollama Modelfile TEMPLATE against the GGUF's embedded Jinja template."
        )
        ok = False
    elif ok:
        print(f"\n[PASS] All engines agree on prompt_tokens = {next(iter(prompt_token_values.values()))}")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="bench/config.yaml")
    args = parser.parse_args()
    passed = asyncio.run(run_parity_check(args.config))
    raise SystemExit(0 if passed else 1)
