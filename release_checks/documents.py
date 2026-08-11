"""Validate local Markdown targets and canonical claim placement."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

DEFAULT_DOCUMENTS = (
    "README.md",
    "EVAL_REPORT.md",
    "DESIGN.md",
    "SETUP.md",
    "PRODUCTION_SCALING.md",
    "OWNER_ACTIONS.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/RELEASE_DESIGN.md",
    "docs/SOURCE_AUDIT.md",
)
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
PRIVATE_DOCUMENT_NAMES = {("pl" + "an.md"), ("interview" + "_prep.md")}
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def _local_target(document: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
    if not target or target.startswith("#") or target.lower().startswith(EXTERNAL_PREFIXES):
        return None
    path_text = unquote(target.split("#", 1)[0].split("?", 1)[0])
    return (document.parent / path_text).resolve()


def verify_documents(
    repo_root: Path, *, required_documents: tuple[str, ...] = DEFAULT_DOCUMENTS
) -> list[str]:
    repo_root = repo_root.resolve()
    violations: list[str] = []
    documents: dict[str, str] = {}

    for relative in required_documents:
        path = repo_root / relative
        if not path.is_file():
            violations.append(f"required document is missing: {relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            violations.append(f"cannot read document {relative}: {type(exc).__name__}")
            continue
        documents[relative] = text
        for raw_target in LINK_PATTERN.findall(text):
            target = _local_target(path, raw_target)
            if target is None:
                continue
            if target.name.lower() in PRIVATE_DOCUMENT_NAMES:
                violations.append(f"private document link in {relative}: {raw_target}")
            try:
                target.relative_to(repo_root)
            except ValueError:
                violations.append(f"local link escapes repository in {relative}: {raw_target}")
                continue
            if not target.exists():
                violations.append(f"missing local link target in {relative}: {raw_target}")

    claims_path = repo_root / "bench" / "results" / "claims.json"
    try:
        claims = json.loads(claims_path.read_text(encoding="utf-8")).get("claims", [])
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return violations + [f"cannot read claims for documentation check: {type(exc).__name__}"]
    for claim in claims:
        relative = claim.get("document")
        display = claim.get("display")
        if relative not in documents:
            violations.append(f"canonical claim targets an unchecked document: {claim.get('id')}")
        elif not isinstance(display, str) or display not in documents[relative]:
            violations.append(f"canonical claim is absent from {relative}: {claim.get('id')}")
    return violations
