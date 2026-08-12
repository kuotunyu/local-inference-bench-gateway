from pathlib import Path

from dashboard.state import load_telemetry_state, slice_observation_window
from gateway.db import init_db


def test_missing_live_database_falls_back_without_creating_it(tmp_path: Path) -> None:
    live = tmp_path / "live.db"
    state = load_telemetry_state("live", live, tmp_path / "demo")
    assert state.source_kind == "demo"
    assert state.notice is not None
    assert "uv run uvicorn gateway.app:app --host 127.0.0.1 --port 9000" in state.notice
    assert "GATEWAY_DB_PATH" in state.notice
    assert not live.exists()


def test_demo_window_anchors_to_fixture_not_wall_clock(tmp_path: Path) -> None:
    state = load_telemetry_state("demo", tmp_path / "live.db", tmp_path / "demo")
    sliced = slice_observation_window(state.snapshot, 15, "demo")
    assert 1 <= len(sliced.requests) <= 16


def test_empty_compatible_live_database_remains_live(tmp_path: Path) -> None:
    live = tmp_path / "gateway.db"
    init_db(live)

    state = load_telemetry_state("live", live, tmp_path / "demo")

    assert state.source_kind == "live"
    assert state.notice is None
    assert state.snapshot.requests.empty


def test_incompatible_live_database_falls_back_without_mutation(tmp_path: Path) -> None:
    live = tmp_path / "incompatible.db"
    live.write_bytes(b"")
    original = live.read_bytes()

    state = load_telemetry_state("live", live, tmp_path / "demo")

    assert state.source_kind == "demo"
    assert "schema version 0" in (state.notice or "")
    assert live.read_bytes() == original


def test_importing_app_does_not_create_runtime_database(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "should-not-exist.db"
    monkeypatch.setenv("GATEWAY_DB_PATH", str(target))
    import dashboard.app  # noqa: F401

    assert not target.exists()
