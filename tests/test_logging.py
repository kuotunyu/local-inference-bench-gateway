"""SQLite request logging: successful and failed requests both produce a row with the
expected fields."""

from __future__ import annotations

import sqlite3

import httpx
import respx

from gateway.app import app

NON_STREAM_UPSTREAM_RESPONSE = {
    "id": "chatcmpl-abc",
    "object": "chat.completion",
    "created": 0,
    "model": "model-a",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
}


def _read_requests(path):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM requests ORDER BY id").fetchall()]
    finally:
        conn.close()


class BrokenSSEStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        raise httpx.ReadError("private upstream stream detail")

    async def aclose(self):
        pass


def test_database_schema_is_versioned_and_indexed(gateway_client, db_path):
    conn = sqlite3.connect(str(db_path()))
    try:
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
    finally:
        conn.close()

    assert user_version == 1
    assert journal_mode == "wal"
    assert indexes == {"idx_requests_timestamp", "idx_failover_events_timestamp"}


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
    respx.post("http://only.test/v1/chat/completions").mock(
        side_effect=httpx.ConnectError("refused")
    )

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


@respx.mock
async def test_connection_details_are_absent_from_response_and_request_log(gateway_client, db_path):
    private_detail = "10.20.30.40:9999/private-token"
    respx.post("http://only.test/v1/chat/completions").mock(
        side_effect=httpx.ConnectError(private_detail)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 502
    assert private_detail not in resp.text
    [row] = _read_requests(db_path())
    assert private_detail not in row["error_message"]
    assert row["error_message"] == "connection_error"


@respx.mock
async def test_upstream_error_body_is_not_persisted_in_request_log(gateway_client, db_path):
    private_detail = "prompt-and-token-must-not-enter-telemetry"
    respx.post("http://only.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            400,
            json={"error": {"message": private_detail, "type": "invalid_request_error"}},
        )
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "single-backend", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 400
    [row] = _read_requests(db_path())
    assert private_detail not in row["error_message"]
    assert row["error_message"] == "HTTP 400"


@respx.mock
async def test_request_log_write_failure_does_not_replace_valid_completion(
    gateway_client, tmp_path
):
    app.state.db_path = tmp_path
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=NON_STREAM_UPSTREAM_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "hi"


@respx.mock
async def test_failover_log_write_failure_does_not_prevent_fallback(gateway_client, tmp_path):
    app.state.db_path = tmp_path
    respx.post("http://primary.test/v1/chat/completions").mock(
        return_value=httpx.Response(503, json={"error": {"message": "busy", "type": "api_error"}})
    )
    respx.post("http://fallback.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=NON_STREAM_UPSTREAM_RESPONSE)
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "hi"


@respx.mock
async def test_stream_read_failure_releases_capacity_and_logs_safe_category(
    gateway_client, db_path
):
    respx.post("http://limited.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            stream=BrokenSSEStream(),
            headers={"Content-Type": "text/event-stream"},
        )
    )

    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={
            "model": "limited-alias",
            "stream": True,
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert resp.status_code == 200
    assert "partial" in resp.text
    assert "[DONE]" not in resp.text
    assert app.state.limiters["limited-alias"].active == 0
    [row] = _read_requests(db_path())
    assert row["success"] == 0
    assert row["error_message"] == "stream_read_error"
    assert "private upstream stream detail" not in row["error_message"]
