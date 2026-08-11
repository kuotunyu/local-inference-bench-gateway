from __future__ import annotations

import json

from release_checks.documents import verify_documents


def _claims(path, display="Measured claim: 1.23 ms", document="README.md"):
    results = path / "bench" / "results"
    results.mkdir(parents=True)
    (results / "claims.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "claims": [{"id": "claim", "display": display, "document": document}],
            }
        ),
        encoding="utf-8",
    )


def test_documents_reject_missing_local_link(tmp_path):
    _claims(tmp_path)
    (tmp_path / "README.md").write_text(
        "Measured claim: 1.23 ms\n\n[missing](docs/missing.md)", encoding="utf-8"
    )

    violations = verify_documents(tmp_path, required_documents=("README.md",))

    assert any("missing local link target" in violation for violation in violations)


def test_documents_reject_private_document_link(tmp_path):
    private_name = "INTERVIEW" + "_PREP.md"
    _claims(tmp_path)
    (tmp_path / "README.md").write_text(
        f"Measured claim: 1.23 ms\n\n[notes]({private_name})", encoding="utf-8"
    )
    (tmp_path / private_name).write_text("private", encoding="utf-8")

    violations = verify_documents(tmp_path, required_documents=("README.md",))

    assert any("private document link" in violation for violation in violations)


def test_documents_require_claim_in_declared_document(tmp_path):
    _claims(tmp_path)
    (tmp_path / "README.md").write_text("No canonical value here.", encoding="utf-8")

    violations = verify_documents(tmp_path, required_documents=("README.md",))

    assert any("canonical claim is absent" in violation for violation in violations)


def test_documents_allow_existing_relative_assets_and_external_links(tmp_path):
    _claims(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "details.md").write_text("# Details", encoding="utf-8")
    (tmp_path / "chart.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "README.md").write_text(
        "Measured claim: 1.23 ms\n\n"
        "[details](docs/details.md#details)\n\n"
        "![chart](chart.png)\n\n"
        "[external](https://example.com)",
        encoding="utf-8",
    )

    assert verify_documents(tmp_path, required_documents=("README.md",)) == []
