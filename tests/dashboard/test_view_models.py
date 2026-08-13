from pathlib import Path

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.live_status import GatewayStatus
from dashboard.data.sqlite_repository import load_snapshot
from dashboard.views.overview import _time_note as overview_time_note
from dashboard.views.overview import build_activity_chart, build_overview_model
from dashboard.views.reliability import build_error_chart, build_reliability_model
from gateway.registry import load_registry


def test_overview_model_discloses_demo_source_and_time_range(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    model = build_overview_model(snapshot, source_kind="demo")
    assert model.source_label == "DEMO DATA"
    assert model.observed_from is not None
    assert model.observed_to is not None
    assert overview_time_note(model).endswith("UTC+8")


def test_overview_activity_chart_uses_full_operational_canvas(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    model = build_overview_model(snapshot, source_kind="demo")

    spec = build_activity_chart(model.series).to_dict()

    assert spec["height"] == 400
    assert len(spec["layer"]) == 2
    assert spec["resolve"]["scale"]["y"] == "independent"


def test_health_is_current_observation_not_uptime(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    status = GatewayStatus(False, model_time(), {}, "offline")
    model = build_reliability_model(snapshot, status, load_registry())
    assert model.health_heading == "Backend Health · 目前觀測"
    assert not hasattr(model, "uptime_pct")


def test_error_chart_is_horizontal_and_readable(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    model = build_reliability_model(
        snapshot, GatewayStatus(False, model_time(), {}, "offline"), load_registry()
    )

    spec = build_error_chart(model.errors).to_dict()

    assert spec["height"] == 360
    assert spec["encoding"]["y"]["field"] == "error_category"
    assert spec["config"]["axis"]["labelFontSize"] >= 14


def model_time():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
