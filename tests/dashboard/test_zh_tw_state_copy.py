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


def test_reliability_states_use_zh_tw_led_copy(monkeypatch) -> None:
    monkeypatch.setenv("DASHBOARD_TEST_STATE", "reliability_degraded")
    app = AppTest.from_file(str(STATE_APP_PATH)).run(timeout=20)

    visible = _visible_markdown(app)
    assert not app.exception
    assert "Routing 原則" in visible
    assert "Backend Health 詳細資訊無法取得" in visible
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

    assert not app.exception
    assert "證據驗證警告" in _visible_markdown(app)
