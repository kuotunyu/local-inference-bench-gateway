"""Reusable Streamlit presentation components."""

from __future__ import annotations

import html
import math

import streamlit as st


def escape_html(value: object) -> str:
    """Escape operator- or upstream-controlled values before HTML rendering."""
    return html.escape(str(value), quote=True)


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


def render_state_message(title: str, copy: str, tone: str = "neutral") -> None:
    tone_class = "" if tone == "neutral" else f" {escape_html(tone)}"
    st.markdown(
        f'<div class="callout{tone_class}"><div class="callout-title">{escape_html(title)}</div>'
        f'<div class="callout-copy">{escape_html(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def render_page_heading(kicker: str, title: str, lede: str) -> None:
    st.markdown(
        f'<div class="ops-kicker">{escape_html(kicker)}</div>'
        f'<div class="ops-title">{escape_html(title)}</div>'
        f'<div class="ops-lede">{escape_html(lede)}</div><div class="ops-rule"></div>',
        unsafe_allow_html=True,
    )
