"""Run one direct child command inside a fail-closed process-tree deadline."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

EXIT_TIMEOUT = 124
EXIT_INTERNAL_ERROR = 125
EXIT_CANNOT_EXECUTE = 126
EXIT_NOT_FOUND = 127
_NS_PER_MS = 1_000_000


def _remaining_seconds(deadline_ns: int) -> float:
    return max(0, deadline_ns - time.monotonic_ns()) / 1_000_000_000


def _wait_until(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
    remaining = _remaining_seconds(deadline_ns)
    if remaining <= 0:
        return process.poll() is not None
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        return False
    return True


def _taskkill_path() -> Path:
    system_root = os.environ.get("SystemRoot")
    if not system_root:
        raise OSError("SystemRoot is unavailable")
    path = Path(system_root) / "System32" / "taskkill.exe"
    if not path.is_file():
        raise OSError("taskkill.exe is unavailable")
    return path


def _terminate_windows_tree(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
    if process.poll() is not None:
        return True
    remaining = _remaining_seconds(deadline_ns)
    if remaining <= 0:
        process.kill()
        return False
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            [
                str(_taskkill_path()),
                "/PID",
                str(process.pid),
                "/T",
                "/F",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=remaining,
            check=False,
            shell=False,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            process.kill()
            _wait_until(process, deadline_ns)
        return False
    if result.returncode != 0:
        if process.poll() is not None:
            return True
        process.kill()
        _wait_until(process, deadline_ns)
        return False
    if _wait_until(process, deadline_ns):
        return True
    if process.poll() is None:
        process.kill()
    return False


def _terminate_posix_tree(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
    if process.poll() is not None:
        return True
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return process.poll() is not None
    except OSError:
        if process.poll() is None:
            process.kill()
            _wait_until(process, deadline_ns)
        return False
    return _wait_until(process, deadline_ns)


def _terminate_tree(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
    if os.name == "nt":
        return _terminate_windows_tree(process, deadline_ns)
    return _terminate_posix_tree(process, deadline_ns)


def _normalized_exit_code(returncode: int) -> int:
    if returncode < 0:
        return min(255, 128 + abs(returncode))
    return min(255, returncode)


def _kill_budget_ns(timeout_ms: int) -> int:
    budget_ms = min(500, max(25, timeout_ms // 4))
    budget_ms = min(budget_ms, max(1, timeout_ms // 2))
    return budget_ms * _NS_PER_MS


def run_bounded_command(command: Sequence[str], *, timeout_ms: int) -> int:
    """Run one argv command and bound its owned process tree by ``timeout_ms``."""
    if (
        timeout_ms <= 0
        or not command
        or any(not isinstance(item, str) or not item for item in command)
    ):
        print("bounded-command: invalid command configuration", file=sys.stderr)
        return EXIT_INTERNAL_ERROR
    started_ns = time.monotonic_ns()
    deadline_ns = started_ns + timeout_ms * _NS_PER_MS
    active_deadline_ns = deadline_ns - _kill_budget_ns(timeout_ms)
    popen_options: dict[str, object] = {"shell": False}
    if os.name == "nt":
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_options["start_new_session"] = True
    try:
        process = subprocess.Popen(list(command), **popen_options)
    except FileNotFoundError:
        print("bounded-command: child executable was not found", file=sys.stderr)
        return EXIT_NOT_FOUND
    except PermissionError:
        print("bounded-command: child executable cannot be executed", file=sys.stderr)
        return EXIT_CANNOT_EXECUTE
    except OSError as error:
        print(f"bounded-command: child spawn failed: {type(error).__name__}", file=sys.stderr)
        return EXIT_INTERNAL_ERROR

    timed_out = False
    try:
        active_remaining = _remaining_seconds(active_deadline_ns)
        if active_remaining <= 0:
            timed_out = True
        else:
            try:
                returncode = process.wait(timeout=active_remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
            else:
                if time.monotonic_ns() <= active_deadline_ns:
                    return _normalized_exit_code(returncode)
                timed_out = True
    except KeyboardInterrupt:
        terminated = _terminate_tree(process, deadline_ns)
        return 130 if terminated else EXIT_INTERNAL_ERROR

    if timed_out:
        terminated = _terminate_tree(process, deadline_ns)
        if not terminated:
            print("bounded-command: process-tree teardown failed", file=sys.stderr)
            return EXIT_INTERNAL_ERROR
        print(f"bounded-command: timed out after {timeout_ms} ms", file=sys.stderr)
        return EXIT_TIMEOUT
    return EXIT_INTERNAL_ERROR


def _parse_cli(argv: Sequence[str]) -> tuple[int, list[str]] | None:
    if len(argv) < 4 or argv[0] != "--timeout-ms" or argv[2] != "--":
        print(
            "bounded-command: expected --timeout-ms <positive-int> -- <argv...>",
            file=sys.stderr,
        )
        return None
    try:
        timeout_ms = int(argv[1], 10)
    except ValueError:
        timeout_ms = 0
    if timeout_ms <= 0:
        print("bounded-command: timeout-ms must be a positive integer", file=sys.stderr)
        return None
    command = list(argv[3:])
    if not command or any(not item for item in command):
        print("bounded-command: child argv must be non-empty", file=sys.stderr)
        return None
    return timeout_ms, command


def main(argv: Sequence[str] | None = None) -> int:
    parsed = _parse_cli(list(sys.argv[1:] if argv is None else argv))
    if parsed is None:
        return EXIT_INTERNAL_ERROR
    timeout_ms, command = parsed
    return run_bounded_command(command, timeout_ms=timeout_ms)


if __name__ == "__main__":
    raise SystemExit(main())
