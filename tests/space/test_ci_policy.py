from pathlib import Path


def test_ci_builds_non_root_space_and_runs_without_network() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/export_hf_space.py" in workflow
    assert "local-inference-bench-gateway-space:rc" in workflow
    assert "--network none" in workflow
    assert "local-inference-space-smoke" in workflow
    assert "Config.User" in workflow
    assert 'test "$runtime_user" = "10001:10001"' in workflow
    assert "for attempt in $(seq 1 45)" in workflow
    assert "deadline=$((SECONDS + 55))" in workflow
    assert "sleep 1" in workflow
    assert "http://127.0.0.1:7860/_stcore/health" in workflow
    assert "docker logs local-inference-space-smoke" in workflow
    assert "space_remote_gate" not in workflow
    assert "docker rm -f local-inference-space-smoke" in workflow


def test_ci_contains_no_network_space_smoke() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "/app" in workflow
    for forbidden_suffix in (".db", ".sqlite", ".gguf", ".safetensors", ".onnx", ".jsonl"):
        assert forbidden_suffix in workflow
    assert "docker logs local-inference-space-smoke >&2" in workflow
    assert "exit 1" in workflow
    assert "if: always()" in workflow
    assert "docker rm -f local-inference-space-smoke" in workflow
