from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.cases.application.service import CasesService
from taxmind.modules.query.application.service import QueryRunService
from taxmind.modules.reviews.application.service import (
    CreateReviewTaskCommand,
    RecordReviewActionCommand,
    ReviewService,
)
from taxmind.modules.reviews.domain import ReviewDecision, ReviewTaskDetail, ReviewTaskRecord
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["reviews"])


class ReviewTaskData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    case_id: str
    profile_version: int
    query_run_id: str | None
    submitted_by: str
    assigned_to: str | None
    status: str
    priority: str
    package_summary: dict[str, object]
    version_no: int
    submitted_at: datetime
    resolved_at: datetime | None


class ReviewActionData(BaseModel):
    id: str
    action_no: int
    decision: str
    comment_safe: str | None
    actor_user_id: str
    occurred_at: datetime


class ReviewTaskResponse(BaseModel):
    data: ReviewTaskData
    meta: ResponseMeta


class ReviewQueueResponse(BaseModel):
    data: list[ReviewTaskData]
    meta: ResponseMeta


class ReviewTaskDetailData(ReviewTaskData):
    actions: list[ReviewActionData]


class ReviewTaskDetailResponse(BaseModel):
    data: ReviewTaskDetailData
    meta: ResponseMeta


class CreateReviewTaskRequest(BaseModel):
    query_run_id: str | None = None


class ReviewActionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|conditionally_approved|returned|escalated)$")
    comment: str | None = Field(default=None, max_length=1000)
    expected_version_no: int = Field(ge=1)


def _service(request: Request) -> ReviewService:
    service = cast(dict[str, object], request.app.state.services).get("reviews")
    if not isinstance(service, ReviewService):
        raise RuntimeError("reviews service is not configured")
    return service


def _cases(request: Request) -> CasesService:
    service = cast(dict[str, object], request.app.state.services).get("cases")
    if not isinstance(service, CasesService):
        raise RuntimeError("cases service is not configured")
    return service


def _query_runs(request: Request) -> QueryRunService:
    service = cast(dict[str, object], request.app.state.services).get("query_runs")
    if not isinstance(service, QueryRunService):
        raise RuntimeError("query runs service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


@router.post("/cases/{case_id}/review-tasks", response_model=ReviewTaskResponse, status_code=201)
async def create_review_task(
    case_id: str,
    payload: CreateReviewTaskRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ReviewTaskResponse:
    detail = await _cases(request).get_case(case_id, principal)
    summary: dict[str, object] = {
        "profile_version": detail.profile.profile_version,
        "fact_keys": [
            fact.fact_key for fact in detail.facts if fact.confirmation_status == "confirmed"
        ],
    }
    if payload.query_run_id is not None:
        run = _query_runs(request).get(payload.query_run_id)
        if run is None or run.org_id != principal.org_id or run.case_id != case_id:
            raise DomainError(code="RESOURCE_NOT_FOUND", message="查询运行不存在或无权访问")
        summary["rule_version_ids"] = [result.rule_version_id for result in run.rule_results]
        summary["follow_up_fact_keys"] = list(run.follow_up_fact_keys)
    task = await _service(request).create_task(
        CreateReviewTaskCommand(
            case_id=case_id,
            profile_version=detail.profile.profile_version,
            query_run_id=payload.query_run_id,
            package_summary=summary,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
        ),
        principal,
    )
    return ReviewTaskResponse(data=_task_data(task), meta=_meta(request))


@router.get("/review-tasks", response_model=ReviewQueueResponse)
async def list_review_tasks(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    status: str | None = None,
) -> ReviewQueueResponse:
    tasks = await _service(request).list_tasks(status=status, principal=principal)
    return ReviewQueueResponse(data=[_task_data(task) for task in tasks], meta=_meta(request))


@router.get("/review-tasks/{task_id}", response_model=ReviewTaskDetailResponse)
async def get_review_task(
    task_id: str, request: Request, principal: Annotated[Principal, Depends(current_principal)]
) -> ReviewTaskDetailResponse:
    detail = await _service(request).get_task_detail(task_id, principal)
    return ReviewTaskDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post("/review-tasks/{task_id}/actions", response_model=ReviewTaskResponse)
async def record_review_action(
    task_id: str,
    payload: ReviewActionRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ReviewTaskResponse:
    task = await _service(request).record_action(
        RecordReviewActionCommand(
            task_id=task_id,
            decision=cast(ReviewDecision, payload.decision),
            comment=payload.comment,
            expected_version_no=payload.expected_version_no,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
        ),
        principal,
    )
    return ReviewTaskResponse(data=_task_data(task), meta=_meta(request))


def _task_data(task: ReviewTaskRecord) -> ReviewTaskData:
    return ReviewTaskData(**{field: getattr(task, field) for field in ReviewTaskData.model_fields})


def _detail_data(detail: ReviewTaskDetail) -> ReviewTaskDetailData:
    return ReviewTaskDetailData(
        **_task_data(detail.task).model_dump(),
        actions=[
            ReviewActionData(
                **{field: getattr(action, field) for field in ReviewActionData.model_fields}
            )
            for action in detail.actions
        ],
    )
