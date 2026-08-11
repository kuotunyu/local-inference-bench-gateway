from __future__ import annotations

import pytest

from gateway.registry import build_registry


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"models": []},
        {"models": {}},
        {"models": {"alias": {"backends": []}}},
        {
            "models": {
                "alias": {
                    "max_concurrent": 0,
                    "backends": [
                        {"name": "primary", "base_url": "http://primary.test/v1", "model": "m"}
                    ],
                }
            }
        },
        {"models": {"alias": {"backends": [{"base_url": "http://primary.test/v1", "model": "m"}]}}},
        {
            "models": {
                "alias": {
                    "backends": [
                        {"name": "primary", "base_url": "ftp://primary.test/v1", "model": "m"}
                    ]
                }
            }
        },
    ],
)
def test_invalid_registry_config_is_rejected_at_startup(data):
    with pytest.raises(ValueError):
        build_registry(data)
