from __future__ import annotations

import pandas as pd

from dashboard.charts import chart_theme, line_chart


def test_chart_theme_has_readable_axes_and_legend() -> None:
    config = chart_theme()

    assert config["axis"]["labelFontSize"] >= 14
    assert config["axis"]["titleFontSize"] >= 15
    assert config["legend"]["labelFontSize"] >= 14
    assert config["legend"]["titleFontSize"] >= 14


def test_line_chart_uses_visible_marks_and_requested_height() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-08-13T00:00:00Z", "2026-08-13T00:10:00Z"]),
            "value": [12, 18],
            "series": ["Requests", "Requests"],
        }
    )

    spec = line_chart(
        frame,
        x="timestamp:T",
        y="value:Q",
        color="series:N",
        height=400,
        y_title="Requests",
    ).to_dict()

    assert spec["height"] == 400
    assert spec["mark"]["strokeWidth"] >= 2.5
    assert spec["mark"]["point"]["size"] >= 60
    assert spec["config"]["axis"]["labelFontSize"] >= 14
