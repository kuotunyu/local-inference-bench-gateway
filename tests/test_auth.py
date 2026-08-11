"""API key auth: disabled when GATEWAY_API_KEY is unset, enforced when it is."""

from __future__ import annotations

from gateway import middleware


async def test_no_key_configured_allows_unauthenticated_requests(gateway_client):
    # gateway_client fixture deletes GATEWAY_API_KEY -- auth is off by default (local-dev mode)
    resp = await gateway_client.get("/v1/models")
    assert resp.status_code == 200


async def test_missing_auth_header_returns_401_when_key_configured(gateway_client, monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")
    resp = await gateway_client.get("/v1/models")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "missing_api_key"


async def test_wrong_bearer_token_returns_401(gateway_client, monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")
    resp = await gateway_client.get("/v1/models", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"


async def test_correct_bearer_token_succeeds(gateway_client, monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")
    resp = await gateway_client.get("/v1/models", headers={"Authorization": "Bearer secret123"})
    assert resp.status_code == 200


async def test_configured_token_uses_constant_time_comparison(gateway_client, monkeypatch):
    calls = []

    def compare_digest(provided, expected):
        calls.append((provided, expected))
        return provided == expected

    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")
    monkeypatch.setattr(middleware.secrets, "compare_digest", compare_digest)

    resp = await gateway_client.get("/v1/models", headers={"Authorization": "Bearer secret123"})

    assert resp.status_code == 200
    assert calls == [("secret123", "secret123")]


async def test_malformed_auth_header_returns_401(gateway_client, monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")
    resp = await gateway_client.get("/v1/models", headers={"Authorization": "secret123"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "missing_api_key"


async def test_public_health_does_not_expose_authenticated_backend_topology(
    gateway_client, monkeypatch
):
    monkeypatch.setenv("GATEWAY_API_KEY", "secret123")

    public_health = await gateway_client.get("/health")
    backend_health = await gateway_client.get("/health/backends")

    assert public_health.status_code == 200
    assert backend_health.status_code == 401
    assert backend_health.json()["error"]["code"] == "missing_api_key"
