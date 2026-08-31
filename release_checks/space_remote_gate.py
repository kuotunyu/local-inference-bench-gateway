"""Fail-closed, read-only checks for the canonical Hugging Face Space identity."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from typing import Literal, Never

import httpx

SPACE_ID = "steven0226/local-inference-bench-gateway"
OWNER = "steven0226"

_WHOAMI_URL = "https://huggingface.co/api/whoami-v2"
_SPACE_URL = f"https://huggingface.co/api/spaces/{SPACE_ID}"
_SPACES_URL = "https://huggingface.co/api/spaces"
_HUGGING_FACE_HOST = "huggingface.co"
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 5
_MAX_PAGES = 100
_MISSING = object()

RemoteGateReason = Literal[
    "owner_mismatch",
    "docker_ineligible",
    "exact_identity_exists",
    "namespace_collision",
    "authentication_failed",
    "rate_limited",
    "remote_error",
    "malformed_response",
    "timeout",
    "pagination_incomplete",
]


class RemoteGateError(RuntimeError):
    """A stable, non-sensitive reason that stops publication."""

    def __init__(self, reason: RemoteGateReason) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class RemoteGateDecision:
    """The verified canonical identity and Docker eligibility decision."""

    space_id: str
    owner: str
    available: bool
    docker_eligible: bool


def _stop(reason: RemoteGateReason) -> Never:
    raise RemoteGateError(reason)


def _is_hugging_face_url(url: httpx.URL, *, spaces_listing: bool = False) -> bool:
    if (
        url.scheme != "https"
        or url.host != _HUGGING_FACE_HOST
        or url.username
        or url.password
        or url.port not in (None, 443)
    ):
        return False
    return not spaces_listing or url.path == "/api/spaces"


def _request_failure(reason: RemoteGateReason, *, continuation: bool) -> Never:
    if continuation:
        _stop("pagination_incomplete")
    _stop(reason)


def _get(
    client: httpx.Client,
    url: httpx.URL,
    token: str,
    *,
    continuation: bool = False,
) -> httpx.Response:
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        try:
            response = client.get(
                current,
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            _request_failure("timeout", continuation=continuation)
        except httpx.HTTPError:
            _request_failure("remote_error", continuation=continuation)

        if response.status_code not in _REDIRECT_STATUSES:
            return response

        location = response.headers.get("location")
        if not location or redirect_count == _MAX_REDIRECTS:
            _request_failure("remote_error", continuation=continuation)
        try:
            redirected = current.join(location)
        except (TypeError, ValueError):
            _request_failure("remote_error", continuation=continuation)
        if not _is_hugging_face_url(redirected):
            _request_failure("remote_error", continuation=continuation)
        current = redirected

    raise AssertionError("unreachable")


def _unexpected_status(response: httpx.Response, *, continuation: bool = False) -> Never:
    if continuation:
        _stop("pagination_incomplete")
    if response.status_code in {401, 403}:
        _stop("authentication_failed")
    if response.status_code == 429:
        _stop("rate_limited")
    _stop("remote_error")


def _json(response: httpx.Response, *, continuation: bool = False) -> object:
    try:
        return response.json()
    except (UnicodeDecodeError, ValueError):
        if continuation:
            _stop("pagination_incomplete")
        _stop("malformed_response")


def _check_owner(client: httpx.Client, token: str) -> None:
    response = _get(client, httpx.URL(_WHOAMI_URL), token)
    if response.status_code != 200:
        _unexpected_status(response)

    payload = _json(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
        _stop("malformed_response")
    if payload["name"] != OWNER:
        _stop("owner_mismatch")
    if payload.get("isPro") is not True:
        _stop("docker_ineligible")


def _check_exact_identity(client: httpx.Client, token: str) -> None:
    response = _get(client, httpx.URL(_SPACE_URL), token)
    if response.status_code == 200:
        _stop("exact_identity_exists")
    if response.status_code != 404:
        _unexpected_status(response)


def _page_items(payload: object, *, continuation: bool) -> tuple[list[object], object]:
    if isinstance(payload, list):
        return payload, _MISSING
    if not isinstance(payload, dict):
        _request_failure("malformed_response", continuation=continuation)

    item_keys = [key for key in ("items", "spaces") if key in payload]
    if len(item_keys) != 1 or not isinstance(payload[item_keys[0]], list):
        _request_failure("malformed_response", continuation=continuation)

    declared_next: object = payload.get("next", _MISSING)
    if "pagination" not in payload:
        return payload[item_keys[0]], declared_next

    pagination = payload["pagination"]
    if not isinstance(pagination, dict):
        _stop("pagination_incomplete")

    pagination_next: object = _MISSING
    for key in ("next", "next_cursor", "nextCursor"):
        if key in pagination:
            pagination_next = pagination[key]
            break

    has_next = pagination.get("has_next", pagination.get("hasNextPage", _MISSING))
    if has_next is True and pagination_next is _MISSING:
        for key in ("cursor", "endCursor"):
            if key in pagination:
                pagination_next = pagination[key]
                break
        if pagination_next is _MISSING:
            _stop("pagination_incomplete")
    elif has_next is False:
        pagination_next = None
    elif has_next is not _MISSING and not isinstance(has_next, bool):
        _stop("pagination_incomplete")

    if declared_next is not _MISSING and pagination_next is not _MISSING:
        if declared_next != pagination_next:
            _stop("pagination_incomplete")
    elif pagination_next is not _MISSING:
        declared_next = pagination_next
    return payload[item_keys[0]], declared_next


def _candidate_space_id(item: object, *, continuation: bool) -> str:
    if not isinstance(item, dict):
        _request_failure("malformed_response", continuation=continuation)
    candidate = item.get("id")
    if candidate is None:
        author = item.get("author")
        name = item.get("name")
        if isinstance(author, str) and isinstance(name, str):
            candidate = f"{author}/{name}"
    if not isinstance(candidate, str) or not candidate or "/" not in candidate:
        _request_failure("malformed_response", continuation=continuation)
    return candidate


def _link_continuation(response: httpx.Response) -> object:
    raw_link = response.headers.get("link")
    try:
        entry = response.links.get("next")
    except (KeyError, TypeError, ValueError):
        entry = None
    if entry is None:
        if raw_link and 'rel="next"' in raw_link.lower():
            _stop("pagination_incomplete")
        return _MISSING
    url = entry.get("url")
    if not isinstance(url, str) or not url:
        _stop("pagination_incomplete")
    return url


def _continuation_url(value: object, current: httpx.URL) -> httpx.URL | None:
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _stop("pagination_incomplete")
    value = value.strip()

    if "://" not in value and not value.startswith(("/", "?")):
        parameters = [(key, item) for key, item in current.params.multi_items() if key != "cursor"]
        parameters.append(("cursor", value))
        target = httpx.URL(_SPACES_URL, params=parameters)
    else:
        try:
            target = current.join(value)
        except (TypeError, ValueError):
            _stop("pagination_incomplete")

    if not _is_hugging_face_url(target, spaces_listing=True):
        _stop("pagination_incomplete")
    authors = target.params.get_list("author")
    if authors and authors != [OWNER]:
        _stop("pagination_incomplete")
    return target


def _next_page_url(
    payload_next: object, response: httpx.Response, current: httpx.URL
) -> httpx.URL | None:
    link_next = _link_continuation(response)
    payload_url = _continuation_url(payload_next, current)
    link_url = _continuation_url(link_next, current)
    if payload_url is not None and link_url is not None and payload_url != link_url:
        _stop("pagination_incomplete")
    return payload_url or link_url


def _check_namespace(client: httpx.Client, token: str) -> None:
    current = httpx.URL(_SPACES_URL, params={"author": OWNER})
    seen = {str(current)}

    for page_index in range(_MAX_PAGES):
        continuation = page_index > 0
        response = _get(client, current, token, continuation=continuation)
        if response.status_code != 200:
            _unexpected_status(response, continuation=continuation)
        payload = _json(response, continuation=continuation)
        items, payload_next = _page_items(payload, continuation=continuation)

        for item in items:
            candidate = _candidate_space_id(item, continuation=continuation)
            if candidate.casefold() == SPACE_ID.casefold():
                _stop("namespace_collision")

        next_url = _next_page_url(payload_next, response, current)
        if next_url is None:
            return
        normalized = str(next_url)
        if normalized in seen:
            _stop("pagination_incomplete")
        seen.add(normalized)
        current = next_url

    _stop("pagination_incomplete")


def check_remote_gate(client: httpx.Client, token: str) -> RemoteGateDecision:
    """Verify ownership, Docker eligibility, and canonical identity availability using GET only."""

    if not isinstance(token, str) or not token.strip():
        _stop("authentication_failed")
    token = token.strip()
    _check_owner(client, token)
    _check_exact_identity(client, token)
    _check_namespace(client, token)
    return RemoteGateDecision(
        space_id=SPACE_ID,
        owner=OWNER,
        available=True,
        docker_eligible=True,
    )


def main(
    *,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[[], httpx.Client] | None = None,
) -> int:
    """Run the authenticated gate without exposing credentials or remote error details."""

    environment = os.environ if environ is None else environ
    token = environment.get("HF_TOKEN")
    if not isinstance(token, str) or not token.strip():
        print("remote gate stopped: authentication_failed", file=sys.stderr)
        return 1

    factory = client_factory or (lambda: httpx.Client(timeout=10.0))
    try:
        with factory() as client:
            decision = check_remote_gate(client, token)
    except RemoteGateError as error:
        print(f"remote gate stopped: {error.reason}", file=sys.stderr)
        return 1
    except Exception:
        print("remote gate stopped: remote_error", file=sys.stderr)
        return 1

    print(json.dumps(asdict(decision), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
