from __future__ import annotations

from pathlib import Path

import pytest

from taxmind.bootstrap.settings import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        app_debug=False,
        log_dir=tmp_path / "logs",
        build_sha="test-build",
    )
