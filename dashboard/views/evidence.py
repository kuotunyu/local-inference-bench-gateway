"""Committed benchmark evidence presentation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from dashboard.components import (
    format_metric,
    render_metric_card,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
from dashboard.models import BenchmarkEvidence


@dataclass(frozen=True)
class EvidenceViewModel:
    measurement_date: str
    gpu: str
    model: str
    public_raw_runs: bool
    scope_note: str


def build_evidence_view_model(evidence: BenchmarkEvidence) -> EvidenceViewModel:
    measurement = evidence.provenance.get("measurement", {})
    hardware = measurement.get("hardware", {})
    model = measurement.get("model", {})
    return EvidenceViewModel(
        measurement_date=str(measurement.get("date", "—")),
        gpu=str(hardware.get("gpu", "—")),
        model=str(model.get("filename", "—")),
        public_raw_runs=bool(measurement.get("public_raw_request_runs", False)),
        scope_note="所有結果只適用於記錄的硬體、版本與 workload；不是通用引擎排名。",
    )


def _engine_label(value: str) -> str:
    return {"llamacpp": "llama.cpp", "ollama": "Ollama", "lmstudio": "LM Studio"}.get(value, value)


def render_evidence(evidence: BenchmarkEvidence) -> None:
    model = build_evidence_view_model(evidence)
    render_page_heading(
        "BENCHMARK EVIDENCE",
        "快，不夠。還要知道為什麼可信。",
        "聚合結果、控制條件、測量環境與 provenance 同頁呈現，讓每個 performance claim 都有邊界。",
    )
    verified = (
        "all published artifact digests verified"
        if not evidence.warnings
        else (f"{len(evidence.warnings)} artifact warning(s)")
    )
    render_source_badge("evidence", f"Committed aggregate artifacts · {verified}")
    if evidence.warnings:
        render_state_message(
            "Evidence verification warning",
            "、".join(f"{path}: {reason}" for path, reason in evidence.warnings.items()),
            "warning",
        )

    c16 = evidence.concurrency[evidence.concurrency["concurrency"].eq(16)].copy()
    c16 = c16.sort_values("median_aggregate_tok_s", ascending=False)
    top = c16.iloc[0] if not c16.empty else None
    columns = st.columns(4)
    cards = [
        (
            "TOP C16 THROUGHPUT",
            "—"
            if top is None
            else format_metric(top["median_aggregate_tok_s"], " tok/s", digits=0),
            "—" if top is None else _engine_label(str(top["engine"])),
        ),
        (
            "GATEWAY OVERHEAD",
            format_metric(evidence.overhead.get("overhead_ms"), " ms", digits=2),
            "median TTFT · direct vs gateway",
        ),
        ("MEASURED ON", model.measurement_date, model.gpu),
        (
            "PUBLIC RAW RUNS",
            "No" if not model.public_raw_runs else "Yes",
            "aggregate evidence only",
        ),
    ]
    for column, card in zip(columns, cards, strict=True):
        with column:
            render_metric_card(*card)

    throughput_col, ttft_col = st.columns(2, gap="large")
    with throughput_col:
        st.markdown("### Aggregate decode throughput")
        if evidence.concurrency.empty:
            render_state_message(
                "Artifact unavailable", "concurrency_summary.csv 無法讀取。", "warning"
            )
        else:
            frame = evidence.concurrency.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            pivot = frame.pivot(
                index="concurrency", columns="engine", values="median_aggregate_tok_s"
            )
            st.line_chart(pivot, color=["#718B7A", "#78909A", "#B1815F"], height=310)
            st.caption("tokens/sec · five-run median · higher is better")
    with ttft_col:
        st.markdown("### P50 TTFT by concurrency")
        if not evidence.concurrency.empty:
            frame = evidence.concurrency.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            frame["p50_ttft_ms"] = frame["p50_ttft_s"] * 1000
            pivot = frame.pivot(index="concurrency", columns="engine", values="p50_ttft_ms")
            st.line_chart(pivot, color=["#718B7A", "#78909A", "#B1815F"], height=310)
            st.caption("milliseconds · lower is better · behavior changes by concurrency")

    prefill_col, overhead_col = st.columns([1.2, 1], gap="large")
    with prefill_col:
        st.markdown("### Prefill · calibrated prompt")
        if not evidence.prefill.empty:
            frame = evidence.prefill.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            frame["label"] = (
                frame["engine"] + " · " + frame["prompt_target_tokens"].astype(str) + " tokens"
            )
            st.bar_chart(frame.set_index("label")["median_ttft_s"], color="#78909A", height=285)
            st.caption("median TTFT in seconds · calibrated 1,970 and 7,880 actual-token inputs")
    with overhead_col:
        st.markdown("### Gateway cost")
        overhead = evidence.overhead
        direct = overhead.get("direct", {})
        via = overhead.get("via_gateway", {})
        compare = pd.DataFrame(
            {
                "path": ["Direct", "Via Gateway"],
                "Median TTFT": [direct.get("ttft_median_ms"), via.get("ttft_median_ms")],
                "P95 TTFT": [direct.get("ttft_p95_ms"), via.get("ttft_p95_ms")],
            }
        ).set_index("path")
        st.bar_chart(compare, color=["#718B7A", "#B1815F"], height=285)
        st.caption(
            "milliseconds · JSON rewrite、failover bookkeeping 與 SSE pass-through 的量測成本"
        )

    st.markdown("### Method & Provenance")
    render_state_message("Scope", model.scope_note)
    measurement = evidence.provenance.get("measurement", {})
    method = measurement.get("method", {})
    engines = measurement.get("engines", {})
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f"""**Model**
`{model.model}`

**GPU**
{model.gpu}

**Measurement date**
{model.measurement_date}"""
        )
    with right:
        st.markdown(
            f"""**Method**
{method.get("warmup_runs", "—")} warmups · {method.get("timed_runs", "—")} timed runs · seed {method.get("seed", "—")}

**Engine isolation**
{method.get("engine_isolation", "—")}"""
        )
    with st.expander("Engine versions 與 publication boundary"):
        st.json(engines)
        st.write(
            "Request-level raw runs 未公開；本頁只使用 committed aggregate summaries、controlled scans、calibrated inputs 與 derived charts。"
        )
