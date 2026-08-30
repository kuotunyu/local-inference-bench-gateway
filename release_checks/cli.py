"""Run all local release checks with one command."""

from __future__ import annotations

import argparse
from pathlib import Path

from release_checks.ci_policy import verify_ci_policy
from release_checks.docker_policy import verify_docker_policy
from release_checks.documents import verify_documents
from release_checks.evidence import verify_evidence
from release_checks.publication import verify_publication
from release_checks.space_bundle import verify_space_source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-mode",
        action="store_true",
        help="audit an archive export without requiring Git metadata",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    checks = (
        ("publication", lambda: verify_publication(repo_root, export_mode=args.export_mode)),
        ("evidence", lambda: verify_evidence(repo_root)),
        ("documents", lambda: verify_documents(repo_root)),
        ("ci", lambda: verify_ci_policy(repo_root)),
        ("docker", lambda: verify_docker_policy(repo_root)),
        ("space", lambda: verify_space_source(repo_root)),
    )
    total = 0
    for name, check in checks:
        violations = check()
        if violations:
            total += len(violations)
            print(f"[{name}] FAIL ({len(violations)})")
            for violation in violations:
                print(f"  - {violation}")
        else:
            print(f"[{name}] OK")
    if total:
        print(f"release checks failed: {total} violation(s)")
        return 1
    print("release checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
