from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_multipart_manual_upload_without_publish_status_input(
    tmp_path: Path,
) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    upload_path = schema["paths"]["/api/v1/knowledge/uploads"]["post"]
    content = upload_path["requestBody"]["content"]
    assert "multipart/form-data" in content
    reference = content["multipart/form-data"]["schema"]["$ref"]
    schema_name = reference.rsplit("/", maxsplit=1)[-1]
    properties = schema["components"]["schemas"][schema_name]["properties"]
    assert {"source_site_id", "title", "canonical_url", "file"} <= set(properties)
    assert "policy_status" not in properties
    assert "review_status" not in properties
