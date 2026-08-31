from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from dashboard import components
from dashboard.data.public_evidence import load_public_evidence
from dashboard.views import evidence as evidence_view

RESULTS_DIR = Path("bench/results")
INTEGRITY_FAILURE = "Unavailable — evidence integrity check failed"


class MarkdownCapture:
    def __init__(self) -> None:
        self.markdown_values: list[str] = []

    def __enter__(self) -> MarkdownCapture:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def altair_chart(self, *_: object, **__: object) -> None:
        return None

    def caption(self, value: str, **_: object) -> None:
        self.markdown_values.append(value)

    def code(self, value: str, **_: object) -> None:
        self.markdown_values.append(value)

    def columns(self, spec: int | list[float], **_: object) -> list[MarkdownCapture]:
        count = spec if isinstance(spec, int) else len(spec)
        return [self] * count

    def expander(self, *_: object, **__: object) -> MarkdownCapture:
        return self

    def json(self, _: object, **__: object) -> None:
        return None

    def markdown(self, value: str, **_: object) -> None:
        self.markdown_values.append(value)

    def write(self, value: str, **_: object) -> None:
        self.markdown_values.append(value)


def copy_results(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def _claim_displays() -> list[str]:
    claims = json.loads((RESULTS_DIR / "claims.json").read_text(encoding="utf-8"))
    return [str(claim["display"]) for claim in claims["claims"]]


def _rendered_markdown(monkeypatch, evidence) -> str:
    return "".join(_rendered_blocks(monkeypatch, evidence))


def _rendered_blocks(monkeypatch, evidence) -> list[str]:
    capture = MarkdownCapture()
    monkeypatch.setattr(components, "st", capture)
    monkeypatch.setattr(evidence_view, "st", capture)
    evidence_view.render_evidence(evidence)
    return capture.markdown_values


def _section_markdown(blocks: list[str], heading: str, next_heading: str | None) -> str:
    start = blocks.index(heading)
    end = len(blocks) if next_heading is None else blocks.index(next_heading, start + 1)
    return "".join(blocks[start:end])


def _assert_every_artifact_is_quarantined(state, monkeypatch) -> None:
    assert state.verified_artifacts == 0
    assert state.complete is False
    assert state.evidence.concurrency.empty
    assert state.evidence.prefill.empty
    assert state.evidence.overhead == {}
    assert state.evidence.provenance == {}
    assert state.evidence.claims == {}
    assert state.evidence.kv_cache_off == []
    assert state.evidence.kv_cache_on == []

    rendered = _rendered_markdown(monkeypatch, state.evidence)
    for display in _claim_displays():
        assert rendered.count(display) == 0


def test_complete_public_evidence_reports_twelve_verified_artifacts() -> None:
    state = load_public_evidence(RESULTS_DIR)

    assert state.declared_artifacts == 12
    assert state.verified_artifacts == 12
    assert state.complete is True
    assert state.evidence.warnings == {}


def test_tampered_artifact_is_quarantined_without_hard_coded_metric(tmp_path: Path) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")

    state = load_public_evidence(tmp_path)

    assert state.complete is False
    assert state.verified_artifacts == 11
    assert state.evidence.concurrency.empty
    assert state.evidence.overhead["overhead_ms"] > 0
    assert state.evidence.warnings["concurrency_summary.csv"] == "digest_mismatch"


@pytest.mark.parametrize(
    "manifest_path",
    [
        "bench/results//concurrency_summary.csv",
        "bench/results/./concurrency_summary.csv",
    ],
)
def test_equivalent_manifest_path_cannot_bypass_digest_warning(
    tmp_path: Path, manifest_path: str
) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    provenance_path = tmp_path / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    for artifact in provenance["artifacts"]:
        if artifact["path"] == "bench/results/concurrency_summary.csv":
            artifact["path"] = manifest_path
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")

    state = load_public_evidence(tmp_path)

    assert state.verified_artifacts == 11
    assert state.complete is False
    assert state.evidence.warnings["concurrency_summary.csv"] == "digest_mismatch"


def test_invalid_provenance_quarantines_every_artifact(tmp_path: Path, monkeypatch) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    (tmp_path / "provenance.json").write_text('{"artifacts":"invalid"}', encoding="utf-8")

    _assert_every_artifact_is_quarantined(load_public_evidence(tmp_path), monkeypatch)


def test_missing_provenance_quarantines_every_artifact(tmp_path: Path, monkeypatch) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    (tmp_path / "provenance.json").unlink()

    _assert_every_artifact_is_quarantined(load_public_evidence(tmp_path), monkeypatch)


@pytest.mark.parametrize(
    ("degradation", "canonical_values"),
    [
        (
            "missing_provenance",
            (
                "2026-07-17",
                "NVIDIA GeForce RTX 4090",
                "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf",
            ),
        ),
        (
            "invalid_provenance",
            (
                "2026-07-17",
                "NVIDIA GeForce RTX 4090",
                "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf",
            ),
        ),
        (
            "tampered_concurrency",
            (
                "626 tok/s",
                "705 tok/s",
                "687 tok/s",
                "15,271 MiB",
                "6,515 MiB",
                "42.7%",
            ),
        ),
    ],
)
def test_evidence_panel_suppresses_unverified_values(
    tmp_path: Path,
    monkeypatch,
    degradation: str,
    canonical_values: tuple[str, ...],
) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    provenance_path = tmp_path / "provenance.json"
    if degradation == "missing_provenance":
        provenance_path.unlink()
    elif degradation == "invalid_provenance":
        provenance_path.write_text('{"artifacts":"invalid"}', encoding="utf-8")
    else:
        (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")

    state = load_public_evidence(tmp_path)
    blocks = _rendered_blocks(monkeypatch, state.evidence)
    rendered = "".join(blocks)

    for heading, next_heading in (
        ("### Aggregate decode throughput 比較", "### 依 concurrency 比較 P50 / P95 TTFT"),
        ("### 依 concurrency 比較 P50 / P95 TTFT", "### Prefill · 校準後 prompt"),
        ("### VRAM baseline · concurrency 16", "### LM Studio · Unified KV Cache 控制"),
    ):
        assert INTEGRITY_FAILURE in _section_markdown(blocks, heading, next_heading)
    if degradation in {"missing_provenance", "invalid_provenance"}:
        assert INTEGRITY_FAILURE in _section_markdown(blocks, "### 測量方法與 provenance", None)
    for value in canonical_values:
        assert value not in rendered
