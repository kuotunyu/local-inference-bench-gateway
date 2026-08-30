from pathlib import Path

import pandas as pd

from dashboard.data.demo_fixture import ensure_demo_database
from dashboard.data.public_demo import build_demo_snapshot, demo_snapshot_digest
from dashboard.data.sqlite_repository import load_snapshot

EXPECTED_DIGEST = "44d6bb22d7bdfc59035ff8b4693ab7af73cba0568abdc7e31981ab264e4d2d16"


def test_public_demo_snapshot_is_exact_stable_and_in_memory(tmp_path: Path, monkeypatch) -> None:
    """Fails if the public demo fixture changes, writes a database, or loses determinism."""
    monkeypatch.chdir(tmp_path)
    first = build_demo_snapshot()
    second = build_demo_snapshot()

    pd.testing.assert_frame_equal(first.requests, second.requests)
    pd.testing.assert_frame_equal(first.failovers, second.failovers)
    assert len(first.requests) == 60
    assert len(first.failovers) == 3
    assert set(first.requests["alias"]) == {"fast", "smart"}
    assert set(first.requests["backend_name"].dropna()) == {
        "llamacpp",
        "ollama",
        "ollama-smart",
    }
    assert first.requests.sort_values("id").iloc[0]["timestamp"] == "2026-08-12T16:45:00+00:00"
    assert demo_snapshot_digest(first) == EXPECTED_DIGEST
    assert list(tmp_path.rglob("*.db")) == []
    assert list(tmp_path.rglob("*.sqlite*")) == []


def test_public_demo_matches_the_existing_local_fixture_contract(tmp_path: Path) -> None:
    """Fails if either fixture's complete request or failover contract diverges."""
    public = build_demo_snapshot()
    local = load_snapshot(ensure_demo_database(tmp_path))

    pd.testing.assert_frame_equal(
        public.requests.sort_values("id").reset_index(drop=True),
        local.requests.sort_values("id").reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(
        public.failovers.sort_values("id").reset_index(drop=True),
        local.failovers.sort_values("id").reset_index(drop=True),
    )
    assert public.source_path == Path("deterministic-demo")
