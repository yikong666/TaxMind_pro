from __future__ import annotations

import contextvars
import json
import logging
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from taxmind.bootstrap.settings import Settings

_LOG_CONTEXT: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "taxmind_log_context", default=None
)
_SENSITIVE_VALUE = re.compile(
    r"(?i)(password|token|secret|api[_-]?key|authorization)\s*[:=]\s*([^\s,;]+)"
)


def redact_log_message(message: str) -> str:
    return _SENSITIVE_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", message)


def bind_log_context(**values: str | None) -> contextvars.Token[dict[str, str] | None]:
    current = dict(_LOG_CONTEXT.get() or {})
    current.update({key: value for key, value in values.items() if value is not None})
    return _LOG_CONTEXT.set(current)


def reset_log_context(token: contextvars.Token[dict[str, str] | None]) -> None:
    _LOG_CONTEXT.reset(token)


class ContextFilter(logging.Filter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        context = _LOG_CONTEXT.get() or {}
        defaults: Mapping[str, Any] = {
            "service": self.service,
            "event": record.name,
            "request_id": context.get("request_id", ""),
            "task_id": context.get("task_id", ""),
            "run_id": context.get("run_id", ""),
            "case_id": context.get("case_id", ""),
            "org_id": context.get("org_id", ""),
            "actor_id": context.get("actor_id", ""),
            "duration_ms": None,
            "error_code": "",
        }
        for key, value in defaults.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "service": getattr(record, "service", ""),
            "event": getattr(record, "event", record.name),
            "request_id": getattr(record, "request_id", ""),
            "task_id": getattr(record, "task_id", ""),
            "run_id": getattr(record, "run_id", ""),
            "case_id": getattr(record, "case_id", ""),
            "org_id": getattr(record, "org_id", ""),
            "actor_id": getattr(record, "actor_id", ""),
            "duration_ms": getattr(record, "duration_ms", None),
            "error_code": getattr(record, "error_code", ""),
            "message": redact_log_message(record.getMessage()),
        }
        if record.exc_info is not None and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class ReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return (
            f"{timestamp} {record.levelname:<7} {getattr(record, 'service', '')} "
            f"event={getattr(record, 'event', record.name)} "
            f"request_id={getattr(record, 'request_id', '') or '-'} "
            f"{redact_log_message(record.getMessage())}"
        )


def _managed_handler(handler: logging.Handler, name: str) -> logging.Handler:
    handler.set_name(f"taxmind-{name}")
    return handler


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in tuple(logger.handlers):
        if handler.get_name().startswith("taxmind-"):
            logger.removeHandler(handler)
            handler.close()


def configure_logging(settings: Settings, *, service: str = "api") -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("taxmind")
    _remove_managed_handlers(logger)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    context_filter = ContextFilter(service)
    console = _managed_handler(logging.StreamHandler(), "console")
    console.addFilter(context_filter)
    console.setFormatter(JsonFormatter() if settings.log_json else ReadableFormatter())

    file_handler = _managed_handler(
        TimedRotatingFileHandler(
            log_dir / f"{service}.log",
            when="midnight",
            interval=1,
            backupCount=14,
            encoding="utf-8",
            utc=True,
        ),
        "file",
    )
    file_handler.addFilter(context_filter)
    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(console)
    logger.addHandler(file_handler)
