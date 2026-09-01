from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.audit.application.service import AuditSearchQuery, AuditService
from taxmind.modules.audit.domain import AuditLogView
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["audit"])


class AuditLogData(BaseModel):
    id: str
    action_code: str
    resource_type: str
    resource_id: str | None
    actor_user_id: str | None
    request_id: str
    result: str
    summary_safe: str | None
    occurred_at: datetime


class AuditLogSearchResponse(BaseModel):
    data: list[AuditLogData]
    meta: ResponseMeta


def _service(request: Request) -> AuditService:
    service = cast(dict[str, object], request.app.state.services).get("audit")
    if not isinstance(service, AuditService):
        raise RuntimeError("audit service is not configured")
    return service


@router.get("/audit-logs", response_model=AuditLogSearchResponse)
async def search_audit_logs(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    resource_type: str | None = None,
    resource_id: str | None = None,
    action_code: str | None = None,
    actor_user_id: str | None = None,
    occurred_after: datetime | None = None,
    occurred_before: datetime | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditLogSearchResponse:
    results = await _service(request).search(
        AuditSearchQuery(
            resource_type=resource_type,
            resource_id=resource_id,
            action_code=action_code,
            actor_user_id=actor_user_id,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            cursor=cursor,
            limit=limit,
        ),
        principal,
    )
    return AuditLogSearchResponse(
        data=[AuditLogData(**_data(item)) for item in results],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


def _data(item: AuditLogView) -> dict[str, object]:
    return {name: getattr(item, name) for name in AuditLogData.model_fields}
