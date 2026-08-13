from pathlib import Path

from dashboard.data.benchmark_repository import load_benchmark_evidence
from dashboard.views.evidence import (
    build_evidence_view_model,
    build_prefill_chart,
    build_throughput_chart,
    build_ttft_chart,
    render_evidence,
)


def test_benchmark_model_includes_scope_and_environment() -> None:
    model = build_evidence_view_model(load_benchmark_evidence(Path("bench/results")))
    assert model.measurement_date == "2026-07-17"
    assert model.gpu == "NVIDIA GeForce RTX 4090"
    assert "硬體、版本與 workload" in model.scope_note
    assert model.public_raw_runs is False


def test_primary_evidence_charts_use_expanded_readable_canvases() -> None:
    evidence = load_benchmark_evidence(Path("bench/results"))

    throughput = build_throughput_chart(evidence.concurrency).to_dict()
    ttft = build_ttft_chart(evidence.concurrency).to_dict()
    prefill = build_prefill_chart(evidence.prefill).to_dict()

    assert throughput["height"] == 400
    assert ttft["height"] == 400
    assert prefill["height"] >= 340
    assert throughput["config"]["axis"]["labelFontSize"] >= 14
    assert ttft["encoding"]["color"]["legend"]["orient"] == "bottom"


def test_missing_evidence_artifacts_degrade_without_exception(tmp_path: Path) -> None:
    evidence = load_benchmark_evidence(tmp_path)

    model = build_evidence_view_model(evidence)

    render_evidence(evidence)

    assert evidence.warnings
    assert evidence.provenance == {}
    assert model.public_raw_runs is None
    assert model.measurement_date == "—"
