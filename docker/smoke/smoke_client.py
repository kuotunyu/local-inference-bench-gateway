"""Assert the CPU-only Compose path from public health through authenticated fallback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("GATEWAY_URL", "http://gateway:9000").rstrip("/")
API_KEY = os.environ["GATEWAY_API_KEY"]


def request(path: str, *, payload: dict | None = None, authenticated: bool = False):
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_for_gateway(*, attempts: int = 30, delay_seconds: float = 1.0):
    """Wait for public health while preserving a nonzero smoke failure on startup errors."""
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            status, health = request("/health")
            if status == 200:
                return status, health
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(delay_seconds)
    raise RuntimeError(f"gateway did not become healthy after {attempts} attempts") from last_error


def main() -> None:
    status, health = wait_for_gateway()
    assert (status, health) == (200, {"status": "ok"})

    status, unauthorized = request("/v1/models")
    assert status == 401
    assert unauthorized["error"]["code"] == "missing_api_key"

    status, models = request("/v1/models", authenticated=True)
    assert status == 200
    assert {item["id"] for item in models["data"]} == {"smoke-alias"}

    status, completion = request(
        "/v1/chat/completions",
        authenticated=True,
        payload={
            "model": "smoke-alias",
            "messages": [{"role": "user", "content": "smoke"}],
        },
    )
    assert status == 200
    assert set(completion) == {"id", "object", "created", "model", "choices", "usage"}
    assert completion["model"] == "mock-fallback"
    assert completion["choices"][0]["message"]["content"] == "fallback-ok"
    print("CPU Compose smoke passed: auth, alias routing, primary 503, fallback 200")


if __name__ == "__main__":
    main()
