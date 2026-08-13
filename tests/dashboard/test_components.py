from dashboard.components import metric_grid_html, page_heading_html


def test_page_heading_removes_redundant_kicker_hierarchy() -> None:
    markup = page_heading_html("GATEWAY OVERVIEW", "推論系統，一眼掌握。", "Operational evidence")

    assert "GATEWAY OVERVIEW" not in markup
    assert "ops-kicker" not in markup
    assert "推論系統，一眼掌握。" in markup


def test_metric_grid_is_compact_and_escapes_values() -> None:
    markup = metric_grid_html([("REQUESTS", "<60>", "selected window")])

    assert 'class="metric-grid"' in markup
    assert "&lt;60&gt;" in markup
    assert "<60>" not in markup
