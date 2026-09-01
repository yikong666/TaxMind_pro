from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from taxmind.modules.feedback.domain import FeedbackDecision, FeedbackErrorType, FeedbackItem
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

_ERROR_TYPES = frozenset(
    {"citation_error", "policy_scope_error", "risk_rule_error", "procedure_error", "other"}
)


class FeedbackRepository(Protocol):
    async def resource_is_visible(
        self, *, org_id: str, resource_type: str, resource_id: str, case_id: str | None
    ) -> bool: ...
    async def create(self, item: FeedbackItem) -> None: ...
    async def list_for_submitter(self, org_id: str, submitted_by: str) -> list[FeedbackItem]: ...
    async def get(
        self, feedback_id: str, org_id: str, *, lock: bool = False
    ) -> FeedbackItem | None: ...
    async def set(self, item: FeedbackItem) -> None: ...
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


class FeedbackUnitOfWork(Protocol):
    @property
    def repository(self) -> FeedbackRepository | None: ...
    async def __aenter__(self) -> FeedbackUnitOfWork: ...
    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...
    async def commit(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CreateFeedbackCommand:
    case_id: str | None
    profile_version: int | None
    resource_type: str
    resource_id: str
    location_key: str | None
    error_type: str
    description: str
    request_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class HandleFeedbackCommand:
    feedback_id: str
    decision: FeedbackDecision
    resolution: str
    linked_knowledge_object_id: str | None
    expected_version_no: int
    request_id: str
    occurred_at: datetime


class FeedbackService:
    def __init__(self, *, uow_factory: Callable[[], FeedbackUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def create(self, command: CreateFeedbackCommand, principal: Principal) -> FeedbackItem:
        _require(principal, "feedback:write", "当前角色无反馈提交权限")
        error_type = _error_type(command.error_type)
        description = _safe_text(command.description, "反馈说明")
        if command.profile_version is not None and command.profile_version < 1:
            raise DomainError(code="VALIDATION_FAILED", message="画像版本无效")
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            if not await repository.resource_is_visible(
                org_id=principal.org_id,
                resource_type=command.resource_type,
                resource_id=command.resource_id,
                case_id=command.case_id,
            ):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="反馈资源不存在或无权访问")
            item = FeedbackItem(
                id=new_id(),
                org_id=principal.org_id,
                case_id=command.case_id,
                profile_version=command.profile_version,
                resource_type=command.resource_type,
                resource_id=command.resource_id,
                location_key=_optional_text(command.location_key),
                error_type=error_type,
                description_safe=description,
                status="submitted",
                linked_knowledge_object_id=None,
                resolution_safe=None,
                submitted_by=principal.user_id,
                handled_by=None,
                version_no=1,
                submitted_at=command.occurred_at,
                resolved_at=None,
            )
            await repository.create(item)
            await repository.create_audit_log(
                org_id=item.org_id,
                actor_user_id=principal.user_id,
                action_code="feedback.item.submitted",
                resource_id=item.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
            )
            await uow.commit()
            return item

    async def list_mine(self, principal: Principal) -> list[FeedbackItem]:
        _require(principal, "feedback:write", "当前角色无反馈查看权限")
        async with self._uow_factory() as uow:
            return await _repository(uow).list_for_submitter(principal.org_id, principal.user_id)

    async def handle(self, command: HandleFeedbackCommand, principal: Principal) -> FeedbackItem:
        _require(principal, "feedback:manage", "当前角色无反馈处理权限")
        resolution = _safe_text(command.resolution, "处理说明")
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            item = await repository.get(command.feedback_id, principal.org_id, lock=True)
            if item is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="反馈不存在或无权访问")
            if item.version_no != command.expected_version_no:
                raise DomainError(
                    code="RESOURCE_VERSION_CONFLICT", message="反馈已更新; 请刷新后重试"
                )
            if item.status in {"resolved", "rejected"}:
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="已结束的反馈不能再次处理")
            if command.decision == "resolved" and not command.linked_knowledge_object_id:
                raise DomainError(code="VALIDATION_FAILED", message="解决反馈必须关联知识修订对象")
            updated = replace(
                item,
                status=command.decision,
                resolution_safe=resolution,
                linked_knowledge_object_id=command.linked_knowledge_object_id,
                handled_by=principal.user_id,
                version_no=item.version_no + 1,
                resolved_at=command.occurred_at
                if command.decision in {"resolved", "rejected"}
                else None,
            )
            await repository.set(updated)
            await repository.create_audit_log(
                org_id=item.org_id,
                actor_user_id=principal.user_id,
                action_code=f"feedback.item.{command.decision}",
                resource_id=item.id,
                request_id=command.request_id,
                occurred_at=command.occurred_at,
            )
            await uow.commit()
            return updated


def _repository(uow: FeedbackUnitOfWork) -> FeedbackRepository:
    if uow.repository is None:
        raise RuntimeError("feedback repository is unavailable")
    return uow.repository


def _require(principal: Principal, permission: str, message: str) -> None:
    if not principal.has_permission(permission):
        raise DomainError(code="AUTH_FORBIDDEN", message=message)


def _error_type(value: str) -> FeedbackErrorType:
    if value not in _ERROR_TYPES:
        raise DomainError(code="VALIDATION_FAILED", message="反馈错误类型无效")
    return value  # type: ignore[return-value]


def _safe_text(value: str, label: str) -> str:
    normalized = value.strip()
    if not 3 <= len(normalized) <= 1000:
        raise DomainError(code="VALIDATION_FAILED", message=f"{label}长度必须为 3 到 1000 个字符")
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = value.strip() if value else ""
    return normalized or None
