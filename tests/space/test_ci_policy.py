from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

import yaml

BOUNDED_MODULE = "release_checks.bounded_command"
DIRECT_INTERPRETER = "./.venv/bin/python"


def _workflow_steps() -> dict[str, dict[str, object]]:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["verify"]["steps"]
    named_steps = {step["name"]: step for step in steps}
    assert len(named_steps) == len(steps), "CI step names must be unique"
    return named_steps


def _space_smoke_run() -> str:
    return str(_workflow_steps()["Smoke public Space without network"]["run"])


def _shortened_smoke_run(
    *,
    deadline_ms: int,
    minimum_probe_ms: int,
    probe_timeout_ms: int,
    sleep_ms: int,
    attempt_limit: int,
) -> str:
    smoke_run = _space_smoke_run()
    replacements = {
        "health_deadline_ms=55000": f"health_deadline_ms={deadline_ms}",
        "health_minimum_probe_ms=1000": f"health_minimum_probe_ms={minimum_probe_ms}",
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


def _run_workflow_shell(
    tmp_path: Path, shell_source: str, *, mode: str
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    fake_bin = tmp_path / "workflow-bin"
    fake_bin.mkdir()
    ledger = tmp_path / "docker-ledger.txt"
    _write_executable(
        fake_bin / "docker",
        """#!/usr/bin/env bash
set -eo pipefail
case "$1" in
  run)
    printf 'fake-container-id\\n'
    ;;
  inspect)
    printf '10001:10001\\n'
    ;;
  *)
    printf 'unbounded docker invocation: %s\\n' "$*" >&2
    exit 97
    ;;
esac
""",
    )
    fake_docker = tmp_path / "fake_docker.py"
    fake_docker.write_text(
        """from __future__ import annotations

import os
import sys
import time
from pathlib import Path

arguments = sys.argv[1:]
ledger = Path(os.environ["FAKE_DOCKER_LEDGER"])
with ledger.open("a", encoding="utf-8") as stream:
    stream.write(" ".join(arguments) + "\\n")
mode = os.environ["FAKE_DOCKER_MODE"]
operation = arguments[0] if arguments else ""
joined = " ".join(arguments)
if operation == "exec" and "_stcore/health" in joined:
    if mode == "health-fail":
        raise SystemExit(1)
    if mode in {"late", "hung"}:
        time.sleep(60 if mode == "hung" else 2)
elif operation == "exec" and "find" in arguments:
    if mode == "artifact-fail":
        raise SystemExit(2)
elif operation == "logs" and mode == "always-log-hang":
    time.sleep(60)
""",
        encoding="utf-8",
        newline="\n",
    )
    test_python = f'"{_bash_path(Path(sys.executable))}"'
    test_docker = f'"{_bash_path(fake_docker)}"'
    shell_source = shell_source.replace(DIRECT_INTERPRETER, test_python)
    shell_source = shell_source.replace("-- docker ", f"-- {test_python} {test_docker} ")
    environment = os.environ.copy()
    environment.update(
        {
            "FAKE_DOCKER_LEDGER": str(ledger),
            "FAKE_DOCKER_MODE": mode,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    prefixed_source = f'export PATH="{_bash_path(fake_bin)}:$PATH"\n{shell_source}'
    result = subprocess.run(
        [_bash_executable(), "-c", prefixed_source],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )
    ledger_lines = ledger.read_text(encoding="utf-8").splitlines() if ledger.exists() else []
    return result, ledger_lines


def test_ci_wires_every_bounded_space_command_and_preserves_cleanup_order() -> None:
    steps = _workflow_steps()
    export_run = str(steps["Export public Space bundle"]["run"])
    build_run = str(steps["Build non-root public Space image"]["run"])
    smoke_run = str(steps["Smoke public Space without network"]["run"])
    logs_step = steps["Always capture public Space logs"]
    cleanup_step = steps["Always remove public Space smoke container"]
    wrapper = f"{DIRECT_INTERPRETER} -m {BOUNDED_MODULE}"

    assert "scripts/export_hf_space.py" in export_run
    assert "local-inference-bench-gateway-space:rc" in build_run
    assert "--network none" in smoke_run
    assert "Config.User" in smoke_run
    assert 'test "$runtime_user" = "10001:10001"' in smoke_run
    assert "http://127.0.0.1:7860/_stcore/health" in smoke_run
    assert f'{wrapper} --timeout-ms "$bounded_probe_ms" -- docker exec' in smoke_run
    assert smoke_run.count(f"{wrapper} --timeout-ms 5000 -- docker logs") == 2
    assert f"{wrapper} --timeout-ms 5000 -- docker exec" in smoke_run
    assert "timeout --" not in smoke_run
    assert 'if [ "$completed_us" -le "$deadline_us" ]; then' in smoke_run
    assert smoke_run.index(f"{wrapper} --timeout-ms") < smoke_run.index('completed_us="$(now_us)"')
    assert smoke_run.index('completed_us="$(now_us)"') < smoke_run.index("healthy=1")

    assert logs_step["if"] == "always()"
    assert logs_step["run"] == (
        f"{wrapper} --timeout-ms 5000 -- docker logs local-inference-space-smoke >&2 || true"
    )
    assert cleanup_step["if"] == "always()"
    assert cleanup_step["run"] == (
        f"{wrapper} --timeout-ms 10000 -- docker rm -f local-inference-space-smoke || true"
    )
    step_names = list(steps)
    assert step_names.index("Always capture public Space logs") < step_names.index(
        "Always remove public Space smoke container"
    )

    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    bounded_lines = [line for line in workflow.splitlines() if BOUNDED_MODULE in line]
    assert len(bounded_lines) == 6
    assert all(DIRECT_INTERPRETER in line for line in bounded_lines)
    assert all("uv run" not in line for line in bounded_lines)
    assert "space_remote_gate" not in workflow


def test_ci_space_health_accepts_an_on_time_success(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=5_000,
        minimum_probe_ms=10,
        probe_timeout_ms=3_000,
        sleep_ms=10,
        attempt_limit=3,
    )

    started = time.monotonic()
    result, ledger = _run_workflow_shell(tmp_path, smoke_run, mode="on-time")
    elapsed = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    assert elapsed < 5.0
    assert sum("_stcore/health" in line for line in ledger) == 1
    assert sum(" find " in line for line in ledger) == 1


def test_ci_space_health_and_failure_logs_fail_closed(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=5_000,
        minimum_probe_ms=10,
        probe_timeout_ms=1_000,
        sleep_ms=10,
        attempt_limit=2,
    )

    result, ledger = _run_workflow_shell(tmp_path, smoke_run, mode="health-fail")

    assert result.returncode != 0
    assert sum("_stcore/health" in line for line in ledger) == 2
    assert sum(line.startswith("logs ") for line in ledger) == 1


def test_ci_space_health_rejects_a_late_real_child(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=1_800,
        minimum_probe_ms=100,
        probe_timeout_ms=1_500,
        sleep_ms=10,
        attempt_limit=1,
    )

    started = time.monotonic()
    result, ledger = _run_workflow_shell(tmp_path, smoke_run, mode="late")
    elapsed = time.monotonic() - started

    assert result.returncode != 0
    assert elapsed < 3.0
    assert sum("_stcore/health" in line for line in ledger) == 1
    assert sum(line.startswith("logs ") for line in ledger) == 1


def test_ci_space_health_bounds_a_hung_real_child(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=1_800,
        minimum_probe_ms=100,
        probe_timeout_ms=1_500,
        sleep_ms=10,
        attempt_limit=1,
    )

    started = time.monotonic()
    result, ledger = _run_workflow_shell(tmp_path, smoke_run, mode="hung")
    elapsed = time.monotonic() - started

    assert result.returncode != 0
    assert elapsed < 3.0
    assert sum("_stcore/health" in line for line in ledger) == 1


def test_ci_space_artifact_scan_and_logs_fail_closed(tmp_path: Path) -> None:
    smoke_run = _shortened_smoke_run(
        deadline_ms=5_000,
        minimum_probe_ms=10,
        probe_timeout_ms=3_000,
        sleep_ms=10,
        attempt_limit=3,
    )

    result, ledger = _run_workflow_shell(tmp_path, smoke_run, mode="artifact-fail")

    assert result.returncode != 0
    assert sum(" find " in line for line in ledger) == 1
    assert sum(line.startswith("logs ") for line in ledger) == 1


def test_ci_always_log_timeout_cannot_block_the_following_cleanup_step(tmp_path: Path) -> None:
    steps = _workflow_steps()
    shell_source = "\n".join(
        (
            str(steps["Always capture public Space logs"]["run"]),
            str(steps["Always remove public Space smoke container"]["run"]),
        )
    )
    shell_source = shell_source.replace("--timeout-ms 5000", "--timeout-ms 1000")
    shell_source = shell_source.replace("--timeout-ms 10000", "--timeout-ms 1500")

    started = time.monotonic()
    result, ledger = _run_workflow_shell(tmp_path, shell_source, mode="always-log-hang")
    elapsed = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    assert elapsed < 3.5
    assert len(ledger) == 2
    assert ledger[0].startswith("logs local-inference-space-smoke")
    assert ledger[1].startswith("rm -f local-inference-space-smoke")


def test_ci_space_artifact_scan_fails_closed() -> None:
    smoke_run = _space_smoke_run()

    assert smoke_run.splitlines()[0] == "set -euo pipefail"
    assert "/app" in smoke_run
    for forbidden_suffix in (".db", ".sqlite", ".gguf", ".safetensors", ".onnx", ".jsonl"):
        assert forbidden_suffix in smoke_run
    assert 'if ! forbidden="$(./.venv/bin/python -m release_checks.bounded_command' in smoke_run
    assert 'test -z "$forbidden"' in smoke_run
    assert "! docker exec" not in smoke_run
    assert "| grep ." not in smoke_run
