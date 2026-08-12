"""Reusable Streamlit presentation components."""

from __future__ import annotations

import html
import math

import streamlit as st


def format_metric(value: float | int | None, suffix: str = "", *, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value:,.{digits}f}{suffix}"


def render_source_badge(kind: str, note: str) -> None:
    label = {"demo": "DEMO DATA", "live": "LIVE", "evidence": "EVIDENCE"}.get(kind, kind.upper())
    st.markdown(
        f'<div class="source-line"><span class="source-badge {html.escape(kind)}">'
        f'● {html.escape(label)}</span><span class="source-note">{html.escape(note)}</span></div>',
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, detail: str) -> None:
    st.markdown(
        '<div class="metric-card">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-detail">{html.escape(detail)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_state_message(title: str, copy: str, tone: str = "neutral") -> None:
    tone_class = "" if tone == "neutral" else f" {html.escape(tone)}"
    st.markdown(
        f'<div class="callout{tone_class}"><div class="callout-title">{html.escape(title)}</div>'
        f'<div class="callout-copy">{html.escape(copy)}</div></div>',
        unsafe_allow_html=True,
    )


def render_page_heading(kicker: str, title: str, lede: str) -> None:
    st.markdown(
        f'<div class="ops-kicker">{html.escape(kicker)}</div>'
        f'<div class="ops-title">{html.escape(title)}</div>'
        f'<div class="ops-lede">{html.escape(lede)}</div><div class="ops-rule"></div>',
        unsafe_allow_html=True,
    )
