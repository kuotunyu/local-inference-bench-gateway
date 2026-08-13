"""Routing, health, failover, and backpressure view."""

from __future__ import annotations

from dataclasses import dataclass

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.charts import style_chart
from dashboard.components import (
    escape_html,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
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


def build_error_chart(errors: pd.DataFrame) -> alt.Chart:
    """Render failure categories with readable labels and direct values."""
    chart = (
        alt.Chart(errors)
        .mark_bar(color="#A45F5F", cornerRadiusEnd=5, height=30)
        .encode(
            x=alt.X("size:Q", title="觀測到的 failure", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("error_category:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("error_category:N", title="分類"),
                alt.Tooltip("size:Q", title="數量"),
            ],
        )
        .properties(height=360)
    )
    return style_chart(chart)


def render_reliability(
    snapshot: TelemetrySnapshot,
    source_kind: str,
    status: GatewayStatus,
    registry: Registry,
) -> None:
    model = build_reliability_model(snapshot, status, registry)
    render_page_heading(
        "ROUTING & RELIABILITY",
        "路由與可靠性分析",
        "對照 Alias Routing、Request-time Failover、Backend Health 與 Backpressure，檢視路由決策及失效處理。",
    )
    note = "SQLite telemetry + models.yaml"
    if source_kind == "demo":
        note += " · 示範 fixture"
    render_source_badge(source_kind, note)
    st.caption(
        "Routing invariant · Health polling 僅供觀測；每個 Request 仍會依照 ordered Backend chain "
        "實際嘗試，不會根據可能過期的 health flag 跳過 Backend。"
    )

    route_col, health_col = st.columns([1.25, 1], gap="large")
    with route_col:
        st.markdown("### Alias Routing")
        route_columns = st.columns(min(max(len(model.routes), 1), 2), gap="small")
        for index, route in enumerate(model.routes):
            with route_columns[index % len(route_columns)]:
                chain = escape_html("　→　".join(route["chain"]))
                cap = route["max_concurrent"]
                capacity = escape_html("無限制" if cap is None else f"max_concurrent = {cap}")
                models = escape_html(" → ".join(route["models"]))
                st.markdown(
                    '<div class="status-card" style="margin-bottom:.55rem">'
                    f"<strong>{escape_html(route['alias'])}</strong>"
                    f'<div style="margin:.4rem 0;color:#40564B">{chain}</div>'
                    f"<small>解析後 model：{models}</small><br>"
                    f"<small>{capacity} · HTTP 429，不建立隱性 queue</small></div>",
                    unsafe_allow_html=True,
                )
    with health_col:
        st.markdown(f"### {model.health_heading}")
        if not status.reachable:
            render_state_message("Gateway 離線", "無法取得目前 probe；不推算 uptime。", "warning")
        elif not status.backends:
            render_state_message(
                "Health detail 無法使用", "Gateway 可連線，但 Backend detail 未授權或尚未回報。"
            )
        else:
            health_rows = []
            for url, entry in status.backends.items():
                health_rows.append(
                    {
                        "backend": url.split("//")[-1],
                        "status": "正常" if entry.get("healthy") else "降級",
                        "last_checked": entry.get("last_checked") or "—",
                    }
                )
            st.dataframe(health_rows, hide_index=True, width="stretch")

    error_col, pressure_col = st.columns([2.15, 1], gap="large")
    with error_col:
        st.markdown("### Error 分類")
        if model.errors.empty:
            st.caption("目前沒有 failure 紀錄。")
        else:
            st.altair_chart(build_error_chart(model.errors), width="stretch")
    with pressure_col:
        st.markdown("### Backpressure")
        st.metric("觀測到的 HTTP 429", model.backpressure_count)
        st.caption(
            "僅計算實際拒絕紀錄；現有 schema 沒有目前的 in-flight 數量或 queue depth，因此不做推測。"
        )

    st.markdown("### Failover event")
    if snapshot.failovers.empty:
        render_state_message("沒有 failover event", "這只代表所選資料範圍未觀測到事件。")
    else:
        table = snapshot.failovers.copy()
        table["next_backend"] = table["next_backend"].fillna("無 · chain 已耗盡")
        st.dataframe(table, hide_index=True, width="stretch", height=300)
