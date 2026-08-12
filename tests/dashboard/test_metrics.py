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
