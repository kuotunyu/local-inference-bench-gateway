"""Audit CI workflow settings needed by release checks."""

from __future__ import annotations

from pathlib import Path

import yaml


def verify_ci_policy(repo_root: Path) -> list[str]:
    workflow_path = repo_root.resolve() / ".github" / "workflows" / "ci.yml"
    try:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [f"cannot read CI workflow: {type(exc).__name__}"]
    if not isinstance(workflow, dict):
        return ["CI workflow root must be a mapping"]

    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict):
        return ["CI workflow jobs must be a mapping"]
    checkout_steps = [
        step
        for job in jobs.values()
        if isinstance(job, dict)
        for step in (job.get("steps", []) if isinstance(job.get("steps", []), list) else [])
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    if not checkout_steps:
        return ["CI workflow must check out source"]
    if any(
        not isinstance(step.get("with"), dict) or str(step["with"].get("fetch-depth")) != "0"
        for step in checkout_steps
    ):
        return ["CI checkout must fetch full Git history for publication audit"]
    triggers = workflow.get("on", workflow.get(True))
    pull_request_enabled = (
        triggers == "pull_request"
        or isinstance(triggers, list)
        and "pull_request" in triggers
        or isinstance(triggers, dict)
        and "pull_request" in triggers
    )
    if pull_request_enabled and any(
        "github.event.pull_request.head.sha" not in str(step["with"].get("ref", ""))
        for step in checkout_steps
    ):
        return ["CI pull_request checkout must use the pull-request head SHA"]
    return []
