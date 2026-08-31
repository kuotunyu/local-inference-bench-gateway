from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import time
from pathlib import Path

import yaml


def _workflow_steps() -> dict[str, dict[str, object]]:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["verify"]["steps"]
    named_steps = {step["name"]: step for step in steps}
    assert len(named_steps) == len(steps), "CI step names must be unique"
    return named_steps


def _space_smoke_run() -> str:
    return str(_workflow_steps()["Smoke public Space without network"]["run"])


def _shortened_smoke_run(
    *, deadline_ms: int, probe_timeout_ms: int, sleep_ms: int, attempt_limit: int
) -> str:
    smoke_run = _space_smoke_run()
    replacements = {
        "health_deadline_ms=55000": f"health_deadline_ms={deadline_ms}",
        "health_probe_timeout_ms=3000": f"health_probe_timeout_ms={probe_timeout_ms}",
        "health_sleep_ms=1000": f"health_sleep_ms={sleep_ms}",
        "health_attempt_limit=45": f"health_attempt_limit={attempt_limit}",
    }
    for original, replacement in replacements.items():
        assert smoke_run.count(original) == 1, f"missing exact CI default: {original}"
        smoke_run = smoke_run.replace(original, replacement)
    return smoke_run


def _bash_executable() -> str:
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    if os.name == "nt" and git_bash.is_file():
        return str(git_bash)
    executable = shutil.which("bash")
    assert executable is not None, "CI behavior contract requires Bash"
    return executable


def _bash_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved.as_posix()
    drive = resolved.drive.removesuffix(":").lower()
    return f"/{drive}{resolved.as_posix()[2:]}"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_smoke_contract(
    tmp_path: Path,
    smoke_run: str,
    *,
    delay_ms: int = 0,
    ignore_timeout: bool = False,
    force_timeout: bool = False,
) -> tuple[subprocess.CompletedProcess[str], float]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "docker",
        """#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  run)
    printf 'fake-container-id\\n'
    ;;
  inspect)
    printf '10001:10001\\n'
    ;;
  exec)
    if [[ "$*" == *"_stcore/health"* ]]; then
      delay_ms="${FAKE_HEALTH_DELAY_MS:-0}"
      if (( delay_ms > 0 )); then
        stamp="${EPOCHREALTIME/./}"
        started_us=$((10#$stamp))
        while :; do
          stamp="${EPOCHREALTIME/./}"
          current_us=$((10#$stamp))
          if (( current_us - started_us >= delay_ms * 1000 )); then break; fi
        done
      fi
    fi
    ;;
  logs)
    printf 'fake container logs\\n' >&2
    ;;
  *)
    printf 'unexpected fake docker command: %s\\n' "$*" >&2
    exit 97
    ;;
esac
""",
    )
    if ignore_timeout or force_timeout:
        timeout_behavior = 'exec "$@"' if ignore_timeout else "sleep 0.02\nexit 124"
        _write_executable(
            fake_bin / "timeout",
            f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "${{1:-}}" == "--foreground" ]]; then shift; fi
shift
{timeout_behavior}
""",
        )
    shell_source = f'export PATH="{_bash_path(fake_bin)}:$PATH"\n{smoke_run}'
    environment = os.environ.copy()
    environment.update(
        {
            "FAKE_HEALTH_DELAY_MS": str(delay_ms),
        }
    )
    started = time.monotonic()
    result = subprocess.run(
        [_bash_executable(), "-c", shell_source],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    return result, time.monotonic() - started


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
    defaults = {
        name: int(value)
        for name, value in re.findall(
            r"^(health_(?:deadline|probe_timeout|sleep)_ms|health_attempt_limit)=(\d+)$",
            smoke_run,
            re.MULTILINE,
        )
    }
    assert defaults == {
        "health_deadline_ms": 55_000,
        "health_probe_timeout_ms": 3_000,
        "health_sleep_ms": 1_000,
        "health_attempt_limit": 45,
    }
    assert 'for attempt in $(seq 1 "$health_attempt_limit")' in smoke_run
    assert "http://127.0.0.1:7860/_stcore/health" in smoke_run
    assert "timeout --foreground" in smoke_run
    assert 'if [ "$completed_us" -le "$deadline_us" ]; then' in smoke_run
    assert smoke_run.index("timeout --foreground") < smoke_run.index('completed_us="$(now_us)"')
    assert smoke_run.index('completed_us="$(now_us)"') < smoke_run.index("healthy=1")
    assert "if docker exec" not in smoke_run
    docker_exec_lines = [line.strip() for line in smoke_run.splitlines() if "docker exec" in line]
    assert len(docker_exec_lines) == 2
    assert all("timeout --foreground" in line for line in docker_exec_lines)
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


def test_ci_space_health_accepts_an_on_time_success(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=500, probe_timeout_ms=100, sleep_ms=10, attempt_limit=3
    )

    result, elapsed = _run_smoke_contract(tmp_path, smoke_run)

    assert result.returncode == 0, result.stderr
    assert elapsed < 1.5


def test_ci_space_health_rejects_a_late_success(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=100, probe_timeout_ms=500, sleep_ms=10, attempt_limit=1
    )

    result, elapsed = _run_smoke_contract(tmp_path, smoke_run, delay_ms=250, ignore_timeout=True)

    assert result.returncode != 0
    assert "fake container logs" in result.stderr
    assert elapsed < 1.5


def test_ci_space_health_bounds_each_hanging_child_process(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=250, probe_timeout_ms=50, sleep_ms=10, attempt_limit=45
    )

    result, elapsed = _run_smoke_contract(tmp_path, smoke_run, force_timeout=True)

    assert result.returncode != 0
    assert "fake container logs" in result.stderr
    assert elapsed < 1.5


def test_ci_space_artifact_scan_fails_closed() -> None:
    smoke_run = str(_workflow_steps()["Smoke public Space without network"]["run"])

    assert smoke_run.splitlines()[0] == "set -euo pipefail"
    assert "/app" in smoke_run
    for forbidden_suffix in (".db", ".sqlite", ".gguf", ".safetensors", ".onnx", ".jsonl"):
        assert forbidden_suffix in smoke_run
    assert (
        'forbidden="$(timeout --foreground 5s docker exec local-inference-space-smoke find /app'
        in smoke_run
    )
    assert 'test -z "$forbidden"' in smoke_run
    assert "! docker exec" not in smoke_run
    assert "| grep ." not in smoke_run
