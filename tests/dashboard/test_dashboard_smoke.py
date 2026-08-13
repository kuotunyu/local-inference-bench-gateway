from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "dashboard/app.py"


@pytest.mark.parametrize(
    "page", ["Overview", "Routing & Reliability", "Requests", "Benchmark Evidence"]
)
def test_every_console_view_renders_without_exception(
    page: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "missing-live.db"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)

    assert not app.exception
    assert not (tmp_path / "missing-live.db").exists()


def test_unavailable_live_mode_degrades_to_demo(tmp_path: Path, monkeypatch) -> None:
    live = tmp_path / "missing-live.db"
    monkeypatch.setenv("GATEWAY_DB_PATH", str(live))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.selectbox(key="telemetry_source").set_value("Live Mode").run(timeout=20)

    assert not app.exception
    assert not live.exists()
    assert any("安全切換 Demo Mode" in item.value for item in app.markdown)


def test_missing_registry_does_not_block_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_MODELS_PATH", str(tmp_path / "missing-models.yaml"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value("Benchmark Evidence").run(timeout=20)

    assert not app.exception
    assert any("Benchmark 測量證據" in item.value for item in app.markdown)


def test_header_renders_product_and_technical_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "missing-live.db"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    markup = "".join(item.value for item in app.markdown)
    assert "Operations Console" in markup
    assert "Local inference gateway" in markup


@pytest.mark.parametrize(
    ("page", "title"),
    [
        ("Overview", "推論閘道運行概覽"),
        ("Routing & Reliability", "路由與可靠性分析"),
        ("Requests", "請求遙測檢視"),
        ("Benchmark Evidence", "Benchmark 測量證據"),
    ],
)
def test_console_views_render_neutral_scientific_titles(
    page: str, title: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "missing-live.db"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)

    assert not app.exception
    assert any(title in item.value for item in app.markdown)
