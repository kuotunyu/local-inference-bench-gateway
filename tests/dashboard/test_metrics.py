from __future__ import annotations

import pandas as pd
import pytest

from dashboard.metrics import categorize_error, compute_overview


def test_compute_overview_preserves_missing_ttft() -> None:
    requests = pd.DataFrame(
        [
            {"success": 1, "total_latency_ms": 100.0, "ttft_ms": None},
            {"success": 0, "total_latency_ms": 900.0, "ttft_ms": None},
        ]
    )
    failovers = pd.DataFrame(columns=["id"])

    result = compute_overview(requests, failovers)

    assert result.request_count == 2
    assert result.success_rate_pct == 50.0
    assert result.p50_latency_ms == 500.0
    assert result.p50_ttft_ms is None
    assert result.failover_rate_pct == 0.0
    assert result.prompt_tokens is None


def test_request_rate_uses_selected_observation_window() -> None:
    requests = pd.DataFrame(
        [
            {"timestamp": "2026-08-13T00:00:00Z"},
            {"timestamp": "2026-08-13T00:00:01Z"},
        ]
    )

    result = compute_overview(
        requests,
        pd.DataFrame(columns=["id"]),
        observation_window_minutes=60,
    )

    assert result.request_rate_per_min == pytest.approx(2 / 60)


@pytest.mark.parametrize(
    ("raw", "status_code", "expected"),
    [
        ("connection_error", None, "Connection"),
        ("stream_read_error", None, "Streaming"),
        ("HTTP 429", 429, "Backpressure"),
        ("HTTP 503", 503, "Upstream 5xx"),
        (None, None, None),
    ],
)
def test_categorize_error(raw: str | None, status_code: int | None, expected: str | None) -> None:
    assert categorize_error(raw, status_code) == expected
