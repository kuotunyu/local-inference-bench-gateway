from dashboard.components import brand_block_html, metric_grid_html, page_heading_html


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
