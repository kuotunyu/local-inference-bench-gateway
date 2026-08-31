from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

SPACE_ROOT = Path("space")


def test_space_assets_pin_public_runtime() -> None:
    card = (SPACE_ROOT / "README.md").read_text(encoding="utf-8")
    dockerfile = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    requirements = (SPACE_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()

    assert "sdk: docker" in card
    assert "app_port: 7860" in card
    assert requirements == [
        "streamlit==1.61.1",
        "pandas==3.0.5",
        "altair==6.2.2",
    ]
    assert "FROM python:3.12.13-slim-bookworm" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "COPY . ." not in dockerfile
    assert "uvicorn" not in dockerfile.lower()
    assert "9000" not in dockerfile
    assert (
        'CMD ["streamlit", "run", "space/app.py", "--server.address=0.0.0.0", '
        '"--server.port=7860", "--server.headless=true"]'
    ) in dockerfile
    assert "http://127.0.0.1:7860/_stcore/health" in dockerfile


def test_space_healthcheck_ignores_poisoned_proxy_environment() -> None:
    dockerfile = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    healthcheck_line = next(
        line for line in dockerfile.splitlines() if line.startswith("HEALTHCHECK")
    )
    healthcheck = json.loads(healthcheck_line.split(" CMD ", maxsplit=1)[1])
    command = healthcheck[1:]

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        command[-1] = command[-1].replace("127.0.0.1:7860", f"127.0.0.1:{port}")
        environment = os.environ.copy()
        environment.update(
            {
                "HTTP_PROXY": "http://127.0.0.1:9",
                "HTTPS_PROXY": "http://127.0.0.1:9",
                "ALL_PROXY": "http://127.0.0.1:9",
                "NO_PROXY": "",
            }
        )
        result = subprocess.run(
            [sys.executable, *command],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result.returncode == 0, result.stderr


def test_space_requirements_match_uv_lock_exactly() -> None:
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    locked = {
        package["name"]: package["version"]
        for package in lock["package"]
        if package["name"] in {"streamlit", "pandas", "altair"}
    }
    requirements = set((SPACE_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines())

    assert {f"{name}=={version}" for name, version in locked.items()} == requirements


def test_space_streamlit_config_disables_usage_stats_and_uses_morandi_theme() -> None:
    config = tomllib.loads((SPACE_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))

    assert config["browser"]["gatherUsageStats"] is False
    assert config["theme"] == {
        "base": "light",
        "primaryColor": "#718B7A",
        "backgroundColor": "#F1EFE8",
        "secondaryBackgroundColor": "#FFFDF9",
        "textColor": "#26322C",
        "font": "sans-serif",
    }
    assert "address" not in config.get("server", {})


def test_space_dockerfile_installs_disabled_usage_stats_config() -> None:
    config = tomllib.loads((SPACE_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    dockerfile = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    copy_instructions = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]

    assert config["browser"]["gatherUsageStats"] is False
    assert "COPY .streamlit/config.toml /app/.streamlit/config.toml" in copy_instructions
    assert not any(line.startswith(("COPY . ", "COPY ./ ")) for line in copy_instructions)
    assert "--browser.gatherUsageStats" not in dockerfile


def test_space_card_states_every_public_truth_boundary() -> None:
    card = (SPACE_ROOT / "README.md").read_text(encoding="utf-8")

    required_copy = (
        "公開證據示範（Demo Mode）",
        "此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate "
        "evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live "
        "inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。",
        "Deterministic Demo data is illustrative and is not production or sampled traffic.",
        "Benchmark evidence is a dated, hardware- and version-specific snapshot.",
        "Request-level raw benchmark runs are not public.",
        "This Space cannot connect to a visitor's local system.",
        "This Space provides neither live inference nor an SLA.",
        "Hosting sleep or cold start is not system uptime evidence.",
    )
    for phrase in required_copy:
        assert phrase in card

    assert "aggregate only" in card
    assert "raw runs unpublished" in card
    assert "[MIT License](LICENSE)" in card
    assert "[Third-party notices](THIRD_PARTY_NOTICES.md)" in card
    assert "https://github.com/kuotunyu/local-inference-bench-gateway" in card
    assert (
        "[Evaluation methodology (EVAL_REPORT.md)](https://github.com/kuotunyu/"
        "local-inference-bench-gateway/blob/main/EVAL_REPORT.md)"
    ) in card
    assert re.search(r"https://[^ ]+\.hf\.space", card) is None
