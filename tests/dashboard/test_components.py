import pytest

from dashboard import components
from dashboard.components import (
    brand_block_html,
    metric_grid_html,
    page_heading_html,
)


def test_brand_block_fills_the_header_with_product_context() -> None:
    markup = brand_block_html()

    assert 'class="brand-block"' in markup
    assert 'class="brand-title"' in markup
    assert 'class="brand-subtitle"' in markup
    assert "Operations Console" in markup
    assert "本機推論 Gateway" in markup


def test_page_heading_uses_a_two_column_scientific_structure() -> None:
    markup = page_heading_html("GATEWAY OVERVIEW", "推論閘道運行概覽", "Operational evidence")

    assert "GATEWAY OVERVIEW" not in markup
    assert "ops-kicker" not in markup
    assert 'class="ops-heading"' in markup
    assert 'class="ops-title"' in markup
    assert 'class="ops-lede"' in markup
    assert "推論閘道運行概覽" in markup


def test_metric_grid_is_compact_and_escapes_values() -> None:
    markup = metric_grid_html([("REQUEST 數量", "<60>", "所選時間範圍")])

    assert 'class="metric-grid metric-count-1"' in markup
    assert "&lt;60&gt;" in markup
    assert "<60>" not in markup
    assert 'class="metric-label"' in markup
    assert "REQUEST 數量" in markup
    assert "所選時間範圍" in markup
    assert 'class="metric-detail"' in markup
    assert 'class="metric-value"' in markup


def test_metric_grid_exposes_cardinality_for_stable_responsive_layout() -> None:
    markup = metric_grid_html([(f"METRIC {index}", str(index), "detail") for index in range(7)])

    assert 'class="metric-grid metric-count-7"' in markup
    assert markup.count('class="metric-card"') == 7


def test_chart_measure_key_maps_marks_and_escapes_labels() -> None:
    assert hasattr(components, "chart_measure_key_html")
    markup = components.chart_measure_key_html(
        [("bar", "request", "Request <count>"), ("line", "latency", "P95 / ms")]
    )

    assert 'class="chart-measure-key chart-key-count-2"' in markup
    assert 'class="chart-key-item request"' in markup
    assert 'class="chart-key-item latency"' in markup
    assert 'class="chart-key-bar" aria-hidden="true"' in markup
    assert 'class="chart-key-line" aria-hidden="true"' in markup
    assert "Request &lt;count&gt;" in markup
    assert "Request <count>" not in markup


def test_chart_measure_key_rejects_unknown_mark_or_tone() -> None:
    assert hasattr(components, "chart_measure_key_html")
    with pytest.raises(ValueError, match="unsupported chart mark"):
        components.chart_measure_key_html([("area", "neutral", "Throughput")])
    with pytest.raises(ValueError, match="unsupported chart tone"):
        components.chart_measure_key_html([("line", "danger", "Throughput")])
