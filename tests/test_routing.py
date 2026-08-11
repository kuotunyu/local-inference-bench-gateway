"""Route-level behavior: /health, /v1/models, and request validation errors."""

from __future__ import annotations


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
