from dashboard.components import format_metric
from dashboard.theme import build_theme_css


def test_theme_contains_accessible_type_and_semantic_tokens() -> None:
    css = build_theme_css()
    assert "--canvas: #F1EFE8" in css
    assert "--healthy: #718B7A" in css
    assert "font-size: 16px" in css
    assert "prefers-reduced-motion" in css


def test_metric_formatter_never_turns_missing_into_zero() -> None:
    assert format_metric(None, " ms") == "—"
    assert format_metric(float("nan"), " ms") == "—"
    assert format_metric(184.25, " ms", digits=0) == "184 ms"
