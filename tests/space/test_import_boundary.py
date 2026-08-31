from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from release_checks.space_bundle import export_space_bundle
from release_checks.space_imports import public_import_closure, verify_public_import_boundary


def write_python(bundle_root: Path, relative: str, source: str | bytes) -> None:
    path = bundle_root.joinpath(*PurePosixPath(relative).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        path.write_bytes(source)
    else:
        path.write_text(source, encoding="utf-8")


def write_minimal_bundle(bundle_root: Path, source: str | bytes) -> None:
    write_python(bundle_root, "space/app.py", source)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("import gateway.app\n", "forbidden import: gateway"),
        ("from dashboard import state\n", "forbidden import: dashboard.state"),
        ("import socket\n", "forbidden import: socket"),
        ("import subprocess\n", "forbidden import: subprocess"),
        ("import os\nVALUE = os.getenv('GATEWAY_API_KEY')\n", "environment read"),
        ("import importlib\nimportlib.import_module('gateway.app')\n", "dynamic import"),
        ("VALUE = __import__('socket')\n", "dynamic import"),
        ("import urllib.request\n", "forbidden import: urllib.request"),
        (
            "import os as operating_system\nVALUE = operating_system.environ['KEY']\n",
            "environment read",
        ),
        (
            "from importlib import import_module\nVALUE = import_module('socket')\n",
            "dynamic import",
        ),
    ],
)
def test_import_boundary_rejects_capabilities(tmp_path: Path, source: str, message: str) -> None:
    write_minimal_bundle(tmp_path, source)
    assert any(message in item for item in verify_public_import_boundary(tmp_path))


def test_nested_import_cannot_mask_live_capability_alias(tmp_path: Path) -> None:
    write_minimal_bundle(
        tmp_path,
        "import os as module\n"
        "def unrelated():\n"
        "    import json as module\n"
        "VALUE = module.getenv('KEY')\n",
    )

    assert verify_public_import_boundary(tmp_path) == ["space/app.py: environment read"]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("from builtins import __import__\n", "dynamic import"),
        ("from importlib import import_module as loader\n", "dynamic import"),
        ("from os import getenv\n", "environment read"),
        ("from os import environ\n", "environment read"),
    ],
)
def test_capability_bearing_import_from_is_rejected(
    tmp_path: Path, source: str, message: str
) -> None:
    write_minimal_bundle(tmp_path, source)

    assert verify_public_import_boundary(tmp_path) == [f"space/app.py: {message}"]


@pytest.mark.parametrize(
    "source",
    [
        "from importlib import *\nVALUE = import_module('socket')\n",
        "from os import *\nVALUE = getenv('KEY')\n",
    ],
)
def test_capability_star_import_is_rejected(tmp_path: Path, source: str) -> None:
    write_minimal_bundle(tmp_path, source)

    assert verify_public_import_boundary(tmp_path) == ["space/app.py: unsafe star import"]


def test_transitive_local_capability_star_reexport_is_rejected(tmp_path: Path) -> None:
    write_minimal_bundle(
        tmp_path,
        "from dashboard.helper import import_module\nVALUE = import_module('gateway.app')\n",
    )
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(tmp_path, "dashboard/helper.py", "from importlib import *\n")

    assert verify_public_import_boundary(tmp_path) == ["dashboard/helper.py: unsafe star import"]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "from pathlib import Path\nVALUE = Path('/etc/passwd').read_text()\n",
            "arbitrary path read",
        ),
        (
            "import http.client\nVALUE = http.client.HTTPSConnection('example.com')\n",
            "forbidden import: http.client",
        ),
        ("import os\nVALUE = os.system('whoami')\n", "process execution"),
        ("import _sqlite3\n", "forbidden import: _sqlite3"),
        ("VALUE = open('/etc/passwd').read()\n", "arbitrary path read"),
        (
            "from pathlib import Path\nSECRET = Path('/etc/passwd')\nVALUE = SECRET.read_text()\n",
            "arbitrary path read",
        ),
        ("import ftplib\nVALUE = ftplib.FTP('example.com')\n", "forbidden import: ftplib"),
        ("import os\nVALUE = os.popen('whoami')\n", "process execution"),
        ("import dbm\nVALUE = dbm.open('local.db')\n", "forbidden import: dbm"),
    ],
)
def test_alternate_standard_library_capabilities_are_rejected(
    tmp_path: Path, source: str, message: str
) -> None:
    write_minimal_bundle(tmp_path, source)

    assert verify_public_import_boundary(tmp_path) == [f"space/app.py: {message}"]


def test_local_capability_reexport_is_rejected(tmp_path: Path) -> None:
    write_minimal_bundle(
        tmp_path,
        "from dashboard.helper import loader\nVALUE = loader('gateway.app')\n",
    )
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(
        tmp_path,
        "dashboard/helper.py",
        "from importlib import import_module as loader\n",
    )

    assert verify_public_import_boundary(tmp_path) == ["dashboard/helper.py: dynamic import"]


