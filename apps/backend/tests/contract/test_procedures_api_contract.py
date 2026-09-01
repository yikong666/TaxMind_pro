from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_published_procedure_search_contract(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()
    assert "/api/v1/procedures/search" in schema["paths"]
    assert "ProcedureSearchResponse" in schema["components"]["schemas"]
