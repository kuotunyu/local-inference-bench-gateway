from pathlib import Path

import pandas as pd

from dashboard.data.demo_fixture import ensure_demo_database, select_default_mode
from dashboard.data.sqlite_repository import load_snapshot


def test_demo_fixture_is_deterministic(tmp_path: Path) -> None:
    demo = ensure_demo_database(tmp_path / "demo")
    first = load_snapshot(demo)
    demo.unlink()
    second = load_snapshot(ensure_demo_database(tmp_path / "demo"))
    pd.testing.assert_frame_equal(first.requests, second.requests)
    assert len(first.requests) >= 48
    assert {"connection_error", "HTTP 503", "HTTP 429"} <= set(
        first.requests["error_message"].dropna()
    )


def test_default_mode_prefers_only_compatible_live_database(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    assert select_default_mode(missing) == "demo"
    demo = ensure_demo_database(tmp_path / "fixture")
    assert select_default_mode(demo) == "live"
