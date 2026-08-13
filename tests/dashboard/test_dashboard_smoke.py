from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "dashboard/app.py"


@pytest.mark.parametrize("page", ["系統總覽", "Routing 與可靠性", "Request 紀錄", "Benchmark 證據"])
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
    app.selectbox(key="telemetry_source").set_value("Live 模式").run(timeout=20)

    assert not app.exception
    assert not live.exists()
    assert any("安全切換至 Demo 模式" in item.value for item in app.markdown)


def test_missing_registry_does_not_block_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_MODELS_PATH", str(tmp_path / "missing-models.yaml"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value("Benchmark 證據").run(timeout=20)

    assert not app.exception
    assert any("Benchmark 測量證據" in item.value for item in app.markdown)


def test_header_renders_product_and_technical_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "missing-live.db"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    markup = "".join(item.value for item in app.markdown)
    assert "Operations Console" in markup
    assert "本機推論 Gateway" in markup
    assert app.selectbox(key="telemetry_source").label == "Telemetry 資料源"
    assert app.selectbox(key="observation_window").label == "觀測時間範圍"


@pytest.mark.parametrize(
    ("page", "title"),
    [
        ("系統總覽", "推論閘道運行概覽"),
        ("Routing 與可靠性", "路由與可靠性分析"),
        ("Request 紀錄", "請求遙測檢視"),
        ("Benchmark 證據", "Benchmark 測量證據"),
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


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ("系統總覽", ["REQUEST 數量", "成功率", "FAILOVER 次數", "近期 Failover"]),
        (
            "Routing 與可靠性",
            ["Error 分類", "觀測到的 HTTP 429", "Failover event"],
        ),
        ("Request 紀錄", ["篩選後 REQUEST", "成功率", "TOKEN 數量"]),
    ],
)
def test_operational_views_use_zh_tw_first_copy(
    page: str, expected: list[str], tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "missing-live.db"))
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)

    visible = "".join(item.value for item in app.markdown)
    visible += "".join(item.label for item in app.metric)
    assert not app.exception
    assert all(fragment in visible for fragment in expected)
