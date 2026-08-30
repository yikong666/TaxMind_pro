from __future__ import annotations

import json
import logging
from pathlib import Path

from taxmind.bootstrap.logging import (
    bind_log_context,
    configure_logging,
    redact_log_message,
    reset_log_context,
)
from taxmind.bootstrap.settings import Settings


def test_redact_log_message_masks_sensitive_assignments() -> None:
    message = "token=abc password:secret normal=value"

    assert redact_log_message(message) == "token=[REDACTED] password=[REDACTED] normal=value"


def test_configure_logging_writes_structured_file(tmp_path: Path) -> None:
    settings = Settings(app_env="test", log_dir=tmp_path, log_json=True)
    configure_logging(settings)
    logger = logging.getLogger("taxmind.test")
    token = bind_log_context(request_id="request-123")
    try:
        logger.info(
            "password=secret lifecycle",
            extra={"event": "test.completed", "duration_ms": 12.5},
        )
    finally:
        reset_log_context(token)
    for handler in logging.getLogger("taxmind").handlers:
        handler.flush()

    payload = json.loads((tmp_path / "api.log").read_text(encoding="utf-8").strip())
    assert payload["event"] == "test.completed"
    assert payload["request_id"] == "request-123"
    assert payload["duration_ms"] == 12.5
    assert payload["message"] == "password=[REDACTED] lifecycle"