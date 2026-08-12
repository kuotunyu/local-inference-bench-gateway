from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from dashboard.data.benchmark_repository import load_benchmark_evidence

RESULTS_DIR = Path("bench/results")


def test_repository_loads_committed_aggregate_evidence() -> None:
    evidence = load_benchmark_evidence(RESULTS_DIR)

    assert set(evidence.concurrency["engine"]) == {"llamacpp", "ollama", "lmstudio"}
    assert evidence.overhead["overhead_ms"] == pytest.approx(1.656700020248536)
    assert evidence.provenance["measurement"]["public_raw_request_runs"] is False
    assert len(evidence.kv_cache_off) == 16
    assert len(evidence.kv_cache_on) == 16
    assert evidence.warnings == {}


def test_digest_mismatch_isolated_to_affected_artifact(tmp_path: Path) -> None:
    for filename in [
        "concurrency_summary.csv",
        "prefill_summary.csv",
        "gateway_overhead.json",
        "provenance.json",
        "claims.json",
    ]:
        shutil.copy2(RESULTS_DIR / filename, tmp_path / filename)
    (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")

    evidence = load_benchmark_evidence(tmp_path)

    assert "concurrency_summary.csv" in evidence.warnings
    assert evidence.overhead["overhead_ms"] > 0
