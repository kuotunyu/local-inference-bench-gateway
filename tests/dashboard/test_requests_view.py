from __future__ import annotations

import pandas as pd

from dashboard.views.requests import build_request_table


def test_request_table_preserves_missing_values_and_newest_first() -> None:
    requests = pd.DataFrame(
        [
            {"timestamp": "2026-08-13T00:00:00+00:00", "ttft_ms": None},
            {"timestamp": "2026-08-13T00:01:00+00:00", "ttft_ms": 12.5},
        ]
    )
    table = build_request_table(requests)
    assert table.iloc[0]["timestamp"] >= table.iloc[1]["timestamp"]
    assert table.loc[table["ttft_ms"].isna(), "TTFT"].eq("—").all()
