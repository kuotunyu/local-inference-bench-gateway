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
    assert any("快，不夠。還要知道為什麼可信。" in item.value for item in app.markdown)
