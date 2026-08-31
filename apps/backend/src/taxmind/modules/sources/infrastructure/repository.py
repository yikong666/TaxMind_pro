from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.sources.domain import IngestionJobRecord, SourceSiteRecord
from taxmind.modules.sources.infrastructure.models import IngestionJobModel, SourceSiteModel


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _source_record(model: SourceSiteModel) -> SourceSiteRecord:
    return SourceSiteRecord(
        id=model.id,
        name=model.name,
        base_url=model.base_url,
        domain=model.domain,
        source_level=model.source_level,
        authority_name=model.authority_name,
        region_code=model.region_code,
        collection_method=model.collection_method,
        whitelist_rules=dict(model.whitelist_rules_json),
        crawl_interval_minutes=model.crawl_interval_minutes,
        status=model.status,
        last_checked_at=_as_utc(model.last_checked_at) if model.last_checked_at else None,
        created_by=model.created_by,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def _job_record(model: IngestionJobModel) -> IngestionJobRecord:
    return IngestionJobRecord(
        id=model.id,
        source_site_id=model.source_site_id,
        job_type=model.job_type,
        trigger_type=model.trigger_type,
        source_url=model.source_url,
        input_object_key=model.input_object_key,
        dedupe_key=model.dedupe_key,
        status=model.status,
        attempt_count=model.attempt_count,
        discovered_count=model.discovered_count,
        changed_count=model.changed_count,
        error_code=model.error_code,
        error_detail_safe=model.error_detail_safe,
        started_at=_as_utc(model.started_at) if model.started_at else None,
        finished_at=_as_utc(model.finished_at) if model.finished_at else None,
        created_by=model.created_by,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


class SqlAlchemySourcesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_scope(self, domain: str, region_code: str) -> SourceSiteRecord | None:
        model = await self._session.scalar(
            select(SourceSiteModel).where(
                SourceSiteModel.domain == domain,
                SourceSiteModel.region_code == region_code,
            )
        )
        return _source_record(model) if model else None

    async def create_source(self, record: SourceSiteRecord) -> None:
        self._session.add(
            SourceSiteModel(
                id=record.id,
                name=record.name,
                base_url=record.base_url,
                domain=record.domain,
                source_level=record.source_level,
                authority_name=record.authority_name,
                region_code=record.region_code,
                collection_method=record.collection_method,
                whitelist_rules_json=record.whitelist_rules,
                crawl_interval_minutes=record.crawl_interval_minutes,
                status=record.status,
                last_checked_at=record.last_checked_at,
                created_by=record.created_by,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )

    async def get_source(self, source_id: str) -> SourceSiteRecord | None:
        model = await self._session.get(SourceSiteModel, source_id)
        return _source_record(model) if model else None

    async def get_job_by_dedupe_key(self, dedupe_key: str) -> IngestionJobRecord | None:
        model = await self._session.scalar(
            select(IngestionJobModel).where(IngestionJobModel.dedupe_key == dedupe_key)
        )
        return _job_record(model) if model else None

    async def get_job(self, job_id: str, *, lock: bool = False) -> IngestionJobRecord | None:
        statement = select(IngestionJobModel).where(IngestionJobModel.id == job_id)
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _job_record(model) if model else None

    async def create_job(self, record: IngestionJobRecord) -> None:
        self._session.add(
            IngestionJobModel(
                id=record.id,
                source_site_id=record.source_site_id,
                job_type=record.job_type,
                trigger_type=record.trigger_type,
                source_url=record.source_url,
                input_object_key=record.input_object_key,
                dedupe_key=record.dedupe_key,
                status=record.status,
                attempt_count=record.attempt_count,
                discovered_count=record.discovered_count,
                changed_count=record.changed_count,
                error_code=record.error_code,
                error_detail_safe=record.error_detail_safe,
                started_at=record.started_at,
                finished_at=record.finished_at,
                created_by=record.created_by,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )

    async def update_job(self, record: IngestionJobRecord) -> None:
        model = await self._session.get(IngestionJobModel, record.id)
        if model is None:
            raise RuntimeError("ingestion job disappeared before update")
        model.status = record.status
        model.attempt_count = record.attempt_count
        model.discovered_count = record.discovered_count
        model.changed_count = record.changed_count
        model.error_code = record.error_code
        model.error_detail_safe = record.error_detail_safe
        model.started_at = record.started_at
        model.finished_at = record.finished_at
        model.updated_at = record.updated_at

    async def list_sources(self) -> list[SourceSiteRecord]:
        models = await self._session.scalars(
            select(SourceSiteModel).order_by(
                SourceSiteModel.source_level,
                SourceSiteModel.region_code,
                SourceSiteModel.domain,
            )
        )
        return [_source_record(model) for model in models]

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
                resource_type="source_site",
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )
