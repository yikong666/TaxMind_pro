from __future__ import annotations

from datetime import date

import pytest

from taxmind.modules.procedures.application.service import ProceduresRepository, ProceduresService
from taxmind.modules.procedures.domain import ProcedureDefinition
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class _StubRepository:
    def __init__(self, records: list[ProcedureDefinition]) -> None:
        self.records = records
        self.calls: list[dict[str, object]] = []

    async def search_published(
        self,
        *,
        query: str,
        region_code: str,
        business_date: date,
    ) -> list[ProcedureDefinition]:
        self.calls.append(
            {
                "query": query,
                "region_code": region_code,
                "business_date": business_date,
            }
        )
        return self.records


class _StubUnitOfWork:
    def __init__(self, repository: _StubRepository) -> None:
        self.repository: ProceduresRepository | None = repository

    async def __aenter__(self) -> _StubUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal(*permissions: str) -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b103",
        roles=frozenset({"knowledge_reader"}),
        permissions=frozenset(permissions),
    )


def _procedure() -> ProcedureDefinition:
    return ProcedureDefinition(
        procedure_version_id="procedure-v1",
        procedure_code="invoice-red-letter",
        title="虚构红字发票开具指引",
        region_code="440300",
        effective_start=date(2026, 1, 1),
        effective_end=None,
        review_status="published",
        official_url="https://example.gov.cn/procedures/red-letter-invoice",
        source_chunk_ids=("chunk-1",),
        materials=("虚构材料清单",),
        channels=("线上办理",),
    )


async def test_search_published_uses_scoped_repository_for_knowledge_reader() -> None:
    repository = _StubRepository([_procedure()])
    service = ProceduresService(uow_factory=lambda: _StubUnitOfWork(repository))

    records = await service.search_published(
        query=" 红字发票 ",
        region_code="440300",
        business_date=date(2026, 9, 1),
        principal=_principal("knowledge:read"),
    )

    assert records == [_procedure()]
    assert repository.calls == [
        {
            "query": "红字发票",
            "region_code": "440300",
            "business_date": date(2026, 9, 1),
        }
    ]


async def test_search_published_requires_knowledge_read_permission() -> None:
    repository = _StubRepository([])
    service = ProceduresService(uow_factory=lambda: _StubUnitOfWork(repository))

    with pytest.raises(DomainError) as error:
        await service.search_published(
            query="红字发票",
            region_code="440300",
            business_date=date(2026, 9, 1),
            principal=_principal(),
        )

    assert error.value.code == "AUTH_FORBIDDEN"
    assert repository.calls == []
