from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_case_and_immutable_profile_routes(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/cases" in schema["paths"]
    assert "/api/v1/cases/{case_id}" in schema["paths"]
    assert "/api/v1/cases/{case_id}/profiles" in schema["paths"]
    assert "data_classification" in str(schema["components"]["schemas"])
