from __future__ import annotations

import html
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


def semantic_app_snapshot(app: AppTest) -> tuple[str, ...]:
    """Capture stable, user-visible AppTest semantics without framework IDs."""
    snapshot = [
        *(f"markdown:{_normalize_html_whitespace(item.value)}" for item in app.markdown),
        *(f"caption:{_normalize_html_whitespace(item.value)}" for item in app.caption),
        *(f"radio:{item.label}|{item.value}|{tuple(item.options)}" for item in app.radio),
        *(f"selectbox:{item.label}|{item.value}|{tuple(item.options)}" for item in app.selectbox),
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


def test_public_app_ignores_hostile_environment_and_never_opens_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean = AppTest.from_file(str(APP_PATH)).run(timeout=20)
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
    assert not hostile.exception
    assert semantic_app_snapshot(hostile) == clean_snapshot


@pytest.mark.parametrize("page", PUBLIC_PAGES)
def test_every_public_page_runs_with_network_guard(
    monkeypatch: pytest.MonkeyPatch, page: str
) -> None:
    _block_network(monkeypatch)
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)

    assert not app.exception


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
