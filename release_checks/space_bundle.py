"""Create the deterministic, allowlisted public Space bundle."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

import yaml

from release_checks.publication import verify_publication
from release_checks.space_imports import verify_public_import_boundary

SPACE_ID = "steven0226/local-inference-bench-gateway"
SOURCE_REPOSITORY = "kuotunyu/local-inference-bench-gateway"
_SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}")
_MANIFEST_PATH = PurePosixPath("space/bundle-manifest.json")
_EVIDENCE_MANIFEST_PATH = PurePosixPath("bench/results/provenance.json")
_DEPLOYMENT_MANIFEST_PATH = PurePosixPath("deployment-manifest.json")
_DEPLOYMENT_KEYS = {
    "schema_version",
    "space_id",
    "source_repository",
    "source_commit",
    "export_manifest_sha256",
    "evidence_manifest_sha256",
}
_CONTROL_MANIFESTS = {
    "bench/results/claims.json",
    "bench/results/provenance.json",
}
_EVIDENCE_ARTIFACT_PATHS = {
    "bench/results/concurrency_summary.csv",
    "bench/results/gateway_overhead.json",
    "bench/results/lmstudio_concurrency_boundary_scan.json",
    "bench/results/lmstudio_concurrency_boundary_scan_unified_kv_on.json",
    "bench/results/lmstudio_unified_kv_cache_comparison.png",
    "bench/results/prefill_summary.csv",
    "bench/results/prefill_time_vs_prompt_length.png",
    "bench/results/prompts/prompt_2000.json",
    "bench/results/prompts/prompt_8000.json",
    "bench/results/throughput_vs_concurrency.png",
    "bench/results/ttft_vs_concurrency.png",
    "bench/results/vram_usage.png",
}
_REQUIRED_DEPENDENCIES = (
    "streamlit==1.61.1",
    "pandas==3.0.5",
    "altair==6.2.2",
)
_TEXT_EVIDENCE_SUFFIXES = {".csv", ".json"}
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GPU_CONFIGURATION = re.compile(
    r"(?:NVIDIA|CUDA)_VISIBLE_DEVICES|(?:^|\s)--gpus(?:\s|=)|"
    r"\b(?:cuda|nvidia-container-runtime)\b",
    re.IGNORECASE | re.MULTILINE,
)
_CANONICAL_HEALTHCHECK = """--interval=10s --timeout=3s --start-period=10s --retries=6 CMD ["python", "-c", "import urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:7860/_stcore/health', timeout=2).read()"]"""
_CANONICAL_CMD = (
    '["streamlit", "run", "space/app.py", "--server.address=0.0.0.0", '
    '"--server.port=7860", "--server.headless=true"]'
)
_CANONICAL_SOURCE_URL = "https://github.com/kuotunyu/local-inference-bench-gateway"
_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))")


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


def _parse_bundle_manifest(repo_root: Path, manifest_bytes: bytes) -> tuple[BundleEntry, ...]:
    try:
        document = json.loads(manifest_bytes.decode("utf-8"))
        entries = document["files"]
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
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


def load_bundle_manifest(repo_root: Path) -> tuple[BundleEntry, ...]:
    """Load the explicit bundle allowlist while containing every path."""
    manifest_path = _repo_path(repo_root, _MANIFEST_PATH, source=True)
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise BundleManifestError("invalid bundle manifest") from error
    return _parse_bundle_manifest(repo_root, manifest_bytes)


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


def _read_text(path: Path, label: str, violations: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        violations.append(f"cannot read {label}")
        return ""


def _read_json(path: Path, label: str, violations: list[str]) -> object | None:
    text = _read_text(path, label, violations)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        violations.append(f"invalid {label}")
        return None


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )


def _commit_exists(repo_root: Path, source_commit: str) -> bool:
    return _git(repo_root, "cat-file", "-e", f"{source_commit}^{{commit}}").returncode == 0


def _committed_bytes(repo_root: Path, source_commit: str, relative: PurePosixPath) -> bytes | None:
    result = _git(repo_root, "show", f"{source_commit}:{relative.as_posix()}")
    return result.stdout if result.returncode == 0 else None


def _actual_bundle_paths(bundle_root: Path, violations: list[str]) -> set[str]:
    if not bundle_root.is_dir():
        violations.append("bundle root is not a directory")
        return set()
    actual: set[str] = set()
    try:
        candidates = sorted(bundle_root.rglob("*"))
    except OSError:
        violations.append("cannot enumerate bundle files")
        return set()
    for path in candidates:
        relative = path.relative_to(bundle_root).as_posix()
        if path.is_symlink():
            violations.append(f"bundle symlink is forbidden: {relative}")
        if path.is_file():
            actual.add(relative)
    return actual


def _deployment_document(bundle_root: Path, violations: list[str]) -> dict[str, object] | None:
    document = _read_json(
        bundle_root / Path(*_DEPLOYMENT_MANIFEST_PATH.parts),
        "deployment manifest",
        violations,
    )
    if document is None:
        return None
    if not isinstance(document, dict):
        violations.append("deployment manifest must be an object")
        return None
    if set(document) != _DEPLOYMENT_KEYS:
        violations.append("deployment manifest keys do not match the required schema")
    if type(document.get("schema_version")) is not int or document.get("schema_version") != 1:
        violations.append("deployment manifest schema_version must be 1")
    if document.get("space_id") != SPACE_ID:
        violations.append(f"Space ID must be {SPACE_ID}")
    if document.get("source_repository") != SOURCE_REPOSITORY:
        violations.append(f"source repository must be {SOURCE_REPOSITORY}")
    for key in ("export_manifest_sha256", "evidence_manifest_sha256"):
        value = document.get(key)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            violations.append(f"invalid deployment digest: {key}")
    return document


def _verify_deployment_digests(
    repo_root: Path,
    deployment: dict[str, object],
    source_commit: str,
    violations: list[str],
) -> None:
    declarations = (
        ("export_manifest_sha256", _MANIFEST_PATH),
        ("evidence_manifest_sha256", _EVIDENCE_MANIFEST_PATH),
    )
    for key, source in declarations:
        source_bytes = _committed_bytes(repo_root, source_commit, source)
        if source_bytes is None:
            violations.append(f"missing source commit file: {source.as_posix()}")
            continue
        if deployment.get(key) != hashlib.sha256(source_bytes).hexdigest():
            violations.append(f"deployment digest mismatch: {key}")


def _verify_source_bytes(
    repo_root: Path,
    bundle_root: Path,
    entries: tuple[BundleEntry, ...],
    source_commit: str,
    violations: list[str],
) -> None:
    for entry in entries:
        bundle_path = bundle_root.joinpath(*entry.destination.parts)
        if not bundle_path.is_file():
            continue
        source_bytes = _committed_bytes(repo_root, source_commit, entry.source)
        if source_bytes is None:
            violations.append(f"missing source commit file: {entry.source.as_posix()}")
            continue
        try:
            bundle_bytes = bundle_path.read_bytes()
        except OSError:
            violations.append(f"cannot read bundle file: {entry.destination.as_posix()}")
            continue
        if bundle_bytes != source_bytes:
            label = (
                "evidence byte mismatch"
                if entry.destination.as_posix().startswith("bench/results/")
                else "source byte mismatch"
            )
            violations.append(f"{label}: {entry.destination.as_posix()}")


def _evidence_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in _TEXT_EVIDENCE_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _verify_evidence_bundle(bundle_root: Path, violations: list[str]) -> None:
    provenance = _read_json(
        bundle_root / "bench" / "results" / "provenance.json",
        "evidence manifest",
        violations,
    )
    if not isinstance(provenance, dict):
        return
    controls = provenance.get("control_manifests")
    if (
        not isinstance(controls, list)
        or len(controls) != 2
        or not all(isinstance(item, str) for item in controls)
        or set(controls) != _CONTROL_MANIFESTS
    ):
        violations.append("evidence control manifests must be exactly two unique control manifests")
        controls = []
    artifacts = provenance.get("artifacts")
    if not isinstance(artifacts, list):
        violations.append("evidence artifacts must be a list")
        return

    seen_artifacts: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            violations.append("evidence artifact declaration must be an object")
            continue
        relative = artifact.get("path")
        digest = artifact.get("sha256")
        if not isinstance(relative, str):
            violations.append("evidence artifact path must be a string")
            continue
        try:
            safe_relative = _safe_path(relative, source=False)
        except BundleManifestError:
            violations.append("evidence artifact path escapes bundle")
            continue
        display = safe_relative.as_posix()
        if display in seen_artifacts:
            violations.append(f"duplicate evidence artifact: {display}")
        seen_artifacts.add(display)
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            violations.append(f"invalid evidence digest: {display}")
            continue
        path = bundle_root.joinpath(*safe_relative.parts)
        if not path.is_file():
            continue
        try:
            actual_digest = _evidence_digest(path)
        except OSError:
            violations.append(f"cannot read evidence artifact: {display}")
            continue
        if actual_digest != digest:
            violations.append(f"evidence byte mismatch: {display}")

    if (
        len(artifacts) != 12
        or len(seen_artifacts) != 12
        or seen_artifacts != _EVIDENCE_ARTIFACT_PATHS
    ):
        violations.append(
            "evidence artifact declarations must be exactly 12 unique canonical paths"
        )


def _docker_instructions(dockerfile: str) -> list[tuple[str, str]]:
    instructions: list[tuple[str, str]] = []
    pending = ""
    for raw_line in dockerfile.splitlines():
        stripped = raw_line.strip()
        if not pending and (not stripped or stripped.startswith("#")):
            continue
        pending = f"{pending} {stripped}".strip()
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        match = re.fullmatch(r"([A-Za-z]+)\s+(.+)", pending)
        if match:
            instructions.append((match.group(1).upper(), match.group(2).strip()))
        pending = ""
    if pending:
        instructions.append(("INVALID", pending))
    return instructions


def _copy_sources(argument: str) -> list[str] | None:
    remaining = argument.strip()
    while remaining.startswith("--"):
        parts = remaining.split(maxsplit=1)
        if len(parts) != 2:
            return None
        remaining = parts[1]
    if remaining.startswith("["):
        try:
            values = json.loads(remaining)
        except json.JSONDecodeError:
            return None
        if (
            not isinstance(values, list)
            or len(values) < 2
            or not all(isinstance(value, str) for value in values)
        ):
            return None
        return values[:-1]
    try:
        values = shlex.split(remaining, posix=True)
    except ValueError:
        return None
    return values[:-1] if len(values) >= 2 else None


def _is_context_root(source: str) -> bool:
    return PurePosixPath(source.replace("\\", "/")) == PurePosixPath(".")


def _verify_dockerfile(bundle_root: Path, violations: list[str]) -> None:
    dockerfile = _read_text(bundle_root / "Dockerfile", "Space Dockerfile", violations)
    if not dockerfile:
        return
    instructions = _docker_instructions(dockerfile)
    from_arguments = [argument for name, argument in instructions if name == "FROM"]
    if from_arguments != ["python:3.12.13-slim-bookworm"]:
        violations.append("Space base image must be python:3.12.13-slim-bookworm")
    user_arguments = [argument for name, argument in instructions if name == "USER"]
    if not user_arguments or user_arguments[-1] != "10001:10001":
        violations.append("Space runtime user must be 10001:10001")
    for name, argument in instructions:
        if name not in {"COPY", "ADD"}:
            continue
        sources = _copy_sources(argument)
        if sources is None:
            violations.append("invalid Docker COPY/ADD instruction")
        elif any(_is_context_root(source) for source in sources):
            violations.append("broad Docker COPY/ADD is forbidden")
    active_dockerfile = "\n".join(f"{name} {argument}" for name, argument in instructions)
    if _GPU_CONFIGURATION.search(active_dockerfile):
        violations.append("GPU configuration is forbidden in the Space Dockerfile")
    if re.search(r"(?<!\d)9000(?!\d)", active_dockerfile):
        violations.append("gateway port 9000 is forbidden in the Space Dockerfile")
    exposed = [argument for name, argument in instructions if name == "EXPOSE"]
    if exposed != ["7860"]:
        violations.append("Space Dockerfile must expose only port 7860")
    healthchecks = [argument for name, argument in instructions if name == "HEALTHCHECK"]
    if healthchecks != [_CANONICAL_HEALTHCHECK]:
        violations.append("Space Dockerfile must have exactly one canonical active HEALTHCHECK")
    commands = [argument for name, argument in instructions if name == "CMD"]
    if not commands or commands[-1] != _CANONICAL_CMD:
        violations.append("Space Dockerfile final CMD must start the canonical Streamlit app")


def _verify_requirements(
    lock_bytes: bytes | None, bundle_root: Path, violations: list[str]
) -> None:
    requirements = _read_text(
        bundle_root / "requirements.txt", "Space requirements", violations
    ).splitlines()
    if requirements != list(_REQUIRED_DEPENDENCIES):
        violations.append("Space dependencies must be exactly pinned")
    if lock_bytes is None:
        violations.append("cannot verify Space dependencies against source-commit uv.lock")
        return
    try:
        lock = tomllib.loads(lock_bytes.decode("utf-8"))
        locked = {
            package["name"]: package["version"]
            for package in lock["package"]
            if package.get("name") in {"streamlit", "pandas", "altair"}
        }
    except (KeyError, TypeError, UnicodeError, tomllib.TOMLDecodeError):
        violations.append("cannot verify Space dependencies against source-commit uv.lock")
        return
    if {f"{name}=={version}" for name, version in locked.items()} != set(_REQUIRED_DEPENDENCIES):
        violations.append("Space dependency pins do not match uv.lock")


def _verify_card(bundle_root: Path, violations: list[str]) -> None:
    card = _read_text(bundle_root / "README.md", "Space card", violations)
    if not card:
        return
    parts = card.split("---", maxsplit=2)
    try:
        metadata = yaml.safe_load(parts[1]) if len(parts) == 3 and not parts[0].strip() else None
    except yaml.YAMLError:
        metadata = None
    if not isinstance(metadata, dict):
        violations.append("invalid Space card metadata")
    else:
        if metadata.get("sdk") != "docker":
            violations.append("Space card sdk must be docker")
        if metadata.get("app_port") != 7860:
            violations.append("Space card app_port must be 7860")
        if metadata.get("license") != "mit":
            violations.append("Space card license must be mit")
    destinations = [
        match.group("angle") or match.group("plain") for match in _MARKDOWN_LINK.finditer(card)
    ]
    for target in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        if target not in destinations:
            violations.append(f"Space card must link {target}")
    if _CANONICAL_SOURCE_URL not in destinations:
        violations.append("Space card must link the canonical source repository")
    for destination in destinations:
        hostname = urlsplit(destination).hostname
        if hostname and (
            hostname.casefold() == "hf.space" or hostname.casefold().endswith(".hf.space")
        ):
            violations.append("Space card must not hard-code an ephemeral hf.space URL")
            break


def verify_space_bundle(repo_root: Path, bundle_root: Path) -> list[str]:
    """Return fail-closed policy violations for an exported public Space bundle."""
    repo_root = repo_root.resolve()
    bundle_root = bundle_root.resolve()
    violations: list[str] = []
    actual_paths = _actual_bundle_paths(bundle_root, violations)
    if _DEPLOYMENT_MANIFEST_PATH.as_posix() not in actual_paths:
        violations.append(f"missing required bundle file: {_DEPLOYMENT_MANIFEST_PATH.as_posix()}")

    violations.extend(verify_publication(bundle_root, export_mode=True))
    deployment = _deployment_document(bundle_root, violations)
    source_commit = deployment.get("source_commit") if deployment else None
    lock_bytes: bytes | None = None
    if not isinstance(source_commit, str) or not _SOURCE_COMMIT.fullmatch(source_commit):
        violations.append("invalid source revision")
    elif not _commit_exists(repo_root, source_commit):
        violations.append("source revision is unavailable in the repository")
    else:
        assert deployment is not None
        manifest_bytes = _committed_bytes(repo_root, source_commit, _MANIFEST_PATH)
        if manifest_bytes is None:
            violations.append(f"missing source commit file: {_MANIFEST_PATH.as_posix()}")
        else:
            try:
                entries = _parse_bundle_manifest(repo_root, manifest_bytes)
            except BundleManifestError as error:
                violations.append(f"invalid source-commit bundle manifest: {error}")
            else:
                expected_paths = {entry.destination.as_posix() for entry in entries}
                expected_paths.add(_DEPLOYMENT_MANIFEST_PATH.as_posix())
                for relative in sorted(expected_paths - actual_paths):
                    violations.append(f"missing required bundle file: {relative}")
                for relative in sorted(actual_paths - expected_paths):
                    violations.append(f"undeclared bundle file: {relative}")
                _verify_source_bytes(repo_root, bundle_root, entries, source_commit, violations)
        _verify_deployment_digests(repo_root, deployment, source_commit, violations)
        lock_bytes = _committed_bytes(repo_root, source_commit, PurePosixPath("uv.lock"))

    _verify_evidence_bundle(bundle_root, violations)
    _verify_dockerfile(bundle_root, violations)
    _verify_requirements(lock_bytes, bundle_root, violations)
    _verify_card(bundle_root, violations)
    violations.extend(verify_public_import_boundary(bundle_root))
    return list(dict.fromkeys(violations))


def verify_space_source(repo_root: Path) -> list[str]:
    """Export the current local revision and verify its complete public boundary."""
    repo_root = repo_root.resolve()
    result = _git(repo_root, "rev-parse", "HEAD")
    if result.returncode:
        return ["cannot determine source revision"]
    try:
        source_commit = result.stdout.decode("ascii").strip()
    except UnicodeDecodeError:
        return ["cannot determine source revision"]
    if not _SOURCE_COMMIT.fullmatch(source_commit):
        return ["cannot determine source revision"]
    try:
        with tempfile.TemporaryDirectory(prefix="space-bundle-check-") as temporary:
            bundle_root = Path(temporary) / "bundle"
            export_space_bundle(repo_root, bundle_root, source_commit)
            return verify_space_bundle(repo_root, bundle_root)
    except (BundleExportError, BundleManifestError, OSError) as error:
        return [f"cannot export Space source: {type(error).__name__}"]
