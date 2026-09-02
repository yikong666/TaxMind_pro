from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_controlled_query_run_submission_and_status_routes(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/cases/{case_id}/query-runs" in schema["paths"]
    assert "/api/v1/query-runs/{run_id}" in schema["paths"]
    event_route = schema["paths"]["/api/v1/query-runs/{run_id}/events"]["get"]
    assert "Last-Event-ID" in str(event_route["parameters"])
    assert "text/event-stream" in event_route["responses"]["200"]["content"]
    assert "RuleResultData" in schema["components"]["schemas"]
    assert "follow_up_fact_keys" in str(schema["components"]["schemas"])
    request = schema["components"]["schemas"]["QueryRunRequest"]
    assert {"query", "conversation_id", "idempotency_key"} <= set(request["required"])
    response = schema["components"]["schemas"]["QueryRunData"]["properties"]
    assert {
        "public_knowledge_snapshot_id",
        "evidence_ids",
        "rule_version_ids",
        "final_answer",
        "error_code",
    } <= set(response)
