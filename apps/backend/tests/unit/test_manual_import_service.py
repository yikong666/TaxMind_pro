from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from taxmind.modules.documents.application.import_service import (
    ManualImportCommand,
    ManualImportService,
)
from taxmind.modules.documents.application.service import (
    ChunkInput,
    DocumentMetadataInput,
    VersionInput,
)
from taxmind.modules.documents.domain import (
    DocumentDetail,
    DocumentVersionRecord,
    SourceDocumentRecord,
)
from taxmind.modules.sources.application.service import CreatedIngestionJob
from taxmind.modules.sources.domain import IngestionJobRecord
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal

_NOW = datetime(2026, 8, 31, tzinfo=UTC)


class _SourcesPort:
    def __init__(self, job: IngestionJobRecord) -> None:
        self.job = job
        self.completed: IngestionJobRecord | None = None
        self.failed: tuple[str, str] | None = None

    async def create_manual_upload_job(
        self, command: object, principal: Principal
    ) -> CreatedIngestionJob:
        del command, principal
        return CreatedIngestionJob(job=self.job, created=True)

    async def mark_job_succeeded(
        self, job_id: str, request_id: str, principal: Principal
    ) -> IngestionJobRecord:
        del request_id, principal
        self.completed = replace(self.job, id=job_id, status="succeeded")
        return self.completed

    async def mark_job_failed(
        self,
        job_id: str,
        error_code: str,
        error_detail_safe: str,
        request_id: str,
        principal: Principal,
    ) -> IngestionJobRecord:
        del request_id, principal
        self.failed = (error_code, error_detail_safe)
        return replace(self.job, id=job_id, status="failed", error_code=error_code)


class _ObjectStorePort:
    def __init__(self, *, fail_upload: bool = False) -> None:
        self.fail_upload = fail_upload
        self.objects: dict[tuple[str, str], tuple[bytes, str, str]] = {}

    async def put_immutable(
        self, bucket: str, key: str, content: bytes, mime_type: str, sha256: str
    ) -> None:
        if self.fail_upload:
            raise RuntimeError("storage unavailable")
        self.objects[(bucket, key)] = (content, mime_type, sha256)


