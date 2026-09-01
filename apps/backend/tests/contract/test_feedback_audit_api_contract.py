from pathlib import Path

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app


def test_openapi_contains_feedback_and_safe_audit_contracts(tmp_path: Path) -> None:
    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    assert "/api/v1/audit-logs" in schema["paths"]
    assert "/api/v1/feedback-items" in schema["paths"]
    assert "AuditLogData" in schema["components"]["schemas"]
    assert "before_json" not in schema["components"]["schemas"]["AuditLogData"]["properties"]
