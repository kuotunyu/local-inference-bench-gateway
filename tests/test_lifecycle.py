from __future__ import annotations

import importlib

import pytest

from gateway.registry import build_registry


async def test_lifespan_always_stops_health_checks_and_closes_client(monkeypatch, tmp_path):
    app_module = importlib.import_module("gateway.app")
    registry = build_registry(
        {
            "models": {
                "test": {
                    "backends": [
                        {
                            "name": "only",
                            "base_url": "http://only.test/v1",
                            "model": "model-a",
                        }
                    ]
                }
            }
        }
    )

    class FakeClient:
        def __init__(self):
            self.closed = False

        async def aclose(self):
            self.closed = True

    class FakeHealthChecker:
        def __init__(self, _client, _urls):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        async def stop(self):
            self.stopped = True

    client = FakeClient()
    checker = FakeHealthChecker(client, [])
    monkeypatch.setattr(app_module, "load_registry", lambda _path: registry)
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(app_module.db, "init_db", lambda _path: None)
    monkeypatch.setattr(app_module.failover, "HealthChecker", lambda _client, _urls: checker)
    monkeypatch.setenv("GATEWAY_DB_PATH", str(tmp_path / "gateway.db"))

    with pytest.raises(RuntimeError, match="application failure"):
        async with app_module.lifespan(app_module.app):
            assert checker.started is True
            raise RuntimeError("application failure")

    assert checker.stopped is True
    assert client.closed is True
