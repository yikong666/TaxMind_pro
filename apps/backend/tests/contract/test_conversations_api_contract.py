from __future__ import annotations

from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_conversation_message_and_context_routes(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/cases/{case_id}/conversations" in schema["paths"]
    assert "/api/v1/conversations/{conversation_id}/messages" in schema["paths"]
    assert "/api/v1/conversations/{conversation_id}/context" in schema["paths"]
    assert "idempotency_key" in str(schema["components"]["schemas"])
    assert "memory_source" in str(schema["components"]["schemas"])
