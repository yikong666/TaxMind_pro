from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.cases.infrastructure.models import ConsultationCaseModel
from taxmind.modules.feedback.domain import FeedbackItem
from taxmind.modules.feedback.infrastructure.models import FeedbackItemModel


class SqlAlchemyFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resource_is_visible(
        self, *, org_id: str, resource_type: str, resource_id: str, case_id: str | None
    ) -> bool:
        if resource_type == "case":
            return await _has_org_row(self._session, ConsultationCaseModel, resource_id, org_id)
        if resource_type == "query_run" and case_id is not None:
            return await _has_org_row(self._session, ConsultationCaseModel, case_id, org_id)
        return False

    async def create(self, item: FeedbackItem) -> None:
        self._session.add(_model(item))

    async def list_for_submitter(self, org_id: str, submitted_by: str) -> list[FeedbackItem]:
        statement = (
            select(FeedbackItemModel)
            .where(
                FeedbackItemModel.org_id == org_id, FeedbackItemModel.submitted_by == submitted_by
            )
            .order_by(FeedbackItemModel.submitted_at.desc())
        )
        return [_record(model) for model in (await self._session.execute(statement)).scalars()]

    async def get(
        self, feedback_id: str, org_id: str, *, lock: bool = False
    ) -> FeedbackItem | None:
        statement = select(FeedbackItemModel).where(
            FeedbackItemModel.id == feedback_id, FeedbackItemModel.org_id == org_id
        )
        if lock:
            statement = statement.with_for_update()
        model = (await self._session.execute(statement)).scalars().first()
        return _record(model) if model is not None else None

    async def set(self, item: FeedbackItem) -> None:
        model = await self._session.get(FeedbackItemModel, item.id)
        if model is None:
            raise RuntimeError("feedback item disappeared during update")
        model.status = item.status
        model.linked_knowledge_object_id = item.linked_knowledge_object_id
        model.resolution_safe = item.resolution_safe
        model.handled_by = item.handled_by
        model.version_no = item.version_no
        model.resolved_at = item.resolved_at

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
                resource_type="feedback_item",
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


async def _has_org_row(
    session: AsyncSession, model: type[ConsultationCaseModel], resource_id: str, org_id: str
) -> bool:
    statement = select(model.id).where(model.id == resource_id, model.org_id == org_id)
    return (await session.execute(statement)).scalar_one_or_none() is not None


def _model(item: FeedbackItem) -> FeedbackItemModel:
    return FeedbackItemModel(
        **{name: getattr(item, name) for name in FeedbackItem.__dataclass_fields__}
    )


def _record(model: FeedbackItemModel) -> FeedbackItem:
    return FeedbackItem(
        **{name: getattr(model, name) for name in FeedbackItem.__dataclass_fields__}
    )
