from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_controlled_query_run_submission_and_status_routes(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/cases/{case_id}/query-runs" in schema["paths"]
    assert "/api/v1/query-runs/{run_id}" in schema["paths"]
    assert "RuleResultData" in schema["components"]["schemas"]
    assert "follow_up_fact_keys" in str(schema["components"]["schemas"])
