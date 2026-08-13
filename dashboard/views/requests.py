"""Filterable request explorer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import (
    format_metric,
    render_metric_grid,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
from dashboard.metrics import compute_overview, with_error_categories
from dashboard.models import TelemetrySnapshot

REQUEST_TABLE_HEIGHT = 540


def build_request_table(requests: pd.DataFrame) -> pd.DataFrame:
    table = with_error_categories(requests)
    table["timestamp"] = pd.to_datetime(
        table["timestamp"], utc=True, errors="coerce"
    ).dt.tz_convert("Asia/Taipei")
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


def apply_request_filters(
    requests: pd.DataFrame,
    *,
    aliases: list[str] | None = None,
    backends: list[str] | None = None,
    outcome: str = "全部",
    categories: list[str] | None = None,
    status_codes: list[int] | None = None,
    stream_mode: str = "全部",
) -> pd.DataFrame:
    frame = with_error_categories(requests)
    if aliases:
        frame = frame[frame["alias"].isin(aliases)]
    if backends:
        frame = frame[frame["backend_name"].isin(backends)]
    if outcome != "全部":
        frame = frame[frame["success"].eq(1 if outcome == "Success" else 0)]
    if categories:
        frame = frame[frame["error_category"].isin(categories)]
    if status_codes:
        frame = frame[pd.to_numeric(frame["status_code"], errors="coerce").isin(status_codes)]
    if stream_mode != "全部":
        frame = frame[frame["stream"].eq(1 if stream_mode == "Streaming" else 0)]
    return frame


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
        outcome = st.selectbox("結果", ["全部", "Success", "Failure"])
    with filters[3]:
        category = st.multiselect("Error 分類", categories, placeholder="全部 Error")
    secondary = st.columns(2)
    status_options = sorted(
        int(value)
        for value in pd.to_numeric(frame["status_code"], errors="coerce").dropna().unique()
    )
    with secondary[0]:
        status_codes = st.multiselect("Status code", status_options, placeholder="全部 Status")
    with secondary[1]:
        stream_mode = st.selectbox("傳輸方式", ["全部", "Streaming", "Non-streaming"])
    return apply_request_filters(
        requests,
        aliases=alias,
        backends=backend,
        outcome=outcome,
        categories=category,
        status_codes=status_codes,
        stream_mode=stream_mode,
    )


def render_requests(snapshot: TelemetrySnapshot, source_kind: str) -> None:
    render_page_heading(
        "REQUEST EXPLORER",
        "請求遙測檢視",
        "依 Alias、Backend、結果與 Error 分類篩選 Request Telemetry；缺失值維持未知，不以 0 取代。",
    )
    render_source_badge(
        source_kind,
        "SQLite Request log" + (" · 示範 fixture" if source_kind == "demo" else ""),
    )
    if snapshot.requests.empty:
        render_state_message(
            "尚無 Request Telemetry",
            "Gateway 收到第一筆 `/v1/chat/completions` 後，本頁會保留在原位並開始顯示資料。",
        )
        return
    filtered = _filter_controls(snapshot.requests)
    summary = compute_overview(filtered, snapshot.failovers.iloc[0:0])
    cards = [
        ("篩選後 REQUEST", f"{summary.request_count:,}", "筆符合條件"),
        ("成功率", format_metric(summary.success_rate_pct, "%"), "目前篩選結果"),
        ("P50 LATENCY", format_metric(summary.p50_latency_ms, " ms", digits=0), "端到端 latency"),
        ("P95 LATENCY", format_metric(summary.p95_latency_ms, " ms", digits=0), "端到端 latency"),
    ]
    cards += [
        ("P50 TTFT", format_metric(summary.p50_ttft_ms, " ms", digits=0), "有資料時顯示"),
        (
            "P95 TTFT",
            format_metric(summary.p95_ttft_ms, " ms", digits=0),
            "Streaming 有資料時顯示",
        ),
        (
            "TOKEN 數量",
            (
                "—"
                if summary.prompt_tokens is None or summary.completion_tokens is None
                else f"{summary.prompt_tokens + summary.completion_tokens:,}"
            ),
            (
                "Upstream usage 不完整"
                if summary.prompt_tokens is None or summary.completion_tokens is None
                else f"{summary.prompt_tokens:,} prompt · {summary.completion_tokens:,} completion"
            ),
        ),
    ]
    render_metric_grid(cards)
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
    st.dataframe(
        table[visible],
        hide_index=True,
        width="stretch",
        height=REQUEST_TABLE_HEIGHT,
        row_height=36,
    )
    st.caption("— 代表 Upstream 未提供或該 Request 不適用；並不代表 0 ms 或 0 tokens。")
