"""Load committed benchmark aggregates and verify their published digests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.models import BenchmarkEvidence


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _digest(path: Path) -> str:
    raw = path.read_bytes()
    if path.suffix.lower() in {".csv", ".json"}:
        raw = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _verification_warnings(results_dir: Path, provenance: dict[str, Any]) -> dict[str, str]:
    warnings: dict[str, str] = {}
    for artifact in provenance.get("artifacts", []):
        relative = Path(str(artifact.get("path", "")))
        parts = relative.parts
        if "results" in parts:
            relative = Path(*parts[parts.index("results") + 1 :])
        key = relative.as_posix()
        local_path = results_dir / relative
        if not local_path.is_file():
            warnings[key] = "artifact_missing"
            continue
        expected = artifact.get("sha256")
        if isinstance(expected, str) and _digest(local_path) != expected:
            warnings[key] = "digest_mismatch"
    return warnings


def load_benchmark_evidence(results_dir: Path) -> BenchmarkEvidence:
    provenance = _read_json(results_dir / "provenance.json", {})
    warnings = _verification_warnings(results_dir, provenance)
    required = [
        "concurrency_summary.csv",
        "prefill_summary.csv",
        "gateway_overhead.json",
        "claims.json",
    ]
    for filename in required:
        if not (results_dir / filename).is_file():
            warnings.setdefault(filename, "artifact_missing")
    return BenchmarkEvidence(
        concurrency=_read_csv(results_dir / "concurrency_summary.csv"),
        prefill=_read_csv(results_dir / "prefill_summary.csv"),
        overhead=_read_json(results_dir / "gateway_overhead.json", {}),
        provenance=provenance,
        claims=_read_json(results_dir / "claims.json", {}),
        kv_cache_off=_read_json(results_dir / "lmstudio_concurrency_boundary_scan.json", []),
        kv_cache_on=_read_json(
            results_dir / "lmstudio_concurrency_boundary_scan_unified_kv_on.json", []
        ),
        warnings=warnings,
    )
