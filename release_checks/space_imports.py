"""Verify the transitive Python import boundary of an exported public Space."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

FORBIDDEN_IMPORTS = {
    "gateway",
    "dashboard.state",
    "dashboard.data.live_status",
    "dashboard.data.sqlite_repository",
    "sqlite3",
    "httpx",
    "requests",
    "urllib.request",
    "socket",
    "subprocess",
}

_LOCAL_PACKAGES = {"dashboard", "space"}
_DYNAMIC_IMPORTS = {"__import__", "importlib.import_module"}
_ENVIRONMENT_READS = {"os.getenv", "os.environ"}


class ImportBoundaryError(ValueError):
    """Raised when a complete, contained import closure cannot be constructed."""


@dataclass(frozen=True)
class _ScanResult:
    paths: tuple[PurePosixPath, ...]
    violations: tuple[str, ...]


def _display(path: PurePosixPath, message: str) -> str:
    return f"{path.as_posix()}: {message}"


def _safe_entrypoint(entrypoint: PurePosixPath) -> None:
    windows_path = PureWindowsPath(str(entrypoint))
    if (
        entrypoint.is_absolute()
        or windows_path.drive
        or windows_path.root
        or ".." in entrypoint.parts
        or "\\" in str(entrypoint)
    ):
        raise ImportBoundaryError(_display(entrypoint, "import escapes bundle"))


def _contained_path(bundle_root: Path, relative: PurePosixPath) -> Path:
    root = bundle_root.resolve()
    target = root.joinpath(*relative.parts).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ImportBoundaryError(_display(relative, "import escapes bundle")) from error
    return target


def _module_candidates(module: str) -> tuple[PurePosixPath, PurePosixPath]:
    stem = PurePosixPath(*module.split("."))
    return (stem.with_suffix(".py"), stem / "__init__.py")


def _existing_module_paths(bundle_root: Path, module: str) -> tuple[PurePosixPath, ...]:
    parts = module.split(".")
    resolved: list[PurePosixPath] = []
    for index in range(1, len(parts)):
        package_init = PurePosixPath(*parts[:index]) / "__init__.py"
        package_path = _contained_path(bundle_root, package_init)
        if package_path.is_file():
            resolved.append(package_init)

    for candidate in _module_candidates(module):
        candidate_path = _contained_path(bundle_root, candidate)
        if candidate_path.is_file():
            resolved.append(candidate)
            return tuple(dict.fromkeys(resolved))
    return ()


def _module_for_path(path: PurePosixPath) -> tuple[str, ...]:
    if path.name == "__init__.py":
        return path.parent.parts
    return path.with_suffix("").parts[:-1]


def _absolute_from_module(
    path: PurePosixPath, node: ast.ImportFrom
) -> tuple[str | None, str | None]:
    if not node.level:
        return node.module, None

    package = _module_for_path(path)
    if node.level > len(package):
        return None, "import escapes bundle"
    prefix = package[: len(package) - node.level + 1]
    parts = (*prefix, *(node.module.split(".") if node.module else ()))
    if not parts:
        return None, "import escapes bundle"
    return ".".join(parts), None


def _is_local(module: str) -> bool:
    return module.split(".", 1)[0] in _LOCAL_PACKAGES


def _is_forbidden(module: str) -> str | None:
    for forbidden in sorted(FORBIDDEN_IMPORTS):
        if module == forbidden or module.startswith(f"{forbidden}."):
            return forbidden
    return None


def _qualified_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value, aliases)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def _aliases(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for imported in node.names:
                bound = imported.asname or imported.name.split(".", 1)[0]
                aliases[bound] = imported.name if imported.asname else bound
        elif isinstance(node, ast.ImportFrom) and node.module:
            for imported in node.names:
                if imported.name != "*":
                    aliases[imported.asname or imported.name] = f"{node.module}.{imported.name}"
    return aliases


def _capability_violations(path: PurePosixPath, tree: ast.AST) -> set[str]:
    violations: set[str] = set()
    aliases = _aliases(tree)
    for node in ast.walk(tree):
        imported_names: list[str] = []
        if isinstance(node, ast.Import):
            imported_names.extend(imported.name for imported in node.names)
        elif isinstance(node, ast.ImportFrom):
            module, _error = _absolute_from_module(path, node)
            if module:
                imported_names.append(module)
                imported_names.extend(
                    f"{module}.{imported.name}" for imported in node.names if imported.name != "*"
                )
        for imported_name in imported_names:
            if forbidden := _is_forbidden(imported_name):
                violations.add(_display(path, f"forbidden import: {forbidden}"))

        qualified = _qualified_name(node, aliases)
        if qualified in _DYNAMIC_IMPORTS:
            violations.add(_display(path, "dynamic import"))
        if qualified in _ENVIRONMENT_READS or (
            qualified is not None and qualified.startswith("os.environ.")
        ):
            violations.add(_display(path, "environment read"))
    return violations


def _local_dependencies(
    bundle_root: Path, path: PurePosixPath, tree: ast.AST
) -> tuple[set[PurePosixPath], set[str]]:
    dependencies: set[PurePosixPath] = set()
    violations: set[str] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        package_imports: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(imported.name for imported in node.names if _is_local(imported.name))
        elif isinstance(node, ast.ImportFrom):
            module, error = _absolute_from_module(path, node)
            if error:
                violations.add(_display(path, error))
                continue
            if module is None or not _is_local(module):
                continue
            modules.append(module)
            package_imports.extend(
                f"{module}.{imported.name}" for imported in node.names if imported.name != "*"
            )

        for module in modules:
            resolved = _existing_module_paths(bundle_root, module)
            if not resolved:
                violations.add(_display(path, f"unresolved local import: {module}"))
                continue
            dependencies.update(resolved)
            if resolved[-1].name == "__init__.py":
                for imported_module in package_imports:
                    imported_paths = _existing_module_paths(bundle_root, imported_module)
                    if imported_paths:
                        dependencies.update(imported_paths)
                    else:
                        violations.add(
                            _display(path, f"unresolved local import: {imported_module}")
                        )
    return dependencies, violations


def _parse_source(bundle_root: Path, path: PurePosixPath) -> tuple[ast.AST | None, str | None]:
    try:
        source_path = _contained_path(bundle_root, path)
        if not source_path.is_file():
            return None, _display(path, "missing Python source")
        source = source_path.read_bytes().decode("utf-8")
        return ast.parse(source, filename=path.as_posix()), None
    except ImportBoundaryError as error:
        return None, str(error)
    except UnicodeDecodeError:
        return None, _display(path, "source decode error")
    except SyntaxError:
        return None, _display(path, "syntax error")
    except OSError:
        return None, _display(path, "cannot read Python source")


def _scan(
    bundle_root: Path, entrypoint: PurePosixPath = PurePosixPath("space/app.py")
) -> _ScanResult:
    try:
        _safe_entrypoint(entrypoint)
    except ImportBoundaryError as error:
        return _ScanResult((), (str(error),))

    pending = [entrypoint]
    visited: set[PurePosixPath] = set()
    violations: set[str] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        tree, error = _parse_source(bundle_root, path)
        if error:
            violations.add(error)
            continue
        assert tree is not None
        violations.update(_capability_violations(path, tree))
        try:
            dependencies, dependency_violations = _local_dependencies(bundle_root, path, tree)
        except ImportBoundaryError as dependency_error:
            violations.add(str(dependency_error))
            continue
        violations.update(dependency_violations)
        pending.extend(sorted(dependencies - visited, reverse=True))
    return _ScanResult(tuple(sorted(visited)), tuple(sorted(violations)))


def public_import_closure(
    bundle_root: Path, entrypoint: PurePosixPath = PurePosixPath("space/app.py")
) -> tuple[PurePosixPath, ...]:
    """Return the deterministic local Python import closure for the public app."""
    result = _scan(bundle_root, entrypoint)
    structural = [
        violation
        for violation in result.violations
        if "forbidden import:" not in violation
        and not violation.endswith("environment read")
        and not violation.endswith("dynamic import")
    ]
    if structural:
        raise ImportBoundaryError(structural[0])
    return result.paths


def verify_public_import_boundary(bundle_root: Path) -> list[str]:
    """Return sorted violations in the public app's transitive local import closure."""
    return list(_scan(bundle_root).violations)
