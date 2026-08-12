from pathlib import Path

from dashboard.data.benchmark_repository import load_benchmark_evidence
from dashboard.views.evidence import build_evidence_view_model


def test_benchmark_model_includes_scope_and_environment() -> None:
    model = build_evidence_view_model(load_benchmark_evidence(Path("bench/results")))
    assert model.measurement_date == "2026-07-17"
    assert model.gpu == "NVIDIA GeForce RTX 4090"
    assert "硬體、版本與 workload" in model.scope_note
    assert model.public_raw_runs is False
