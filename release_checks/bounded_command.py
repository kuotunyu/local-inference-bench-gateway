"""Run one direct child command inside a fail-closed process-tree deadline."""

from __future__ import annotations

import errno
import os
import signal
import subprocess
import sys
import time
from typing import Protocol, Sequence

EXIT_TIMEOUT = 124
EXIT_INTERNAL_ERROR = 125
EXIT_CANNOT_EXECUTE = 126
EXIT_NOT_FOUND = 127
_NS_PER_MS = 1_000_000
_TREE_POLL_SECONDS = 0.01


class _TreeOwner(Protocol):
    def active_processes(self) -> int: ...

    def terminate(self) -> None: ...

    def close(self) -> None: ...


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _CREATE_SUSPENDED = 0x00000004
    _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _PROCESS_TERMINATE = 0x0001
    _PROCESS_SET_QUOTA = 0x0100
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _TH32CS_SNAPTHREAD = 0x00000004
    _THREAD_SUSPEND_RESUME = 0x0002
    _THREAD_QUERY_LIMITED_INFORMATION = 0x0800
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _RESUME_THREAD_FAILED = 0xFFFFFFFF

    class _JobObjectBasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JobObjectExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobObjectBasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _JobObjectBasicAccountingInformation(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    class _ThreadEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _KERNEL32.CreateJobObjectW.restype = wintypes.HANDLE
    _KERNEL32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _KERNEL32.SetInformationJobObject.restype = wintypes.BOOL
    _KERNEL32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    _KERNEL32.QueryInformationJobObject.restype = wintypes.BOOL
    _KERNEL32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _KERNEL32.TerminateJobObject.restype = wintypes.BOOL
    _KERNEL32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _KERNEL32.OpenProcess.restype = wintypes.HANDLE
    _KERNEL32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _KERNEL32.AssignProcessToJobObject.restype = wintypes.BOOL
    _KERNEL32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    _KERNEL32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _KERNEL32.Thread32First.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ThreadEntry32),
    ]
    _KERNEL32.Thread32First.restype = wintypes.BOOL
    _KERNEL32.Thread32Next.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ThreadEntry32),
    ]
    _KERNEL32.Thread32Next.restype = wintypes.BOOL
    _KERNEL32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _KERNEL32.OpenThread.restype = wintypes.HANDLE
    _KERNEL32.ResumeThread.argtypes = [wintypes.HANDLE]
    _KERNEL32.ResumeThread.restype = wintypes.DWORD
    _KERNEL32.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL32.CloseHandle.restype = wintypes.BOOL

    def _windows_error(message: str) -> OSError:
        error_code = ctypes.get_last_error()
        return OSError(error_code, message)

    def _close_windows_handle(handle: int) -> None:
        if not _KERNEL32.CloseHandle(handle):
            raise _windows_error("CloseHandle failed")

    class _WindowsJob:
        def __init__(self) -> None:
            handle = _KERNEL32.CreateJobObjectW(None, None)
            if not handle:
                raise _windows_error("CreateJobObjectW failed")
            self._handle: int | None = handle
            information = _JobObjectExtendedLimitInformation()
            information.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not _KERNEL32.SetInformationJobObject(
                handle,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(information),
                ctypes.sizeof(information),
            ):
                try:
                    _close_windows_handle(handle)
                finally:
                    self._handle = None
                raise _windows_error("SetInformationJobObject failed")

        def _required_handle(self) -> int:
            if self._handle is None:
                raise OSError("job handle is closed")
            return self._handle

        def assign_and_resume(self, process: subprocess.Popen[bytes]) -> None:
            handles: list[int] = []
            pending_error: BaseException | None = None
            try:
                process_handle = _KERNEL32.OpenProcess(
                    _PROCESS_TERMINATE | _PROCESS_SET_QUOTA | _PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    process.pid,
                )
                if not process_handle:
                    raise _windows_error("OpenProcess failed")
                handles.append(process_handle)
                if not _KERNEL32.AssignProcessToJobObject(self._required_handle(), process_handle):
                    raise _windows_error("AssignProcessToJobObject failed")

                snapshot = _KERNEL32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
                if snapshot == _INVALID_HANDLE_VALUE:
                    raise _windows_error("CreateToolhelp32Snapshot failed")
                handles.append(snapshot)
                entry = _ThreadEntry32()
                entry.dwSize = ctypes.sizeof(entry)
                thread_ids: list[int] = []
                has_entry = _KERNEL32.Thread32First(snapshot, ctypes.byref(entry))
                while has_entry:
                    if entry.th32OwnerProcessID == process.pid:
                        thread_ids.append(entry.th32ThreadID)
                    entry.dwSize = ctypes.sizeof(entry)
                    has_entry = _KERNEL32.Thread32Next(snapshot, ctypes.byref(entry))
                if len(thread_ids) != 1:
                    raise OSError("suspended child initial thread is unavailable")

                thread_handle = _KERNEL32.OpenThread(
                    _THREAD_SUSPEND_RESUME | _THREAD_QUERY_LIMITED_INFORMATION,
                    False,
                    thread_ids[0],
                )
                if not thread_handle:
                    raise _windows_error("OpenThread failed")
                handles.append(thread_handle)
                previous_suspend_count = _KERNEL32.ResumeThread(thread_handle)
                if previous_suspend_count != 1:
                    if previous_suspend_count == _RESUME_THREAD_FAILED:
                        raise _windows_error("ResumeThread failed")
                    raise OSError("suspended child resume count is invalid")
            except BaseException as error:
                pending_error = error
            finally:
                for handle in reversed(handles):
                    try:
                        _close_windows_handle(handle)
                    except BaseException as error:
                        if pending_error is None:
                            pending_error = error
            if pending_error is not None:
                raise pending_error

        def active_processes(self) -> int:
            information = _JobObjectBasicAccountingInformation()
            if not _KERNEL32.QueryInformationJobObject(
                self._required_handle(),
                _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                ctypes.byref(information),
                ctypes.sizeof(information),
                None,
            ):
                raise _windows_error("QueryInformationJobObject failed")
            return int(information.ActiveProcesses)

        def terminate(self) -> None:
            if not _KERNEL32.TerminateJobObject(self._required_handle(), 1):
                raise _windows_error("TerminateJobObject failed")

        def close(self) -> None:
            handle = self._required_handle()
            try:
                _close_windows_handle(handle)
            finally:
                self._handle = None


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


