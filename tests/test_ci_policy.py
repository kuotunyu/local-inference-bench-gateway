from __future__ import annotations

from release_checks.ci_policy import verify_ci_policy


def _write_workflow(tmp_path, workflow: str) -> None:
    path = tmp_path / ".github" / "workflows" / "ci.yml"
    path.parent.mkdir(parents=True)
    path.write_text(workflow, encoding="utf-8")


def test_ci_policy_requires_checkout_to_fetch_full_history(tmp_path) -> None:
    _write_workflow(
        tmp_path,
        """
jobs:
  verify:
    steps:
      - uses: actions/checkout@pinned
""",
    )

    violations = verify_ci_policy(tmp_path)

    assert any("full Git history" in violation for violation in violations), violations


def test_ci_policy_accepts_pinned_checkout_with_full_history(tmp_path) -> None:
    _write_workflow(
        tmp_path,
        """
jobs:
  verify:
    steps:
      - uses: actions/checkout@pinned
        with:
          fetch-depth: 0
""",
    )

    assert verify_ci_policy(tmp_path) == []


def test_ci_policy_accepts_quoted_zero_fetch_depth(tmp_path) -> None:
    _write_workflow(
        tmp_path,
        """
jobs:
  verify:
    steps:
      - uses: actions/checkout@pinned
        with:
          fetch-depth: "0"
""",
    )

    assert verify_ci_policy(tmp_path) == []


def test_ci_policy_requires_pull_request_checkout_to_use_head_sha(tmp_path) -> None:
    _write_workflow(
        tmp_path,
        """
on:
  pull_request:
jobs:
  verify:
    steps:
      - uses: actions/checkout@pinned
        with:
          fetch-depth: 0
""",
    )

    violations = verify_ci_policy(tmp_path)

    assert any("pull-request head SHA" in violation for violation in violations), violations


def test_ci_policy_reports_malformed_workflow_without_crashing(tmp_path) -> None:
    _write_workflow(tmp_path, "jobs: scalar")

    violations = verify_ci_policy(tmp_path)

    assert any("mapping" in violation for violation in violations), violations


def test_ci_policy_rejects_any_shallow_checkout_step(tmp_path) -> None:
    _write_workflow(
        tmp_path,
        """
jobs:
  verify:
    steps:
      - uses: actions/checkout@pinned
        with:
          fetch-depth: 0
      - uses: actions/checkout@pinned
        with:
""",
    )

    violations = verify_ci_policy(tmp_path)

    assert any("full Git history" in violation for violation in violations), violations
