from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

STATE_APP_PATH = Path(__file__).parent / "apps/zh_tw_states_app.py"


def _visible_markdown(app: AppTest) -> str:
    return "".join(item.value for item in [*app.markdown, *app.caption])


def test_empty_overview_keeps_request_as_an_original_engineering_term(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "overview_empty")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    assert not app.exception
    assert "第一筆 Request 寫入後" in _visible_markdown(app)


def test_overview_public_demo_uses_fixture_heading(monkeypatch) -> None:
    """Fails if public fixture rendering is mistaken for a current local probe."""
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "overview_public_demo")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    visible = _visible_markdown(app)
    assert not app.exception
    assert "Fixture backend state" in visible
    assert "目前觀測" not in visible


def test_overview_local_runtime_preserves_observed_heading(monkeypatch) -> None:
    """Fails if the local runtime loses its current-observation health disclosure."""
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "overview_empty")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    assert not app.exception
    assert "Backend Health · 目前觀測" in _visible_markdown(app)


def test_reliability_states_use_zh_tw_led_copy(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "reliability_degraded")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    visible = _visible_markdown(app)
    assert not app.exception
    assert "Routing 原則" in visible
    assert "Backend Health 詳細資訊無法取得" in visible
    assert "Gateway 可連線，但 Backend detail 未授權或尚未回報。" in visible
    assert "沒有 Failover event" in visible


def test_empty_request_filter_result_preserves_request_capitalization(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "requests_filterable")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)
    app.selectbox[0].set_value("Failure").run(timeout=20)

    assert not app.exception
    assert "沒有符合條件的 Request" in _visible_markdown(app)


def test_missing_evidence_uses_zh_tw_warning_heading(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "evidence_missing")
    monkeypatch.setenv("DASHBOARD_TEST_RESULTS_DIR", str(tmp_path))
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    visible = _visible_markdown(app)
    assert not app.exception
    assert "證據驗證警告" in visible
    assert all(
        label not in visible
        for label in (
            "Throughput／tok/s",
            "TTFT／ms",
            "Median TTFT／s",
            "Latency／ms",
            "VRAM baseline／MiB",
            "P50 TTFT／ms",
        )
    )


def test_partial_evidence_renders_only_labels_for_available_charts(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "evidence_partial")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    visible = _visible_markdown(app)
    assert not app.exception
    assert "Throughput／tok/s" in visible
    assert "TTFT／ms" in visible
    assert "Latency／ms" in visible
    assert "VRAM baseline／MiB" in visible
    assert "P50 TTFT／ms" in visible
    assert "Median TTFT／s" not in visible
