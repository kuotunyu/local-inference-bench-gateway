from __future__ import annotations

import json
import shutil
from pathlib import Path

from dashboard import components
from dashboard.data.public_evidence import load_public_evidence
from dashboard.views import evidence as evidence_view

RESULTS_DIR = Path("bench/results")


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
    capture = MarkdownCapture()
    monkeypatch.setattr(components, "st", capture)
    monkeypatch.setattr(evidence_view, "st", capture)
    evidence_view.render_evidence(evidence)
    return "".join(capture.markdown_values)


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


def test_invalid_provenance_quarantines_every_artifact(tmp_path: Path, monkeypatch) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    (tmp_path / "provenance.json").write_text('{"artifacts":"invalid"}', encoding="utf-8")

    _assert_every_artifact_is_quarantined(load_public_evidence(tmp_path), monkeypatch)


def test_missing_provenance_quarantines_every_artifact(tmp_path: Path, monkeypatch) -> None:
    copy_results(RESULTS_DIR, tmp_path)
    (tmp_path / "provenance.json").unlink()

    _assert_every_artifact_is_quarantined(load_public_evidence(tmp_path), monkeypatch)
