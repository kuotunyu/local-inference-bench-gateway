"""Audit public files and reachable Git metadata for accidental disclosure."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REQUIRED_AUTHOR_NAME = "kuotunyu"
REQUIRED_AUTHOR_EMAIL = "61350295+kuotunyu@users.noreply.github.com"
MAX_PUBLIC_FILE_BYTES = 5 * 1024 * 1024
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
ENGINE_BINARY_SUFFIXES = {".exe", ".dll", ".so", ".dylib"}
ARCHIVE_SUFFIXES = {".7z", ".rar"}
PRIVATE_DOCUMENT_NAMES = {("pl" + "an.md"), ("interview" + "_prep.md")}
WINDOWS_USER_PATH = re.compile(r"[A-Za-z]:" + r"[\\/]+Users[\\/]+", re.IGNORECASE)
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
BINARY_SCAN_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf"}


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _candidate_files(repo_root: Path, export_mode: bool) -> list[Path]:
    if export_mode or not (repo_root / ".git").exists():
        return sorted(
            path
            for path in repo_root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(repo_root).parts
        )

    result = _git(
        repo_root,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    if result.returncode != 0:
        return []
    return sorted(repo_root / relative for relative in result.stdout.split("\0") if relative)


def _path_violations(relative: Path, size: int) -> list[str]:
    violations: list[str] = []
    lower_parts = tuple(part.lower() for part in relative.parts)
    name = relative.name.lower()
    suffix = relative.suffix.lower()
    display = relative.as_posix()

    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        violations.append(f"environment file is public: {display}")
    if "raw" in lower_parts or suffix == ".jsonl":
        violations.append(f"raw result or log is public: {display}")
    if suffix in DATABASE_SUFFIXES:
        violations.append(f"runtime database is public: {display}")
    if suffix == ".gguf":
        violations.append(f"model weight is public: {display}")
    if suffix in ENGINE_BINARY_SUFFIXES or "engines" in lower_parts:
        violations.append(f"engine binary is public: {display}")
    if suffix in ARCHIVE_SUFFIXES:
        violations.append(f"binary archive is public: {display}")
    if name in PRIVATE_DOCUMENT_NAMES:
        violations.append(f"private document name is public: {display}")
    if size >= MAX_PUBLIC_FILE_BYTES:
        violations.append(f"file is at least 5 MiB: {display}")
    return violations


def _content_violations(relative: Path, path: Path) -> list[str]:
    if path.suffix.lower() in BINARY_SCAN_SUFFIXES or path.stat().st_size > 1024 * 1024:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []

    display = relative.as_posix()
    violations: list[str] = []
    if WINDOWS_USER_PATH.search(text):
        violations.append(f"Windows user path found in: {display}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            violations.append(f"secret-like token found in: {display}")
            break
    return violations


def _history_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    revs = _git(repo_root, "rev-list", "--all")
    if revs.returncode != 0:
        return ["cannot inspect Git history"]
    for commit in (line for line in revs.stdout.splitlines() if line):
        metadata = _git(repo_root, "show", "-s", "--format=%an%x00%ae%x00%B", commit)
        if metadata.returncode != 0:
            violations.append(f"cannot inspect commit metadata: {commit}")
            continue
        name, email, message = metadata.stdout.split("\0", 2)
        if name != REQUIRED_AUTHOR_NAME or email != REQUIRED_AUTHOR_EMAIL:
            violations.append(f"disallowed author in commit {commit}")
        if "co-authored-by:" in message.lower():
            violations.append(f"co-author trailer in commit {commit}")

    merges = _git(repo_root, "rev-list", "--all", "--min-parents=2")
    if merges.returncode == 0 and merges.stdout.strip():
        violations.append("merge commit found in release history")
    return violations


def verify_publication(repo_root: Path, *, export_mode: bool = False) -> list[str]:
    repo_root = repo_root.resolve()
    violations: list[str] = []
    candidates = _candidate_files(repo_root, export_mode)
    if not candidates:
        violations.append("no public files found")
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root)
        violations.extend(_path_violations(relative, path.stat().st_size))
        violations.extend(_content_violations(relative, path))
    if not export_mode and (repo_root / ".git").exists():
        violations.extend(_history_violations(repo_root))
    return violations
