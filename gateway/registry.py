"""Loads models.yaml: alias -> ordered backend list (primary first, then failover targets)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


class RegistryConfigError(ValueError):
    """The model registry is missing a required, safe runtime value."""


@dataclass(frozen=True)
class Backend:
    name: str
    base_url: str
    model: str
    api_key: str | None = None


@dataclass(frozen=True)
class ModelAlias:
    alias: str
    backends: tuple[Backend, ...]
    max_concurrent: int | None = None  # None = unlimited; see gateway/concurrency.py


class Registry:
    def __init__(self, aliases: dict[str, ModelAlias]):
        self._aliases = aliases

    def get(self, alias: str) -> ModelAlias | None:
        return self._aliases.get(alias)

    def list_aliases(self) -> list[str]:
        return list(self._aliases.keys())

    def items(self):
        return self._aliases.items()

    def list_backend_urls(self) -> list[str]:
        """Unique base_urls across every alias -- used by the health checker so a backend
        shared by multiple aliases only gets polled once."""
        seen: dict[str, None] = {}
        for model_alias in self._aliases.values():
            for backend in model_alias.backends:
                seen.setdefault(backend.base_url, None)
        return list(seen.keys())


def build_registry(data: dict) -> Registry:
    """Builds a Registry from an already-parsed dict shaped like models.yaml -- shared by
    load_registry() and by tests that construct a registry in-memory without a YAML file."""
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        raise RegistryConfigError("registry must contain a 'models' mapping")
    if not data["models"]:
        raise RegistryConfigError("registry must contain at least one model alias")

    aliases: dict[str, ModelAlias] = {}
    for alias, cfg in data["models"].items():
        if not isinstance(alias, str) or not alias.strip() or not isinstance(cfg, dict):
            raise RegistryConfigError("each model alias must be a non-empty string mapping")
        backend_data = cfg.get("backends")
        if not isinstance(backend_data, list) or not backend_data:
            raise RegistryConfigError(f"model alias '{alias}' must contain at least one backend")
        max_concurrent = cfg.get("max_concurrent")
        if max_concurrent is not None and (
            isinstance(max_concurrent, bool)
            or not isinstance(max_concurrent, int)
            or max_concurrent <= 0
        ):
            raise RegistryConfigError(f"model alias '{alias}' max_concurrent must be positive")

        for backend in backend_data:
            if not isinstance(backend, dict):
                raise RegistryConfigError(f"model alias '{alias}' contains a non-object backend")
            for field in ("name", "base_url", "model"):
                if not isinstance(backend.get(field), str) or not backend[field].strip():
                    raise RegistryConfigError(
                        f"model alias '{alias}' backend field '{field}' must be a non-empty string"
                    )
            parsed_url = urlparse(backend["base_url"])
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise RegistryConfigError(
                    f"model alias '{alias}' backend base_url must use HTTP or HTTPS"
                )

        backends = tuple(
            Backend(
                name=b["name"],
                base_url=b["base_url"],
                model=b["model"],
                api_key=b.get("api_key"),
            )
            for b in backend_data
        )
        aliases[alias] = ModelAlias(alias=alias, backends=backends, max_concurrent=max_concurrent)
    return Registry(aliases)


def load_registry(path: str | Path = "gateway/models.yaml") -> Registry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return build_registry(data)
