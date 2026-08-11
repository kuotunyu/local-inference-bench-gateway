"""SQLite request logging: successful and failed requests both produce a row with the
expected fields."""

from __future__ import annotations

import sqlite3

import httpx
import respx

NON_STREAM_UPSTREAM_RESPONSE = {
    "id": "chatcmpl-abc",
    "object": "chat.completion",
    "created": 0,
    "model": "model-a",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
}


def _read_requests(path):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM requests ORDER BY id").fetchall()]
    finally:
        conn.close()


@respx.mock
async def test_successful_request_logs_expected_row(gateway_client, db_path):
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=NON_STREAM_UPSTREAM_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200

    rows = _read_requests(db_path())
    assert len(rows) == 1
    row = rows[0]
    assert row["alias"] == "test-alias"
    assert row["backend_name"] == "primary"
    assert row["model"] == "model-a"
    assert row["stream"] == 0
    assert row["status_code"] == 200
    assert row["success"] == 1
    assert row["prompt_tokens"] == 5
    assert row["completion_tokens"] == 2
    assert row["total_latency_ms"] > 0
    assert row["error_message"] is None


@respx.mock
async def test_all_backends_failing_logs_failure_row(gateway_client, db_path):
    respx.post("http://only.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("refused"))

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 502

    rows = _read_requests(db_path())
    assert len(rows) == 1
    row = rows[0]
    assert row["alias"] == "single-backend"
    assert row["success"] == 0
    assert row["backend_name"] is None
    assert row["error_message"] is not None
