from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.application.service import AuditSearchQuery
from taxmind.modules.audit.domain import AuditLogView
from taxmind.modules.audit.infrastructure.models import AuditLogModel


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, org_id: str, query: AuditSearchQuery) -> list[AuditLogView]:
        statement = select(AuditLogModel).where(AuditLogModel.org_id == org_id)
        if query.resource_type is not None:
            statement = statement.where(AuditLogModel.resource_type == query.resource_type)
        if query.resource_id is not None:
            statement = statement.where(AuditLogModel.resource_id == query.resource_id)
        if query.action_code is not None:
            statement = statement.where(AuditLogModel.action_code == query.action_code)
        if query.actor_user_id is not None:
            statement = statement.where(AuditLogModel.actor_user_id == query.actor_user_id)
        if query.occurred_after is not None:
            statement = statement.where(AuditLogModel.occurred_at >= query.occurred_after)
        if query.occurred_before is not None:
            statement = statement.where(AuditLogModel.occurred_at <= query.occurred_before)
        if query.cursor is not None:
            cursor = await self._session.get(AuditLogModel, query.cursor)
            if cursor is not None and cursor.org_id == org_id:
                statement = statement.where(
                    or_(
                        AuditLogModel.occurred_at < cursor.occurred_at,
                        and_(
                            AuditLogModel.occurred_at == cursor.occurred_at,
                            AuditLogModel.id < cursor.id,
                        ),
                    )
                )
        statement = statement.order_by(
            AuditLogModel.occurred_at.desc(), AuditLogModel.id.desc()
        ).limit(query.limit)
        models = (await self._session.execute(statement)).scalars()
        return [_view(model) for model in models]


def _view(model: AuditLogModel) -> AuditLogView:
    return AuditLogView(
        id=model.id,
        action_code=model.action_code,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        actor_user_id=model.actor_user_id,
        request_id=model.request_id,
        result=model.result,
        summary_safe=_safe_summary(model.after_json) or _safe_summary(model.before_json),
        occurred_at=model.occurred_at,
    )


def _safe_summary(payload: dict[str, object] | None) -> str | None:
    if not payload:
        return None
    summary = payload.get("summary_safe") or payload.get("reason_safe")
    return summary if isinstance(summary, str) else None
