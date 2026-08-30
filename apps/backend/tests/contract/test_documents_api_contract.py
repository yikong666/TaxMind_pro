from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_document_review_and_exact_search_routes(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/knowledge/documents" in schema["paths"]
    assert "/api/v1/knowledge/document-versions/{version_id}/submit-review" in schema["paths"]
    assert "/api/v1/knowledge/document-versions/{version_id}/publish" in schema["paths"]
    assert "/api/v1/policies/search" in schema["paths"]
