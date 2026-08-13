from __future__ import annotations

import pandas as pd

from dashboard.views.requests import (
    REQUEST_TABLE_HEIGHT,
    REQUEST_TABLE_ROW_HEIGHT,
    apply_request_filters,
    build_request_table,
    request_table_column_config,
)


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


def test_request_table_uses_readable_display_values() -> None:
    requests = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-13T00:00:00+00:00",
                "alias": "fast",
                "backend_name": None,
                "model": "bench-model",
                "status_code": None,
                "prompt_tokens": None,
                "completion_tokens": 9,
                "success": 0,
                "stream": 1,
                "error_message": "timeout",
            }
        ]
    )

    table = build_request_table(requests)

    assert table.iloc[0]["backend_name"] == "—"
    assert table.iloc[0]["status_code"] == "—"
    assert table.iloc[0]["prompt_tokens"] == "—"
    assert table.iloc[0]["completion_tokens"] == "9"
    assert bool(table.iloc[0]["success"]) is False
    assert bool(table.iloc[0]["stream"]) is True


def test_request_table_columns_are_centered_and_zh_tw_first() -> None:
    config = request_table_column_config()

    assert set(config) == {
        "timestamp",
        "alias",
        "backend_name",
        "model",
        "status_code",
        "success",
        "Latency",
        "TTFT",
        "prompt_tokens",
        "completion_tokens",
        "stream",
        "error_category",
    }
    assert all(column["alignment"] == "center" for column in config.values())
    assert config["timestamp"]["label"] == "時間（UTC+8）"
    assert config["status_code"]["label"] == "HTTP"
    assert config["success"]["label"] == "成功"
    assert config["stream"]["label"] == "Streaming"
    assert config["error_category"]["label"] == "Error 分類"
    assert REQUEST_TABLE_ROW_HEIGHT >= 42


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


def test_request_table_uses_remaining_operational_canvas() -> None:
    assert REQUEST_TABLE_HEIGHT >= 540
