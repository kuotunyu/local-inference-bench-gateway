from __future__ import annotations

import hashlib
import html
import json
import re
import socket
import urllib.request
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[2] / "space/app.py"
PUBLIC_PAGES = (
    "Demo 概覽",
    "Demo Routing 與可靠性",
    "Demo Request 紀錄",
    "Committed Benchmark Evidence",
)
RUNTIME_ARTIFACT_PATTERNS = (
    "*.db",
    "*.sqlite*",
    "*.gguf",
    "*.safetensors",
    "*.onnx",
    "*.jsonl",
)


def _normalize_html_whitespace(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(text).split())


def _semantic_chart_snapshot(chart) -> str:
    dataset_names = {
        dataset.name: f"dataset-{index}" for index, dataset in enumerate(chart.proto.datasets)
    }

    def normalize_dataset_names(value):
        if isinstance(value, dict):
            return {
                key: dataset_names.get(item, item)
                if key == "name" and isinstance(item, str)
                else normalize_dataset_names(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [normalize_dataset_names(item) for item in value]
        return value

    spec = normalize_dataset_names(json.loads(chart.proto.spec))
    datasets = tuple(
        hashlib.sha256(bytes(dataset.data.data)).hexdigest() for dataset in chart.proto.datasets
    )
    return f"chart:{json.dumps(spec, ensure_ascii=False, sort_keys=True)}|{datasets}"


def semantic_app_snapshot(app: AppTest) -> tuple[str, ...]:
    """Capture stable, user-visible AppTest semantics without framework IDs."""
    snapshot = [
        *(f"markdown:{_normalize_html_whitespace(item.value)}" for item in app.markdown),
        *(f"caption:{_normalize_html_whitespace(item.value)}" for item in app.caption),
        *(f"metric:{item.label}|{item.value}|{item.delta}" for item in app.metric),
        *(f"radio:{item.label}|{item.value}|{tuple(item.options)}" for item in app.radio),
        *(f"selectbox:{item.label}|{item.value}|{tuple(item.options)}" for item in app.selectbox),
        *(
            f"multiselect:{item.label}|{tuple(item.value)}|{tuple(item.options)}"
            for item in app.multiselect
        ),
        *(f"json:{item.value}" for item in app.json),
        *(f"code:{item.language}|{item.value}" for item in app.code),
        *(f"expander:{item.label}" for item in app.expander),
        *(_semantic_chart_snapshot(item) for item in app.get("vega_lite_chart")),
    ]
    snapshot.extend(
        f"dataframe:{item.value.to_json(orient='split', date_format='iso')}"
        for item in app.dataframe
    )
    return tuple(snapshot)


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_connection(*args, **kwargs):
        raise AssertionError("public app attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_connection)
    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(urllib.request, "urlopen", reject_connection)
    monkeypatch.setattr(httpx.Client, "request", reject_connection)


@pytest.mark.parametrize("page", PUBLIC_PAGES)
def test_every_public_page_ignores_hostile_environment_and_never_opens_socket(
    monkeypatch: pytest.MonkeyPatch, page: str
) -> None:
    clean = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    clean.radio[0].set_value(page).run(timeout=20)
    clean_snapshot = semantic_app_snapshot(clean)

    for key in (
        "GATEWAY_DB_PATH",
        "GATEWAY_BASE_URL",
        "GATEWAY_API_KEY",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HF_HOME",
        "DATABASE_URL",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    ):
        monkeypatch.setenv(key, "http://attacker.invalid/secret")

    _block_network(monkeypatch)
    hostile = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    hostile.radio[0].set_value(page).run(timeout=20)
    assert not hostile.exception
    assert semantic_app_snapshot(hostile) == clean_snapshot


def test_semantic_snapshot_captures_reliability_metric_values() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value("Demo Routing 與可靠性").run(timeout=20)

    assert "metric:觀測到的 HTTP 429|1|" in semantic_app_snapshot(app)


def test_public_app_creates_no_runtime_or_model_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    for page in PUBLIC_PAGES:
        app.radio[0].set_value(page).run(timeout=20)

    created = {
        path.relative_to(tmp_path).as_posix()
        for pattern in RUNTIME_ARTIFACT_PATTERNS
        for path in tmp_path.rglob(pattern)
    }
    assert created == set()
