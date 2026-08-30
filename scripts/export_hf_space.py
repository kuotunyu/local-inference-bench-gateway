"""Export the committed, allowlisted Hugging Face Space bundle locally."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from release_checks.space_bundle import BundleExportError, export_space_bundle  # noqa: E402


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise BundleExportError("cannot inspect Git worktree")
    return result.stdout


def _clean_head_commit() -> str:
    if _git("status", "--porcelain"):
        raise BundleExportError("worktree must be clean")
    return _git("rev-parse", "HEAD").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        deployment_manifest = export_space_bundle(REPO_ROOT, args.destination, _clean_head_commit())
    except BundleExportError as error:
        parser.error(str(error))
    print(deployment_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
