"""Sequential local quality measurements; not an official OpenTWBench leaderboard run.

Install twinkle-eval==2.10.0 in a separate evaluation environment. The upstream
BoxExtractor is used unchanged, but only FINAL content is scored (never reasoning).
Dataset downloads, server lifecycle and publication are deliberately separate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Callable

import httpx

SYSTEM = r"請回答選擇題，使用繁體中文。最後以 \boxed{X} 表示答案，X 為 A、B、C 或 D。"
LETTERS = "ABCD"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def prepare_rows(rows: list[dict], seed: int) -> list[dict]:
    """Allowlist question/options; retain labels separately, never context/provenance text."""
    result, seen = [], set()
    for row in rows:
        if (
            any(
                not isinstance(row.get(k), str) or not row[k].strip()
                for k in ("question", *LETTERS, "answer")
            )
            or row["answer"] not in LETTERS
        ):
            raise ValueError("Invalid MCQ row")
        if len(row["answer"]) != 1:
            raise ValueError("Invalid gold label")
        identity = digest([row["question"], sorted(row[k] for k in LETTERS)])
        if identity in seen:
            raise ValueError("Duplicate question/options")
        seen.add(identity)
        order = list(LETTERS)
        random.Random(f"{seed}:{identity}").shuffle(order)
        options = {new: row[old] for new, old in zip(LETTERS, order, strict=True)}
        result.append(
            {
                "id": identity,
                "category": row.get("category", "unknown"),
                "prompt": row["question"]
                + "\n"
                + "\n".join(f"{key}. {value}" for key, value in options.items()),
                "options": options,
                "answer": LETTERS[order.index(row["answer"])],
            }
        )
    return sorted(result, key=lambda r: r["id"])


def score_response(response: dict, gold: str, extract: Callable) -> dict:
    choice = response["choices"][0]
    content = choice["message"].get("content") or ""
    predicted = extract(content)
    parsed = isinstance(predicted, str) and predicted in set(LETTERS)
    return {
        "predicted": predicted,
        "parsed": parsed,
        "correct": parsed and predicted == gold,
        "finish_reason": choice.get("finish_reason"),
    }


def summarize(records: list[dict]) -> dict:
    count = len(records)
    return {
        "requests": count,
        "accuracy": sum(r["correct"] for r in records) / count if count else None,
        "parse_rate": sum(r["parsed"] for r in records) / count if count else None,
        "errors": sum(r.get("error") is not None for r in records),
        "length_finishes": sum(r.get("finish_reason") == "length" for r in records),
    }


def run(args: argparse.Namespace) -> None:
    # Lazy import keeps the normal Gateway/CI environment independent of Twinkle's stack.
    from importlib.metadata import version

    from twinkle_eval.metrics.extractors.box import BoxExtractor

    if version("twinkle-eval") != "2.10.0":
        raise ValueError("Use the pinned twinkle-eval==2.10.0 evaluation environment")
    if httpx.URL(args.base_url).host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("This experiment only calls a loopback backend")
    rows = []
    files = sorted(args.dataset.glob("*.jsonl"))
    if not files:
        raise ValueError("No JSONL dataset files")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for path in files:
        rows.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    prepared = prepare_rows(rows, args.seed)
    if len(prepared) != args.expected_count:
        raise ValueError(f"Expected {args.expected_count} unique rows; got {len(prepared)}")
    args.output.mkdir(parents=True, exist_ok=False)  # Never overwrite or silently retry a run.
    config = {
        "dataset_files": hashes,
        "dataset_revision": args.revision,
        "prepared_sha256": digest(prepared),
        "count": len(prepared),
        "thinking": args.thinking,
        "seed": args.seed,
        "system": SYSTEM,
        "max_tokens": 1536,
        "temperature": 0,
        "top_p": 1,
        "concurrency": 1,
        "retries": 0,
        "extractor": "twinkle-eval==2.10.0/box",
        "final_content_only": True,
        "base_url": args.base_url,
        "model_sha256": args.model_sha256,
        "started_unix": time.time(),
    }
    extract = BoxExtractor().extract
    records = []
    with httpx.Client(base_url=args.base_url, timeout=180, trust_env=False) as client:
        # Store the served template and effective runtime defaults with every run.
        props = client.get("/props")
        props.raise_for_status()
        config["server_props"] = props.json()
        (args.output / "manifest.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with (args.output / "raw.jsonl").open("x", encoding="utf-8") as handle:
            for row in prepared:
                request = {
                    "model": "gemma-local",
                    "messages": [
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": row["prompt"]},
                    ],
                    "temperature": 0,
                    "top_p": 1,
                    "seed": args.seed,
                    "max_tokens": 1536,
                    "stream": False,
                    "cache_prompt": False,
                    "chat_template_kwargs": {"enable_thinking": args.thinking},
                }
                record = {
                    "id": row["id"],
                    "category": row["category"],
                    "gold": row["answer"],
                    "request": request,
                    "correct": False,
                    "parsed": False,
                    "error": None,
                }
                start = time.perf_counter()
                try:
                    response = client.post("/v1/chat/completions", json=request)
                    record["http_status"] = response.status_code
                    response.raise_for_status()
                    record["response"] = response.json()
                    record.update(score_response(record["response"], row["answer"], extract))
                except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
                    record["error"] = type(exc).__name__ + ": " + str(exc)
                record["client_seconds"] = time.perf_counter() - start
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                records.append(record)
                print(
                    json.dumps(
                        {
                            "completed": len(records),
                            "total": len(prepared),
                            "error": record["error"],
                        }
                    ),
                    flush=True,
                )
                # Infrastructure failure stops admission; partial runs are never full scores.
                if record["error"] is not None:
                    break
    summary = summarize(records)
    summary["expected"] = len(prepared)
    summary["complete"] = len(records) == len(prepared)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if not summary["complete"] or summary["errors"]:
        raise RuntimeError("Run failed or incomplete; preserved records, no automatic retry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:18765")
    parser.add_argument("--seed", type=int, default=42)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
