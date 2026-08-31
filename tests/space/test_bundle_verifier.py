from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from release_checks.space_bundle import (
    SPACE_ID,
    export_space_bundle,
    verify_space_bundle,
    verify_space_source,
)
from tests.space.test_exporter import expected_bundle_paths

Mutation = Callable[[Path], None]
CANONICAL_SOURCE_URL = "https://github.com/kuotunyu/local-inference-bench-gateway"
CANONICAL_SOURCE_LINK = f"[`kuotunyu/local-inference-bench-gateway`]({CANONICAL_SOURCE_URL})"


def _head_revision(repo_root: Path = Path.cwd()) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def export_valid_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    export_space_bundle(Path.cwd(), bundle, _head_revision())
    return bundle


def clone_source_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(Path.cwd()), str(repo_root)],
        capture_output=True,
        text=True,
        check=True,
    )
    return repo_root


def commit_file(repo_root: Path, relative: str) -> None:
    for args in (
        ("config", "user.name", "Bundle verifier test"),
        ("config", "user.email", "bundle-verifier@example.invalid"),
        ("add", "--", relative),
        ("commit", "-m", "hostile manifest fixture"),
    ):
        subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )


def _write(bundle: Path, relative: str, content: str | bytes) -> None:
    path = bundle / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def add_unlisted_file(bundle: Path) -> None:
    _write(bundle, "notes.txt", "not declared")


def add_environment_file(bundle: Path) -> None:
    _write(bundle, ".env", "GATEWAY_API_KEY=value")


def add_database_file(bundle: Path) -> None:
    _write(bundle, "data/gateway.sqlite3", b"SQLite format 3\x00")


def add_raw_jsonl(bundle: Path) -> None:
    _write(bundle, "bench/results/raw/requests.jsonl", "{}\n")


def add_model_weight(bundle: Path) -> None:
    _write(bundle, "models/model.gguf", b"GGUF")


def add_large_file(bundle: Path) -> None:
    _write(bundle, "large.bin", b"x" * (5 * 1024 * 1024))


def add_secret_token(bundle: Path) -> None:
    _write(bundle, "token.txt", "ghp_" + "A" * 36)


def remove_license(bundle: Path) -> None:
    (bundle / "LICENSE").unlink()


def tamper_evidence(bundle: Path) -> None:
    path = bundle / "bench/results/gateway_overhead.json"
    path.write_bytes(path.read_bytes() + b"\n")


