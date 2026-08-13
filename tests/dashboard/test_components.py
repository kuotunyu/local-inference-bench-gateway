from dashboard.components import brand_block_html, metric_grid_html, page_heading_html


def test_brand_block_fills_the_header_with_product_context() -> None:
    markup = brand_block_html()

    assert 'class="brand-block"' in markup
    assert 'class="brand-title"' in markup
    assert 'class="brand-subtitle"' in markup
    assert "Operations Console" in markup
    assert "Local inference gateway" in markup


def test_page_heading_uses_a_two_column_scientific_structure() -> None:
    markup = page_heading_html("GATEWAY OVERVIEW", "推論閘道運行概覽", "Operational evidence")

    assert "GATEWAY OVERVIEW" not in markup
    assert "ops-kicker" not in markup
    assert 'class="ops-heading"' in markup
    assert 'class="ops-title"' in markup
    assert 'class="ops-lede"' in markup
    assert "推論閘道運行概覽" in markup


def test_metric_grid_is_compact_and_escapes_values() -> None:
    markup = metric_grid_html([("REQUESTS", "<60>", "selected window")])

    assert 'class="metric-grid"' in markup
    assert "&lt;60&gt;" in markup
    assert "<60>" not in markup
    assert 'class="metric-label"' in markup
    assert 'class="metric-detail"' in markup
    assert 'class="metric-value"' in markup
