from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from taxmind.modules.audit.domain import AuditLogView
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


@dataclass(frozen=True, slots=True)
class AuditSearchQuery:
    resource_type: str | None = None
    resource_id: str | None = None
    action_code: str | None = None
    actor_user_id: str | None = None
    occurred_after: datetime | None = None
    occurred_before: datetime | None = None
    cursor: str | None = None
    limit: int = 50


class AuditRepository(Protocol):
    async def search(self, org_id: str, query: AuditSearchQuery) -> list[AuditLogView]: ...


class AuditUnitOfWork(Protocol):
    @property
    def repository(self) -> AuditRepository | None: ...

    async def __aenter__(self) -> AuditUnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class AuditService:
    def __init__(self, *, uow_factory: Callable[[], AuditUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def search(self, query: AuditSearchQuery, principal: Principal) -> list[AuditLogView]:
        if not principal.has_permission("audit:read"):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无审计查看权限")
        if query.limit < 1 or query.limit > 100:
            raise DomainError(code="VALIDATION_FAILED", message="审计查询分页大小无效")
        async with self._uow_factory() as uow:
            if uow.repository is None:
                raise RuntimeError("audit repository is unavailable")
            return await uow.repository.search(principal.org_id, query)
