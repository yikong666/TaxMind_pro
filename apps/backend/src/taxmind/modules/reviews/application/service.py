from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from taxmind.modules.reviews.domain import (
    ReviewActionRecord,
    ReviewDecision,
    ReviewTaskDetail,
    ReviewTaskRecord,
    aggregate_decisions,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class ReviewsRepository(Protocol):
    async def get_active_by_case_profile(
        self, org_id: str, case_id: str, profile_version: int
    ) -> ReviewTaskRecord | None: ...

    async def create_task(self, task: ReviewTaskRecord) -> None: ...

    async def list_tasks(self, org_id: str, *, status: str | None) -> list[ReviewTaskRecord]: ...

    async def get_task(
        self, task_id: str, org_id: str, *, lock: bool = False
    ) -> ReviewTaskRecord | None: ...

    async def create_action(self, action: ReviewActionRecord) -> None: ...

    async def list_actions(self, task_id: str) -> list[ReviewActionRecord]: ...

    async def set_task(self, task: ReviewTaskRecord) -> None: ...

    async def create_audit_log(
        self,
        *,
        org_id: str,
        actor_user_id: str,
        action_code: str,
        resource_id: str,
        request_id: str,
        occurred_at: datetime,
    ) -> None: ...


class ReviewsUnitOfWork(Protocol):
    @property
    def repository(self) -> ReviewsRepository | None: ...

    async def __aenter__(self) -> ReviewsUnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    async def commit(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CreateReviewTaskCommand:
    case_id: str
    profile_version: int
    query_run_id: str | None
    package_summary: dict[str, object]
    request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RecordReviewActionCommand:
    task_id: str
    decision: ReviewDecision
    comment: str | None
    expected_version_no: int
    request_id: str
    occurred_at: datetime


class ReviewService:
    def __init__(self, *, uow_factory: Callable[[], ReviewsUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def create_task(
        self,
        command: CreateReviewTaskCommand,
        principal: Principal,
    ) -> ReviewTaskRecord:
        _require_cases_read(principal)
        if command.profile_version < 1:
            raise DomainError(code="VALIDATION_FAILED", message="画像版本无效")
        now = command.occurred_at
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            existing = await repository.get_active_by_case_profile(
                principal.org_id,
                command.case_id,
                command.profile_version,
            )
            if existing is not None:
                raise DomainError(
                    code="RESOURCE_CONFLICT", message="该事项画像已有进行中的审核任务"
                )
            task = ReviewTaskRecord(
                id=new_id(),
                org_id=principal.org_id,
                case_id=command.case_id,
                profile_version=command.profile_version,
                query_run_id=command.query_run_id,
                submitted_by=principal.user_id,
                assigned_to=None,
                status="pending_review",
                priority="normal",
                package_summary=command.package_summary,
                version_no=1,
                submitted_at=now,
                resolved_at=None,
            )
            await repository.create_task(task)
            await repository.create_audit_log(
                org_id=task.org_id,
                actor_user_id=principal.user_id,
                action_code="review.task.created",
                resource_id=task.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
            return task

    async def list_tasks(
        self,
        *,
        status: str | None,
        principal: Principal,
    ) -> list[ReviewTaskRecord]:
        _require_cases_review(principal)
        async with self._uow_factory() as uow:
            return await _repository(uow).list_tasks(principal.org_id, status=status)

    async def get_task_detail(self, task_id: str, principal: Principal) -> ReviewTaskDetail:
        _require_cases_review(principal)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            task = await repository.get_task(task_id, principal.org_id)
            if task is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="审核任务不存在或无权访问")
            return ReviewTaskDetail(task=task, actions=await repository.list_actions(task.id))

    async def record_action(
        self,
        command: RecordReviewActionCommand,
        principal: Principal,
    ) -> ReviewTaskRecord:
        _require_cases_review(principal)
        comment = _review_comment(command.decision, command.comment)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            task = await repository.get_task(command.task_id, principal.org_id, lock=True)
            if task is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="审核任务不存在或无权访问")
            if task.submitted_by == principal.user_id:
                raise DomainError(code="AUTH_FORBIDDEN", message="提交人不得审核自己的任务")
            if task.status not in {"pending_review", "returned", "escalated"}:
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="当前审核任务不能再次处理")
            if task.version_no != command.expected_version_no:
                raise DomainError(
                    code="RESOURCE_VERSION_CONFLICT", message="审核任务已更新; 请刷新后重试"
                )
            action = ReviewActionRecord(
                id=new_id(),
                task_id=task.id,
                action_no=task.version_no,
                decision=command.decision,
                comment_safe=comment,
                actor_user_id=principal.user_id,
                occurred_at=command.occurred_at,
            )
            next_status = aggregate_decisions([action])
            updated = replace(
                task,
                status=next_status,
                assigned_to=principal.user_id if next_status == "escalated" else task.assigned_to,
                version_no=task.version_no + 1,
                resolved_at=command.occurred_at if next_status == "approved" else None,
            )
            await repository.create_action(action)
            await repository.set_task(updated)
            await repository.create_audit_log(
                org_id=task.org_id,
                actor_user_id=principal.user_id,
                action_code="review.task.action_recorded",
                resource_id=task.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
            )
            await uow.commit()
            return updated


def _repository(uow: ReviewsUnitOfWork) -> ReviewsRepository:
    if uow.repository is None:
        raise RuntimeError("reviews repository is unavailable")
    return uow.repository


def _require_cases_read(principal: Principal) -> None:
    if not principal.has_permission("cases:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无审核任务提交权限")


def _require_cases_review(principal: Principal) -> None:
    if not principal.has_permission("cases:review"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无审核权限")


def _review_comment(decision: ReviewDecision, comment: str | None) -> str | None:
    normalized = comment.strip() if comment else ""
    if decision in {"returned", "escalated"} and len(normalized) < 3:
        raise DomainError(code="VALIDATION_FAILED", message="退回或升级审核必须填写原因")
    if len(normalized) > 1000:
        raise DomainError(code="VALIDATION_FAILED", message="审核意见不能超过 1000 个字符")
    return normalized or None
