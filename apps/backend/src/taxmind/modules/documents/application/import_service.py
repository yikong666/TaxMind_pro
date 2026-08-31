from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from taxmind.modules.documents.application.parsers import parse_uploaded_document
from taxmind.modules.documents.application.service import (
    ChunkInput,
    DocumentMetadataInput,
    VersionInput,
)
from taxmind.modules.documents.domain import DocumentDetail
from taxmind.modules.sources.application.service import (
    CreatedIngestionJob,
    CreateManualUploadJobCommand,
)
from taxmind.modules.sources.domain import IngestionJobRecord
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class ImmutableObjectStore(Protocol):
    async def put_immutable(
        self,
        bucket: str,
        key: str,
        content: bytes,
        mime_type: str,
        sha256: str,
    ) -> None: ...


class SourcesImportPort(Protocol):
    async def create_manual_upload_job(
        self,
        command: CreateManualUploadJobCommand,
        principal: Principal,
    ) -> CreatedIngestionJob: ...

    async def mark_job_succeeded(
        self,
        job_id: str,
        request_id: str,
        principal: Principal,
    ) -> IngestionJobRecord: ...

    async def mark_job_failed(
        self,
        job_id: str,
        error_code: str,
        error_detail_safe: str,
        request_id: str,
        principal: Principal,
    ) -> IngestionJobRecord: ...


class DocumentsImportPort(Protocol):
    async def create_document(
        self,
        metadata: DocumentMetadataInput,
        version_input: VersionInput,
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail: ...

    async def create_chunks(
        self,
        version_id: str,
        inputs: list[ChunkInput],
        *,
        request_id: str,
        principal: Principal,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class ManualImportCommand:
    source_site_id: str
    filename: str
    mime_type: str
    content: bytes
    metadata: DocumentMetadataInput
    request_id: str


@dataclass(frozen=True, slots=True)
class ManualImportResult:
    job: IngestionJobRecord
    document_id: str | None
    document_version_id: str | None
    chunk_count: int
    idempotent: bool


class ManualImportService:
    def __init__(
        self,
        *,
        sources: SourcesImportPort,
        documents: DocumentsImportPort,
        object_store: ImmutableObjectStore,
        raw_bucket: str,
        max_bytes: int,
    ) -> None:
        self._sources = sources
        self._documents = documents
        self._object_store = object_store
        self._raw_bucket = raw_bucket
        self._max_bytes = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    async def import_file(
        self,
        command: ManualImportCommand,
        principal: Principal,
    ) -> ManualImportResult:
        if not command.content:
            raise DomainError(code="VALIDATION_FAILED", message="导入文件不能为空")
        if len(command.content) > self._max_bytes:
            raise DomainError(code="VALIDATION_FAILED", message="导入文件超过大小限制")
        parsed = parse_uploaded_document(
            content=command.content,
            mime_type=command.mime_type,
            filename=command.filename,
        )
        content_hash = sha256(command.content).hexdigest()
        created = await self._sources.create_manual_upload_job(
            CreateManualUploadJobCommand(
                source_site_id=command.source_site_id,
                filename=command.filename,
                content_hash_sha256=content_hash,
                request_id=command.request_id,
            ),
            principal,
        )
        if not created.created:
            return ManualImportResult(
                job=created.job,
                document_id=None,
                document_version_id=None,
                chunk_count=0,
                idempotent=True,
            )
        job = created.job
        if job.input_object_key is None:
            raise RuntimeError("manual import job is missing an object key")
        try:
            await self._object_store.put_immutable(
                self._raw_bucket,
                job.input_object_key,
                command.content,
                command.mime_type,
                content_hash,
            )
        except Exception as error:
            await self._sources.mark_job_failed(
                job.id,
                "INGESTION_OBJECT_STORE_FAILED",
                "对象存储写入失败",
                command.request_id,
                principal,
            )
            raise DomainError(
                code="INGESTION_PROCESSING_FAILED",
                message="导入原件保存失败,请稍后重试",
            ) from error
        try:
            detail = await self._documents.create_document(
                command.metadata,
                VersionInput(
                    source_url=command.metadata.canonical_url,
                    mime_type=command.mime_type,
                    content_hash_sha256=content_hash,
                    raw_object_key=job.input_object_key,
                    parsed_object_key=None,
                ),
                request_id=command.request_id,
                principal=principal,
            )
            document = detail.document
            version = detail.version
            document_id = _record_id(document, "document")
            version_id = _record_id(version, "document_version")
            chunks = [
                ChunkInput(
                    source_chunk_id=f"{job.id}:{index + 1}",
                    chunk_order=index,
                    chunk_type=chunk.chunk_type,
                    heading_path=chunk.heading_path,
                    clause_label=chunk.clause_label,
                    content_text=chunk.content_text,
                    content_hash_sha256=sha256(chunk.content_text.encode()).hexdigest(),
                    token_count=len(chunk.content_text),
                    effective_start=None,
                    effective_end=None,
                )
                for index, chunk in enumerate(parsed.chunks)
            ]
            await self._documents.create_chunks(
                version_id,
                chunks,
                request_id=command.request_id,
                principal=principal,
            )
            succeeded = await self._sources.mark_job_succeeded(
                job.id,
                command.request_id,
                principal,
            )
        except DomainError:
            await self._sources.mark_job_failed(
                job.id,
                "INGESTION_DOCUMENT_PROCESSING_FAILED",
                "资料解析或草稿写入失败",
                command.request_id,
                principal,
            )
            raise
        except Exception as error:
            await self._sources.mark_job_failed(
                job.id,
                "INGESTION_DOCUMENT_PROCESSING_FAILED",
                "资料解析或草稿写入失败",
                command.request_id,
                principal,
            )
            raise DomainError(
                code="INGESTION_PROCESSING_FAILED",
                message="资料解析失败,请检查文件后重试",
            ) from error
        return ManualImportResult(
            job=succeeded,
            document_id=document_id,
            document_version_id=version_id,
            chunk_count=len(parsed.chunks),
            idempotent=False,
        )


def _record_id(record: object, record_type: str) -> str:
    value = getattr(record, "id", None)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{record_type} record is missing an id")
    return value
