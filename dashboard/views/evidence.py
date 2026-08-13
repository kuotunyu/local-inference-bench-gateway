"""Committed benchmark evidence presentation."""

from __future__ import annotations

from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.charts import bar_chart, line_chart
from dashboard.components import (
    format_metric,
    render_metric_grid,
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


def build_throughput_chart(concurrency: pd.DataFrame) -> alt.Chart:
    frame = concurrency.copy()
    frame["engine"] = frame["engine"].map(_engine_label)
    return line_chart(
        frame,
        x="concurrency:Q",
        y="median_aggregate_tok_s:Q",
        color="engine:N",
        height=400,
        x_title="Concurrency",
        y_title="Throughput / tok/s",
        tooltip=["engine:N", "concurrency:Q", "median_aggregate_tok_s:Q"],
        color_range=["#718B7A", "#78909A", "#B1815F"],
        zero=True,
    )


def build_ttft_chart(concurrency: pd.DataFrame) -> alt.Chart:
    frame = concurrency.copy()
    frame["engine"] = frame["engine"].map(_engine_label)
    frame["P50"] = frame["p50_ttft_s"] * 1000
    frame["P95"] = frame["p95_ttft_s"] * 1000
    long = frame.melt(
        id_vars=["engine", "concurrency"],
        value_vars=["P50", "P95"],
        var_name="percentile",
        value_name="ttft_ms",
    )
    long["series"] = long["engine"] + " · " + long["percentile"]
    return line_chart(
        long,
        x="concurrency:Q",
        y="ttft_ms:Q",
        color="series:N",
        height=400,
        x_title="Concurrency",
        y_title="TTFT / ms",
        tooltip=["engine:N", "percentile:N", "concurrency:Q", "ttft_ms:Q"],
        color_range=["#718B7A", "#9FB2A5", "#78909A", "#A6BBC2", "#B1815F", "#D1AA8E"],
        zero=True,
    )


def build_prefill_chart(prefill: pd.DataFrame) -> alt.Chart:
    frame = prefill.copy()
    frame["engine"] = frame["engine"].map(_engine_label)
    frame["label"] = frame["engine"] + " · " + frame["prompt_target_tokens"].astype(str)
    return bar_chart(
        frame,
        x="label:N",
        y="median_ttft_s:Q",
        color="engine:N",
        height=350,
        x_title="Engine · 目標 tokens",
        y_title="Median TTFT / s",
        tooltip=["engine:N", "prompt_target_tokens:Q", "median_ttft_s:Q"],
        color_range=["#718B7A", "#78909A", "#B1815F"],
    )


def build_gateway_cost_chart(overhead: dict) -> alt.Chart:
    direct = overhead.get("direct", {})
    via = overhead.get("via_gateway", {})
    frame = pd.DataFrame(
        {
            "path": ["Direct", "經 Gateway"],
            "Median TTFT": [direct.get("ttft_median_ms"), via.get("ttft_median_ms")],
            "P95 TTFT": [direct.get("ttft_p95_ms"), via.get("ttft_p95_ms")],
            "Median total": [direct.get("total_median_ms"), via.get("total_median_ms")],
        }
    ).melt(id_vars="path", var_name="metric", value_name="milliseconds")
    return bar_chart(
        frame,
        x="path:N",
        y="milliseconds:Q",
        color="metric:N",
        height=350,
        x_title=None,
        y_title="Latency / ms",
        tooltip=["path:N", "metric:N", "milliseconds:Q"],
        color_range=["#718B7A", "#B1815F", "#78909A"],
    )


def build_vram_chart(c16: pd.DataFrame) -> alt.Chart:
    frame = c16.copy()
    frame["engine"] = frame["engine"].map(_engine_label)
    return bar_chart(
        frame,
        x="engine:N",
        y="median_vram_baseline_mb:Q",
        color="engine:N",
        height=350,
        x_title=None,
        y_title="VRAM baseline / MiB",
        tooltip=["engine:N", "median_vram_baseline_mb:Q"],
        color_range=["#718B7A", "#78909A", "#B1815F"],
    )


def build_kv_chart(control: pd.DataFrame) -> alt.Chart:
    long = control.melt(id_vars="concurrency", var_name="setting", value_name="ttft_ms")
    return line_chart(
        long,
        x="concurrency:Q",
        y="ttft_ms:Q",
        color="setting:N",
        height=350,
        x_title="Concurrency",
        y_title="P50 TTFT / ms",
        tooltip=["setting:N", "concurrency:Q", "ttft_ms:Q"],
        color_range=["#718B7A", "#B1815F"],
        zero=True,
    )


def render_evidence(evidence: BenchmarkEvidence) -> None:
    model = build_evidence_view_model(evidence)
    render_page_heading(
        "BENCHMARK EVIDENCE",
        "Benchmark 測量證據",
        "並列 aggregate 結果、控制條件、測量環境與 provenance，界定 performance measurement 的適用範圍。",
    )
    verified = (
        "已驗證所有已發布 Artifact 的 digest"
        if not evidence.warnings
        else (f"{len(evidence.warnings)} 個 Artifact 警告")
    )
    render_source_badge("evidence", f"已提交的 aggregate Artifact · {verified}")
    if evidence.warnings:
        render_state_message(
            "Evidence 驗證警告",
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
    cards = [
        (
            "C16 最高 THROUGHPUT",
            "—"
            if top is None
            else format_metric(top["median_aggregate_tok_s"], " tok/s", digits=0),
            "—" if top is None else _engine_label(str(top["engine"])),
        ),
        (
            "GATEWAY 額外成本",
            format_metric(evidence.overhead.get("overhead_ms"), " ms", digits=2),
            "Median TTFT · Direct 與 Gateway",
        ),
        ("測量日期", model.measurement_date, model.gpu),
        (
            "PUBLIC RAW RUNS",
            "—" if model.public_raw_runs is None else ("是" if model.public_raw_runs else "否"),
            "manifest 無法使用" if model.public_raw_runs is None else "僅提供 aggregate evidence",
        ),
    ]
    render_metric_grid(cards)

    st.markdown("### Aggregate decode throughput 比較")
    if not concurrency_ok:
        render_state_message("Artifact 無法使用", "concurrency_summary.csv 無法讀取。", "warning")
    else:
        st.altair_chart(build_throughput_chart(evidence.concurrency), width="stretch")
        st.caption("tokens/sec · 五次測量的 median · 數值越高越好")

    st.markdown("### 依 concurrency 比較 P50 / P95 TTFT")
    if concurrency_ok:
        st.altair_chart(build_ttft_chart(evidence.concurrency), width="stretch")
        st.caption("milliseconds · series label 標示 percentile · 數值越低越好")

    prefill_col, overhead_col = st.columns([1.2, 1], gap="large")
    with prefill_col:
        st.markdown("### Prefill · 校準後 prompt")
        prefill_ok = _has_columns(
            evidence.prefill, {"engine", "prompt_target_tokens", "median_ttft_s"}
        )
        if prefill_ok:
            st.altair_chart(build_prefill_chart(evidence.prefill), width="stretch")
            st.caption("Median TTFT（秒）· 校準為實際 1,970 與 7,880 tokens 的輸入")
        else:
            render_state_message("Artifact 無法使用", "prefill_summary.csv 無法讀取。", "warning")
    with overhead_col:
        st.markdown("### Gateway 成本")
        overhead = evidence.overhead
        direct = overhead.get("direct", {})
        via = overhead.get("via_gateway", {})
        if isinstance(direct, dict) and isinstance(via, dict) and direct and via:
            st.altair_chart(build_gateway_cost_chart(overhead), width="stretch")
            st.caption(
                "milliseconds · JSON rewrite、Failover bookkeeping 與 SSE pass-through 的量測成本"
            )
        else:
            render_state_message("Artifact 無法使用", "gateway_overhead.json 無法讀取。", "warning")

    vram_col, kv_col = st.columns([1, 1.35], gap="large")
    with vram_col:
        st.markdown("### VRAM baseline · concurrency 16")
        if not c16.empty:
            st.altair_chart(build_vram_chart(c16), width="stretch")
            st.caption(
                "MiB · measured baseline，並非模型品質或跨硬體效率排名；不同 frontend 採用不同 memory strategy。"
            )
    with kv_col:
        st.markdown("### LM Studio · Unified KV Cache 控制")
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
                st.altair_chart(build_kv_chart(control), width="stretch")
                st.caption(
                    "P50 TTFT / ms · paired controlled observation。ON 在部分 concurrency 出現高延遲；內部分配或 scheduling 的解釋仍屬 hypothesis。"
                )
            else:
                render_state_message(
                    "Controlled scan 無法使用",
                    "Unified KV Cache paired Artifact schema 無法辨識。",
                    "warning",
                )
        else:
            render_state_message(
                "Controlled scan 無法使用",
                "Unified KV Cache paired Artifact 無法讀取。",
                "warning",
            )

    st.markdown("### 測量方法與 provenance")
    render_state_message("適用範圍", model.scope_note)
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
            f"""**模型**
`{model.model}`

**GPU**
{model.gpu}

**測量日期**
{model.measurement_date}"""
        )
    with right:
        st.markdown(
            f"""**測量方法**
{method.get("warmup_runs", "—")} 次 warmup · {method.get("timed_runs", "—")} 次計時測量 · seed {method.get("seed", "—")}

**Engine 隔離**
{method.get("engine_isolation", "—")}"""
        )
        st.markdown(f"**Prefix-cache 控制**\n\n{method.get('request_nonce', '—')}")
    artifact_classes: dict[str, int] = {}
    for artifact in evidence.provenance.get("artifacts", []):
        if isinstance(artifact, dict):
            artifact_class = str(artifact.get("class", "unknown"))
            artifact_classes[artifact_class] = artifact_classes.get(artifact_class, 0) + 1
    with st.expander("Engine 版本與 publication boundary"):
        st.json(engines)
        st.write(
            "Request-level raw runs 未公開；本頁僅使用 committed aggregate summaries、controlled scans、calibrated inputs 與 derived charts。"
        )
        st.write("Digest policy：" + str(evidence.provenance.get("digest_policy", "無法使用")))
        st.write(f"Artifact classes：{artifact_classes or '無法使用'}")
        st.code("EVAL_REPORT.md", language=None)
