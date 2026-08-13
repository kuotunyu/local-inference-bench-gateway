"""Reusable Streamlit presentation components."""

from __future__ import annotations

import html
import math

import streamlit as st

MetricCard = tuple[str, str, str]


def escape_html(value: object) -> str:
    """Escape operator- or upstream-controlled values before HTML rendering."""
    return html.escape(str(value), quote=True)


def brand_block_html() -> str:
    """Return the compact two-line identity used beside dashboard controls."""
    return (
        '<div class="brand-block">'
        '<div class="brand-title">Operations Console</div>'
        '<div class="brand-subtitle">本機推論 Gateway</div>'
        "</div>"
    )


def format_metric(value: float | int | None, suffix: str = "", *, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:,.{digits}f}{suffix}"


def render_source_badge(kind: str, note: str) -> None:
    label = {"demo": "DEMO DATA", "live": "LIVE", "evidence": "EVIDENCE"}.get(kind, kind.upper())
    st.markdown(
        f'<div class="source-line"><span class="source-badge {escape_html(kind)}">'
        f'● {escape_html(label)}</span><span class="source-note">{escape_html(note)}</span></div>',
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, detail: str) -> None:
    st.markdown(
        '<div class="metric-card">'
        f'<div class="metric-label">{escape_html(label)}</div>'
        f'<div class="metric-value">{escape_html(value)}</div>'
        f'<div class="metric-detail">{escape_html(detail)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def metric_grid_html(cards: list[MetricCard]) -> str:
    items = "".join(
        '<div class="metric-card">'
        f'<div class="metric-label">{escape_html(label)}</div>'
        f'<div class="metric-value">{escape_html(value)}</div>'
        f'<div class="metric-detail">{escape_html(detail)}</div>'
        "</div>"
        for label, value, detail in cards
    )
    return f'<div class="metric-grid metric-count-{len(cards)}">{items}</div>'


def render_metric_grid(cards: list[MetricCard]) -> None:
    st.markdown(metric_grid_html(cards), unsafe_allow_html=True)


def render_state_message(title: str, copy: str, tone: str = "neutral") -> None:
    tone_class = "" if tone == "neutral" else f" {escape_html(tone)}"
    st.markdown(
        f'<div class="callout{tone_class}"><div class="callout-title">{escape_html(title)}</div>'
        f'<div class="callout-copy">{escape_html(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def page_heading_html(kicker: str, title: str, lede: str) -> str:
    del kicker
    return (
        '<div class="ops-heading">'
        f'<div class="ops-title">{escape_html(title)}</div>'
        f'<div class="ops-lede">{escape_html(lede)}</div>'
        '</div><div class="ops-rule"></div>'
    )


def render_page_heading(kicker: str, title: str, lede: str) -> None:
    st.markdown(page_heading_html(kicker, title, lede), unsafe_allow_html=True)
