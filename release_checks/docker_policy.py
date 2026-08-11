"""Static policy checks for the production image and CPU-only Compose smoke topology."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REQUIRED_SMOKE_SERVICES = {"mock-primary", "mock-fallback", "gateway", "smoke-client"}
GPU_KEY_PATTERN = re.compile(
    r"^\s*(?:gpus|devices|runtime)\s*:|NVIDIA_VISIBLE_DEVICES|runtime\s*:\s*nvidia",
    re.IGNORECASE | re.MULTILINE,
)
BROAD_COPY_PATTERN = re.compile(
    r"^\s*(?:COPY|ADD)\s+(?:--[^\s]+\s+)*\.\s+(?:\.|/\S*)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _read(path: Path, label: str, violations: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        violations.append(f"cannot read {label}: {type(exc).__name__}")
        return ""


def _service_names(compose_text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(r"^  ([A-Za-z0-9_-]+):\s*$", compose_text, re.MULTILINE)
    }


def _published_ports(compose_text: str) -> list[str]:
    ports: list[str] = []
    lines = compose_text.splitlines()
    ports_indent = None
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if stripped == "ports:":
            ports_indent = indent
            continue
        if ports_indent is not None:
            if stripped and indent <= ports_indent:
                ports_indent = None
            elif stripped.startswith("-"):
                ports.append(stripped[1:].strip().strip("\"'"))
    return ports


def verify_docker_policy(repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    violations: list[str] = []
    dockerfile = _read(repo_root / "Dockerfile", "Dockerfile", violations)
    compose = _read(repo_root / "compose.yaml", "compose.yaml", violations)
    smoke = _read(repo_root / "compose.smoke.yaml", "compose.smoke.yaml", violations)
    smoke_models = _read(
        repo_root / "docker" / "smoke" / "models.yaml", "smoke models registry", violations
    )

    user_matches = re.findall(r"^\s*USER\s+([^\s]+)", dockerfile, re.IGNORECASE | re.MULTILINE)
    if not user_matches or any(
        user.lower().startswith("root") or user.startswith("0") for user in user_matches
    ):
        violations.append("Dockerfile must declare a non-root USER")
    if not re.search(r"^\s*HEALTHCHECK\b", dockerfile, re.IGNORECASE | re.MULTILINE):
        violations.append("Dockerfile must declare HEALTHCHECK")
    if BROAD_COPY_PATTERN.search(dockerfile):
        violations.append("broad Docker COPY/ADD is forbidden")
    for required in ("pyproject.toml", "uv.lock", "gateway", "dashboard"):
        if not re.search(rf"^\s*COPY\b[^\n]*\b{re.escape(required)}\b", dockerfile, re.MULTILINE):
            violations.append(f"Dockerfile lacks explicit COPY for {required}")

    published_ports = _published_ports(compose)
    if not published_ports:
        violations.append("compose.yaml must publish loopback ports")
    for port in published_ports:
        if not port.startswith("127.0.0.1:"):
            violations.append(f"published port is not loopback-bound: {port}")

    if GPU_KEY_PATTERN.search(compose) or GPU_KEY_PATTERN.search(smoke):
        violations.append("GPU configuration is forbidden in Compose")
    services = _service_names(smoke)
    for missing in sorted(REQUIRED_SMOKE_SERVICES - services):
        violations.append(f"CPU smoke service is missing: {missing}")
    try:
        smoke_config = yaml.safe_load(smoke) or {}
    except yaml.YAMLError as exc:
        violations.append(f"cannot parse compose.smoke.yaml: {type(exc).__name__}")
        smoke_config = {}
    smoke_services = smoke_config.get("services", {})
    gateway = smoke_services.get("gateway", {})
    gateway_tmpfs = gateway.get("tmpfs", []) if isinstance(gateway, dict) else []
    if isinstance(gateway_tmpfs, str):
        gateway_tmpfs = [gateway_tmpfs]
    writable_data_tmpfs = "/app/data:uid=10001,gid=10001,mode=0770"
    if writable_data_tmpfs not in gateway_tmpfs:
        violations.append("gateway tmpfs must grant /app/data to the non-root container user")
    smoke_client = smoke_services.get("smoke-client", {})
    depends_on = smoke_client.get("depends_on", {}) if isinstance(smoke_client, dict) else {}
    gateway_dependency = depends_on.get("gateway", {}) if isinstance(depends_on, dict) else {}
    if not (
        isinstance(gateway_dependency, dict)
        and gateway_dependency.get("condition") == "service_started"
    ):
        violations.append(
            "smoke-client must use gateway condition service_started so startup failures exit nonzero"
        )
    lower_registry = smoke_models.lower()
    if any(host in lower_registry for host in ("host.docker.internal", "127.0.0.1", "localhost")):
        violations.append("smoke registry must not contact host inference services")
    for backend in ("mock-primary", "mock-fallback"):
        if backend not in lower_registry:
            violations.append(f"smoke registry lacks container backend: {backend}")
    return violations
