"""Aggregates bench/results/raw/*/*.jsonl into summary CSVs and comparison charts.

Reads whatever engines/test_types are present under raw_results_dir -- run this after any
subset of runner.py invocations to get a partial view, or after the full matrix for the final
EVAL_REPORT.md numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ENGINE_ORDER = ["llamacpp", "ollama", "lmstudio"]
ENGINE_LABELS = {"llamacpp": "llama.cpp", "ollama": "Ollama", "lmstudio": "LM Studio"}
ENGINE_COLORS = {"llamacpp": "#4C72B0", "ollama": "#DD8452", "lmstudio": "#55A868"}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pct(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else float("nan")


def build_concurrency_summary(raw_dir: Path) -> pd.DataFrame:
    rows = []
    for engine in ENGINE_ORDER:
        records = _load_jsonl(raw_dir / engine / "concurrency.jsonl")
        by_c: dict[int, list[dict]] = {}
        for r in records:
            by_c.setdefault(r["concurrency"], []).append(r)

        for concurrency, batches in sorted(by_c.items()):
            agg_tok_s = [
                b["aggregate_tokens_per_sec"] for b in batches if b.get("aggregate_tokens_per_sec")
            ]
            all_ttft = [
                req["ttft_s"]
                for b in batches
                for req in b["requests"]
                if req.get("success") and req.get("ttft_s") is not None
            ]
            vram_deltas = [b["vram_peak_delta_mb"] for b in batches]
            vram_baselines = [b["vram_baseline_mb"] for b in batches]
            n_failed = sum(b["n_failed"] for b in batches)
            n_total = sum(b["n_success"] + b["n_failed"] for b in batches)

            rows.append(
                {
                    "engine": engine,
                    "concurrency": concurrency,
                    "n_runs": len(batches),
                    "n_requests_total": n_total,
                    "n_failed": n_failed,
                    "median_aggregate_tok_s": float(np.median(agg_tok_s))
                    if agg_tok_s
                    else float("nan"),
                    "p50_ttft_s": _pct(all_ttft, 50),
                    "p95_ttft_s": _pct(all_ttft, 95),
                    "p99_ttft_s": _pct(all_ttft, 99),
                    "median_vram_peak_delta_mb": float(np.median(vram_deltas))
                    if vram_deltas
                    else float("nan"),
                    # This is the resident model+runtime footprint (baseline is sampled AFTER the
                    # engine's model is already loaded), not incremental KV growth during a batch --
                    # the meaningful cross-engine VRAM comparison, see plot_vram().
                    "median_vram_baseline_mb": float(np.median(vram_baselines))
                    if vram_baselines
                    else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def build_prefill_summary(raw_dir: Path) -> pd.DataFrame:
    rows = []
    for engine in ENGINE_ORDER:
        records = _load_jsonl(raw_dir / engine / "prefill.jsonl")
        by_target: dict[int, list[dict]] = {}
        for r in records:
            by_target.setdefault(r["prompt_target_tokens"], []).append(r)

        for target, runs in sorted(by_target.items()):
            ok_runs = [r for r in runs if r.get("success")]
            ttfts = [r["ttft_s"] for r in ok_runs if r.get("ttft_s") is not None]
            vram_deltas = [r["vram_peak_delta_mb"] for r in runs]
            actual_tokens = ok_runs[0]["prompt_actual_tokens"] if ok_runs else None

            rows.append(
                {
                    "engine": engine,
                    "prompt_target_tokens": target,
                    "prompt_actual_tokens": actual_tokens,
                    "n_runs": len(runs),
                    "n_failed": len(runs) - len(ok_runs),
                    "median_ttft_s": float(np.median(ttfts)) if ttfts else float("nan"),
                    "p50_ttft_s": _pct(ttfts, 50),
                    "p95_ttft_s": _pct(ttfts, 95),
                    "median_vram_peak_delta_mb": float(np.median(vram_deltas))
                    if vram_deltas
                    else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def plot_throughput_vs_concurrency(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for engine in ENGINE_ORDER:
        sub = df[df["engine"] == engine].sort_values("concurrency")
        if sub.empty:
            continue
        ax.plot(
            sub["concurrency"],
            sub["median_aggregate_tok_s"],
            marker="o",
            label=ENGINE_LABELS[engine],
            color=ENGINE_COLORS[engine],
        )
    ax.set_xlabel("Concurrency")
    ax.set_ylabel("Aggregate decode throughput (tokens/sec)")
    ax.set_title("Throughput vs. Concurrency")
    ax.set_xticks(sorted(df["concurrency"].unique()) if not df.empty else [])
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_ttft_vs_concurrency(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for engine in ENGINE_ORDER:
        sub = df[df["engine"] == engine].sort_values("concurrency")
        if sub.empty:
            continue
        ax.plot(
            sub["concurrency"],
            sub["p50_ttft_s"],
            marker="o",
            label=f"{ENGINE_LABELS[engine]} P50",
            color=ENGINE_COLORS[engine],
        )
        ax.plot(
            sub["concurrency"],
            sub["p95_ttft_s"],
            marker="x",
            linestyle="--",
            label=f"{ENGINE_LABELS[engine]} P95",
            color=ENGINE_COLORS[engine],
            alpha=0.6,
        )
    ax.set_xlabel("Concurrency")
    ax.set_ylabel("TTFT (seconds)")
    ax.set_title("TTFT (P50/P95) vs. Concurrency")
    ax.set_xticks(sorted(df["concurrency"].unique()) if not df.empty else [])
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_prefill_time(df: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    for engine in ENGINE_ORDER:
        sub = df[df["engine"] == engine].sort_values("prompt_target_tokens")
        if sub.empty:
            continue
        ax.plot(
            sub["prompt_target_tokens"],
            sub["median_ttft_s"],
            marker="o",
            label=ENGINE_LABELS[engine],
            color=ENGINE_COLORS[engine],
        )
    ax.set_xlabel("Prompt length (tokens, target)")
    ax.set_ylabel("TTFT / prefill time (seconds)")
    ax.set_title("Prefill Time vs. Prompt Length")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_vram(concurrency_df: pd.DataFrame, out_path: Path) -> None:
    # Baseline (sampled after the model is already loaded, before the timed batch) is the
    # resident model+runtime VRAM footprint -- the meaningful cross-engine comparison. Per-batch
    # delta stays near zero for this workload (max_tokens=256 barely grows the KV cache), so it
    # isn't chart-worthy on its own.
    max_c = concurrency_df["concurrency"].max() if not concurrency_df.empty else None
    sub = (
        concurrency_df[concurrency_df["concurrency"] == max_c]
        if max_c
        else concurrency_df.iloc[0:0]
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    engines = [e for e in ENGINE_ORDER if e in sub["engine"].values]
    values = [sub[sub["engine"] == e]["median_vram_baseline_mb"].iloc[0] for e in engines]
    colors = [ENGINE_COLORS[e] for e in engines]
    ax.bar([ENGINE_LABELS[e] for e in engines], values, color=colors)
    ax.set_ylabel("Resident VRAM footprint (MB)")
    ax.set_title(f"VRAM Footprint at Concurrency={max_c} (model + runtime, loaded)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="bench/config.yaml")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    raw_dir = Path(config["paths"]["raw_results_dir"])
    out_dir = Path(config["paths"]["summary_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    concurrency_df = build_concurrency_summary(raw_dir)
    prefill_df = build_prefill_summary(raw_dir)

    concurrency_df.to_csv(out_dir / "concurrency_summary.csv", index=False)
    prefill_df.to_csv(out_dir / "prefill_summary.csv", index=False)
    print(f"Wrote {out_dir / 'concurrency_summary.csv'} ({len(concurrency_df)} rows)")
    print(f"Wrote {out_dir / 'prefill_summary.csv'} ({len(prefill_df)} rows)")

    if not concurrency_df.empty:
        plot_throughput_vs_concurrency(concurrency_df, out_dir / "throughput_vs_concurrency.png")
        plot_ttft_vs_concurrency(concurrency_df, out_dir / "ttft_vs_concurrency.png")
        plot_vram(concurrency_df, out_dir / "vram_usage.png")
        print("Wrote throughput_vs_concurrency.png, ttft_vs_concurrency.png, vram_usage.png")
    if not prefill_df.empty:
        plot_prefill_time(prefill_df, out_dir / "prefill_time_vs_prompt_length.png")
        print("Wrote prefill_time_vs_prompt_length.png")

    print("\n=== Concurrency summary ===")
    print(concurrency_df.to_string(index=False))
    print("\n=== Prefill summary ===")
    print(prefill_df.to_string(index=False))


if __name__ == "__main__":
    main()
