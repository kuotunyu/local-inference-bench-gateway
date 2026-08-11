from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from release_checks.evidence import verify_evidence

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS = REPO_ROOT / "bench" / "results"


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (RESULTS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_value(name: str, field: str, **filters: str) -> float:
    rows = _csv_rows(name)
    [row] = [row for row in rows if all(row[key] == value for key, value in filters.items())]
    return float(row[field])


def _scan_value(name: str, concurrency: int) -> float:
    rows = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    [row] = [row for row in rows if row["concurrency"] == concurrency]
    return float(row["ttft_p50_s"])


def test_evidence_manifest_is_complete_and_valid():
    assert verify_evidence(REPO_ROOT) == []


def test_canonical_claim_values_recompute_from_public_artifacts():
    assert _csv_value(
        "concurrency_summary.csv",
        "median_aggregate_tok_s",
        engine="llamacpp",
        concurrency="16",
    ) == pytest.approx(625.5453408690353)
    assert _csv_value(
        "concurrency_summary.csv",
        "median_aggregate_tok_s",
        engine="ollama",
        concurrency="16",
    ) == pytest.approx(704.9783261338363)
    assert _csv_value(
        "concurrency_summary.csv",
        "median_aggregate_tok_s",
        engine="lmstudio",
        concurrency="16",
    ) == pytest.approx(686.7198727101736)
    assert _csv_value(
        "prefill_summary.csv",
        "median_ttft_s",
        engine="lmstudio",
        prompt_target_tokens="8000",
    ) == pytest.approx(1.2390633999966667)

    llama_vram = _csv_value(
        "concurrency_summary.csv",
        "median_vram_baseline_mb",
        engine="llamacpp",
        concurrency="16",
    )
    lmstudio_vram = _csv_value(
        "concurrency_summary.csv",
        "median_vram_baseline_mb",
        engine="lmstudio",
        concurrency="16",
    )
    assert round(lmstudio_vram / llama_vram * 100, 1) == 42.7

    gateway = json.loads((RESULTS / "gateway_overhead.json").read_text(encoding="utf-8"))
    assert round(gateway["overhead_ms"], 2) == 1.66
    assert (
        round(_scan_value("lmstudio_concurrency_boundary_scan_unified_kv_on.json", 14) * 1000)
        == 4024
    )
    assert round(_scan_value("lmstudio_concurrency_boundary_scan.json", 16) * 1000) == 430


def test_each_concurrency_level_spread_is_explicitly_not_a_universal_ten_percent_claim():
    rows = _csv_rows("concurrency_summary.csv")
    spreads = {}
    for concurrency in {row["concurrency"] for row in rows}:
        values = [
            float(row["median_aggregate_tok_s"])
            for row in rows
            if row["concurrency"] == concurrency
        ]
        spreads[int(concurrency)] = (max(values) - min(values)) / min(values) * 100

    assert spreads[8] > 10
    public_docs = "\n".join(
        (REPO_ROOT / name).read_text(encoding="utf-8").lower()
        for name in ("README.md", "EVAL_REPORT.md", "DESIGN.md")
    )
    assert "within 10%" not in public_docs
    assert "10% 以內" not in public_docs


def test_provenance_records_pinned_environment_and_raw_data_boundary():
    provenance = json.loads((RESULTS / "provenance.json").read_text(encoding="utf-8"))

    assert provenance["measurement"]["date"] == "2026-07-17"
    assert provenance["measurement"]["hardware"]["gpu"] == "NVIDIA GeForce RTX 4090"
    assert provenance["measurement"]["hardware"]["vram_mib"] == 24564
    assert provenance["measurement"]["public_raw_request_runs"] is False
    assert provenance["source_snapshot"]["commit"] == ("f7b80d221460f1e1219a0ec5c7044465ea961dba")
