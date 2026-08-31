from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_source_registration_and_listing_without_org_input(
    tmp_path: Path,
) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    source_path = schema["paths"]["/api/v1/knowledge/sources"]
    assert {"get", "post"} <= set(source_path)
    request_reference = source_path["post"]["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    request_schema_name = request_reference.rsplit("/", maxsplit=1)[-1]
    request_properties = schema["components"]["schemas"][request_schema_name]["properties"]
    assert "org_id" not in request_properties
    assert "status" not in request_properties


def test_openapi_contains_ingestion_job_status_route(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/knowledge/jobs/{job_id}" in schema["paths"]
