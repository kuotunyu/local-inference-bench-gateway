"""OpenAI-shaped error envelopes for gateway-level failures.

Errors that originate from a live backend (the engine itself returned 4xx/5xx) are passed
through as-is instead of using these -- llama.cpp/Ollama/LM Studio all already return
OpenAI-shaped {"error": {...}} bodies (verified in Part A), so wrapping them again would be
redundant. These helpers are only for failures the gateway itself detects: unknown alias,
malformed request, unreachable backend, upstream timeout.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse


def error_content(
    message: str,
    error_type: str,
    *,
    param: str | None = None,
    code: str | None = None,
) -> dict:
    return {
        "error": {
            "message": message,
            "type": error_type,
            "param": param,
            "code": code,
        }
    }


def openai_error(
    status_code: int,
    message: str,
    error_type: str,
    *,
    param: str | None = None,
    code: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=error_content(message, error_type, param=param, code=code),
    )


def model_not_found(alias: str) -> JSONResponse:
    return openai_error(
        404,
        f"The model '{alias}' does not exist or is not registered with this gateway.",
        "invalid_request_error",
        param="model",
        code="model_not_found",
    )


def missing_field(field: str) -> JSONResponse:
    return openai_error(
        400,
        f"Missing required field: '{field}'.",
        "invalid_request_error",
        param=field,
        code="missing_field",
    )


def invalid_json() -> JSONResponse:
    return openai_error(400, "Request body is not valid JSON.", "invalid_request_error")


def invalid_request_body() -> JSONResponse:
    return openai_error(
        400,
        "Request body must be a JSON object.",
        "invalid_request_error",
        code="invalid_request_body",
    )


def invalid_field(field: str, expected: str) -> JSONResponse:
    return openai_error(
        400,
        f"Field '{field}' must be {expected}.",
        "invalid_request_error",
        param=field,
        code="invalid_field",
    )


def upstream_unavailable(alias: str) -> JSONResponse:
    return openai_error(
        502,
        f"No upstream backend is available for model '{alias}'.",
        "api_error",
        code="upstream_unavailable",
    )


def upstream_timeout(backend_name: str) -> JSONResponse:
    return openai_error(
        504,
        f"Upstream backend '{backend_name}' timed out.",
        "api_error",
        code="upstream_timeout",
    )


def upstream_protocol_error_content() -> dict:
    return error_content(
        "Upstream backend returned a non-JSON error response.",
        "api_error",
        code="upstream_protocol_error",
    )


def too_many_requests(alias: str, limit: int, retry_after_s: int = 1) -> JSONResponse:
    return openai_error(
        429,
        f"Too many concurrent requests for model '{alias}' (limit: {limit}). Retry shortly.",
        "rate_limit_error",
        code="concurrency_limit_exceeded",
        headers={"Retry-After": str(retry_after_s)},
    )
