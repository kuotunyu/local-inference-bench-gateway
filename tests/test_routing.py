"""Route-level behavior: /health, /v1/models, and request validation errors."""

from __future__ import annotations

import pytest


async def test_health(gateway_client):
    resp = await gateway_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_list_models_returns_registered_aliases(gateway_client):
    resp = await gateway_client.get("/v1/models")
    assert resp.status_code == 200
    body = resp.json()
    ids = {m["id"] for m in body["data"]}
    assert ids == {"test-alias", "single-backend", "limited-alias"}
    assert body["object"] == "list"


async def test_unknown_model_alias_returns_404(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "does-not-exist", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["code"] == "model_not_found"


async def test_missing_model_field_returns_400(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["code"] == "missing_field"


async def test_invalid_json_body_returns_400(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions", content=b"not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["type"] == "invalid_request_error"


async def test_non_object_json_body_returns_openai_error(gateway_client):
    resp = await gateway_client.post("/v1/chat/completions", json=[])

    assert resp.status_code == 400
    assert resp.json()["error"] == {
        "message": "Request body must be a JSON object.",
        "type": "invalid_request_error",
        "param": None,
        "code": "invalid_request_body",
    }


async def test_invalid_utf8_json_body_returns_400(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions", content=b"\xff", headers={"Content-Type": "application/json"}
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["type"] == "invalid_request_error"


@pytest.mark.parametrize("invalid_model", [[], {}, 123])
async def test_non_string_model_field_returns_400(gateway_client, invalid_model):
    resp = await gateway_client.post(
        "/v1/chat/completions", json={"model": invalid_model, "messages": []}
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["param"] == "model"


async def test_non_object_stream_options_returns_400(gateway_client):
    resp = await gateway_client.post(
        "/v1/chat/completions",
        json={"model": "test-alias", "stream": True, "stream_options": [], "messages": []},
    )

    assert resp.status_code == 400
    assert resp.json()["error"]["param"] == "stream_options"
