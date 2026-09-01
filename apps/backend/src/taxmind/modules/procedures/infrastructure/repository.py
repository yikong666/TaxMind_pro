from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.procedures.domain import ProcedureDefinition
from taxmind.modules.procedures.infrastructure.models import ProcedureVersionModel


class SqlAlchemyProceduresRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_published(
        self, *, query: str, region_code: str, business_date: date
    ) -> list[ProcedureDefinition]:
        pattern = f"%{query.casefold()}%"
        statement = (
            select(ProcedureVersionModel)
            .where(
                ProcedureVersionModel.review_status == "published",
                ProcedureVersionModel.region_code.in_([region_code, "000000"]),
                or_(
                    ProcedureVersionModel.effective_start.is_(None),
                    ProcedureVersionModel.effective_start <= business_date,
                ),
                or_(
                    ProcedureVersionModel.effective_end.is_(None),
                    ProcedureVersionModel.effective_end >= business_date,
                ),
                or_(
                    ProcedureVersionModel.procedure_code.ilike(pattern),
                    ProcedureVersionModel.title.ilike(pattern),
                ),
            )
            .order_by(
                ProcedureVersionModel.region_code.desc(),
                ProcedureVersionModel.version_no.desc(),
            )
        )
        result = await self._session.execute(statement)
        return [_record(row) for row in result.scalars()]


def _record(model: ProcedureVersionModel) -> ProcedureDefinition:
    return ProcedureDefinition(
        procedure_version_id=model.id,
        procedure_code=model.procedure_code,
        title=model.title,
        region_code=model.region_code,
        effective_start=model.effective_start,
        effective_end=model.effective_end,
        review_status=model.review_status,
        official_url=model.official_url,
        source_chunk_ids=tuple(model.source_chunk_ids_json),
        materials=tuple(model.materials_json),
        channels=tuple(model.channels_json),
    )
