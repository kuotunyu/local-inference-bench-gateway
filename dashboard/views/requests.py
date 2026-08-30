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
REQUEST_TABLE_ROW_HEIGHT = 42
REQUEST_TABLE_COLUMNS = [
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


def request_table_column_config() -> dict[str, dict[str, object]]:
    """Return a centered, zh-TW-first display contract for Request telemetry."""
    return {
        "timestamp": st.column_config.DatetimeColumn(
            "時間（UTC+8）",
            width=205,
            alignment="center",
            format="YYYY-MM-DD HH:mm:ss",
            timezone="Asia/Taipei",
        ),
        "alias": st.column_config.TextColumn("Alias", width=82, alignment="center"),
        "backend_name": st.column_config.TextColumn("Backend", width=125, alignment="center"),
        "model": st.column_config.TextColumn("Model", width=145, alignment="center"),
        "status_code": st.column_config.TextColumn("HTTP", width=82, alignment="center"),
        "success": st.column_config.CheckboxColumn("成功", width=72, alignment="center"),
        "Latency": st.column_config.TextColumn("Latency", width=95, alignment="center"),
        "TTFT": st.column_config.TextColumn("TTFT", width=90, alignment="center"),
        "prompt_tokens": st.column_config.TextColumn(
            "Prompt tokens", width=120, alignment="center"
        ),
        "completion_tokens": st.column_config.TextColumn(
            "Completion tokens", width=145, alignment="center"
        ),
        "stream": st.column_config.CheckboxColumn("Streaming", width=95, alignment="center"),
        "error_category": st.column_config.TextColumn("Error 分類", width=130, alignment="center"),
    }


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
    for column in ("alias", "backend_name", "model", "error_category"):
        if column in table:
            table[column] = table[column].astype("string").fillna("—")
    for column in ("status_code", "prompt_tokens", "completion_tokens"):
        if column in table:
            numeric = pd.to_numeric(table[column], errors="coerce")
            table[column] = numeric.map(lambda value: "—" if pd.isna(value) else f"{value:,.0f}")
    for column in ("success", "stream"):
        if column in table:
            numeric = pd.to_numeric(table[column], errors="coerce")
            table[column] = numeric.map({1: True, 0: False}).astype("boolean")
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


def render_requests(
    snapshot: TelemetrySnapshot, source_kind: str, *, source_note: str | None = None
) -> None:
    render_page_heading(
        "REQUEST EXPLORER",
        "請求遙測檢視",
        "依 Alias、Backend、結果與 Error 分類篩選 Request Telemetry；缺失值維持未知，不以 0 取代。",
    )
    render_source_badge(source_kind, source_note or "SQLite Request log")
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
        render_state_message("沒有符合條件的 Request", "篩選器已保留；放寬任一條件即可繼續探索。")
        return
    table = build_request_table(filtered)
    st.dataframe(
        table.loc[:, REQUEST_TABLE_COLUMNS],
        hide_index=True,
        width="stretch",
        height=REQUEST_TABLE_HEIGHT,
        row_height=REQUEST_TABLE_ROW_HEIGHT,
        column_order=REQUEST_TABLE_COLUMNS,
        column_config=request_table_column_config(),
    )
    st.caption("— 代表 Upstream 未提供或該 Request 不適用；並不代表 0 ms 或 0 tokens。")
