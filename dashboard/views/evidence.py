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
    public_raw_runs: bool | None
    scope_note: str


def build_evidence_view_model(evidence: BenchmarkEvidence) -> EvidenceViewModel:
    measurement = evidence.provenance.get("measurement", {})
    if not isinstance(measurement, dict):
        measurement = {}
    hardware = measurement.get("hardware", {})
    model = measurement.get("model", {})
    if not isinstance(hardware, dict):
        hardware = {}
    if not isinstance(model, dict):
        model = {}
    raw_runs = measurement.get("public_raw_request_runs")
    return EvidenceViewModel(
        measurement_date=str(measurement.get("date", "—")),
        gpu=str(hardware.get("gpu", "—")),
        model=str(model.get("filename", "—")),
        public_raw_runs=raw_runs if isinstance(raw_runs, bool) else None,
        scope_note="所有結果只適用於記錄的硬體、版本與 workload；不是通用引擎排名。",
    )


def _engine_label(value: str) -> str:
    return {"llamacpp": "llama.cpp", "ollama": "Ollama", "lmstudio": "LM Studio"}.get(value, value)


def _has_columns(frame: pd.DataFrame, columns: set[str]) -> bool:
    return not frame.empty and columns <= set(frame.columns)


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

    concurrency_ok = _has_columns(
        evidence.concurrency,
        {
            "engine",
            "concurrency",
            "median_aggregate_tok_s",
            "p50_ttft_s",
            "p95_ttft_s",
            "median_vram_baseline_mb",
        },
    )
    c16 = (
        evidence.concurrency[evidence.concurrency["concurrency"].eq(16)].copy()
        if concurrency_ok
        else pd.DataFrame()
    )
    if not c16.empty:
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
            "—" if model.public_raw_runs is None else ("Yes" if model.public_raw_runs else "No"),
            "manifest unavailable" if model.public_raw_runs is None else "aggregate evidence only",
        ),
    ]
    for column, card in zip(columns, cards, strict=True):
        with column:
            render_metric_card(*card)

    throughput_col, ttft_col = st.columns(2, gap="large")
    with throughput_col:
        st.markdown("### Aggregate decode throughput")
        if not concurrency_ok:
            render_state_message(
                "Artifact unavailable", "concurrency_summary.csv 無法讀取。", "warning"
            )
        else:
            frame = evidence.concurrency.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            pivot = frame.pivot(
                index="concurrency", columns="engine", values="median_aggregate_tok_s"
            )
            st.line_chart(
                pivot,
                color=["#718B7A", "#78909A", "#B1815F"],
                height=310,
            )
            st.caption("tokens/sec · five-run median · higher is better")
    with ttft_col:
        st.markdown("### P50 / P95 TTFT by concurrency")
        if concurrency_ok:
            frame = evidence.concurrency.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            frame["p50_ttft_ms"] = frame["p50_ttft_s"] * 1000
            frame["p95_ttft_ms"] = frame["p95_ttft_s"] * 1000
            p50 = frame.pivot(index="concurrency", columns="engine", values="p50_ttft_ms")
            p95 = frame.pivot(index="concurrency", columns="engine", values="p95_ttft_ms")
            p50.columns = [f"{column} · P50" for column in p50.columns]
            p95.columns = [f"{column} · P95" for column in p95.columns]
            pivot = p50.join(p95)
            st.line_chart(
                pivot,
                color=["#718B7A", "#9FB2A5", "#78909A", "#A6BBC2", "#B1815F", "#D1AA8E"],
                height=310,
            )
            st.caption("milliseconds · solid series labels identify percentile · lower is better")

    prefill_col, overhead_col = st.columns([1.2, 1], gap="large")
    with prefill_col:
        st.markdown("### Prefill · calibrated prompt")
        prefill_ok = _has_columns(
            evidence.prefill, {"engine", "prompt_target_tokens", "median_ttft_s"}
        )
        if prefill_ok:
            frame = evidence.prefill.copy()
            frame["engine"] = frame["engine"].map(_engine_label)
            frame["label"] = (
                frame["engine"] + " · " + frame["prompt_target_tokens"].astype(str) + " tokens"
            )
            st.bar_chart(frame.set_index("label")["median_ttft_s"], color="#78909A", height=285)
            st.caption("median TTFT in seconds · calibrated 1,970 and 7,880 actual-token inputs")
        else:
            render_state_message(
                "Artifact unavailable", "prefill_summary.csv 無法讀取。", "warning"
            )
    with overhead_col:
        st.markdown("### Gateway cost")
        overhead = evidence.overhead
        direct = overhead.get("direct", {})
        via = overhead.get("via_gateway", {})
        if isinstance(direct, dict) and isinstance(via, dict) and direct and via:
            compare = pd.DataFrame(
                {
                    "path": ["Direct", "Via Gateway"],
                    "Median TTFT": [direct.get("ttft_median_ms"), via.get("ttft_median_ms")],
                    "P95 TTFT": [direct.get("ttft_p95_ms"), via.get("ttft_p95_ms")],
                    "Median total": [direct.get("total_median_ms"), via.get("total_median_ms")],
                }
            ).set_index("path")
            st.bar_chart(compare, color=["#718B7A", "#B1815F", "#78909A"], height=285)
            st.caption(
                "milliseconds · JSON rewrite、failover bookkeeping 與 SSE pass-through 的量測成本"
            )
        else:
            render_state_message(
                "Artifact unavailable", "gateway_overhead.json 無法讀取。", "warning"
            )

    vram_col, kv_col = st.columns([1, 1.35], gap="large")
    with vram_col:
        st.markdown("### VRAM baseline · concurrency 16")
        if not c16.empty:
            vram = c16.copy()
            vram["engine"] = vram["engine"].map(_engine_label)
            vram = vram.set_index("engine")[["median_vram_baseline_mb"]]
            st.bar_chart(vram, color="#718B7A", height=300)
            st.caption(
                "MiB · measured baseline，並非模型品質或跨硬體效率排名；不同 frontend 的 memory strategy 不同。"
            )
    with kv_col:
        st.markdown("### LM Studio · Unified KV Cache control")
        if evidence.kv_cache_off and evidence.kv_cache_on:
            off = pd.DataFrame(evidence.kv_cache_off).rename(
                columns={"ttft_p50_s": "Unified KV Cache OFF"}
            )
            on = pd.DataFrame(evidence.kv_cache_on).rename(
                columns={"ttft_p50_s": "Unified KV Cache ON"}
            )
            required_off = {"concurrency", "Unified KV Cache OFF"}
            required_on = {"concurrency", "Unified KV Cache ON"}
            if _has_columns(off, required_off) and _has_columns(on, required_on):
                control = off[["concurrency", "Unified KV Cache OFF"]].merge(
                    on[["concurrency", "Unified KV Cache ON"]], on="concurrency"
                )
                control[["Unified KV Cache OFF", "Unified KV Cache ON"]] *= 1000
                st.line_chart(
                    control.set_index("concurrency"),
                    color=["#718B7A", "#B1815F"],
                    height=300,
                )
                st.caption(
                    "P50 TTFT / ms · paired controlled observation。ON 在部分 concurrency 出現高延遲；內部分配或 scheduling 解釋仍是 hypothesis。"
                )
            else:
                render_state_message(
                    "Controlled scan unavailable",
                    "Unified KV Cache paired artifacts schema 無法辨識。",
                    "warning",
                )
        else:
            render_state_message(
                "Controlled scan unavailable",
                "Unified KV Cache paired artifacts 無法讀取。",
                "warning",
            )

    st.markdown("### Method & Provenance")
    render_state_message("Scope", model.scope_note)
    measurement = evidence.provenance.get("measurement", {})
    if not isinstance(measurement, dict):
        measurement = {}
    method = measurement.get("method", {})
    engines = measurement.get("engines", {})
    if not isinstance(method, dict):
        method = {}
    if not isinstance(engines, dict):
        engines = {}
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
        st.markdown(f"**Prefix-cache control**\n\n{method.get('request_nonce', '—')}")
    artifact_classes: dict[str, int] = {}
    for artifact in evidence.provenance.get("artifacts", []):
        if isinstance(artifact, dict):
            artifact_class = str(artifact.get("class", "unknown"))
            artifact_classes[artifact_class] = artifact_classes.get(artifact_class, 0) + 1
    with st.expander("Engine versions 與 publication boundary"):
        st.json(engines)
        st.write(
            "Request-level raw runs 未公開；本頁只使用 committed aggregate summaries、controlled scans、calibrated inputs 與 derived charts。"
        )
        st.write("Digest policy：" + str(evidence.provenance.get("digest_policy", "unavailable")))
        st.write(f"Artifact classes：{artifact_classes or 'unavailable'}")
        st.code("EVAL_REPORT.md", language=None)
