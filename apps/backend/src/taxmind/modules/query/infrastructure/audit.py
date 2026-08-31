from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.shared.domain.ids import new_id


class SqlAlchemyQueryAuditRecorder:
    """Persists only trace metadata, never raw query text or model content."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, entry: dict[str, object]) -> None:
        async with self._sessions() as session:
            session.add(
                AuditLogModel(
                    id=new_id(),
                    org_id=_optional_text(entry.get("org_id")),
                    actor_user_id=_optional_text(entry.get("actor_id")),
                    action_code=_required_text(entry, "action_code"),
                    resource_type="query_run",
                    resource_id=_optional_text(entry.get("resource_id")),
                    request_id=_required_text(entry, "request_id"),
                    result=_required_text(entry, "result"),
                    ip_hash=None,
                    user_agent_hash=None,
                    before_json=None,
                    after_json=_after_json(entry.get("after_json")),
                    occurred_at=entry["occurred_at"],
                )
            )
            await session.commit()


def _required_text(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"audit {key} is required")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _after_json(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None
