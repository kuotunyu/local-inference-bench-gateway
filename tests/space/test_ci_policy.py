from pathlib import Path

import yaml


def _workflow_steps() -> dict[str, dict[str, object]]:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["verify"]["steps"]
    named_steps = {step["name"]: step for step in steps}
    assert len(named_steps) == len(steps), "CI step names must be unique"
    return named_steps


def test_ci_builds_non_root_space_and_runs_without_network() -> None:
    steps = _workflow_steps()
    export_run = str(steps["Export public Space bundle"]["run"])
    build_run = str(steps["Build non-root public Space image"]["run"])
    smoke_run = str(steps["Smoke public Space without network"]["run"])
    logs_step = steps["Always capture public Space logs"]
    cleanup_step = steps["Always remove public Space smoke container"]

    assert "scripts/export_hf_space.py" in export_run
    assert "local-inference-bench-gateway-space:rc" in build_run
    assert "--network none" in smoke_run
    assert "local-inference-space-smoke" in smoke_run
    assert "Config.User" in smoke_run
    assert 'test "$runtime_user" = "10001:10001"' in smoke_run
    assert "for attempt in $(seq 1 45)" in smoke_run
    assert "deadline=$((SECONDS + 55))" in smoke_run
    assert "sleep 1" in smoke_run
    assert "http://127.0.0.1:7860/_stcore/health" in smoke_run
    timeout_branch = """if [ "$healthy" -ne 1 ]; then
  docker logs local-inference-space-smoke >&2
  exit 1
fi"""
    assert timeout_branch in smoke_run
    assert logs_step["if"] == "always()"
    assert logs_step["run"] == "docker logs local-inference-space-smoke >&2 || true"
    assert cleanup_step["if"] == "always()"
    assert cleanup_step["run"] == "docker rm -f local-inference-space-smoke || true"

    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "space_remote_gate" not in workflow


def test_ci_space_artifact_scan_fails_closed() -> None:
    smoke_run = str(_workflow_steps()["Smoke public Space without network"]["run"])

    assert smoke_run.splitlines()[0] == "set -euo pipefail"
    assert "/app" in smoke_run
    for forbidden_suffix in (".db", ".sqlite", ".gguf", ".safetensors", ".onnx", ".jsonl"):
        assert forbidden_suffix in smoke_run
    assert 'forbidden="$(docker exec local-inference-space-smoke find /app' in smoke_run
    assert 'test -z "$forbidden"' in smoke_run
    assert "! docker exec" not in smoke_run
    assert "| grep ." not in smoke_run
