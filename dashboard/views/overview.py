"""Gateway overview view."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import streamlit as st

from dashboard.components import (
    format_metric,
    render_metric_card,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
from dashboard.data.live_status import GatewayStatus
from dashboard.metrics import OverviewMetrics, bucket_request_series, compute_overview
from dashboard.models import TelemetrySnapshot
from gateway.registry import Registry


@dataclass(frozen=True)
class OverviewModel:
    source_label: str
    observed_from: datetime | None
    observed_to: datetime | None
    metrics: OverviewMetrics
    series: pd.DataFrame


def _bounds(frame: pd.DataFrame) -> tuple[datetime | None, datetime | None]:
    values = pd.to_datetime(frame.get("timestamp"), utc=True, errors="coerce").dropna()
    if values.empty:
        return None, None
    return values.min().to_pydatetime(), values.max().to_pydatetime()


def build_overview_model(snapshot: TelemetrySnapshot, source_kind: str) -> OverviewModel:
    observed_from, observed_to = _bounds(snapshot.requests)
    return OverviewModel(
        source_label="DEMO DATA" if source_kind == "demo" else "LIVE",
        observed_from=observed_from,
        observed_to=observed_to,
        metrics=compute_overview(snapshot.requests, snapshot.failovers),
        series=bucket_request_series(snapshot.requests),
    )


def _time_note(model: OverviewModel) -> str:
    if model.observed_from is None or model.observed_to is None:
        return "目前 observation window 尚無 request telemetry"
    start = model.observed_from.astimezone().strftime("%Y/%m/%d %H:%M")
    end = model.observed_to.astimezone().strftime("%H:%M %Z")
    return f"Observation window · {start}–{end}"


def _render_health(status: GatewayStatus) -> None:
    st.markdown("### Backend Health · 目前觀測")
    if not status.reachable:
        render_state_message(
            "Gateway offline",
            "仍可閱讀已寫入的 telemetry；offline 不等於歷史 Backend Health 或 SLA。",
            "warning",
        )
        return
    if not status.backends:
        render_state_message(
            "Gateway reachable",
            "Backend Health 需要有效的 API key；目前不推測 backend 狀態。",
        )
        return
    for url, health in status.backends.items():
        healthy = bool(health.get("healthy"))
        label = "Healthy" if healthy else "Degraded"
        tone = "healthy" if healthy else "warning"
        name = url.split("//")[-1].split("/")[0]
        st.markdown(
            f'<div class="status-card"><span class="status-dot {tone}"></span>'
            f"<strong>{name}</strong><br><small>{label} · current probe</small></div>",
            unsafe_allow_html=True,
        )


def render_overview(
    snapshot: TelemetrySnapshot,
    source_kind: str,
    status: GatewayStatus,
    registry: Registry,
) -> None:
    model = build_overview_model(snapshot, source_kind)
    render_page_heading(
        "GATEWAY OVERVIEW",
        "推論系統，一眼掌握。",
        "從 request、latency、routing 到 failover，把單機 inference gateway 的運行證據放在同一個視野。",
    )
    source_note = _time_note(model)
    if source_kind == "demo":
        source_note += " · illustrative fixture，非 production traffic"
    render_source_badge(source_kind, source_note)

    metrics = model.metrics
    columns = st.columns(5)
    cards = [
        ("REQUEST VOLUME", f"{metrics.request_count:,}", "selected window"),
        (
            "SUCCESS RATE",
            format_metric(metrics.success_rate_pct, "%", digits=1),
            f"{int(round(metrics.request_count * (metrics.success_rate_pct or 0) / 100)):,} successful",
        ),
        ("P50 LATENCY", format_metric(metrics.p50_latency_ms, " ms", digits=0), "total latency"),
        ("P95 LATENCY", format_metric(metrics.p95_latency_ms, " ms", digits=0), "total latency"),
        ("FAILOVER EVENTS", f"{metrics.failover_count:,}", "observed transitions"),
    ]
    for column, card in zip(columns, cards, strict=True):
        with column:
            render_metric_card(*card)

    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown("### Request volume 與 P95 latency")
        if model.series.empty:
            render_state_message("尚無趨勢資料", "第一筆 request 寫入後，這裡會顯示時間序列。")
        else:
            request_chart, latency_chart = st.columns(2)
            series = model.series.set_index("timestamp")
            with request_chart:
                st.caption("REQUESTS / BUCKET")
                st.bar_chart(series[["requests"]], color="#718B7A", height=245)
            with latency_chart:
                st.caption("P95 LATENCY / MS")
                st.line_chart(series[["p95_latency_ms"]], color="#B1815F", height=245)
            st.caption("分離量級避免小流量被 latency 軸壓扁；hover 可讀取精確值。")
    with right:
        _render_health(status)

    route_col, failover_col = st.columns([1.15, 1], gap="large")
    with route_col:
        st.markdown("### Alias Routing")
        for alias, config in registry.items():
            chain = " → ".join(backend.name for backend in config.backends)
            cap = "uncapped" if config.max_concurrent is None else f"max {config.max_concurrent}"
            st.markdown(f"**{alias}**　`{chain}`　 · {cap}")
    with failover_col:
        st.markdown("### Recent Failover")
        if snapshot.failovers.empty:
            st.caption("目前 observation window 沒有 failover event。")
        else:
            recent = snapshot.failovers.head(4).copy()
            recent["route"] = (
                recent["failed_backend"].fillna("—") + " → " + recent["next_backend"].fillna("none")
            )
            st.dataframe(
                recent[["timestamp", "alias", "route", "reason"]],
                hide_index=True,
                width="stretch",
                height=180,
            )
