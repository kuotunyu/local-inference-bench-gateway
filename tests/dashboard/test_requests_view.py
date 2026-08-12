from __future__ import annotations

import pandas as pd

from dashboard.views.requests import apply_request_filters, build_request_table


def test_request_table_preserves_missing_values_and_newest_first() -> None:
    requests = pd.DataFrame(
        [
            {"timestamp": "2026-08-13T00:00:00+00:00", "ttft_ms": None},
            {"timestamp": "2026-08-13T00:01:00+00:00", "ttft_ms": 12.5},
        ]
    )
    table = build_request_table(requests)
    assert table.iloc[0]["timestamp"] >= table.iloc[1]["timestamp"]
    assert str(table.iloc[0]["timestamp"].tz) == "Asia/Taipei"
    assert table.loc[table["ttft_ms"].isna(), "TTFT"].eq("—").all()


def test_request_filters_combine_status_and_transport() -> None:
    requests = pd.DataFrame(
        [
            {
                "alias": "fast",
                "backend_name": "llamacpp",
                "success": 0,
                "status_code": 429,
                "stream": 1,
                "error_message": "HTTP 429",
            },
            {
                "alias": "fast",
                "backend_name": "llamacpp",
                "success": 1,
                "status_code": 200,
                "stream": 0,
                "error_message": None,
            },
        ]
    )

    filtered = apply_request_filters(
        requests,
        status_codes=[429],
        stream_mode="Streaming",
        categories=["Backpressure"],
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["status_code"] == 429
