"""Shared test fixtures.

Wires app.state directly instead of running the real lifespan -- the lifespan loads the real
gateway/models.yaml and starts a real HealthChecker polling loop, neither of which tests want
(tests need a registry pointed at fake backend URLs, and no background polling racing test
assertions). Route handlers only ever read request.app.state.*, so setting it up manually here
is sufficient without needing the app's startup/shutdown events to run.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from gateway import db as db_module
from gateway.app import app
from gateway.concurrency import ConcurrencyLimiter
from gateway.failover import HealthChecker
from gateway.registry import build_registry

TEST_REGISTRY_DATA = {
    "models": {
        "test-alias": {
            "backends": [
                {"name": "primary", "base_url": "http://primary.test/v1", "model": "model-a"},
                {"name": "fallback", "base_url": "http://fallback.test/v1", "model": "model-b"},
            ]
        },
        "single-backend": {
            "backends": [
                {"name": "only", "base_url": "http://only.test/v1", "model": "model-c"},
            ]
        },
        "limited-alias": {
            "max_concurrent": 2,
            "backends": [
                {"name": "limited", "base_url": "http://limited.test/v1", "model": "model-d"},
            ],
        },
    }
}


@pytest_asyncio.fixture
async def gateway_client(tmp_path, monkeypatch):
    monkeypatch.delenv("GATEWAY_API_KEY", raising=False)

    db_path = tmp_path / "test.db"
    db_module.init_db(db_path)

    app.state.registry = build_registry(TEST_REGISTRY_DATA)
    app.state.limiters = {
        alias: ConcurrencyLimiter(model_alias.max_concurrent)
        for alias, model_alias in app.state.registry.items()
    }
    app.state.db_path = db_path

    async with httpx.AsyncClient() as upstream_client:
        app.state.http_client = upstream_client
        app.state.health_checker = HealthChecker(upstream_client, [])

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


@pytest.fixture
def db_path():
    """Set by gateway_client via app.state.db_path; exposed separately for tests that want to
    inspect the SQLite log directly after making requests."""

    def _get():
        return app.state.db_path

    return _get
