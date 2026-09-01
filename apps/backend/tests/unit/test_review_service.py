from __future__ import annotations

from datetime import UTC, datetime

import pytest

from taxmind.modules.reviews.application.service import (
    CreateReviewTaskCommand,
    RecordReviewActionCommand,
    ReviewService,
    ReviewsRepository,
)
from taxmind.modules.reviews.domain import ReviewActionRecord, ReviewTaskRecord
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class _StubRepository:
    def __init__(self) -> None:
        self.task: ReviewTaskRecord | None = None
        self.actions: list[object] = []
        self.audit_calls: list[dict[str, object]] = []

    async def get_active_by_case_profile(
        self, org_id: str, case_id: str, profile_version: int
    ) -> ReviewTaskRecord | None:
        return self.task

    async def create_task(self, task: ReviewTaskRecord) -> None:
        self.task = task

    async def get_task(
        self, task_id: str, org_id: str, *, lock: bool = False
    ) -> ReviewTaskRecord | None:
        return self.task if self.task is not None and self.task.id == task_id else None

    async def list_tasks(self, org_id: str, *, status: str | None) -> list[ReviewTaskRecord]:
        return []

    async def create_action(self, action: ReviewActionRecord) -> None:
        self.actions.append(action)

    async def list_actions(self, task_id: str) -> list[ReviewActionRecord]:
        return []

    async def set_task(self, task: ReviewTaskRecord) -> None:
        self.task = task

    async def create_audit_log(self, **kwargs: object) -> None:
        self.audit_calls.append(kwargs)


class _StubUnitOfWork:
    def __init__(self, repository: _StubRepository) -> None:
        self.repository: ReviewsRepository | None = repository
        self.committed = False

    async def __aenter__(self) -> _StubUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def _principal(user_id: str, *permissions: str) -> Principal:
    return Principal(
        user_id=user_id,
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b103",
        roles=frozenset({"reviewer"}),
        permissions=frozenset(permissions),
    )


async def test_reviewer_cannot_review_task_submitted_by_self() -> None:
    repository = _StubRepository()
    service = ReviewService(uow_factory=lambda: _StubUnitOfWork(repository))
    submitter = _principal("submitter-1", "cases:read")
    task = await service.create_task(
        CreateReviewTaskCommand(
            case_id="case-1",
            profile_version=1,
            query_run_id="run-1",
            package_summary={"rule_version_ids": ["rule-v1"]},
            request_id="request-1",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        submitter,
    )

    with pytest.raises(DomainError) as error:
        await service.record_action(
            RecordReviewActionCommand(
                task_id=task.id,
                decision="approved",
                comment=None,
                expected_version_no=1,
                request_id="request-2",
                occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
            ),
            _principal("submitter-1", "cases:review"),
        )

    assert error.value.code == "AUTH_FORBIDDEN"
    assert repository.actions == []
