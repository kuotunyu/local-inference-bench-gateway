"""Loads models.yaml: alias -> ordered backend list (primary first, then failover targets)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


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
    aliases: dict[str, ModelAlias] = {}
    for alias, cfg in data["models"].items():
        backends = tuple(
            Backend(
                name=b["name"],
                base_url=b["base_url"],
                model=b["model"],
                api_key=b.get("api_key"),
            )
            for b in cfg["backends"]
        )
        aliases[alias] = ModelAlias(
            alias=alias, backends=backends, max_concurrent=cfg.get("max_concurrent")
        )
    return Registry(aliases)


def load_registry(path: str | Path = "gateway/models.yaml") -> Registry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return build_registry(data)
