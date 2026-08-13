from __future__ import annotations

import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HERO_ASSET = REPO_ROOT / "docs" / "assets" / "operations-console-overview.png"


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def test_operations_console_hero_is_readable_and_publication_safe():
    assert HERO_ASSET.is_file()
    width, height = _png_dimensions(HERO_ASSET)
    assert 1440 <= width <= 1800
    assert 800 <= height <= 1100
    assert HERO_ASSET.stat().st_size < 1024 * 1024
