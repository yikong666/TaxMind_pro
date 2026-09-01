from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Self, cast

import pytest

from taxmind.modules.audit.application.service import (
    AuditSearchQuery,
    AuditService,
    AuditUnitOfWork,
)
from taxmind.modules.audit.domain import AuditLogView
from taxmind.modules.feedback.application.service import (
    CreateFeedbackCommand,
    FeedbackService,
    HandleFeedbackCommand,
)
from taxmind.modules.feedback.domain import FeedbackItem
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class _AuditRepository:
    async def search(self, org_id: str, query: AuditSearchQuery) -> list[AuditLogView]:
        return []


class _AuditUow:
    def __init__(self) -> None:
        self.repository = _AuditRepository()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _FeedbackRepository:
    def __init__(self) -> None:
        self.created: FeedbackItem | None = None
        self.audit_calls: list[dict[str, object]] = []

    async def resource_is_visible(
        self, *, org_id: str, resource_type: str, resource_id: str, case_id: str | None
    ) -> bool:
        return org_id == "org-1" and resource_type == "query_run" and resource_id == "run-1"

    async def create(self, item: FeedbackItem) -> None:
        self.created = item

    async def create_audit_log(self, **kwargs: object) -> None:
        self.audit_calls.append(kwargs)

    async def list_for_submitter(self, org_id: str, submitted_by: str) -> list[FeedbackItem]:
        return [self.created] if self.created is not None else []

    async def get(
        self, feedback_id: str, org_id: str, *, lock: bool = False
    ) -> FeedbackItem | None:
        return self.created if self.created is not None and self.created.id == feedback_id else None

    async def set(self, item: FeedbackItem) -> None:
        self.created = item


class _FeedbackUow:
    def __init__(self, repository: _FeedbackRepository) -> None:
        self.repository = repository
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _principal(*permissions: str) -> Principal:
    return Principal(
        user_id="user-1",
        org_id="org-1",
        session_id="session-1",
        roles=frozenset({"consultant"}),
        permissions=frozenset(permissions),
    )


async def test_audit_search_requires_audit_read_and_returns_safe_view() -> None:
    service = AuditService(uow_factory=cast(Callable[[], AuditUnitOfWork], _AuditUow))

    with pytest.raises(DomainError) as error:
        await service.search(AuditSearchQuery(), _principal())

    assert error.value.code == "AUTH_FORBIDDEN"


async def test_feedback_submission_validates_visible_resource_redacts_text_and_audits() -> None:
    repository = _FeedbackRepository()
    service = FeedbackService(uow_factory=lambda: _FeedbackUow(repository))

    item = await service.create(
        CreateFeedbackCommand(
            case_id="case-1",
            profile_version=2,
            resource_type="query_run",
            resource_id="run-1",
            location_key="risk-card:RISK-001",
            error_type="citation_error",
            description="请核对引用的政策条款。",
            request_id="request-1",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        _principal("feedback:write"),
    )

    assert item.status == "submitted"
    assert item.description_safe == "请核对引用的政策条款。"
    assert repository.created == item
    assert repository.audit_calls[0]["action_code"] == "feedback.item.submitted"


async def test_feedback_resolution_requires_linked_knowledge_revision_and_uses_version_lock() -> (
    None
):
    repository = _FeedbackRepository()
    service = FeedbackService(uow_factory=lambda: _FeedbackUow(repository))
    item = await service.create(
        CreateFeedbackCommand(
            case_id="case-1",
            profile_version=1,
            resource_type="query_run",
            resource_id="run-1",
            location_key=None,
            error_type="risk_rule_error",
            description="规则依据需要复核。",
            request_id="request-create",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        _principal("feedback:write"),
    )

    with pytest.raises(DomainError) as error:
        await service.handle(
            HandleFeedbackCommand(
                feedback_id=item.id,
                decision="resolved",
                resolution="已转入规则修订。",
                linked_knowledge_object_id=None,
                expected_version_no=1,
                request_id="request-resolve",
                occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
            _principal("feedback:manage"),
        )

    assert error.value.code == "VALIDATION_FAILED"
