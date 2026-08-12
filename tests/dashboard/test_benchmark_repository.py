from __future__ import annotations

import json
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
    assert evidence.concurrency.empty
    assert evidence.overhead["overhead_ms"] > 0


def test_missing_provenance_never_claims_verified(tmp_path: Path) -> None:
    evidence = load_benchmark_evidence(tmp_path)

    assert evidence.warnings["provenance.json"] == "invalid_or_missing_manifest"
    assert evidence.concurrency.empty
    assert evidence.overhead == {}


def test_malformed_provenance_and_json_shapes_are_quarantined(tmp_path: Path) -> None:
    (tmp_path / "provenance.json").write_text('{"artifacts":"invalid"}', encoding="utf-8")
    (tmp_path / "gateway_overhead.json").write_text("[]", encoding="utf-8")
    (tmp_path / "lmstudio_concurrency_boundary_scan.json").write_text("{}", encoding="utf-8")

    evidence = load_benchmark_evidence(tmp_path)

    assert evidence.warnings["provenance.json"] == "invalid_or_missing_manifest"
    assert evidence.provenance == {}
    assert evidence.overhead == {}
    assert evidence.kv_cache_off == []


@pytest.mark.parametrize(
    ("artifact", "expected_reason"),
    [
        ({"path": "concurrency_summary.csv"}, "invalid_manifest_entry"),
        (
            {"path": "concurrency_summary.csv", "sha256": "not-a-digest"},
            "invalid_manifest_entry",
        ),
        ({"path": "../outside.csv", "sha256": "0" * 64}, "unsafe_artifact_path"),
        (
            {"path": "../results/concurrency_summary.csv", "sha256": "0" * 64},
            "unsafe_artifact_path",
        ),
    ],
)
def test_invalid_manifest_entries_never_claim_verified(
    tmp_path: Path, artifact: dict, expected_reason: str
) -> None:
    (tmp_path / "provenance.json").write_text(
        json.dumps({"artifacts": [artifact]}), encoding="utf-8"
    )

    evidence = load_benchmark_evidence(tmp_path)

    assert expected_reason in evidence.warnings.values()
    assert evidence.provenance == {}


def test_manifest_must_cover_every_displayed_artifact(tmp_path: Path) -> None:
    shutil.copy2(RESULTS_DIR / "provenance.json", tmp_path / "provenance.json")
    provenance = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
    provenance["artifacts"] = [provenance["artifacts"][0]]
    (tmp_path / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    evidence = load_benchmark_evidence(tmp_path)

    assert evidence.warnings["prefill_summary.csv"] == "missing_from_manifest"
    assert evidence.provenance == {}


def test_duplicate_manifest_paths_are_invalid(tmp_path: Path) -> None:
    shutil.copy2(RESULTS_DIR / "provenance.json", tmp_path / "provenance.json")
    provenance = json.loads((tmp_path / "provenance.json").read_text(encoding="utf-8"))
    provenance["artifacts"].append(provenance["artifacts"][0])
    (tmp_path / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    evidence = load_benchmark_evidence(tmp_path)

    assert evidence.warnings["provenance.json"] == "duplicate_artifact_path"
    assert evidence.provenance == {}
