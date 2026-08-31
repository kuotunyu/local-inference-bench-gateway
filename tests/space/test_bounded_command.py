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


def _write_owned_tree(tmp_path: Path, marker: str) -> Path:
    tree_script = tmp_path / "owned_tree.py"
    tree_script.write_text(
        """from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import time

marker = sys.argv[1]
parent_mode = sys.argv[2]
grandchild = subprocess.Popen(
    [
        sys.executable,
        "-c",
        "from pathlib import Path; import sys,time; "
        "Path(sys.argv[1] + '-grandchild-ready').write_text(str(__import__('os').getpid()), encoding='utf-8'); "
        "time.sleep(60)",
        marker,
    ]
)
Path(marker + "-parent-ready").write_text(str(grandchild.pid), encoding="utf-8")
if parent_mode == "sleep":
    time.sleep(60)
while not Path(marker + "-grandchild-ready").is_file():
    time.sleep(0.01)
""",
        encoding="utf-8",
        newline="\n",
    )
    return tree_script


def _wait_for_file(path: Path, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.01)
    raise AssertionError(f"timed out waiting for {path}")


def _inject_first_root_wait_failure(
    monkeypatch: pytest.MonkeyPatch,
    ready_path: Path,
    failure: BaseException,
) -> None:
    def faulting_wait(*args: object, **kwargs: object) -> int:
        _wait_for_file(ready_path)
        raise failure

    monkeypatch.setattr(bounded_command, "_wait_for_tree", faulting_wait)


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

    def terminate_but_report_failure(
        process: subprocess.Popen[bytes],
        deadline_ns: int,
        windows_job: bounded_command._TreeOwner | None = None,
    ) -> bool:
        real_terminate(process, deadline_ns, windows_job)
        return False

    monkeypatch.setattr(bounded_command, "_terminate_tree", terminate_but_report_failure)

    result = bounded_command.run_bounded_command(
        [sys.executable, "-c", "import time; time.sleep(60)"], timeout_ms=500
    )

    assert result == bounded_command.EXIT_INTERNAL_ERROR


def test_unexpected_exception_after_spawn_cleans_owned_tree_and_returns_125(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "ordinary-exception-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)
    _inject_first_root_wait_failure(
        monkeypatch,
        Path(marker + "-grandchild-ready"),
        RuntimeError("synthetic wait failure"),
    )

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "sleep"], timeout_ms=2_000
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)
        time.sleep(0.05)

    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()
    assert _owned_process_ids(marker) == ()


def test_keyboard_interrupt_after_spawn_cleans_owned_tree_and_returns_130(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "keyboard-interrupt-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)
    _inject_first_root_wait_failure(
        monkeypatch,
        Path(marker + "-grandchild-ready"),
        KeyboardInterrupt(),
    )

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "sleep"], timeout_ms=2_000
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)
        time.sleep(0.05)

    assert result == 130
    assert residue == ()
    assert _owned_process_ids(marker) == ()


def test_cleanup_exception_uses_protected_fallback_and_returns_125(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "cleanup-exception-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)
    real_terminate = bounded_command._terminate_tree
    calls = 0

    def fail_first_cleanup(*args: object, **kwargs: object) -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("synthetic cleanup failure")
        return real_terminate(*args, **kwargs)

    monkeypatch.setattr(bounded_command, "_terminate_tree", fail_first_cleanup)

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "sleep"], timeout_ms=1_000
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)
        time.sleep(0.05)

    assert calls >= 2
    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()
    assert _owned_process_ids(marker) == ()


def test_root_exit_with_live_grandchild_times_out_and_cleans_owned_tree(
    tmp_path: Path,
) -> None:
    marker = str(tmp_path / "root-exit-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)

    started = time.monotonic()
    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "exit"],
            timeout_ms=1_500,
        )
        elapsed = time.monotonic() - started
        _wait_for_file(Path(marker + "-grandchild-ready"))
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)
        time.sleep(0.05)

    assert result == bounded_command.EXIT_TIMEOUT
    assert elapsed < 2.5
    assert residue == ()
    assert _owned_process_ids(marker) == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_job_assignment_failure_returns_125_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "assignment-failure-owned-marker")
    monkeypatch.setattr(
        bounded_command._KERNEL32,
        "AssignProcessToJobObject",
        lambda *_args: 0,
    )

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, "-c", "import time; time.sleep(60)", marker],
            timeout_ms=1_000,
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)

    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_job_query_failure_returns_125_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "query-failure-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)

    def fail_query(_job: object) -> int:
        raise OSError("synthetic job query failure")

    monkeypatch.setattr(bounded_command._WindowsJob, "active_processes", fail_query)

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "exit"],
            timeout_ms=2_000,
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)

    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_job_terminate_failure_returns_125_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "terminate-failure-owned-marker")
    tree_script = _write_owned_tree(tmp_path, marker)

    def fail_terminate(_job: object) -> None:
        raise OSError("synthetic job terminate failure")

    monkeypatch.setattr(bounded_command._WindowsJob, "terminate", fail_terminate)

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, str(tree_script), marker, "sleep"],
            timeout_ms=1_000,
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)

    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_closes_every_task_owned_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_close = bounded_command._close_windows_handle
    closed_handles: list[int] = []

    def record_close(handle: int) -> None:
        closed_handles.append(int(handle))
        real_close(handle)

    monkeypatch.setattr(bounded_command, "_close_windows_handle", record_close)

    result = bounded_command.run_bounded_command(
        [sys.executable, "-c", "raise SystemExit(0)"], timeout_ms=2_000
    )

    assert result == 0
    assert len(closed_handles) == 4
    assert len(set(closed_handles)) == 4


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_windows_handle_close_failure_returns_125_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = str(tmp_path / "handle-close-failure-owned-marker")
    real_close = bounded_command._close_windows_handle
    close_calls = 0

    def fail_first_close(handle: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(handle)
        if close_calls == 1:
            raise OSError("synthetic handle close failure")

    monkeypatch.setattr(bounded_command, "_close_windows_handle", fail_first_close)

    try:
        result = bounded_command.run_bounded_command(
            [sys.executable, "-c", "import time; time.sleep(60)", marker],
            timeout_ms=2_000,
        )
        residue = _owned_process_ids(marker)
    finally:
        remaining = _owned_process_ids(marker)
        _terminate_owned_pids(remaining)

    assert close_calls >= 4
    assert result == bounded_command.EXIT_INTERNAL_ERROR
    assert residue == ()


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
