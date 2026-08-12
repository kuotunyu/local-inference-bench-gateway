"""Load committed benchmark aggregates and verify their published digests."""

from __future__ import annotations

import hashlib
import json
import re
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


DISPLAYED_ARTIFACTS = {
    "concurrency_summary.csv",
    "prefill_summary.csv",
    "gateway_overhead.json",
    "lmstudio_concurrency_boundary_scan.json",
    "lmstudio_concurrency_boundary_scan_unified_kv_on.json",
}
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


def _local_artifact_path(results_dir: Path, raw_path: str) -> tuple[str, Path] | None:
    normalized = raw_path.replace("\\", "/")
    relative = Path(normalized)
    if (
        relative.is_absolute()
        or relative.drive
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return None
    parts = relative.parts
    if len(parts) >= 2 and parts[:2] == ("bench", "results"):
        relative = Path(*parts[2:])
    if not relative.parts:
        return None
    root = results_dir.resolve()
    local_path = (root / relative).resolve()
    try:
        local_path.relative_to(root)
    except ValueError:
        return None
    return relative.as_posix(), local_path


def _verification_warnings(
    results_dir: Path, provenance: dict[str, Any]
) -> tuple[dict[str, str], bool]:
    warnings: dict[str, str] = {}
    artifacts = provenance.get("artifacts", [])
    if not isinstance(artifacts, list) or not all(
        isinstance(artifact, dict) for artifact in artifacts
    ):
        return {"provenance.json": "invalid_or_missing_manifest"}, False
    manifest_valid = bool(artifacts)
    manifested: set[str] = set()
    for artifact in artifacts:
        raw_path = artifact.get("path")
        expected = artifact.get("sha256")
        key = str(raw_path or "manifest-entry")
        if not isinstance(raw_path, str) or not SHA256_PATTERN.fullmatch(str(expected or "")):
            warnings[key] = "invalid_manifest_entry"
            warnings["provenance.json"] = "invalid_manifest_entry"
            manifest_valid = False
            continue
        resolved = _local_artifact_path(results_dir, raw_path)
        if resolved is None:
            warnings[key] = "unsafe_artifact_path"
            warnings["provenance.json"] = "unsafe_artifact_path"
            manifest_valid = False
            continue
        key, local_path = resolved
        if key in manifested:
            warnings["provenance.json"] = "duplicate_artifact_path"
            manifest_valid = False
            continue
        manifested.add(key)
        if not local_path.is_file():
            warnings[key] = "artifact_missing"
            continue
        if _digest(local_path) != expected.lower():
            warnings[key] = "digest_mismatch"
    for filename in DISPLAYED_ARTIFACTS - manifested:
        warnings[filename] = "missing_from_manifest"
        manifest_valid = False
    if not manifest_valid:
        warnings.setdefault("provenance.json", "invalid_or_missing_manifest")
    return warnings, manifest_valid


def load_benchmark_evidence(results_dir: Path) -> BenchmarkEvidence:
    provenance = _read_json(results_dir / "provenance.json", {})
    if not isinstance(provenance, dict):
        provenance = {}
    warnings, manifest_valid = _verification_warnings(results_dir, provenance)
    artifacts = provenance.get("artifacts")
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or not all(isinstance(artifact, dict) for artifact in artifacts)
    ):
        warnings["provenance.json"] = "invalid_or_missing_manifest"
    required = [
        "concurrency_summary.csv",
        "prefill_summary.csv",
        "gateway_overhead.json",
        "claims.json",
        "provenance.json",
        "lmstudio_concurrency_boundary_scan.json",
        "lmstudio_concurrency_boundary_scan_unified_kv_on.json",
    ]
    for filename in required:
        if not (results_dir / filename).is_file():
            warnings.setdefault(filename, "artifact_missing")
    if not manifest_valid:
        for filename in required:
            if filename != "provenance.json" and (results_dir / filename).is_file():
                warnings.setdefault(filename, "unverified_without_manifest")
        provenance = {}

    concurrency = _read_csv(results_dir / "concurrency_summary.csv")
    prefill = _read_csv(results_dir / "prefill_summary.csv")
    overhead = _read_json(results_dir / "gateway_overhead.json", {})
    claims = _read_json(results_dir / "claims.json", {})
    kv_off_name = "lmstudio_concurrency_boundary_scan.json"
    kv_on_name = "lmstudio_concurrency_boundary_scan_unified_kv_on.json"
    kv_cache_off = _read_json(results_dir / kv_off_name, [])
    kv_cache_on = _read_json(results_dir / kv_on_name, [])

    if not isinstance(overhead, dict):
        warnings["gateway_overhead.json"] = "invalid_schema"
        overhead = {}
    if not isinstance(claims, dict):
        warnings["claims.json"] = "invalid_schema"
        claims = {}
    if not isinstance(kv_cache_off, list):
        warnings[kv_off_name] = "invalid_schema"
        kv_cache_off = []
    if not isinstance(kv_cache_on, list):
        warnings[kv_on_name] = "invalid_schema"
        kv_cache_on = []

    if "concurrency_summary.csv" in warnings:
        concurrency = pd.DataFrame()
    if "prefill_summary.csv" in warnings:
        prefill = pd.DataFrame()
    if "gateway_overhead.json" in warnings:
        overhead = {}
    if "claims.json" in warnings:
        claims = {}
    if kv_off_name in warnings:
        kv_cache_off = []
    if kv_on_name in warnings:
        kv_cache_on = []
    return BenchmarkEvidence(
        concurrency=concurrency,
        prefill=prefill,
        overhead=overhead,
        provenance=provenance,
        claims=claims,
        kv_cache_off=kv_cache_off,
        kv_cache_on=kv_cache_on,
        warnings=warnings,
    )
