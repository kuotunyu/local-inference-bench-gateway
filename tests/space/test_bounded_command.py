from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

import pytest

from release_checks import bounded_command
from release_checks.space_bundle import export_space_bundle
from release_checks.space_imports import public_import_closure


def _wrapper_cli(timeout_ms: int, command: list[str]) -> list[str]:
    return [
        sys.executable,
        "-m",
        "release_checks.bounded_command",
        "--timeout-ms",
        str(timeout_ms),
        "--",
        *command,
    ]


def _run_wrapper(timeout_ms: int, command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _wrapper_cli(timeout_ms, command),
        capture_output=True,
        text=True,
        timeout=max(3.0, timeout_ms / 1000 + 2.0),
        check=False,
    )


def _owned_process_ids(marker: str) -> tuple[int, ...]:
    if os.name == "nt":
        executable = shutil.which("powershell.exe") or shutil.which("pwsh")
        assert executable is not None
        environment = os.environ.copy()
        environment["TASK_OWNED_PROCESS_MARKER"] = marker
        result = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-Command",
                "$marker=$env:TASK_OWNED_PROCESS_MARKER; "
                "Get-CimInstance Win32_Process | Where-Object { "
                "$_.CommandLine -and $_.CommandLine.Contains($marker) } | "
                "ForEach-Object { $_.ProcessId }",
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        return tuple(
            sorted(int(line.strip()) for line in result.stdout.splitlines() if line.strip())
        )
    result = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    return tuple(
        sorted(
            int(line.strip().split(maxsplit=1)[0])
            for line in result.stdout.splitlines()
            if marker in line
        )
    )


def _terminate_owned_pids(process_ids: tuple[int, ...]) -> None:
    for process_id in process_ids:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process_id), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        else:
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                continue


def test_cli_propagates_child_output_and_exit_code() -> None:
    result = _run_wrapper(
        1_000,
        [
            sys.executable,
            "-c",
            "import sys; print('child-out'); print('child-err', file=sys.stderr); sys.exit(7)",
        ],
    )

    assert result.returncode == 7
    assert result.stdout == "child-out\n"
    assert result.stderr == "child-err\n"


def test_cli_returns_125_for_invalid_wrapper_configuration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "release_checks.bounded_command",
            "--timeout-ms",
            "0",
            "--",
            sys.executable,
        ],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )

    assert result.returncode == bounded_command.EXIT_INTERNAL_ERROR == 125
    assert "timeout-ms must be a positive integer" in result.stderr


def test_cli_returns_127_when_child_executable_is_missing() -> None:
    result = _run_wrapper(1_000, ["definitely-missing-bounded-command-executable"])

    assert result.returncode == 127
    assert "child executable was not found" in result.stderr


def test_cli_rejects_completion_after_the_active_deadline() -> None:
    result = _run_wrapper(
        1_500,
        [sys.executable, "-c", "import time; time.sleep(1.2)"],
    )

    assert result.returncode == bounded_command.EXIT_TIMEOUT == 124
    assert "timed out after 1500 ms" in result.stderr


def test_timeout_kills_term_ignoring_parent_and_grandchild_without_residue(
    tmp_path: Path,
) -> None:
    marker = str(tmp_path / "bounded-command-owned-marker")
    tree_script = tmp_path / "term_ignoring_tree.py"
    tree_script.write_text(
        """from __future__ import annotations
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

marker = sys.argv[1]
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
grandchild = subprocess.Popen(
    [
        sys.executable,
        "-c",
        "import signal,sys,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "open(sys.argv[1], 'w', encoding='utf-8').write('ready'); time.sleep(60)",
        marker + "-grandchild",
    ]
)
Path(marker + "-parent").write_text(str(os.getpid()), encoding="utf-8")
Path(marker + "-grandchild-pid").write_text(str(grandchild.pid), encoding="utf-8")
time.sleep(60)
""",
        encoding="utf-8",
        newline="\n",
    )

    started = time.monotonic()
    try:
        result = _run_wrapper(1_500, [sys.executable, str(tree_script), marker])
        elapsed = time.monotonic() - started
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)
        time.sleep(0.05)

    assert result.returncode == bounded_command.EXIT_TIMEOUT
    assert elapsed < 2.5
    assert residue == ()
    assert _owned_process_ids(marker) == ()


def test_teardown_failure_is_never_reported_as_an_ordinary_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_terminate = bounded_command._terminate_tree

    def terminate_but_report_failure(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
        real_terminate(process, deadline_ns)
        return False

    monkeypatch.setattr(bounded_command, "_terminate_tree", terminate_but_report_failure)

    result = bounded_command.run_bounded_command(
        [sys.executable, "-c", "import time; time.sleep(60)"], timeout_ms=500
    )

    assert result == bounded_command.EXIT_INTERNAL_ERROR


def test_bounded_command_helper_is_not_exported_or_publicly_reachable(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    export_space_bundle(Path.cwd(), bundle_root, "a" * 40)
    exported_files = {
        path.relative_to(bundle_root).as_posix()
        for path in bundle_root.rglob("*")
        if path.is_file()
    }

    assert len(exported_files) == 40
    assert "release_checks/bounded_command.py" not in exported_files
    assert PurePosixPath("release_checks/bounded_command.py") not in public_import_closure(
        bundle_root
    )
