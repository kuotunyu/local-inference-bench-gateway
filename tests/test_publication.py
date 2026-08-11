from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from release_checks.publication import verify_publication

AUTHOR_NAME = "kuotunyu"
AUTHOR_EMAIL = "61350295+kuotunyu@users.noreply.github.com"


def _run(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


def _repo(tmp_path: Path, files: dict[str, str | bytes], message: str = "test fixture") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(repo, "init", "--initial-branch=main")
    _run(repo, "config", "user.name", AUTHOR_NAME)
    _run(repo, "config", "user.email", AUTHOR_EMAIL)
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    _run(repo, "add", "-A")
    _run(repo, "commit", "-m", message)
    return repo


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        (".env", "TOKEN=value", "environment file"),
        ("bench/results/raw/request.jsonl", "{}", "raw result"),
        ("data/gateway.db", b"SQLite", "runtime database"),
        ("models/model.gguf", b"GGUF", "model weight"),
        ("engines/server.exe", b"MZ", "engine binary"),
        ("large.bin", b"x" * (5 * 1024 * 1024), "file is at least 5 MiB"),
        ("notes.txt", "C:" + "\\Users\\alice\\private", "Windows user path"),
        (("PL" + "AN.md"), "internal", "private document name"),
        ("token.txt", "ghp_" + "A" * 36, "secret-like token"),
    ],
    ids=(
        "environment",
        "raw-result",
        "database",
        "model-weight",
        "engine-binary",
        "large-file",
        "windows-user-path",
        "private-document",
        "secret-token",
    ),
)
def test_publication_rejects_forbidden_files_and_content(tmp_path, relative, content, expected):
    repo = _repo(tmp_path, {relative: content})

    violations = verify_publication(repo)

    assert any(expected in violation for violation in violations), violations


def test_publication_rejects_nonignored_untracked_file(tmp_path):
    repo = _repo(tmp_path, {"README.md": "safe"})
    (repo / ".env.local").write_text("TOKEN=value", encoding="utf-8")

    violations = verify_publication(repo)

    assert any("environment file" in violation for violation in violations)


def test_publication_rejects_disallowed_author(tmp_path):
    repo = _repo(tmp_path, {"README.md": "safe"})
    _run(repo, "config", "user.email", "other@example.com")
    (repo / "other.txt").write_text("second", encoding="utf-8")
    _run(repo, "add", "other.txt")
    _run(repo, "commit", "-m", "other author")

    violations = verify_publication(repo)

    assert any("disallowed author" in violation for violation in violations)


def test_publication_rejects_coauthor_trailer(tmp_path):
    trailer = "Co-authored" + "-by: Other <other@example.com>"
    repo = _repo(tmp_path, {"README.md": "safe"}, message=f"fixture\n\n{trailer}")

    violations = verify_publication(repo)

    assert any("co-author trailer" in violation for violation in violations)


def test_publication_allows_expected_public_examples(tmp_path):
    repo = _repo(
        tmp_path,
        {
            ".env.example": "GATEWAY_API_KEY=change-me",
            "README.md": "http://127.0.0.1:9000",
            "bench/results/chart.png": b"\x89PNG\r\n\x1a\nsmall",
        },
    )

    assert verify_publication(repo) == []
