"""Gateway overview view."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from dashboard.charts import style_chart
from dashboard.components import (
    escape_html,
    format_metric,
    render_metric_grid,
    render_page_heading,
    render_source_badge,
    render_state_message,
)
from dashboard.data.live_status import GatewayStatus
from dashboard.metrics import OverviewMetrics, bucket_request_series, compute_overview
from dashboard.models import TelemetrySnapshot
from gateway.registry import Registry

DISPLAY_TIMEZONE = ZoneInfo("Asia/Taipei")
ACTIVITY_INTERVALS = tuple(
    pd.Timedelta(value)
    for value in ("10min", "30min", "1h", "2h", "4h", "6h", "12h", "1D", "2D", "7D")
)
ACTIVITY_DOMAIN_PADDING = pd.Timedelta(minutes=5)


@dataclass(frozen=True)
class ActivityTimeGuide:
    domain: tuple[datetime, datetime]
    ticks: tuple[datetime, ...]


@dataclass(frozen=True)
class OverviewModel:
    source_label: str
    observed_from: datetime | None
    observed_to: datetime | None
    metrics: OverviewMetrics
    series: pd.DataFrame


def _activity_time_guide(frame: pd.DataFrame) -> ActivityTimeGuide:
    timestamps = pd.to_datetime(frame.get("timestamp"), utc=True, errors="coerce").dropna()
    if timestamps.empty:
        raise ValueError("activity chart requires a valid timestamp")
    start = timestamps.min()
    end = timestamps.max()
    target = max((end - start) / 6, ACTIVITY_INTERVALS[0])
    interval = next(
        (candidate for candidate in ACTIVITY_INTERVALS if candidate >= target),
        ACTIVITY_INTERVALS[-1],
    )
    tick_start = start.ceil(interval)
    ticks = tuple(pd.date_range(tick_start, end, freq=interval).to_pydatetime())
    if not ticks:
        ticks = (start.to_pydatetime(),)
    return ActivityTimeGuide(
        domain=(
            (start - ACTIVITY_DOMAIN_PADDING).to_pydatetime(),
            (end + ACTIVITY_DOMAIN_PADDING).to_pydatetime(),
        ),
        ticks=ticks,
    )


def _bounds(frame: pd.DataFrame) -> tuple[datetime | None, datetime | None]:
    values = pd.to_datetime(frame.get("timestamp"), utc=True, errors="coerce").dropna()
    if values.empty:
        return None, None
    return values.min().to_pydatetime(), values.max().to_pydatetime()


def build_overview_model(
    snapshot: TelemetrySnapshot,
    source_kind: str,
    observation_window_minutes: int | None = None,
) -> OverviewModel:
    observed_from, observed_to = _bounds(snapshot.requests)
    return OverviewModel(
        source_label="DEMO DATA" if source_kind == "demo" else "LIVE",
        observed_from=observed_from,
        observed_to=observed_to,
        metrics=compute_overview(
            snapshot.requests,
            snapshot.failovers,
            observation_window_minutes=observation_window_minutes,
        ),
        series=bucket_request_series(snapshot.requests),
    )


def _time_note(model: OverviewModel) -> str:
    if model.observed_from is None or model.observed_to is None:
        return "目前觀測時間範圍尚無 Request Telemetry"
    start = model.observed_from.astimezone(DISPLAY_TIMEZONE).strftime("%Y/%m/%d %H:%M")
    end = model.observed_to.astimezone(DISPLAY_TIMEZONE).strftime("%H:%M")
    return f"觀測時間範圍 · {start}–{end} UTC+8"


def build_activity_chart(series: pd.DataFrame) -> alt.Chart:
    """Combine request volume and latency without compressing either scale."""
    frame = series.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    guide = _activity_time_guide(frame)
    bucket_slots = max(len(frame) + 2, 9)
    x_encoding = alt.X(
        "timestamp:T",
        title=None,
        scale=alt.Scale(domain=list(guide.domain), nice=False),
        axis=alt.Axis(
            values=list(guide.ticks),
            format="%H:%M",
            labelAngle=0,
            labelOverlap="greedy",
            tickSize=6,
            tickWidth=1.25,
            tickColor="#7B867F",
            domainColor="#7B867F",
        ),
    )
    requests = (
        alt.Chart(frame)
        .mark_bar(
            color="#5F7F6B",
            opacity=0.9,
            size=alt.ExprRef(expr=f"min(54, width / {bucket_slots} * 0.82)"),
        )
        .encode(
            x=x_encoding,
            y=alt.Y(
                "requests:Q",
                title=None,
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="時間", format="%Y/%m/%d %H:%M"),
                alt.Tooltip("requests:Q", title="Request 數"),
            ],
        )
    )
    latency = (
        alt.Chart(frame)
        .mark_line(
            color="#B56F45",
            strokeWidth=5,
            point=alt.OverlayMarkDef(color="#B56F45", size=120, filled=True, strokeWidth=2),
        )
        .encode(
            x=x_encoding,
            y=alt.Y(
                "p95_latency_ms:Q",
                title=None,
                scale=alt.Scale(zero=False),
                axis=alt.Axis(orient="right"),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="時間", format="%Y/%m/%d %H:%M"),
                alt.Tooltip("p95_latency_ms:Q", title="P95 latency", format=",.0f"),
            ],
        )
    )
    return style_chart(
        alt.layer(requests, latency).resolve_scale(y="independent").properties(height=400)
    )


def activity_measure_key_html() -> str:
    """Map each horizontal measure label to its chart mark without rotated text."""
    return (
        '<div class="activity-measure-key">'
        '<span class="activity-key-item request"><i class="activity-key-bar" '
        'aria-hidden="true"></i>Request 數量／bucket</span>'
        '<span class="activity-key-item latency"><i class="activity-key-line" '
        'aria-hidden="true"></i>P95 latency／ms</span>'
        "</div>"
    )


def _render_health(status: GatewayStatus) -> None:
    st.markdown("### Backend Health · 目前觀測")
    if not status.reachable:
        render_state_message(
            "Gateway 離線",
            "仍可閱讀已寫入的 Telemetry；離線不代表歷史 Backend Health 或 SLA。",
            "warning",
        )
        return
    if not status.backends:
        render_state_message(
            "Gateway 可連線",
            f"Backend Health 暫時無法取得（{status.reason}）；目前不推測 Backend 狀態。",
        )
        return
    for url, health in status.backends.items():
        healthy = bool(health.get("healthy"))
        label = "正常" if healthy else "降級"
        tone = "healthy" if healthy else "warning"
        name = url.split("//")[-1].split("/")[0]
        st.markdown(
            f'<div class="status-card"><span class="status-dot {tone}"></span>'
            f"<strong>{escape_html(name)}</strong><br>"
            f"<small>{escape_html(label)} · 目前 probe</small></div>",
            unsafe_allow_html=True,
        )


def render_overview(
    snapshot: TelemetrySnapshot,
    source_kind: str,
    status: GatewayStatus,
    registry: Registry,
    observation_window_minutes: int | None = None,
) -> None:
    model = build_overview_model(snapshot, source_kind, observation_window_minutes)
    render_page_heading(
        "GATEWAY OVERVIEW",
        "推論閘道運行概覽",
        "彙整 Request throughput、latency、routing、Failover 與 Backend Health，呈現所選觀測時間範圍內可追溯的運行狀態。",
    )
    source_note = _time_note(model)
    if source_kind == "demo":
        source_note += " · 示範 fixture，非正式流量"
    render_source_badge(source_kind, source_note)

    metrics = model.metrics
    cards = [
        (
            "REQUEST 數量",
            f"{metrics.request_count:,}",
            (
                "所選時間範圍"
                if metrics.request_rate_per_min is None
                else f"{metrics.request_rate_per_min:,.1f} req/min"
            ),
        ),
        (
            "成功率",
            format_metric(metrics.success_rate_pct, "%", digits=1),
            f"{int(round(metrics.request_count * (metrics.success_rate_pct or 0) / 100)):,} 筆成功",
        ),
        ("P50 LATENCY", format_metric(metrics.p50_latency_ms, " ms", digits=0), "端到端 latency"),
        ("P95 LATENCY", format_metric(metrics.p95_latency_ms, " ms", digits=0), "端到端 latency"),
        (
            "FAILOVER 次數",
            f"{metrics.failover_count:,}",
            (
                "—"
                if metrics.failover_rate_pct is None
                else f"占 Request 的 {metrics.failover_rate_pct:,.2f}%"
            ),
        ),
    ]
    render_metric_grid(cards)

    st.markdown("### Request 數量與 P95 latency")
    if model.series.empty:
        render_state_message("尚無趨勢資料", "第一筆 Request 寫入後，這裡會顯示時間序列。")
    else:
        st.markdown(activity_measure_key_html(), unsafe_allow_html=True)
        st.altair_chart(build_activity_chart(model.series), width="stretch")
        st.caption("Request 數量與 latency 使用獨立 Y 軸，以保留真實量級；hover 可讀取精確值。")

    health_col, route_col, failover_col = st.columns([1, 1, 1.2], gap="medium")
    with health_col:
        _render_health(status)
    with route_col:
        st.markdown("### Alias Routing")
        for alias, config in registry.items():
            chain = " → ".join(backend.name for backend in config.backends)
            cap = "無上限" if config.max_concurrent is None else f"上限 {config.max_concurrent}"
            st.markdown(f"**{alias}**　`{chain}`　 · {cap}")
    with failover_col:
        st.markdown("### 近期 Failover")
        if snapshot.failovers.empty:
            st.caption("目前觀測時間範圍沒有 Failover event。")
        else:
            recent = snapshot.failovers.head(4).copy()
            recent["route"] = (
                recent["failed_backend"].fillna("—") + " → " + recent["next_backend"].fillna("無")
            )
            st.dataframe(
                recent[["timestamp", "alias", "route", "reason"]],
                hide_index=True,
                width="stretch",
                height=180,
            )
