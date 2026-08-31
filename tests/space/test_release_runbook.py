from __future__ import annotations

from pathlib import Path

RUNBOOK = Path("docs/HF_SPACE_RELEASE.md")
CANONICAL_HUB_URL = "https://huggingface.co/spaces/steven0226/local-inference-bench-gateway"
TRUTH_CONTRACT = """\
公開證據示範（Demo Mode）
此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。
Deterministic Demo data is illustrative and is not production or sampled traffic.
Benchmark evidence is a dated, hardware- and version-specific snapshot.
Request-level raw benchmark runs are not public.
This Space cannot connect to a visitor's local system.
This Space provides neither live inference nor an SLA.
Hosting sleep or cold start is not system uptime evidence.
"""


def _runbook_text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def test_runbook_preserves_remote_and_about_gates() -> None:
    text = _runbook_text()
    ordered = [
        "Authenticated collision preflight",
        "STOP — separate owner authorization required for Space creation",
        "Public Space cold-start and mobile/desktop review",
        "STOP — separate owner authorization required for GitHub About",
        CANONICAL_HUB_URL,
    ]
    positions = [text.index(item) for item in ordered]

    assert positions == sorted(positions)
    assert "steven0226-local-inference-bench-gateway.hf.space" not in text
    assert "1440x900" in text
    assert "390x844" in text
    assert "No SLA" in text
    assert "NEVER_DEPLOY-hf-space-tampered" in text


def test_release_runbook_contains_every_claim_and_visual_gate() -> None:
    text = _runbook_text()
    required_instructions = (
        TRUTH_CONTRACT,
        "12/12 verified artifacts",
        "No degraded-evidence warning",
        "No endpoint URL",
        "No Demo/Live selector",
        "No current model or GPU execution claim",
        "Zero browser-console errors",
        "document.documentElement.scrollWidth === document.documentElement.clientWidth",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "Space sleep/cold-start",
        "Unavailable — evidence integrity check failed",
        "Gateway median TTFT overhead: 1.66 ms",
    )

    for instruction in required_instructions:
        assert instruction in text

    assert "all four views" in text
    assert "1440x900" in text
    assert "390x844" in text
    assert "NEVER_DEPLOY-hf-space-tampered" in text
    assert "suppressed" in text


def test_release_runbook_requires_unintercepted_zero_external_request_graphs() -> None:
    text = _runbook_text()
    valid_gate = text[
        text.index("## 2. Local valid-bundle visual review") : text.index(
            "## 3. Local fail-closed NEVER_DEPLOY review"
        )
    ]
    never_deploy_gate = text[
        text.index("## 3. Local fail-closed NEVER_DEPLOY review") : text.index(
            "## 4. Authenticated collision preflight"
        )
    ]
    required_instructions = (
        "unintercepted CDP or Playwright request graph",
        "original full URL",
        "resource type",
        "initiator metadata",
        "Only loopback and same-origin runtime requests are permitted",
        "Require exactly zero external origins",
        "Any external origin, including `data.streamlit.io` and Fivetran, is RED",
        "Do not block, abort, intercept, rewrite, or fulfill requests",
    )

    for gate in (valid_gate, never_deploy_gate):
        normalized_gate = " ".join(gate.split())
        for instruction in required_instructions:
            assert instruction in normalized_gate


def test_release_runbook_keeps_remote_writes_behind_stops() -> None:
    text = _runbook_text()
    remote_gate = text.index("uv run --frozen python -m release_checks.space_remote_gate")
    creation_stop = text.index("STOP — separate owner authorization required for Space creation")
    create_space = text.index("create_repo(")
    upload_bundle = text.index("upload_folder(")
    public_review = text.index("Public Space cold-start and mobile/desktop review")
    about_stop = text.index("STOP — separate owner authorization required for GitHub About")
    about_mutation = text.index("gh api --method PATCH")
    about_readback = text.index("gh api --method GET", about_mutation)

    first_remote_write = min(create_space, upload_bundle, about_mutation)
    assert remote_gate < creation_stop < first_remote_write
    assert create_space < upload_bundle < public_review < about_stop
    assert about_stop < about_mutation < about_readback
    assert "The preflight performs GET only" in text
    assert "Paths containing `NEVER_DEPLOY` are prohibited inputs to every remote command" in text
