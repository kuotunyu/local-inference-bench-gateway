from pathlib import Path

from dashboard.components import escape_html, format_metric
from dashboard.theme import build_theme_css


def test_theme_contains_accessible_type_and_semantic_tokens() -> None:
    css = build_theme_css()
    assert "--canvas: #F1EFE8" in css
    assert "--healthy: #718B7A" in css
    assert "font-size: 16px" in css
    assert "prefers-reduced-motion" in css
    assert "font-size:.72rem" not in css
    assert "font-size:.78rem" not in css
    assert "font-size:.8rem" not in css
    assert "font-size: 17px" in css
    assert "2.65rem" in css
    assert "3.55rem" not in css


def test_metric_formatter_never_turns_missing_into_zero() -> None:
    assert format_metric(None, " ms") == "—"
    assert format_metric(float("nan"), " ms") == "—"
    assert format_metric(184.25, " ms", digits=0) == "184 ms"


def test_operator_controlled_text_is_safe_for_html_cards() -> None:
    assert escape_html('<img src=x onerror="alert(1)">') == (
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    )


def test_streamlit_defaults_to_loopback() -> None:
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")
    assert 'address = "127.0.0.1"' in config
