from __future__ import annotations

from datetime import UTC, datetime

import pytest

from taxmind.modules.sources.application.service import (
    CreateManualUploadJobCommand,
    SourcesService,
)
from taxmind.modules.sources.domain import IngestionJobRecord, SourceSiteRecord
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_HASH = "a" * 64
_NOW = datetime(2026, 8, 31, tzinfo=UTC)


class _InMemorySourcesRepository:
    def __init__(self, source: SourceSiteRecord) -> None:
        self.source = source
        self.jobs: list[IngestionJobRecord] = []
        self.audit_actions: list[str] = []

    async def get_source(self, source_id: str) -> SourceSiteRecord | None:
        return self.source if source_id == self.source.id else None

    async def get_job_by_dedupe_key(self, dedupe_key: str) -> IngestionJobRecord | None:
        return next((job for job in self.jobs if job.dedupe_key == dedupe_key), None)

    async def create_job(self, record: IngestionJobRecord) -> None:
        self.jobs.append(record)

    async def create_audit_log(self, **kwargs: object) -> None:
        action_code = kwargs["action_code"]
        assert isinstance(action_code, str)
        self.audit_actions.append(action_code)


class _StubUnitOfWork:
    def __init__(self, repository: _InMemorySourcesRepository) -> None:
        self.repository = repository
        self.committed = False

    async def __aenter__(self) -> _StubUnitOfWork:
        return self

    async def commit(self) -> None:
        self.committed = True

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal() -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c103",
        roles=frozenset({"knowledge_admin"}),
        permissions=frozenset({"knowledge:write"}),
    )


def _source() -> SourceSiteRecord:
    return SourceSiteRecord(
        id="018f4cc1-7852-7d5d-8c1c-dbd404e8c201",
        name="虚构官方来源",
        base_url="https://example.invalid",
        domain="example.invalid",
        source_level="A",
        authority_name="虚构机关",
        region_code="000000",
        collection_method="file_import",
        whitelist_rules={},
        crawl_interval_minutes=None,
        status="draft",
        last_checked_at=None,
        created_by="018f4cc1-7852-7d5d-8c1c-dbd404e8c101",
        created_at=_NOW,
        updated_at=_NOW,
    )


async def test_manual_upload_job_is_idempotent_and_stays_queued_until_processing() -> None:
    repository = _InMemorySourcesRepository(_source())
    unit_of_work = _StubUnitOfWork(repository)
    service = SourcesService(uow_factory=lambda: unit_of_work)  # type: ignore[arg-type]
    command = CreateManualUploadJobCommand(
        source_site_id=repository.source.id,
        filename="virtual-policy.txt",
        content_hash_sha256=_HASH,
        request_id="request-stage5-upload",
    )

    first = await service.create_manual_upload_job(command, _principal())
    repeated = await service.create_manual_upload_job(command, _principal())

    assert first.created is True
    assert first.job.status == "queued"
    assert first.job.job_type == "manual_file_import"
    assert first.job.input_object_key is not None
    assert first.job.input_object_key.endswith(f"/raw/{_HASH}.txt")
    assert repeated.created is False
    assert repeated.job.id == first.job.id
    assert len(repository.jobs) == 1
    assert repository.audit_actions == ["knowledge.ingestion_job.created"]


async def test_manual_upload_job_rejects_unknown_source_and_invalid_hash() -> None:
    repository = _InMemorySourcesRepository(_source())
    service = SourcesService(
        uow_factory=lambda: _StubUnitOfWork(repository)  # type: ignore[arg-type]
    )

    with pytest.raises(DomainError) as missing_source:
        await service.create_manual_upload_job(
            CreateManualUploadJobCommand(
                source_site_id="018f4cc1-7852-7d5d-8c1c-dbd404e8c999",
                filename="virtual-policy.txt",
                content_hash_sha256=_HASH,
                request_id="request-stage5-missing-source",
            ),
            _principal(),
        )
    with pytest.raises(DomainError) as invalid_hash:
        await service.create_manual_upload_job(
            CreateManualUploadJobCommand(
                source_site_id=repository.source.id,
                filename="virtual-policy.txt",
                content_hash_sha256="not-a-sha256",
                request_id="request-stage5-invalid-hash",
            ),
            _principal(),
        )

    assert missing_source.value.code == "RESOURCE_NOT_FOUND"
    assert invalid_hash.value.code == "VALIDATION_FAILED"
