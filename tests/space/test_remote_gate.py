from __future__ import annotations

from collections.abc import Iterator, Sequence

import httpx
import pytest
import respx

from release_checks.space_remote_gate import (
    RemoteGateDecision,
    RemoteGateError,
    check_remote_gate,
    main,
)

SPACE_ID = "steven0226/local-inference-bench-gateway"
OWNER = "steven0226"
TOKEN = "secret-test-token"
WHOAMI_URL = "https://huggingface.co/api/whoami-v2"
SPACE_URL = f"https://huggingface.co/api/spaces/{SPACE_ID}"
SPACES_URL = "https://huggingface.co/api/spaces"


class ScriptedRemote:
    """A transport that permits only a finite sequence of mocked GET responses."""

    def __init__(self, outcomes: Sequence[httpx.Response | Exception]) -> None:
        self._outcomes: Iterator[httpx.Response | Exception] = iter(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method != "GET":
            raise AssertionError(f"remote mutation attempted with {request.method}")
        try:
            outcome = next(self._outcomes)
        except StopIteration as error:
            raise AssertionError(f"unexpected remote request: {request.url}") from error
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def client_for(script: ScriptedRemote) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(script))


def verified_owner() -> httpx.Response:
    return httpx.Response(200, json={"name": OWNER, "isPro": True})


def missing_space() -> httpx.Response:
    return httpx.Response(404, json={"error": "Not Found"})


def namespace_space(space_id: str = SPACE_ID) -> dict[str, object]:
    return {
        "id": space_id,
        "author": OWNER,
        "private": False,
        "sdk": "docker",
        "likes": 0,
        "downloads": 0,
        "tags": [],
        "lastModified": "2026-08-31T00:00:00.000Z",
    }


@respx.mock
def test_remote_gate_accepts_only_verified_owner_clear_name_and_pro_account(
    capsys: pytest.CaptureFixture[str],
) -> None:
    respx.get(WHOAMI_URL).mock(
        return_value=httpx.Response(200, json={"name": OWNER, "isPro": True})
    )
    respx.get(SPACE_URL).mock(return_value=httpx.Response(404))
    respx.get(SPACES_URL).mock(return_value=httpx.Response(200, json=[]))

    with httpx.Client() as client:
        decision = check_remote_gate(client, TOKEN)

    assert decision == RemoteGateDecision(
        space_id=SPACE_ID,
        owner=OWNER,
        available=True,
        docker_eligible=True,
    )
    assert {call.request.method for call in respx.calls} == {"GET"}
    assert all(call.request.headers["authorization"] == f"Bearer {TOKEN}" for call in respx.calls)
    captured = capsys.readouterr()
    assert TOKEN not in captured.out
    assert TOKEN not in captured.err


def remote_error_scenarios() -> list[tuple[str, list[httpx.Response | Exception]]]:
    next_url = f"{SPACES_URL}?author={OWNER}&cursor=next-page"
    return [
        ("owner_mismatch", [httpx.Response(200, json={"name": "someone-else", "isPro": True})]),
        ("docker_ineligible", [httpx.Response(200, json={"name": OWNER, "isPro": False})]),
        ("docker_ineligible", [httpx.Response(200, json={"name": OWNER})]),
        ("docker_ineligible", [httpx.Response(200, json={"name": OWNER, "isPro": "true"})]),
        (
            "exact_identity_exists",
            [verified_owner(), httpx.Response(200, json=namespace_space())],
        ),
        (
            "namespace_collision",
            [verified_owner(), missing_space(), httpx.Response(200, json=[namespace_space()])],
        ),
        ("authentication_failed", [httpx.Response(401, json={"error": "Unauthorized"})]),
        ("authentication_failed", [httpx.Response(403, json={"error": "Forbidden"})]),
        ("rate_limited", [httpx.Response(429, json={"error": "Too Many Requests"})]),
        ("remote_error", [httpx.Response(503, json={"error": "Unavailable"})]),
        (
            "malformed_response",
            [
                httpx.Response(
                    200, content=b"not-json", headers={"content-type": "application/json"}
                )
            ],
        ),
        ("timeout", [httpx.ReadTimeout("timed out")]),
        (
            "pagination_incomplete",
            [
                verified_owner(),
                missing_space(),
                httpx.Response(
                    200,
                    json=[],
                    headers={"Link": f'<{next_url}>; rel="next"'},
                ),
                httpx.ReadTimeout("next page timed out"),
            ],
        ),
    ]


