from pathlib import Path

from dashboard.components import escape_html, format_metric
from dashboard.theme import build_theme_css


def test_theme_contains_accessible_type_and_semantic_tokens() -> None:
    css = build_theme_css()
    assert "--canvas: #F1EFE8" in css
    assert "--healthy: #718B7A" in css
    assert "html { font-size: 18px; }" in css
    assert "font-size: 16px" in css
    assert (
        'p, label, [data-testid="stMarkdownContainer"] { font-size:16px; line-height:1.5; }' in css
    )
    assert "prefers-reduced-motion" in css
    assert "font-size:.72rem" not in css
    assert "font-size:.78rem" not in css
    assert "font-size:.8rem" not in css
    assert "font-size:17px" in css
    assert ".ops-heading" in css
    assert "grid-template-columns:minmax(0,38fr) minmax(0,62fr)" in css
    assert "grid-template-areas:" in css
    assert "min-height:88px" in css
    assert "2.05rem" in css
    assert "2.65rem" not in css
    assert "3.55rem" not in css


def test_theme_uses_flat_instrument_surfaces() -> None:
    css = build_theme_css()
    assert ".metric-grid" in css
    assert "grid-template-columns:repeat(var(--metric-columns),minmax(0,1fr))" in css
    assert ".metric-count-7 { --metric-columns:7; }" in css
    assert ".metric-count-7 .metric-card:nth-child(5)" in css
    assert ".metric-count-7 .metric-card:nth-child(n+5)" in css
    assert "border-top:1px solid var(--border)" in css
    assert "border-bottom:1px solid var(--border)" in css
    assert ".metric-card" in css
    assert "border-radius:0" in css
    assert "box-shadow:none" in css
    assert ".status-card" in css
    assert "background:transparent" in css
    assert 'div[role="radiogroup"]' in css
    assert "border:0" in css
    assert '[data-testid="stDataFrame"]' in css
    assert "border-radius:4px" in css
    assert '[data-testid="stExpander"]' in css
    assert ".stButton button" in css
    assert "border-radius:6px" in css
    assert ".activity-measure-key" in css
    assert ".activity-key-bar" in css
    assert ".activity-key-line" in css
    assert "grid-template-columns:minmax(0,1fr) minmax(0,1fr)" in css


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
