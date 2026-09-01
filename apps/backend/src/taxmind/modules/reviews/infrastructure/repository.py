from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.reviews.domain import ReviewActionRecord, ReviewTaskRecord
from taxmind.modules.reviews.infrastructure.models import ReviewActionModel, ReviewTaskModel


class SqlAlchemyReviewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_case_profile(
        self, org_id: str, case_id: str, profile_version: int
    ) -> ReviewTaskRecord | None:
        statement = (
            select(ReviewTaskModel)
            .where(
                ReviewTaskModel.org_id == org_id,
                ReviewTaskModel.case_id == case_id,
                ReviewTaskModel.profile_version == profile_version,
                ReviewTaskModel.status.in_(("pending_review", "returned", "escalated")),
            )
            .order_by(ReviewTaskModel.submitted_at.desc())
        )
        model = (await self._session.execute(statement)).scalars().first()
        return _task_record(model) if model is not None else None

    async def create_task(self, task: ReviewTaskRecord) -> None:
        self._session.add(
            ReviewTaskModel(
                id=task.id,
                org_id=task.org_id,
                case_id=task.case_id,
                profile_version=task.profile_version,
                query_run_id=task.query_run_id,
                submitted_by=task.submitted_by,
                assigned_to=task.assigned_to,
                status=task.status,
                priority=task.priority,
                package_summary=task.package_summary,
                version_no=task.version_no,
                submitted_at=task.submitted_at,
                resolved_at=task.resolved_at,
            )
        )

    async def list_tasks(self, org_id: str, *, status: str | None) -> list[ReviewTaskRecord]:
        statement = select(ReviewTaskModel).where(ReviewTaskModel.org_id == org_id)
        if status is not None:
            statement = statement.where(ReviewTaskModel.status == status)
        statement = statement.order_by(ReviewTaskModel.submitted_at.desc())
        return [_task_record(item) for item in (await self._session.execute(statement)).scalars()]

    async def get_task(
        self, task_id: str, org_id: str, *, lock: bool = False
    ) -> ReviewTaskRecord | None:
        statement = select(ReviewTaskModel).where(
            ReviewTaskModel.id == task_id,
            ReviewTaskModel.org_id == org_id,
        )
        if lock:
            statement = statement.with_for_update()
        model = (await self._session.execute(statement)).scalars().first()
        return _task_record(model) if model is not None else None

    async def create_action(self, action: ReviewActionRecord) -> None:
        self._session.add(
            ReviewActionModel(
                id=action.id,
                task_id=action.task_id,
                action_no=action.action_no,
                decision=action.decision,
                comment_safe=action.comment_safe,
                actor_user_id=action.actor_user_id,
                occurred_at=action.occurred_at,
            )
        )

    async def list_actions(self, task_id: str) -> list[ReviewActionRecord]:
        statement = (
            select(ReviewActionModel)
            .where(ReviewActionModel.task_id == task_id)
            .order_by(ReviewActionModel.action_no)
        )
        return [_action_record(item) for item in (await self._session.execute(statement)).scalars()]

    async def set_task(self, task: ReviewTaskRecord) -> None:
        model = await self._session.get(ReviewTaskModel, task.id)
        if model is None:
            raise RuntimeError("review task disappeared during update")
        model.assigned_to = task.assigned_to
        model.status = task.status
        model.version_no = task.version_no
        model.resolved_at = task.resolved_at

    async def create_audit_log(
        self,
        *,
        org_id: str,
        actor_user_id: str,
        action_code: str,
        resource_id: str,
        request_id: str,
        occurred_at: datetime,
    ) -> None:
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type="review_task",
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                ip_hash=None,
                user_agent_hash=None,
                before_json=None,
                after_json=None,
                occurred_at=occurred_at,
            )
        )


def _task_record(model: ReviewTaskModel) -> ReviewTaskRecord:
    return ReviewTaskRecord(
        id=model.id,
        org_id=model.org_id,
        case_id=model.case_id,
        profile_version=model.profile_version,
        query_run_id=model.query_run_id,
        submitted_by=model.submitted_by,
        assigned_to=model.assigned_to,
        status=model.status,  # type: ignore[arg-type]
        priority=model.priority,
        package_summary=model.package_summary,
        version_no=model.version_no,
        submitted_at=model.submitted_at,
        resolved_at=model.resolved_at,
    )


def _action_record(model: ReviewActionModel) -> ReviewActionRecord:
    return ReviewActionRecord(
        id=model.id,
        task_id=model.task_id,
        action_no=model.action_no,
        decision=model.decision,  # type: ignore[arg-type]
        comment_safe=model.comment_safe,
        actor_user_id=model.actor_user_id,
        occurred_at=model.occurred_at,
    )