@pytest.mark.parametrize(("reason", "outcomes"), remote_error_scenarios())
def test_remote_gate_failures_have_stable_reasons_and_never_disclose_the_token(
    reason: str,
    outcomes: list[httpx.Response | Exception],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = ScriptedRemote(outcomes)

    with client_for(script) as client, pytest.raises(RemoteGateError) as raised:
        check_remote_gate(client, TOKEN)

    assert raised.value.reason == reason
    assert script.requests
    assert {request.method for request in script.requests} == {"GET"}
    captured = capsys.readouterr()
    assert TOKEN not in captured.out
    assert TOKEN not in captured.err


def test_remote_gate_completes_link_header_pagination_before_deciding() -> None:
    next_url = f"{SPACES_URL}?author={OWNER}&cursor=second-page"
    script = ScriptedRemote(
        [
            verified_owner(),
            missing_space(),
            httpx.Response(
                200,
                json=[namespace_space(f"{OWNER}/another-space")],
                headers={"Link": f'<{next_url}>; rel="next"'},
            ),
            httpx.Response(200, json=[]),
        ]
    )

    with client_for(script) as client:
        decision = check_remote_gate(client, TOKEN)

    assert decision.available is True
    assert str(script.requests[-1].url) == next_url
    assert all(request.headers["authorization"] == f"Bearer {TOKEN}" for request in script.requests)


def test_remote_gate_detects_case_insensitive_identity_on_later_page() -> None:
    next_url = f"{SPACES_URL}?author={OWNER}&cursor=second-page"
    script = ScriptedRemote(
        [
            verified_owner(),
            missing_space(),
            httpx.Response(200, json=[], headers={"Link": f'<{next_url}>; rel="next"'}),
            httpx.Response(
                200,
                json=[namespace_space("Steven0226/LOCAL-INFERENCE-BENCH-GATEWAY")],
            ),
        ]
    )

    with client_for(script) as client, pytest.raises(RemoteGateError) as raised:
        check_remote_gate(client, TOKEN)

    assert raised.value.reason == "namespace_collision"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "not-an-object",
        {"name": 123, "isPro": True},
    ],
)
def test_remote_gate_rejects_malformed_identity_payloads(payload: object) -> None:
    script = ScriptedRemote([httpx.Response(200, json=payload)])

    with client_for(script) as client, pytest.raises(RemoteGateError) as raised:
        check_remote_gate(client, TOKEN)

    assert raised.value.reason == "malformed_response"


def test_remote_gate_rejects_unsafe_redirect_without_sending_authorization_off_host() -> None:
    script = ScriptedRemote(
        [httpx.Response(302, headers={"Location": "https://example.invalid/credential-capture"})]
    )

    with client_for(script) as client, pytest.raises(RemoteGateError) as raised:
        check_remote_gate(client, TOKEN)

    assert raised.value.reason == "remote_error"
    assert [request.url.host for request in script.requests] == ["huggingface.co"]


def test_remote_gate_stops_when_declared_next_cursor_repeats() -> None:
    repeated_url = f"{SPACES_URL}?author={OWNER}"
    script = ScriptedRemote(
        [
            verified_owner(),
            missing_space(),
            httpx.Response(
                200,
                json={"items": [], "next": repeated_url},
            ),
        ]
    )

    with client_for(script) as client, pytest.raises(RemoteGateError) as raised:
        check_remote_gate(client, TOKEN)

    assert raised.value.reason == "pagination_incomplete"


def test_cli_stops_without_reading_a_real_environment_or_opening_a_client(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden_client_factory() -> httpx.Client:
        raise AssertionError("client must not open without an injected token")

    result = main(environ={}, client_factory=forbidden_client_factory)

    assert result == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "remote gate stopped: authentication_failed\n"


def test_cli_uses_injected_token_and_mock_transport_without_disclosing_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = ScriptedRemote([verified_owner(), missing_space(), httpx.Response(200, json=[])])

    def client_factory() -> httpx.Client:
        return client_for(script)

    result = main(environ={"HF_TOKEN": TOKEN}, client_factory=client_factory)

    assert result == 0
    captured = capsys.readouterr()
    assert captured.out == (
        '{"available": true, "docker_eligible": true, '
        f'"owner": "{OWNER}", "space_id": "{SPACE_ID}"}}\n'
    )
    assert captured.err == ""
    assert TOKEN not in captured.out
    assert TOKEN not in captured.err


def test_cli_reports_only_stable_failure_reason_from_mock_transport(
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = ScriptedRemote([httpx.Response(200, json={"name": "someone-else", "isPro": True})])

    result = main(
        environ={"HF_TOKEN": TOKEN},
        client_factory=lambda: client_for(script),
    )

    assert result == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "remote gate stopped: owner_mismatch\n"
    assert TOKEN not in captured.err