def _posix_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as error:
        if error.errno == errno.ESRCH:
            return False
        if error.errno == errno.EPERM:
            return True
        raise
    return True


def _tree_active(
    process: subprocess.Popen[bytes],
    windows_job: _TreeOwner | None,
) -> bool:
    if os.name == "nt":
        if windows_job is None:
            return process.poll() is None
        return windows_job.active_processes() > 0
    return _posix_group_exists(process.pid)


def _wait_for_tree(
    process: subprocess.Popen[bytes],
    deadline_ns: int,
    windows_job: _TreeOwner | None,
) -> int | None:
    remaining = _remaining_seconds(deadline_ns)
    if remaining <= 0:
        return None
    try:
        returncode = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        return None
    while _tree_active(process, windows_job):
        remaining = _remaining_seconds(deadline_ns)
        if remaining <= 0:
            return None
        time.sleep(min(_TREE_POLL_SECONDS, remaining))
    return returncode


def _terminate_windows_tree(
    process: subprocess.Popen[bytes],
    deadline_ns: int,
    windows_job: _TreeOwner | None,
) -> bool:
    if windows_job is not None:
        windows_job.terminate()
        while windows_job.active_processes() > 0:
            remaining = _remaining_seconds(deadline_ns)
            if remaining <= 0:
                return False
            time.sleep(min(_TREE_POLL_SECONDS, remaining))
    if process.poll() is None:
        process.kill()
    return _wait_until(process, deadline_ns)


def _terminate_posix_tree(process: subprocess.Popen[bytes], deadline_ns: int) -> bool:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as error:
        if error.errno != errno.ESRCH:
            raise
    while _posix_group_exists(process.pid):
        remaining = _remaining_seconds(deadline_ns)
        if remaining <= 0:
            return False
        time.sleep(min(_TREE_POLL_SECONDS, remaining))
    return _wait_until(process, deadline_ns)


def _terminate_tree(
    process: subprocess.Popen[bytes],
    deadline_ns: int,
    windows_job: _TreeOwner | None = None,
) -> bool:
    if os.name == "nt":
        return _terminate_windows_tree(process, deadline_ns, windows_job)
    return _terminate_posix_tree(process, deadline_ns)


