"""Verify benchmark artifact provenance and canonical numeric claims without network access."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ALLOWED_CLASSES = {
    "measured_summary",
    "measured_control",
    "calibrated_input",
    "derived_chart",
}
CONTROL_MANIFESTS = {"bench/results/provenance.json", "bench/results/claims.json"}
TEXT_ARTIFACT_SUFFIXES = {".csv", ".json"}


def _digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_ARTIFACT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _selector_value(repo_root: Path, selector: dict) -> float:
    kind = selector["kind"]
    if kind == "csv_value":
        path = repo_root / selector["path"]
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        matches = [
            row
            for row in rows
            if all(row.get(key) == str(value) for key, value in selector["filters"].items())
        ]
        if len(matches) != 1:
            raise ValueError(f"selector matched {len(matches)} CSV rows")
        value = float(matches[0][selector["field"]])
    elif kind == "json_key":
        value = float(_read_json(repo_root / selector["path"])[selector["key"]])
    elif kind == "json_list_value":
        rows = _read_json(repo_root / selector["path"])
        matches = [
            row
            for row in rows
            if all(row.get(key) == expected for key, expected in selector["filters"].items())
        ]
        if len(matches) != 1:
            raise ValueError(f"selector matched {len(matches)} JSON rows")
        value = float(matches[0][selector["field"]])
    elif kind == "ratio_percent":
        numerator = _selector_value(repo_root, selector["numerator"])
        denominator = _selector_value(repo_root, selector["denominator"])
        value = numerator / denominator * 100
    else:
        raise ValueError(f"unsupported selector kind: {kind}")
    return value * float(selector.get("multiply", 1))


def verify_evidence(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    results_root = repo_root / "bench" / "results"
    provenance_path = results_root / "provenance.json"
    claims_path = results_root / "claims.json"
    violations: list[str] = []

    try:
        provenance = _read_json(provenance_path)
        claims_manifest = _read_json(claims_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"cannot read evidence manifest: {type(exc).__name__}"]

    if provenance.get("schema_version") != 1:
        violations.append("provenance schema_version must be 1")
    if set(provenance.get("control_manifests", [])) != CONTROL_MANIFESTS:
        violations.append("provenance control_manifests do not match the two manifest files")

    artifacts = provenance.get("artifacts")
    if not isinstance(artifacts, list):
        return violations + ["provenance artifacts must be a list"]

    listed_paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            violations.append("provenance contains a non-object artifact")
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str):
            violations.append("artifact path must be a string")
            continue
        if relative in listed_paths:
            violations.append(f"duplicate artifact path: {relative}")
        listed_paths.add(relative)
        if artifact.get("class") not in ALLOWED_CLASSES:
            violations.append(f"invalid evidence class: {relative}")
        expected = artifact.get("sha256")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or expected != expected.lower()
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            violations.append(f"invalid SHA-256 declaration: {relative}")
            continue
        path = repo_root / relative
        if not path.is_file():
            violations.append(f"missing artifact: {relative}")
            continue
        if _digest(path) != expected:
            violations.append(f"SHA-256 mismatch: {relative}")

    actual_paths = {
        path.relative_to(repo_root).as_posix()
        for path in results_root.rglob("*")
        if path.is_file() and path.relative_to(repo_root).as_posix() not in CONTROL_MANIFESTS
    }
    for relative in sorted(actual_paths - listed_paths):
        violations.append(f"unlisted artifact: {relative}")
    for relative in sorted(listed_paths - actual_paths):
        violations.append(f"listed artifact is outside the public artifact set: {relative}")

    expected_prompts = {
        "bench/results/prompts/prompt_2000.json": (2000, 1970),
        "bench/results/prompts/prompt_8000.json": (8000, 7880),
    }
    for relative, (target, actual) in expected_prompts.items():
        try:
            prompt = _read_json(repo_root / relative)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            violations.append(f"invalid calibrated prompt {relative}: {type(exc).__name__}")
            continue
        if (
            prompt.get("target_tokens") != target
            or prompt.get("actual_tokens") != actual
            or prompt.get("reference_engine") != "llamacpp"
            or not isinstance(prompt.get("text"), str)
            or not prompt["text"]
        ):
            violations.append(f"unexpected calibrated prompt metadata: {relative}")

    if claims_manifest.get("schema_version") != 1:
        violations.append("claims schema_version must be 1")
    claims = claims_manifest.get("claims")
    if not isinstance(claims, list):
        return violations + ["claims must be a list"]
    seen_claim_ids: set[str] = set()
    for claim in claims:
        claim_id = claim.get("id") if isinstance(claim, dict) else None
        if not isinstance(claim_id, str) or not claim_id:
            violations.append("claim id must be a non-empty string")
            continue
        if claim_id in seen_claim_ids:
            violations.append(f"duplicate claim id: {claim_id}")
        seen_claim_ids.add(claim_id)
        if not isinstance(claim.get("display"), str) or not claim["display"]:
            violations.append(f"claim has no display string: {claim_id}")
        if not isinstance(claim.get("document"), str) or not claim["document"]:
            violations.append(f"claim has no target document: {claim_id}")
        try:
            actual = _selector_value(repo_root, claim["selector"])
            rounded = round(actual, int(claim["round_digits"]))
            if rounded != claim["value"]:
                violations.append(
                    f"claim value mismatch: {claim_id} expected {claim['value']}, computed {rounded}"
                )
        except (KeyError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            violations.append(f"cannot resolve claim {claim_id}: {type(exc).__name__}: {exc}")

    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    violations = verify_evidence(repo_root)
    if violations:
        for violation in violations:
            print(f"[evidence] {violation}")
        return 1
    provenance = _read_json(repo_root / "bench" / "results" / "provenance.json")
    claims = _read_json(repo_root / "bench" / "results" / "claims.json")
    print(
        f"evidence OK: {len(provenance['artifacts'])} artifacts, "
        f"{len(claims['claims'])} canonical claims"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
