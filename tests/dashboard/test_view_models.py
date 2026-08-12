from pathlib import Path

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.live_status import GatewayStatus
from dashboard.data.sqlite_repository import load_snapshot
from dashboard.views.overview import build_overview_model
from dashboard.views.reliability import build_reliability_model
from gateway.registry import load_registry


def test_overview_model_discloses_demo_source_and_time_range(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    model = build_overview_model(snapshot, source_kind="demo")
    assert model.source_label == "DEMO DATA"
    assert model.observed_from is not None
    assert model.observed_to is not None


def test_health_is_current_observation_not_uptime(tmp_path: Path) -> None:
    snapshot = load_snapshot(ensure_demo_database(tmp_path))
    status = GatewayStatus(False, model_time(), {}, "offline")
    model = build_reliability_model(snapshot, status, load_registry())
    assert model.health_heading == "Backend Health · 目前觀測"
    assert not hasattr(model, "uptime_pct")


def model_time():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
