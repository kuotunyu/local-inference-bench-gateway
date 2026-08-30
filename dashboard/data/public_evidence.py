"""Public integrity state derived from committed benchmark evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard.data.benchmark_repository import load_benchmark_evidence
from dashboard.models import BenchmarkEvidence

DECLARED_PUBLIC_ARTIFACTS = 12


@dataclass(frozen=True)
class PublicEvidenceState:
    evidence: BenchmarkEvidence
    declared_artifacts: int
    verified_artifacts: int
    complete: bool


def _warning_key(artifact: dict[str, Any]) -> str | None:
    path = artifact.get("path")
    if not isinstance(path, str):
        return None
    normalized = path.replace("\\", "/")
    prefix = "bench/results/"
    return normalized[len(prefix) :] if normalized.startswith(prefix) else normalized


def load_public_evidence(results_dir: Path) -> PublicEvidenceState:
    """Load verified evidence and expose its public completeness without re-reading files."""
    evidence = load_benchmark_evidence(results_dir)
    artifacts = evidence.provenance.get("artifacts")
    if (
        "provenance.json" in evidence.warnings
        or not isinstance(artifacts, list)
        or not artifacts
        or not all(isinstance(artifact, dict) for artifact in artifacts)
    ):
        return PublicEvidenceState(evidence, 0, 0, False)

    declared_artifacts = len(artifacts)
    verified_artifacts = sum(
        _warning_key(artifact) not in evidence.warnings for artifact in artifacts
    )
    complete = (
        declared_artifacts == DECLARED_PUBLIC_ARTIFACTS
        and verified_artifacts == DECLARED_PUBLIC_ARTIFACTS
        and not evidence.warnings
    )
    return PublicEvidenceState(
        evidence=evidence,
        declared_artifacts=declared_artifacts,
        verified_artifacts=verified_artifacts,
        complete=complete,
    )