def _emergency_terminate_tree(
    process: subprocess.Popen[bytes],
    deadline_ns: int,
    windows_job: _TreeOwner | None,
) -> bool:
    if os.name == "nt":
        if windows_job is not None:
            try:
                windows_job.terminate()
            except BaseException:
                pass
        if process.poll() is None:
            try:
                process.kill()
            except BaseException:
                return False
        return _wait_until(process, deadline_ns)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except BaseException:
        if process.poll() is None:
            try:
                process.kill()
            except BaseException:
                return False
    while _posix_group_exists(process.pid):
        remaining = _remaining_seconds(deadline_ns)
        if remaining <= 0:
            return False
        time.sleep(min(_TREE_POLL_SECONDS, remaining))
    return _wait_until(process, deadline_ns)


def _safe_terminate_tree(
    process: subprocess.Popen[bytes],
    deadline_ns: int,
    windows_job: _TreeOwner | None,
) -> tuple[bool, bool]:
    cleanup_fault = False
    for _attempt in range(2):
        try:
            if _terminate_tree(process, deadline_ns, windows_job):
                return True, cleanup_fault
            cleanup_fault = True
        except BaseException:
            cleanup_fault = True
    try:
        return _emergency_terminate_tree(process, deadline_ns, windows_job), True
    except BaseException:
        return False, True


def _close_owner(windows_job: _TreeOwner | None) -> bool:
    if windows_job is None:
        return True
    try:
        windows_job.close()
    except BaseException:
        return False
    return True


def _normalized_exit_code(returncode: int) -> int:
    if returncode < 0:
        return min(255, 128 + abs(returncode))
    return min(255, returncode)


def _kill_budget_ns(timeout_ms: int) -> int:
    budget_ms = min(500, max(25, timeout_ms // 4))
    budget_ms = min(budget_ms, max(1, timeout_ms // 2))
    return budget_ms * _NS_PER_MS


def run_bounded_command(command: Sequence[str], *, timeout_ms: int) -> int:
    """Run one argv command and bound its owned process tree by timeout_ms."""
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
    process: subprocess.Popen[bytes] | None = None
    windows_job: _TreeOwner | None = None
    result = EXIT_INTERNAL_ERROR
    tree_known_clean = False
    timed_out = False
    internal_failure: str | None = None

    try:
        popen_options: dict[str, object] = {"shell": False}
        if os.name == "nt":
            windows_job = _WindowsJob()
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_SUSPENDED
        else:
            popen_options["start_new_session"] = True
        process = subprocess.Popen(list(command), **popen_options)
        if os.name == "nt":
            assert isinstance(windows_job, _WindowsJob)
            windows_job.assign_and_resume(process)

        returncode = _wait_for_tree(process, active_deadline_ns, windows_job)
        if returncode is None:
            timed_out = True
        else:
            tree_known_clean = True
            result = _normalized_exit_code(returncode)
    except FileNotFoundError:
        if process is None:
            print("bounded-command: child executable was not found", file=sys.stderr)
            result = EXIT_NOT_FOUND
        else:
            internal_failure = "FileNotFoundError"
    except PermissionError:
        if process is None:
            print("bounded-command: child executable cannot be executed", file=sys.stderr)
            result = EXIT_CANNOT_EXECUTE
        else:
            internal_failure = "PermissionError"
    except KeyboardInterrupt:
        result = 130
    except Exception as error:
        internal_failure = type(error).__name__
    finally:
        cleanup_fault = False
        terminated = True
        if process is not None and not tree_known_clean:
            terminated, cleanup_fault = _safe_terminate_tree(process, deadline_ns, windows_job)
            if timed_out and terminated and not cleanup_fault:
                result = EXIT_TIMEOUT
            elif result == 130 and terminated and not cleanup_fault:
                pass
            else:
                result = EXIT_INTERNAL_ERROR
        owner_closed = _close_owner(windows_job)
        if not terminated or cleanup_fault:
            print("bounded-command: process-tree teardown failed", file=sys.stderr)
            result = EXIT_INTERNAL_ERROR
        if not owner_closed:
            print("bounded-command: process-tree owner close failed", file=sys.stderr)
            result = EXIT_INTERNAL_ERROR

    if internal_failure is not None:
        print(
            f"bounded-command: internal failure: {internal_failure}",
            file=sys.stderr,
        )
        result = EXIT_INTERNAL_ERROR
    if timed_out and result == EXIT_TIMEOUT:
        print(f"bounded-command: timed out after {timeout_ms} ms", file=sys.stderr)
    return result


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
