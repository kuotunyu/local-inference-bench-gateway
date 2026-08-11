from __future__ import annotations

from release_checks.docker_policy import verify_docker_policy

GOOD_DOCKERFILE = """
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY gateway ./gateway
COPY dashboard ./dashboard
RUN useradd --uid 10001 app
USER 10001:10001
HEALTHCHECK CMD ["python", "-c", "print('ok')"]
CMD ["uvicorn", "gateway.app:app"]
"""

GOOD_COMPOSE = """
services:
  gateway:
    build: .
    ports:
      - "127.0.0.1:9000:9000"
  dashboard:
    build: .
    ports:
      - "127.0.0.1:8501:8501"
"""

GOOD_SMOKE = """
services:
  mock-primary:
    image: python:3.12-slim
  mock-fallback:
    image: python:3.12-slim
  gateway:
    build: .
    tmpfs:
      - /app/data:uid=10001,gid=10001,mode=0770
  smoke-client:
    image: python:3.12-slim
    depends_on:
      gateway:
        condition: service_started
"""

GOOD_MODELS = """
models:
  smoke-alias:
    backends:
      - name: primary
        base_url: http://mock-primary:8000/v1
        model: mock-primary
      - name: fallback
        base_url: http://mock-fallback:8000/v1
        model: mock-fallback
"""


def _write_fixture(tmp_path, *, dockerfile=GOOD_DOCKERFILE, compose=GOOD_COMPOSE, smoke=GOOD_SMOKE):
    (tmp_path / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(compose, encoding="utf-8")
    (tmp_path / "compose.smoke.yaml").write_text(smoke, encoding="utf-8")
    models = tmp_path / "docker" / "smoke"
    models.mkdir(parents=True)
    (models / "models.yaml").write_text(GOOD_MODELS, encoding="utf-8")


def test_docker_policy_accepts_safe_minimal_fixture(tmp_path):
    _write_fixture(tmp_path)

    assert verify_docker_policy(tmp_path) == []


def test_docker_policy_requires_non_root_user_and_healthcheck(tmp_path):
    _write_fixture(
        tmp_path,
        dockerfile=GOOD_DOCKERFILE.replace("USER 10001:10001\n", "").replace(
            "HEALTHCHECK CMD", "# no health command"
        ),
    )

    violations = verify_docker_policy(tmp_path)

    assert any("non-root USER" in violation for violation in violations)
    assert any("HEALTHCHECK" in violation for violation in violations)


def test_docker_policy_rejects_broad_copy(tmp_path):
    _write_fixture(tmp_path, dockerfile=GOOD_DOCKERFILE + "\nCOPY . .\n")

    assert any("broad Docker COPY" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_requires_loopback_host_ports(tmp_path):
    _write_fixture(tmp_path, compose=GOOD_COMPOSE.replace("127.0.0.1:9000:9000", "9000:9000"))

    assert any("loopback" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_rejects_gpu_configuration(tmp_path):
    _write_fixture(tmp_path, smoke=GOOD_SMOKE + "\n    runtime: nvidia\n")

    assert any("GPU configuration" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_requires_all_cpu_smoke_services(tmp_path):
    _write_fixture(tmp_path, smoke=GOOD_SMOKE.replace("  mock-fallback:\n", "  other:\n"))

    assert any("mock-fallback" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_requires_writable_gateway_tmpfs(tmp_path):
    _write_fixture(
        tmp_path,
        smoke=GOOD_SMOKE.replace("/app/data:uid=10001,gid=10001,mode=0770", "/app/data"),
    )

    assert any("gateway tmpfs" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_requires_smoke_client_to_observe_gateway_startup_failure(tmp_path):
    _write_fixture(
        tmp_path,
        smoke=GOOD_SMOKE.replace("condition: service_started", "condition: service_healthy"),
    )

    assert any("service_started" in item for item in verify_docker_policy(tmp_path))


def test_docker_policy_rejects_host_inference_from_smoke_registry(tmp_path):
    _write_fixture(tmp_path)
    models = tmp_path / "docker" / "smoke" / "models.yaml"
    models.write_text(GOOD_MODELS.replace("mock-primary", "host.docker.internal"), encoding="utf-8")

    assert any("host inference" in item for item in verify_docker_policy(tmp_path))
