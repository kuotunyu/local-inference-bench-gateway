from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from release_checks.space_bundle import (
    BundleExportError,
    BundleManifestError,
    export_space_bundle,
    load_bundle_manifest,
)


def relative_file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def expected_bundle_paths() -> set[str]:
    return {
        ".streamlit/config.toml",
        "Dockerfile",
        "EVAL_REPORT.md",
        "LICENSE",
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "bench/results/claims.json",
        "bench/results/concurrency_summary.csv",
        "bench/results/gateway_overhead.json",
        "bench/results/lmstudio_concurrency_boundary_scan.json",
        "bench/results/lmstudio_concurrency_boundary_scan_unified_kv_on.json",
        "bench/results/lmstudio_unified_kv_cache_comparison.png",
        "bench/results/prefill_summary.csv",
        "bench/results/prefill_time_vs_prompt_length.png",
        "bench/results/prompts/prompt_2000.json",
        "bench/results/prompts/prompt_8000.json",
        "bench/results/provenance.json",
        "bench/results/throughput_vs_concurrency.png",
        "bench/results/ttft_vs_concurrency.png",
        "bench/results/vram_usage.png",
        "bundle-manifest.json",
        "dashboard/__init__.py",
        "dashboard/charts.py",
        "dashboard/components.py",
        "dashboard/data/__init__.py",
        "dashboard/data/benchmark_repository.py",
        "dashboard/data/public_demo.py",
        "dashboard/data/public_evidence.py",
        "dashboard/metrics.py",
        "dashboard/models.py",
        "dashboard/theme.py",
        "dashboard/views/__init__.py",
        "dashboard/views/evidence.py",
        "dashboard/views/overview.py",
        "dashboard/views/reliability.py",
        "dashboard/views/requests.py",
        "dashboard/windows.py",
        "deployment-manifest.json",
        "requirements.txt",
        "space/app.py",
    }


def write_manifest(repo_root: Path, entries: list[dict[str, str]]) -> None:
    manifest = repo_root / "space" / "bundle-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"files": entries}), encoding="utf-8")


def make_minimal_repo(
    tmp_path: Path,
    manifest_bytes: bytes = b'{"files": [{"source": "payload.txt", "destination": "payload.txt"}]}',
) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "space").mkdir(parents=True)
    (repo_root / "bench" / "results").mkdir(parents=True)
    (repo_root / "payload.txt").write_bytes(b"payload\x00bytes")
    (repo_root / "space" / "bundle-manifest.json").write_bytes(manifest_bytes)
    (repo_root / "bench" / "results" / "provenance.json").write_bytes(b'{"origin":"test"}')
    return repo_root


def test_export_is_exact_deterministic_and_refuses_nonempty_destination(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    export_space_bundle(Path.cwd(), first, "a" * 40)
    export_space_bundle(Path.cwd(), second, "a" * 40)

    assert relative_file_bytes(first) == relative_file_bytes(second)
    assert set(relative_file_bytes(first)) == expected_bundle_paths()

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(BundleExportError, match="destination must be empty"):
        export_space_bundle(Path.cwd(), occupied, "b" * 40)
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "preserve"


def test_manifest_rejects_source_traversal(tmp_path: Path) -> None:
    repo_root = make_minimal_repo(tmp_path)
    write_manifest(repo_root, [{"source": "../secret", "destination": "secret"}])

    with pytest.raises(BundleManifestError, match="^source escapes repository$"):
        load_bundle_manifest(repo_root)


def test_manifest_rejects_destination_traversal(tmp_path: Path) -> None:
    repo_root = make_minimal_repo(tmp_path)
    write_manifest(repo_root, [{"source": "payload.txt", "destination": "../secret"}])

    with pytest.raises(BundleManifestError, match="^destination escapes bundle$"):
        load_bundle_manifest(repo_root)


def test_manifest_rejects_duplicate_destination(tmp_path: Path) -> None:
    repo_root = make_minimal_repo(tmp_path)
    write_manifest(
        repo_root,
        [
            {"source": "payload.txt", "destination": "README.md"},
            {"source": "space/bundle-manifest.json", "destination": "README.md"},
        ],
    )

    with pytest.raises(BundleManifestError, match="^duplicate destination$"):
        load_bundle_manifest(repo_root)


def test_export_rejects_missing_source(tmp_path: Path) -> None:
    repo_root = make_minimal_repo(tmp_path)
    write_manifest(repo_root, [{"source": "missing.txt", "destination": "missing.txt"}])

    with pytest.raises(BundleExportError, match="^missing source$"):
        export_space_bundle(repo_root, tmp_path / "bundle", "a" * 40)
    assert not (tmp_path / "bundle").exists()


def test_export_rejects_malformed_source_commit(tmp_path: Path) -> None:
    repo_root = make_minimal_repo(tmp_path)

    with pytest.raises(BundleExportError, match="^invalid source commit$"):
        export_space_bundle(repo_root, tmp_path / "bundle", "A" * 40)
    assert not (tmp_path / "bundle").exists()


def test_export_manifest_digest_uses_source_bytes(tmp_path: Path) -> None:
    lf_manifest = b'{\n  "files": [{"source": "payload.txt", "destination": "payload.txt"}]\n}\n'
    crlf_manifest = lf_manifest.replace(b"\n", b"\r\n")
    lf_repo = make_minimal_repo(tmp_path / "lf", lf_manifest)
    crlf_repo = make_minimal_repo(tmp_path / "crlf", crlf_manifest)

    lf_path = export_space_bundle(lf_repo, tmp_path / "lf-bundle", "a" * 40)
    crlf_path = export_space_bundle(crlf_repo, tmp_path / "crlf-bundle", "a" * 40)
    lf_deployment = json.loads(lf_path.read_text(encoding="utf-8"))
    crlf_deployment = json.loads(crlf_path.read_text(encoding="utf-8"))

    assert lf_deployment["export_manifest_sha256"] == hashlib.sha256(lf_manifest).hexdigest()
    assert crlf_deployment["export_manifest_sha256"] == hashlib.sha256(crlf_manifest).hexdigest()
    assert lf_deployment["export_manifest_sha256"] != crlf_deployment["export_manifest_sha256"]