class _DocumentsPort:
    def __init__(self) -> None:
        self.chunk_inputs: list[ChunkInput] = []
        self.detail = DocumentDetail(
            document=SourceDocumentRecord(
                id="018f4cc1-7852-7d5d-8c1c-dbd404e8d301",
                canonical_key="虚构机关::TEST-IMPORT-001",
                title="虚构导入政策",
                doc_no="TEST-IMPORT-001",
                doc_type="announcement",
                source_level="A",
                issuing_authority="虚构机关",
                region_code="000000",
                publish_date=None,
                effective_start=None,
                effective_end=None,
                policy_status="active",
                canonical_url="https://example.invalid/virtual-policy",
                current_version_id=None,
                review_status="draft",
                created_by="018f4cc1-7852-7d5d-8c1c-dbd404e8d101",
                created_at=_NOW,
                updated_at=_NOW,
            ),
            version=DocumentVersionRecord(
                id="018f4cc1-7852-7d5d-8c1c-dbd404e8d302",
                document_id="018f4cc1-7852-7d5d-8c1c-dbd404e8d301",
                version_no=1,
                captured_at=_NOW,
                source_url="https://example.invalid/virtual-policy",
                raw_object_key=None,
                parsed_object_key=None,
                mime_type="text/plain",
                content_hash_sha256="b" * 64,
                parse_status="parsed",
                ocr_status="not_required",
                review_status="draft",
                published_at=None,
                supersedes_version_id=None,
                created_by="018f4cc1-7852-7d5d-8c1c-dbd404e8d101",
            ),
            chunks=[],
        )

    async def create_document(
        self,
        metadata: DocumentMetadataInput,
        version_input: VersionInput,
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail:
        del metadata, version_input, request_id, principal
        return self.detail

    async def create_chunks(
        self,
        version_id: str,
        inputs: list[ChunkInput],
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail:
        del version_id, request_id, principal
        self.chunk_inputs = inputs
        return self.detail


def _job(content_hash: str = "b" * 64) -> IngestionJobRecord:
    return IngestionJobRecord(
        id="018f4cc1-7852-7d5d-8c1c-dbd404e8d201",
        source_site_id="018f4cc1-7852-7d5d-8c1c-dbd404e8d202",
        job_type="manual_file_import",
        trigger_type="api",
        source_url="https://example.invalid",
        input_object_key=(
            "018f4cc1-7852-7d5d-8c1c-dbd404e8d202/"
            "018f4cc1-7852-7d5d-8c1c-dbd404e8d201/raw/" + content_hash + ".txt"
        ),
        dedupe_key="manual-file-import-test",
        status="queued",
        attempt_count=0,
        discovered_count=0,
        changed_count=0,
        error_code=None,
        error_detail_safe=None,
        started_at=None,
        finished_at=None,
        created_by="018f4cc1-7852-7d5d-8c1c-dbd404e8d101",
        created_at=_NOW,
        updated_at=_NOW,
    )


def _principal() -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8d101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8d102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8d103",
        roles=frozenset({"knowledge_admin"}),
        permissions=frozenset({"knowledge:write"}),
    )


def _metadata() -> DocumentMetadataInput:
    return DocumentMetadataInput(
        title="虚构导入政策",
        doc_no="TEST-IMPORT-001",
        doc_type="announcement",
        source_level="A",
        issuing_authority="虚构机关",
        region_code="000000",
        publish_date=None,
        effective_start=None,
        effective_end=None,
        policy_status="active",
        canonical_url="https://example.invalid/virtual-policy",
    )


async def test_manual_import_stores_original_then_creates_draft_document_chunks() -> None:
    content = "第一条 仅用于测试。\n第二条 仍然仅用于测试。".encode()
    job = _job(sha256(content).hexdigest())
    sources = _SourcesPort(job)
    objects = _ObjectStorePort()
    documents = _DocumentsPort()
    service = ManualImportService(
        sources=sources,
        documents=documents,
        object_store=objects,
        raw_bucket="taxmind-raw",
        max_bytes=1024,
    )
    result = await service.import_file(
        ManualImportCommand(
            source_site_id=job.source_site_id,
            filename="virtual-policy.txt",
            mime_type="text/plain",
            content=content,
            metadata=_metadata(),
            request_id="request-stage5-import",
        ),
        _principal(),
    )

    assert result.job.status == "succeeded"
    assert result.document_id == "018f4cc1-7852-7d5d-8c1c-dbd404e8d301"
    assert result.document_version_id == "018f4cc1-7852-7d5d-8c1c-dbd404e8d302"
    assert job.input_object_key is not None
    assert objects.objects[("taxmind-raw", job.input_object_key)] == (
        content,
        "text/plain",
        sha256(content).hexdigest(),
    )
    assert len(documents.chunk_inputs) == 2
    assert sources.failed is None


async def test_manual_import_marks_job_failed_without_exposing_storage_exception() -> None:
    sources = _SourcesPort(_job())
    service = ManualImportService(
        sources=sources,
        documents=_DocumentsPort(),
        object_store=_ObjectStorePort(fail_upload=True),
        raw_bucket="taxmind-raw",
        max_bytes=1024,
    )

    with pytest.raises(DomainError) as error:
        await service.import_file(
            ManualImportCommand(
                source_site_id=_job().source_site_id,
                filename="virtual-policy.txt",
                mime_type="text/plain",
                content="第一条 仅用于测试。".encode(),
                metadata=_metadata(),
                request_id="request-stage5-storage-failure",
            ),
            _principal(),
        )

    assert error.value.code == "INGESTION_PROCESSING_FAILED"
    assert sources.failed == ("INGESTION_OBJECT_STORE_FAILED", "对象存储写入失败")
