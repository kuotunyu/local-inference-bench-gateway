"""Readable Altair charts for the Operations Console."""

from __future__ import annotations

from collections.abc import Sequence

import altair as alt
import pandas as pd

CHART_COLORS = ["#718B7A", "#78909A", "#B1815F", "#A45F5F", "#9A8E78", "#667C70"]


def chart_theme() -> dict:
    """Return the shared chart presentation tokens."""
    return {
        "axis": {
            "domainColor": "#C7C4BA",
            "domainWidth": 1,
            "gridColor": "#E2DFD6",
            "gridOpacity": 0.78,
            "labelColor": "#56615B",
            "labelFont": "Noto Sans TC, Microsoft JhengHei, sans-serif",
            "labelFontSize": 14,
            "labelPadding": 8,
            "tickColor": "#C7C4BA",
            "titleColor": "#34413A",
            "titleFont": "Noto Sans TC, Microsoft JhengHei, sans-serif",
            "titleFontSize": 15,
            "titleFontWeight": 600,
            "titlePadding": 12,
        },
        "legend": {
            "labelColor": "#4F5C55",
            "labelFont": "Noto Sans TC, Microsoft JhengHei, sans-serif",
            "labelFontSize": 14,
            "labelLimit": 240,
            "symbolSize": 130,
            "titleColor": "#34413A",
            "titleFont": "Noto Sans TC, Microsoft JhengHei, sans-serif",
            "titleFontSize": 14,
            "titleFontWeight": 700,
        },
        "view": {"stroke": None},
    }


def style_chart(chart: alt.Chart) -> alt.Chart:
    """Apply the shared accessible presentation configuration."""
    config = chart_theme()
    return (
        chart.configure_axis(**config["axis"])
        .configure_legend(**config["legend"])
        .configure_view(**config["view"])
    )


def _tooltip(fields: Sequence[str] | None) -> list[alt.Tooltip] | None:
    return None if fields is None else [alt.Tooltip(field) for field in fields]


def line_chart(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None = None,
    height: int = 400,
    y_title: str | None = None,
    x_title: str | None = None,
    tooltip: Sequence[str] | None = None,
    color_range: Sequence[str] | None = None,
    zero: bool = False,
) -> alt.Chart:
    """Build a legible multi-series line chart with visible data points."""
    encodings: dict[str, object] = {
        "x": alt.X(x, title=x_title),
        "y": alt.Y(y, title=y_title, scale=alt.Scale(zero=zero)),
    }
    if color is not None:
        encodings["color"] = alt.Color(
            color,
            scale=alt.Scale(range=list(color_range or CHART_COLORS)),
            legend=alt.Legend(orient="bottom", direction="horizontal", columns=3),
        )
    tooltip_encoding = _tooltip(tooltip)
    if tooltip_encoding is not None:
        encodings["tooltip"] = tooltip_encoding
    chart = (
        alt.Chart(data)
        .mark_line(
            strokeWidth=2.75,
            point=alt.OverlayMarkDef(size=68, filled=True, strokeWidth=1.5),
        )
        .encode(**encodings)
        .properties(height=height)
        .interactive(bind_y=False)
    )
    return style_chart(chart)


def bar_chart(
    data: pd.DataFrame,
    *,
    x: str,
    y: str,
    color: str | None = None,
    height: int = 360,
    x_title: str | None = None,
    y_title: str | None = None,
    tooltip: Sequence[str] | None = None,
    color_range: Sequence[str] | None = None,
) -> alt.Chart:
    """Build a legible bar chart for vertical or horizontal categorical data."""
    encodings: dict[str, object] = {
        "x": alt.X(x, title=x_title),
        "y": alt.Y(y, title=y_title),
    }
    if color is not None:
        encodings["color"] = alt.Color(
            color,
            scale=alt.Scale(range=list(color_range or CHART_COLORS)),
            legend=alt.Legend(orient="bottom", direction="horizontal", columns=3),
        )
    tooltip_encoding = _tooltip(tooltip)
    if tooltip_encoding is not None:
        encodings["tooltip"] = tooltip_encoding
    chart = (
        alt.Chart(data).mark_bar(cornerRadiusEnd=5).encode(**encodings).properties(height=height)
    )
    return style_chart(chart)
