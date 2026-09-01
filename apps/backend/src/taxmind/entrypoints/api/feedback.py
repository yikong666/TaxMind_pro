from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.feedback.application.service import (
    CreateFeedbackCommand,
    FeedbackService,
    HandleFeedbackCommand,
)
from taxmind.modules.feedback.domain import FeedbackDecision, FeedbackItem
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["feedback"])


class FeedbackItemData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    case_id: str | None
    profile_version: int | None
    resource_type: str
    resource_id: str
    location_key: str | None
    error_type: str
    description_safe: str
    status: str
    linked_knowledge_object_id: str | None
    resolution_safe: str | None
    submitted_by: str
    handled_by: str | None
    version_no: int
    submitted_at: datetime
    resolved_at: datetime | None


class FeedbackItemResponse(BaseModel):
    data: FeedbackItemData
    meta: ResponseMeta


class FeedbackListResponse(BaseModel):
    data: list[FeedbackItemData]
    meta: ResponseMeta


class CreateFeedbackRequest(BaseModel):
    case_id: str | None = None
    profile_version: int | None = Field(default=None, ge=1)
    resource_type: str = Field(pattern="^(case|query_run)$")
    resource_id: str = Field(min_length=1, max_length=36)
    location_key: str | None = Field(default=None, max_length=128)
    error_type: str = Field(
        pattern="^(citation_error|policy_scope_error|risk_rule_error|procedure_error|other)$"
    )
    description: str = Field(min_length=3, max_length=1000)


class HandleFeedbackRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|resolved|rejected)$")
    resolution: str = Field(min_length=3, max_length=1000)
    linked_knowledge_object_id: str | None = None
    expected_version_no: int = Field(ge=1)


def _service(request: Request) -> FeedbackService:
    service = cast(dict[str, object], request.app.state.services).get("feedback")
    if not isinstance(service, FeedbackService):
        raise RuntimeError("feedback service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


@router.post("/feedback-items", response_model=FeedbackItemResponse, status_code=201)
async def create_feedback_item(
    payload: CreateFeedbackRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> FeedbackItemResponse:
    item = await _service(request).create(
        CreateFeedbackCommand(
            case_id=payload.case_id,
            profile_version=payload.profile_version,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            location_key=payload.location_key,
            error_type=payload.error_type,
            description=payload.description,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
        ),
        principal,
    )
    return FeedbackItemResponse(data=FeedbackItemData(**_data(item)), meta=_meta(request))


@router.get("/feedback-items", response_model=FeedbackListResponse)
async def list_my_feedback_items(
    request: Request, principal: Annotated[Principal, Depends(current_principal)]
) -> FeedbackListResponse:
    items = await _service(request).list_mine(principal)
    return FeedbackListResponse(
        data=[FeedbackItemData(**_data(item)) for item in items], meta=_meta(request)
    )


@router.post("/feedback-items/{feedback_id}/actions", response_model=FeedbackItemResponse)
async def handle_feedback_item(
    feedback_id: str,
    payload: HandleFeedbackRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> FeedbackItemResponse:
    item = await _service(request).handle(
        HandleFeedbackCommand(
            feedback_id=feedback_id,
            decision=cast(FeedbackDecision, payload.decision),
            resolution=payload.resolution,
            linked_knowledge_object_id=payload.linked_knowledge_object_id,
            expected_version_no=payload.expected_version_no,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
        ),
        principal,
    )
    return FeedbackItemResponse(data=FeedbackItemData(**_data(item)), meta=_meta(request))


def _data(item: FeedbackItem) -> dict[str, object]:
    return {name: getattr(item, name) for name in FeedbackItemData.model_fields}
