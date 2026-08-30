from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse

from taxmind.shared.contracts.api import ErrorBody, ErrorEnvelope, ResponseMeta
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id

logger = logging.getLogger("taxmind.errors")

_STATUS_BY_CODE = {
    "VALIDATION_FAILED": 400,
    "AUTH_REQUIRED": 401,
    "AUTH_FORBIDDEN": 403,
    "TENANT_SCOPE_VIOLATION": 403,
    "RESOURCE_NOT_FOUND": 404,
    "RESOURCE_CONFLICT": 409,
    "RESOURCE_VERSION_CONFLICT": 409,
    "CONFIGURATION_INVALID": 500,
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", new_id())


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> ORJSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or {},
            retryable=retryable,
        ),
        meta=ResponseMeta(request_id=_request_id(request)),
    )
    return ORJSONResponse(status_code=status_code, content=envelope.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> ORJSONResponse:
        status_code = _STATUS_BY_CODE.get(exc.code, 422)
        return _error_response(
            request=request,
            status_code=status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        fields = [
            {"location": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
            for error in exc.errors()
        ]
        return _error_response(
            request=request,
            status_code=400,
            code="VALIDATION_FAILED",
            message="请求参数校验失败",
            details={"fields": fields},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> ORJSONResponse:
        logger.error(
            "unexpected application error",
            extra={"event": "application.error", "error_code": "INTERNAL_ERROR"},
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _error_response(
            request=request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="系统暂时无法完成请求，请稍后重试",  # noqa: RUF001
            retryable=True,
        )