def make_root_user(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(
        path.read_text(encoding="utf-8").replace("USER 10001:10001", "USER root"),
        encoding="utf-8",
    )


def add_broad_copy(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(path.read_text(encoding="utf-8") + "\nCOPY . .\n", encoding="utf-8")


def add_json_broad_copy(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(
        path.read_text(encoding="utf-8") + '\nCOPY [".", "/app"]\n',
        encoding="utf-8",
    )


def add_relative_broad_copy(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(path.read_text(encoding="utf-8") + "\nCOPY ./ /shadow\n", encoding="utf-8")


def add_relative_broad_add(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(path.read_text(encoding="utf-8") + "\nADD ./ /shadow\n", encoding="utf-8")


def add_json_broad_add(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(
        path.read_text(encoding="utf-8") + '\nADD ["./", "/shadow"]\n',
        encoding="utf-8",
    )


def add_gpu_term(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(
        path.read_text(encoding="utf-8") + "\nENV NVIDIA_VISIBLE_DEVICES=all\n",
        encoding="utf-8",
    )


def add_cuda_visible_devices(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(
        path.read_text(encoding="utf-8") + "\nENV CUDA_VISIBLE_DEVICES=0\n",
        encoding="utf-8",
    )


def add_gateway_port(bundle: Path) -> None:
    path = bundle / "Dockerfile"
    path.write_text(path.read_text(encoding="utf-8") + "\nEXPOSE 9000\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (add_unlisted_file, "undeclared bundle file"),
        (add_environment_file, "environment file"),
        (add_database_file, "runtime database"),
        (add_raw_jsonl, "raw result"),
        (add_model_weight, "model weight"),
        (add_large_file, "file is at least 5 MiB"),
        (add_secret_token, "secret-like token"),
        (remove_license, "missing required bundle file: LICENSE"),
        (tamper_evidence, "evidence byte mismatch"),
        (make_root_user, "Space runtime user must be 10001:10001"),
        (add_broad_copy, "broad Docker COPY"),
        (add_json_broad_copy, "broad Docker COPY"),
        (add_relative_broad_copy, "broad Docker COPY"),
        (add_relative_broad_add, "broad Docker COPY"),
        (add_json_broad_add, "broad Docker COPY"),
        (add_gpu_term, "GPU configuration"),
        (add_cuda_visible_devices, "GPU configuration"),
        (add_gateway_port, "gateway port 9000"),
    ],
)
def test_bundle_verifier_rejects_public_boundary_violation(
    tmp_path: Path, mutation: Mutation, expected: str
) -> None:
    bundle = export_valid_bundle(tmp_path)
    mutation(bundle)

    assert any(expected in item for item in verify_space_bundle(Path.cwd(), bundle))


def test_bundle_verifier_includes_import_boundary_violations(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    app = bundle / "space/app.py"
    app.write_text(app.read_text(encoding="utf-8") + "\nimport socket\n", encoding="utf-8")

    assert any(
        "forbidden import: socket" in item for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_fails_closed_on_non_string_control_manifest(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    provenance_path = bundle / "bench/results/provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["control_manifests"] = [{}]
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    assert any(
        "evidence control manifests" in item for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_uses_source_commit_allowlist_not_dirty_checkout(tmp_path: Path) -> None:
    repo_root = clone_source_repo(tmp_path)
    bundle = tmp_path / "bundle"
    export_space_bundle(repo_root, bundle, _head_revision(repo_root))
    manifest_path = repo_root / "space/bundle-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    [report_entry] = [
        entry for entry in manifest["files"] if entry["destination"] == "EVAL_REPORT.md"
    ]
    report_entry["destination"] = "RENAMED_REPORT.md"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (bundle / "EVAL_REPORT.md").rename(bundle / "RENAMED_REPORT.md")

    assert any(
        "missing required bundle file: EVAL_REPORT.md" in item
        for item in verify_space_bundle(repo_root, bundle)
    )


def test_bundle_verifier_uses_source_commit_lock_not_dirty_checkout(tmp_path: Path) -> None:
    repo_root = clone_source_repo(tmp_path)
    bundle = tmp_path / "bundle"
    export_space_bundle(repo_root, bundle, _head_revision(repo_root))
    lock_path = repo_root / "uv.lock"
    lock_text = lock_path.read_text(encoding="utf-8")
    mutated = lock_text.replace(
        'name = "streamlit"\nversion = "1.61.1"',
        'name = "streamlit"\nversion = "0.0.0"',
    )
    assert mutated != lock_text
    lock_path.write_text(mutated, encoding="utf-8")

    assert verify_space_bundle(repo_root, bundle) == []


@pytest.mark.parametrize("mutation", ["extra", "missing", "repeated"])
def test_bundle_verifier_requires_twelve_unique_canonical_evidence_artifacts(
    tmp_path: Path, mutation: str
) -> None:
    bundle = export_valid_bundle(tmp_path)
    provenance_path = bundle / "bench/results/provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if mutation == "extra":
        extra_path = "bench/results/extra.json"
        _write(bundle, extra_path, "{}")
        provenance["artifacts"].append(
            {
                "path": extra_path,
                "sha256": hashlib.sha256(b"{}").hexdigest(),
                "class": "measured_summary",
                "description": "hostile extra",
            }
        )
    elif mutation == "missing":
        provenance["artifacts"].pop()
    else:
        provenance["artifacts"].append(dict(provenance["artifacts"][0]))
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    assert any(
        "exactly 12 unique canonical paths" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_requires_two_unique_control_manifests(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    provenance_path = bundle / "bench/results/provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["control_manifests"].append("bench/results/claims.json")
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    assert any(
        "exactly two unique control manifests" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


@pytest.mark.parametrize(
    "omitted",
    [
        "bench/results/gateway_overhead.json",
        "bench/results/claims.json",
    ],
)
def test_bundle_verifier_requires_canonical_evidence_files_even_if_commit_omits_them(
    tmp_path: Path, omitted: str
) -> None:
    repo_root = clone_source_repo(tmp_path)
    manifest_path = repo_root / "space/bundle-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [entry for entry in manifest["files"] if entry["destination"] != omitted]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    commit_file(repo_root, "space/bundle-manifest.json")
    bundle = tmp_path / "bundle"
    export_space_bundle(repo_root, bundle, _head_revision(repo_root))

    assert any(
        f"missing canonical evidence file: {omitted}" in item
        for item in verify_space_bundle(repo_root, bundle)
    )


def test_bundle_verifier_rejects_comment_only_healthcheck(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    dockerfile = bundle / "Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text(encoding="utf-8").replace("HEALTHCHECK ", "# HEALTHCHECK "),
        encoding="utf-8",
    )

    assert any(
        "exactly one canonical active HEALTHCHECK" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_rejects_trailing_overriding_cmd(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    dockerfile = bundle / "Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text(encoding="utf-8") + '\nCMD ["python", "-m", "http.server"]\n',
        encoding="utf-8",
    )

    assert any(
        "final CMD must start the canonical Streamlit app" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_space_source_returns_violation_for_malformed_manifest(tmp_path: Path) -> None:
    repo_root = clone_source_repo(tmp_path)
    (repo_root / "space/bundle-manifest.json").write_text("{", encoding="utf-8")

    violations = verify_space_source(repo_root)

    assert violations == ["cannot export Space source: BundleManifestError"]


@pytest.mark.parametrize(
    "replacement",
    [
        "https://example.test/?next=https://github.com/kuotunyu/local-inference-bench-gateway",
        "plain https://github.com/kuotunyu/local-inference-bench-gateway text",
    ],
)
def test_bundle_verifier_requires_exact_canonical_source_link(
    tmp_path: Path, replacement: str
) -> None:
    bundle = export_valid_bundle(tmp_path)
    card_path = bundle / "README.md"
    card_path.write_text(
        card_path.read_text(encoding="utf-8").replace(
            "https://github.com/kuotunyu/local-inference-bench-gateway", replacement
        ),
        encoding="utf-8",
    )

    assert any(
        "must link the canonical source repository" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_rejects_case_insensitive_hf_space_hostname(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    card_path = bundle / "README.md"
    card_path.write_text(
        card_path.read_text(encoding="utf-8") + "\n[hosted demo](https://demo.HF.SPACE)\n",
        encoding="utf-8",
    )

    assert any(
        "must not hard-code an ephemeral hf.space URL" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


@pytest.mark.parametrize(
    "replacement",
    [
        f"<!-- [source]({CANONICAL_SOURCE_URL}) -->",
        f"`[source]({CANONICAL_SOURCE_URL})`",
        f"```text\n[source]({CANONICAL_SOURCE_URL})\n```",
    ],
    ids=("html-comment", "inline-code", "fenced-code"),
)
def test_bundle_verifier_requires_rendered_canonical_source_link(
    tmp_path: Path, replacement: str
) -> None:
    bundle = export_valid_bundle(tmp_path)
    card_path = bundle / "README.md"
    card = card_path.read_text(encoding="utf-8")
    assert CANONICAL_SOURCE_LINK in card
    card_path.write_text(card.replace(CANONICAL_SOURCE_LINK, replacement), encoding="utf-8")

    assert any(
        "must link the canonical source repository" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_bundle_verifier_accepts_canonical_source_autolink(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    card_path = bundle / "README.md"
    card = card_path.read_text(encoding="utf-8")
    assert CANONICAL_SOURCE_LINK in card
    card_path.write_text(
        card.replace(CANONICAL_SOURCE_LINK, f"<{CANONICAL_SOURCE_URL}>"),
        encoding="utf-8",
    )

    assert not any(
        "must link the canonical source repository" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


@pytest.mark.parametrize(
    "hostile_url",
    [
        "https://demo.HF.SPACE/path",
        "<https://demo.HF.SPACE/path>",
        "[hosted demo](https://demo.HF.SPACE./path)",
    ],
    ids=("plain", "autolink", "inline-trailing-dot"),
)
def test_bundle_verifier_rejects_hf_space_in_rendered_url_forms(
    tmp_path: Path, hostile_url: str
) -> None:
    bundle = export_valid_bundle(tmp_path)
    card_path = bundle / "README.md"
    card_path.write_text(
        card_path.read_text(encoding="utf-8") + f"\n{hostile_url}\n",
        encoding="utf-8",
    )

    assert any(
        "must not hard-code an ephemeral hf.space URL" in item
        for item in verify_space_bundle(Path.cwd(), bundle)
    )


def test_valid_exported_bundle_passes_every_policy(tmp_path: Path) -> None:
    bundle = export_valid_bundle(tmp_path)
    actual_paths = {
        path.relative_to(bundle).as_posix() for path in bundle.rglob("*") if path.is_file()
    }
    assert actual_paths == expected_bundle_paths()

    deployment = json.loads((bundle / "deployment-manifest.json").read_text(encoding="utf-8"))
    assert (
        deployment["export_manifest_sha256"]
        == hashlib.sha256(Path("space/bundle-manifest.json").read_bytes()).hexdigest()
    )
    assert (
        deployment["evidence_manifest_sha256"]
        == hashlib.sha256(Path("bench/results/provenance.json").read_bytes()).hexdigest()
    )
    assert (bundle / "requirements.txt").read_text(encoding="utf-8").splitlines() == [
        "streamlit==1.61.1",
        "pandas==3.0.5",
        "altair==6.2.2",
    ]
    card = (bundle / "README.md").read_text(encoding="utf-8")
    assert "[MIT License](LICENSE)" in card
    assert "[Third-party notices](THIRD_PARTY_NOTICES.md)" in card
    assert deployment["space_id"] == SPACE_ID
    assert deployment["source_commit"] == _head_revision()

    provenance = json.loads((bundle / "bench/results/provenance.json").read_text(encoding="utf-8"))
    evidence_paths = {
        *provenance["control_manifests"],
        *(artifact["path"] for artifact in provenance["artifacts"]),
    }
    assert len(evidence_paths) == 14
    assert all((bundle / relative).is_file() for relative in evidence_paths)

    assert verify_space_bundle(Path.cwd(), bundle) == []


def test_space_source_exports_and_verifies_current_revision() -> None:
    assert verify_space_source(Path.cwd()) == []