def test_import_boundary_rejects_module_path_escape(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from ..outside import VALUE\n")

    violations = verify_public_import_boundary(tmp_path)

    assert any("import escapes bundle" in item for item in violations)


def test_import_boundary_rejects_unresolved_local_import(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from dashboard import missing\n")
    write_python(tmp_path, "dashboard/__init__.py", "")

    violations = verify_public_import_boundary(tmp_path)

    assert any("unresolved local import" in item for item in violations)


def test_import_boundary_accepts_static_package_export(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from dashboard import VALUE\n")
    write_python(tmp_path, "dashboard/__init__.py", "VALUE = 1\n")

    assert verify_public_import_boundary(tmp_path) == []
    assert public_import_closure(tmp_path) == (
        PurePosixPath("dashboard/__init__.py"),
        PurePosixPath("space/app.py"),
    )


def test_import_boundary_accepts_module_control_flow_package_export(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from dashboard import VALUE\n")
    write_python(tmp_path, "dashboard/__init__.py", "if True:\n    VALUE = 1\n")

    assert verify_public_import_boundary(tmp_path) == []


def test_function_local_name_is_not_a_package_export(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from dashboard import VALUE\n")
    write_python(
        tmp_path,
        "dashboard/__init__.py",
        "def configure():\n    VALUE = 1\n",
    )

    assert verify_public_import_boundary(tmp_path) == [
        "space/app.py: unresolved local import: dashboard.VALUE"
    ]


def test_import_boundary_terminates_on_cycle(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "import dashboard.first\n")
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(tmp_path, "dashboard/first.py", "import dashboard.second\nimport socket\n")
    write_python(tmp_path, "dashboard/second.py", "import dashboard.first\nimport subprocess\n")

    assert verify_public_import_boundary(tmp_path) == [
        "dashboard/first.py: forbidden import: socket",
        "dashboard/second.py: forbidden import: subprocess",
    ]


def test_import_boundary_scans_transitive_local_modules(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "from dashboard.safe import VALUE\n")
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(tmp_path, "dashboard/safe.py", "import socket\nVALUE = 1\n")

    assert verify_public_import_boundary(tmp_path) == [
        "dashboard/safe.py: forbidden import: socket"
    ]


def test_import_boundary_rejects_relative_forbidden_import(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "import dashboard.public\n")
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(tmp_path, "dashboard/public.py", "from . import state\n")
    write_python(tmp_path, "dashboard/state.py", "VALUE = 1\n")

    assert verify_public_import_boundary(tmp_path) == [
        "dashboard/public.py: forbidden import: dashboard.state"
    ]


def test_public_import_closure_is_sorted_and_deduplicates_cycles(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "import dashboard.first\n")
    write_python(tmp_path, "dashboard/__init__.py", "")
    write_python(tmp_path, "dashboard/first.py", "import dashboard.second\n")
    write_python(tmp_path, "dashboard/second.py", "import dashboard.first\n")

    assert public_import_closure(tmp_path) == (
        PurePosixPath("dashboard/__init__.py"),
        PurePosixPath("dashboard/first.py"),
        PurePosixPath("dashboard/second.py"),
        PurePosixPath("space/app.py"),
    )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("def broken(:\n", "syntax error"),
        (b"VALUE = '\xff'\n", "source decode error"),
    ],
)
def test_import_boundary_fails_closed_for_unparseable_python(
    tmp_path: Path, source: str | bytes, message: str
) -> None:
    write_minimal_bundle(tmp_path, source)

    assert verify_public_import_boundary(tmp_path) == [f"space/app.py: {message}"]


def test_import_boundary_fails_closed_for_missing_entrypoint(tmp_path: Path) -> None:
    assert verify_public_import_boundary(tmp_path) == ["space/app.py: missing Python source"]


def test_real_exported_bundle_has_zero_import_boundary_violations(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    export_space_bundle(Path.cwd(), bundle_root, "a" * 40)

    assert verify_public_import_boundary(bundle_root) == []
    exported_python = tuple(
        PurePosixPath(path.relative_to(bundle_root).as_posix())
        for path in sorted(bundle_root.rglob("*.py"))
    )
    assert public_import_closure(bundle_root) == exported_python


def test_documentation_words_are_not_capability_violations(tmp_path: Path) -> None:
    write_minimal_bundle(tmp_path, "VALUE = 'public demo'\n")
    (tmp_path / "README.md").write_text(
        "This documentation discusses SQLite and HTTP.\n", encoding="utf-8"
    )

    assert verify_public_import_boundary(tmp_path) == []
