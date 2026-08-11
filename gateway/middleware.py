"""API key auth: `Authorization: Bearer <GATEWAY_API_KEY>`.

Reads the expected key at call time (not at import time) so tests can monkeypatch the
environment per-case without reloading the module. Auth is skipped entirely when no
GATEWAY_API_KEY is configured -- a deliberate local-dev convenience (matches how the gateway
ships with .env.example: copy it, set a real key, and auth turns on automatically).
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException


def _configured_api_key() -> str | None:
    return os.environ.get("GATEWAY_API_KEY") or None


async def verify_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = _configured_api_key()
    if not expected:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Missing or malformed Authorization header. Expected 'Bearer <key>'.",
                "type": "invalid_request_error",
                "code": "missing_api_key",
            },
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=401,
            detail={
                "message": "Incorrect API key provided.",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            },
        )
