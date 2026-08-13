from datetime import timedelta
from pathlib import Path

import pandas as pd

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.live_status import GatewayStatus
from dashboard.data.sqlite_repository import load_snapshot
from dashboard.views.overview import (
    _activity_time_guide,
    build_activity_chart,
    build_overview_model,
)
from dashboard.views.overview import _time_note as overview_time_note
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
    bar, line = spec["layer"]
    assert bar["mark"]["size"] == {"expr": "min(54, width / 9 * 0.82)"}
    assert bar["mark"]["color"] == "#5F7F6B"
    assert bar["mark"]["opacity"] == 0.9
    assert line["mark"]["strokeWidth"] == 5
    assert line["mark"]["color"] == "#B56F45"
    assert line["mark"]["point"]["size"] == 120
    assert line["mark"]["point"]["strokeWidth"] == 2
    assert bar["encoding"]["x"]["scale"] == line["encoding"]["x"]["scale"]
    assert bar["encoding"]["x"]["axis"]["tickSize"] == 6
    assert bar["encoding"]["x"]["axis"]["labelOverlap"] == "greedy"
    assert bar["encoding"]["y"]["title"] == "每 bucket Request 數"
    assert bar["encoding"]["tooltip"][1]["title"] == "Request 數"
    assert line["encoding"]["y"]["title"] == "P95 latency / ms"


def test_activity_time_guide_pads_half_a_bucket_and_uses_ten_minute_ticks() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-13T00:40:00Z", periods=7, freq="10min"),
            "requests": [5, 10, 10, 10, 10, 10, 5],
            "p95_latency_ms": [180, 280, 380, 460, 560, 650, 700],
        }
    )

    guide = _activity_time_guide(frame)

    assert guide.domain[0] == frame["timestamp"].iloc[0].to_pydatetime() - timedelta(minutes=5)
    assert guide.domain[1] == frame["timestamp"].iloc[-1].to_pydatetime() + timedelta(minutes=5)
    assert guide.ticks == tuple(frame["timestamp"].dt.to_pydatetime())


def test_activity_time_guide_uses_one_hour_ticks_for_six_hours() -> None:
    frame = pd.DataFrame(
        {"timestamp": pd.date_range("2026-08-13T00:10:00Z", periods=37, freq="10min")}
    )

    guide = _activity_time_guide(frame)

    assert [tick.minute for tick in guide.ticks] == [0] * 6
    assert [tick.hour for tick in guide.ticks] == [1, 2, 3, 4, 5, 6]


def test_activity_bar_width_scales_with_six_hour_bucket_density() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-13T00:00:00Z", periods=37, freq="10min"),
            "requests": [10] * 37,
            "p95_latency_ms": [500] * 37,
        }
    )

    spec = build_activity_chart(frame).to_dict()

    assert spec["layer"][0]["mark"]["size"] == {"expr": "min(54, width / 39 * 0.82)"}


def test_activity_bar_width_scales_with_twenty_four_hour_bucket_density() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-13T00:00:00Z", periods=145, freq="10min"),
            "requests": [10] * 145,
            "p95_latency_ms": [500] * 145,
        }
    )

    spec = build_activity_chart(frame).to_dict()

    assert spec["layer"][0]["mark"]["size"] == {"expr": "min(54, width / 147 * 0.82)"}


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
    assert spec["encoding"]["x"]["title"] == "觀測到的 failure"
    assert spec["encoding"]["tooltip"][0]["title"] == "分類"
    assert spec["encoding"]["tooltip"][1]["title"] == "數量"
    assert spec["config"]["axis"]["labelFontSize"] >= 14


def model_time():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
