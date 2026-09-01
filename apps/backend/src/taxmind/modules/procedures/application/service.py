from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Protocol

from taxmind.modules.procedures.domain import ProcedureDefinition
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class ProceduresRepository(Protocol):
    async def search_published(
        self, *, query: str, region_code: str, business_date: date
    ) -> list[ProcedureDefinition]: ...


class ProceduresUnitOfWork(Protocol):
    @property
    def repository(self) -> ProceduresRepository | None: ...

    async def __aenter__(self) -> ProceduresUnitOfWork: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class ProceduresService:
    def __init__(self, *, uow_factory: Callable[[], ProceduresUnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def search_published(
        self, *, query: str, region_code: str, business_date: date, principal: Principal
    ) -> list[ProcedureDefinition]:
        if not principal.has_permission("knowledge:read"):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无办税事项查看权限")

        async with self._uow_factory() as uow:
            if uow.repository is None:
                raise RuntimeError("procedures repository is not available")
            return await uow.repository.search_published(
                query=query.strip(),
                region_code=region_code,
                business_date=business_date,
            )
