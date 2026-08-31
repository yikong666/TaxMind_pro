from __future__ import annotations

import logging
import re
from time import perf_counter

from fastapi import FastAPI, Request, Response

from taxmind.bootstrap.logging import bind_log_context, reset_log_context
from taxmind.shared.domain.ids import new_id

logger = logging.getLogger("taxmind.http")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def _request_id_from(request: Request) -> str:
    supplied = request.headers.get("X-Request-Id", "")
    if _REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return new_id()


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next: object) -> Response:
        request_id = _request_id_from(request)
        request.state.request_id = request_id
        token = bind_log_context(request_id=request_id)
        started = perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)  # type: ignore[operator]
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            duration_ms = round((perf_counter() - started) * 1000, 3)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "request completed",
                extra={
                    "event": "http.request.completed",
                    "duration_ms": duration_ms,
                    "error_code": "" if status_code < 500 else "INTERNAL_ERROR",
                },
            )
            reset_log_context(token)
