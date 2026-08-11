from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path


def _load_smoke_client(monkeypatch):
    monkeypatch.setenv("GATEWAY_API_KEY", "test-key")
    path = Path(__file__).parents[1] / "docker" / "smoke" / "smoke_client.py"
    spec = importlib.util.spec_from_file_location("smoke_client", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wait_for_gateway_retries_connection_errors(monkeypatch):
    smoke_client = _load_smoke_client(monkeypatch)
    responses = iter(
        [
            urllib.error.URLError("connection refused"),
            (200, {"status": "ok"}),
        ]
    )

    def fake_request(path):
        assert path == "/health"
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(smoke_client, "request", fake_request)
    monkeypatch.setattr(smoke_client.time, "sleep", lambda _: None)

    assert smoke_client.wait_for_gateway(attempts=2, delay_seconds=0) == (
        200,
        {"status": "ok"},
    )


def test_wait_for_gateway_fails_after_retry_budget(monkeypatch):
    smoke_client = _load_smoke_client(monkeypatch)
    monkeypatch.setattr(
        smoke_client,
        "request",
        lambda path: (_ for _ in ()).throw(urllib.error.URLError("connection refused")),
    )
    monkeypatch.setattr(smoke_client.time, "sleep", lambda _: None)

    try:
        smoke_client.wait_for_gateway(attempts=2, delay_seconds=0)
    except RuntimeError as exc:
        assert "did not become healthy" in str(exc)
    else:
        raise AssertionError("unavailable gateway must fail the smoke client")
