"""Create the deterministic, allowlisted public Space bundle."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

SPACE_ID = "steven0226/local-inference-bench-gateway"
SOURCE_REPOSITORY = "kuotunyu/local-inference-bench-gateway"
_SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}")
_MANIFEST_PATH = PurePosixPath("space/bundle-manifest.json")
_EVIDENCE_MANIFEST_PATH = PurePosixPath("bench/results/provenance.json")


class BundleManifestError(ValueError):
    """Raised when the source allowlist is unsafe or malformed."""


class BundleExportError(ValueError):
    """Raised when an allowlisted bundle cannot be safely exported."""


@dataclass(frozen=True)
class BundleEntry:
    source: PurePosixPath
    destination: PurePosixPath


def _safe_path(value: object, *, source: bool) -> PurePosixPath:
    error = "source escapes repository" if source else "destination escapes bundle"
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleManifestError(error)
    path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or ".." in path.parts
        or path == PurePosixPath(".")
    ):
        raise BundleManifestError(error)
    return path


def _repo_path(repo_root: Path, relative: PurePosixPath, *, source: bool) -> Path:
    root = repo_root.resolve()
    path = (root / Path(*relative.parts)).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        message = "source escapes repository" if source else "destination escapes bundle"
        raise BundleManifestError(message) from error
    return path


def load_bundle_manifest(repo_root: Path) -> tuple[BundleEntry, ...]:
    """Load the explicit bundle allowlist while containing every path."""
    manifest_path = _repo_path(repo_root, _MANIFEST_PATH, source=True)
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = document["files"]
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as error:
        raise BundleManifestError("invalid bundle manifest") from error
    if not isinstance(entries, list):
        raise BundleManifestError("invalid bundle manifest")

    seen_destinations: set[PurePosixPath] = set()
    bundle_entries: list[BundleEntry] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise BundleManifestError("invalid bundle manifest")
        source = _safe_path(entry.get("source"), source=True)
        destination = _safe_path(entry.get("destination"), source=False)
        _repo_path(repo_root, source, source=True)
        if destination in seen_destinations:
            raise BundleManifestError("duplicate destination")
        seen_destinations.add(destination)
        bundle_entries.append(BundleEntry(source=source, destination=destination))
    return tuple(bundle_entries)


def _ensure_empty_destination(destination: Path) -> None:
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise BundleExportError("destination must be empty")


def _source_file(repo_root: Path, source: PurePosixPath) -> Path:
    path = _repo_path(repo_root, source, source=True)
    if not path.is_file():
        raise BundleExportError("missing source")
    return path


def _bundle_path(bundle_root: Path, relative: PurePosixPath) -> Path:
    root = bundle_root.resolve()
    target = (root / Path(*relative.parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise BundleManifestError("destination escapes bundle") from error
    return target


def export_space_bundle(repo_root: Path, destination: Path, source_commit: str) -> Path:
    """Copy the allowlisted Space bundle and return its deployment manifest."""
    if not _SOURCE_COMMIT.fullmatch(source_commit):
        raise BundleExportError("invalid source commit")
    _ensure_empty_destination(destination)
    entries = load_bundle_manifest(repo_root)
    sources = [
        (entry, _source_file(repo_root, entry.source), _bundle_path(destination, entry.destination))
        for entry in entries
    ]
    manifest_source = _source_file(repo_root, _MANIFEST_PATH)
    evidence_source = _source_file(repo_root, _EVIDENCE_MANIFEST_PATH)

    destination.mkdir(parents=True, exist_ok=True)
    for _entry, source, target in sources:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    deployment_manifest = {
        "schema_version": 1,
        "space_id": SPACE_ID,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "export_manifest_sha256": hashlib.sha256(manifest_source.read_bytes()).hexdigest(),
        "evidence_manifest_sha256": hashlib.sha256(evidence_source.read_bytes()).hexdigest(),
    }
    deployment_path = destination / "deployment-manifest.json"
    deployment_path.write_text(
        json.dumps(deployment_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return deployment_path
