from dataclasses import replace
from pathlib import Path

import pandas as pd

from dashboard.data.benchmark_repository import load_benchmark_evidence
from dashboard.views.evidence import (
    _has_finite_numeric_values,
    build_evidence_view_model,
    build_gateway_cost_chart,
    build_kv_chart,
    build_prefill_chart,
    build_throughput_chart,
    build_ttft_chart,
    build_vram_chart,
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
    c16 = evidence.concurrency[evidence.concurrency["concurrency"].eq(16)]
    kv_control = pd.DataFrame(
        {
            "concurrency": [1, 4],
            "Unified KV Cache OFF": [110.0, 160.0],
            "Unified KV Cache ON": [105.0, 180.0],
        }
    )

    throughput = build_throughput_chart(evidence.concurrency).to_dict()
    ttft = build_ttft_chart(evidence.concurrency).to_dict()
    prefill = build_prefill_chart(evidence.prefill).to_dict()
    gateway = build_gateway_cost_chart(evidence.overhead).to_dict()
    vram = build_vram_chart(c16).to_dict()
    kv = build_kv_chart(kv_control).to_dict()

    assert throughput["height"] == 400
    assert throughput["encoding"]["x"]["title"] == "Concurrency"
    assert throughput["encoding"]["x"]["scale"] == {
        "domain": [0.4, 16.6],
        "nice": False,
    }
    assert throughput["encoding"]["x"]["axis"]["values"] == [1, 4, 8, 16]
    assert throughput["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert ttft["encoding"]["x"]["scale"] == throughput["encoding"]["x"]["scale"]
    assert ttft["encoding"]["x"]["axis"] == throughput["encoding"]["x"]["axis"]
    assert kv["encoding"]["x"]["scale"] == {
        "domain": [0.5, 4.5],
        "nice": False,
    }
    assert kv["encoding"]["x"]["axis"]["values"] == [1, 4]
    assert kv["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert ttft["height"] == 400
    assert prefill["height"] >= 340
    assert gateway["height"] >= 340
    assert vram["height"] >= 340
    assert kv["height"] >= 340
    assert throughput["config"]["axis"]["labelFontSize"] >= 14
    assert ttft["encoding"]["color"]["legend"]["orient"] == "bottom"
    for chart in (throughput, ttft, prefill, gateway, vram, kv):
        assert chart["encoding"]["y"]["title"] is None
    assert throughput["encoding"]["y"]["field"] == "median_aggregate_tok_s"
    assert ttft["encoding"]["y"]["field"] == "ttft_ms"
    assert prefill["encoding"]["y"]["field"] == "median_ttft_s"
    assert gateway["encoding"]["y"]["field"] == "milliseconds"
    assert vram["encoding"]["y"]["field"] == "median_vram_baseline_mb"
    assert kv["encoding"]["y"]["field"] == "ttft_ms"
    assert throughput["encoding"]["y"]["scale"]["zero"] is True
    assert ttft["encoding"]["y"]["scale"]["zero"] is True
    assert kv["encoding"]["y"]["scale"]["zero"] is True
    for chart in (throughput, ttft, kv):
        assert chart["mark"]["type"] == "line"
        assert chart["mark"]["strokeWidth"] == 2.75
        assert chart["mark"]["point"]["size"] == 68
        assert chart["encoding"]["color"]["legend"]["orient"] == "bottom"
    for chart in (prefill, gateway, vram):
        assert chart["mark"]["type"] == "bar"
        assert chart["mark"]["cornerRadiusEnd"] == 5
        assert chart["encoding"]["color"]["legend"]["orient"] == "bottom"
        assert chart["encoding"]["x"]["scale"]["paddingOuter"] == 0.3
        assert chart["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert [item["field"] for item in throughput["encoding"]["tooltip"]] == [
        "engine",
        "concurrency",
        "median_aggregate_tok_s",
    ]
    assert [item["field"] for item in ttft["encoding"]["tooltip"]] == [
        "engine",
        "percentile",
        "concurrency",
        "ttft_ms",
    ]
    assert [item["field"] for item in prefill["encoding"]["tooltip"]] == [
        "engine",
        "prompt_target_tokens",
        "median_ttft_s",
    ]
    assert [item["field"] for item in gateway["encoding"]["tooltip"]] == [
        "path",
        "metric",
        "milliseconds",
    ]
    assert [item["field"] for item in vram["encoding"]["tooltip"]] == [
        "engine",
        "median_vram_baseline_mb",
    ]
    assert [item["field"] for item in kv["encoding"]["tooltip"]] == [
        "setting",
        "concurrency",
        "ttft_ms",
    ]


def test_missing_evidence_artifacts_degrade_without_exception(tmp_path: Path) -> None:
    evidence = load_benchmark_evidence(tmp_path)

    model = build_evidence_view_model(evidence)

    render_evidence(evidence)

    assert evidence.warnings
    assert evidence.provenance == {}
    assert model.public_raw_runs is None
    assert model.measurement_date == "—"


def test_numeric_axis_ignores_non_finite_concurrency_values() -> None:
    frame = pd.DataFrame(
        {
            "engine": ["ollama", "ollama", "ollama", "ollama"],
            "concurrency": [1, float("inf"), float("-inf"), 4],
            "median_aggregate_tok_s": [100, 200, 300, 400],
        }
    )

    x_encoding = build_throughput_chart(frame).to_dict()["encoding"]["x"]

    assert x_encoding["axis"]["values"] == [1, 4]
    assert x_encoding["scale"]["domain"] == [0.5, 4.5]


def test_invalid_concurrency_artifact_degrades_without_exception() -> None:
    evidence = load_benchmark_evidence(Path("bench/results"))
    invalid = evidence.concurrency.copy()
    invalid["concurrency"] = [float("inf")] * len(invalid)

    assert not _has_finite_numeric_values(invalid, "concurrency")
    render_evidence(replace(evidence, concurrency=invalid))


def test_kv_control_without_shared_concurrency_degrades_without_exception() -> None:
    evidence = load_benchmark_evidence(Path("bench/results"))

    render_evidence(
        replace(
            evidence,
            kv_cache_off=[{"concurrency": 1, "ttft_p50_s": 0.1}],
            kv_cache_on=[{"concurrency": 4, "ttft_p50_s": 0.2}],
        )
    )
