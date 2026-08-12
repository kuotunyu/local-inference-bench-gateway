"""Filterable request explorer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import (
    format_metric,
    render_metric_card,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
from dashboard.metrics import compute_overview, with_error_categories
from dashboard.models import TelemetrySnapshot


def build_request_table(requests: pd.DataFrame) -> pd.DataFrame:
    table = with_error_categories(requests)
    table["timestamp"] = pd.to_datetime(table["timestamp"], utc=True, errors="coerce")
    table = table.sort_values("timestamp", ascending=False, na_position="last")
    ttft = pd.to_numeric(
        table.get("ttft_ms", pd.Series(index=table.index, dtype=float)), errors="coerce"
    )
    table["TTFT"] = ttft.map(lambda value: "—" if pd.isna(value) else f"{value:,.0f} ms")
    latency = pd.to_numeric(
        table.get("total_latency_ms", pd.Series(index=table.index, dtype=float)),
        errors="coerce",
    )
    table["Latency"] = latency.map(lambda value: "—" if pd.isna(value) else f"{value:,.0f} ms")
    return table


def _filter_controls(requests: pd.DataFrame) -> pd.DataFrame:
    frame = with_error_categories(requests)
    filters = st.columns([1.1, 1.1, 1, 1])
    aliases = sorted(frame["alias"].dropna().unique().tolist())
    backends = sorted(frame["backend_name"].dropna().unique().tolist())
    categories = sorted(frame["error_category"].dropna().unique().tolist())
    with filters[0]:
        alias = st.multiselect("Alias", aliases, placeholder="全部 Alias")
    with filters[1]:
        backend = st.multiselect("Backend", backends, placeholder="全部 Backend")
    with filters[2]:
        outcome = st.selectbox("Outcome", ["全部", "Success", "Failure"])
    with filters[3]:
        category = st.multiselect("Error category", categories, placeholder="全部 Error")
    if alias:
        frame = frame[frame["alias"].isin(alias)]
    if backend:
        frame = frame[frame["backend_name"].isin(backend)]
    if outcome != "全部":
        frame = frame[frame["success"].eq(1 if outcome == "Success" else 0)]
    if category:
        frame = frame[frame["error_category"].isin(category)]
    return frame


def render_requests(snapshot: TelemetrySnapshot, source_kind: str) -> None:
    render_page_heading(
        "REQUEST EXPLORER",
        "每一筆請求，都能回到證據。",
        "用 Alias、Backend、Outcome 與 Error category 收斂問題；空值保留為空值，不用 0 製造假精確。",
    )
    render_source_badge(
        source_kind,
        "SQLite request log" + (" · illustrative fixture" if source_kind == "demo" else ""),
    )
    if snapshot.requests.empty:
        render_state_message(
            "尚無 request telemetry",
            "Gateway 收到第一筆 `/v1/chat/completions` 後，本頁會保留在原位並開始顯示資料。",
        )
        return
    filtered = _filter_controls(snapshot.requests)
    summary = compute_overview(filtered, snapshot.failovers.iloc[0:0])
    columns = st.columns(4)
    cards = [
        ("FILTERED REQUESTS", f"{summary.request_count:,}", "matching records"),
        ("SUCCESS RATE", format_metric(summary.success_rate_pct, "%"), "filtered scope"),
        ("P50 LATENCY", format_metric(summary.p50_latency_ms, " ms", digits=0), "total latency"),
        ("P95 TTFT", format_metric(summary.p95_ttft_ms, " ms", digits=0), "streaming when present"),
    ]
    for column, card in zip(columns, cards, strict=True):
        with column:
            render_metric_card(*card)
    if filtered.empty:
        render_state_message("沒有符合條件的 request", "篩選器已保留；放寬任一條件即可繼續探索。")
        return
    table = build_request_table(filtered)
    visible = [
        "timestamp",
        "alias",
        "backend_name",
        "model",
        "status_code",
        "success",
        "Latency",
        "TTFT",
        "prompt_tokens",
        "completion_tokens",
        "stream",
        "error_category",
    ]
    st.dataframe(table[visible], hide_index=True, width="stretch", height=470)
    st.caption("— 代表 upstream 未提供或該 request 不適用；並不代表 0 ms 或 0 tokens。")
