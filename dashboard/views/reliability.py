"""Routing, health, failover, and backpressure view."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from dashboard.components import render_page_heading, render_source_badge, render_state_message
from dashboard.data.live_status import GatewayStatus
from dashboard.metrics import with_error_categories
from dashboard.models import TelemetrySnapshot
from gateway.registry import Registry


@dataclass(frozen=True)
class ReliabilityModel:
    health_heading: str
    routes: list[dict]
    errors: pd.DataFrame
    backpressure_count: int


def build_reliability_model(
    snapshot: TelemetrySnapshot, status: GatewayStatus, registry: Registry
) -> ReliabilityModel:
    del status
    categorized = with_error_categories(snapshot.requests)
    errors = (
        categorized.dropna(subset=["error_category"])
        .groupby("error_category", as_index=False)
        .size()
        .sort_values("size", ascending=False)
    )
    routes = [
        {
            "alias": alias,
            "chain": [backend.name for backend in config.backends],
            "models": [backend.model for backend in config.backends],
            "max_concurrent": config.max_concurrent,
        }
        for alias, config in registry.items()
    ]
    backpressure = categorized["error_category"].eq("Backpressure").sum()
    return ReliabilityModel("Backend Health · 目前觀測", routes, errors, int(backpressure))


def render_reliability(
    snapshot: TelemetrySnapshot,
    source_kind: str,
    status: GatewayStatus,
    registry: Registry,
) -> None:
    model = build_reliability_model(snapshot, status, registry)
    render_page_heading(
        "ROUTING & RELIABILITY",
        "不是漂亮圖表，是可追溯的行為。",
        "把 Alias routing、request-time failover、Backend Health 與 Backpressure 放回同一條因果鏈。",
    )
    note = "SQLite telemetry + models.yaml"
    if source_kind == "demo":
        note += " · illustrative fixture"
    render_source_badge(source_kind, note)
    render_state_message(
        "Routing invariant",
        "Health polling 只提供觀測；每次 request 仍會依 ordered backend chain 實際嘗試，不使用可能過期的 health flag 跳過 backend。",
    )

    route_col, health_col = st.columns([1.25, 1], gap="large")
    with route_col:
        st.markdown("### Alias Routing")
        for route in model.routes:
            chain = "　→　".join(route["chain"])
            cap = route["max_concurrent"]
            capacity = "unlimited" if cap is None else f"max_concurrent = {cap}"
            st.markdown(
                f'<div class="status-card" style="margin-bottom:.7rem"><strong>{route["alias"]}</strong>'
                f'<div style="margin:.5rem 0;color:#40564B">{chain}</div>'
                f"<small>{capacity} · HTTP 429，不建立隱性 queue</small></div>",
                unsafe_allow_html=True,
            )
    with health_col:
        st.markdown(f"### {model.health_heading}")
        if not status.reachable:
            render_state_message(
                "Gateway offline", "無法取得 current probe；不推算 uptime。", "warning"
            )
        elif not status.backends:
            render_state_message(
                "Health detail unavailable", "Gateway 可達，但 backend detail 未授權或尚未回報。"
            )
        else:
            health_rows = []
            for url, entry in status.backends.items():
                health_rows.append(
                    {
                        "backend": url.split("//")[-1],
                        "status": "Healthy" if entry.get("healthy") else "Degraded",
                        "last_checked": entry.get("last_checked") or "—",
                    }
                )
            st.dataframe(health_rows, hide_index=True, width="stretch")

    error_col, pressure_col = st.columns([1.4, 1], gap="large")
    with error_col:
        st.markdown("### Error Categories")
        if model.errors.empty:
            st.caption("目前沒有 failure record。")
        else:
            st.bar_chart(model.errors.set_index("error_category"), color="#A45F5F", height=235)
    with pressure_col:
        st.markdown("### Backpressure")
        st.metric("Observed HTTP 429", model.backpressure_count)
        st.caption(
            "僅計算實際拒絕紀錄；現有 schema 沒有 current in-flight 或 queue depth，因此不做推測。"
        )

    st.markdown("### Failover Events")
    if snapshot.failovers.empty:
        render_state_message("沒有 failover event", "這只代表所選資料範圍未觀測到事件。")
    else:
        table = snapshot.failovers.copy()
        table["next_backend"] = table["next_backend"].fillna("none · chain exhausted")
        st.dataframe(table, hide_index=True, width="stretch", height=300)
